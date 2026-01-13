"""
Repository pattern implementations for solc-select.

This module provides abstractions for fetching Solidity compiler version information
and artifacts from different sources (soliditylang.org, crytic, alloy, etc.).
"""

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import requests

from .constants import (
    ALLOY_SOLC_ARTIFACTS,
    ALLOY_SOLC_JSON,
    CRYTIC_SOLC_ARTIFACTS,
    CRYTIC_SOLC_JSON,
)
from .models import SolcVersion

if TYPE_CHECKING:
    from .models import Platform


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


class GenericRepository(AbstractSolcRepository):
    """Generic repository implementation that works with any URL configuration.

    This replaces the specific repository classes (Soliditylang, Crytic, Alloy)
    with a single implementation driven by manifest configuration.
    """

    def __init__(
        self,
        base_url: str,
        list_url: str,
        session: requests.Session,
        has_latest_release: bool = False,
    ):
        """Initialize generic repository.

        Args:
            base_url: Base URL for downloading artifacts
            list_url: URL for the list.json file
            session: HTTP session for requests
            has_latest_release: Whether list.json has a "latestRelease" field
        """
        super().__init__(session)
        self._base_url = base_url
        self._list_url = list_url
        self._has_latest_release = has_latest_release

    @property
    def base_url(self) -> str:
        return self._base_url

    @property
    def list_url(self) -> str:
        return self._list_url

    @property
    @lru_cache(maxsize=5)  # noqa: B019
    def latest_version(self) -> SolcVersion:
        """Get the latest available version."""
        if self._has_latest_release:
            # Soliditylang repositories have a latestRelease field
            list_data = self._fetch_list_json()
            latest_str = list_data["latestRelease"]
            return SolcVersion.parse(latest_str)
        else:
            # For other repositories, compute from available versions
            return super().latest_version


# Legacy repository class names kept for backward compatibility
# but they now just create GenericRepository instances


def SoliditylangRepository(platform: "Platform", session: requests.Session) -> GenericRepository:
    """Create a Soliditylang repository for the given platform.

    Note: This is now a factory function, not a class.
    """
    platform_key = platform.get_soliditylang_key()
    return GenericRepository(
        base_url=f"https://binaries.soliditylang.org/{platform_key}/",
        list_url=f"https://binaries.soliditylang.org/{platform_key}/list.json",
        session=session,
        has_latest_release=True,
    )


def CryticRepository(session: requests.Session) -> GenericRepository:
    """Create a Crytic repository.

    Note: This is now a factory function, not a class.
    """
    return GenericRepository(
        base_url=CRYTIC_SOLC_ARTIFACTS,
        list_url=CRYTIC_SOLC_JSON,
        session=session,
        has_latest_release=False,
    )


def AlloyRepository(session: requests.Session) -> GenericRepository:
    """Create an Alloy repository.

    Note: This is now a factory function, not a class.
    """
    return GenericRepository(
        base_url=ALLOY_SOLC_ARTIFACTS,
        list_url=ALLOY_SOLC_JSON,
        session=session,
        has_latest_release=False,
    )
