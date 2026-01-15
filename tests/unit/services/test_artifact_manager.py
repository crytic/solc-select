"""Unit tests for ArtifactManager service.

Tests cover checksum verification, download operations, bulk installs, and metadata creation.
"""

import hashlib
import io
import sys
import zipfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from Crypto.Hash import keccak

from solc_select.exceptions import ChecksumMismatchError
from solc_select.models.artifacts import SolcArtifact, SolcArtifactOnDisk
from solc_select.models.platforms import Platform
from solc_select.models.versions import SolcVersion
from solc_select.platform_capabilities import (
    PlatformCapability,
    PlatformIdentifier,
)
from solc_select.repositories import SolcRepository
from solc_select.services.artifact_manager import ArtifactManager
from solc_select.services.repository_matcher import RepositoryMatcher


@pytest.fixture
def mock_repository_matcher():
    """Mock RepositoryMatcher."""
    matcher = Mock(spec=RepositoryMatcher)
    mock_repo = Mock(spec=SolcRepository)
    mock_repo.available_versions = {
        "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
        "0.8.20": "solc-linux-amd64-v0.8.20+commit.def456",
        "0.8.21": "solc-linux-amd64-v0.8.21+commit.ghi789",
    }
    mock_repo.get_download_url.return_value = (
        "https://binaries.soliditylang.org/linux-amd64/solc-linux-amd64-v0.8.19+commit.abc123"
    )
    mock_repo.get_checksums.return_value = (
        "abcd1234" * 8,  # 64 char SHA256
        "efgh5678" * 8,  # 64 char Keccak256
    )
    matcher.find_repository_for_version.return_value = (
        mock_repo,
        PlatformIdentifier("linux", "amd64"),
    )
    return matcher


@pytest.fixture
def mock_platform_capability():
    """Mock PlatformCapability."""
    return PlatformCapability(
        host_platform=PlatformIdentifier("linux", "amd64"),
        native_support=PlatformIdentifier("linux", "amd64"),
        emulation_capabilities=[],
    )


@pytest.fixture
def artifact_manager(
    mock_repository_matcher, mock_platform_capability, mock_platform, mock_session, mock_filesystem
):
    """Create ArtifactManager with mocked dependencies."""
    return ArtifactManager(
        repository_matcher=mock_repository_matcher,
        platform_capability=mock_platform_capability,
        platform=mock_platform,
        session=mock_session,
        filesystem=mock_filesystem,
    )


@pytest.fixture
def sample_artifact():
    """Sample SolcArtifact for testing."""
    return SolcArtifact(
        version=SolcVersion("0.8.19"),
        platform=Platform("linux", "amd64"),
        download_url="https://binaries.soliditylang.org/linux-amd64/solc-linux-amd64-v0.8.19+commit.abc123",
        checksum_sha256="abcd1234" * 8,
        checksum_keccak256="efgh5678" * 8,
        file_path=Path("/tmp/solc-0.8.19"),
    )


@pytest.fixture
def sample_artifact_windows_zip():
    """Sample Windows ZIP artifact for testing (< 0.7.1)."""
    return SolcArtifact(
        version=SolcVersion("0.4.26"),
        platform=Platform("windows", "amd64"),
        download_url="https://binaries.soliditylang.org/windows-amd64/solc-windows-amd64-v0.4.26+commit.abc123.zip",
        checksum_sha256="1234abcd" * 8,
        checksum_keccak256="5678efgh" * 8,
        file_path=Path("/tmp/solc-0.4.26.zip"),
    )


class TestArtifactManagerChecksum:
    """Test checksum verification functionality."""

    def test_verify_checksum_success(self, artifact_manager, sample_artifact):
        """Valid checksums (SHA256 and Keccak256) should verify successfully."""
        content = b"test content"
        sample_artifact.checksum_sha256 = hashlib.sha256(content).hexdigest()
        sample_artifact.checksum_keccak256 = keccak.new(digest_bits=256, data=content).hexdigest()

        artifact_manager.verify_checksum(sample_artifact, io.BytesIO(content))

    def test_verify_checksum_sha256_mismatch(self, artifact_manager, sample_artifact):
        """SHA256 mismatch should raise ChecksumMismatchError."""
        content = b"wrong content"
        actual_sha256 = hashlib.sha256(content).hexdigest()

        with pytest.raises(ChecksumMismatchError) as exc_info:
            artifact_manager.verify_checksum(sample_artifact, io.BytesIO(content))

        assert exc_info.value.algorithm == "SHA256"
        assert exc_info.value.expected == sample_artifact.checksum_sha256
        assert exc_info.value.actual == actual_sha256

    def test_verify_checksum_keccak256_mismatch(self, artifact_manager, sample_artifact):
        """Keccak256 mismatch should raise ChecksumMismatchError."""
        content = b"test content"
        sample_artifact.checksum_sha256 = hashlib.sha256(content).hexdigest()
        sample_artifact.checksum_keccak256 = "wrong_keccak256_hash" + "0" * 48

        with pytest.raises(ChecksumMismatchError) as exc_info:
            artifact_manager.verify_checksum(sample_artifact, io.BytesIO(content))

        assert exc_info.value.algorithm == "Keccak256"

    def test_verify_checksum_large_file(self, artifact_manager, sample_artifact):
        """Chunked reading should work for large files (>10MB)."""
        content = b"x" * (12 * 1024 * 1024)  # 12MB
        sample_artifact.checksum_sha256 = hashlib.sha256(content).hexdigest()
        sample_artifact.checksum_keccak256 = keccak.new(digest_bits=256, data=content).hexdigest()

        artifact_manager.verify_checksum(sample_artifact, io.BytesIO(content))


class TestArtifactManagerDownload:
    """Test download and installation functionality."""

    def test_download_already_installed_skips(self, artifact_manager, mock_filesystem):
        """Should return early if version is already installed."""
        version = SolcVersion("0.8.19")
        mock_filesystem.is_installed.return_value = True

        result = artifact_manager.download_and_install(version, silent=True)

        assert result is True
        mock_filesystem.is_installed.assert_called_once_with(version)
        # Should not attempt download
        artifact_manager.session.get.assert_not_called()

    def test_download_successful_standard_binary(
        self, artifact_manager, mock_filesystem, mock_session, sample_artifact, tmp_path
    ):
        """Should download, verify checksum, and chmod +x for standard binaries."""
        version = SolcVersion("0.8.19")
        binary_path = tmp_path / "solc-0.8.19"

        # Setup mocks
        mock_filesystem.is_installed.return_value = False
        mock_filesystem.get_binary_path.return_value = binary_path

        # Create real binary content with matching checksums
        content = b"solc binary content"
        sha256_hash = hashlib.sha256(content).hexdigest()
        keccak_hash = keccak.new(digest_bits=256, data=content).hexdigest()

        # Mock HTTP response
        mock_response = Mock()
        mock_response.iter_content.return_value = [content]
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response

        # Mock repository to return correct checksums
        mock_repo = artifact_manager.repository_matcher.find_repository_for_version.return_value[0]
        mock_repo.get_checksums.return_value = (sha256_hash, keccak_hash)

        result = artifact_manager.download_and_install(version, silent=True)

        assert result is True
        mock_session.get.assert_called_once()
        assert binary_path.exists()
        # Check file has execute permissions
        if sys.platform != "win32":
            assert binary_path.stat().st_mode & 0o100  # User execute bit

    def test_download_successful_zip_archive(
        self,
        mock_repository_matcher,
        mock_platform_capability,
        mock_session,
        mock_filesystem,
        tmp_path,
    ):
        """Should extract Windows ZIP archives (<0.7.1) correctly."""
        version = SolcVersion("0.4.26")

        # Create artifact directory structure
        artifact_dir = tmp_path / "0.4.26"
        artifact_dir.mkdir(parents=True)

        zip_path = artifact_dir / "solc-0.4.26.zip"
        binary_path = artifact_dir / "solc-0.4.26.exe"

        # Setup mocks for Windows platform
        mock_filesystem.is_installed.return_value = False
        mock_filesystem.get_binary_path.return_value = zip_path
        mock_filesystem.ensure_artifact_directory = Mock()

        # Create a real ZIP file
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("solc.exe", b"windows binary content")
        zip_content = zip_buffer.getvalue()

        # Calculate checksums for ZIP
        sha256_hash = hashlib.sha256(zip_content).hexdigest()
        keccak_hash = keccak.new(digest_bits=256, data=zip_content).hexdigest()

        # Mock HTTP response
        mock_response = Mock()
        mock_response.iter_content.return_value = [zip_content]
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response

        # Mock repository to return correct checksums and available_versions
        mock_repo = mock_repository_matcher.find_repository_for_version.return_value[0]
        mock_repo.available_versions = {"0.4.26": "solc-windows-amd64-v0.4.26+commit.abc123.zip"}
        mock_repo.get_download_url.return_value = "https://example.com/solc-0.4.26.zip"
        mock_repo.get_checksums.return_value = (sha256_hash, keccak_hash)

        # Create ArtifactManager with Windows platform
        windows_platform = Platform("windows", "amd64")
        artifact_manager = ArtifactManager(
            repository_matcher=mock_repository_matcher,
            platform_capability=mock_platform_capability,
            platform=windows_platform,
            session=mock_session,
            filesystem=mock_filesystem,
        )

        # Mock _extract_zip_archive to verify it's called instead of testing full extraction
        # (Full extraction is tested in integration tests)
        extract_called = []

        def mock_extract(artifact: SolcArtifact) -> None:
            extract_called.append(artifact)
            # Simulate extraction: remove ZIP and create binary
            artifact.file_path.unlink()
            binary_path.touch()
            binary_path.chmod(0o775)

        with patch.object(artifact_manager, "_extract_zip_archive", side_effect=mock_extract):
            result = artifact_manager.download_and_install(version, silent=True)

        assert result is True
        # Verify _extract_zip_archive was called
        assert len(extract_called) == 1
        assert extract_called[0].version == version
        assert extract_called[0].is_zip_archive is True
        # ZIP should be extracted and removed, binary should exist
        assert not zip_path.exists()
        assert binary_path.exists()

    def test_download_checksum_error_cleanup(
        self, artifact_manager, mock_filesystem, mock_session, sample_artifact, tmp_path
    ):
        """Should delete file on checksum failure."""
        version = SolcVersion("0.8.19")
        binary_path = tmp_path / "solc-0.8.19"

        # Setup mocks
        mock_filesystem.is_installed.return_value = False
        mock_filesystem.get_binary_path.return_value = binary_path

        # Create content with wrong checksum
        content = b"wrong content"
        mock_response = Mock()
        mock_response.iter_content.return_value = [content]
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response

        # Repository returns expected checksums (won't match)
        mock_repo = artifact_manager.repository_matcher.find_repository_for_version.return_value[0]
        mock_repo.get_checksums.return_value = ("expected_sha256" * 4, "expected_keccak" * 4)

        with pytest.raises(ChecksumMismatchError):
            artifact_manager.download_and_install(version, silent=True)

        # File should be cleaned up
        assert not binary_path.exists()

    def test_download_network_error_cleanup(
        self, artifact_manager, mock_filesystem, mock_session, tmp_path
    ):
        """Should clean up partial download on network error."""
        version = SolcVersion("0.8.19")
        binary_path = tmp_path / "solc-0.8.19"

        # Setup mocks
        mock_filesystem.is_installed.return_value = False
        mock_filesystem.get_binary_path.return_value = binary_path

        # Simulate network error
        mock_session.get.side_effect = requests.RequestException("Network error")

        result = artifact_manager.download_and_install(version, silent=True)

        assert result is False
        # File should be cleaned up if it exists
        assert not binary_path.exists()

    def test_download_keyboard_interrupt_cleanup(
        self, artifact_manager, mock_filesystem, mock_session, tmp_path
    ):
        """Should cleanup on Ctrl+C (KeyboardInterrupt)."""
        version = SolcVersion("0.8.19")
        binary_path = tmp_path / "solc-0.8.19"

        # Setup mocks
        mock_filesystem.is_installed.return_value = False
        mock_filesystem.get_binary_path.return_value = binary_path

        # Simulate KeyboardInterrupt during download
        def iter_with_interrupt() -> Iterator[bytes]:
            yield b"partial content"
            raise KeyboardInterrupt("User cancelled")

        mock_response = Mock()
        mock_response.iter_content.return_value = iter_with_interrupt()
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response

        with pytest.raises(KeyboardInterrupt):
            artifact_manager.download_and_install(version, silent=True)

        # File should be cleaned up
        assert not binary_path.exists()


class TestArtifactManagerBulkInstall:
    """Test bulk installation with parallel downloads."""

    def test_install_single_version(self, artifact_manager, mock_filesystem):
        """Single version should use direct download path."""
        mock_filesystem.is_installed.return_value = True
        result = artifact_manager.install_versions([SolcVersion("0.8.19")], silent=True)
        assert result is True

    def test_install_multiple_versions_uses_thread_pool(self, artifact_manager):
        """Multiple versions should use ThreadPoolExecutor with 5 workers."""
        versions = [SolcVersion("0.8.19"), SolcVersion("0.8.20"), SolcVersion("0.8.21")]

        with (
            patch.object(artifact_manager, "download_and_install", return_value=True),
            patch(
                "solc_select.services.artifact_manager.ThreadPoolExecutor"
            ) as mock_executor_class,
            patch("solc_select.services.artifact_manager.as_completed") as mock_as_completed,
        ):
            mock_executor = Mock()
            mock_executor_class.return_value.__enter__.return_value = mock_executor
            mock_futures = [Mock(result=Mock(return_value=True)) for _ in versions]
            mock_executor.submit.side_effect = mock_futures
            mock_as_completed.return_value = mock_futures

            result = artifact_manager.install_versions(versions, silent=True)

            assert result is True
            mock_executor_class.assert_called_once_with(max_workers=5)
            assert mock_executor.submit.call_count == len(versions)

    def test_install_partial_failure_returns_false(self, artifact_manager):
        """Partial installation failure should return False."""
        versions = [SolcVersion("0.8.19"), SolcVersion("0.8.20")]
        call_count = [0]

        def mock_install(version, silent):
            call_count[0] += 1
            return call_count[0] == 1  # Only first succeeds

        with patch.object(artifact_manager, "download_and_install", side_effect=mock_install):
            result = artifact_manager.install_versions(versions, silent=True)
        assert result is False

    def test_install_empty_list(self, artifact_manager):
        """Empty version list should return True immediately."""
        result = artifact_manager.install_versions([], silent=True)
        assert result is True
        artifact_manager.session.get.assert_not_called()


class TestArtifactManagerMetadata:
    """Test artifact metadata creation."""

    def test_create_artifact_metadata(self, artifact_manager, mock_repository_matcher):
        """Should fetch metadata from repository."""
        version = SolcVersion("0.8.19")

        artifact = artifact_manager.create_artifact_metadata(version)

        assert isinstance(artifact, SolcArtifact)
        assert artifact.version == version
        assert artifact.download_url.startswith("https://")
        assert len(artifact.checksum_sha256) == 64
        assert artifact.checksum_keccak256 is None or len(artifact.checksum_keccak256) == 64
        mock_repository_matcher.find_repository_for_version.assert_called_once_with(version)

    def test_create_artifact_metadata_not_available(
        self, artifact_manager, mock_repository_matcher
    ):
        """Should raise ValueError if version is not available."""
        version = SolcVersion("9.9.9")

        # Mock repository to not have this version
        mock_repo = mock_repository_matcher.find_repository_for_version.return_value[0]
        mock_repo.available_versions = {}

        with pytest.raises(ValueError) as exc_info:
            artifact_manager.create_artifact_metadata(version)

        assert "is not available" in str(exc_info.value)
        assert "9.9.9" in str(exc_info.value)

    def test_create_local_artifact_metadata(
        self, artifact_manager, mock_repository_matcher, mock_filesystem
    ):
        """Should use local filesystem paths for installed versions."""
        version = SolcVersion("0.8.19")
        expected_path = Path("/home/user/.solc-select/artifacts/0.8.19/solc-0.8.19")
        mock_filesystem.get_binary_path.return_value = expected_path

        artifact = artifact_manager.create_local_artifact_metadata(version)

        assert isinstance(artifact, SolcArtifactOnDisk)
        assert artifact.version == version
        assert artifact.file_path == expected_path
        mock_filesystem.get_binary_path.assert_called_once_with(version)
        # Should use exact=False for local lookups
        mock_repository_matcher.find_repository_for_version.assert_called_once_with(
            version, exact=False
        )
