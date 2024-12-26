# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, *_args: Any, **_kwargs: Any) -> None:
        import json
        import os

        expected_metadata = {
            "dependencies": self.metadata.core.dependencies,
            "features": self.metadata.core.optional_dependencies,
        }
        expected_content = f"{json.dumps(expected_metadata, indent=4)}\n"
        metadata_file = os.path.join(self.root, "src", "deva", "metadata.json")

        if os.environ.get("DEVA_BUILD_METADATA_CHECK") in {"1", "true"}:
            if not os.path.isfile(metadata_file):
                message = f"Metadata file not found: {metadata_file}"
                raise FileNotFoundError(message)

            with open(metadata_file, encoding="utf-8") as f:
                actual_content = f.read()

            if actual_content != expected_content:
                message = f"Metadata file content mismatch, a rebuild is required: {metadata_file}"
                raise ValueError(message)

        with open(metadata_file, "w", encoding="utf-8") as f:
            f.write(expected_content)
