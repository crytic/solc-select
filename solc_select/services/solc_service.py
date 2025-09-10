"""
Main service facade for solc-select.

This module provides a high-level interface that coordinates between
all the other services and provides the main business logic operations.
"""

import argparse
import subprocess
import sys
from typing import List, Optional, Tuple

from ..infrastructure.filesystem import FilesystemManager
from ..models import Platform, SolcVersion
from ..repositories import CompositeRepository
from .artifact_manager import ArtifactManager
from .platform_service import PlatformService
from .version_manager import VersionManager


class SolcService:
    """Main service facade for solc-select operations."""

    def __init__(self, platform: Optional[Platform] = None):
        if platform is None:
            platform = Platform.current()

        self.platform = platform
        self.filesystem = FilesystemManager()
        self.repository = CompositeRepository(platform)
        self.version_manager = VersionManager(self.repository, platform)
        self.artifact_manager = ArtifactManager(self.repository, platform)
        self.platform_service = PlatformService(platform)

    def get_current_version(self) -> Tuple[Optional[SolcVersion], str]:
        """Get the current version and its source.

        Returns:
            Tuple of (version, source) where source is the setting origin

        Raises:
            argparse.ArgumentTypeError: If version is set but not installed
        """
        version = self.filesystem.get_current_version()
        source = self.filesystem.get_version_source()

        if version is None:
            raise argparse.ArgumentTypeError(
                "No solc version set. Run `solc-select use VERSION` or set SOLC_VERSION environment variable."
            )

        # Check if version is actually installed
        installed_versions = self.artifact_manager.get_installed_versions()
        if version not in installed_versions:
            installed_strs = [str(v) for v in installed_versions]
            raise argparse.ArgumentTypeError(
                f"\nVersion '{version}' not installed (set by {source})."
                f"\nRun `solc-select install {version}`."
                f"\nOr use one of the following versions: {installed_strs}"
            )

        return version, source

    def get_installed_versions(self) -> List[SolcVersion]:
        """Get list of installed versions."""
        return self.artifact_manager.get_installed_versions()

    def get_installable_versions(self) -> List[SolcVersion]:
        """Get versions that can be installed."""
        installed = self.get_installed_versions()
        return self.version_manager.get_installable_versions(installed)

    def install_versions(self, version_strings: List[str], silent: bool = False) -> bool:
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

        except argparse.ArgumentTypeError as e:
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
            argparse.ArgumentTypeError: If version is invalid or not available
        """
        # Resolve "latest" to actual version
        if version_str == "latest":
            version = self.version_manager.get_latest_version()
        else:
            version = self.version_manager.validate_version(version_str)

        # Check if version is installed
        if self.artifact_manager.is_installed(version):
            self.filesystem.set_global_version(version)
            if not silent:
                print(f"Switched global version to {version}")
        elif always_install:
            # Install the version first
            if self.install_versions([str(version)], silent):
                self.switch_global_version(str(version), always_install=False, silent=silent)
            else:
                raise argparse.ArgumentTypeError(f"Failed to install version {version}")
        else:
            available_versions = self.version_manager.get_available_versions()
            if version in available_versions:
                raise argparse.ArgumentTypeError(f"'{version}' must be installed prior to use.")
            else:
                raise argparse.ArgumentTypeError(f"Unknown version '{version}'")

    def upgrade_architecture(self) -> None:
        """Upgrade from old architecture to new directory structure.

        Raises:
            argparse.ArgumentTypeError: If upgrade fails or no versions to upgrade
        """
        currently_installed = self.get_installed_versions()

        if not currently_installed:
            raise argparse.ArgumentTypeError(
                "Run `solc-select install --help` for more information"
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
                raise argparse.ArgumentTypeError("Failed to upgrade installations")
        else:
            print("solc-select is already up to date")

    def execute_solc(self, args: List[str]) -> None:
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
        except argparse.ArgumentTypeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if version is None:
            sys.exit(1)

        binary_path = self.filesystem.get_binary_path(version)

        # Validate binary compatibility
        try:
            self.platform_service.validate_binary_compatibility(binary_path, version)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Get emulation prefix if needed
        emulation_prefix = self.platform_service.get_emulation_prefix()

        # Execute solc
        cmd = emulation_prefix + [str(binary_path)] + args

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
        except FileNotFoundError:
            print(f"Error: Could not execute solc binary at {binary_path}", file=sys.stderr)
            sys.exit(1)
