import unittest

from absl.testing import parameterized

from moose.compiler.compiler import Compiler
from moose.compiler.fixedpoint import host_encoding_pass
from moose.computation import dtypes
from moose.computation import fixedpoint as fixedpoint_ops
from moose.computation import standard as standard_ops
from moose.computation.base import Computation
from moose.computation.host import HostPlacement
from moose.computation.standard import TensorType


class HostEncodingPassTest(parameterized.TestCase):
    def test_cast_into_fixed(self):
        comp = Computation(placements={}, operations={})
        comp.add_placement(HostPlacement(name="alice"))
        comp.add_operation(
            standard_ops.ConstantOperation(
                name="x",
                inputs={},
                value=2,
                placement_name="alice",
                output_type=TensorType(dtype=dtypes.float64),
            )
        )
        comp.add_operation(
            standard_ops.CastOperation(
                name="x_cast",
                placement_name="alice",
                inputs={"value": "x"},
                output_type=TensorType(dtype=dtypes.fixed(14, 23)),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0", placement_name="alice", inputs={"value": "x_cast"},
            )
        )

        compiler = Compiler(passes=[host_encoding_pass.HostEncodingPass()])
        comp = compiler.run_passes(comp)

        expected_comp = Computation(placements={}, operations={})
        expected_comp.add_placement(HostPlacement(name="alice"))
        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="x",
                inputs={},
                value=2,
                placement_name="alice",
                output_type=TensorType(dtype=dtypes.float64),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.EncodeOperation(
                name="fixed_encode_0",
                placement_name="alice",
                inputs={"value": "x"},
                output_type=fixedpoint_ops.EncodedTensorType(
                    dtype=dtypes.fixed(14, 23), precision=23,
                ),
                precision=23,
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0",
                placement_name="alice",
                inputs={"value": "fixed_encode_0"},
            )
        )
        assert comp.operations == expected_comp.operations
        assert comp == expected_comp

    def test_cast_from_fixed(self):
        comp = Computation(placements={}, operations={})

        comp.add_placement(HostPlacement(name="alice"))
        comp.add_operation(
            standard_ops.ConstantOperation(
                name="x",
                inputs={},
                value=2,
                placement_name="alice",
                output_type=TensorType(dtype=dtypes.fixed(14, 23)),
            )
        )
        comp.add_operation(
            standard_ops.CastOperation(
                name="x_cast",
                placement_name="alice",
                inputs={"value": "x"},
                output_type=TensorType(dtype=dtypes.float64),
            )
        )
        comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0", placement_name="alice", inputs={"value": "x_cast"},
            )
        )

        compiler = Compiler(passes=[host_encoding_pass.HostEncodingPass()])
        comp = compiler.run_passes(comp)

        expected_comp = Computation(placements={}, operations={})
        expected_comp.add_placement(HostPlacement(name="alice"))
        expected_comp.add_operation(
            standard_ops.ConstantOperation(
                name="x",
                inputs={},
                value=2,
                placement_name="alice",
                output_type=TensorType(dtype=dtypes.fixed(14, 23)),
            )
        )
        expected_comp.add_operation(
            fixedpoint_ops.DecodeOperation(
                name="fixed_decode_0",
                placement_name="alice",
                inputs={"value": "x"},
                precision=23,
                output_type=TensorType(dtypes.float64),
            )
        )
        expected_comp.add_operation(
            standard_ops.OutputOperation(
                name="output_0",
                placement_name="alice",
                inputs={"value": "fixed_decode_0"},
            )
        )
        assert comp.operations == expected_comp.operations
        assert comp == expected_comp


if __name__ == "__main__":
    unittest.main()