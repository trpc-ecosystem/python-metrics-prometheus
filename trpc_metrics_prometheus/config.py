# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Config model of the ``plugins.metrics.prometheus`` section."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass
class PrometheusConfig:
    """Settings of the prometheus plugin, parsed by ``TrpcConfigParser.populate_from_dict``.

    Empty identity fields are filled later by ``fix_prometheus_config``
    from the framework ``server`` and ``global`` sections. Pushing is
    skipped when ``push_gateway_addr`` is empty.

    Attributes:
        report_interval: Seconds between push-gateway reports.
        push_gateway_addr: Push gateway address as ``host:port``. Empty
            disables pushing.
        username: Basic-auth username for the push gateway. Auth is used
            only when both ``username`` and ``password`` are set.
        password: Basic-auth password for the push gateway. Omitted from
            ``repr``.
        app: Application name. Empty falls back to ``server.app``.
        server: Server name. Empty falls back to ``server.server``.
        namespace: Physical environment. Empty falls back to
            ``global.namespace``.
        env_name: User environment. Empty falls back to ``global.env_name``.
        set_name: Set name. Empty falls back to ``global.full_set_name``.
        container: Container name. Empty falls back to
            ``global.container_name``.
        ip: Local address, used as the instance label and the exporter
            bind address. Empty falls back to ``global.local_ip``.
        port: HTTP exporter port. Defaults to 8080.
        path: HTTP exporter path. Defaults to ``/metrics``.
    """

    report_interval: int = 0
    push_gateway_addr: str = ""
    username: str = ""
    password: str = field(default="", repr=False)
    app: str = ""
    server: str = ""
    namespace: str = ""
    env_name: str = ""
    set_name: str = ""
    container: str = ""
    ip: str = ""
    port: int = 8080
    path: str = "/metrics"
