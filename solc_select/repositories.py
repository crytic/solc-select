"""
Repository pattern implementations for solc-select.

This module provides abstractions for fetching Solidity compiler version information
and artifacts from different sources (soliditylang.org, crytic, alloy, etc.).
"""

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


class SolcRepository:
    """Repository for fetching Solidity compiler version information and artifacts.

    Replaces the former AbstractSolcRepository/GenericRepository hierarchy with a single
    concrete implementation. All behavior differences are handled through constructor parameters.
    """

    def __init__(
        self,
        base_url: str,
        list_url: str,
        session: requests.Session,
        has_latest_release: bool = False,
    ):
        """Initialize repository.

        Args:
            base_url: Base URL for downloading artifacts
            list_url: URL for the list.json file
            session: HTTP session for requests
            has_latest_release: Whether list.json has a "latestRelease" field
        """
        self.session = session
        self._base_url = base_url
        self._list_url = list_url
        self._has_latest_release = has_latest_release

    @property
    def base_url(self) -> str:
        """Get the base URL for downloading artifacts."""
        return self._base_url

    @property
    def list_url(self) -> str:
        """Get the URL for the list.json file containing version information."""
        return self._list_url

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
        return list_data["releases"]  # type: ignore[no-any-return]

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
            versions = self.available_versions
            if not versions:
                raise ValueError("No versions available")
            version_objs = [SolcVersion.parse(v) for v in versions]
            return max(version_objs)

    def get_download_url(self, artifact_filename: str) -> str:
        """Get the download URL for a specific artifact."""
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


# Factory functions for creating repository instances
# These provide convenience for constructing repositories with appropriate URLs


def SoliditylangRepository(platform: "Platform", session: requests.Session) -> SolcRepository:
    """Create a Soliditylang repository for the given platform.

    Args:
        platform: Platform to construct URLs for
        session: HTTP session for requests

    Returns:
        SolcRepository instance configured for soliditylang.org
    """
    platform_key = platform.get_soliditylang_key()
    return SolcRepository(
        base_url=f"https://binaries.soliditylang.org/{platform_key}/",
        list_url=f"https://binaries.soliditylang.org/{platform_key}/list.json",
        session=session,
        has_latest_release=True,
    )


def CryticRepository(session: requests.Session) -> SolcRepository:
    """Create a Crytic repository.

    Args:
        session: HTTP session for requests

    Returns:
        SolcRepository instance configured for crytic/solc
    """
    return SolcRepository(
        base_url=CRYTIC_SOLC_ARTIFACTS,
        list_url=CRYTIC_SOLC_JSON,
        session=session,
        has_latest_release=False,
    )


def AlloyRepository(session: requests.Session) -> SolcRepository:
    """Create an Alloy repository.

    Args:
        session: HTTP session for requests

    Returns:
        SolcRepository instance configured for alloy-rs/solc-builds
    """
    return SolcRepository(
        base_url=ALLOY_SOLC_ARTIFACTS,
        list_url=ALLOY_SOLC_JSON,
        session=session,
        has_latest_release=False,
    )
