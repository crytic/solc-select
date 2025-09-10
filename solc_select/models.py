"""
Domain models for solc-select.

This module contains the core business entities and value objects that represent
the domain concepts of Solidity compiler version management.
"""

import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from packaging.version import Version

from .constants import (
    EARLIEST_RELEASE,
    LINUX_AMD64,
    MACOSX_AMD64,
    WINDOWS_AMD64,
)


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

    def is_compatible_with_platform(self, platform: "Platform") -> bool:
        """Check if this version is compatible with the given platform.

        Args:
            platform: The target platform

        Returns:
            True if compatible, False otherwise
        """
        platform_key = platform.get_soliditylang_key()
        if platform_key not in EARLIEST_RELEASE:
            return False

        earliest = Version(EARLIEST_RELEASE[platform_key])
        return self >= earliest


@dataclass(frozen=True)
class Platform:
    """Represents a target platform for Solidity compilation."""

    os_type: str  # 'linux', 'darwin', 'windows'
    architecture: str  # 'amd64', 'arm64'

    def __post_init__(self):
        """Validate platform components."""
        valid_os = {"linux", "darwin", "windows"}
        valid_arch = {"amd64", "arm64", "386"}

        if self.os_type not in valid_os:
            raise ValueError(f"Invalid OS type: {self.os_type}")
        if self.architecture not in valid_arch:
            raise ValueError(f"Invalid architecture: {self.architecture}")

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
        elif machine in ["i386", "i686"]:
            return "386"
        return machine

    def get_soliditylang_key(self) -> str:
        """Get the platform key used by binaries.soliditylang.org."""
        if self.os_type == "linux" and self.architecture == "amd64":
            return LINUX_AMD64
        elif self.os_type == "darwin" and self.architecture in ["amd64", "arm64"]:
            # soliditylang.org uses macosx-amd64 for both Intel and ARM (with Rosetta)
            return MACOSX_AMD64
        elif self.os_type == "windows" and self.architecture == "amd64":
            return WINDOWS_AMD64
        else:
            raise ValueError(
                f"Unsupported platform combination: {self.os_type}-{self.architecture}"
            )

    # ========================================
    # EMULATION CAPABILITIES
    # ========================================

    def has_rosetta(self) -> bool:
        """Check if Rosetta 2 is available on macOS ARM64."""
        if self.os_type != "darwin" or self.architecture != "arm64":
            return False

        # Check if oahd (Rosetta daemon) is running
        try:
            result = subprocess.run(["pgrep", "-q", "oahd"], capture_output=True, check=False)
            return result.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def has_qemu(self) -> bool:
        """Check if qemu-x86_64 is available on Linux ARM64."""
        if self.os_type != "linux" or self.architecture != "arm64":
            return False

        try:
            result = subprocess.run(
                ["which", "qemu-x86_64"], capture_output=True, text=True, check=False
            )
            return result.returncode == 0
        except (FileNotFoundError, OSError):
            return False

    def can_run_x86_binaries(self) -> bool:
        """Check if this platform can run x86_64 binaries (natively or via emulation)."""
        # Native x86_64 platforms can always run x86 binaries
        if self.architecture == "amd64":
            return True

        # ARM64 platforms need emulation
        if self.architecture == "arm64":
            if self.os_type == "darwin":
                return self.has_rosetta()
            elif self.os_type == "linux":
                return self.has_qemu()

        return False

    # ========================================
    # BINARY COMPATIBILITY
    # ========================================

    def can_run_binary(self, binary_path: Path) -> bool:
        """Check if we can run a binary on this platform.

        Args:
            binary_path: Path to the binary

        Returns:
            True if binary can be executed, False otherwise
        """
        if not binary_path.exists():
            return False

        # Native architecture can always run
        if self.architecture == "amd64":
            return True

        # ARM64 platforms need special handling
        if self.architecture == "arm64":
            if self.os_type == "darwin":
                return self._can_run_darwin_binary(binary_path)
            else:
                # Other ARM64 platforms need x86 emulation
                return self.can_run_x86_binaries()

        return True

    def _can_run_darwin_binary(self, binary_path: Path) -> bool:
        """Check if we can run a binary on macOS ARM64.

        Handles universal binaries, native ARM64 binaries, and Rosetta emulation.
        """
        # If Rosetta is available, we can run anything
        if self.has_rosetta():
            return True

        # Check if it's a universal binary (works natively)
        if self._mac_binary_is_universal(binary_path):
            return True

        # Check if it's native ARM64
        return self._mac_binary_is_native(binary_path)

    # ========================================
    # PRIVATE HELPERS
    # ========================================

    def _mac_binary_is_universal(self, path: Path) -> bool:
        """Check if the Mac binary is Universal or not."""
        if self.os_type != "darwin":
            return False

        try:
            result = subprocess.run(["/usr/bin/file", str(path)], capture_output=True, check=False)
            if result.returncode != 0:
                return False

            output = result.stdout.decode()
            return all(text in output for text in ("Mach-O universal binary", "x86_64", "arm64"))
        except (FileNotFoundError, OSError):
            return False

    def _mac_binary_is_native(self, path: Path) -> bool:
        """Check if the Mac binary matches the current system architecture."""
        if self.os_type != "darwin":
            return False

        try:
            result = subprocess.run(["/usr/bin/file", str(path)], capture_output=True, check=False)
            if result.returncode != 0:
                return False

            output = result.stdout.decode()
            arch_in_file = "arm64" if self.architecture == "arm64" else "x86_64"
            return "Mach-O" in output and arch_in_file in output
        except (FileNotFoundError, OSError):
            return False


@dataclass
class SolcArtifact:
    """Represents a downloadable Solidity compiler artifact."""

    version: SolcVersion
    platform: Platform
    download_url: str
    checksum_sha256: str
    checksum_keccak256: Optional[str]
    file_path: Path

    def __post_init__(self):
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
