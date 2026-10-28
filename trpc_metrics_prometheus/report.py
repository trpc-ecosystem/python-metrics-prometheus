# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Plugin config loading, the metrics exporter, and push gateway reporting."""

import threading
import time

from prometheus_client import push_to_gateway
from prometheus_client.exposition import basic_auth_handler
from trpc_sdk.config import TrpcConfig
from trpc_sdk.config import TrpcConfigParser
from trpc_sdk.log import logger

from .config import PrometheusConfig
from .prometheus import init_metrics
from .registry import REGISTRY

GLOBAL_PROMETHEUS_CONFIG: PrometheusConfig = None  # type: ignore
_CONFIG_LOCK = threading.Lock()


def load_config() -> PrometheusConfig:
    """Load ``plugins.metrics.prometheus`` once and fill empty fields from the framework config.

    Filters built in a process that never starts ``MetricsPlugin``, such as
    a task process, reach this through ``get_prometheus_config``.

    Returns:
        The loaded plugin config.
    """
    global GLOBAL_PROMETHEUS_CONFIG
    if GLOBAL_PROMETHEUS_CONFIG is not None:
        return GLOBAL_PROMETHEUS_CONFIG
    with _CONFIG_LOCK:
        if GLOBAL_PROMETHEUS_CONFIG is None:
            prometheus_config = PrometheusConfig()
            TrpcConfigParser.populate_from_dict(TrpcConfig.plugins_config()["metrics"]["prometheus"],
                                                prometheus_config)
            fix_prometheus_config(prometheus_config)
            GLOBAL_PROMETHEUS_CONFIG = prometheus_config
    return GLOBAL_PROMETHEUS_CONFIG


def initialize():
    """Load the plugin config and start the exporter."""
    prometheus_config = load_config()
    init_metrics(prometheus_config.ip, prometheus_config.port, prometheus_config.path)


def fix_prometheus_config(prometheus_config: PrometheusConfig):
    """Fill fields left empty in the plugin config from the ``server`` and ``global`` sections."""
    server_config = TrpcConfig.server_config()
    global_config = TrpcConfig.global_config()

    prometheus_config.app = set_if_empty(prometheus_config.app, server_config.app)

    prometheus_config.server = set_if_empty(prometheus_config.server, server_config.server)

    prometheus_config.namespace = set_if_empty(prometheus_config.namespace, global_config.namespace)

    prometheus_config.env_name = set_if_empty(prometheus_config.env_name, global_config.env_name)

    prometheus_config.set_name = set_if_empty(prometheus_config.set_name, global_config.full_set_name)

    prometheus_config.container = set_if_empty(prometheus_config.container, global_config.container_name)

    prometheus_config.ip = set_if_empty(prometheus_config.ip, global_config.local_ip)


def set_if_empty(parameter, value):
    """Return ``value`` when ``parameter`` is empty, else ``parameter``."""
    if len(parameter) == 0:
        return value
    return parameter


def get_prometheus_config() -> PrometheusConfig:
    """Return the plugin config, loading it on first use."""
    return load_config()


def gateway_auth_handler(url, method, timeout, headers, data):
    """Push gateway handler that adds basic auth from the plugin config."""
    username = GLOBAL_PROMETHEUS_CONFIG.username
    password = GLOBAL_PROMETHEUS_CONFIG.password
    return basic_auth_handler(url, method, timeout, headers, data, username, password)


def interval_batch_push():
    """Push ``REGISTRY`` to the gateway every ``report_interval`` seconds, forever.

    Returns immediately when ``push_gateway_addr`` is empty.
    """
    if GLOBAL_PROMETHEUS_CONFIG.push_gateway_addr == "":
        return
    while True:
        try:
            if GLOBAL_PROMETHEUS_CONFIG.username != "" and GLOBAL_PROMETHEUS_CONFIG.password != "":
                push_to_gateway(GLOBAL_PROMETHEUS_CONFIG.push_gateway_addr,
                                job='interval_batch_push',
                                registry=REGISTRY,
                                handler=gateway_auth_handler)
            else:
                push_to_gateway(GLOBAL_PROMETHEUS_CONFIG.push_gateway_addr,
                                job='interval_batch_push',
                                registry=REGISTRY)
        except Exception as e:  # pylint: disable=broad-except
            logger.error(f'prometheus client push_to_gateway error: {e}')
        time.sleep(GLOBAL_PROMETHEUS_CONFIG.report_interval)
