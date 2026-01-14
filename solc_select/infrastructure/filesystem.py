"""Filesystem operations for solc-select."""

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
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def get_current_version(self) -> SolcVersion | None:
        """Get the currently selected version."""
        env_version = os.environ.get("SOLC_VERSION")
        if env_version:
            try:
                return SolcVersion.parse(env_version)
            except ValueError:
                return None

        global_version_file = self.config_dir / "global-version"
        if not global_version_file.exists():
            return None

        try:
            version_text = global_version_file.read_text(encoding="utf-8").strip()
            return SolcVersion.parse(version_text)
        except (OSError, ValueError):
            return None

    def set_global_version(self, version: SolcVersion) -> None:
        """Set the global version."""
        global_version_file = self.config_dir / "global-version"
        global_version_file.write_text(str(version), encoding="utf-8")

    def get_version_source(self) -> str:
        """Get the source of the current version setting."""
        if os.environ.get("SOLC_VERSION"):
            return "SOLC_VERSION"
        return (self.config_dir / "global-version").as_posix()

    def get_artifact_directory(self, version: SolcVersion) -> Path:
        """Get the directory for a version's artifacts."""
        return self.artifacts_dir / f"solc-{version}"

    def get_binary_path(self, version: SolcVersion) -> Path:
        """Get the path to a version's binary."""
        return self.get_artifact_directory(version) / f"solc-{version}"

    def cleanup_artifacts_directory(self) -> None:
        """Remove the entire artifacts directory for upgrades."""
        if self.artifacts_dir.exists():
            shutil.rmtree(self.artifacts_dir)
            self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def is_legacy_installation(self, version: SolcVersion) -> bool:
        """Check if a version uses the old installation format (file instead of directory)."""
        legacy_path = self.artifacts_dir / f"solc-{version}"
        return legacy_path.exists() and legacy_path.is_file()

    def get_installed_versions(self) -> list[SolcVersion]:
        """Get list of installed versions sorted by version number."""
        if not self.artifacts_dir.exists():
            return []

        installed = []
        for item in self.artifacts_dir.iterdir():
            if not (item.is_dir() and item.name.startswith("solc-")):
                continue
            version_str = item.name.removeprefix("solc-")
            try:
                version = SolcVersion.parse(version_str)
                if self.is_installed(version):
                    installed.append(version)
            except ValueError:
                pass

        return sorted(installed)

    def is_installed(self, version: SolcVersion) -> bool:
        """Check if a version is installed."""
        return self.get_binary_path(version).exists()

    def ensure_artifact_directory(self, version: SolcVersion) -> Path:
        """Ensure artifact directory exists for a version."""
        artifact_dir = self.get_artifact_directory(version)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        return artifact_dir
