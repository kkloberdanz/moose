from dataclasses import dataclass
from dataclasses import field
from typing import List

from pymoose.computation.base import Operation
from pymoose.computation.base import Placement
from pymoose.computation.base import ValueType
from pymoose.computation.standard import UnitType


@dataclass
class MpspdzPlacement(Placement):
    player_names: List[str]

    def __hash__(self):
        return hash(self.name)


@dataclass
class MpspdzOperation(Operation):
    @classmethod
    def dialect(cls):
        return "mpspdz"


@dataclass
class MpspdzSaveInputOperation(MpspdzOperation):
    player_index: int
    invocation_key: str
    output_type: ValueType = UnitType()


@dataclass
class MpspdzCallOperation(MpspdzOperation):
    num_players: int
    player_index: int
    mlir: str = field(repr=False)
    invocation_key: str
    coordinator: str
    protocol: str
    output_type: ValueType = UnitType()


@dataclass
class MpspdzLoadOutputOperation(MpspdzOperation):
    player_index: int
    invocation_key: str
    output_type: ValueType