from dataclasses import dataclass

from moose.computation.base import Operation
from moose.computation.base import ValueType


@dataclass
class PrimitiveOperation(Operation):
    @property
    def dialect(self):
        return "prim"


@dataclass
class SeedType(ValueType):
    pass


@dataclass
class DeriveSeedOperation(PrimitiveOperation):
    nonce: bytes
    output_type: ValueType = SeedType()


@dataclass
class PRFKeyType(ValueType):
    pass


@dataclass
class SampleKeyOperation(PrimitiveOperation):
    output_type: ValueType = PRFKeyType()