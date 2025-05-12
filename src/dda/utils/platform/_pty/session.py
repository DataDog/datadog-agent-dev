# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dda.utils.platform._pty.interface import PtySessionInterface

PtySession: type[PtySessionInterface]
if sys.__stdout__ is not None and not sys.__stdout__.isatty():
    from dda.utils.platform._pty.mock import PtySession
elif sys.platform == "win32":
    from dda.utils.platform._pty.windows import PtySession
else:
    from dda.utils.platform._pty.unix import PtySession

__all__ = ["PtySession"]
