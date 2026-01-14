"""Unit tests for PlatformService."""

import sys
from collections.abc import Generator
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from _pytest.monkeypatch import MonkeyPatch

from solc_select.models.artifacts import SolcArtifactOnDisk
from solc_select.models.platforms import Platform
from solc_select.models.versions import SolcVersion
from solc_select.platform_capabilities import EmulationCapability, PlatformIdentifier
from solc_select.services.platform_service import PlatformService


@contextmanager
def capture_stderr() -> Generator[StringIO, None, None]:
    """Context manager to capture stderr output."""
    capture = StringIO()
    original = sys.stderr
    sys.stderr = capture
    try:
        yield capture
    finally:
        sys.stderr = original


@pytest.fixture
def darwin_arm64_platform() -> Platform:
    """Platform instance for macOS ARM64."""
    return Platform("darwin", "arm64")


@pytest.fixture
def linux_arm64_platform() -> Platform:
    """Platform instance for Linux ARM64."""
    return Platform("linux", "arm64")


@pytest.fixture
def linux_amd64_platform() -> Platform:
    """Platform instance for Linux AMD64."""
    return Platform("linux", "amd64")


@pytest.fixture
def native_artifact(linux_amd64_platform: Platform, tmp_path: Path) -> SolcArtifactOnDisk:
    """Native artifact without emulation."""
    return SolcArtifactOnDisk(
        version=SolcVersion("0.8.19"),
        platform=linux_amd64_platform,
        file_path=tmp_path / "solc-v0.8.19",
        emulation=None,
    )


def create_emulated_artifact(
    platform: Platform, tmp_path: Path, emulation_type: str, detector_available: bool = True
) -> SolcArtifactOnDisk:
    """Create an emulated artifact for testing."""
    if emulation_type == "qemu":
        target = PlatformIdentifier("linux", "amd64")
        prefix = ["qemu-x86_64"]
    else:  # rosetta
        target = PlatformIdentifier("darwin", "amd64")
        prefix = []  # Rosetta is transparent

    emulation = EmulationCapability(
        target_platform=target,
        emulation_type=emulation_type,
        detector=Mock(return_value=detector_available),
        command_prefix=prefix,
    )
    return SolcArtifactOnDisk(
        version=SolcVersion("0.8.19"),
        platform=platform,
        file_path=tmp_path / "solc-v0.8.19",
        emulation=emulation,
    )


class TestPlatformServiceEmulation:
    """Tests for emulation prefix retrieval."""

    def test_get_emulation_prefix_native(
        self, linux_amd64_platform: Platform, native_artifact: SolcArtifactOnDisk
    ) -> None:
        """Returns empty list for native binary."""
        service = PlatformService(linux_amd64_platform)
        assert service.get_emulation_prefix(native_artifact) == []

    def test_get_emulation_prefix_qemu_available(
        self, linux_arm64_platform: Platform, tmp_path: Path
    ) -> None:
        """Returns ['qemu-x86_64'] when QEMU available."""
        service = PlatformService(linux_arm64_platform)
        artifact = create_emulated_artifact(linux_arm64_platform, tmp_path, "qemu")
        assert service.get_emulation_prefix(artifact) == ["qemu-x86_64"]

    def test_get_emulation_prefix_emulator_unavailable(
        self, linux_arm64_platform: Platform, tmp_path: Path
    ) -> None:
        """Raises RuntimeError when emulator is not available."""
        service = PlatformService(linux_arm64_platform)
        artifact = create_emulated_artifact(
            linux_arm64_platform, tmp_path, "qemu", detector_available=False
        )

        with pytest.raises(RuntimeError) as exc_info:
            service.get_emulation_prefix(artifact)

        error_msg = str(exc_info.value).lower()
        assert "qemu" in error_msg
        assert "not available" in error_msg

    def test_get_emulation_prefix_rosetta(
        self, darwin_arm64_platform: Platform, tmp_path: Path
    ) -> None:
        """Returns empty list for Rosetta (transparent emulation)."""
        service = PlatformService(darwin_arm64_platform)
        artifact = create_emulated_artifact(darwin_arm64_platform, tmp_path, "rosetta")
        assert service.get_emulation_prefix(artifact) == []


class TestPlatformServiceWarnings:
    """Tests for ARM64 compatibility warnings."""

    def test_warn_arm64_skips_on_amd64(self, linux_amd64_platform: Platform) -> None:
        """No warning shown on non-ARM64 platforms."""
        service = PlatformService(linux_amd64_platform)
        with capture_stderr() as output:
            service.warn_about_arm64_compatibility()
        assert output.getvalue() == ""

    def test_warn_arm64_shown_once_with_marker(
        self, linux_arm64_platform: Platform, temp_solc_select_dir: Path, monkeypatch: MonkeyPatch
    ) -> None:
        """Warning shown once, creates marker file, not shown again."""
        monkeypatch.setattr(
            "solc_select.services.platform_service.SOLC_SELECT_DIR", temp_solc_select_dir
        )

        with patch("solc_select.services.platform_service.detect_qemu", return_value=False):
            service = PlatformService(linux_arm64_platform)

            # First call shows warning
            with capture_stderr() as first:
                service.warn_about_arm64_compatibility()
            assert "WARNING: ARM64 Architecture Detected" in first.getvalue()
            assert (temp_solc_select_dir / ".arm64_warning_shown").exists()

            # Second call is silent
            with capture_stderr() as second:
                service.warn_about_arm64_compatibility()
            assert second.getvalue() == ""

            # force=True shows again
            with capture_stderr() as forced:
                service.warn_about_arm64_compatibility(force=True)
            assert "WARNING: ARM64 Architecture Detected" in forced.getvalue()

    @pytest.mark.parametrize(
        "os_type,detector_name,detector_value,expected_phrases,unexpected_phrases",
        [
            # Darwin with Rosetta available
            (
                "darwin",
                "detect_rosetta",
                True,
                ["Rosetta 2 detected", "will use emulation for older versions"],
                ["To use solc-select on ARM64"],
            ),
            # Darwin without Rosetta
            (
                "darwin",
                "detect_rosetta",
                False,
                ["Rosetta 2 not available", "versions prior to 0.8.5 are x86_64 only"],
                [],
            ),
            # Linux with QEMU available
            (
                "linux",
                "detect_qemu",
                True,
                ["qemu-x86_64 detected", "will use emulation for versions < 0.8.31"],
                ["To use solc-select on ARM64"],
            ),
            # Linux without QEMU
            (
                "linux",
                "detect_qemu",
                False,
                ["Versions < 0.8.31 require x86_64 emulation", "qemu is not installed"],
                [],
            ),
        ],
    )
    def test_warn_arm64_platform_specific(
        self,
        temp_solc_select_dir: Path,
        monkeypatch: MonkeyPatch,
        os_type: str,
        detector_name: str,
        detector_value: bool,
        expected_phrases: list[str],
        unexpected_phrases: list[str],
    ) -> None:
        """Test platform-specific warning messages."""
        platform = Platform(os_type, "arm64")
        monkeypatch.setattr(
            "solc_select.services.platform_service.SOLC_SELECT_DIR", temp_solc_select_dir
        )

        with patch(
            f"solc_select.services.platform_service.{detector_name}", return_value=detector_value
        ):
            service = PlatformService(platform)
            with capture_stderr() as output:
                service.warn_about_arm64_compatibility()
            result = output.getvalue()

        assert "WARNING: ARM64 Architecture Detected" in result
        for phrase in expected_phrases:
            assert phrase in result
        for phrase in unexpected_phrases:
            assert phrase not in result
