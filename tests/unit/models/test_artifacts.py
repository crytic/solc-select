"""Unit tests for artifact-related domain models."""

from pathlib import Path

import pytest

from solc_select.models.artifacts import SolcArtifact
from solc_select.models.platforms import Platform
from solc_select.models.versions import SolcVersion


def create_artifact(
    version: str = "0.8.19",
    platform: Platform | None = None,
    checksum_sha256: str = "abc123",
    checksum_keccak256: str | None = None,
    download_url: str = "https://example.com/solc",
) -> SolcArtifact:
    """Helper to create SolcArtifact with sensible defaults."""
    if platform is None:
        platform = Platform("linux", "amd64")
    return SolcArtifact(
        version=SolcVersion(version),
        platform=platform,
        file_path=Path(f"/tmp/solc-{version}"),
        download_url=download_url,
        checksum_sha256=checksum_sha256,
        checksum_keccak256=checksum_keccak256,
    )


class TestSolcArtifact:
    """Tests for SolcArtifact domain model."""

    @pytest.mark.parametrize(
        "version,expected",
        [
            ("0.6.12", True),  # Old Windows version - should be ZIP
            ("0.7.1", True),  # Boundary - still ZIP
            ("0.7.2", False),  # First non-ZIP version
            ("0.8.19", False),  # Modern version
        ],
    )
    def test_is_zip_archive_windows(self, version: str, expected: bool) -> None:
        """Windows ZIP archive detection based on version boundary (0.7.1)."""
        artifact = create_artifact(version=version, platform=Platform("windows", "amd64"))
        assert artifact.is_zip_archive == expected

    @pytest.mark.parametrize("os_type", ["linux", "darwin"])
    def test_is_zip_archive_non_windows(self, os_type: str) -> None:
        """Non-Windows platforms should never have ZIP archives."""
        artifact = create_artifact(version="0.6.12", platform=Platform(os_type, "amd64"))
        assert not artifact.is_zip_archive

    def test_checksum_prefix_removal(self) -> None:
        """Checksums with 0x prefix should be stripped in __post_init__."""
        artifact = create_artifact(
            checksum_sha256="0xabc123def456",
            checksum_keccak256="0x789xyz",
        )
        assert artifact.checksum_sha256 == "abc123def456"
        assert artifact.checksum_keccak256 == "789xyz"

    def test_get_binary_name_in_zip(self) -> None:
        """Binary name inside ZIP archives should be solc.exe."""
        artifact = create_artifact(version="0.6.12", platform=Platform("windows", "amd64"))
        assert artifact.get_binary_name_in_zip() == "solc.exe"

    def test_get_binary_name_in_zip_raises_for_non_zip(self) -> None:
        """Calling get_binary_name_in_zip on non-ZIP should raise ValueError."""
        artifact = create_artifact(version="0.8.19", platform=Platform("windows", "amd64"))
        with pytest.raises(ValueError, match="Not a ZIP archive"):
            artifact.get_binary_name_in_zip()

    @pytest.mark.parametrize(
        "download_url,checksum,error_msg",
        [
            ("", "abc123", "Download URL cannot be empty"),
            ("https://example.com", "", "SHA256 checksum cannot be empty"),
        ],
    )
    def test_validation_errors(self, download_url: str, checksum: str, error_msg: str) -> None:
        """Empty URL or checksum should raise ValueError."""
        with pytest.raises(ValueError, match=error_msg):
            SolcArtifact(
                version=SolcVersion("0.8.19"),
                platform=Platform("linux", "amd64"),
                file_path=Path("/tmp/solc-0.8.19"),
                download_url=download_url,
                checksum_sha256=checksum,
                checksum_keccak256=None,
            )
