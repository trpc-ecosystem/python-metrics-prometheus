# Tencent is pleased to support the open source community by making tRPC-Metrics-Prometheus available.
#
# Copyright (C) 2026 Tencent. All rights reserved.
#
# tRPC-Metrics-Prometheus is licensed under Apache-2.0.
"""Install entry point for the trpc-metrics-prometheus package."""

import codecs
import os
import re

from setuptools import find_packages
from setuptools import setup


def _read_version():
    """Read ``__version__`` from the package version module.

    Returns:
        The semantic version string declared in ``version.py``.

    Raises:
        RuntimeError: The version assignment is missing.
    """
    regexp = re.compile(r"^__version__\W*=\W*'([\d.abrc]+)'")
    version_py = os.path.join(os.path.dirname(__file__), "trpc_metrics_prometheus", "version.py")
    with open(version_py, encoding="utf-8") as f:
        for line in f:
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
        raise RuntimeError(f"Cannot find version in {version_py}")


setup(name="trpc_metrics_prometheus",
      version=_read_version(),
      url="",
      project_urls={
          "Documentation": "",
          "Code": "",
          "Issue tracker": "",
      },
      maintainer="TRPC Python Group",
      description="prometheus plugin for trpc framework",
      long_description=codecs.open('README.md', encoding='UTF-8').read(),
      long_description_content_type="text/markdown",
      python_requires=">=3.8",
      install_requires=[
          "trpc-python ; sys_platform != 'win32'",
          "prometheus-client>=0.20.0",
      ],
      packages=find_packages(include=("trpc_metrics_prometheus", "trpc_metrics_prometheus.*")))
