import asyncio
import json
import subprocess
import tempfile

import dill
from grpc.experimental import aio

from moose.compiler.computation import AddOperation
from moose.compiler.computation import CallPythonFunctionOperation
from moose.compiler.computation import ConstantOperation
from moose.compiler.computation import DivOperation
from moose.compiler.computation import LoadOperation
from moose.compiler.computation import MulOperation
from moose.compiler.computation import ReceiveOperation
from moose.compiler.computation import RunProgramOperation
from moose.compiler.computation import SaveOperation
from moose.compiler.computation import SendOperation
from moose.compiler.computation import SubOperation
from moose.logger import get_logger
from moose.storage import AsyncStore
from moose.protos import executor_pb2
from moose.protos import executor_pb2_grpc


class Kernel:
    async def execute(self, op, session_id, output, **kwargs):
        concrete_kwargs = {key: await value for key, value in kwargs.items()}
        concrete_output = self.execute_synchronous_block(
            op=op, session_id=session_id, **concrete_kwargs
        )
        if output:
            output.set_result(concrete_output)

    def execute_synchronous_block(self, op, session_id, **kwargs):
        raise NotImplementedError()


class AddKernel(Kernel):
    def execute_synchronous_block(self, op, session_id, lhs, rhs):
        assert isinstance(op, AddOperation)
        return lhs + rhs


class CallPythonFunctionKernel(Kernel):
    async def execute(self, op, session_id, output, **inputs):
        python_fn = dill.loads(op.pickled_fn)
        concrete_inputs = await asyncio.gather(*inputs.values())
        concrete_output = python_fn(*concrete_inputs)
        return output.set_result(concrete_output)


class ConstantKernel(Kernel):
    def execute_synchronous_block(self, op, session_id):
        assert isinstance(op, ConstantOperation)
        return op.value


class DivKernel(Kernel):
    def execute_synchronous_block(self, op, session_id, lhs, rhs):
        assert isinstance(op, DivOperation)
        return lhs / rhs


class LoadKernel(Kernel):
    def __init__(self, store):
        self.store = store

    def execute_synchronous_block(self, op, session_id):
        assert isinstance(op, LoadOperation)
        return self.store[op.key]


class MulKernel(Kernel):
    def execute_synchronous_block(self, op, session_id, lhs, rhs):
        assert isinstance(op, MulOperation)
        return lhs * rhs


class ReceiveKernel(Kernel):
    def __init__(self, channel_manager):
        self.channel_manager = channel_manager

    async def execute(self, op, session_id, output):
        assert isinstance(op, ReceiveOperation)
        value = await self.channel_manager.receive(op=op, session_id=session_id)
        output.set_result(value)


class RunProgramKernel(Kernel):
    async def execute(self, op, session_id, output, **inputs):
        with tempfile.NamedTemporaryFile() as inputfile:
            with tempfile.NamedTemporaryFile() as outputfile:

                concrete_inputs = await asyncio.gather(*inputs.values())
                inputfile.write(json.dumps(concrete_inputs).encode())
                inputfile.flush()

                args = [
                    op.path,
                    *op.args,
                    "--input-file",
                    inputfile.name,
                    "--output-file",
                    outputfile.name,
                    "--session-id",
                    str(session_id),
                    "--device",
                    op.device_name,
                ]
                get_logger().debug(f"Running external program: {args}")
                _ = subprocess.run(
                    args, stdout=subprocess.PIPE, universal_newlines=True,
                )

                concrete_output = json.loads(outputfile.read())

        return output.set_result(concrete_output)


class SaveKernel(Kernel):
    def __init__(self, store):
        self.store = store

    def execute_synchronous_block(self, op, session_id, value):
        assert isinstance(op, SaveOperation)
        self.store[op.key] = value
        get_logger().debug(f"Saved {value}")


class SendKernel(Kernel):
    def __init__(self, channel_manager):
        self.channel_manager = channel_manager

    async def execute(self, op, session_id, value, output=None):
        assert isinstance(op, SendOperation)
        await self.channel_manager.send(await value, op=op, session_id=session_id)


class SubKernel(Kernel):
    def execute_synchronous_block(self, op, session_id, lhs, rhs):
        assert isinstance(op, SubOperation)
        return lhs - rhs


class KernelBasedExecutor:
    def __init__(self, name, channel_manager, store={}):
        self.name = name
        self.store = store
        self.kernels = {
            LoadOperation: LoadKernel(store),
            SaveOperation: SaveKernel(store),
            SendOperation: SendKernel(channel_manager),
            ReceiveOperation: ReceiveKernel(channel_manager),
            ConstantOperation: ConstantKernel(),
            AddOperation: AddKernel(),
            SubOperation: SubKernel(),
            MulOperation: MulKernel(),
            DivOperation: DivKernel(),
            RunProgramOperation: RunProgramKernel(),
            CallPythonFunctionOperation: CallPythonFunctionKernel(),
        }

    def compile_computation(self, logical_computation):
        # TODO for now we don't do any compilation of computations
        return logical_computation

    async def run_computation(self, logical_computation, placement, session_id):
        physical_computation = self.compile_computation(logical_computation)
        execution_plan = self.schedule_execution(physical_computation, placement)
        # lazily create futures for all edges in the graph
        # link futures together using kernels
        session_values = AsyncStore()
        tasks = []
        for op in execution_plan:
            kernel = self.kernels.get(type(op))
            if not kernel:
                get_logger().fatal(f"No kernel found for operation {type(op)}")

            inputs = {
                param_name: session_values.get_future(key=value_name)
                for (param_name, value_name) in op.inputs.items()
            }
            output = session_values.get_future(key=op.output) if op.output else None
            tasks += [
                asyncio.create_task(
                    kernel.execute(op, session_id=session_id, output=output, **inputs)
                )
            ]
        # execute kernels
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        # address any errors that may have occurred
        exceptions = [task.exception() for task in done if task.exception()]
        for e in exceptions:
            get_logger().exception(e)
        if exceptions:
            raise Exception(f"One or more errors occurred in '{self.name}'")

    def schedule_execution(self, comp, placement):
        # TODO(Morten) this is as simple and naive as it gets; we should at least
        # do some kind of topology sorting to make sure we have all async values
        # ready for linking with kernels in `run_computation`
        return [node for node in comp.nodes() if node.device_name == placement]


class RemoteExecutor:
    def __init__(self, endpoint):
        self.channel = aio.insecure_channel(endpoint)
        self._stub = executor_pb2_grpc.ExecutorStub(self.channel)

    async def run_computation(self, logical_computation, placement, session_id):
        comp_ser = logical_computation.serialize()
        compute_request = executor_pb2.RunComputationRequest(
            computation=comp_ser, placement=placement, session_id=session_id
        )
        _ = await self._stub.RunComputation(compute_request)