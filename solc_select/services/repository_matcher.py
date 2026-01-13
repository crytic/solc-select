"""
Repository matching service for solc-select.

This module implements the declarative matching algorithm that finds the best
repository for a requested version based on platform capabilities and repository manifests.
"""

import requests

from ..exceptions import VersionNotFoundError
from ..models import (
    Platform,
    PlatformCapability,
    PlatformIdentifier,
    RepositoryManifest,
    SolcVersion,
)
from ..repositories import (
    AlloyRepository,
    CryticRepository,
    SolcRepository,
    SoliditylangRepository,
)


class RepositoryMatcher:
    """
    Matches version requests to appropriate repositories based on platform capabilities.

    Replaces the conditional logic in CompositeRepository with declarative matching
    using repository manifests and platform capabilities.

    Example:
        capability = platform.get_capability()
        matcher = RepositoryMatcher(capability, REPOSITORY_REGISTRY, session)
        repo, target_platform = matcher.find_repository_for_version(version)
    """

    def __init__(
        self,
        platform_capability: PlatformCapability,
        manifests: list[RepositoryManifest],
        session: requests.Session,
    ):
        """Initialize the repository matcher.

        Args:
            platform_capability: Platform capability declaration
            manifests: List of repository manifests to search
            session: HTTP session for repository requests
        """
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
            exact: Whether to provide an exact match. If false, it will return a repository
                that claims to be compatible but it won't verify that the version is
                indeed available on said repository.

        Returns:
            Tuple of (repository, target_platform) where target_platform indicates
            which platform binary will be used (may differ from host if emulated)

        Raises:
            VersionNotFoundError: If no repository provides this version
        """
        runnable_platforms = self.platform_capability.get_runnable_platforms()

        # Try each runnable platform in priority order (native first)
        for target_platform in runnable_platforms:
            # Try each manifest for this platform (sorted by priority)
            for manifest in self.manifests:
                if manifest.supports_version(version, target_platform):
                    key = (manifest.repository_id, str(target_platform))
                    repo = self.repositories[key]

                    # Check if version actually exists in repository
                    if not exact or str(version) in repo.available_versions:
                        return repo, target_platform

        # No repository found
        platform_list = ", ".join(str(p) for p in runnable_platforms)
        raise VersionNotFoundError(
            str(version),
            available_versions=[],
            suggestion=f"No repository provides {version} for platforms: {platform_list}",
        )

    def get_all_available_versions(
        self,
    ) -> dict[SolcVersion, tuple[RepositoryManifest, PlatformIdentifier]]:
        """Get all versions available across all repositories and runnable platforms.

        Returns:
            Dict mapping version to (manifest, platform) tuple.
            If multiple repos provide a version, higher priority manifest wins.
        """
        available: dict[SolcVersion, tuple[RepositoryManifest, PlatformIdentifier]] = {}
        runnable_platforms = self.platform_capability.get_runnable_platforms()

        # Iterate through platforms and manifests in priority order
        for target_platform in runnable_platforms:
            for manifest in self.manifests:
                key = (manifest.repository_id, str(target_platform))

                # Skip if repository doesn't exist for this combination
                if key not in self.repositories:
                    continue

                repo = self.repositories[key]

                # Fetch versions from repository
                try:
                    versions = repo.available_versions
                    for version_str in versions:
                        try:
                            version = SolcVersion.parse(version_str)
                            # Only add if manifest supports this combination
                            if manifest.supports_version(version, target_platform):
                                # Prefer higher priority manifests (already sorted)
                                if version not in available:
                                    available[version] = (manifest, target_platform)
                        except ValueError:
                            # Skip invalid version strings
                            continue
                except requests.RequestException:
                    # Continue if one repository fails
                    continue

        return available

    def _create_repository(
        self,
        manifest: RepositoryManifest,
        platform: PlatformIdentifier,
    ) -> SolcRepository:
        """Create repository instance from manifest.

        Factory method that instantiates the appropriate repository
        based on the manifest's repository_id.

        Args:
            manifest: Repository manifest
            platform: Target platform

        Returns:
            Repository instance

        Raises:
            ValueError: If repository_id is unknown
        """
        repository_id = manifest.repository_id

        if repository_id == "soliditylang":
            platform_obj = Platform(os_type=platform.os_type, architecture=platform.architecture)
            return SoliditylangRepository(platform_obj, self.session)

        if repository_id == "crytic":
            return CryticRepository(self.session)

        if repository_id == "alloy":
            return AlloyRepository(self.session)

        raise ValueError(f"Unknown repository: {repository_id}")
