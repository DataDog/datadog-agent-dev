# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from dda.utils.editors.interface import EditorInterface


class VSCodeEditorInterface(EditorInterface):
    def open_via_ssh(self, *, server: str, port: int, path: str) -> None:
        self.app.subprocess.run(["code", "--remote", f"ssh-remote+root@{server}:{port}", path])
