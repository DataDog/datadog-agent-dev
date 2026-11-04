# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import os


def running_in_bits_code() -> bool:
    """Select noninteractive Bits behavior; this marker never grants authorization."""
    return os.environ.get("DD_BITS_CODE") == "1"
