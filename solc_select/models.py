"""
Domain models for solc-select.

This module contains the core business entities and value objects that represent
the domain concepts of Solidity compiler version management.
"""

import platform
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from packaging.version import Version

from .constants import (
    LINUX_AMD64,
    LINUX_ARM64,
    MACOSX_AMD64,
    WINDOWS_AMD64,
)

# ========================================
# PLATFORM CAPABILITY MODELS
# ========================================


@dataclass(frozen=True)
class PlatformIdentifier:
    """Unique identifier for a platform (OS + architecture).

    Examples: 'linux-amd64', 'darwin-arm64', 'windows-amd64'
    """

    os_type: str  # 'linux', 'darwin', 'windows'
    architecture: str  # 'amd64', 'arm64', '386'


@dataclass(frozen=True)
class EmulationCapability:
    """Describes emulation support for running foreign platform binaries.

    Example: Linux ARM64 can run linux-amd64 binaries via QEMU.
    """

    target_platform: PlatformIdentifier  # Platform that can be emulated
    emulation_type: str  # 'rosetta', 'qemu'
    detector: Callable[[], bool]  # Function to check if emulation available
    command_prefix: list[str]  # Command prefix for emulation (e.g., ["qemu-x86_64"])
    performance_note: str | None = None  # Warning message for users


@dataclass
class PlatformCapability:
    """Declares which platforms a device can execute binaries for.

    Supports both native execution and emulated platforms.

    Example for Linux ARM64 with QEMU:
        - native_support: linux-arm64
        - emulation_capabilities: [linux-amd64 via QEMU]
    """

    host_platform: PlatformIdentifier  # The actual hardware platform
    native_support: PlatformIdentifier  # Always can run native binaries
    emulation_capabilities: list[EmulationCapability] = field(default_factory=list)

    def get_runnable_platforms(self) -> list[PlatformIdentifier]:
        """Get all platforms this device can execute, prioritized.

        Returns native first, then emulated platforms (only if emulator available).

        Returns:
            List of PlatformIdentifier, native first
        """
        platforms = [self.native_support]

        # Add emulated platforms with available emulators
        for ec in self.emulation_capabilities:
            if ec.detector():
                platforms.append(ec.target_platform)

        return platforms

    def get_emulation_for_platform(self, target: PlatformIdentifier) -> EmulationCapability | None:
        """Get emulation info for a target platform.

        Args:
            target: Platform to check

        Returns:
            EmulationCapability if target requires emulation, None if native
        """
        if target == self.native_support:
            return None
        return next(
            (ec for ec in self.emulation_capabilities if ec.target_platform == target),
            None,
        )


@dataclass(frozen=True)
class VersionRange:
    """Inclusive version range [min, max].

    None means unbounded in that direction.
    """

    min_version: "SolcVersion | None" = None  # None = no lower bound
    max_version: "SolcVersion | None" = None  # None = no upper bound

    def contains(self, version: "SolcVersion") -> bool:
        """Check if version is within range (inclusive).

        Args:
            version: Version to check

        Returns:
            True if version is in [min, max], False otherwise
        """
        if self.min_version and version < self.min_version:
            return False
        return not (self.max_version and version > self.max_version)

    @classmethod
    def from_min(cls, min_ver: str) -> "VersionRange":
        """Create range with only minimum version.

        Args:
            min_ver: Minimum version string

        Returns:
            VersionRange from min_ver to infinity
        """
        # Import here to avoid circular import
        return cls(min_version=SolcVersion.parse(min_ver), max_version=None)

    @classmethod
    def exact_range(cls, min_ver: str, max_ver: str) -> "VersionRange":
        """Create exact range [min, max].

        Args:
            min_ver: Minimum version string
            max_ver: Maximum version string

        Returns:
            VersionRange from min_ver to max_ver (inclusive)
        """
        return cls(
            min_version=SolcVersion.parse(min_ver),
            max_version=SolcVersion.parse(max_ver),
        )


@dataclass(frozen=True)
class PlatformSupport:
    """Declares what versions a repository provides for a specific platform.

    Example: Soliditylang provides linux-amd64 binaries from version 0.4.10+
    """

    platform: PlatformIdentifier
    version_range: VersionRange

    def supports(self, version: "SolcVersion", target_platform: PlatformIdentifier) -> bool:
        """Check if this support matches version + platform.

        Args:
            version: Version to check
            target_platform: Platform to check

        Returns:
            True if this support provides the version for the platform
        """
        return self.platform == target_platform and self.version_range.contains(version)


@dataclass
class RepositoryManifest:
    """Declarative manifest of what a repository provides.

    Example:
        SOLIDITYLANG_MANIFEST = RepositoryManifest(
            repository_id="soliditylang",
            base_url="https://binaries.soliditylang.org",
            platform_supports=[...],
            priority=100,
        )
    """

    repository_id: str  # 'soliditylang', 'crytic', 'alloy'
    base_url: str
    platform_supports: list[PlatformSupport]
    priority: int = 50  # Higher = checked first (100=primary, 50=fallback, 10=legacy)

    def supports_version(self, version: "SolcVersion", platform: PlatformIdentifier) -> bool:
        """Check if this repository can provide version for platform.

        Args:
            version: Version to check
            platform: Platform to check

        Returns:
            True if repository provides this version/platform combo
        """
        return any(ps.supports(version, platform) for ps in self.platform_supports)


# ========================================
# VERSION MODELS
# ========================================


class SolcVersion(Version):
    """Represents a Solidity compiler version, inheriting from packaging.Version."""

    @classmethod
    def parse(cls, version_str: str) -> "SolcVersion":
        """Parse a version string into a SolcVersion instance.

        Args:
            version_str: Version string like '0.8.19'

        Returns:
            SolcVersion instance

        Raises:
            ValueError: If version string format is invalid
        """
        if version_str == "latest":
            raise ValueError("Cannot parse 'latest' - resolve to actual version first")

        # Let packaging.Version handle the parsing and validation
        return cls(version_str)


@dataclass(frozen=True)
class Platform:
    """Represents a target platform for Solidity compilation."""

    os_type: str  # 'linux', 'darwin', 'windows'
    architecture: str  # 'amd64', 'arm64'

    # Class-level capability registry
    _capability_registry: ClassVar[dict[str, PlatformCapability]] = {}

    def __post_init__(self) -> None:
        """Validate platform components."""
        valid_os = {"linux", "darwin", "windows"}
        valid_arch = {"amd64", "arm64"}

        if self.os_type not in valid_os:
            raise ValueError(f"Invalid OS type: {self.os_type}")
        if self.architecture not in valid_arch:
            raise ValueError(f"Invalid architecture: {self.architecture}")

    @classmethod
    def register_capability(cls, capability: PlatformCapability) -> None:
        """Register a platform capability configuration.

        Args:
            capability: PlatformCapability to register
        """
        key = f"{capability.host_platform.os_type}-{capability.host_platform.architecture}"
        cls._capability_registry[key] = capability

    def get_capability(self) -> PlatformCapability:
        """Get the capability declaration for this platform.

        Returns:
            PlatformCapability for this platform (default if not registered)
        """
        key = f"{self.os_type}-{self.architecture}"
        return self._capability_registry.get(key, self._create_default_capability())

    def _create_default_capability(self) -> PlatformCapability:
        """Create default capability (native-only, no emulation).

        Returns:
            PlatformCapability with only native support
        """
        platform_id = PlatformIdentifier(self.os_type, self.architecture)
        return PlatformCapability(
            host_platform=platform_id,
            native_support=platform_id,
            emulation_capabilities=[],
        )

    # ========================================
    # CORE PLATFORM DETECTION
    # ========================================

    @classmethod
    def current(cls) -> "Platform":
        """Get the current system platform."""
        if sys.platform == "linux":
            os_type = "linux"
        elif sys.platform == "darwin":
            os_type = "darwin"
        elif sys.platform in ["win32", "cygwin"]:
            os_type = "windows"
        else:
            raise ValueError(f"Unsupported platform: {sys.platform}")

        architecture = cls._get_arch()
        return cls(os_type=os_type, architecture=architecture)

    @staticmethod
    def _get_arch() -> str:
        """Get the current system architecture."""
        machine = platform.machine().lower()
        if machine in ["x86_64", "amd64"]:
            return "amd64"
        elif machine in ["aarch64", "arm64"]:
            return "arm64"
        return machine

    def get_soliditylang_key(self) -> str:
        """Get the platform key used by binaries.soliditylang.org."""
        if self.os_type == "linux" and self.architecture == "amd64":
            return LINUX_AMD64
        elif self.os_type == "linux" and self.architecture == "arm64":
            return LINUX_ARM64
        elif self.os_type == "darwin" and self.architecture in ["amd64", "arm64"]:
            # soliditylang.org uses macosx-amd64 for both Intel and ARM (with Rosetta and universal binaries)
            return MACOSX_AMD64
        elif self.os_type == "windows" and self.architecture == "amd64":
            return WINDOWS_AMD64
        else:
            raise ValueError(
                f"Unsupported platform combination: {self.os_type}-{self.architecture}"
            )


@dataclass(kw_only=True)
class SolcArtifactOnDisk:
    """Represents a Solidity compiler artifact on disk."""

    version: SolcVersion
    platform: Platform
    file_path: Path
    emulation: EmulationCapability | None = None  # Emulation info if not native


@dataclass(kw_only=True)
class SolcArtifact(SolcArtifactOnDisk):
    """Represents a downloadable Solidity compiler artifact."""

    download_url: str
    checksum_sha256: str
    checksum_keccak256: str | None

    def __post_init__(self) -> None:
        """Validate artifact properties."""
        if not self.download_url:
            raise ValueError("Download URL cannot be empty")
        if not self.checksum_sha256:
            raise ValueError("SHA256 checksum cannot be empty")
        if self.checksum_sha256.startswith("0x"):
            # Normalize by removing 0x prefix
            object.__setattr__(self, "checksum_sha256", self.checksum_sha256[2:])
        if self.checksum_keccak256 and self.checksum_keccak256.startswith("0x"):
            # Normalize by removing 0x prefix
            object.__setattr__(self, "checksum_keccak256", self.checksum_keccak256[2:])

    @property
    def is_zip_archive(self) -> bool:
        """Check if this artifact is a ZIP archive (older Windows versions)."""
        return self.platform.os_type == "windows" and self.version <= Version("0.7.1")

    def get_binary_name_in_zip(self) -> str:
        """Get the binary name inside ZIP archives."""
        if not self.is_zip_archive:
            raise ValueError("Not a ZIP archive")
        return "solc.exe"
