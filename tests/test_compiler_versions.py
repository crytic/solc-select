"""
Test Solidity compiler version-specific functionality.

This module tests compilation with different Solidity versions,
exactly mirroring the behavior of the original test_solc.sh script.
"""

import os
import shutil

import pytest


class TestCompilerVersions:
    """Test compilation with different Solidity compiler versions."""

    @pytest.fixture(scope="function", autouse=True)
    def install_required_versions(self, run_command):
        """Install all required compiler versions before running tests."""
        # Install all versions needed for tests, exactly as bash script did
        run_command("solc-select install 0.4.5 0.5.0 0.6.0 0.7.0 0.8.0 0.8.1 0.8.9", check=False)
        # Don't fail if already installed

    def test_solc_045(self, run_command, test_contracts_dir, backup_current_version):
        """Test Solidity 0.4.5 compilation behavior."""
        _ = backup_current_version  # Fixture ensures clean state
        # Switch to 0.4.5
        result = run_command("solc-select use 0.4.5", check=False)
        assert result.returncode == 0, f"Failed to switch to 0.4.5: {result.stdout}"

        # Test successful compilation
        result = run_command(f"solc {test_contracts_dir}/solc045_success.sol", check=False)
        assert result.returncode == 0, f"solc045_success failed with: {result.stdout}"

        # Test expected compilation failure
        result = run_command(f"solc {test_contracts_dir}/solc045_fail_compile.sol", check=False)
        assert result.returncode != 0
        assert "Error: Expected token Semicolon got 'Function'" in result.stdout, (
            f"solc045_fail_compile did not fail as expected. Output: {result.stdout}"
        )

    def test_solc_050(self, run_command, test_contracts_dir, backup_current_version):
        """Test Solidity 0.5.0 compilation behavior."""
        _ = backup_current_version  # Fixture ensures clean state
        # Switch to 0.5.0
        result = run_command("solc-select use 0.5.0", check=False)
        assert result.returncode == 0, f"Failed to switch to 0.5.0: {result.stdout}"

        # Test successful compilation
        result = run_command(f"solc {test_contracts_dir}/solc050_success.sol", check=False)
        assert result.returncode == 0, f"solc050_success failed with: {result.stdout}"

        # Test expected compilation failure
        result = run_command(f"solc {test_contracts_dir}/solc050_fail_compile.sol", check=False)
        assert result.returncode != 0
        assert (
            "Error: Functions are not allowed to have the same name as the contract."
            in result.stdout
        ), f"solc050_fail_compile did not fail as expected. Output: {result.stdout}"

    def test_solc_060(self, run_command, test_contracts_dir, backup_current_version):
        """Test Solidity 0.6.0 compilation behavior."""
        _ = backup_current_version  # Fixture ensures clean state
        # Switch to 0.6.0
        result = run_command("solc-select use 0.6.0", check=False)
        assert result.returncode == 0, f"Failed to switch to 0.6.0: {result.stdout}"

        # Test try/catch feature (new in 0.6.0)
        result = run_command(f"solc {test_contracts_dir}/solc060_success_trycatch.sol", check=False)
        assert result.returncode == 0, f"solc060_success_trycatch failed with: {result.stdout}"

        # Test receive function (new in 0.6.0)
        result = run_command(f"solc {test_contracts_dir}/solc060_success_receive.sol", check=False)
        assert result.returncode == 0, f"solc060_success_receive failed with: {result.stdout}"

    def test_solc_070(self, run_command, test_contracts_dir, backup_current_version):
        """Test Solidity 0.7.0 compilation behavior."""
        _ = backup_current_version  # Fixture ensures clean state
        # Switch to 0.7.0
        result = run_command("solc-select use 0.7.0", check=False)
        assert result.returncode == 0, f"Failed to switch to 0.7.0: {result.stdout}"

        # Test deprecated 'now' keyword
        result = run_command(f"solc {test_contracts_dir}/solc070_fail_compile.sol", check=False)
        assert result.returncode != 0
        assert '"now" has been deprecated.' in result.stdout, (
            f"solc070_fail_compile did not show deprecation warning. Output: {result.stdout}"
        )

        # Test successful compilation
        result = run_command(f"solc {test_contracts_dir}/solc070_success.sol", check=False)
        assert result.returncode == 0, f"solc070_success failed with: {result.stdout}"

    def test_solc_080(self, run_command, test_contracts_dir, backup_current_version):
        """Test Solidity 0.8.0 compilation behavior."""
        _ = backup_current_version  # Fixture ensures clean state
        # Switch to 0.8.0
        result = run_command("solc-select use 0.8.0", check=False)
        assert result.returncode == 0, f"Failed to switch to 0.8.0: {result.stdout}"

        # Test successful compilation
        result = run_command(f"solc {test_contracts_dir}/solc080_success.sol", check=False)
        assert result.returncode == 0, f"solc080_success failed with: {result.stdout}"

        # Test compilation with warning
        result = run_command(f"solc {test_contracts_dir}/solc080_success_warning.sol", check=False)
        # Should succeed but with warning
        assert result.returncode == 0
        assert "Warning: Function state mutability can be restricted to pure" in result.stdout, (
            f"solc080_success_warning did not show expected warning. Output: {result.stdout}"
        )

        # Test expected compilation failure
        result = run_command(f"solc {test_contracts_dir}/solc080_fail_compile.sol", check=False)
        assert result.returncode != 0
        assert "Error: Explicit type conversion not allowed" in result.stdout, (
            f"solc080_fail_compile did not fail as expected. Output: {result.stdout}"
        )


class TestVersionSwitching:
    """Test version switching functionality."""

    def test_always_install_flag(self, run_command, solc_select_path, backup_current_version):
        """Test --always-install flag functionality."""
        _ = backup_current_version  # Fixture ensures clean state
        # Safely remove 0.8.9 if it exists
        artifacts_path = solc_select_path / "artifacts"

        # Validate path to ensure we're in the right place
        path_parts = str(artifacts_path).replace(os.sep, "/").split("/")
        if len(path_parts) < 2 or path_parts[-2:] != [".solc-select", "artifacts"]:
            pytest.fail(f"Unsafe artifacts path: {artifacts_path}")

        # Remove specific solc versions (can be files or directories)
        for filename in ["solc-0.8.9", "solc-0.8.9.exe"]:
            file_path = artifacts_path / filename
            if file_path.exists():
                try:
                    if file_path.is_file():
                        file_path.chmod(0o755)  # Ensure we have permission
                        file_path.unlink()
                    elif file_path.is_dir():
                        # On macOS, solc binaries are directories
                        shutil.rmtree(file_path)
                except (PermissionError, OSError):
                    # If we can't delete, that's okay - test will still work
                    pass

        # Use with --always-install should install and switch
        result = run_command("solc-select use 0.8.9 --always-install", check=False)
        assert result.returncode == 0
        assert "Switched global version to 0.8.9" in result.stdout, (
            f"Failed to switch with --always-install. Output: {result.stdout}"
        )

    def test_use_without_install(self, run_command, solc_select_path, backup_current_version):
        """Test that 'use' fails when version is not installed."""
        _ = backup_current_version  # Fixture ensures clean state
        # Safely remove 0.8.1 if it exists
        artifacts_path = solc_select_path / "artifacts"

        # Validate path to ensure we're in the right place

        path_parts = str(artifacts_path).replace(os.sep, "/").split("/")
        if len(path_parts) < 2 or path_parts[-2:] != [".solc-select", "artifacts"]:
            pytest.fail(f"Unsafe artifacts path: {artifacts_path}")

        # Remove specific solc versions (can be files or directories)
        for filename in ["solc-0.8.1", "solc-0.8.1.exe"]:
            file_path = artifacts_path / filename
            if file_path.exists():
                try:
                    if file_path.is_file():
                        file_path.chmod(0o755)  # Ensure we have permission
                        file_path.unlink()
                    elif file_path.is_dir():
                        # On macOS, solc binaries are directories
                        shutil.rmtree(file_path)
                except (PermissionError, OSError):
                    # If we can't delete, that's okay - test will still work
                    pass

        # Use without install should fail
        result = run_command("solc-select use 0.8.1", check=False)
        assert result.returncode != 0
        assert "'0.8.1' must be installed prior to use" in result.stdout, (
            f"Did not fail as expected when version not installed. Output: {result.stdout}"
        )

        # Clean up: install 0.8.1 for other tests
        run_command("solc-select install 0.8.1", check=False)
