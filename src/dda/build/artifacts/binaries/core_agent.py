# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, Any, override

from dda.build.artifacts.binaries.base import BinaryArtifact
from dda.build.languages.go import GoArtifact

if TYPE_CHECKING:
    from dda.cli.application import Application
    from dda.utils.fs import Path


@cache
def get_repo_root(app: Application) -> Path:
    return app.tools.git.get_repo_root()


class CoreAgent(BinaryArtifact, GoArtifact):
    """
    Build artifact for the `core-agent` binary.
    """

    @override
    def get_build_tags(self, *args: Any, **kwargs: Any) -> set[str]:
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
    def get_gcflags(self, *args: Any, **kwargs: Any) -> list[str]:
        return []

    @override
    def get_ldflags(self, app: Application, *args: Any, **kwargs: Any) -> list[str]:
        from dda.build.versioning import parse_describe_result

        repo_root = get_repo_root(app)
        with repo_root.as_cwd():
            commit = app.tools.git.get_commit().sha1
            agent_version = parse_describe_result(app.tools.git.capture(["describe", "--tags"]).strip())

        return [
            "-X",
            f"github.com/DataDog/datadog-agent/pkg/version.Commit={commit[:10]}",
            "-X",
            f"github.com/DataDog/datadog-agent/pkg/version.AgentVersion={agent_version}",
            "-X",
            # TODO: Make this dynamic
            "github.com/DataDog/datadog-agent/pkg/version.AgentPayloadVersion=v5.0.174",
            "-X",
            f"github.com/DataDog/datadog-agent/pkg/version.AgentPackageVersion={agent_version}",
            "-r",
            f"{repo_root}/dev/lib",
            "'-extldflags=-Wl,-bind_at_load,-no_warn_duplicate_libraries'",
        ]

    @override
    def get_build_env(self, app: Application, *args: Any, **kwargs: Any) -> dict[str, str]:
        # TODO: Implement a properly dynamic function, matching the old invoke task
        repo_root = get_repo_root(app)
        return {
            "GO111MODULE": "on",
            "CGO_LDFLAGS_ALLOW": "-Wl,--wrap=.*",
            "DYLD_LIBRARY_PATH": f"{repo_root}/dev/lib",
            "LD_LIBRARY_PATH": f"{repo_root}/dev/lib",
            "CGO_LDFLAGS": f" -L{repo_root}/dev/lib",
            "CGO_CFLAGS": f" -Werror -Wno-deprecated-declarations -I{repo_root}/dev/include",
            "CGO_ENABLED": "1",
            "PATH": f"{repo_root}/go/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        }

    @property
    @override
    def name(self) -> str:
        return "core-agent"

    @override
    def build(self, app: Application, output: Path, *args: Any, **kwargs: Any) -> None:
        # TODO: Build rtloader first if needed
        # TODO: Make this build in a devenv ? Or at least add a flag
        app.tools.go.build(
            "github.com/DataDog/datadog-agent/cmd/agent",
            output=output,
            build_tags=self.get_build_tags(),
            gcflags=self.get_gcflags(),
            ldflags=self.get_ldflags(app),
            env_vars=self.get_build_env(app),
        )
