# SPDX-FileCopyrightText: 2026-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from msgspec import Struct, field


class FeatureFlagsCIConfig(Struct, frozen=True, forbid_unknown_fields=True):
    """
    /// tab | :octicons-file-code-16: config.toml
    ```toml
    [feature-flags.ci]
    token-command = ["vault", "kv", "get", "-field=token", "kv/path/to/secret"]
    ```
    ///

    Command whose output is used as the feature flag client token in CI. A string is split with POSIX shell rules,
    except on Windows.
    """

    token_command: list[str] | str = field(name="token-command", default_factory=list)


class FeatureFlagsConfig(Struct, frozen=True):
    ci: FeatureFlagsCIConfig = field(default_factory=FeatureFlagsCIConfig)
