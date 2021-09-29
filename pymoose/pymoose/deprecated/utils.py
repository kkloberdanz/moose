import asyncio
from pathlib import Path

import grpc
from grpc.experimental import aio as grpc_aio

from pymoose.logger import get_logger


class AsyncStore:
    def __init__(self, initial_values={}, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.key_to_future = dict()
        self.future_to_key = dict()
        for key, value in initial_values.items():
            self.get_future(key).set_result(value)

    async def put(self, key, value):
        if key not in self.key_to_future:
            self._create_future(key)
        return self.key_to_future[key].set_result(value)

    async def get(self, key):
        if key not in self.key_to_future:
            self._create_future(key)
        return await self.key_to_future[key]

    def get_future(self, key):
        if key not in self.key_to_future:
            self._create_future(key)
        return self.key_to_future[key]

    def _create_future(self, key):
        future = self.loop.create_future()
        get_logger().debug(f"Future created: id:{id(future)}, key:{key}")
        self.key_to_future[key] = future
        self.future_to_key[future] = key
        future.add_done_callback(self._future_done_callback)

    def _future_done_callback(self, future):
        key = self.future_to_key[future]
        get_logger().debug(f"Future done: id:{id(future)}, key:{key}")
        # def self.key_to_future[key]
        del self.future_to_key[future]


def load_certificate(filename):
    file = Path(filename) if filename else None
    if file and file.exists():
        with open(str(file), "rb") as f:
            cert = f.read()
            return cert
    return None


class DebugInterceptor(grpc_aio.ServerInterceptor):
    def __init__(self):
        self.handler_type = {
            (False, False): grpc.unary_unary_rpc_method_handler,
        }

    async def intercept_service(self, continuation, handler_call_details):
        handler = await continuation(handler_call_details)

        async def intercepted_handler(request, context):
            get_logger().debug(
                f"Incoming gRPC, "
                f"method:'{handler_call_details.method}', "
                f"peer:'{context.peer()}', "
                f"peer_identities:'{context.peer_identities()}'"
            )
            return await handler.unary_unary(request, context)

        handler_type = self.handler_type.get(
            (handler.request_streaming, handler.response_streaming), None
        )
        if not handler_type:
            raise NotImplementedError(f"Unknown handler {handler}")
        return handler_type(
            intercepted_handler,
            handler.request_deserializer,
            handler.response_serializer,
        )