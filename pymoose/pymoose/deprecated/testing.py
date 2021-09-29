import asyncio
import random
from typing import Dict

from pymoose.computation.base import Computation
from pymoose.deprecated.executor.executor import AsyncExecutor
from pymoose.deprecated.networking.memory import Networking
from pymoose.deprecated.storage.memory import MemoryDataStore
from pymoose.logger import get_logger
from pymoose.logger import get_tracer


class TestRuntime:
    def __init__(self, networking=None, backing_executors=None) -> None:
        self.networking = networking or Networking()
        self.existing_executors = backing_executors or dict()

    def evaluate_computation(
        self,
        computation: Computation,
        placement_instantiation: Dict,
        arguments: Dict = {},
    ):
        placement_instantiation = {
            placement.name if not isinstance(placement, str) else placement: endpoint
            for placement, endpoint in placement_instantiation.items()
        }
        placement_executors = dict()
        for placement, name in placement_instantiation.items():
            if name not in self.existing_executors:
                self.existing_executors[name] = AsyncExecutor(
                    networking=self.networking, storage=MemoryDataStore()
                )
            placement_executors[placement] = self.existing_executors[name]

        sid = random.randrange(2 ** 32)

        with get_tracer().start_as_current_span("eval") as span:
            span.set_attribute("moose.session_id", sid)
            tasks = [
                executor.run_computation(
                    computation,
                    placement_instantiation=placement_instantiation,
                    placement=placement,
                    session_id=sid,
                    arguments=arguments,
                )
                for placement, executor in placement_executors.items()
            ]
            joint_task = asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            done, _ = asyncio.get_event_loop().run_until_complete(joint_task)
            exceptions = [task.exception() for task in done if task.exception()]
            for e in exceptions:
                get_logger().exception(e)
            if exceptions:
                raise Exception(
                    "One or more errors evaluting the computation, see log for details"
                )

    def get_executor(self, executor_name):
        return self.existing_executors[executor_name]


def run_test_computation(computation, players, arguments={}):
    runtime = TestRuntime()
    runtime.evaluate_computation(
        computation,
        placement_instantiation={player: player.name for player in players},
        arguments=arguments,
    )
    return {
        player: runtime.get_executor(player.name).storage.store for player in players
    }