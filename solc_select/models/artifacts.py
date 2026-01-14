"""Artifact-related domain models."""

from dataclasses import dataclass
from pathlib import Path

from packaging.version import Version

from ..platform_capabilities import EmulationCapability
from .platforms import Platform
from .versions import SolcVersion


@dataclass(kw_only=True)
class SolcArtifactOnDisk:
    """Represents a Solidity compiler artifact on disk."""

    version: SolcVersion
    platform: Platform
    file_path: Path
    emulation: EmulationCapability | None = None


@dataclass(kw_only=True)
class SolcArtifact(SolcArtifactOnDisk):
    """Represents a downloadable Solidity compiler artifact."""

    download_url: str
    checksum_sha256: str
    checksum_keccak256: str | None

    def __post_init__(self) -> None:
        if not self.download_url:
            raise ValueError("Download URL cannot be empty")
        if not self.checksum_sha256:
            raise ValueError("SHA256 checksum cannot be empty")
        self.checksum_sha256 = self.checksum_sha256.removeprefix("0x")
        if self.checksum_keccak256:
            self.checksum_keccak256 = self.checksum_keccak256.removeprefix("0x")

    @property
    def is_zip_archive(self) -> bool:
        """Check if this artifact is a ZIP archive (older Windows versions)."""
        return self.platform.os_type == "windows" and self.version <= Version("0.7.1")

    def get_binary_name_in_zip(self) -> str:
        """Get the binary name inside ZIP archives."""
        if not self.is_zip_archive:
            raise ValueError("Not a ZIP archive")
        return "solc.exe"
