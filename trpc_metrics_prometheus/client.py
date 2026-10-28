# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Client-side RPC reporter."""

import time

from .metrics import CLIENT_HANDLED_COUNTER
from .metrics import CLIENT_HANDLED_HISTOGRAM
from .metrics import CLIENT_STARTED_COUNTER
from .metrics import add_ex_label_values
from .metrics import get_code_type_func
from .utils import clean_rpc_method


class ClientReporter:
    """Reports one downstream RPC made by this service.

    Created for each outgoing request; records the request count, the
    completion count by code, and the latency.
    """

    def __init__(self,
                 system_name: str = "",
                 caller_service: str = "",
                 caller_method: str = "",
                 callee_service: str = "",
                 callee_method: str = "",
                 start_time: int = 0) -> None:
        """Store the identity of one downstream RPC and when it started.

        Args:
            system_name: Value of the ``system_name`` label.
            caller_service: Service that sent the request.
            caller_method: Method that sent the request.
            callee_service: Downstream service.
            callee_method: Downstream method.
            start_time: Unix time when the request started, used to measure latency.
        """
        self.system_name = system_name
        self.caller_service = caller_service
        self.caller_method = caller_method
        self.callee_service = callee_service
        self.callee_method = callee_method
        self.start_time = start_time

    def handled(self, code: str):
        """Record completion with ``code`` and the latency since ``start_time``."""
        code_type = get_code_type_func()(code)
        CLIENT_HANDLED_COUNTER.labels(
            *add_ex_label_values(self.system_name, self.caller_service, self.caller_method, self.callee_service,
                                 self.callee_method, code, str(code_type))).inc()
        CLIENT_HANDLED_HISTOGRAM.labels(
            *add_ex_label_values(self.system_name, self.caller_service, self.caller_method, self.callee_service,
                                 self.callee_method)).observe(time.time() - self.start_time)


def create_client_reporter(system_name: str, caller_service: str, caller_method: str, callee_service: str,
                        callee_method: str) -> ClientReporter:
    """Create a client reporter and count the request as started."""
    reporter = ClientReporter(
        system_name=system_name,
        caller_service=caller_service,
        caller_method=clean_rpc_method(caller_method),
        callee_service=callee_service,
        callee_method=clean_rpc_method(callee_method),
        start_time=int(time.time()),
    )
    CLIENT_STARTED_COUNTER.labels(
        *add_ex_label_values(reporter.system_name, reporter.caller_service, reporter.caller_method,
                             reporter.callee_service, reporter.callee_method)).inc()
    return reporter
