"""
Test Solidity compiler version-specific functionality.

This module tests compilation with different Solidity versions.
"""

from .utils import run_command


class TestCompilerVersions:
    """Test compilation with different Solidity compiler versions."""

    def test_solc_045(self, test_contracts_dir, isolated_solc_data):
        """Test Solidity 0.4.5 compilation behavior."""
        # Switch to 0.4.5
        result = run_command("solc-select use 0.4.5 --always-install", check=False)
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

    def test_solc_050(self, test_contracts_dir, isolated_solc_data):
        """Test Solidity 0.5.0 compilation behavior."""
        # Switch to 0.5.0
        result = run_command("solc-select use 0.5.0 --always-install", check=False)
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

    def test_solc_060(self, test_contracts_dir, isolated_solc_data):
        """Test Solidity 0.6.0 compilation behavior."""
        # Switch to 0.6.0
        result = run_command("solc-select use 0.6.0 --always-install", check=False)
        assert result.returncode == 0, f"Failed to switch to 0.6.0: {result.stdout}"

        # Test try/catch feature (new in 0.6.0)
        result = run_command(f"solc {test_contracts_dir}/solc060_success_trycatch.sol", check=False)
        assert result.returncode == 0, f"solc060_success_trycatch failed with: {result.stdout}"

        # Test receive function (new in 0.6.0)
        result = run_command(f"solc {test_contracts_dir}/solc060_success_receive.sol", check=False)
        assert result.returncode == 0, f"solc060_success_receive failed with: {result.stdout}"

    def test_solc_070(self, test_contracts_dir, isolated_solc_data):
        """Test Solidity 0.7.0 compilation behavior."""
        # Switch to 0.7.0
        result = run_command("solc-select use 0.7.0 --always-install", check=False)
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

    def test_solc_080(self, test_contracts_dir, isolated_solc_data):
        """Test Solidity 0.8.0 compilation behavior."""
        # Switch to 0.8.0
        result = run_command("solc-select use 0.8.0 --always-install", check=False)
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

    def test_solc_0831_if_contains_prerelease(self, test_contracts_dir, isolated_solc_data):
        """Test Solidity 0.8.31 compilation behavior."""
        # Switch to 0.8.31
        result = run_command("solc-select use 0.8.31 --always-install", check=False)
        assert result.returncode == 0, f"Failed to switch to 0.8.31: {result.stdout}"


class TestVersionSwitching:
    """Test version switching functionality."""

    def test_always_install_flag(self, isolated_solc_data):
        """Test --always-install flag functionality."""
        # In isolated environment, 0.8.9 won't be installed initially
        # No need for complex path validation or manual cleanup

        # Use with --always-install should install and switch
        result = run_command("solc-select use 0.8.9 --always-install", check=False)
        assert result.returncode == 0
        assert "Switched global version to 0.8.9" in result.stdout, (
            f"Failed to switch with --always-install. Output: {result.stdout}"
        )

    def test_use_without_install(self, isolated_solc_data):
        """Test that 'use' fails when version is not installed."""
        # In isolated environment, 0.8.1 won't be installed initially
        # No need for complex cleanup logic

        # Use without install should fail
        result = run_command("solc-select use 0.8.1", check=False)
        assert result.returncode != 0
        assert "'0.8.1' must be installed prior to use" in result.stdout, (
            f"Did not fail as expected when version not installed. Output: {result.stdout}"
        )
