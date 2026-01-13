"""Repository declaration models."""

from dataclasses import dataclass

from ..platform_capabilities import PlatformIdentifier
from .versions import SolcVersion, VersionRange


@dataclass(frozen=True)
class PlatformSupport:
    """Declares what versions a repository provides for a specific platform.

    Example: Soliditylang provides linux-amd64 binaries from version 0.4.10+
    """

    platform: PlatformIdentifier
    version_range: VersionRange

    def supports(self, version: SolcVersion, target_platform: PlatformIdentifier) -> bool:
        """Check if this support matches version + platform.

        Args:
            version: Version to check
            target_platform: Platform to check

        Returns:
            True if this support provides the version for the platform
        """
        return self.platform == target_platform and self.version_range.contains(version)


@dataclass
class RepositoryManifest:
    """Declarative manifest of what a repository provides.

    Example:
        SOLIDITYLANG_MANIFEST = RepositoryManifest(
            repository_id="soliditylang",
            base_url="https://binaries.soliditylang.org",
            platform_supports=[...],
            priority=100,
        )
    """

    repository_id: str  # 'soliditylang', 'crytic', 'alloy'
    base_url: str
    platform_supports: list[PlatformSupport]
    priority: int = 50  # Higher = checked first (100=primary, 50=fallback, 10=legacy)

    def supports_version(self, version: SolcVersion, platform: PlatformIdentifier) -> bool:
        """Check if this repository can provide version for platform.

        Args:
            version: Version to check
            platform: Platform to check

        Returns:
            True if repository provides this version/platform combo
        """
        return any(ps.supports(version, platform) for ps in self.platform_supports)
