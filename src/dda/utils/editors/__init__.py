# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from dda.utils.editors.interface import EditorInterface


def get_editor(env_type: str) -> type[EditorInterface]:
    getter = __EDITORS.get(env_type)
    if getter is None:  # no cov
        message = f"Unknown editor `{env_type}`, must be one of: {', '.join(AVAILABLE_EDITORS)}"
        raise ValueError(message)

    return getter()


def __get_vscode() -> type[EditorInterface]:
    from dda.utils.editors.types.vscode import VSCodeEditorInterface

    return VSCodeEditorInterface


def __get_cursor() -> type[EditorInterface]:
    from dda.utils.editors.types.cursor import CursorEditorInterface

    return CursorEditorInterface


__EDITORS: dict[str, Callable[[], type[EditorInterface]]] = {
    "vscode": __get_vscode,
    "cursor": __get_cursor,
}

AVAILABLE_EDITORS: list[str] = sorted(__EDITORS)
DEFAULT_EDITOR = "vscode"
