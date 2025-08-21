"""
Platform-specific tests for solc-select.

This module contains tests that are specific to Linux, macOS, and Windows,
exactly mirroring the behavior of test_linux.sh, test_macos.sh, and test_windows.sh.
"""

import json
import urllib.request

import pytest


class TestLinuxSpecific:
    """Linux-specific version boundary tests."""

    @pytest.mark.linux
    def test_linux_version_boundaries(self, run_command, backup_current_version):
        """Test Linux version boundaries and constraints."""
        # Install all versions (as original script does)
        run_command("solc-select install all", check=False)

        # Test minimum version (0.4.0 on Linux)
        result = run_command("solc-select use 0.4.0", check=False)
        assert result.returncode == 0
        assert "Switched global version to 0.4.0" in result.stdout, (
            f"Failed to set minimum version. Output: {result.stdout}"
        )

        # Get and test latest version
        with urllib.request.urlopen(
            "https://binaries.soliditylang.org/linux-amd64/list.json"
        ) as response:
            data = json.loads(response.read())
            latest_release = data["latestRelease"]

        result = run_command(f"solc-select use {latest_release}", check=False)
        assert result.returncode == 0
        assert f"Switched global version to {latest_release}" in result.stdout, (
            f"Failed to set maximum version. Output: {result.stdout}"
        )

        # Test version too low
        result = run_command("solc-select use 0.3.9", check=False)
        assert result.returncode != 0
        assert (
            "Invalid version - only solc versions above '0.4.0' are available" in result.stdout
        ), f"Did not fail for version too low. Output: {result.stdout}"

        # Test version too high
        result = run_command("solc-select use 0.100.8", check=False)
        assert result.returncode != 0
        assert (
            f"Invalid version '{latest_release}' is the latest available version" in result.stdout
        ), f"Did not fail for version too high. Output: {result.stdout}"


class TestMacOSSpecific:
    """macOS-specific version boundary tests."""

    @pytest.mark.macos
    def test_macos_version_boundaries(self, run_command, backup_current_version):
        """Test macOS version boundaries and constraints."""
        # Install all versions (as original script does)
        run_command("solc-select install all", check=False)

        # Test minimum version (0.3.6 on macOS)
        result = run_command("solc-select use 0.3.6", check=False)
        assert result.returncode == 0
        assert "Switched global version to 0.3.6" in result.stdout, (
            f"Failed to set minimum version. Output: {result.stdout}"
        )

        # Get and test latest version
        with urllib.request.urlopen(
            "https://binaries.soliditylang.org/macosx-amd64/list.json"
        ) as response:
            data = json.loads(response.read())
            latest_release = data["latestRelease"]

        result = run_command(f"solc-select use {latest_release}", check=False)
        assert result.returncode == 0
        assert f"Switched global version to {latest_release}" in result.stdout, (
            f"Failed to set maximum version. Output: {result.stdout}"
        )

        # Test version too low
        result = run_command("solc-select use 0.3.5", check=False)
        assert result.returncode != 0
        assert (
            "Invalid version - only solc versions above '0.3.6' are available" in result.stdout
        ), f"Did not fail for version too low. Output: {result.stdout}"

        # Test version too high
        result = run_command("solc-select use 0.100.8", check=False)
        assert result.returncode != 0
        assert (
            f"Invalid version '{latest_release}' is the latest available version" in result.stdout
        ), f"Did not fail for version too high. Output: {result.stdout}"


class TestWindowsSpecific:
    """Windows-specific version boundary tests."""

    @pytest.mark.windows
    def test_windows_version_boundaries(self, run_command, backup_current_version):
        """Test Windows version boundaries and constraints."""
        # Install all versions (as original script does)
        run_command("solc-select install all", check=False)

        # Test minimum version (0.4.11 on Windows)
        result = run_command("solc-select use 0.4.11", check=False)
        assert result.returncode == 0
        assert "Switched global version to 0.4.11" in result.stdout, (
            f"Failed to set minimum version. Output: {result.stdout}"
        )

        # Get and test latest version
        with urllib.request.urlopen(
            "https://binaries.soliditylang.org/windows-amd64/list.json"
        ) as response:
            data = json.loads(response.read())
            latest_release = data["latestRelease"]

        result = run_command(f"solc-select use {latest_release}", check=False)
        assert result.returncode == 0
        assert f"Switched global version to {latest_release}" in result.stdout, (
            f"Failed to set maximum version. Output: {result.stdout}"
        )

        # Test version too low
        result = run_command("solc-select use 0.4.10", check=False)
        assert result.returncode != 0
        assert (
            "Invalid version - only solc versions above '0.4.11' are available" in result.stdout
        ), f"Did not fail for version too low. Output: {result.stdout}"

        # Test version too high
        result = run_command("solc-select use 0.100.8", check=False)
        assert result.returncode != 0
        assert (
            f"Invalid version '{latest_release}' is the latest available version" in result.stdout
        ), f"Did not fail for version too high. Output: {result.stdout}"
