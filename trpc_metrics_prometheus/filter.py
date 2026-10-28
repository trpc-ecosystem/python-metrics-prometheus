# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Metrics plugin and the server/client filters that report RPC metrics.

``MetricsPlugin`` loads the config, starts the exporter, and starts the push
loop in each process that initializes worker plugins. The filters are
enabled by listing ``prometheus`` under ``server.filter`` / ``client.filter``.
"""

import threading
from typing import Any

from trpc_sdk.abc import BaseFilter
from trpc_sdk.abc import BasePlugin
from trpc_sdk.abc import FilterAsyncGenHandleType
from trpc_sdk.abc import FilterAsyncGenReturnType
from trpc_sdk.abc import FilterHandleType
from trpc_sdk.abc import FilterReturnType
from trpc_sdk.abc import PluginInitPos
from trpc_sdk.abc import PluginType
from trpc_sdk.abc import TrpcContext
from trpc_sdk.abc import get_message
from trpc_sdk.plugin import register_plugin

from .client import create_client_reporter
from .constants import PLUGIN_NAME
from .constants import SYSTEM_NAME
from .report import initialize
from .report import interval_batch_push
from .server import create_server_reporter
from .utils import GetCodeFunc
from .utils import default_get_code_func
from .version import __version__

# Code mapping used by both filters. Services may replace it when the code lives elsewhere in the response.
DEFAULT_GET_CODE_FUNC: GetCodeFunc = default_get_code_func


@register_plugin(PluginType.METRICS, PLUGIN_NAME, init_pos=PluginInitPos.WORKER, version=__version__, report=True)
class MetricsPlugin(BasePlugin):
    """Loads the plugin config, starts the exporter, and starts the push loop."""

    def start(self):
        """Initialize from config and start the daemon push thread."""
        initialize()
        t = threading.Thread(target=interval_batch_push, args=())
        t.daemon = True
        t.start()


@register_plugin(PluginType.SERVER_FILTER_COMPONENT, PLUGIN_NAME, init_pos=PluginInitPos.WORKER)
class MetricsServerFilter(BaseFilter):
    """Server filter that reports each received RPC."""

    async def run(self, ctx: TrpcContext, req: Any, next_handle: FilterHandleType) -> FilterReturnType:
        """Count the request, run the chain, then record its code and latency."""
        msg = get_message(ctx)
        reporter = create_server_reporter(SYSTEM_NAME, msg.caller_service_name, msg.caller_method,
                                       msg.callee_service_name, msg.callee_method)
        rsp, err = await next_handle()
        reporter.handled(DEFAULT_GET_CODE_FUNC(ctx, req, rsp, err))
        return rsp, err

    async def run_stream(self, ctx: TrpcContext, req: Any,
                         next_handle: FilterAsyncGenHandleType) -> FilterAsyncGenReturnType:
        """Pass streaming results through unchanged; streams are not reported."""
        async for result in next_handle():
            yield result


@register_plugin(PluginType.CLIENT_FILTER_COMPONENT, PLUGIN_NAME, init_pos=PluginInitPos.WORKER)
class MetricsClientFilter(BaseFilter):
    """Client filter that reports each downstream RPC."""

    async def run(self, ctx: TrpcContext, req: Any, next_handle: FilterHandleType) -> FilterReturnType:
        """Count the request, run the chain, then record its code and latency."""
        msg = get_message(ctx)
        reporter = create_client_reporter(SYSTEM_NAME, msg.caller_service_name, msg.caller_method,
                                       msg.callee_service_name, msg.callee_method)
        rsp, err = await next_handle()
        reporter.handled(DEFAULT_GET_CODE_FUNC(ctx, req, rsp, err))
        return rsp, err

    async def run_stream(self, ctx: TrpcContext, req: Any,
                         next_handle: FilterAsyncGenHandleType) -> FilterAsyncGenReturnType:
        """Pass streaming results through unchanged; streams are not reported."""
        async for result in next_handle():
            yield result
