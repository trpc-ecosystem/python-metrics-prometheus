# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Example server that registers Greeter and the prometheus metrics plugin.

Importing ``trpc_metrics_prometheus`` registers the metrics plugin and
filters. The process then loads a config file and serves Greeter.
"""

import os
import sys
import argparse
from typing import List

from trpc_sdk.log import logger
from trpc_sdk.server import create_server

# add the stub to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "stub")))  # noqa
sys.path.append(os.path.abspath(os.path.dirname(__file__)))  # noqa

# import sdk and plugins

# DO NOT remove the plugin below!
import trpc_metrics_prometheus as _

# Import the generated RPC package.
from trpc_trpc_python_group_helloworld import rpc
# Import the service implementation.
from greeter import GreeterServicer

DEFAULT_CONF_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "trpc_python.yaml"))


def parse_args(argv: List[str]):
    """Resolve the server config path from the command line.

    Args:
        argv: Full argument vector, including the script name at index 0.

    Returns:
        Path of a config file that exists. Falls back to the example config
        when the requested path is missing.
    """
    parser = argparse.ArgumentParser(description='TRPC Python Framework Server')
    # define config file argument
    parser.add_argument('--conf',
                        '-c',
                        default=DEFAULT_CONF_PATH,
                        help='start server with conf, for example: `python3 trpc_main.py  --conf=trpc_python.yaml`')
    try:
        args = parser.parse_args(argv[1:])  # Skip the script name
        if os.path.exists(args.conf):
            print(f"conf_path: {args.conf}")
            return args.conf
        print(f"conf_path: {args.conf} not exists")
        if os.path.exists(DEFAULT_CONF_PATH):
            print(f"use default conf path: {DEFAULT_CONF_PATH}")
            return DEFAULT_CONF_PATH
        print(f"default conf path: {DEFAULT_CONF_PATH} not exists, please check the path")
        sys.exit(1)
    except SystemExit:
        # argparse will call sys.exit() when --help is used or invalid args
        sys.exit(1)


def serve(conf_path: str):
    """Create the server, register Greeter, and block in ``serve``.

    Args:
        conf_path: Path of the tRPC config file.
    """

    # Build the server from the config file.
    server = create_server(conf_path)

    rpc.register_GreeterServicer_server(server, GreeterServicer(), fix_rpc_name=True)

    server.serve()


def main():
    """Parse arguments and start the server."""

    # Resolve the config path from the command line.
    conf_path = parse_args(sys.argv)
    logger.info("load config %s", conf_path)

    # Start the server.
    serve(conf_path)


if __name__ == '__main__':
    sys.exit(main())
