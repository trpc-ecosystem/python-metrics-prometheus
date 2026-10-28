# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""RPC metric definitions and the label helpers every metric shares.

Every metric carries the labels from ``add_ex_label_names`` after its own,
filled from the prometheus plugin config by ``add_ex_label_values``.
"""

import os
from typing import Callable

from prometheus_client import Counter
from prometheus_client import Histogram

from .constants import CodeType
from .constants import CodeTypeException
from .constants import CodeTypeSuccess
from .constants import KEY_APP
from .constants import KEY_CONTAINER_NAME
from .constants import KEY_ENV_NAME
from .constants import KEY_INSTANCE
from .constants import KEY_NAMESPACE
from .constants import KEY_PID
from .constants import KEY_SERVER
from .constants import KEY_SET_NAME
from .registry import REGISTRY
from .report import get_prometheus_config


def add_ex_label_names(*labels):
    """Append the shared label names to a metric's own label names."""
    return labels + (KEY_NAMESPACE, KEY_APP, KEY_SERVER, KEY_ENV_NAME, KEY_SET_NAME, KEY_INSTANCE,
                     KEY_CONTAINER_NAME, KEY_PID)


def add_ex_label_values(*values):
    """Append the shared label values, in ``add_ex_label_names`` order, to a metric's own values."""
    prometheus_config = get_prometheus_config()
    return values + (prometheus_config.namespace, prometheus_config.app, prometheus_config.server,
                     prometheus_config.env_name, prometheus_config.set_name, prometheus_config.ip,
                     prometheus_config.container, str(os.getpid()))


# Requests this service started toward downstream services.
CLIENT_STARTED_COUNTER = Counter(name="client_started_total",
                                 documentation="Total number of RPCs started on the client.",
                                 subsystem="rpc",
                                 registry=REGISTRY,
                                 labelnames=add_ex_label_names("system_name", "caller_service", "caller_method",
                                                               "callee_service", "callee_method"))

# Downstream requests this service finished, successful or not.
CLIENT_HANDLED_COUNTER = Counter(
    name="client_handled_total",
    documentation="Total number of RPCs completed by the client, regardless of success or failure.",
    subsystem="rpc",
    registry=REGISTRY,
    labelnames=add_ex_label_names("system_name", "caller_service", "caller_method", "callee_service", "callee_method",
                                  "code", "code_type"))

# Latency of downstream requests.
CLIENT_HANDLED_HISTOGRAM = Histogram(
    name="client_handled_seconds",
    documentation="Histogram of response latency (seconds) of the RPC until it is finished by the application",
    subsystem="rpc",
    registry=REGISTRY,
    buckets=(.005, .01, .1, .5, 1, 5),
    labelnames=add_ex_label_names("system_name", "caller_service", "caller_method", "callee_service", "callee_method"))

# Requests this service received.
SERVER_STARTED_COUNTER = Counter(name="server_started_total",
                                 documentation="Total number of RPCs started on the server.",
                                 subsystem="rpc",
                                 registry=REGISTRY,
                                 labelnames=add_ex_label_names("system_name", "caller_service", "caller_method",
                                                               "callee_service", "callee_method"))

# Received requests this service finished handling.
SERVER_HANDLED_COUNTER = Counter(
    name="server_handled_total",
    documentation="Total number of RPCs completed on the server, regardless of success or failure.",
    subsystem="rpc",
    registry=REGISTRY,
    labelnames=add_ex_label_names("system_name", "caller_service", "caller_method", "callee_service", "callee_method",
                                  "code", "code_type"))

# Latency of handling received requests.
SERVER_HANDLED_HISTOGRAM = Histogram(name="server_handled_seconds",
                                     documentation="Histogram of response latency (seconds) of RPC"
                                     "that had been application-level handled by the server.",
                                     subsystem="rpc",
                                     registry=REGISTRY,
                                     buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 5),
                                     labelnames=add_ex_label_names("system_name", "caller_service", "caller_method",
                                                                   "callee_service", "callee_method"))

CodeTypeFunc = Callable[[str], CodeType]


def default_code_type_func(code: str) -> CodeType:
    """Classify ``""`` and ``"0"`` as success and every other code as exception."""
    if code in ["", "0"]:
        return CodeTypeSuccess
    return CodeTypeException


# Code-to-type mapping in use. Services may replace it with ``set_code_type_func``.
_DEFAULT_CODE_TYPE_FUNC = default_code_type_func


def get_code_type_func() -> CodeTypeFunc:
    """Return the code-to-type mapping currently in use."""
    return _DEFAULT_CODE_TYPE_FUNC


def set_code_type_func(func: CodeTypeFunc):
    """Replace the code-to-type mapping used by the client and server reporters."""
    global _DEFAULT_CODE_TYPE_FUNC
    _DEFAULT_CODE_TYPE_FUNC = func
