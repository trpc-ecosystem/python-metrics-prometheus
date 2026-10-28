# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""HTTP exporter that serves ``REGISTRY`` for Prometheus to scrape."""

import threading
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer

from prometheus_client import exposition
from trpc_sdk.log import logger

from .registry import REGISTRY


def init_metrics(ip: str, port: int, path: str) -> None:
    """Serve ``REGISTRY`` at ``http://{ip}:{port}{path}`` from a daemon thread.

    If the port is already bound, e.g. by another process of the same
    service, a warning is logged and this process exports nothing.

    Args:
        ip: Address to bind.
        port: Port to bind.
        path: URL path that returns the metrics; any other path returns 404.
    """

    class MetricsHandler(BaseHTTPRequestHandler):

        def do_GET(self):
            if self.path == path:
                self.send_response(200)
                self.send_header('Content-Type', exposition.CONTENT_TYPE_LATEST)
                self.end_headers()
                self.wfile.write(exposition.generate_latest(registry=REGISTRY))
            else:
                self.send_response(404)
                self.end_headers()

    addr = f"{ip}:{port}"
    try:
        server = HTTPServer((ip, port), MetricsHandler)
    except OSError as e:
        logger.warning(f"prometheus exporter not started, cannot bind {addr}: {e}")
        return

    logger.info(f"prometheus exporter running at {addr}, metrics path {path}")

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
