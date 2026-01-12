"""
Test solc-select version verification functionality.

This module tests that all installed Solidity compiler versions
work correctly and return expected version information.
"""

from typing import Any

import pytest

from .utils import run_command


class TestVersionVerification:  # pylint: disable=too-few-public-methods
    """Test solc-select version verification behavior."""

    @pytest.mark.parametrize("test_mode", [pytest.param("all", marks=pytest.mark.slow), "some"])
    def test_all_versions_work_correctly(self, isolated_solc_data: Any, test_mode: str) -> None:
        """
        Test that installed Solidity versions work correctly.

        This test installs Solidity versions using solc-select (either all or some specific ones),
        then verifies each version by running `solc --version` and checking
        that the output contains "solidity compiler" and the correct version number.
        """
        if test_mode == "all":
            # Install all available versions
            run_command("solc-select install all", check=True)
        else:  # test_mode == "some"
            # Install specific versions in one call
            specific_versions = ["0.4.11", "0.7.3", "0.8.10", "0.8.30"]
            run_command(f"solc-select install {' '.join(specific_versions)}", check=True)

        # Get list of all installed versions
        result = run_command("solc-select versions", check=True)
        versions = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

        assert versions, "No versions found - installation may have failed"

        # Test each version
        for version in versions:
            # Run solc --version with the specific version set
            result = run_command("solc --version", check=True, env={"SOLC_VERSION": version})
            output = result.stdout.lower()

            # Check that output contains "solidity compiler" and the version
            assert "solidity compiler" in output, (
                f"Version {version}: Missing 'solidity compiler' in output"
            )
            assert version in output, f"Version {version}: Version number not found in output"

    def test_no_global_version_selected_error(self, isolated_solc_data: Any) -> None:
        """
        Test that running solc without a global version selected throws an error.
        """
        # Install at least one version but don't select it globally
        run_command("solc-select install 0.8.10", check=True)

        # Try to run solc without setting a global version - this should fail
        result = run_command("solc --version", check=False)

        # Should have non-zero exit code and error message about no version selected
        assert result.returncode != 0, "Expected solc to fail when no version is selected"
        error_output = result.stdout.lower()
        assert "no solc version set" in error_output, (
            f"Expected error about no version selected, got: {result.stdout}"
        )
