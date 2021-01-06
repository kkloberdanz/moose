import unittest

from absl.testing import parameterized

from moose.compiler.compiler import Compiler
from moose.compiler.replicated.encoding_pass import ReplicatedEncodingPass
from moose.computation import fixedpoint as fixedpoint_ops
from moose.computation import standard as standard_ops
from moose.computation.base import Computation
from moose.computation.fixedpoint import EncodedTensorType
from moose.computation.host import HostPlacement
from moose.computation.replicated import ReplicatedPlacement
from moose.computation.standard import TensorType


class ReplicatedTest(parameterized.TestCase):
    def test_float_encoding_pass(self):
        comp = Computation(placements={}, operations={})

        comp.add_placement(HostPlacement(name="alice"))
        comp.add_placement(HostPlacement(name="bob"))
        comp.add_placement(HostPlacement(name="carole"))
        comp.add_placement(
            ReplicatedPlacement(name="rep", player_names=["alice", "bob", "carole"])
        )
        comp.add_placement(HostPlacement(name="dave"))
        comp.add_placement(HostPlacement(name="eric"))

        comp.add_operation(
            standard_ops.ConstantOperation(
                name="alice_input",
                inputs={},
                value=1,
                placement_name="alice",
                output_type=TensorType(datatype="float"),
            )
        )
        comp.add_operation(
            standard_ops.ConstantOperation(
                name="bob_input",
                inputs={},
                value=2,
                placement_name="bob",
                output_type=TensorType(datatype="float"),
            )
        )
        comp.add_operation(
            standard_ops.AddOperation(
                name="add",
                inputs={"lhs": "alice_input", "rhs": "bob_input"},
                placement_name="rep",
                output_type=TensorType(datatype="float"),
            )
        )
        comp.add_operation(
            standard_ops.MulOperation(
                name="mul",
                inputs={"lhs": "alice_input", "rhs": "bob_input"},
                placement_name="rep",
                output_type=TensorType(datatype="float"),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0", inputs={"value": "add"}, placement_name="dave"
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_1", inputs={"value": "add"}, placement_name="eric"
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_2", inputs={"value": "mul"}, placement_name="dave"
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_3", inputs={"value": "mul"}, placement_name="eric"
            )
        )

        compiler = Compiler(passes=[ReplicatedEncodingPass()])
        comp = compiler.run_passes(comp)

        expected_comp = Computation(placements={}, operations={})
        expected_comp.add_placement(HostPlacement(name="alice"))
        expected_comp.add_placement(HostPlacement(name="bob"))
        expected_comp.add_placement(HostPlacement(name="carole"))
        expected_comp.add_placement(
            ReplicatedPlacement(name="rep", player_names=["alice", "bob", "carole"])
        )
        expected_comp.add_placement(HostPlacement(name="dave"))
        expected_comp.add_placement(HostPlacement(name="eric"))

        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="alice_input",
                inputs={},
                value=1,
                placement_name="alice",
                output_type=TensorType(datatype="float"),
            )
        )
        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="bob_input",
                inputs={},
                value=2,
                placement_name="bob",
                output_type=TensorType(datatype="float"),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_0",
                inputs={"value": "alice_input"},
                placement_name="rep",
                output_type=EncodedTensorType(datatype="fixed64", precision=16),
                precision=16,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_1",
                inputs={"value": "bob_input"},
                placement_name="rep",
                output_type=EncodedTensorType(datatype="fixed64", precision=16),
                precision=16,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.AddOperation(
                name="fixed_add_0",
                inputs={"lhs": "encode_0", "rhs": "encode_1"},
                placement_name="rep",
                output_type=EncodedTensorType(datatype="fixed64", precision=16),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.MulOperation(
                name="fixed_mul_0",
                inputs={"lhs": "encode_0", "rhs": "encode_1"},
                placement_name="rep",
                output_type=EncodedTensorType(datatype="fixed64", precision=32),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="decode_0",
                inputs={"value": "fixed_add_0"},
                placement_name="rep",
                output_type=TensorType(datatype="float"),
                precision=16,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0", inputs={"value": "decode_0"}, placement_name="dave"
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_1", inputs={"value": "decode_0"}, placement_name="eric"
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="decode_1",
                inputs={"value": "fixed_mul_0"},
                placement_name="rep",
                output_type=TensorType(datatype="float"),
                precision=32,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_2", inputs={"value": "decode_1"}, placement_name="dave"
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_3", inputs={"value": "decode_1"}, placement_name="eric"
            )
        )

        assert comp.placements == expected_comp.placements
        assert comp.operations == expected_comp.operations
        assert comp == expected_comp

    def test_int_encoding_pass(self):
        comp = Computation(placements={}, operations={})

        comp.add_placement(HostPlacement(name="alice"))
        comp.add_placement(HostPlacement(name="bob"))
        comp.add_placement(HostPlacement(name="carole"))
        comp.add_placement(
            ReplicatedPlacement(name="rep", player_names=["alice", "bob", "carole"])
        )
        comp.add_placement(HostPlacement(name="dave"))
        comp.add_placement(HostPlacement(name="eric"))

        comp.add_operation(
            standard_ops.ConstantOperation(
                name="alice_input",
                inputs={},
                value=1,
                placement_name="alice",
                output_type=TensorType(datatype="int64"),
            )
        )
        comp.add_operation(
            standard_ops.ConstantOperation(
                name="bob_input",
                inputs={},
                value=2,
                placement_name="bob",
                output_type=TensorType(datatype="int64"),
            )
        )
        comp.add_operation(
            standard_ops.AddOperation(
                name="add_0",
                inputs={"lhs": "alice_input", "rhs": "bob_input"},
                placement_name="rep",
                output_type=TensorType(datatype="int64"),
            )
        )
        comp.add_operation(
            standard_ops.MulOperation(
                name="add_1",
                inputs={"lhs": "alice_input", "rhs": "bob_input"},
                placement_name="rep",
                output_type=TensorType(datatype="int64"),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0", inputs={"value": "add_0"}, placement_name="dave"
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_1", inputs={"value": "add_0"}, placement_name="eric"
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_2", inputs={"value": "add_1"}, placement_name="dave"
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_3", inputs={"value": "add_1"}, placement_name="eric"
            )
        )

        compiler = Compiler(passes=[ReplicatedEncodingPass()])
        comp = compiler.run_passes(comp)

        expected_comp = Computation(placements={}, operations={})
        expected_comp.add_placement(HostPlacement(name="alice"))
        expected_comp.add_placement(HostPlacement(name="bob"))
        expected_comp.add_placement(HostPlacement(name="carole"))
        expected_comp.add_placement(
            ReplicatedPlacement(name="rep", player_names=["alice", "bob", "carole"])
        )
        expected_comp.add_placement(HostPlacement(name="dave"))
        expected_comp.add_placement(HostPlacement(name="eric"))

        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="alice_input",
                inputs={},
                value=1,
                placement_name="alice",
                output_type=TensorType(datatype="int64"),
            )
        )
        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="bob_input",
                inputs={},
                value=2,
                placement_name="bob",
                output_type=TensorType(datatype="int64"),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_0",
                inputs={"value": "alice_input"},
                placement_name="rep",
                output_type=EncodedTensorType(datatype="fixed64", precision=0),
                precision=0,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_1",
                inputs={"value": "bob_input"},
                placement_name="rep",
                output_type=EncodedTensorType(datatype="fixed64", precision=0),
                precision=0,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.AddOperation(
                name="fixed_add_0",
                inputs={"lhs": "encode_0", "rhs": "encode_1"},
                placement_name="rep",
                output_type=EncodedTensorType(datatype="fixed64", precision=0),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.MulOperation(
                name="fixed_mul_0",
                inputs={"lhs": "encode_0", "rhs": "encode_1"},
                placement_name="rep",
                output_type=EncodedTensorType(datatype="fixed64", precision=0),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="decode_0",
                inputs={"value": "fixed_add_0"},
                placement_name="rep",
                output_type=TensorType(datatype="int64"),
                precision=0,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0", inputs={"value": "decode_0"}, placement_name="dave"
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_1", inputs={"value": "decode_0"}, placement_name="eric"
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="decode_1",
                inputs={"value": "fixed_mul_0"},
                placement_name="rep",
                output_type=TensorType(datatype="int64"),
                precision=0,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_2", inputs={"value": "decode_1"}, placement_name="dave"
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_3", inputs={"value": "decode_1"}, placement_name="eric"
            )
        )

        assert comp.placements == expected_comp.placements
        assert comp.operations == expected_comp.operations
        assert comp == expected_comp


if __name__ == "__main__":
    unittest.main()
