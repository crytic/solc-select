"""
Test solc-select upgrade functionality.

This module tests that upgrading solc-select preserves installed
compiler versions, exactly mirroring test_solc_upgrade.sh.
"""

import subprocess
import sys
from pathlib import Path

import pytest


class TestUpgrade:
    """Test solc-select upgrade behavior."""
    
    @pytest.mark.slow  # This test reinstalls packages, so it's slow
    def test_upgrade_preserves_versions(self, run_command, tmp_path):
        """
        Test that upgrading solc-select preserves installed versions.
        
        This test installs an old version of solc-select, sets up some
        compiler versions, then upgrades to the current development version
        and verifies everything is preserved.
        """
        # Save current directory
        original_dir = Path.cwd()
        
        try:
            # Uninstall current version
            run_command("pip3 uninstall --yes solc-select", check=False)
            
            # Install release version from PyPI
            result = run_command("pip3 install solc-select", check=True)
            
            # Install and use a specific version
            run_command("solc-select use 0.8.0 --always-install", check=True)
            
            # Get the solc version before upgrade
            result = run_command("solc --version", check=True)
            old_solc_version = result.stdout.strip()
            
            # Install additional versions
            run_command("solc-select install 0.4.11 0.5.0 0.6.12 0.7.3 0.8.3", check=False)
            
            # Get all installed versions before upgrade
            result = run_command("solc-select versions", check=True)
            # Sort the versions for comparison
            old_versions = sorted(result.stdout.strip().split("\n"))
            
            # Uninstall PyPI version
            run_command("pip3 uninstall --yes solc-select", check=False)
            
            # Install development version
            run_command(f"pip3 install -e {original_dir}", check=True)
            
            # Get the solc version after upgrade
            result = run_command("solc --version", check=True)
            new_solc_version = result.stdout.strip()
            
            # Get all installed versions after upgrade
            result = run_command("solc-select versions", check=True)
            new_versions = sorted(result.stdout.strip().split("\n"))
            
            # Verify solc version wasn't changed
            assert old_solc_version == new_solc_version, \
                f"solc version changed during upgrade: {old_solc_version} -> {new_solc_version}"
            
            # Verify all versions are still installed
            assert old_versions == new_versions, \
                f"Installed versions changed during upgrade.\nOld: {old_versions}\nNew: {new_versions}"
            
        finally:
            # Ensure development version is reinstalled for other tests
            run_command(f"pip3 install -e {original_dir}", check=False)