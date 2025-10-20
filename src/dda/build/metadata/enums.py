# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from enum import StrEnum, auto
from typing import ClassVar

from msgspec import Struct


class ArtifactType(StrEnum):
    """
    The type of the build artifact, one of:
    - `comp` (component)
    - `dist` (distribution)
    """

    COMP = auto()
    DIST = auto()


class ArtifactFormat(StrEnum):
    """
    The format of the build artifact.
    """

    BIN = auto()
    DEB = auto()
    RPM = auto()
    MSI = auto()
    OCI = auto()  # Docker container image

    def validate_for_type(self, artifact_type: ArtifactType) -> None:
        """
        Validate that the artifact format is valid for the given artifact type.
        """
        match artifact_type:
            case ArtifactType.COMP:
                if self is not self.BIN:
                    msg = f"Invalid artifact format for component artifact: {self}"
                    raise ValueError(msg)
            case ArtifactType.DIST:
                if self not in {self.DEB, self.RPM, self.MSI, self.OCI}:
                    msg = f"Invalid artifact format for distribution artifact: {self}"
                    raise ValueError(msg)

    def get_file_identifier(self) -> str:
        """
        Get the file identifier for the artifact format.
        This is the string that will be used to identify the artifact format in the filename.
        This usually corresponds to the file extension, but can include some other charactres before it.
        """
        match self:
            case self.BIN:
                return ""
            case self.DEB:
                return ".deb"
            case self.RPM:
                return ".rpm"
            case self.MSI:
                return ".msi"
            case self.OCI:
                return "-oci.tar.gz"
        # Adding a default return value to satisfy mypy, even though we should never reach here
        return ""


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
