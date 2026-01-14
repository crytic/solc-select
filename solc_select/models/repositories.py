"""Repository declaration models."""

from dataclasses import dataclass

from ..platform_capabilities import PlatformIdentifier
from .versions import SolcVersion, VersionRange


@dataclass(frozen=True)
class PlatformSupport:
    """Declares what versions a repository provides for a specific platform."""

    platform: PlatformIdentifier
    version_range: VersionRange

    def supports(self, version: SolcVersion, target_platform: PlatformIdentifier) -> bool:
        """Check if this support matches version + platform."""
        return self.platform == target_platform and self.version_range.contains(version)


@dataclass
class RepositoryManifest:
    """Declarative manifest of what a repository provides."""

    repository_id: str  # 'soliditylang', 'crytic', 'alloy'
    base_url: str
    platform_supports: list[PlatformSupport]
    priority: int = 50  # Higher = checked first (100=primary, 50=fallback, 10=legacy)

    def supports_version(self, version: SolcVersion, platform: PlatformIdentifier) -> bool:
        """Check if this repository can provide version for platform."""
        return any(ps.supports(version, platform) for ps in self.platform_supports)
