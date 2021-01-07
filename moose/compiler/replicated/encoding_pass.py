from moose.compiler.replicated.subgraph_replace_pass import SubgraphReplacementPass
from moose.computation import fixedpoint as fixedpoint_dialect
from moose.computation import replicated as rep_dialect
from moose.computation import standard as std_dialect


class ReplicatedEncodingPass(SubgraphReplacementPass):
    """Lower standard ops to fixedpoint ops on replicated placements.
    """

    def __init__(self):
        super().__init__()
        self.incoming_edge_cache = None
        self.outgoing_edge_cache = None

    def run(self, computation, context):
        self.incoming_edge_cache = dict()
        self.outgoing_edge_cache = dict()
        return super().run(computation, context)

    def collect_subgraph(self):
        op_names_to_process = set()
        for op in self.computation.operations.values():
            if not isinstance(op, std_dialect.StandardOperation):
                continue
            op_placement = self.computation.placement(op.placement_name)
            if not isinstance(op_placement, rep_dialect.ReplicatedPlacement):
                continue
            op_names_to_process.add(op.name)
        return op_names_to_process

    def process_AddOperation(self, op, processed_inputs):
        assert isinstance(op, std_dialect.AddOperation)
        lowered_lhs_op = processed_inputs["lhs"]
        lowered_rhs_op = processed_inputs["rhs"]
        lhs_output_type = lowered_lhs_op.output_type
        rhs_output_type = lowered_rhs_op.output_type
        assert isinstance(lhs_output_type, fixedpoint_dialect.EncodedTensorType)
        assert isinstance(rhs_output_type, fixedpoint_dialect.EncodedTensorType)
        assert lhs_output_type.datatype == rhs_output_type.datatype
        assert lhs_output_type.precision == rhs_output_type.precision
        output_type = fixedpoint_dialect.EncodedTensorType(
            datatype=lhs_output_type.datatype, precision=lhs_output_type.precision,
        )
        return self.computation.add(
            fixedpoint_dialect.AddOperation(
                name=self.context.get_fresh_name("fixed_add"),
                placement_name=op.placement_name,
                inputs={"lhs": lowered_lhs_op.name, "rhs": lowered_rhs_op.name},
                output_type=output_type,
            )
        )

    def process_SubOperation(self, op, processed_inputs):
        assert isinstance(op, std_dialect.SubOperation)
        lowered_lhs_op = processed_inputs["lhs"]
        lowered_rhs_op = processed_inputs["rhs"]
        lhs_output_type = lowered_lhs_op.output_type
        rhs_output_type = lowered_rhs_op.output_type
        assert isinstance(lhs_output_type, fixedpoint_dialect.EncodedTensorType)
        assert isinstance(rhs_output_type, fixedpoint_dialect.EncodedTensorType)
        assert lhs_output_type.datatype == rhs_output_type.datatype
        assert lhs_output_type.precision == rhs_output_type.precision
        output_type = fixedpoint_dialect.EncodedTensorType(
            datatype=lhs_output_type.datatype, precision=lhs_output_type.precision,
        )
        return self.computation.add(
            fixedpoint_dialect.SubOperation(
                name=self.context.get_fresh_name("fixed_add"),
                placement_name=op.placement_name,
                inputs={"lhs": lowered_lhs_op.name, "rhs": lowered_rhs_op.name},
                output_type=output_type,
            )
        )

    def process_MulOperation(self, op, processed_inputs):
        assert isinstance(op, std_dialect.MulOperation)
        lowered_lhs_op = processed_inputs["lhs"]
        lowered_rhs_op = processed_inputs["rhs"]
        lhs_output_type = lowered_lhs_op.output_type
        rhs_output_type = lowered_rhs_op.output_type
        assert isinstance(lhs_output_type, fixedpoint_dialect.EncodedTensorType)
        assert isinstance(rhs_output_type, fixedpoint_dialect.EncodedTensorType)
        assert lhs_output_type.datatype == rhs_output_type.datatype
        assert lhs_output_type.precision == rhs_output_type.precision
        output_type = fixedpoint_dialect.EncodedTensorType(
            datatype=lhs_output_type.datatype,
            precision=lhs_output_type.precision + rhs_output_type.precision,
        )
        mul_op = self.computation.add(
            fixedpoint_dialect.MulOperation(
                name=self.context.get_fresh_name("fixed_mul"),
                placement_name=op.placement_name,
                inputs={"lhs": lowered_lhs_op.name, "rhs": lowered_rhs_op.name},
                output_type=output_type,
            )
        )
        # TODO(Morten) insert trunc op
        return mul_op

    def process_DotOperation(self, op, processed_inputs):
        assert isinstance(op, std_dialect.DotOperation)
        lowered_lhs_op = processed_inputs["lhs"]
        lowered_rhs_op = processed_inputs["rhs"]
        lhs_output_type = lowered_lhs_op.output_type
        rhs_output_type = lowered_rhs_op.output_type
        assert isinstance(lhs_output_type, fixedpoint_dialect.EncodedTensorType)
        assert isinstance(rhs_output_type, fixedpoint_dialect.EncodedTensorType)
        assert lhs_output_type.datatype == rhs_output_type.datatype
        assert lhs_output_type.precision == rhs_output_type.precision
        output_type = fixedpoint_dialect.EncodedTensorType(
            datatype=lhs_output_type.datatype,
            precision=lhs_output_type.precision + rhs_output_type.precision,
        )
        dot_op = self.computation.add(
            fixedpoint_dialect.DotOperation(
                name=self.context.get_fresh_name("fixed_dot"),
                placement_name=op.placement_name,
                inputs={"lhs": lowered_lhs_op.name, "rhs": lowered_rhs_op.name},
                output_type=output_type,
            )
        )
        # TODO(Morten) insert trunc op
        return dot_op

    def process_incoming_edge(self, src_op_name, input_key, dst_op_name):
        src_op = self.computation.operation(src_op_name)
        dst_op = self.computation.operation(dst_op_name)
        assert isinstance(src_op, std_dialect.StandardOperation)

        cache_key = (src_op.name, dst_op.placement_name)
        if cache_key not in self.incoming_edge_cache:
            (datatype, precision) = {"float": ("fixed64", 16), "int64": ("fixed64", 0)}[
                src_op.output_type.datatype
            ]
            self.incoming_edge_cache[cache_key] = self.computation.add_operation(
                fixedpoint_dialect.EncodeOperation(
                    name=self.context.get_fresh_name("encode"),
                    placement_name=dst_op.placement_name,
                    inputs={"value": src_op.name},
                    output_type=fixedpoint_dialect.EncodedTensorType(
                        datatype=datatype, precision=precision
                    ),
                    precision=precision,
                )
            )

        return self.incoming_edge_cache[cache_key]

    def process_outgoing_edge(self, src_op, input_key, dst_op_name):
        assert isinstance(src_op, fixedpoint_dialect.FixedpointOperation), type(src_op)

        cache_key = (src_op.name,)
        if cache_key not in self.outgoing_edge_cache:
            assert src_op.output_type.datatype == "fixed64"
            if src_op.output_type.precision > 0:
                datatype = "float"
            else:
                datatype = "int64"
            self.outgoing_edge_cache[cache_key] = self.computation.add_operation(
                fixedpoint_dialect.DecodeOperation(
                    name=self.context.get_fresh_name("decode"),
                    placement_name=src_op.placement_name,
                    inputs={"value": src_op.name},
                    output_type=std_dialect.TensorType(datatype=datatype),
                    precision=src_op.output_type.precision,
                )
            )

        return self.outgoing_edge_cache[cache_key].name