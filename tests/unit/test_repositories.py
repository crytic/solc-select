"""Unit tests for SolcRepository implementations."""

from unittest.mock import Mock

import pytest
import requests

from solc_select.constants import (
    ALLOY_SOLC_ARTIFACTS,
    CRYTIC_SOLC_ARTIFACTS,
)
from solc_select.models.platforms import Platform
from solc_select.models.versions import SolcVersion
from solc_select.repositories import (
    AlloyRepository,
    CryticRepository,
    SolcRepository,
    SoliditylangRepository,
)


class TestSolcRepositoryVersions:
    """Tests for available_versions property and version parsing."""

    def test_available_versions_parses_json(self, mock_session: Mock) -> None:
        """Test that available_versions extracts versions from list.json."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {
                "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
                "0.8.20": "solc-linux-amd64-v0.8.20+commit.def456",
            },
            "builds": [],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act
        versions = repository.available_versions

        # Assert
        assert "0.8.19" in versions
        assert "0.8.20" in versions
        assert versions["0.8.19"] == "solc-linux-amd64-v0.8.19+commit.abc123"
        assert versions["0.8.20"] == "solc-linux-amd64-v0.8.20+commit.def456"
        mock_session.get.assert_called_once_with("https://example.com/list.json")

    def test_available_versions_filters_prerelease(self, mock_session: Mock) -> None:
        """Test that available_versions includes prerelease versions in releases."""
        # Arrange - Prerelease versions ARE included in the releases dict
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {
                "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
                "0.8.20-nightly.2023.1.1": "solc-linux-amd64-v0.8.20-nightly+commit.xyz",
            },
            "builds": [],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act
        versions = repository.available_versions

        # Assert - Repository returns releases dict as-is
        assert "0.8.19" in versions
        assert "0.8.20-nightly.2023.1.1" in versions

    def test_available_versions_caches(self, mock_session: Mock) -> None:
        """Test that lru_cache works and same object is returned."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {"0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123"},
            "builds": [],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act
        versions1 = repository.available_versions
        versions2 = repository.available_versions

        # Assert - Same object reference (cached)
        assert versions1 is versions2
        # Session.get should only be called once due to caching
        mock_session.get.assert_called_once()

    def test_available_versions_network_error(self, mock_session: Mock) -> None:
        """Test that network errors raise HTTPError."""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act & Assert
        with pytest.raises(requests.HTTPError):
            _ = repository.available_versions


class TestSolcRepositoryChecksums:
    """Tests for get_checksums method."""

    def test_get_checksums_sha256_only(self, mock_session: Mock) -> None:
        """Test extracting SHA256 checksum only."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {"0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123"},
            "builds": [
                {
                    "version": "0.8.19",
                    "sha256": "0xabc123def456",
                    "path": "solc-linux-amd64-v0.8.19+commit.abc123",
                }
            ],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act
        sha256, keccak256 = repository.get_checksums(SolcVersion("0.8.19"))

        # Assert
        assert sha256 == "abc123def456"
        assert keccak256 is None

    def test_get_checksums_sha256_and_keccak256(self, mock_session: Mock) -> None:
        """Test extracting both SHA256 and Keccak256 checksums."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {"0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123"},
            "builds": [
                {
                    "version": "0.8.19",
                    "sha256": "0xabc123def456",
                    "keccak256": "0x789ghi012jkl",
                    "path": "solc-linux-amd64-v0.8.19+commit.abc123",
                }
            ],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act
        sha256, keccak256 = repository.get_checksums(SolcVersion("0.8.19"))

        # Assert
        assert sha256 == "abc123def456"
        assert keccak256 == "789ghi012jkl"

    def test_get_checksums_removes_0x_prefix(self, mock_session: Mock) -> None:
        """Test that 0x prefix is stripped from checksums."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {"0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123"},
            "builds": [
                {
                    "version": "0.8.19",
                    "sha256": "0xfedcba987654",
                    "keccak256": "0x123456789abc",
                    "path": "solc-linux-amd64-v0.8.19+commit.abc123",
                }
            ],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act
        sha256, keccak256 = repository.get_checksums(SolcVersion("0.8.19"))

        # Assert
        assert not sha256.startswith("0x")
        assert keccak256 is not None
        assert not keccak256.startswith("0x")
        assert sha256 == "fedcba987654"
        assert keccak256 == "123456789abc"

    def test_get_checksums_version_not_found(self, mock_session: Mock) -> None:
        """Test that ValueError is raised when version not found."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {"0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123"},
            "builds": [
                {
                    "version": "0.8.19",
                    "sha256": "0xabc123",
                    "path": "solc-linux-amd64-v0.8.19+commit.abc123",
                }
            ],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act & Assert
        with pytest.raises(ValueError, match=r"Unable to retrieve checksum for 0\.8\.20"):
            repository.get_checksums(SolcVersion("0.8.20"))

    def test_get_checksums_missing_checksum(self, mock_session: Mock) -> None:
        """Test that ValueError is raised when checksum is missing."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {"0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123"},
            "builds": [
                {
                    "version": "0.8.19",
                    "sha256": None,  # Missing checksum
                    "path": "solc-linux-amd64-v0.8.19+commit.abc123",
                }
            ],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act & Assert
        with pytest.raises(ValueError, match=r"Unable to retrieve checksum for 0\.8\.19"):
            repository.get_checksums(SolcVersion("0.8.19"))

    def test_get_checksums_filters_prerelease(self, mock_session: Mock) -> None:
        """Test that prerelease builds are filtered out when getting checksums."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {"0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123"},
            "builds": [
                {
                    "version": "0.8.19",
                    "sha256": "0x111222333",
                    "path": "solc-linux-amd64-v0.8.19-nightly+commit.xyz",
                    "prerelease": "nightly",
                },
                {
                    "version": "0.8.19",
                    "sha256": "0xabc123def456",
                    "path": "solc-linux-amd64-v0.8.19+commit.abc123",
                },
            ],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
        )

        # Act
        sha256, _ = repository.get_checksums(SolcVersion("0.8.19"))

        # Assert - Should get the non-prerelease checksum
        assert sha256 == "abc123def456"


class TestSolcRepositoryLatest:
    """Tests for latest_version property."""

    def test_latest_version_from_field(self, mock_session: Mock) -> None:
        """Test that latest_version uses latestRelease field when available."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "latestRelease": "0.8.21",
            "releases": {
                "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
                "0.8.20": "solc-linux-amd64-v0.8.20+commit.def456",
                "0.8.21": "solc-linux-amd64-v0.8.21+commit.ghi789",
            },
            "builds": [],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
            has_latest_release=True,
        )

        # Act
        latest = repository.latest_version

        # Assert
        assert latest == SolcVersion("0.8.21")

    def test_latest_version_from_max(self, mock_session: Mock) -> None:
        """Test that latest_version computes max when no latestRelease field."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {
                "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
                "0.8.20": "solc-linux-amd64-v0.8.20+commit.def456",
                "0.8.18": "solc-linux-amd64-v0.8.18+commit.ghi789",
            },
            "builds": [],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
            has_latest_release=False,
        )

        # Act
        latest = repository.latest_version

        # Assert
        assert latest == SolcVersion("0.8.20")

    def test_latest_version_no_versions(self, mock_session: Mock) -> None:
        """Test that ValueError is raised when no versions available."""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            "releases": {},
            "builds": [],
        }
        mock_session.get.return_value = mock_response

        repository = SolcRepository(
            base_url="https://example.com/",
            list_url="https://example.com/list.json",
            session=mock_session,
            has_latest_release=False,
        )

        # Act & Assert
        with pytest.raises(ValueError, match="No versions available"):
            _ = repository.latest_version


class TestSolcRepositoryFactory:
    """Tests for repository factory functions."""

    @pytest.mark.parametrize(
        "platform_args,expected_url_part",
        [
            (("linux", "amd64"), "linux-amd64"),
            (("darwin", "arm64"), "macosx-amd64"),  # ARM64 uses x86 binaries via emulation
        ],
    )
    def test_soliditylang_repository_creation(
        self, mock_session: Mock, platform_args: tuple[str, str], expected_url_part: str
    ) -> None:
        """SoliditylangRepository creates correct URLs for different platforms."""
        repository = SoliditylangRepository(Platform(*platform_args), mock_session)

        assert isinstance(repository, SolcRepository)
        assert expected_url_part in repository.base_url
        assert repository.session is mock_session
        assert repository._has_latest_release is True

    def test_crytic_repository_creation(self, mock_session: Mock) -> None:
        """CryticRepository creates correct instance."""
        repository = CryticRepository(mock_session)

        assert isinstance(repository, SolcRepository)
        assert repository.base_url == CRYTIC_SOLC_ARTIFACTS
        assert repository._has_latest_release is False

    def test_alloy_repository_creation(self, mock_session: Mock) -> None:
        """AlloyRepository creates correct instance."""
        repository = AlloyRepository(mock_session)

        assert isinstance(repository, SolcRepository)
        assert repository.base_url == ALLOY_SOLC_ARTIFACTS
        assert repository._has_latest_release is False


class TestSolcRepositoryURL:
    """Tests for get_download_url method."""

    @pytest.mark.parametrize(
        "base_url,filename",
        [
            ("https://example.com/artifacts/", "solc-linux-amd64-v0.8.19+commit.abc123"),
            (
                "https://binaries.soliditylang.org/linux-amd64/",
                "solc-linux-amd64-v0.8.19+commit.7dd6d40",
            ),
        ],
    )
    def test_get_download_url(self, mock_session: Mock, base_url: str, filename: str) -> None:
        """URL construction concatenates base_url with artifact filename."""
        repository = SolcRepository(
            base_url=base_url,
            list_url=f"{base_url}list.json",
            session=mock_session,
        )

        url = repository.get_download_url(filename)

        assert url == f"{base_url}{filename}"
        assert url.startswith(repository.base_url)
