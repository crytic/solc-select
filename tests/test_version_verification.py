"""
Test solc-select version verification functionality.

This module tests that all installed Solidity compiler versions
work correctly and return expected version information.
"""

from pathlib import Path

from .utils import run_in_venv


class TestVersionVerification:  # pylint: disable=too-few-public-methods
    """Test solc-select version verification behavior."""

    def test_all_versions_work_correctly(self, isolated_python_env):
        """
        Test that all installed Solidity versions work correctly.

        This test installs all available Solidity versions using solc-select,
        then verifies each version by running `solc --version` and checking
        that the output contains "solidity compiler" and the correct version number.
        """
        venv = isolated_python_env
        project_root = Path(__file__).parent.parent

        # Install development version of solc-select
        run_in_venv(venv, f"pip install -e {project_root}", check=True)

        # Install all available versions
        run_in_venv(venv, "solc-select install all", check=True)

        # Get list of all installed versions
        result = run_in_venv(venv, "solc-select versions", check=True)
        versions = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]

        assert versions, "No versions found - installation may have failed"

        # Test each version
        for version in versions:
            # Run solc --version with the specific version set
            result = run_in_venv(venv, f"SOLC_VERSION={version} solc --version", check=True)
            output = result.stdout.lower()
            
            # Check that output contains "solidity compiler" and the version
            assert "solidity compiler" in output, f"Version {version}: Missing 'solidity compiler' in output"
            assert version in output, f"Version {version}: Version number not found in output"