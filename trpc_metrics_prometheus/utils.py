# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Helpers shared by the RPC filters and reporters."""

from typing import Any
from typing import Callable
from typing import Optional

from trpc_sdk.abc import TrpcContext
from trpc_sdk.exceptions import TrpcErrorCode

# Maps ``(ctx, req, rsp, err)`` to the value of the ``code`` label.
GetCodeFunc = Callable[[TrpcContext, Any, Any, Optional[Exception]], str]


def _code_to_str(code: Any) -> str:
    """Render a code as its number so IntEnum members do not print as ``Enum.NAME`` before 3.11."""
    if isinstance(code, int):
        return str(int(code))
    return str(code)


def default_get_code_func(ctx: TrpcContext, req: Any, rsp: Any, err: Optional[Exception]) -> str:
    """Default mapping from an RPC result to the ``code`` label.

    Services whose responses carry the code in another field can replace
    ``trpc_metrics_prometheus.filter.DEFAULT_GET_CODE_FUNC``.

    Args:
        ctx: Request context.
        req: Request object.
        rsp: Response object, or None when the call failed.
        err: Error returned by the filter chain, if any.

    Returns:
        ``err.code`` when there is an error (``TRPC_INVOKE_UNKNOWN_ERR`` if it
        has none), else the first of ``rsp.retcode``, ``rsp.ret_code``,
        ``rsp.code`` that exists, else ``"0"``.
    """
    if err is not None:
        return _code_to_str(getattr(err, "code", TrpcErrorCode.TRPC_INVOKE_UNKNOWN_ERR))
    for attr in ("retcode", "ret_code", "code"):
        try:
            return str(getattr(rsp, attr))
        except AttributeError:
            pass
    return "0"


def clean_rpc_method(method: str) -> str:
    """Return ``"unknown"`` for an empty method name so the label is never blank."""
    if method == "":
        return "unknown"
    return method
