# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Module for Ethtool exceptions."""

import subprocess
from mfd_base_tool.exceptions import ToolNotAvailable


class EthtoolException(Exception):
    """Handle Ethtool exceptions."""


class EthtoolNotAvailable(ToolNotAvailable, EthtoolException):
    """Handle tool not available exception."""


class EthtoolExecutionError(EthtoolException, subprocess.CalledProcessError):
    """Handle Ethtool execution errors."""


class EthtoolParserException(Exception):
    """Handle Ethtool parser exceptions."""
