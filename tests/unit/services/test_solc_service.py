"""Unit tests for SolcService."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from solc_select.exceptions import (
    InstallationError,
    NoVersionSetError,
    VersionNotFoundError,
    VersionNotInstalledError,
)
from solc_select.models.platforms import Platform
from solc_select.models.versions import SolcVersion
from solc_select.services.solc_service import SolcService


@pytest.fixture
def mock_dependencies():
    """Create mocked dependencies for SolcService."""
    return {
        "filesystem": Mock(),
        "version_manager": Mock(),
        "artifact_manager": Mock(),
        "platform_service": Mock(),
        "repository_matcher": Mock(),
    }


@pytest.fixture
def arm64_platform():
    """Create an ARM64 platform for testing."""
    return Platform("linux", "arm64")


@pytest.fixture
def amd64_platform():
    """Create an AMD64 platform for testing."""
    return Platform("linux", "amd64")


@pytest.fixture
def solc_service(mock_platform, mock_dependencies, monkeypatch):
    """Create SolcService with mocked dependencies."""
    # Create service (this will create real dependencies initially)
    service = SolcService(platform=mock_platform)

    # Replace dependencies with mocks
    service.filesystem = mock_dependencies["filesystem"]
    service.version_manager = mock_dependencies["version_manager"]
    service.artifact_manager = mock_dependencies["artifact_manager"]
    service.platform_service = mock_dependencies["platform_service"]
    service.repository_matcher = mock_dependencies["repository_matcher"]

    return service


class TestSolcServiceVersion:
    """Tests for version querying operations."""

    def test_get_current_version_success(self, solc_service, mock_dependencies):
        """Returns version and source when version is set and installed."""
        version = SolcVersion("0.8.19")
        mock_dependencies["filesystem"].get_current_version.return_value = version
        mock_dependencies["filesystem"].get_version_source.return_value = "SOLC_VERSION env var"
        mock_dependencies["filesystem"].is_installed.return_value = True

        result_version, result_source = solc_service.get_current_version()

        assert result_version == version
        assert result_source == "SOLC_VERSION env var"
        mock_dependencies["filesystem"].get_current_version.assert_called_once()
        mock_dependencies["filesystem"].get_version_source.assert_called_once()
        mock_dependencies["filesystem"].is_installed.assert_called_once_with(version)

    def test_get_current_version_none_set(self, solc_service, mock_dependencies):
        """Raises NoVersionSetError when no version is set."""
        mock_dependencies["filesystem"].get_current_version.return_value = None

        with pytest.raises(NoVersionSetError) as exc_info:
            solc_service.get_current_version()

        assert "No solc version set" in str(exc_info.value)

    def test_get_current_version_not_installed(self, solc_service, mock_dependencies):
        """Raises VersionNotInstalledError when version is set but not installed."""
        version = SolcVersion("0.8.19")
        installed = [SolcVersion("0.8.20"), SolcVersion("0.8.21")]
        mock_dependencies["filesystem"].get_current_version.return_value = version
        mock_dependencies[
            "filesystem"
        ].get_version_source.return_value = "~/.solc-select/global-version"
        mock_dependencies["filesystem"].is_installed.return_value = False
        mock_dependencies["filesystem"].get_installed_versions.return_value = installed

        with pytest.raises(VersionNotInstalledError) as exc_info:
            solc_service.get_current_version()

        assert "0.8.19" in str(exc_info.value)
        assert "is not installed" in str(exc_info.value)
        assert exc_info.value.version == "0.8.19"
        assert exc_info.value.installed_versions == ["0.8.20", "0.8.21"]
        assert exc_info.value.source == "~/.solc-select/global-version"

    def test_get_installed_versions(self, solc_service, mock_dependencies):
        """Returns list of installed versions from filesystem."""
        installed = [SolcVersion("0.8.19"), SolcVersion("0.8.20"), SolcVersion("0.8.21")]
        mock_dependencies["filesystem"].get_installed_versions.return_value = installed

        result = solc_service.get_installed_versions()

        assert result == installed
        mock_dependencies["filesystem"].get_installed_versions.assert_called_once()


class TestSolcServiceSwitch:
    """Tests for switching global version."""

    @pytest.mark.parametrize(
        "silent,expected_output", [(False, "Switched global version"), (True, "")]
    )
    def test_switch_already_installed(
        self, solc_service, mock_dependencies, capsys, silent, expected_output
    ):
        """Switches immediately when version is already installed."""
        version = SolcVersion("0.8.19")
        mock_dependencies["version_manager"].validate_version.return_value = version
        mock_dependencies["filesystem"].is_installed.return_value = True

        solc_service.switch_global_version("0.8.19", silent=silent)

        mock_dependencies["filesystem"].set_global_version.assert_called_once_with(version)
        captured = capsys.readouterr()
        if expected_output:
            assert expected_output in captured.out
        else:
            assert captured.out == ""

    def test_switch_not_installed_offline(self, solc_service, mock_dependencies):
        """Raises VersionNotInstalledError when version not installed and auto_install=False."""
        version = SolcVersion("0.8.19")
        available = [SolcVersion("0.8.19"), SolcVersion("0.8.20")]
        mock_dependencies["version_manager"].validate_version.return_value = version
        mock_dependencies["filesystem"].is_installed.return_value = False
        mock_dependencies["version_manager"].get_available_versions.return_value = available

        with pytest.raises(VersionNotInstalledError) as exc_info:
            solc_service.switch_global_version("0.8.19", auto_install=False)

        assert "0.8.19" in str(exc_info.value)
        assert "is not installed" in str(exc_info.value)

    def test_switch_not_installed_auto_install_default(
        self, solc_service, mock_dependencies, capsys
    ):
        """Auto-install is the default: installs then switches without an explicit flag."""
        version = SolcVersion("0.8.19")
        mock_dependencies["version_manager"].validate_version.return_value = version
        # First call: not installed, second call: installed
        mock_dependencies["filesystem"].is_installed.side_effect = [False, True]
        mock_dependencies["version_manager"].resolve_version_strings.return_value = [version]
        mock_dependencies["version_manager"].get_available_versions.return_value = [version]
        mock_dependencies["artifact_manager"].install_versions.return_value = True

        solc_service.switch_global_version("0.8.19")

        # Should call install_versions with the version (silent=False for internal call)
        mock_dependencies["version_manager"].resolve_version_strings.assert_called_once_with(
            ["0.8.19"]
        )
        mock_dependencies["artifact_manager"].install_versions.assert_called_once_with(
            [version], False
        )
        # Should set global version after installation
        mock_dependencies["filesystem"].set_global_version.assert_called_once_with(version)
        captured = capsys.readouterr()
        assert "Switched global version to 0.8.19" in captured.out

    def test_switch_invalid_version(self, solc_service, mock_dependencies):
        """Raises VersionNotFoundError when version is invalid."""
        available = [
            SolcVersion("0.8.19"),
            SolcVersion("0.8.20"),
            SolcVersion("0.8.21"),
            SolcVersion("0.8.22"),
            SolcVersion("0.8.23"),
        ]
        mock_dependencies["version_manager"].validate_version.side_effect = VersionNotFoundError(
            "0.8.99", [str(v) for v in available]
        )

        with pytest.raises(VersionNotFoundError) as exc_info:
            solc_service.switch_global_version("0.8.99")

        assert "0.8.99" in str(exc_info.value)

    def test_switch_installation_fails(self, solc_service, mock_dependencies):
        """Raises InstallationError when auto-install is enabled and installation fails."""
        version = SolcVersion("0.8.19")
        mock_dependencies["version_manager"].validate_version.return_value = version
        mock_dependencies["filesystem"].is_installed.return_value = False
        mock_dependencies["version_manager"].resolve_version_strings.return_value = [version]
        mock_dependencies["version_manager"].get_available_versions.return_value = [version]
        mock_dependencies["artifact_manager"].install_versions.return_value = False

        with pytest.raises(InstallationError) as exc_info:
            solc_service.switch_global_version("0.8.19")

        assert "0.8.19" in str(exc_info.value)
        assert "Installation failed" in str(exc_info.value)

    def test_switch_not_available_raises_version_not_found(self, solc_service, mock_dependencies):
        """Raises VersionNotFoundError when version is not available at all."""
        version = SolcVersion("0.4.3")
        available = [
            SolcVersion("0.8.19"),
            SolcVersion("0.8.20"),
            SolcVersion("0.8.21"),
            SolcVersion("0.8.22"),
            SolcVersion("0.8.23"),
        ]
        mock_dependencies["version_manager"].validate_version.return_value = version
        mock_dependencies["filesystem"].is_installed.return_value = False
        mock_dependencies["version_manager"].get_available_versions.return_value = available

        with pytest.raises(VersionNotFoundError) as exc_info:
            solc_service.switch_global_version("0.4.3", auto_install=False)

        assert "0.4.3" in str(exc_info.value)
        # Should show first 5 available versions
        assert exc_info.value.available_versions == [
            "0.8.19",
            "0.8.20",
            "0.8.21",
            "0.8.22",
            "0.8.23",
        ]


class TestSolcServiceInstall:
    """Tests for installing versions."""

    def test_install_versions_shows_arm64_warning(self, arm64_platform, mock_dependencies):
        """Calls PlatformService.warn_about_arm64_compatibility for ARM64."""
        # Create service with ARM64 platform
        service = SolcService(platform=arm64_platform)
        service.filesystem = mock_dependencies["filesystem"]
        service.version_manager = mock_dependencies["version_manager"]
        service.artifact_manager = mock_dependencies["artifact_manager"]
        service.platform_service = mock_dependencies["platform_service"]

        versions = [SolcVersion("0.8.19")]
        mock_dependencies["version_manager"].resolve_version_strings.return_value = versions
        mock_dependencies["version_manager"].get_available_versions.return_value = versions
        mock_dependencies["artifact_manager"].install_versions.return_value = True

        service.install_versions(["0.8.19"])

        mock_dependencies["platform_service"].warn_about_arm64_compatibility.assert_called_once()

    def test_install_versions_no_warning_for_amd64(self, amd64_platform, mock_dependencies):
        """Does not show warning for non-ARM64 platforms."""
        # Create service with AMD64 platform
        service = SolcService(platform=amd64_platform)
        service.filesystem = mock_dependencies["filesystem"]
        service.version_manager = mock_dependencies["version_manager"]
        service.artifact_manager = mock_dependencies["artifact_manager"]
        service.platform_service = mock_dependencies["platform_service"]

        versions = [SolcVersion("0.8.19")]
        mock_dependencies["version_manager"].resolve_version_strings.return_value = versions
        mock_dependencies["version_manager"].get_available_versions.return_value = versions
        mock_dependencies["artifact_manager"].install_versions.return_value = True

        service.install_versions(["0.8.19"])

        mock_dependencies["platform_service"].warn_about_arm64_compatibility.assert_not_called()

    def test_install_versions_silent_no_warning(self, arm64_platform, mock_dependencies):
        """Does not show warning when silent=True even on ARM64."""
        # Create service with ARM64 platform
        service = SolcService(platform=arm64_platform)
        service.filesystem = mock_dependencies["filesystem"]
        service.version_manager = mock_dependencies["version_manager"]
        service.artifact_manager = mock_dependencies["artifact_manager"]
        service.platform_service = mock_dependencies["platform_service"]

        versions = [SolcVersion("0.8.19")]
        mock_dependencies["version_manager"].resolve_version_strings.return_value = versions
        mock_dependencies["version_manager"].get_available_versions.return_value = versions
        mock_dependencies["artifact_manager"].install_versions.return_value = True

        service.install_versions(["0.8.19"], silent=True)

        mock_dependencies["platform_service"].warn_about_arm64_compatibility.assert_not_called()

    def test_install_versions_empty_list(self, solc_service, mock_dependencies):
        """Returns True immediately for empty version list."""
        result = solc_service.install_versions([])

        assert result is True
        mock_dependencies["version_manager"].resolve_version_strings.assert_not_called()
        mock_dependencies["artifact_manager"].install_versions.assert_not_called()

    def test_install_versions_success(self, solc_service, mock_dependencies):
        """Delegates to ArtifactManager for successful installation."""
        versions = [SolcVersion("0.8.19"), SolcVersion("0.8.20")]
        mock_dependencies["version_manager"].resolve_version_strings.return_value = versions
        mock_dependencies["version_manager"].get_available_versions.return_value = versions
        mock_dependencies["artifact_manager"].install_versions.return_value = True

        result = solc_service.install_versions(["0.8.19", "0.8.20"])

        assert result is True
        mock_dependencies["version_manager"].resolve_version_strings.assert_called_once_with(
            ["0.8.19", "0.8.20"]
        )
        mock_dependencies["artifact_manager"].install_versions.assert_called_once_with(
            versions, False
        )

    def test_install_versions_filters_unavailable(self, solc_service, mock_dependencies, capsys):
        """Warns about unavailable versions and returns False."""
        requested = [SolcVersion("0.8.19"), SolcVersion("0.8.99")]
        available = [SolcVersion("0.8.19"), SolcVersion("0.8.20")]
        mock_dependencies["version_manager"].resolve_version_strings.return_value = requested
        mock_dependencies["version_manager"].get_available_versions.return_value = available

        result = solc_service.install_versions(["0.8.19", "0.8.99"])

        assert result is False
        captured = capsys.readouterr()
        assert "0.8.99 solc versions are not available" in captured.out
        mock_dependencies["artifact_manager"].install_versions.assert_not_called()

    @pytest.mark.parametrize("silent", [False, True])
    def test_install_versions_error_handling(self, solc_service, mock_dependencies, capsys, silent):
        """Returns False on exception, prints error only when not silent."""
        mock_dependencies[
            "version_manager"
        ].resolve_version_strings.side_effect = VersionNotFoundError("0.8.99", [])

        result = solc_service.install_versions(["0.8.99"], silent=silent)

        assert result is False
        captured = capsys.readouterr()
        if silent:
            assert captured.out == ""
        else:
            assert "Error:" in captured.out
            assert "0.8.99" in captured.out
        mock_dependencies["artifact_manager"].install_versions.assert_not_called()


class TestSolcServiceExecute:
    """Tests for executing solc binaries."""

    @patch("subprocess.run")
    def test_execute_solc_auto_install_latest(
        self, mock_subprocess, solc_service, mock_dependencies
    ):
        """Installs latest version if none are installed."""
        version = SolcVersion("0.8.21")
        binary_path = Path("/home/user/.solc-select/artifacts/solc-0.8.21")

        # No versions installed initially
        mock_dependencies["filesystem"].get_installed_versions.return_value = []
        # After auto-install, version is set
        mock_dependencies["filesystem"].get_current_version.return_value = version
        mock_dependencies["filesystem"].get_version_source.return_value = "auto"
        mock_dependencies["filesystem"].is_installed.return_value = True
        mock_dependencies["filesystem"].get_binary_path.return_value = binary_path

        # Mock the validation and installation flow
        mock_dependencies["version_manager"].validate_version.return_value = version
        mock_dependencies["version_manager"].resolve_version_strings.return_value = [version]
        mock_dependencies["version_manager"].get_available_versions.return_value = [version]
        mock_dependencies["artifact_manager"].install_versions.return_value = True

        # Mock artifact creation
        mock_artifact = Mock()
        mock_artifact.emulation = None
        mock_dependencies[
            "artifact_manager"
        ].create_local_artifact_metadata.return_value = mock_artifact
        mock_dependencies["platform_service"].get_emulation_prefix.return_value = []

        solc_service.execute_solc(["--version"])

        # Should have called switch_global_version with "latest" and auto_install=True
        mock_dependencies["version_manager"].validate_version.assert_called_with("latest")
        mock_subprocess.assert_called_once_with([str(binary_path), "--version"], check=True)

    @patch("subprocess.run")
    def test_execute_solc_success(self, mock_subprocess, solc_service, mock_dependencies):
        """Runs subprocess with correct args for normal execution."""
        version = SolcVersion("0.8.19")
        binary_path = Path("/home/user/.solc-select/artifacts/solc-0.8.19")

        mock_dependencies["filesystem"].get_installed_versions.return_value = [version]
        mock_dependencies["filesystem"].get_current_version.return_value = version
        mock_dependencies["filesystem"].get_version_source.return_value = "global"
        mock_dependencies["filesystem"].is_installed.return_value = True
        mock_dependencies["filesystem"].get_binary_path.return_value = binary_path

        mock_artifact = Mock()
        mock_artifact.emulation = None
        mock_dependencies[
            "artifact_manager"
        ].create_local_artifact_metadata.return_value = mock_artifact
        mock_dependencies["platform_service"].get_emulation_prefix.return_value = []

        solc_service.execute_solc(["--version"])

        mock_subprocess.assert_called_once_with([str(binary_path), "--version"], check=True)

    @patch("subprocess.run")
    def test_execute_solc_with_emulation(self, mock_subprocess, solc_service, mock_dependencies):
        """Prepends emulation prefix when needed."""
        version = SolcVersion("0.8.19")
        binary_path = Path("/home/user/.solc-select/artifacts/solc-0.8.19")

        mock_dependencies["filesystem"].get_installed_versions.return_value = [version]
        mock_dependencies["filesystem"].get_current_version.return_value = version
        mock_dependencies["filesystem"].get_version_source.return_value = "global"
        mock_dependencies["filesystem"].is_installed.return_value = True
        mock_dependencies["filesystem"].get_binary_path.return_value = binary_path

        mock_artifact = Mock()
        mock_artifact.emulation = Mock()
        mock_dependencies[
            "artifact_manager"
        ].create_local_artifact_metadata.return_value = mock_artifact
        mock_dependencies["platform_service"].get_emulation_prefix.return_value = ["qemu-x86_64"]

        solc_service.execute_solc(["--version"])

        mock_subprocess.assert_called_once_with(
            ["qemu-x86_64", str(binary_path), "--version"], check=True
        )

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_execute_solc_no_version_set(
        self, mock_exit, mock_subprocess, solc_service, mock_dependencies, capsys
    ):
        """Handles NoVersionSetError gracefully."""
        # Make sys.exit raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit(1)

        mock_dependencies["filesystem"].get_installed_versions.return_value = [
            SolcVersion("0.8.19")
        ]
        mock_dependencies["filesystem"].get_current_version.return_value = None

        with pytest.raises(SystemExit):
            solc_service.execute_solc(["--version"])

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "No solc version set" in captured.err
        mock_exit.assert_called_once_with(1)
        mock_subprocess.assert_not_called()

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_execute_solc_emulation_unavailable(
        self, mock_exit, mock_subprocess, solc_service, mock_dependencies, capsys
    ):
        """Handles RuntimeError from missing emulation."""
        # Make sys.exit raise SystemExit to stop execution
        mock_exit.side_effect = SystemExit(1)

        version = SolcVersion("0.8.19")
        binary_path = Path("/home/user/.solc-select/artifacts/solc-0.8.19")

        mock_dependencies["filesystem"].get_installed_versions.return_value = [version]
        mock_dependencies["filesystem"].get_current_version.return_value = version
        mock_dependencies["filesystem"].get_version_source.return_value = "global"
        mock_dependencies["filesystem"].is_installed.return_value = True
        mock_dependencies["filesystem"].get_binary_path.return_value = binary_path

        mock_artifact = Mock()
        mock_artifact.emulation = Mock()
        mock_dependencies[
            "artifact_manager"
        ].create_local_artifact_metadata.return_value = mock_artifact
        mock_dependencies["platform_service"].get_emulation_prefix.side_effect = RuntimeError(
            "QEMU is required but not available"
        )

        with pytest.raises(SystemExit):
            solc_service.execute_solc(["--version"])

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "QEMU is required but not available" in captured.err
        mock_exit.assert_called_once_with(1)
        mock_subprocess.assert_not_called()

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_execute_solc_subprocess_error(
        self, mock_exit, mock_subprocess, solc_service, mock_dependencies
    ):
        """Propagates CalledProcessError exit code."""
        version = SolcVersion("0.8.19")
        binary_path = Path("/home/user/.solc-select/artifacts/solc-0.8.19")

        mock_dependencies["filesystem"].get_installed_versions.return_value = [version]
        mock_dependencies["filesystem"].get_current_version.return_value = version
        mock_dependencies["filesystem"].get_version_source.return_value = "global"
        mock_dependencies["filesystem"].is_installed.return_value = True
        mock_dependencies["filesystem"].get_binary_path.return_value = binary_path

        mock_artifact = Mock()
        mock_artifact.emulation = None
        mock_dependencies[
            "artifact_manager"
        ].create_local_artifact_metadata.return_value = mock_artifact
        mock_dependencies["platform_service"].get_emulation_prefix.return_value = []

        mock_subprocess.side_effect = subprocess.CalledProcessError(2, "solc")

        solc_service.execute_solc(["invalid-file.sol"])

        mock_exit.assert_called_once_with(2)

    @patch("subprocess.run")
    @patch("sys.exit")
    def test_execute_solc_binary_not_found(
        self, mock_exit, mock_subprocess, solc_service, mock_dependencies, capsys
    ):
        """Handles FileNotFoundError when binary doesn't exist."""
        version = SolcVersion("0.8.19")
        binary_path = Path("/home/user/.solc-select/artifacts/solc-0.8.19")

        mock_dependencies["filesystem"].get_installed_versions.return_value = [version]
        mock_dependencies["filesystem"].get_current_version.return_value = version
        mock_dependencies["filesystem"].get_version_source.return_value = "global"
        mock_dependencies["filesystem"].is_installed.return_value = True
        mock_dependencies["filesystem"].get_binary_path.return_value = binary_path

        mock_artifact = Mock()
        mock_artifact.emulation = None
        mock_dependencies[
            "artifact_manager"
        ].create_local_artifact_metadata.return_value = mock_artifact
        mock_dependencies["platform_service"].get_emulation_prefix.return_value = []

        mock_subprocess.side_effect = FileNotFoundError()

        solc_service.execute_solc(["--version"])

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Could not execute solc binary at" in captured.err
        assert str(binary_path) in captured.err
        mock_exit.assert_called_once_with(1)
