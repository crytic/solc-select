"""
Test solc-select upgrade functionality.

This module tests that upgrading solc-select preserves installed
compiler versions.
"""

from pathlib import Path

from .utils import run_in_venv


class TestUpgrade:  # pylint: disable=too-few-public-methods
    """Test solc-select upgrade behavior."""

    def test_upgrade_preserves_versions(self, isolated_python_env):
        """
        Test that upgrading solc-select preserves installed versions.

        This test installs an old version of solc-select, sets up some
        compiler versions, then upgrades to the current development version
        and verifies everything is preserved.
        """
        venv = isolated_python_env
        project_root = Path(__file__).parent.parent

        # Install release version from PyPI
        run_in_venv(venv, 'pip install "solc-select>=1.0"', check=True)

        # Install additional versions
        run_in_venv(venv, "solc-select install 0.4.11 0.5.0 0.6.12 0.7.3 0.8.0 0.8.3", check=False)

        # Use a specific version
        run_in_venv(venv, "solc-select use 0.8.0", check=True)

        # Get the solc version before upgrade
        result = run_in_venv(venv, "solc --version", check=True)
        old_solc_version = result.stdout.strip()
        assert "0.8.0" in old_solc_version, "unexpected version"

        # Get all installed versions before upgrade
        result = run_in_venv(venv, "solc-select versions", check=True)
        # Sort the versions for comparison
        old_versions = sorted(result.stdout.strip().split("\n"))

        # Uninstall PyPI version
        run_in_venv(venv, "pip uninstall --yes solc-select", check=False)

        # Install development version
        run_in_venv(venv, f"pip install -e {project_root}", check=True)

        # Get the solc version after upgrade
        result = run_in_venv(venv, "solc --version", check=True)
        new_solc_version = result.stdout.strip()

        # Get all installed versions after upgrade
        result = run_in_venv(venv, "solc-select versions", check=True)
        new_versions = sorted(result.stdout.strip().split("\n"))

        # Verify solc version wasn't changed
        assert old_solc_version == new_solc_version, (
            f"solc version changed during upgrade: {old_solc_version} -> {new_solc_version}"
        )

        # Verify all versions are still installed
        assert old_versions == new_versions, (
            f"Installed versions changed during upgrade.\nOld: {old_versions}\nNew: {new_versions}"
        )

    def test_cache_already_installed(self, isolated_python_env):
        venv = isolated_python_env
        project_root = Path(__file__).parent.parent

        # Install development version
        run_in_venv(venv, f"pip install -e {project_root}", check=True)

        run_in_venv(venv, "solc-select install 0.8.20", check=False)

        result = run_in_venv(venv, "solc-select install 0.8.20", check=False)
        already_installed = result.stdout.strip()
        assert "Version '0.8.20' is already installed, skipping.." in already_installed, (
            "No skipping already installed versions"
        )
