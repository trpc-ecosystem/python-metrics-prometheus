# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Greeter service implementation used by the example server."""

import os
import sys

from trpc_sdk.abc import TrpcContext
from trpc_sdk.log import logger

# add the stub to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "stub")))  # noqa

from trpc_trpc_python_group_helloworld import pb
from trpc_trpc_python_group_helloworld import rpc


class GreeterServicer(rpc.GreeterServicer):
    """Provides methods that implement functionality of greeter servicer."""

    def __init__(self):
        """Create a Greeter servicer with no extra state."""
        pass

    async def SayHello(self, ctx: TrpcContext, request: pb.HelloRequest) -> pb.HelloReply:
        """Reply with the request message prefixed by ``hello: ``.

        Args:
            ctx: tRPC request context. This example does not read it.
            request: Incoming hello request.

        Returns:
            A reply whose ``msg`` is ``hello: `` plus ``request.msg``.
        """
        logger.info(f"test log in SayHello req: {request.msg}")
        rsp = pb.HelloReply()
        rsp.msg = "hello: " + request.msg
        return rsp
