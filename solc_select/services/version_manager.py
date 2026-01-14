"""Version management service for solc-select."""

from ..exceptions import (
    PlatformNotSupportedError,
    VersionNotFoundError,
    VersionResolutionError,
)
from ..models.platforms import Platform
from ..models.versions import SolcVersion
from .repository_matcher import RepositoryMatcher


class VersionManager:
    """Service for managing Solidity compiler versions."""

    def __init__(self, repository_matcher: RepositoryMatcher, platform: Platform):
        self.repository_matcher = repository_matcher
        self.platform = platform

    def get_available_versions(self) -> list[SolcVersion]:
        """Get all available versions that can be installed."""
        available = self.repository_matcher.get_all_available_versions()
        return sorted(available.keys())

    def get_latest_version(self) -> SolcVersion:
        """Get the latest available version."""
        versions = self.get_available_versions()
        if not versions:
            raise ValueError("No versions available")
        return max(versions)

    def validate_version(self, version_str: str) -> SolcVersion:
        """Validate and parse a version string."""
        if version_str == "latest":
            try:
                return self.get_latest_version()
            except Exception as e:
                raise VersionResolutionError("latest", str(e)) from e

        try:
            version = SolcVersion.parse(version_str)
        except ValueError as e:
            available_versions = self.get_available_versions()
            available_strs = [str(v) for v in available_versions[:5]]
            raise VersionNotFoundError(
                version_str, available_strs, "Check the version format (e.g., '0.8.19')"
            ) from e

        try:
            self.repository_matcher.find_repository_for_version(version)
            return version
        except VersionNotFoundError:
            pass

        available_versions = self.get_available_versions()
        if not available_versions:
            raise VersionNotFoundError(str(version), [])

        latest = max(available_versions)
        minimum = min(available_versions)

        if version > latest:
            raise VersionNotFoundError(
                str(version), [str(latest)], f"'{latest}' is the latest available version"
            )

        if version < minimum:
            platform_str = f"{self.platform.os_type}-{self.platform.architecture}"
            raise PlatformNotSupportedError(str(version), platform_str, str(minimum))

        available_strs = [str(v) for v in available_versions[:5]]
        raise VersionNotFoundError(str(version), available_strs)

    def resolve_version_strings(self, version_strings: list[str]) -> list[SolcVersion]:
        """Resolve a list of version strings to SolcVersion objects."""
        if "all" in version_strings:
            return self.get_available_versions()

        return [
            self.get_latest_version() if v == "latest" else self.validate_version(v)
            for v in version_strings
        ]

    def get_installable_versions(self, installed_versions: list[SolcVersion]) -> list[SolcVersion]:
        """Get versions that can be installed (not already installed)."""
        available = self.get_available_versions()
        return [v for v in available if v not in installed_versions]
