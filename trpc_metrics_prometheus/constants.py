# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Constants for the prometheus metrics plugin.

Plugin name, shared label keys, the RPC system name, and response code
types live here so filters, reporters, and custom metrics share one definition.
"""

# Name used when this package registers its metrics plugin and filters.
PLUGIN_NAME = "prometheus"

# Label keys shared by every metric this plugin exports
KEY_ENV = "env"
KEY_APP = "app"
KEY_SERVER = "server"
KEY_NAMESPACE = "namespace"
KEY_ENV_NAME = "env_name"
KEY_SET_NAME = "set_name"
KEY_CONTAINER_NAME = "container"
KEY_INSTANCE = "instance"
KEY_PID = "pid"

# Value of the ``system_name`` label on RPC metrics.
SYSTEM_NAME = "trpc"

# Classification of a response code, used as the ``code_type`` label.
CodeType = str
CodeTypeSuccess: CodeType = "success"
CodeTypeException: CodeType = "exception"
CodeTypeTimeout: CodeType = "timeout"
