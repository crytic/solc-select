"""
Filesystem operations for solc-select.

This module handles file system operations including version storage,
configuration management, and directory operations.
"""

import os
import shutil
from pathlib import Path

from ..constants import ARTIFACTS_DIR, SOLC_SELECT_DIR
from ..models.versions import SolcVersion


class FilesystemManager:
    """Manages filesystem operations for solc-select."""

    def __init__(self) -> None:
        self.artifacts_dir = ARTIFACTS_DIR
        self.config_dir = SOLC_SELECT_DIR
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure required directories exist."""
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def get_current_version(self) -> SolcVersion | None:
        """Get the currently selected version.

        Returns:
            Currently selected version or None if not set
        """
        # Check environment variable first
        env_version = os.environ.get("SOLC_VERSION")
        if env_version:
            try:
                return SolcVersion.parse(env_version)
            except ValueError:
                return None

        # Check global version file
        global_version_file = self.config_dir / "global-version"
        if global_version_file.exists():
            try:
                with open(global_version_file, encoding="utf-8") as f:
                    version_str = f.read().strip()
                    return SolcVersion.parse(version_str)
            except (OSError, ValueError):
                return None

        return None

    def set_global_version(self, version: SolcVersion) -> None:
        """Set the global version.

        Args:
            version: Version to set as global
        """
        global_version_file = self.config_dir / "global-version"
        with open(global_version_file, "w", encoding="utf-8") as f:
            f.write(str(version))

    def get_version_source(self) -> str:
        """Get the source of the current version setting.

        Returns:
            Source description (environment variable or file path)
        """
        if os.environ.get("SOLC_VERSION"):
            return "SOLC_VERSION"

        global_version_file = self.config_dir / "global-version"
        return global_version_file.as_posix()

    def get_artifact_directory(self, version: SolcVersion) -> Path:
        """Get the directory for a version's artifacts.

        Args:
            version: Version to get directory for

        Returns:
            Path to the artifact directory
        """
        return self.artifacts_dir / f"solc-{version}"

    def get_binary_path(self, version: SolcVersion) -> Path:
        """Get the path to a version's binary.

        Args:
            version: Version to get binary path for

        Returns:
            Path to the binary executable
        """
        artifact_dir = self.get_artifact_directory(version)
        return artifact_dir / f"solc-{version}"

    def cleanup_artifacts_directory(self) -> None:
        """Remove the entire artifacts directory for upgrades."""
        if self.artifacts_dir.exists():
            shutil.rmtree(self.artifacts_dir)
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def is_legacy_installation(self, version: SolcVersion) -> bool:
        """Check if a version uses the old installation format.

        Args:
            version: Version to check

        Returns:
            True if using legacy format, False otherwise
        """
        # Legacy format: artifacts/solc-{version} (file instead of directory)
        legacy_path = self.artifacts_dir / f"solc-{version}"
        return legacy_path.exists() and legacy_path.is_file()

    def get_installed_versions(self) -> list[SolcVersion]:
        """Get list of installed versions by scanning artifacts directory.

        Returns:
            List of installed SolcVersion objects sorted by version
        """
        if not self.artifacts_dir.exists():
            return []

        installed = []
        for item in self.artifacts_dir.iterdir():
            if item.is_dir() and item.name.startswith("solc-"):
                version_str = item.name.replace("solc-", "")
                try:
                    version = SolcVersion.parse(version_str)
                    if self.is_installed(version):
                        installed.append(version)
                except ValueError:
                    # Skip invalid version directories
                    continue

        installed.sort()
        return installed

    def is_installed(self, version: SolcVersion) -> bool:
        """Check if a version is installed.

        Args:
            version: Version to check

        Returns:
            True if installed and binary exists, False otherwise
        """
        binary_path = self.get_binary_path(version)
        return binary_path.exists()

    def ensure_artifact_directory(self, version: SolcVersion) -> Path:
        """Ensure artifact directory exists for a version.

        Args:
            version: Version to create directory for

        Returns:
            Path to the artifact directory
        """
        artifact_dir = self.get_artifact_directory(version)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir
