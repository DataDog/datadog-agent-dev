# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from dda.build.artifacts.binaries.base import BinaryArtifact
from dda.build.languages.go import GoArtifact

if TYPE_CHECKING:
    from dda.cli.application import Application


class CoreAgent(BinaryArtifact, GoArtifact):
    """
    Build artifact for the `core-agent` binary.
    """

    @override
    def get_build_tags(self) -> set[str]:
        # TODO: Implement a properly dynamic function, matching the old invoke task
        return {
            "ec2",
            "python",
            "kubeapiserver",
            "oracle",
            "etcd",
            "jmx",
            "grpcnotrace",
            "consul",
            "systemprobechecks",
            "ncm",
            "otlp",
            "zstd",
            "orchestrator",
            "zk",
            "datadog.no_waf",
            "trivy_no_javadb",
            "zlib",
            "bundle_agent",
            "fargateprocess",
            "kubelet",
            "cel",
        }

    @override
    def get_gcflags(self) -> list[str]:
        return []

    @override
    def get_ldflags(self) -> list[str]:
        # TODO: Implement a properly dynamic function, matching the old invoke task
        return [
            "-X",
            "github.com/DataDog/datadog-agent/pkg/version.Commit=e927e2bc6e",
            "-X",
            "github.com/DataDog/datadog-agent/pkg/version.AgentVersion=7.74.0-devel+git.96.e927e2b",
            "-X",
            "github.com/DataDog/datadog-agent/pkg/version.AgentPayloadVersion=v5.0.174",
            "-X",
            "github.com/DataDog/datadog-agent/pkg/version.AgentPackageVersion=7.74.0-devel+git.96.e927e2b",
            "-r",
            "/Users/pierrelouis.veyrenc/go/src/github.com/DataDog/datadog-agent/dev/lib",
            "'-extldflags=-Wl,-bind_at_load,-no_warn_duplicate_libraries'",
        ]

    @override
    def get_build_env(self) -> dict[str, str]:
        # TODO: Implement a properly dynamic function, matching the old invoke task
        return {
            # TODO: Move GOPATH a GOCACHE to a configurable thing probably ? Probably also set them in the general go context
            "GO111MODULE": "on",
            "CGO_LDFLAGS_ALLOW": "-Wl,--wrap=.*",
            "DYLD_LIBRARY_PATH": ":/Users/pierrelouis.veyrenc/go/src/github.com/DataDog/datadog-agent/dev/lib",
            "LD_LIBRARY_PATH": ":/Users/pierrelouis.veyrenc/go/src/github.com/DataDog/datadog-agent/dev/lib",
            "CGO_LDFLAGS": " -L/Users/pierrelouis.veyrenc/go/src/github.com/DataDog/datadog-agent/dev/lib",
            "CGO_CFLAGS": " -Werror -Wno-deprecated-declarations -I/Users/pierrelouis.veyrenc/go/src/github.com/DataDog/datadog-agent/dev/include",
            "CGO_ENABLED": "1",
            "PATH": "/Users/pierrelouis.veyrenc/go/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        }

    @property
    @override
    def name(self) -> str:
        return "core-agent"

    @override
    def build(self, app: Application, *args: Any, **kwargs: Any) -> None:
        from dda.utils.fs import Path

        # TODO: Build rtloader first if needed
        # TODO: Make this build in a devenv ? Or at least add a flag
        app.tools.go.build(
            "github.com/DataDog/datadog-agent/cmd/agent",
            output=Path("./bin/agent"),
            build_tags=self.get_build_tags(),
            gcflags=self.get_gcflags(),
            ldflags=self.get_ldflags(),
            env_vars=self.get_build_env(),
        )
