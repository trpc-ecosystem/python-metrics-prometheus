# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Test utils"""

from types import SimpleNamespace

from trpc_sdk.exceptions import TrpcErrorCode
from trpc_sdk.exceptions import UnknownError

from trpc_metrics_prometheus.utils import clean_rpc_method
from trpc_metrics_prometheus.utils import default_get_code_func


def test_code_from_trpc_exception():
    """A tRPC error reports its numeric code"""
    err = UnknownError("boom")
    assert default_get_code_func(None, None, None, err) == str(int(TrpcErrorCode.TRPC_INVOKE_UNKNOWN_ERR))


def test_code_from_plain_exception():
    """An error without a code reports the unknown-error code"""
    assert default_get_code_func(None, None, None, ValueError("boom")) == str(
        int(TrpcErrorCode.TRPC_INVOKE_UNKNOWN_ERR))


def test_code_from_exception_with_str_code():
    """A non-integer error code is reported as-is"""
    err = ValueError("boom")
    err.code = "E1"
    assert default_get_code_func(None, None, None, err) == "E1"


def test_code_from_response_fields():
    """Response fields are tried in order: retcode, ret_code, code"""
    assert default_get_code_func(None, None, SimpleNamespace(retcode=1, ret_code=2, code=3), None) == "1"
    assert default_get_code_func(None, None, SimpleNamespace(ret_code=2, code=3), None) == "2"
    assert default_get_code_func(None, None, SimpleNamespace(code=3), None) == "3"


def test_code_default():
    """No error and no code field reports 0"""
    assert default_get_code_func(None, None, object(), None) == "0"
    assert default_get_code_func(None, None, None, None) == "0"


def test_clean_rpc_method():
    """Empty method names become unknown"""
    assert clean_rpc_method("") == "unknown"
    assert clean_rpc_method("/a/b") == "/a/b"
