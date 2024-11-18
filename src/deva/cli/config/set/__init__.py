# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click

from deva.cli.base import dynamic_command

if TYPE_CHECKING:
    from deva.cli.application import Application


@dynamic_command(short_help="Set the value of config keys")
@click.argument("key")
@click.argument("value", required=False)
@click.pass_obj
def cmd(app: Application, key: str, value: str | None) -> None:
    """
    Set the value of config keys. If the value is omitted, you will
    be prompted, with the input hidden if it is sensitive.
    """
    import json
    from fnmatch import fnmatch

    import msgspec
    import tomlkit

    from deva.config.model import construct_model
    from deva.config.utils import SCRUBBED_GLOBS, create_toml_document, save_toml_document, scrub_config

    scrubbing = any(fnmatch(key, glob) for glob in SCRUBBED_GLOBS)
    if value is None:
        value = click.prompt("Value", hide_input=scrubbing)

    user_config = new_config = tomlkit.parse(app.config_file.read())

    data = [value]
    data.extend(reversed(key.split(".")))
    key = data.pop()
    value = data.pop()

    # Use a separate mapping to show only what has changed in the end
    branch_config_root: dict[str, Any] = {}
    branch_config = branch_config_root

    # Consider dots as keys
    while data:
        default_branch = {value: ""}
        branch_config[key] = default_branch
        branch_config = branch_config[key]

        new_value = new_config.get(key)
        if not hasattr(new_value, "get"):
            new_value = default_branch

        new_config[key] = new_value
        new_config = new_config[key]  # type: ignore[assignment]

        key = value
        value = data.pop()

    if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
        new_config[key] = int(value)
    elif value.startswith(("{", "[")):
        from ast import literal_eval

        new_config[key] = literal_eval(value)
    elif value.lower() == "true":
        new_config[key] = True
    elif value.lower() == "false":
        new_config[key] = False
    else:
        new_config[key] = value

    branch_config[key] = new_config[key]

    # Reconstruct the config without weird tomlkit objects that mirror built-in types
    fresh_config = json.loads(json.dumps(user_config))

    try:
        construct_model(fresh_config)
    except msgspec.ValidationError as e:
        app.display_error(str(e))
        app.abort()

    save_toml_document(user_config, app.config_file.path)
    if scrubbing:
        scrub_config(branch_config_root)

    rendered_changed = tomlkit.dumps(create_toml_document(branch_config_root)).strip()
    app.display_syntax(rendered_changed, "toml", background_color="default")
