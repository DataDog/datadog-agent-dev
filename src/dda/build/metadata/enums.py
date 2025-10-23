# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from enum import StrEnum, auto
from typing import ClassVar

from msgspec import Struct


class OS(StrEnum):
    """
    The operating system for which the build artifact is intended.
    """

    LINUX = auto()
    WINDOWS = auto()
    MACOS = auto()

    # Any OS - used for indicating compatibility with any operating system
    ANY = auto()

    @classmethod
    def from_alias(cls, alias: str) -> "OS":
        """
        Get the OS enum value from an alias.
        """
        match alias.lower():
            case "linux":
                return cls.LINUX
            case "windows" | "nt" | "win":
                return cls.WINDOWS
            case "macos" | "darwin" | "osx":
                return cls.MACOS
            case "any":
                return cls.ANY
            case _:
                msg = f"Invalid OS identifier: {alias}"
                raise ValueError(msg)


class Arch(StrEnum):
    """
    The CPU architecture for which the build artifact is intended.
    """

    # x86 architectures - canonical name is amd64
    AMD64 = auto()

    # ARM architectures - canonical name is arm64
    ARM64 = auto()

    # ARMHF architectures
    ARMHF = auto()

    # Any architecture - used for indicating compatibility with any CPU architecture
    ANY = auto()

    @classmethod
    def from_alias(cls, alias: str) -> "Arch":
        """
        Get the Arch enum value from an alias.
        """
        match alias.lower():
            case "amd64" | "x86_64" | "x86-64" | "x86" | "x64":
                return cls.AMD64
            case "arm64" | "aarch64" | "arm" | "aarch":
                return cls.ARM64
            case "any":
                return cls.ANY
            case _:
                msg = f"Invalid Arch identifier: {alias}"
                raise ValueError(msg)


class Platform(Struct, frozen=True):
    """
    The platform for which the build artifact is intended.
    """

    os: OS
    arch: Arch

    ANY: ClassVar["Platform"]

    @classmethod
    def from_alias(cls, os_alias: str, arch_alias: str) -> "Platform":
        """
        Get the Platform enum value from an alias.
        """
        return cls(os=OS.from_alias(os_alias), arch=Arch.from_alias(arch_alias))

    def __str__(self) -> str:
        """
        Get the string representation of the platform.
        """
        return f"{self.os}-{self.arch}"


# Initialize the ANY class variable after the class is fully defined
Platform.ANY = Platform(os=OS.ANY, arch=Arch.ANY)


class DigestType(StrEnum):
    """
    The type of digest for a build artifact, i.e. the possible values for the `digest` field in the BuildMetadata struct.
    """

    # Digest applicable to files
    # Suport only SHA256 for now
    FILE_SHA256 = auto()

    # Digest applicable to OCI container images
    # Use the OCI image digest format (result of `docker image inspect <image> --format '{{.Id}}'`)
    OCI_DIGEST = auto()
