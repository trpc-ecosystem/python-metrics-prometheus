# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Prometheus metrics plugin for the tRPC Python framework.

Importing this package registers the ``prometheus`` metrics plugin and the
``prometheus`` server/client filters. The plugin reads
``plugins.metrics.prometheus``, serves the metrics over HTTP, and optionally
pushes them to a push gateway.

Public API:

    MetricsPlugin: Metrics plugin that loads config and starts exporting.
    MetricsServerFilter: Server filter that reports received RPCs.
    MetricsClientFilter: Client filter that reports downstream RPCs.
    DEFAULT_GET_CODE_FUNC: Code mapping used by the filters at import time.
    default_get_code_func: Default mapping from an RPC result to a code.
    clean_rpc_method: Replace an empty method name with ``"unknown"``.
    ClientReporter: Reports one downstream RPC.
    create_client_reporter: Create a ``ClientReporter`` and count the start.
    ServerReporter: Reports one received RPC.
    create_server_reporter: Create a ``ServerReporter`` and count the start.
    default_code_type_func: Default mapping from a code to a code type.
    get_code_type_func: Return the code-to-type mapping in use.
    set_code_type_func: Replace the code-to-type mapping.
    CodeType: Type of a code classification.
    CodeTypeSuccess: Code type of a successful call.
    CodeTypeException: Code type of a failed call.
    CodeTypeTimeout: Code type of a timed-out call.
    PrometheusConfig: Model of the plugin config section.
    REGISTRY: Registry holding every metric this plugin exports.
    custom_counter: Decorator counting calls to a function.
    custom_gauge: Decorator tracking in-flight calls to a function.
    custom_histogram: Decorator observing call durations of a function.
    init_metrics: Start an HTTP exporter for ``REGISTRY``.
    __version__: Version of this plugin package.
"""

from .client import ClientReporter
from .client import create_client_reporter
from .config import PrometheusConfig
from .constants import CodeType
from .constants import CodeTypeException
from .constants import CodeTypeSuccess
from .constants import CodeTypeTimeout
from .custom import custom_counter
from .custom import custom_gauge
from .custom import custom_histogram
from .filter import DEFAULT_GET_CODE_FUNC
from .filter import MetricsClientFilter
from .filter import MetricsPlugin
from .filter import MetricsServerFilter
from .metrics import default_code_type_func
from .metrics import get_code_type_func
from .metrics import set_code_type_func
from .prometheus import init_metrics
from .registry import REGISTRY
from .server import ServerReporter
from .server import create_server_reporter
from .utils import clean_rpc_method
from .utils import default_get_code_func

__all__ = [
    "MetricsPlugin",
    "MetricsServerFilter",
    "MetricsClientFilter",
    "DEFAULT_GET_CODE_FUNC",
    "default_get_code_func",
    "clean_rpc_method",
    "ClientReporter",
    "create_client_reporter",
    "ServerReporter",
    "create_server_reporter",
    "default_code_type_func",
    "get_code_type_func",
    "set_code_type_func",
    "CodeType",
    "CodeTypeSuccess",
    "CodeTypeException",
    "CodeTypeTimeout",
    "PrometheusConfig",
    "REGISTRY",
    "custom_counter",
    "custom_gauge",
    "custom_histogram",
    "init_metrics",
]
