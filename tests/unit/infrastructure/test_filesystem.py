"""Unit tests for FilesystemManager."""

import shutil

from solc_select.infrastructure.filesystem import FilesystemManager
from solc_select.models.versions import SolcVersion


class TestFilesystemManagerVersion:
    """Tests for version management functionality."""

    def test_get_current_version_from_env(self, temp_solc_select_dir, monkeypatch) -> None:
        """SOLC_VERSION environment variable takes precedence."""
        monkeypatch.setenv("SOLC_VERSION", "0.8.19")
        fm = FilesystemManager()

        version = fm.get_current_version()

        assert version == SolcVersion("0.8.19")

    def test_get_current_version_from_file(self, temp_solc_select_dir) -> None:
        """Reads version from global-version file when env var not set."""
        global_version_file = temp_solc_select_dir / "global-version"
        global_version_file.write_text("0.8.20")
        fm = FilesystemManager()

        version = fm.get_current_version()

        assert version == SolcVersion("0.8.20")

    def test_get_current_version_env_precedence(self, temp_solc_select_dir, monkeypatch) -> None:
        """Environment variable overrides file setting."""
        # Set file version
        global_version_file = temp_solc_select_dir / "global-version"
        global_version_file.write_text("0.8.20")

        # Set env version
        monkeypatch.setenv("SOLC_VERSION", "0.8.19")
        fm = FilesystemManager()

        version = fm.get_current_version()

        # Env var should win
        assert version == SolcVersion("0.8.19")

    def test_get_current_version_none_set(self, temp_solc_select_dir) -> None:
        """Returns None when no version is configured."""
        fm = FilesystemManager()
        version = fm.get_current_version()

        assert version is None

    def test_get_current_version_invalid_env_format(
        self, temp_solc_select_dir, monkeypatch
    ) -> None:
        """Returns None gracefully when env var has invalid format."""
        monkeypatch.setenv("SOLC_VERSION", "invalid-version")
        fm = FilesystemManager()

        version = fm.get_current_version()

        assert version is None

    def test_get_current_version_invalid_file_format(self, temp_solc_select_dir) -> None:
        """Returns None gracefully when file has invalid format."""
        global_version_file = temp_solc_select_dir / "global-version"
        global_version_file.write_text("not-a-version")
        fm = FilesystemManager()

        version = fm.get_current_version()

        assert version is None

    def test_set_global_version(self, temp_solc_select_dir) -> None:
        """Writes version to global-version file correctly."""
        fm = FilesystemManager()
        version = SolcVersion("0.8.21")

        fm.set_global_version(version)

        global_version_file = temp_solc_select_dir / "global-version"
        assert global_version_file.exists()
        assert global_version_file.read_text() == "0.8.21"

    def test_get_version_source_env(self, temp_solc_select_dir, monkeypatch) -> None:
        """Returns 'SOLC_VERSION' when version is from environment."""
        monkeypatch.setenv("SOLC_VERSION", "0.8.19")
        fm = FilesystemManager()

        source = fm.get_version_source()

        assert source == "SOLC_VERSION"

    def test_get_version_source_file(self, temp_solc_select_dir) -> None:
        """Returns file path when version is from file."""
        fm = FilesystemManager()
        source = fm.get_version_source()

        expected_path = (temp_solc_select_dir / "global-version").as_posix()
        assert source == expected_path


class TestFilesystemManagerInstalled:
    """Tests for installed version detection."""

    def test_get_installed_versions_multiple(self, temp_solc_select_dir) -> None:
        """Scans artifacts directory and finds multiple installed versions."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        # Create multiple version directories with binaries
        versions = ["0.8.19", "0.8.20", "0.8.21"]
        for version_str in versions:
            version_dir = artifacts_dir / f"solc-{version_str}"
            version_dir.mkdir()
            binary = version_dir / f"solc-{version_str}"
            binary.write_text("fake binary")

        fm = FilesystemManager()
        installed = fm.get_installed_versions()

        assert len(installed) == 3
        assert SolcVersion("0.8.19") in installed
        assert SolcVersion("0.8.20") in installed
        assert SolcVersion("0.8.21") in installed

    def test_get_installed_versions_filters_invalid(self, temp_solc_select_dir) -> None:
        """Skips non-version directories and invalid formats."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        # Create valid version
        valid_dir = artifacts_dir / "solc-0.8.19"
        valid_dir.mkdir()
        (valid_dir / "solc-0.8.19").write_text("binary")

        # Create invalid entries
        (artifacts_dir / "not-a-version").mkdir()
        (artifacts_dir / "solc-invalid").mkdir()
        (artifacts_dir / "random.txt").write_text("file")

        fm = FilesystemManager()
        installed = fm.get_installed_versions()

        assert len(installed) == 1
        assert installed[0] == SolcVersion("0.8.19")

    def test_get_installed_versions_sorted(self, temp_solc_select_dir) -> None:
        """Returns versions sorted by version number."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        # Create versions in random order
        versions = ["0.8.21", "0.8.19", "0.8.20", "0.8.17", "0.8.25"]
        for version_str in versions:
            version_dir = artifacts_dir / f"solc-{version_str}"
            version_dir.mkdir()
            (version_dir / f"solc-{version_str}").write_text("binary")

        fm = FilesystemManager()
        installed = fm.get_installed_versions()

        # Should be sorted
        assert installed == [
            SolcVersion("0.8.17"),
            SolcVersion("0.8.19"),
            SolcVersion("0.8.20"),
            SolcVersion("0.8.21"),
            SolcVersion("0.8.25"),
        ]

    def test_get_installed_versions_empty_dir(self, temp_solc_select_dir) -> None:
        """Returns empty list when artifacts directory is empty."""
        fm = FilesystemManager()
        installed = fm.get_installed_versions()

        assert installed == []

    def test_get_installed_versions_only_directories_with_binaries(
        self, temp_solc_select_dir
    ) -> None:
        """Only includes directories that actually contain the binary."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        # Create directory with binary
        valid_dir = artifacts_dir / "solc-0.8.19"
        valid_dir.mkdir()
        (valid_dir / "solc-0.8.19").write_text("binary")

        # Create directory without binary
        empty_dir = artifacts_dir / "solc-0.8.20"
        empty_dir.mkdir()

        fm = FilesystemManager()
        installed = fm.get_installed_versions()

        assert len(installed) == 1
        assert installed[0] == SolcVersion("0.8.19")

    def test_is_installed_true(self, temp_solc_select_dir) -> None:
        """Returns True when binary exists."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        version = SolcVersion("0.8.19")
        version_dir = artifacts_dir / "solc-0.8.19"
        version_dir.mkdir()
        binary = version_dir / "solc-0.8.19"
        binary.write_text("fake binary")

        fm = FilesystemManager()
        assert fm.is_installed(version) is True

    def test_is_installed_false(self, temp_solc_select_dir) -> None:
        """Returns False when binary doesn't exist."""
        version = SolcVersion("0.8.19")

        fm = FilesystemManager()
        assert fm.is_installed(version) is False

    def test_is_installed_false_directory_exists_but_no_binary(self, temp_solc_select_dir) -> None:
        """Returns False when directory exists but binary is missing."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        version = SolcVersion("0.8.19")
        version_dir = artifacts_dir / "solc-0.8.19"
        version_dir.mkdir()
        # Directory exists but no binary inside

        fm = FilesystemManager()
        assert fm.is_installed(version) is False


class TestFilesystemManagerPaths:
    """Tests for path construction methods."""

    def test_get_artifact_directory(self, temp_solc_select_dir) -> None:
        """Constructs correct artifact directory path."""
        version = SolcVersion("0.8.19")
        fm = FilesystemManager()

        artifact_dir = fm.get_artifact_directory(version)

        expected = temp_solc_select_dir / "artifacts" / "solc-0.8.19"
        assert artifact_dir == expected

    def test_get_binary_path(self, temp_solc_select_dir) -> None:
        """Constructs correct binary path."""
        version = SolcVersion("0.8.19")
        fm = FilesystemManager()

        binary_path = fm.get_binary_path(version)

        expected = temp_solc_select_dir / "artifacts" / "solc-0.8.19" / "solc-0.8.19"
        assert binary_path == expected

    def test_ensure_artifact_directory_creates_directory(self, temp_solc_select_dir) -> None:
        """Creates artifact directory if it doesn't exist."""
        version = SolcVersion("0.8.19")
        fm = FilesystemManager()

        artifact_dir = fm.ensure_artifact_directory(version)

        assert artifact_dir.exists()
        assert artifact_dir.is_dir()

    def test_ensure_artifact_directory_idempotent(self, temp_solc_select_dir) -> None:
        """Can be called multiple times without error."""
        version = SolcVersion("0.8.19")
        fm = FilesystemManager()

        # Call twice
        dir1 = fm.ensure_artifact_directory(version)
        dir2 = fm.ensure_artifact_directory(version)

        assert dir1 == dir2
        assert dir1.exists()


class TestFilesystemManagerLegacy:
    """Tests for legacy installation detection and cleanup."""

    def test_is_legacy_installation_file(self, temp_solc_select_dir) -> None:
        """Detects legacy installation (file instead of directory)."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        version = SolcVersion("0.8.19")
        # Legacy format: binary is directly in artifacts dir
        legacy_binary = artifacts_dir / f"solc-{version}"
        legacy_binary.write_text("legacy binary")

        fm = FilesystemManager()
        assert fm.is_legacy_installation(version) is True

    def test_is_legacy_installation_directory(self, temp_solc_select_dir) -> None:
        """Returns False for new installation format (directory)."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        version = SolcVersion("0.8.19")
        # New format: binary is in subdirectory
        version_dir = artifacts_dir / f"solc-{version}"
        version_dir.mkdir()
        (version_dir / f"solc-{version}").write_text("new binary")

        fm = FilesystemManager()
        assert fm.is_legacy_installation(version) is False

    def test_is_legacy_installation_not_exists(self, temp_solc_select_dir) -> None:
        """Returns False when nothing exists."""
        version = SolcVersion("0.8.19")

        fm = FilesystemManager()
        assert fm.is_legacy_installation(version) is False

    def test_cleanup_artifacts_directory_removes_all(self, temp_solc_select_dir) -> None:
        """Removes entire artifacts directory for upgrades."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        # Create multiple versions
        versions = ["0.8.19", "0.8.20", "0.8.21"]
        for version_str in versions:
            version_dir = artifacts_dir / f"solc-{version_str}"
            version_dir.mkdir()
            (version_dir / f"solc-{version_str}").write_text("binary")

        # Add some other files
        (artifacts_dir / "random.txt").write_text("data")

        fm = FilesystemManager()
        fm.cleanup_artifacts_directory()

        # Directory should still exist but be empty
        assert artifacts_dir.exists()
        assert list(artifacts_dir.iterdir()) == []

    def test_cleanup_artifacts_directory_recreates(self, temp_solc_select_dir) -> None:
        """Recreates artifacts directory after removal."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        # Add content
        (artifacts_dir / "test.txt").write_text("data")

        fm = FilesystemManager()
        fm.cleanup_artifacts_directory()

        # Should exist and be usable
        assert artifacts_dir.exists()
        assert artifacts_dir.is_dir()

        # Should be able to create new content
        (artifacts_dir / "new.txt").write_text("new data")
        assert (artifacts_dir / "new.txt").exists()


class TestFilesystemManagerInitialization:
    """Tests for FilesystemManager initialization."""

    def test_init_creates_directories(self, temp_solc_select_dir) -> None:
        """Initialization creates required directories."""
        artifacts_dir = temp_solc_select_dir / "artifacts"

        # Remove artifacts dir to test creation
        if artifacts_dir.exists():
            shutil.rmtree(artifacts_dir)

        # Create new instance after removal
        FilesystemManager()

        assert temp_solc_select_dir.exists()
        assert artifacts_dir.exists()

    def test_init_idempotent(self, temp_solc_select_dir) -> None:
        """Can create multiple FilesystemManager instances."""
        fm1 = FilesystemManager()
        fm2 = FilesystemManager()

        assert fm1.artifacts_dir == fm2.artifacts_dir
        assert fm1.config_dir == fm2.config_dir
