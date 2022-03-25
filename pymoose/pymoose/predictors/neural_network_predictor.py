import abc
import struct
from enum import Enum

import numpy as np

from pymoose import edsl
from pymoose.predictors import aes_predictor
from pymoose.predictors import predictor_utils


class Activation(Enum):
    IDENTITY = 1
    SIGMOID = 2
    SOFTMAX = 3


class NeuralNetwork(aes_predictor.AesPredictor, metaclass=abc.ABCMeta):
    def __init__(self, weights, biases, activations):
        super().__init__()
        self.weights = weights
        self.biases = biases
        self.activations = activations
        self.n_classes = np.shape(biases[-1])[0]  # infer number of classes

    def apply_layer(self, input, i, fixedpoint_dtype):
        w = self.fixedpoint_constant(
            self.weights[i], plc=self.mirrored, dtype=fixedpoint_dtype
        )
        b = self.fixedpoint_constant(
            self.biases[i], plc=self.mirrored, dtype=fixedpoint_dtype
        )
        y = edsl.dot(input, w)
        z = edsl.add(y, b)
        return z

    def activation_fn(self, z, i):
        activation = self.activations[i]
        if activation == Activation.SIGMOID:
            activation_output = edsl.sigmoid(z)
        # There is a bug in edsl.shape
        #  Relu code:
        #     y_1_shape = edsl.slice(edsl.shape(x), begin=0, end=1)
        #     ones = edsl.ones(y_1_shape, dtype=edsl.float64)
        #     ones = edsl.cast(ones, dtype=fixedpoint_dtype)
        #     zeros = edsl.sub(ones, ones)
        #     activation_output = edsl.maximum([zeros, y_1])
        elif activation == Activation.SOFTMAX:
            activation_output = edsl.softmax(z, axis=1, upmost_index=self.n_classes)
        elif activation == Activation.IDENTITY:
            activation_output = z
        else:
            raise ValueError("Invalid or unsupported activation function")
        return activation_output

    def neural_predictor_fn(self, x, fixedpoint_dtype):
        num_layers = len(self.weights)
        for i in range(num_layers):
            x = self.apply_layer(x, i, fixedpoint_dtype)
            x = self.activation_fn(x, i)
        return x

    def predictor_factory(self, fixedpoint_dtype=predictor_utils.DEFAULT_FIXED_DTYPE):
        @edsl.computation
        def predictor(
            aes_data: edsl.Argument(
                self.alice, vtype=edsl.AesTensorType(dtype=fixedpoint_dtype)
            ),
            aes_key: edsl.Argument(self.replicated, vtype=edsl.AesKeyType()),
        ):
            x = self.handle_aes_input(aes_key, aes_data, decryptor=self.replicated)
            with self.replicated:
                y = self.neural_predictor_fn(x, fixedpoint_dtype)
            return self.handle_output(y, prediction_handler=self.bob)

        return predictor

    @classmethod
    def from_onnx(cls, model_proto):
        # extract activations from operations
        operations = predictor_utils.find_op_types_in_model_proto(model_proto)
        activations = []
        for i in range(len(operations)):
            if operations[i] == "Sigmoid":
                activations.append(Activation.SIGMOID)
            elif operations[i] == "Softmax":
                activations.append(Activation.SOFTMAX)
            if i > 0:
                if operations[i] == "Gemm" and operations[i - 1] == "Gemm":
                    activations.append(Activation.IDENTITY)

        weights_data = predictor_utils.find_parameters_in_model_proto(
            model_proto, "weight", enforce=False
        )
        biases_data = predictor_utils.find_parameters_in_model_proto(
            model_proto, "bias", enforce=False
        )
        weights = []
        for weight in weights_data:
            dimentions = weight.dims
            assert weight is not None
            if weight.data_type != 1:  # FLOATS
                raise ValueError(
                    "Neural Network Weights must be of type FLOATS, found other."
                )
            weight = weight.raw_data
            # decode bytes object
            weight = struct.unpack("f" * (dimentions[0] * dimentions[1]), weight)
            weight = np.asarray(weight)
            weight = weight.reshape(dimentions[0], dimentions[1]).T
            weights.append(weight)

        biases = []
        for bias in biases_data:
            dimentions = bias.dims
            assert bias is not None
            if bias.data_type != 1:  # FLOATS
                raise ValueError(
                    "Neural network biases must be of type FLOATS, found other."
                )
            bias = bias.raw_data
            bias = struct.unpack("f" * dimentions[0], bias)
            bias = np.asarray(bias)
            biases.append(bias)

        return cls(weights, biases, activations)