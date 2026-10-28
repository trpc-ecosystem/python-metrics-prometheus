# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Test metrics plugin, filters, and exporter"""

import multiprocessing
import socket
import threading
import urllib.error
import urllib.request
from types import SimpleNamespace
from unittest import mock

import pytest
from trpc_sdk.abc import PluginType
from trpc_sdk.config import TrpcConfigParser
from trpc_sdk.exceptions import UnknownError
from trpc_sdk.plugin import DEFAULT_PLUGIN_MANAGER
from trpc_sdk.plugin import init_task_plugins
from trpc_sdk.plugin import init_worker_plugins

from trpc_metrics_prometheus import REGISTRY
from trpc_metrics_prometheus import MetricsClientFilter
from trpc_metrics_prometheus import MetricsPlugin
from trpc_metrics_prometheus import MetricsServerFilter
from trpc_metrics_prometheus import init_metrics
from trpc_metrics_prometheus import report
from trpc_metrics_prometheus.constants import PLUGIN_NAME
from trpc_metrics_prometheus.constants import SYSTEM_NAME
from .utils import init_plugin_config
from .utils import labels_of

RPC_LABELS = ("system_name", "caller_service", "caller_method", "callee_service", "callee_method")


def setup_module():
    """Load the plugin config before the filter tests run."""
    init_plugin_config()


def fake_message(callee_method: str):
    """Build a message with fixed caller fields and the given callee method.

    Args:
        callee_method: Method name stored on the message.

    Returns:
        A namespace with caller and callee service and method names.
    """
    return SimpleNamespace(caller_service_name="trpc.caller.svc",
                           caller_method="/caller/m",
                           callee_service_name="trpc.callee.svc",
                           callee_method=callee_method)


def rpc_values(callee_method: str):
    """Return the RPC label values used to look up a sample.

    Args:
        callee_method: Method name included in the label values.

    Returns:
        ``system_name``, caller service, caller method, callee service, and
        ``callee_method``, in label order.
    """
    return (SYSTEM_NAME, "trpc.caller.svc", "/caller/m", "trpc.callee.svc", callee_method)


def sample(name: str, callee_method: str, *extra: str) -> float:
    """Read one sample from ``REGISTRY``, or 0 when it is absent.

    Args:
        name: Metric name.
        callee_method: Method name used in the RPC labels.
        *extra: Optional ``code`` and ``code_type`` label values. When omitted,
            the lookup uses only the RPC labels.

    Returns:
        The sample value, or 0.
    """
    names = RPC_LABELS + (("code", "code_type") if extra else ())
    return REGISTRY.get_sample_value(name, labels_of(names, rpc_values(callee_method) + extra)) or 0


@pytest.mark.asyncio
@pytest.mark.parametrize("filter_cls, prefix", [(MetricsServerFilter, "rpc_server"),
                                                (MetricsClientFilter, "rpc_client")])
async def test_filter_success(filter_cls, prefix):
    """A successful call counts started/handled with code 0"""
    method = f"/ok/{prefix}"
    with mock.patch("trpc_metrics_prometheus.filter.get_message", return_value=fake_message(method)):
        rsp, err = await filter_cls().run(object(), None, mock.AsyncMock(return_value=({"code": 0}, None)))

    assert rsp == {"code": 0} and err is None
    assert sample(f"{prefix}_started_total", method) == 1
    assert sample(f"{prefix}_handled_total", method, "0", "success") == 1
    assert sample(f"{prefix}_handled_seconds_count", method) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("filter_cls, prefix", [(MetricsServerFilter, "rpc_server"),
                                                (MetricsClientFilter, "rpc_client")])
async def test_filter_error(filter_cls, prefix):
    """A failed call reports the error code as exception"""
    method = f"/err/{prefix}"
    err = UnknownError("boom")
    with mock.patch("trpc_metrics_prometheus.filter.get_message", return_value=fake_message(method)):
        _, got = await filter_cls().run(object(), None, mock.AsyncMock(return_value=(None, err)))

    assert got is err
    assert sample(f"{prefix}_handled_total", method, str(int(err.code)), "exception") == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("filter_cls", [MetricsServerFilter, MetricsClientFilter])
async def test_filter_stream_passthrough(filter_cls):
    """Streaming results are yielded unchanged"""

    async def next_handle():
        for i in range(3):
            yield i

    assert [r async for r in filter_cls().run_stream(object(), None, next_handle)] == [0, 1, 2]


def test_plugin_start():
    """start() initializes from config and runs the push loop in a thread"""
    pushed = threading.Event()
    with mock.patch("trpc_metrics_prometheus.filter.initialize") as initialize, \
            mock.patch("trpc_metrics_prometheus.filter.interval_batch_push", side_effect=pushed.set):
        MetricsPlugin().start()
        assert pushed.wait(1)
    initialize.assert_called_once_with()


def _free_port() -> int:
    """Return a local TCP port that is free at the moment it is chosen.

    Returns:
        An unused port on ``127.0.0.1``.
    """
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_init_metrics_serves_registry():
    """The exporter serves REGISTRY on the configured path and 404 elsewhere"""
    port = _free_port()
    init_metrics("127.0.0.1", port, "/metrics")

    with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=5) as rsp:
        assert b"rpc_server_started_total" in rsp.read()
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/other", timeout=5)
    assert exc.value.code == 404


def test_init_metrics_port_in_use():
    """A bind failure is logged instead of raised"""
    with mock.patch("trpc_metrics_prometheus.prometheus.HTTPServer", side_effect=OSError("in use")), \
            mock.patch("trpc_metrics_prometheus.prometheus.logger") as logger:
        init_metrics("127.0.0.1", 1, "/metrics")
    logger.warning.assert_called_once()


def test_forked_workers_share_one_exporter():
    """Forked workers (rpc tasks, multi-process merge workers) bind one exporter between them; the rest only warn"""
    ctx = multiprocessing.get_context("fork")
    port = _free_port()
    bound = ctx.Value('i', 0)
    barrier = ctx.Barrier(3)

    def worker():
        with mock.patch("trpc_metrics_prometheus.prometheus.logger") as logger:
            init_metrics("127.0.0.1", port, "/metrics")
        if logger.info.called:
            with bound.get_lock():
                bound.value += 1
        # Stay alive until every worker has tried, so the winner keeps the port.
        barrier.wait(10)

    procs = [ctx.Process(target=worker) for _ in range(3)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(15)

    assert [p.exitcode for p in procs] == [0, 0, 0]
    assert bound.value == 1


@pytest.mark.asyncio
async def test_filter_loads_config_on_first_use():
    """A filter built without MetricsPlugin.start(), as in a task process, loads the config itself"""
    method = "/lazy/client"
    with mock.patch.object(report, "GLOBAL_PROMETHEUS_CONFIG", None), \
            mock.patch("trpc_metrics_prometheus.filter.get_message", return_value=fake_message(method)):
        await MetricsClientFilter().run(object(), None, mock.AsyncMock(return_value=({}, None)))
        assert report.GLOBAL_PROMETHEUS_CONFIG.app == "ExampleApp"
        assert sample("rpc_client_started_total", method) == 1


def test_load_config_once_across_threads():
    """Concurrent first reads load the config once and share it"""
    real_populate = TrpcConfigParser.populate_from_dict
    start = threading.Barrier(8)
    results = []

    def read():
        start.wait(5)
        results.append(report.get_prometheus_config())

    with mock.patch.object(report, "GLOBAL_PROMETHEUS_CONFIG", None), \
            mock.patch.object(report.TrpcConfigParser, "populate_from_dict", side_effect=real_populate) as populate:
        threads = [threading.Thread(target=read) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(5)

    populate.assert_called_once()
    assert len(results) == 8 and all(r is results[0] for r in results)


def _metrics_spec():
    """Return the registered spec of the metrics plugin."""
    return DEFAULT_PLUGIN_MANAGER.get_plugin_spec(PluginType.METRICS, PLUGIN_NAME)


@mock.patch("trpc_metrics_prometheus.filter.interval_batch_push")
@mock.patch("trpc_metrics_prometheus.filter.initialize")
def test_task_plugins_skip_exporter(initialize, _push):
    """The TASK pass (separate I/O process, task processes) does not start the exporter"""
    with mock.patch.object(DEFAULT_PLUGIN_MANAGER, "all_plugin_specs", return_value=[_metrics_spec()]):
        init_task_plugins()
    initialize.assert_not_called()


@mock.patch("trpc_metrics_prometheus.filter.interval_batch_push")
@mock.patch("trpc_metrics_prometheus.filter.initialize")
def test_worker_plugins_start_exporter(initialize, _push):
    """The WORKER pass (merge, rpc task, multi-process merge) starts the exporter"""
    with mock.patch.object(DEFAULT_PLUGIN_MANAGER, "all_plugin_specs", return_value=[_metrics_spec()]):
        init_worker_plugins()
    initialize.assert_called_once_with()
