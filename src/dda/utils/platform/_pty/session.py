# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys

if sys.platform == "win32":
    from dda.utils.platform._pty.windows import PtySession
else:
    from dda.utils.platform._pty.unix import PtySession

__all__ = ["PtySession"]
