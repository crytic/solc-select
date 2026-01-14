"""Main service facade for solc-select."""

import subprocess
import sys

from ..exceptions import (
    ArchitectureUpgradeError,
    InstallationError,
    NoVersionSetError,
    SolcSelectError,
    VersionNotFoundError,
    VersionNotInstalledError,
)
from ..infrastructure.filesystem import FilesystemManager
from ..infrastructure.http_client import create_http_session
from ..models.platforms import Platform
from ..models.versions import SolcVersion
from ..repository_registry import REPOSITORY_REGISTRY
from .artifact_manager import ArtifactManager
from .platform_service import PlatformService
from .repository_matcher import RepositoryMatcher
from .version_manager import VersionManager


class SolcService:
    """Main service facade for solc-select operations."""

    def __init__(self, platform: Platform | None = None):
        if platform is None:
            platform = Platform.current()

        self.platform = platform
        self.filesystem = FilesystemManager()
        self.session = create_http_session()

        self.platform_capability = platform.get_capability()
        self.repository_matcher = RepositoryMatcher(
            self.platform_capability, REPOSITORY_REGISTRY, self.session
        )

        self.version_manager = VersionManager(self.repository_matcher, platform)
        self.artifact_manager = ArtifactManager(
            self.repository_matcher,
            self.platform_capability,
            platform,
            self.session,
            self.filesystem,
        )
        self.platform_service = PlatformService(platform)

    def get_current_version(self) -> tuple[SolcVersion, str]:
        """Get the current version and its source."""
        version = self.filesystem.get_current_version()
        source = self.filesystem.get_version_source()

        if version is None:
            raise NoVersionSetError()

        if not self.filesystem.is_installed(version):
            installed_strs = [str(v) for v in self.filesystem.get_installed_versions()]
            raise VersionNotInstalledError(str(version), installed_strs, source)

        return version, source

    def get_installed_versions(self) -> list[SolcVersion]:
        """Get list of installed versions."""
        return self.filesystem.get_installed_versions()

    def get_installable_versions(self) -> list[SolcVersion]:
        """Get versions that can be installed."""
        installed = self.get_installed_versions()
        return self.version_manager.get_installable_versions(installed)

    def install_versions(self, version_strings: list[str], silent: bool = False) -> bool:
        """Install one or more versions."""
        if self.platform.architecture == "arm64" and not silent:
            self.platform_service.warn_about_arm64_compatibility()

        if not version_strings:
            return True

        try:
            versions = self.version_manager.resolve_version_strings(version_strings)
            available_versions = self.version_manager.get_available_versions()
            not_available = [v for v in versions if v not in available_versions]

            if not_available:
                not_available_strs = [str(v) for v in not_available]
                print(f"{', '.join(not_available_strs)} solc versions are not available.")
                return False

            return self.artifact_manager.install_versions(versions, silent)

        except SolcSelectError as e:
            if not silent:
                print(f"Error: {e}")
            return False

    def switch_global_version(
        self, version_str: str, always_install: bool = False, silent: bool = False
    ) -> None:
        """Switch to a different global version."""
        version = self.version_manager.validate_version(version_str)

        if self.filesystem.is_installed(version):
            self.filesystem.set_global_version(version)
            if not silent:
                print(f"Switched global version to {version}")
        elif always_install:
            if self.install_versions([str(version)], silent):
                self.switch_global_version(str(version), always_install=False, silent=silent)
            else:
                raise InstallationError(str(version), "Installation failed")
        else:
            available_versions = self.version_manager.get_available_versions()
            if version in available_versions:
                raise VersionNotInstalledError(str(version))
            else:
                available_strs = [str(v) for v in available_versions[:5]]
                raise VersionNotFoundError(str(version), available_strs)

    def upgrade_architecture(self) -> None:
        """Upgrade from old architecture to new directory structure."""
        currently_installed = self.get_installed_versions()

        if not currently_installed:
            raise ArchitectureUpgradeError(
                "No installed versions found. Run `solc-select install --help` for more information"
            )

        has_legacy = any(self.filesystem.is_legacy_installation(v) for v in currently_installed)

        if has_legacy:
            self.filesystem.cleanup_artifacts_directory()
            version_strs = [str(v) for v in currently_installed]

            if self.install_versions(version_strs, silent=True):
                print("solc-select is now up to date!")
            else:
                raise ArchitectureUpgradeError("Failed to reinstall existing versions")
        else:
            print("solc-select is already up to date")

    def execute_solc(self, args: list[str]) -> None:
        """Execute solc with the current version."""
        if not self.get_installed_versions():
            self.switch_global_version("latest", always_install=True, silent=True)

        try:
            version, _ = self.get_current_version()
        except SolcSelectError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        binary_path = self.filesystem.get_binary_path(version)
        artifact = self.artifact_manager.create_local_artifact_metadata(version)

        try:
            emulation_prefix = self.platform_service.get_emulation_prefix(artifact)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        cmd = emulation_prefix + [str(binary_path)] + args

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        except FileNotFoundError:
            print(f"Error: Could not execute solc binary at {binary_path}", file=sys.stderr)
            sys.exit(1)
