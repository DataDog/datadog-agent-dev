# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from dda.build.metadata.digests import ArtifactDigest, DigestType
from dda.cli.base import dynamic_command, pass_app
from dda.utils.fs import Path

if TYPE_CHECKING:
    from dda.cli.application import Application

DEFAULT_OUTPUT_PLACEHOLDER = Path("./bin/agent/canonical_filename")


@dynamic_command(short_help="Build the `core-agent` binary.")
@click.option(
    "--output",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False, exists=False, writable=True),
    default=DEFAULT_OUTPUT_PLACEHOLDER,
    help="""
The path on which to create the binary.
Defaults to bin/agent/canonical_filename - the canonical filename of the built artifact.
This filename contains some metadata about the built artifact, e.g. commit hash, build timestamp, etc.
    """,
)
@pass_app
def cmd(app: Application, output: Path) -> None:
    import shutil

    from dda.build.artifacts.binaries.core_agent import CoreAgent
    from dda.utils.fs import temp_file

    artifact = CoreAgent()
    app.display_waiting("Building the `core-agent` binary...")
    with temp_file() as tf:
        artifact.build(app, output=tf)
        digest = ArtifactDigest(value=tf.hexdigest(), type=DigestType.FILE_SHA256)

        metadata = artifact.compute_metadata(app, digest)

        # Special case: if output is the default value, use the canonical filename from the metadata
        if output == DEFAULT_OUTPUT_PLACEHOLDER:
            output = Path("./bin/") / metadata.get_canonical_filename()

        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(tf, output)
    metadata.to_file(output.with_suffix(".json"))
