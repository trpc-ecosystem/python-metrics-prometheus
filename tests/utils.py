# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Shared helpers for the prometheus metrics tests."""

import os
from typing import Dict
from typing import Iterable
from unittest import mock

from trpc_sdk.config import TrpcConfig

from trpc_metrics_prometheus import report
from trpc_metrics_prometheus.metrics import add_ex_label_names
from trpc_metrics_prometheus.metrics import add_ex_label_values

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "trpc_python.yaml")


def init_plugin_config():
    """Load the test framework config and the plugin config without binding the exporter port."""
    TrpcConfig.load(CONFIG_PATH)
    with mock.patch("trpc_metrics_prometheus.report.init_metrics"):
        report.initialize()


def labels_of(names: Iterable[str], values: Iterable[str]) -> Dict[str, str]:
    """Return the full label dict, shared labels included, for a sample lookup."""
    return dict(zip(add_ex_label_names(*names), add_ex_label_values(*values)))
