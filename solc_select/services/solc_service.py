"""
Main service facade for solc-select.

This module provides a high-level interface that coordinates between
all the other services and provides the main business logic operations.
"""

import subprocess
import sys

# Import platform_capabilities to ensure capabilities are registered
import solc_select.platform_capabilities  # noqa: F401

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
from ..models import Platform, SolcVersion
from ..repository_registry import REPOSITORY_REGISTRY
from .artifact_manager import ArtifactManager
from .platform_service import PlatformService
from .repository_matcher import RepositoryMatcher
from .version_manager import VersionManager


class SolcService:
    """Main service facade for solc-select operations."""

    def __init__(self, platform: Platform | None = None):
        """Initialize SolcService.

        Args:
            platform: Platform to use (defaults to current platform)
        """
        if platform is None:
            platform = Platform.current()

        self.platform = platform
        self.filesystem = FilesystemManager()
        self.session = create_http_session()

        # Get platform capability and create repository matcher
        self.platform_capability = platform.get_capability()
        self.repository_matcher = RepositoryMatcher(
            self.platform_capability, REPOSITORY_REGISTRY, self.session
        )

        # Initialize service dependencies
        self.version_manager = VersionManager(self.repository_matcher, platform)
        self.artifact_manager = ArtifactManager(
            self.repository_matcher,
            self.platform_capability,
            platform,
            self.session,
            self.filesystem,
        )
        self.platform_service = PlatformService(platform)

    def get_current_version(self) -> tuple[SolcVersion | None, str]:
        """Get the current version and its source.

        Returns:
            Tuple of (version, source) where source is the setting origin

        Raises:
            NoVersionSetError: If no version is currently set
            VersionNotInstalledError: If version is set but not installed
        """
        version = self.filesystem.get_current_version()
        source = self.filesystem.get_version_source()

        if version is None:
            raise NoVersionSetError()

        # Check if version is actually installed
        if not self.filesystem.is_installed(version):
            installed_versions = self.filesystem.get_installed_versions()
            installed_strs = [str(v) for v in installed_versions]
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
        """Install one or more versions.

        Args:
            version_strings: List of version strings to install
            silent: Whether to suppress output messages

        Returns:
            True if all installations succeeded, False otherwise
        """
        # Warn ARM64 users about compatibility on first install
        if self.platform.architecture == "arm64" and not silent:
            self.platform_service.warn_about_arm64_compatibility()

        if not version_strings:
            return True

        try:
            # Resolve version strings to actual versions
            versions = self.version_manager.resolve_version_strings(version_strings)

            # Check for unavailable versions
            available_versions = self.version_manager.get_available_versions()
            not_available = [v for v in versions if v not in available_versions]

            if not_available:
                not_available_strs = [str(v) for v in not_available]
                print(f"{', '.join(not_available_strs)} solc versions are not available.")
                return False

            # Install versions
            return self.artifact_manager.install_versions(versions, silent)

        except SolcSelectError as e:
            if not silent:
                print(f"Error: {e}")
            return False

    def switch_global_version(
        self, version_str: str, always_install: bool = False, silent: bool = False
    ) -> None:
        """Switch to a different global version.

        Args:
            version_str: Version string to switch to
            always_install: Whether to install the version if not present
            silent: Whether to suppress output messages

        Raises:
            VersionNotFoundError: If version is invalid or not available
            VersionNotInstalledError: If version is not installed
            InstallationError: If installation fails
        """
        # Resolve "latest" to actual version
        if version_str == "latest":
            version = self.version_manager.get_latest_version()
        else:
            version = self.version_manager.validate_version(version_str)

        # Check if version is installed
        if self.filesystem.is_installed(version):
            self.filesystem.set_global_version(version)
            if not silent:
                print(f"Switched global version to {version}")
        elif always_install:
            # Install the version first
            if self.install_versions([str(version)], silent):
                self.switch_global_version(str(version), always_install=False, silent=silent)
            else:
                raise InstallationError(str(version), "Installation failed")
        else:
            available_versions = self.version_manager.get_available_versions()
            if version in available_versions:
                raise VersionNotInstalledError(str(version))
            else:
                available_strs = [str(v) for v in available_versions[:5]]  # Show first 5
                raise VersionNotFoundError(str(version), available_strs)

    def upgrade_architecture(self) -> None:
        """Upgrade from old architecture to new directory structure.

        Raises:
            ArchitectureUpgradeError: If upgrade fails or no versions to upgrade
        """
        currently_installed = self.get_installed_versions()

        if not currently_installed:
            raise ArchitectureUpgradeError(
                "No installed versions found. Run `solc-select install --help` for more information"
            )

        # Check if we actually have old-format installations
        has_legacy = any(self.filesystem.is_legacy_installation(v) for v in currently_installed)

        if has_legacy:
            # Clean artifacts directory and reinstall
            self.filesystem.cleanup_artifacts_directory()
            version_strs = [str(v) for v in currently_installed]

            if self.install_versions(version_strs, silent=True):
                print("solc-select is now up to date! 🎉")
            else:
                raise ArchitectureUpgradeError("Failed to reinstall existing versions")
        else:
            print("solc-select is already up to date")

    def execute_solc(self, args: list[str]) -> None:
        """Execute solc with the current version.

        Args:
            args: Command line arguments to pass to solc

        Raises:
            SystemExit: With solc's exit code
        """
        # Auto-install latest if no versions installed
        if not self.get_installed_versions():
            self.switch_global_version("latest", always_install=True, silent=True)

        try:
            version, _ = self.get_current_version()
        except SolcSelectError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if version is None:
            sys.exit(1)

        binary_path = self.filesystem.get_binary_path(version)

        # Get artifact metadata for emulation info
        artifact = self.artifact_manager.create_local_artifact_metadata(version)

        # Validate binary compatibility
        try:
            emulation_prefix = self.platform_service.get_emulation_prefix(artifact)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Execute solc
        cmd = emulation_prefix + [str(binary_path)] + args

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        except FileNotFoundError:
            print(f"Error: Could not execute solc binary at {binary_path}", file=sys.stderr)
            sys.exit(1)
