"""
Version management service for solc-select.

This module handles validation, resolution, and management of Solidity compiler versions.
"""

import argparse
from typing import List

from ..constants import EARLIEST_RELEASE
from ..models import Platform, SolcVersion
from ..repositories import CompositeRepository


class VersionManager:
    """Service for managing Solidity compiler versions."""

    def __init__(self, repository: CompositeRepository, platform: Platform):
        self.repository = repository
        self.platform = platform

    def get_available_versions(self) -> List[SolcVersion]:
        """Get all available versions that can be installed.

        Returns:
            List of available versions sorted by version number
        """
        releases = self.repository.get_available_versions()
        versions = []

        for version_str in releases:
            try:
                version = SolcVersion.parse(version_str)
                if version.is_compatible_with_platform(self.platform):
                    versions.append(version)
            except ValueError:
                # Skip invalid version strings
                continue

        # Sort versions
        versions.sort()
        return versions

    def get_latest_version(self) -> SolcVersion:
        """Get the latest available version.

        Returns:
            The latest SolcVersion

        Raises:
            ValueError: If no versions are available
        """
        return self.repository.get_latest_version()

    def validate_version(self, version_str: str) -> SolcVersion:
        """Validate and parse a version string.

        Args:
            version_str: Version string to validate (e.g., "0.8.19", "latest")

        Returns:
            Validated SolcVersion

        Raises:
            argparse.ArgumentTypeError: If version is invalid
        """
        if version_str == "latest":
            try:
                return self.get_latest_version()
            except Exception as e:
                raise argparse.ArgumentTypeError(f"Could not resolve latest version: {e}")

        try:
            version = SolcVersion.parse(version_str)
        except ValueError:
            raise argparse.ArgumentTypeError(f"Invalid version '{version_str}'.")

        # Check minimum version for platform
        if not version.is_compatible_with_platform(self.platform):
            platform_key = self.platform.get_soliditylang_key()
            earliest = EARLIEST_RELEASE.get(platform_key, "0.0.0")
            raise argparse.ArgumentTypeError(
                f"Invalid version - only solc versions above '{earliest}' are available"
            )

        # Check if version exists in available releases
        available_versions = self.get_available_versions()
        if version not in available_versions:
            latest = self.get_latest_version()
            if version > latest:
                raise argparse.ArgumentTypeError(
                    f"Invalid version '{latest}' is the latest available version"
                )
            else:
                raise argparse.ArgumentTypeError(f"Version '{version}' is not available")

        return version

    def resolve_version_strings(self, version_strings: List[str]) -> List[SolcVersion]:
        """Resolve a list of version strings to SolcVersion objects.

        Args:
            version_strings: List of version strings (may contain "latest", "all")

        Returns:
            List of resolved SolcVersion objects
        """
        if "all" in version_strings:
            return self.get_available_versions()

        versions = []
        for version_str in version_strings:
            if version_str == "latest":
                versions.append(self.get_latest_version())
            else:
                versions.append(self.validate_version(version_str))

        return versions

    def get_installable_versions(self, installed_versions: List[SolcVersion]) -> List[SolcVersion]:
        """Get versions that can be installed (not already installed).

        Args:
            installed_versions: List of currently installed versions

        Returns:
            List of installable versions
        """
        available = self.get_available_versions()
        installable = [v for v in available if v not in installed_versions]
        return installable
