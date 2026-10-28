# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Example client that calls Greeter.SayHello and prints the exported server metrics.

Start ``trpc_main.py`` first, then run this script. It sends ``--count``
requests to ``127.0.0.1:8000`` and reads ``rpc_server_started_total`` from
the exporter at ``--metrics-url``.
"""

import argparse
import os
import sys
import urllib.request

from trpc_sdk.abc import TrpcContext
from trpc_sdk.client import Options
from trpc_sdk.serialization import SerializationType

# add the stub to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "stub")))  # noqa

from trpc_trpc_python_group_helloworld import pb
from trpc_trpc_python_group_helloworld import rpc


# pylint: disable=invalid-name
def say_hello(msg: str) -> str:
    """Call Greeter.SayHello once.

    Args:
        msg: Message sent in the request.

    Returns:
        The ``msg`` field of the reply.
    """
    proxy = rpc.GreeterClientProxyImpl()
    req = pb.HelloRequest()
    req.msg = msg
    options = (Options().set_target('ip://127.0.0.1:8000').set_protocol('trpc').set_serialization_type(
        SerializationType.PB).set_network('tcp').set_timeout(3000))
    return proxy.SayHello(TrpcContext(), req, options).msg


def server_started_lines(metrics_url: str):
    """Return the ``rpc_server_started_total`` samples served by the exporter.

    Args:
        metrics_url: Exporter URL, for example ``http://127.0.0.1:8080/metrics``.

    Returns:
        The matching exposition lines.
    """
    with urllib.request.urlopen(metrics_url, timeout=5) as rsp:
        body = rsp.read().decode()
    return [line for line in body.splitlines() if line.startswith("rpc_server_started_total{")]


def main():
    """Send the requests, then print the server-side counters."""
    parser = argparse.ArgumentParser(description="Call Greeter.SayHello and read the prometheus exporter")
    parser.add_argument("--count", "-n", type=int, default=20, help="number of SayHello calls")
    parser.add_argument("--metrics-url", default="http://127.0.0.1:8080/metrics", help="exporter URL")
    args = parser.parse_args()

    for i in range(args.count):
        reply = say_hello(f"hello {i}")
        assert reply == f"hello: hello {i}", reply
    print(f"{args.count} SayHello calls succeeded")

    for line in server_started_lines(args.metrics_url):
        print(line)


if __name__ == "__main__":
    main()
