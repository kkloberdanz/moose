from dataclasses import dataclass

from pymoose.computation.base import Placement


@dataclass
class HostPlacement(Placement):
    def __hash__(self):
        return hash(self.name)

    @classmethod
    def dialect(cls):
        return "host"