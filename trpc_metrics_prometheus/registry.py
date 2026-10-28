# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Collector registry shared by every metric this plugin creates.

The exporter and the push gateway both read from ``REGISTRY``, so metrics
registered elsewhere in the process (e.g. the prometheus_client default
registry) are not exported by this plugin.
"""

from prometheus_client import CollectorRegistry

REGISTRY = CollectorRegistry()
