"""Repository matching service for solc-select."""

import requests

from ..exceptions import VersionNotFoundError
from ..models.platforms import Platform
from ..models.repositories import RepositoryManifest
from ..models.versions import SolcVersion
from ..platform_capabilities import PlatformCapability, PlatformIdentifier
from ..repositories import (
    AlloyRepository,
    CryticRepository,
    SolcRepository,
    SoliditylangRepository,
)


class RepositoryMatcher:
    """Matches version requests to appropriate repositories based on platform capabilities."""

    def __init__(
        self,
        platform_capability: PlatformCapability,
        manifests: list[RepositoryManifest],
        session: requests.Session,
    ):
        self.platform_capability = platform_capability
        # Sort manifests by priority (highest first)
        self.manifests = sorted(manifests, key=lambda m: m.priority, reverse=True)
        self.session = session

        # Pre-compute all repositories for runnable platforms
        self.repositories: dict[tuple[str, str], SolcRepository] = {}
        runnable_platforms = platform_capability.get_runnable_platforms()

        for manifest in manifests:
            for platform in runnable_platforms:
                # Only create if manifest supports this platform
                if any(ps.platform == platform for ps in manifest.platform_supports):
                    repo = self._create_repository(manifest, platform)
                    key = (manifest.repository_id, str(platform))
                    self.repositories[key] = repo

    def find_repository_for_version(
        self,
        version: SolcVersion,
        exact: bool = True,
    ) -> tuple[SolcRepository, PlatformIdentifier]:
        """Find the best repository for a version.

        Uses declarative matching algorithm:
        1. Get runnable platforms from capability (native first, then emulated)
        2. For each runnable platform:
           3. For each manifest (sorted by priority):
              4. If manifest supports (version, platform) AND version exists in repository:
                 5. Return (repository, target_platform)

        Args:
            version: Version to find
            exact: Whether to verify the version exists in the repository

        Returns:
            Tuple of (repository, target_platform) where target_platform indicates
            which platform binary will be used (may differ from host if emulated)

        Raises:
            VersionNotFoundError: If no repository provides this version
        """
        runnable_platforms = self.platform_capability.get_runnable_platforms()

        for target_platform in runnable_platforms:
            for manifest in self.manifests:
                if manifest.supports_version(version, target_platform):
                    key = (manifest.repository_id, str(target_platform))
                    repo = self.repositories[key]

                    if not exact or str(version) in repo.available_versions:
                        return repo, target_platform

        platform_list = ", ".join(map(str, runnable_platforms))
        raise VersionNotFoundError(
            str(version),
            available_versions=[],
            suggestion=f"No repository provides {version} for platforms: {platform_list}",
        )

    def get_all_available_versions(
        self,
    ) -> dict[SolcVersion, tuple[RepositoryManifest, PlatformIdentifier]]:
        """Get all versions available across all repositories and runnable platforms."""
        available: dict[SolcVersion, tuple[RepositoryManifest, PlatformIdentifier]] = {}
        runnable_platforms = self.platform_capability.get_runnable_platforms()

        for target_platform in runnable_platforms:
            for manifest in self.manifests:
                key = (manifest.repository_id, str(target_platform))

                if key not in self.repositories:
                    continue

                repo = self.repositories[key]

                try:
                    versions = repo.available_versions
                    for version_str in versions:
                        try:
                            version = SolcVersion.parse(version_str)
                            if manifest.supports_version(version, target_platform):
                                if version not in available:
                                    available[version] = (manifest, target_platform)
                        except ValueError:
                            continue
                except requests.RequestException:
                    continue

        return available

    def _create_repository(
        self,
        manifest: RepositoryManifest,
        platform: PlatformIdentifier,
    ) -> SolcRepository:
        """Create repository instance from manifest."""
        repository_id = manifest.repository_id

        if repository_id == "soliditylang":
            platform_obj = Platform(platform.os_type, platform.architecture)
            return SoliditylangRepository(platform_obj, self.session)

        if repository_id == "crytic":
            return CryticRepository(self.session)

        if repository_id == "alloy":
            return AlloyRepository(self.session)

        raise ValueError(f"Unknown repository: {repository_id}")
