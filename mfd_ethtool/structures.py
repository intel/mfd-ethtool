# Copyright (C) 2025 Intel Corporation
# SPDX-License-Identifier: MIT
"""Structures for Ethtool module."""

from enum import Enum


class GetReceiveNetworkFlowClassification(Enum):
    """Structure for get receive network flow classification options."""

    N = "-n"
    U = "-u"
    ShowNFC = "--show-nfc"
    ShowNtuple = "--show-ntuple"


class SetReceiveNetworkFlowClassification(Enum):
    """Structure for set receive network flow classification options."""

    N = "-N"
    U = "-U"
    ConfigNFC = "--config-nfc"
    ConfigNtuple = "--config-ntuple"
