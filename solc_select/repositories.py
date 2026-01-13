"""
Repository pattern implementations for solc-select.

This module provides abstractions for fetching Solidity compiler version information
and artifacts from different sources (soliditylang.org, crytic, alloy, etc.).
"""

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any

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
    EARLIEST_RELEASE_OS,
    LINUX_AMD64,
)
from .models import Platform, SolcVersion


class AbstractSolcRepository(ABC):
    """Abstract base class for Solidity compiler repositories."""

    def __init__(self, session: requests.Session) -> None:
        self.session = session

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

    @lru_cache(maxsize=5)  # noqa: B019
    def _fetch_list_json(self) -> dict[str, Any]:
        """Fetch and cache the list.json data from the repository.

        Returns:
            The parsed JSON data from the list.json endpoint
        """
        response = self.session.get(self.list_url)
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]

    @property
    @lru_cache(maxsize=5)  # noqa: B019
    def available_versions(self) -> dict[str, str]:
        """Get available versions as a dict of version -> artifact_filename."""
        list_data = self._fetch_list_json()
        all_releases = list_data["releases"]
        return self._filter_versions(all_releases)

    @property
    @lru_cache(maxsize=5)  # noqa: B019
    def latest_version(self) -> SolcVersion:
        """Get the latest available version.

        Default implementation parses from available versions.
        Subclasses can override this for more efficient implementations.
        """
        versions = self.available_versions
        if not versions:
            raise ValueError("No versions available")

        version_objs = [SolcVersion.parse(v) for v in versions]
        return max(version_objs)

    def _filter_versions(self, releases: dict[str, str]) -> dict[str, str]:
        """Filter versions based on repository-specific criteria.

        Override this method to apply custom filtering logic.
        Default implementation returns all versions.
        """
        return releases

    def get_download_url(self, version: SolcVersion, artifact_filename: str) -> str:
        """Get the download URL for a specific version."""
        return f"{self.base_url}{artifact_filename}"

    def get_checksums(self, version: SolcVersion) -> tuple[str, str | None]:
        """Get SHA256 and optional Keccak256 checksums for a version."""
        list_data = self._fetch_list_json()
        builds = list_data["builds"]

        version_str = str(version)
        matches = [b for b in builds if b["version"] == version_str and "prerelease" not in b]

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

    def __init__(self, platform: Platform, session: requests.Session) -> None:
        super().__init__(session)
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
        platform_key = platform.get_soliditylang_key()
        if platform_key not in EARLIEST_RELEASE:
            return False

        earliest = Version(EARLIEST_RELEASE[platform_key])
        return version >= earliest

    @property
    @lru_cache(maxsize=5)  # noqa: B019
    def latest_version(self) -> SolcVersion:
        """Get the latest available version."""
        list_data = self._fetch_list_json()
        latest_str = list_data["latestRelease"]
        return SolcVersion.parse(latest_str)


class CryticRepository(AbstractSolcRepository):
    """Repository for crytic/solc - provides additional Linux versions."""

    def __init__(self, session: requests.Session) -> None:
        super().__init__(session)

    @property
    def base_url(self) -> str:
        return CRYTIC_SOLC_ARTIFACTS

    @property
    def list_url(self) -> str:
        return CRYTIC_SOLC_JSON

    def supports_version(self, version: SolcVersion, platform: Platform) -> bool:
        """Check if this repository supports the version."""
        # Special case: version 0.8.18 is supported
        if version == Version("0.8.18"):
            return True

        # General case: versions <= 0.4.10 for Linux
        earliest = Version(EARLIEST_RELEASE_OS["linux"])
        return version <= Version("0.4.10") and version >= earliest


class AlloyRepository(AbstractSolcRepository):
    """Repository for alloy-rs/solc-builds - provides native ARM64 Darwin binaries."""

    def __init__(self, session: requests.Session) -> None:
        super().__init__(session)

    @property
    def base_url(self) -> str:
        return ALLOY_SOLC_ARTIFACTS

    @property
    def list_url(self) -> str:
        return ALLOY_SOLC_JSON

    def _filter_versions(self, releases: dict[str, str]) -> dict[str, str]:
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

    def __init__(self, platform: Platform, session: requests.Session):
        self.platform = platform
        self.repositories: list[AbstractSolcRepository] = []

        # Linux ARM64: Add x86_64 fallback first
        if platform.os_type == "linux" and platform.architecture == "arm64":
            # The main soliditylang repository (line 226) already handles native ARM64
            # Just add x86_64 fallback for older versions (via QEMU emulation)
            x86_platform = Platform(os_type="linux", architecture="amd64")
            self.repositories.append(SoliditylangRepository(x86_platform, session))

        # Always include the main soliditylang repository
        self.repositories.append(SoliditylangRepository(platform, session))

        # Add platform-specific repositories
        if platform.os_type == "linux":
            self.repositories.append(CryticRepository(session))

        if platform.os_type == "darwin" and platform.architecture == "arm64":
            self.repositories.append(AlloyRepository(session))

    @property
    @lru_cache(maxsize=5)  # noqa: B019
    def available_versions(self) -> dict[str, str]:
        """Get all available versions from all repositories."""
        all_versions = {}

        for repo in self.repositories:
            try:
                versions = repo.available_versions
                all_versions.update(versions)
            except requests.RequestException:
                # Continue if one repository fails
                continue

        return all_versions

    @property
    @lru_cache(maxsize=5)  # noqa: B019
    def latest_version(self) -> SolcVersion:
        """Get the latest version across all repositories."""
        latest_versions = []

        for repo in self.repositories:
            try:
                latest_versions.append(repo.latest_version)
            except (ValueError, requests.RequestException):
                # Continue if one repository fails
                continue

        if not latest_versions:
            raise ValueError("No versions available from any repository")

        return max(latest_versions)

    def get_repository_for_version(self, version: SolcVersion) -> AbstractSolcRepository:
        """Get the appropriate repository for a specific version."""
        # Check for platform-specific repositories
        for repo in reversed(self.repositories):  # Check specialized repos first
            if repo.supports_version(version, self.platform):
                return repo

        # Fallback to main soliditylang repository
        return self.repositories[0]
