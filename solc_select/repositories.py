"""
Repository pattern implementations for solc-select.

This module provides abstractions for fetching Solidity compiler version information
and artifacts from different sources (soliditylang.org, crytic, alloy, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple

import requests
from packaging.version import Version

from .constants import (
    ALLOY_ARM64_MAX_VERSION,
    ALLOY_ARM64_MIN_VERSION,
    ALLOY_SOLC_ARTIFACTS,
    ALLOY_SOLC_JSON,
    CRYTIC_SOLC_ARTIFACTS,
    CRYTIC_SOLC_JSON,
    EARLIEST_RELEASE,
    LINUX_AMD64,
)
from .infrastructure.http_client import create_http_session
from .models import Platform, SolcVersion


class AbstractSolcRepository(ABC):
    """Abstract base class for Solidity compiler repositories."""

    def __init__(self) -> None:
        self.session = create_http_session()

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Get the base URL for downloading artifacts."""
        pass

    @property
    @abstractmethod
    def list_url(self) -> str:
        """Get the URL for the list.json file containing version information."""
        pass

    def get_available_versions(self) -> Dict[str, str]:
        """Get available versions as a dict of version -> artifact_filename."""
        response = self.session.get(self.list_url)
        response.raise_for_status()
        all_releases = response.json()["releases"]
        return self._filter_versions(all_releases)

    def _filter_versions(self, releases: Dict[str, str]) -> Dict[str, str]:
        """Filter versions based on repository-specific criteria.

        Override this method to apply custom filtering logic.
        Default implementation returns all versions.
        """
        return releases

    def get_download_url(self, version: SolcVersion, artifact_filename: str) -> str:
        """Get the download URL for a specific version."""
        return f"{self.base_url}{artifact_filename}"

    def get_checksums(self, version: SolcVersion) -> Tuple[str, Optional[str]]:
        """Get SHA256 and optional Keccak256 checksums for a version."""
        response = self.session.get(self.list_url)
        response.raise_for_status()
        builds = response.json()["builds"]

        version_str = str(version)
        matches = [b for b in builds if b["version"] == version_str]

        if not matches or not matches[0]["sha256"]:
            raise ValueError(f"Unable to retrieve checksum for {version}")

        sha256_hash = matches[0]["sha256"]
        keccak256_hash = matches[0].get("keccak256")

        # Normalize checksums by removing 0x prefix if present
        if sha256_hash and sha256_hash.startswith("0x"):
            sha256_hash = sha256_hash[2:]
        if keccak256_hash and keccak256_hash.startswith("0x"):
            keccak256_hash = keccak256_hash[2:]

        return sha256_hash, keccak256_hash

    @abstractmethod
    def supports_version(self, version: SolcVersion, platform: Platform) -> bool:
        """Check if this repository supports the given version on the platform."""
        pass


class SoliditylangRepository(AbstractSolcRepository):
    """Repository for binaries.soliditylang.org - the main Solidity releases."""

    def __init__(self, platform: Platform) -> None:
        super().__init__()
        self.platform = platform
        platform_key = platform.get_soliditylang_key()
        self._base_url = f"https://binaries.soliditylang.org/{platform_key}/"
        self._list_url = f"https://binaries.soliditylang.org/{platform_key}/list.json"

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def list_url(self) -> str:
        return self._list_url

    def supports_version(self, version: SolcVersion, platform: Platform) -> bool:
        """Check if this repository supports the version on the platform."""
        return version.is_compatible_with_platform(platform)

    def get_latest_version(self) -> SolcVersion:
        """Get the latest available version."""
        response = self.session.get(self.list_url)
        response.raise_for_status()
        latest_str = response.json()["latestRelease"]
        return SolcVersion.parse(latest_str)


class CryticRepository(AbstractSolcRepository):
    """Repository for crytic/solc - provides additional Linux versions."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def base_url(self) -> str:
        return CRYTIC_SOLC_ARTIFACTS

    @property
    def list_url(self) -> str:
        return CRYTIC_SOLC_JSON

    def supports_version(self, version: SolcVersion, platform: Platform) -> bool:
        """Check if this repository supports the version."""
        # Crytic repo is for Linux AMD64 only
        if platform.get_soliditylang_key() != LINUX_AMD64:
            return False

        # Special case: version 0.8.18 is supported
        if version == Version("0.8.18"):
            return True

        # General case: versions <= 0.4.10 for Linux
        earliest = Version(EARLIEST_RELEASE[LINUX_AMD64])
        return version <= Version("0.4.10") and version >= earliest


class AlloyRepository(AbstractSolcRepository):
    """Repository for alloy-rs/solc-builds - provides native ARM64 Darwin binaries."""

    def __init__(self) -> None:
        super().__init__()

    @property
    def base_url(self) -> str:
        return ALLOY_SOLC_ARTIFACTS

    @property
    def list_url(self) -> str:
        return ALLOY_SOLC_JSON

    def _filter_versions(self, releases: Dict[str, str]) -> Dict[str, str]:
        """Filter to only include versions in the supported ARM64 range."""
        min_version = Version(ALLOY_ARM64_MIN_VERSION)
        max_version = Version(ALLOY_ARM64_MAX_VERSION)

        return {
            version: release
            for version, release in releases.items()
            if min_version <= Version(version) <= max_version
        }

    def supports_version(self, version: SolcVersion, platform: Platform) -> bool:
        """Check if this repository supports the version."""
        # Only for Darwin ARM64
        if not (platform.os_type == "darwin" and platform.architecture == "arm64"):
            return False

        min_version = Version(ALLOY_ARM64_MIN_VERSION)
        max_version = Version(ALLOY_ARM64_MAX_VERSION)

        return min_version <= version <= max_version


class CompositeRepository:
    """Composite repository that manages multiple underlying repositories."""

    def __init__(self, platform: Platform):
        self.platform = platform
        self.repositories: List[AbstractSolcRepository] = []

        # Always include the main soliditylang repository
        self.repositories.append(SoliditylangRepository(platform))

        # Add platform-specific repositories
        if platform.get_soliditylang_key() == LINUX_AMD64:
            self.repositories.append(CryticRepository())

        if platform.os_type == "darwin" and platform.architecture == "arm64":
            self.repositories.append(AlloyRepository())

    def get_available_versions(self) -> Dict[str, str]:
        """Get all available versions from all repositories."""
        all_versions = {}

        for repo in self.repositories:
            try:
                versions = repo.get_available_versions()
                all_versions.update(versions)
            except requests.RequestException:
                # Continue if one repository fails
                continue

        return all_versions

    def get_repository_for_version(self, version: SolcVersion) -> AbstractSolcRepository:
        """Get the appropriate repository for a specific version."""
        # Check for platform-specific repositories (including Crytic special cases)
        for repo in reversed(self.repositories):  # Check specialized repos first
            if repo.supports_version(version, self.platform):
                return repo

        # Fallback to main soliditylang repository
        return self.repositories[0]

    def get_latest_version(self) -> SolcVersion:
        """Get the latest version from the main repository."""
        main_repo = self.repositories[0]
        if isinstance(main_repo, SoliditylangRepository):
            return main_repo.get_latest_version()

        # Fallback: parse from available versions
        versions = self.get_available_versions()
        if not versions:
            raise ValueError("No versions available")

        version_objs = [SolcVersion.parse(v) for v in versions]
        latest = max(version_objs)
        return latest
