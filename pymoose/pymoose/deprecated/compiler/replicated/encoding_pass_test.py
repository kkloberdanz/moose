import unittest

from absl.testing import parameterized

from pymoose.computation import dtypes
from pymoose.computation import standard as standard_ops
from pymoose.computation.base import Computation
from pymoose.computation.host import HostPlacement
from pymoose.computation.replicated import ReplicatedPlacement
from pymoose.computation.standard import TensorType
from pymoose.computation.standard import UnitType
from pymoose.deprecated.compiler.compiler import Compiler
from pymoose.deprecated.compiler.replicated.encoding_pass import ReplicatedEncodingPass
from pymoose.deprecated.computation import fixedpoint as fixedpoint_ops
from pymoose.deprecated.computation.fixedpoint import EncodedTensorType


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
        fp_dtype = dtypes.fixed(8, 27)

        comp.add_operation(
            standard_ops.ConstantOperation(
                name="alice_input",
                inputs={},
                value=1,
                placement_name="alice",
                output_type=TensorType(dtype=dtypes.float64),
            )
        )
        comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_alice",
                inputs={"value": "alice_input"},
                placement_name="alice",
                output_type=EncodedTensorType(
                    dtype=fp_dtype, precision=fp_dtype.fractional_precision,
                ),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            standard_ops.ConstantOperation(
                name="bob_input",
                inputs={},
                value=2,
                placement_name="bob",
                output_type=TensorType(dtype=dtypes.float64),
            )
        )
        comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_bob",
                inputs={"value": "bob_input"},
                placement_name="bob",
                output_type=EncodedTensorType(
                    dtype=fp_dtype, precision=fp_dtype.fractional_precision,
                ),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            standard_ops.AddOperation(
                name="add",
                inputs={"lhs": "encode_alice", "rhs": "encode_bob"},
                placement_name="rep",
                output_type=TensorType(dtype=fp_dtype),
            )
        )
        comp.add_operation(
            standard_ops.MulOperation(
                name="mul",
                inputs={"lhs": "encode_alice", "rhs": "encode_bob"},
                placement_name="rep",
                output_type=TensorType(dtype=fp_dtype),
            )
        )
        comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="dave_add_decode",
                inputs={"value": "add"},
                placement_name="dave",
                output_type=TensorType(dtype=dtypes.float64),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="dave_mul_decode",
                inputs={"value": "mul"},
                placement_name="dave",
                output_type=TensorType(dtype=dtypes.float64),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="eric_add_decode",
                inputs={"value": "add"},
                placement_name="eric",
                output_type=TensorType(dtype=dtypes.float64),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="eric_mul_decode",
                inputs={"value": "mul"},
                placement_name="eric",
                output_type=TensorType(dtype=dtypes.float64),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0",
                inputs={"value": "dave_add_decode"},
                placement_name="dave",
                output_type=UnitType(),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_1",
                inputs={"value": "eric_add_decode"},
                placement_name="eric",
                output_type=UnitType(),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_2",
                inputs={"value": "dave_mul_decode"},
                placement_name="dave",
                output_type=UnitType(),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_3",
                inputs={"value": "eric_mul_decode"},
                placement_name="eric",
                output_type=UnitType(),
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
        expected_encoded_dtype = dtypes.fixed(8, 27)

        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="alice_input",
                inputs={},
                value=1,
                placement_name="alice",
                output_type=TensorType(dtype=dtypes.float64),
            )
        )
        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="bob_input",
                inputs={},
                value=2,
                placement_name="bob",
                output_type=TensorType(dtype=dtypes.float64),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_alice",
                inputs={"value": "alice_input"},
                placement_name="alice",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision,
                ),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_bob",
                inputs={"value": "bob_input"},
                placement_name="bob",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision,
                ),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.AddOperation(
                name="fixed_add_0",
                inputs={"lhs": "encode_alice", "rhs": "encode_bob"},
                placement_name="rep",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision,
                ),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.MulOperation(
                name="fixed_mul_0",
                inputs={"lhs": "encode_alice", "rhs": "encode_bob"},
                placement_name="rep",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision * 2,
                ),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.TruncPrOperation(
                name="trunc_pr_0",
                inputs={"value": "fixed_mul_0"},
                precision=expected_encoded_dtype.fractional_precision,
                placement_name="rep",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision,
                ),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="dave_add_decode",
                inputs={"value": "fixed_add_0"},
                placement_name="dave",
                output_type=TensorType(dtype=dtypes.float64),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="eric_add_decode",
                inputs={"value": "fixed_add_0"},
                placement_name="eric",
                output_type=TensorType(dtype=dtypes.float64),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0",
                inputs={"value": "dave_add_decode"},
                placement_name="dave",
                output_type=UnitType(),
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_1",
                inputs={"value": "eric_add_decode"},
                placement_name="eric",
                output_type=UnitType(),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="dave_mul_decode",
                inputs={"value": "trunc_pr_0"},
                placement_name="dave",
                output_type=TensorType(dtype=dtypes.float64),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="eric_mul_decode",
                inputs={"value": "trunc_pr_0"},
                placement_name="eric",
                output_type=TensorType(dtype=dtypes.float64),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_2",
                inputs={"value": "dave_mul_decode"},
                placement_name="dave",
                output_type=UnitType(),
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_3",
                inputs={"value": "eric_mul_decode"},
                placement_name="eric",
                output_type=UnitType(),
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
        fp_dtype = dtypes.fixed(60, 0)

        comp.add_operation(
            standard_ops.ConstantOperation(
                name="alice_input",
                inputs={},
                value=1,
                placement_name="alice",
                output_type=TensorType(dtype=dtypes.int64),
            )
        )
        comp.add_operation(
            standard_ops.ConstantOperation(
                name="bob_input",
                inputs={},
                value=2,
                placement_name="bob",
                output_type=TensorType(dtype=dtypes.int64),
            )
        )
        comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_alice",
                inputs={"value": "alice_input"},
                placement_name="alice",
                output_type=EncodedTensorType(
                    dtype=fp_dtype, precision=fp_dtype.fractional_precision,
                ),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_bob",
                inputs={"value": "bob_input"},
                placement_name="bob",
                output_type=EncodedTensorType(
                    dtype=fp_dtype, precision=fp_dtype.fractional_precision,
                ),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            standard_ops.AddOperation(
                name="add",
                inputs={"lhs": "encode_alice", "rhs": "encode_bob"},
                placement_name="rep",
                output_type=TensorType(dtype=dtypes.int64),
            )
        )
        comp.add_operation(
            standard_ops.MulOperation(
                name="mul",
                inputs={"lhs": "encode_alice", "rhs": "encode_bob"},
                placement_name="rep",
                output_type=TensorType(dtype=dtypes.int64),
            )
        )
        comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="dave_add_decode",
                inputs={"value": "add"},
                placement_name="dave",
                output_type=TensorType(dtype=dtypes.int64),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="dave_mul_decode",
                inputs={"value": "mul"},
                placement_name="dave",
                output_type=TensorType(dtype=dtypes.int64),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="eric_add_decode",
                inputs={"value": "add"},
                placement_name="eric",
                output_type=TensorType(dtype=dtypes.int64),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="eric_mul_decode",
                inputs={"value": "mul"},
                placement_name="eric",
                output_type=TensorType(dtype=dtypes.int64),
                precision=fp_dtype.fractional_precision,
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0",
                inputs={"value": "dave_add_decode"},
                placement_name="dave",
                output_type=UnitType(),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_1",
                inputs={"value": "eric_add_decode"},
                placement_name="eric",
                output_type=UnitType(),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_2",
                inputs={"value": "dave_mul_decode"},
                placement_name="dave",
                output_type=UnitType(),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_3",
                inputs={"value": "eric_mul_decode"},
                placement_name="eric",
                output_type=UnitType(),
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
        expected_encoded_dtype = dtypes.fixed(60, 0)

        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="alice_input",
                inputs={},
                value=1,
                placement_name="alice",
                output_type=TensorType(dtype=dtypes.int64),
            )
        )
        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="bob_input",
                inputs={},
                value=2,
                placement_name="bob",
                output_type=TensorType(dtype=dtypes.int64),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_alice",
                inputs={"value": "alice_input"},
                placement_name="alice",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision,
                ),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="encode_bob",
                inputs={"value": "bob_input"},
                placement_name="bob",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision,
                ),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.AddOperation(
                name="fixed_add_0",
                inputs={"lhs": "encode_alice", "rhs": "encode_bob"},
                placement_name="rep",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision,
                ),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.MulOperation(
                name="fixed_mul_0",
                inputs={"lhs": "encode_alice", "rhs": "encode_bob"},
                placement_name="rep",
                output_type=EncodedTensorType(
                    dtype=expected_encoded_dtype,
                    precision=expected_encoded_dtype.fractional_precision,
                ),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="dave_add_decode",
                inputs={"value": "fixed_add_0"},
                placement_name="dave",
                output_type=TensorType(dtype=dtypes.int64),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="eric_add_decode",
                inputs={"value": "fixed_add_0"},
                placement_name="eric",
                output_type=TensorType(dtype=dtypes.int64),
                precision=expected_encoded_dtype.fractional_precision,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0",
                inputs={"value": "dave_add_decode"},
                placement_name="dave",
                output_type=UnitType(),
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_1",
                inputs={"value": "eric_add_decode"},
                placement_name="eric",
                output_type=UnitType(),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="dave_mul_decode",
                inputs={"value": "fixed_mul_0"},
                placement_name="dave",
                output_type=TensorType(dtype=dtypes.int64),
                precision=0,
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="eric_mul_decode",
                inputs={"value": "fixed_mul_0"},
                placement_name="eric",
                output_type=TensorType(dtype=dtypes.int64),
                precision=0,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_2",
                inputs={"value": "dave_mul_decode"},
                placement_name="dave",
                output_type=UnitType(),
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_3",
                inputs={"value": "eric_mul_decode"},
                placement_name="eric",
                output_type=UnitType(),
            )
        )

        assert comp.placements == expected_comp.placements
        assert comp.operations == expected_comp.operations
        assert comp == expected_comp


if __name__ == "__main__":
    unittest.main()