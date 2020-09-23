import asyncio
import random
from typing import Dict
from typing import Optional
from typing import Union

from moose.channels.memory import ChannelManager
from moose.cluster.cluster_spec import load_cluster_spec
from moose.compiler.computation import Computation
from moose.executor.executor import KernelBasedExecutor
from moose.executor.executor import RemoteExecutor


class Runtime:
    def evaluate_computation(
        self, computation: Computation, placement_assignment: Dict
    ):
        sid = random.randrange(2 ** 32)
        tasks = [
            executor.run_computation(
                computation, placement=placement.name, session_id=sid
            )
            for placement, executor in placement_assignment.items()
        ]
        joint_task = asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
        done, _ = asyncio.get_event_loop().run_until_complete(joint_task)
        if any(task.exception() for task in done):
            raise Exception(
                "One or more errors evaluting the computation, see log for details."
            )


class RemoteRuntime(Runtime):
    def __init__(self, cluster_spec: Union[Dict, str]) -> None:
        if isinstance(cluster_spec, str):
            # assume `cluster_spec` is given as a path
            cluster_spec = load_cluster_spec(cluster_spec)
        self.executors = [
            RemoteExecutor(endpoint) for _, endpoint in cluster_spec.items()
        ]


class TestRuntime(Runtime):
    def __init__(self, num_workers) -> None:
        channel_manager = ChannelManager()
        self.executors = [
            KernelBasedExecutor(name=f"worker{i}", channel_manager=channel_manager)
            for i in range(num_workers)
        ]


_RUNTIME: Optional[Runtime] = None


def set_runtime(runtime: Runtime):
    global _RUNTIME
    _RUNTIME = runtime


def get_runtime():
    global _RUNTIME
    assert _RUNTIME is not None
    return _RUNTIME