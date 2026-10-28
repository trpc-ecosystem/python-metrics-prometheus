# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Test custom metric decorators"""

from typing import Iterable

import pytest

from trpc_metrics_prometheus import REGISTRY
from trpc_metrics_prometheus import custom_counter
from trpc_metrics_prometheus import custom_gauge
from trpc_metrics_prometheus import custom_histogram
from trpc_metrics_prometheus.custom import _CustomMetricCache
from .utils import init_plugin_config
from .utils import labels_of

LABEL_NAMES = ("dim1", "dim2")


def setup_module():
    """Load the plugin config before the custom-metric tests run."""
    init_plugin_config()


def get_label_values(ctx, req) -> Iterable[str]:
    """Pick the label values from the request."""
    return (str(req.get('dim1')), str(req.get('dim2')))


@custom_counter('counter1', 'customer counter1', LABEL_NAMES, get_label_values)
@custom_gauge('gauge1', 'customer gauge1', LABEL_NAMES, get_label_values)
@custom_histogram('target_func_seconds', 'customer histogram', LABEL_NAMES, get_label_values)
def target_func(ctx, req):
    """Return a successful response so the sync decorators can record a call.

    Args:
        ctx: Request context. Unused.
        req: Request carrying the label values.

    Returns:
        A mapping with code 0.
    """
    return {'code': 0}


@custom_counter('async_counter1', 'customer async counter1', LABEL_NAMES, get_label_values)
@custom_gauge('async_gauge1', 'customer async gauge1', LABEL_NAMES, get_label_values)
@custom_histogram('async_target_func_seconds', 'customer async histogram', LABEL_NAMES, get_label_values)
async def async_target_func(ctx, req):
    """Return a successful response so the async decorators can record a call.

    Args:
        ctx: Request context. Unused.
        req: Request carrying the label values.

    Returns:
        A mapping with code 0.
    """
    return {'code': 0}


def test_custom():
    """Sync decorators count, track concurrency, and observe duration"""
    req = {'dim1': 'v1', 'dim2': 'v2'}
    for _ in range(3):
        assert target_func({}, req) == {'code': 0}

    labels = labels_of(LABEL_NAMES, ('v1', 'v2'))
    assert REGISTRY.get_sample_value('custom_counter1_started_total', labels) == 3
    assert REGISTRY.get_sample_value('custom_counter1_finished_total', labels) == 3
    assert REGISTRY.get_sample_value('custom_gauge1', labels) == 0
    assert REGISTRY.get_sample_value('custom_target_func_seconds_count', labels) == 3


@pytest.mark.asyncio
async def test_custom_async():
    """Async decorators count, track concurrency, and observe duration"""
    req = {'dim1': 'a1', 'dim2': 'a2'}
    assert await async_target_func({}, req) == {'code': 0}

    labels = labels_of(LABEL_NAMES, ('a1', 'a2'))
    assert REGISTRY.get_sample_value('custom_async_counter1_started_total', labels) == 1
    assert REGISTRY.get_sample_value('custom_async_counter1_finished_total', labels) == 1
    assert REGISTRY.get_sample_value('custom_async_gauge1', labels) == 0
    assert REGISTRY.get_sample_value('custom_async_target_func_seconds_count', labels) == 1


def test_cache_returns_same_metric():
    """A name is registered once and reused afterwards"""
    assert _CustomMetricCache.get_counter('cached', 'd', LABEL_NAMES) is _CustomMetricCache.get_counter(
        'cached', 'd', LABEL_NAMES)
    assert _CustomMetricCache.get_gauge('cached_g', 'd', LABEL_NAMES) is _CustomMetricCache.get_gauge(
        'cached_g', 'd', LABEL_NAMES)
    assert _CustomMetricCache.get_histogram('cached_h', 'd', LABEL_NAMES) is _CustomMetricCache.get_histogram(
        'cached_h', 'd', LABEL_NAMES)
