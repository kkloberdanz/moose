import json
import re
from dataclasses import asdict
from dataclasses import dataclass
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

OPS_REGISTER = {}


@dataclass
class Operation:
    device_name: str
    name: str
    inputs: Dict[str, str]
    output: Optional[str]

    @classmethod
    def identifier(cls):
        return cls.__name__


@dataclass
class AddOperation(Operation):
    pass


@dataclass
class CallPythonFunctionOperation(Operation):
    pickled_fn: bytes


@dataclass
class ConstantOperation(Operation):
    value: Union[int, float]


@dataclass
class DivOperation(Operation):
    pass


@dataclass
class LoadOperation(Operation):
    key: str


@dataclass
class MulOperation(Operation):
    pass


@dataclass
class ReceiveOperation(Operation):
    sender: str
    receiver: str
    rendezvous_key: str


@dataclass
class RunProgramOperation(Operation):
    path: str
    args: List[str]


@dataclass
class SaveOperation(Operation):
    key: str


@dataclass
class SubOperation(Operation):
    pass


@dataclass
class SendOperation(Operation):
    sender: str
    receiver: str
    rendezvous_key: str


@dataclass
class Graph:
    nodes: Dict[str, Operation]


@dataclass
class Computation:
    graph: Graph

    def devices(self):
        return set(node.device_name for node in self.graph.nodes.values())

    def nodes(self):
        return self.graph.nodes.values()

    def node(self, name):
        return self.graph.nodes.get(name)

    def serialize(self):
        return json.dumps(asdict(self)).encode("utf-8")

    @classmethod
    def deserialize(cls, bytes_stream):
        computation_dict = json.loads(bytes_stream.decode("utf-8"))
        nodes_dict = computation_dict["graph"]["nodes"]
        nodes = {node: select_op(node)(**args) for node, args in nodes_dict.items()}
        return Computation(Graph(nodes))


def register_op(op):
    OPS_REGISTER[op.identifier()] = op


def select_op(op_name):
    name = op_name.split("_")[0]
    if "operation" in name:
        name = re.sub("operation", "", name)
    name = name[0].upper() + name[1:] + "Operation"
    op = OPS_REGISTER[name]
    return op


# NOTE: this is only needed for gRPC so far
register_op(AddOperation)
register_op(CallPythonFunctionOperation)
register_op(RunProgramOperation)
register_op(LoadOperation)
register_op(ConstantOperation)
register_op(DivOperation)
register_op(MulOperation)
register_op(SaveOperation)
register_op(SendOperation)
register_op(SubOperation)
register_op(ReceiveOperation)