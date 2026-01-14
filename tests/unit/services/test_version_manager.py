"""Unit tests for VersionManager service."""

from typing import Any
from unittest.mock import Mock

import pytest

from solc_select.exceptions import (
    PlatformNotSupportedError,
    VersionNotFoundError,
    VersionResolutionError,
)
from solc_select.models.platforms import Platform
from solc_select.models.versions import SolcVersion
from solc_select.services.repository_matcher import RepositoryMatcher
from solc_select.services.version_manager import VersionManager


@pytest.fixture
def mock_repository_matcher() -> Mock:
    """Mock RepositoryMatcher for testing."""
    return Mock(spec=RepositoryMatcher)


@pytest.fixture
def platform() -> Platform:
    """Platform instance for testing."""
    return Platform("linux", "amd64")


@pytest.fixture
def version_manager(mock_repository_matcher: Mock, platform: Platform) -> VersionManager:
    """VersionManager instance with mocked dependencies."""
    return VersionManager(mock_repository_matcher, platform)


@pytest.fixture
def sample_available_versions() -> dict[SolcVersion, tuple[Any, Any]]:
    """Sample version dictionary for testing."""
    return {
        SolcVersion("0.8.17"): (Mock(), Mock()),
        SolcVersion("0.8.18"): (Mock(), Mock()),
        SolcVersion("0.8.19"): (Mock(), Mock()),
        SolcVersion("0.8.20"): (Mock(), Mock()),
        SolcVersion("0.8.21"): (Mock(), Mock()),
    }


class TestVersionManagerValidation:
    """Tests for version validation functionality."""

    def test_validate_version_valid_format(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that valid version strings are parsed successfully."""
        # Arrange
        mock_repository_matcher.find_repository_for_version.return_value = (Mock(), Mock())
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act
        result = version_manager.validate_version("0.8.19")

        # Assert
        assert isinstance(result, SolcVersion)
        assert str(result) == "0.8.19"
        mock_repository_matcher.find_repository_for_version.assert_called_once()

    def test_validate_version_latest_keyword(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that 'latest' keyword resolves to highest available version."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act
        result = version_manager.validate_version("latest")

        # Assert
        assert result == SolcVersion("0.8.21")

    def test_validate_version_invalid_format(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that invalid version format raises VersionNotFoundError with helpful message."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act & Assert
        with pytest.raises(VersionNotFoundError) as exc_info:
            version_manager.validate_version("invalid.version")

        # Verify error details
        error = exc_info.value
        assert error.version == "invalid.version"
        assert len(error.available_versions) == 5
        assert error.suggestion == "Check the version format (e.g., '0.8.19')"
        assert "Check the version format" in str(error)

    def test_validate_version_not_found(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that non-existent version raises VersionNotFoundError."""
        # Arrange
        mock_repository_matcher.find_repository_for_version.side_effect = VersionNotFoundError(
            "99.99.99"
        )
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act & Assert
        with pytest.raises(VersionNotFoundError) as exc_info:
            version_manager.validate_version("99.99.99")

        # Verify error includes suggestion for latest version
        error = exc_info.value
        assert error.version == "99.99.99"
        assert error.suggestion == "'0.8.21' is the latest available version"

    def test_validate_version_platform_not_supported(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that version below platform minimum raises PlatformNotSupportedError."""
        # Arrange
        mock_repository_matcher.find_repository_for_version.side_effect = VersionNotFoundError(
            "0.4.0"
        )
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act & Assert
        with pytest.raises(PlatformNotSupportedError) as exc_info:
            version_manager.validate_version("0.4.0")

        # Verify error details
        error = exc_info.value
        assert error.version == "0.4.0"
        assert error.platform == "linux-amd64"
        assert error.min_version == "0.8.17"
        assert "Minimum supported version" in str(error)

    def test_validate_version_helpful_error_messages(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that error messages include helpful suggestions and available versions."""
        # Arrange
        mock_repository_matcher.find_repository_for_version.side_effect = VersionNotFoundError(
            "0.8.22"
        )
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act & Assert - version above latest
        with pytest.raises(VersionNotFoundError) as exc_info:
            version_manager.validate_version("0.8.22")

        error = exc_info.value
        assert error.version == "0.8.22"
        assert error.suggestion == "'0.8.21' is the latest available version"

    def test_validate_version_no_versions_available(
        self, version_manager: VersionManager, mock_repository_matcher: Mock
    ) -> None:
        """Test handling when no versions are available at all."""
        # Arrange
        mock_repository_matcher.find_repository_for_version.side_effect = VersionNotFoundError(
            "0.8.19"
        )
        mock_repository_matcher.get_all_available_versions.return_value = {}

        # Act & Assert
        with pytest.raises(VersionNotFoundError) as exc_info:
            version_manager.validate_version("0.8.19")

        error = exc_info.value
        assert error.version == "0.8.19"
        assert error.available_versions == []

    def test_validate_version_latest_no_versions_available(
        self, version_manager: VersionManager, mock_repository_matcher: Mock
    ) -> None:
        """Test that 'latest' with no versions raises VersionResolutionError."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = {}

        # Act & Assert
        with pytest.raises(VersionResolutionError) as exc_info:
            version_manager.validate_version("latest")

        error = exc_info.value
        assert error.requested == "latest"
        assert "No versions available" in error.reason


class TestVersionManagerResolution:
    """Tests for version resolution functionality."""

    def test_resolve_all_keyword(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that 'all' keyword returns all available versions."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act
        result = version_manager.resolve_version_strings(["all"])

        # Assert
        assert len(result) == 5
        assert SolcVersion("0.8.17") in result
        assert SolcVersion("0.8.21") in result
        # Should be sorted
        assert result == sorted(result)

    def test_resolve_latest_keyword(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that 'latest' is resolved in list."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions
        mock_repository_matcher.find_repository_for_version.return_value = (Mock(), Mock())

        # Act
        result = version_manager.resolve_version_strings(["latest"])

        # Assert
        assert len(result) == 1
        assert result[0] == SolcVersion("0.8.21")

    def test_resolve_mixed_versions(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test resolving mixed list with 'latest', explicit versions."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions
        mock_repository_matcher.find_repository_for_version.return_value = (Mock(), Mock())

        # Act
        result = version_manager.resolve_version_strings(["0.8.19", "latest", "0.8.20"])

        # Assert
        assert len(result) == 3
        assert result[0] == SolcVersion("0.8.19")
        assert result[1] == SolcVersion("0.8.21")  # latest
        assert result[2] == SolcVersion("0.8.20")

    def test_resolve_empty_list(
        self, version_manager: VersionManager, mock_repository_matcher: Mock
    ) -> None:
        """Test that empty list returns empty list."""
        # Act
        result = version_manager.resolve_version_strings([])

        # Assert
        assert result == []
        # Should not make any repository calls
        mock_repository_matcher.get_all_available_versions.assert_not_called()

    def test_resolve_duplicate_versions(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test resolving list with duplicate versions."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions
        mock_repository_matcher.find_repository_for_version.return_value = (Mock(), Mock())

        # Act
        result = version_manager.resolve_version_strings(["0.8.19", "0.8.19", "0.8.20"])

        # Assert
        assert len(result) == 3
        # Duplicates are preserved (caller's responsibility to handle)
        assert result[0] == SolcVersion("0.8.19")
        assert result[1] == SolcVersion("0.8.19")
        assert result[2] == SolcVersion("0.8.20")


class TestVersionManagerAvailability:
    """Tests for version availability functionality."""

    def test_get_latest_version_success(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that get_latest_version returns the highest version."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act
        result = version_manager.get_latest_version()

        # Assert
        assert result == SolcVersion("0.8.21")

    def test_get_latest_version_no_versions(
        self, version_manager: VersionManager, mock_repository_matcher: Mock
    ) -> None:
        """Test that get_latest_version raises ValueError when no versions available."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = {}

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            version_manager.get_latest_version()

        assert "No versions available" in str(exc_info.value)

    def test_get_available_versions_sorted(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that get_available_versions returns sorted list."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions

        # Act
        result = version_manager.get_available_versions()

        # Assert
        assert len(result) == 5
        assert result == sorted(result)
        assert result[0] == SolcVersion("0.8.17")
        assert result[-1] == SolcVersion("0.8.21")

    def test_get_available_versions_empty(
        self, version_manager: VersionManager, mock_repository_matcher: Mock
    ) -> None:
        """Test that get_available_versions handles empty repository."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = {}

        # Act
        result = version_manager.get_available_versions()

        # Assert
        assert result == []

    def test_get_installable_versions(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that get_installable_versions filters out installed versions."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions
        installed: list[SolcVersion] = [SolcVersion("0.8.19"), SolcVersion("0.8.20")]

        # Act
        result = version_manager.get_installable_versions(installed)

        # Assert
        assert len(result) == 3
        assert SolcVersion("0.8.19") not in result
        assert SolcVersion("0.8.20") not in result
        assert SolcVersion("0.8.17") in result
        assert SolcVersion("0.8.18") in result
        assert SolcVersion("0.8.21") in result

    def test_get_installable_versions_all_installed(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that get_installable_versions returns empty when all are installed."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions
        installed = list(sample_available_versions.keys())

        # Act
        result = version_manager.get_installable_versions(installed)

        # Assert
        assert result == []

    def test_get_installable_versions_none_installed(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
    ) -> None:
        """Test that get_installable_versions returns all when none installed."""
        # Arrange
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions
        installed: list[SolcVersion] = []

        # Act
        result = version_manager.get_installable_versions(installed)

        # Assert
        assert len(result) == 5
        assert result == sorted(sample_available_versions.keys())


class TestVersionManagerIntegration:
    """Integration tests combining multiple VersionManager operations."""

    @pytest.mark.parametrize(
        "version_string,expected",
        [
            ("0.8.19", SolcVersion("0.8.19")),
            ("0.8.20", SolcVersion("0.8.20")),
            ("0.8.21", SolcVersion("0.8.21")),
        ],
    )
    def test_validate_version_parametrized(
        self,
        version_manager: VersionManager,
        mock_repository_matcher: Mock,
        sample_available_versions: dict[SolcVersion, tuple[Any, Any]],
        version_string: str,
        expected: SolcVersion,
    ) -> None:
        """Test validation of multiple versions using parametrization."""
        mock_repository_matcher.get_all_available_versions.return_value = sample_available_versions
        mock_repository_matcher.find_repository_for_version.return_value = (Mock(), Mock())

        result = version_manager.validate_version(version_string)

        assert result == expected
