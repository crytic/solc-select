"""
Domain models for solc-select.

This module contains the core business entities and value objects that represent
the domain concepts of Solidity compiler version management.
"""

import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from packaging.version import Version

from .constants import (
    LINUX_AMD64,
    LINUX_ARM64,
    MACOSX_AMD64,
    WINDOWS_AMD64,
)
from .platform_capabilities import (
    DARWIN_ARM64_CAPABILITY,
    LINUX_ARM64_CAPABILITY,
    EmulationCapability,
    PlatformCapability,
    PlatformIdentifier,
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
        above_minimum = self.min_version is None or version >= self.min_version
        below_maximum = self.max_version is None or version <= self.max_version
        return above_minimum and below_maximum

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

    # Class-level capability registry (hardcoded for darwin-arm64 and linux-arm64)
    _capability_registry: ClassVar[dict[str, PlatformCapability]] = {
        "darwin-arm64": DARWIN_ARM64_CAPABILITY,
        "linux-arm64": LINUX_ARM64_CAPABILITY,
    }

    def __post_init__(self) -> None:
        """Validate platform components."""
        valid_os = {"linux", "darwin", "windows"}
        valid_arch = {"amd64", "arm64"}

        if self.os_type not in valid_os:
            raise ValueError(f"Invalid OS type: {self.os_type}")
        if self.architecture not in valid_arch:
            raise ValueError(f"Invalid architecture: {self.architecture}")

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
        os_mapping = {
            "linux": "linux",
            "darwin": "darwin",
            "win32": "windows",
            "cygwin": "windows",
        }
        os_type = os_mapping.get(sys.platform)
        if os_type is None:
            raise ValueError(f"Unsupported platform: {sys.platform}")

        return cls(os_type=os_type, architecture=cls._get_arch())

    @staticmethod
    def _get_arch() -> str:
        """Get the current system architecture."""
        machine = platform.machine().lower()
        arch_mapping = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }
        return arch_mapping.get(machine, machine)

    def get_soliditylang_key(self) -> str:
        """Get the platform key used by binaries.soliditylang.org."""
        # soliditylang.org uses macosx-amd64 for both Intel and ARM (with Rosetta and universal binaries)
        platform_keys = {
            ("linux", "amd64"): LINUX_AMD64,
            ("linux", "arm64"): LINUX_ARM64,
            ("darwin", "amd64"): MACOSX_AMD64,
            ("darwin", "arm64"): MACOSX_AMD64,
            ("windows", "amd64"): WINDOWS_AMD64,
        }
        key = platform_keys.get((self.os_type, self.architecture))
        if key is None:
            raise ValueError(
                f"Unsupported platform combination: {self.os_type}-{self.architecture}"
            )
        return key


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
