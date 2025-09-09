"""
Platform-specific tests for solc-select.

This module contains tests that are specific to Linux, macOS, and Windows.
"""

import pytest
import requests

from .utils import run_command

# Platform configuration matrix
PLATFORM_CONFIGS = {
    "linux": {
        "min_version": "0.4.0",
        "api_url": "https://binaries.soliditylang.org/linux-amd64/list.json",
        "marker": pytest.mark.linux,
    },
    "macos": {
        "min_version": "0.3.6",
        "api_url": "https://binaries.soliditylang.org/macosx-amd64/list.json",
        "marker": pytest.mark.macos,
    },
    "windows": {
        "min_version": "0.4.5",
        "api_url": "https://binaries.soliditylang.org/windows-amd64/list.json",
        "marker": pytest.mark.windows,
    },
}


class TestPlatformSpecific:  # pylint: disable=too-few-public-methods
    """Platform-specific version boundary tests."""

    @pytest.mark.parametrize(
        "platform,config",
        [
            pytest.param("linux", PLATFORM_CONFIGS["linux"], marks=pytest.mark.linux, id="linux"),
            pytest.param("macos", PLATFORM_CONFIGS["macos"], marks=pytest.mark.macos, id="macos"),
            pytest.param(
                "windows", PLATFORM_CONFIGS["windows"], marks=pytest.mark.windows, id="windows"
            ),
        ],
    )
    def test_version_boundaries(self, platform, config, isolated_solc_data):
        """Test version boundaries and constraints for all platforms."""

        min_version = config["min_version"]
        api_url = config["api_url"]

        # Install minimum and latest versions
        run_command(f"solc-select install {min_version} latest", check=True)

        # Test minimum version
        result = run_command(f"solc-select use {min_version}", check=False)
        assert result.returncode == 0
        assert f"Switched global version to {min_version}" in result.stdout, (
            f"Failed to set minimum version on {platform}. Output: {result.stdout}"
        )

        # Get and test latest version
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        latest_release = data["latestRelease"]

        result = run_command(f"solc-select use {latest_release}", check=False)
        assert result.returncode == 0
        assert f"Switched global version to {latest_release}" in result.stdout, (
            f"Failed to set maximum version on {platform}. Output: {result.stdout}"
        )

        # Test version too low (use a version that's definitely below minimum for all platforms)
        result = run_command("solc-select use 0.2.0", check=False)
        assert result.returncode != 0
        assert (
            f"Invalid version - only solc versions above '{min_version}' are available"
            in result.stdout
        ), f"Did not fail for version too low on {platform}. Output: {result.stdout}"

        # Test version too high
        result = run_command("solc-select use 0.100.8", check=False)
        assert result.returncode != 0
        assert (
            f"Invalid version '{latest_release}' is the latest available version" in result.stdout
        ), f"Did not fail for version too high on {platform}. Output: {result.stdout}"
