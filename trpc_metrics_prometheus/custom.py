# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Decorators that report user-defined counters, gauges, and histograms."""

import inspect
import threading
import time
from typing import Callable
from typing import Dict
from typing import Iterable

from prometheus_client import Counter
from prometheus_client import Gauge
from prometheus_client import Histogram

from .metrics import add_ex_label_names
from .metrics import add_ex_label_values
from .registry import REGISTRY


class _CustomMetricCache:
    """Process-wide cache of custom metrics, keyed by metric name.

    prometheus_client rejects registering the same name twice, so each
    decorator looks its metric up here and creates it only on first use.
    """

    counter_lock: threading.Lock = threading.Lock()
    counters: Dict[str, Counter] = {}

    gauge_lock: threading.Lock = threading.Lock()
    gauges: Dict[str, Gauge] = {}

    histogram_lock: threading.Lock = threading.Lock()
    histograms: Dict[str, Histogram] = {}

    @classmethod
    def get_counter(cls, name: str, desc: str, labels: Iterable[str]) -> Counter:
        """Return the counter named ``name``, creating it on first use."""
        with cls.counter_lock:
            c = cls.counters.get(name)
            if c is None:
                c = Counter(name=name,
                            documentation=desc,
                            subsystem="custom",
                            registry=REGISTRY,
                            labelnames=add_ex_label_names(*labels))
                cls.counters[name] = c
            return c

    @classmethod
    def get_gauge(cls, name: str, desc: str, labels: Iterable[str]) -> Gauge:
        """Return the gauge named ``name``, creating it on first use."""
        with cls.gauge_lock:
            g = cls.gauges.get(name)
            if g is None:
                g = Gauge(name=name,
                          documentation=desc,
                          subsystem="custom",
                          registry=REGISTRY,
                          labelnames=add_ex_label_names(*labels))
                cls.gauges[name] = g
            return g

    @classmethod
    def get_histogram(cls, name: str, desc: str, labels: Iterable[str]) -> Histogram:
        """Return the histogram named ``name``, creating it on first use."""
        with cls.histogram_lock:
            h = cls.histograms.get(name)
            if h is None:
                h = Histogram(name=name,
                              documentation=desc,
                              subsystem="custom",
                              registry=REGISTRY,
                              buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 5),
                              labelnames=add_ex_label_names(*labels))
                cls.histograms[name] = h
            return h


def custom_counter(name: str, desc: str, label_names: Iterable[str], label_values_func: Callable[..., Iterable[str]]):
    """Count calls to the decorated function.

    Args:
        name: Metric name. Two counters are created: ``{name}_started`` and
            ``{name}_finished``, incremented before and after the call.
        desc: Metric description.
        label_names: Label names of the metric.
        label_values_func: Called with the decorated function's arguments;
            returns the label values in ``label_names`` order.

    Returns:
        Decorator for a sync or async function.
    """

    def decorator(func):
        if inspect.iscoroutinefunction(func):

            async def wrapper(*args, **kwargs):
                c_start = _CustomMetricCache.get_counter(name + "_started", desc, label_names)
                c_finished = _CustomMetricCache.get_counter(name + '_finished', desc, label_names)
                label_values = label_values_func(*args, **kwargs)
                c_start.labels(*add_ex_label_values(*label_values)).inc()
                result = await func(*args, **kwargs)
                c_finished.labels(*add_ex_label_values(*label_values)).inc()
                return result

            return wrapper
        else:

            def wrapper(*args, **kwargs):
                c_start = _CustomMetricCache.get_counter(name + "_started", desc, label_names)
                c_finished = _CustomMetricCache.get_counter(name + '_finished', desc, label_names)
                label_values = label_values_func(*args, **kwargs)
                c_start.labels(*add_ex_label_values(*label_values)).inc()
                result = func(*args, **kwargs)
                c_finished.labels(*add_ex_label_values(*label_values)).inc()
                return result

            return wrapper

    return decorator


def custom_gauge(name: str, desc: str, label_names: Iterable[str], label_values_func: Callable[..., Iterable[str]]):
    """Track in-flight calls to the decorated function.

    The gauge is incremented before the call and decremented after it, so
    its value is the current concurrency.

    Args:
        name: Metric name, usually in progressive form.
        desc: Metric description.
        label_names: Label names of the metric.
        label_values_func: Called with the decorated function's arguments;
            returns the label values in ``label_names`` order.

    Returns:
        Decorator for a sync or async function.
    """

    def decorator(func):
        if inspect.iscoroutinefunction(func):

            async def wrapper(*args, **kwargs):
                g = _CustomMetricCache.get_gauge(name, desc, label_names)
                label_values = label_values_func(*args, **kwargs)
                g.labels(*add_ex_label_values(*label_values)).inc()
                result = await func(*args, **kwargs)
                g.labels(*add_ex_label_values(*label_values)).dec()
                return result

            return wrapper
        else:

            def wrapper(*args, **kwargs):
                g = _CustomMetricCache.get_gauge(name, desc, label_names)
                label_values = label_values_func(*args, **kwargs)
                g.labels(*add_ex_label_values(*label_values)).inc()
                result = func(*args, **kwargs)
                g.labels(*add_ex_label_values(*label_values)).dec()
                return result

            return wrapper

    return decorator


def custom_histogram(name: str, desc: str, label_names: Iterable[str], label_values_func: Callable[..., Iterable[str]]):
    """Observe the duration of calls to the decorated function.

    Args:
        name: Metric name, usually ending in ``_seconds``.
        desc: Metric description.
        label_names: Label names of the metric.
        label_values_func: Called with the decorated function's arguments;
            returns the label values in ``label_names`` order.

    Returns:
        Decorator for a sync or async function.
    """

    def decorator(func):
        if inspect.iscoroutinefunction(func):

            async def wrapper(*args, **kwargs):
                h = _CustomMetricCache.get_histogram(name, desc, label_names)
                label_values = label_values_func(*args, **kwargs)
                start_time = time.time()
                result = await func(*args, **kwargs)
                h.labels(*add_ex_label_values(*label_values)).observe(time.time() - start_time)
                return result

            return wrapper
        else:

            def wrapper(*args, **kwargs):
                h = _CustomMetricCache.get_histogram(name, desc, label_names)
                label_values = label_values_func(*args, **kwargs)
                start_time = time.time()
                result = func(*args, **kwargs)
                h.labels(*add_ex_label_values(*label_values)).observe(time.time() - start_time)
                return result

            return wrapper

    return decorator
