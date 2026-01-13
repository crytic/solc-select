"""
Version management service for solc-select.

This module handles validation, resolution, and management of Solidity compiler versions.
"""

from ..exceptions import (
    PlatformNotSupportedError,
    VersionNotFoundError,
    VersionResolutionError,
)
from ..models import Platform, SolcVersion
from .repository_matcher import RepositoryMatcher


class VersionManager:
    """Service for managing Solidity compiler versions."""

    def __init__(self, repository_matcher: RepositoryMatcher, platform: Platform):
        """Initialize version manager.

        Args:
            repository_matcher: Repository matcher for finding versions
            platform: Current platform
        """
        self.repository_matcher = repository_matcher
        self.platform = platform

    def get_available_versions(self) -> list[SolcVersion]:
        """Get all available versions that can be installed.

        Returns:
            List of available versions sorted by version number (ascending)
        """
        # Get all versions from matcher (already filtered by platform capability)
        available = self.repository_matcher.get_all_available_versions()
        versions = sorted(available.keys())
        return versions

    def get_latest_version(self) -> SolcVersion:
        """Get the latest available version.

        Returns:
            The latest SolcVersion

        Raises:
            ValueError: If no versions are available
        """
        versions = self.get_available_versions()
        if not versions:
            raise ValueError("No versions available")
        return max(versions)

    def validate_version(self, version_str: str) -> SolcVersion:
        """Validate and parse a version string.

        Args:
            version_str: Version string to validate (e.g., "0.8.19", "latest")

        Returns:
            Validated SolcVersion

        Raises:
            VersionResolutionError: If 'latest' version cannot be resolved
            VersionNotFoundError: If version is invalid or not available
        """
        if version_str == "latest":
            try:
                return self.get_latest_version()
            except Exception as e:
                raise VersionResolutionError("latest", str(e)) from e

        try:
            version = SolcVersion.parse(version_str)
        except ValueError as e:
            available_versions = self.get_available_versions()
            available_strs = [str(v) for v in available_versions[:5]]  # Show first 5
            raise VersionNotFoundError(
                version_str, available_strs, "Check the version format (e.g., '0.8.19')"
            ) from e

        # Check if version can be found in any repository
        try:
            self.repository_matcher.find_repository_for_version(version)
        except VersionNotFoundError:
            # Provide helpful error message
            available_versions = self.get_available_versions()

            if not available_versions:
                raise VersionNotFoundError(str(version), []) from None

            latest = max(available_versions)
            minimum = min(available_versions)

            if version > latest:
                raise VersionNotFoundError(
                    str(version), [str(latest)], f"'{latest}' is the latest available version"
                ) from None
            elif version < minimum:
                # Version is below minimum supported version for this platform
                platform_str = f"{self.platform.os_type}-{self.platform.architecture}"
                raise PlatformNotSupportedError(str(version), platform_str, str(minimum)) from None
            else:
                available_strs = [str(v) for v in available_versions[:5]]  # Show first 5
                raise VersionNotFoundError(str(version), available_strs) from None

        return version

    def resolve_version_strings(self, version_strings: list[str]) -> list[SolcVersion]:
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

    def get_installable_versions(self, installed_versions: list[SolcVersion]) -> list[SolcVersion]:
        """Get versions that can be installed (not already installed).

        Args:
            installed_versions: List of currently installed versions

        Returns:
            List of installable versions
        """
        available = self.get_available_versions()
        installable = [v for v in available if v not in installed_versions]
        return installable
