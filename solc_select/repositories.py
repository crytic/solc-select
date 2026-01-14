"""Repository implementations for fetching Solidity compiler versions."""

from functools import lru_cache
from typing import Any

import requests

from .constants import (
    ALLOY_SOLC_ARTIFACTS,
    ALLOY_SOLC_JSON,
    CRYTIC_SOLC_ARTIFACTS,
    CRYTIC_SOLC_JSON,
)
from .models.platforms import Platform
from .models.versions import SolcVersion


class SolcRepository:
    """Repository for fetching Solidity compiler version information and artifacts."""

    def __init__(
        self,
        base_url: str,
        list_url: str,
        session: requests.Session,
        has_latest_release: bool = False,
    ):
        self.session = session
        self.base_url = base_url
        self.list_url = list_url
        self._has_latest_release = has_latest_release

    @lru_cache(maxsize=5)  # noqa: B019
    def _fetch_list_json(self) -> dict[str, Any]:
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
            list_data = self._fetch_list_json()
            return SolcVersion.parse(list_data["latestRelease"])

        versions = self.available_versions
        if not versions:
            raise ValueError("No versions available")
        return max(SolcVersion.parse(v) for v in versions)

    def get_download_url(self, artifact_filename: str) -> str:
        return f"{self.base_url}{artifact_filename}"

    def get_checksums(self, version: SolcVersion) -> tuple[str, str | None]:
        """Get SHA256 and optional Keccak256 checksums for a version."""
        list_data = self._fetch_list_json()
        builds = list_data["builds"]
        version_str = str(version)

        matches = [b for b in builds if b["version"] == version_str and "prerelease" not in b]
        if not matches or not matches[0]["sha256"]:
            raise ValueError(f"Unable to retrieve checksum for {version}")

        sha256_hash = matches[0]["sha256"].removeprefix("0x")
        keccak256_hash = matches[0].get("keccak256")
        if keccak256_hash:
            keccak256_hash = keccak256_hash.removeprefix("0x")

        return sha256_hash, keccak256_hash


def SoliditylangRepository(platform: Platform, session: requests.Session) -> SolcRepository:
    """Create a Soliditylang repository for the given platform."""
    platform_key = platform.get_soliditylang_key()
    return SolcRepository(
        base_url=f"https://binaries.soliditylang.org/{platform_key}/",
        list_url=f"https://binaries.soliditylang.org/{platform_key}/list.json",
        session=session,
        has_latest_release=True,
    )


def CryticRepository(session: requests.Session) -> SolcRepository:
    """Create a Crytic repository."""
    return SolcRepository(
        base_url=CRYTIC_SOLC_ARTIFACTS,
        list_url=CRYTIC_SOLC_JSON,
        session=session,
        has_latest_release=False,
    )


def AlloyRepository(session: requests.Session) -> SolcRepository:
    """Create an Alloy repository."""
    return SolcRepository(
        base_url=ALLOY_SOLC_ARTIFACTS,
        list_url=ALLOY_SOLC_JSON,
        session=session,
        has_latest_release=False,
    )
