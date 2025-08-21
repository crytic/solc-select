"""
Pytest configuration and fixtures for solc-select tests.

This module provides conservative test fixtures that closely mirror
the original bash test behavior while ensuring proper isolation and cleanup.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture(scope="session", name="solc_select_path")
def _solc_select_path() -> Path:
    """Get the path to solc-select artifacts directory."""
    virtual_env = os.environ.get("VIRTUAL_ENV")
    if virtual_env:
        return Path(virtual_env) / ".solc-select"
    return Path.home() / ".solc-select"


@pytest.fixture(scope="function")
def backup_current_version(solc_select_path: Path) -> Generator[None, None, None]:
    """
    Backup and restore the current solc version.

    This fixture ensures that each test starts with a clean state
    and doesn't affect the user's current solc configuration.
    """
    global_version_file = solc_select_path / "global-version"
    backup_file = None

    # Backup current version if it exists
    if global_version_file.exists():
        backup_file = global_version_file.with_suffix(".backup")
        shutil.copy2(global_version_file, backup_file)

    yield

    # Restore original version
    if backup_file and backup_file.exists():
        shutil.copy2(backup_file, global_version_file)
        backup_file.unlink()
    elif global_version_file.exists():
        # If there was no original version, remove the file
        global_version_file.unlink()


@pytest.fixture(scope="function")
def clean_artifacts(solc_select_path: Path) -> Generator[None, None, None]:
    """
    Clean up test artifacts after each test.

    This is used for tests that need complete isolation and
    should start with no installed versions.
    """
    artifacts_dir = solc_select_path / "artifacts"
    backup_dir = None

    # Backup existing artifacts if they exist
    if artifacts_dir.exists():
        backup_dir = artifacts_dir.with_suffix(".backup")
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.copytree(artifacts_dir, backup_dir)
        shutil.rmtree(artifacts_dir)

    yield

    # Clean up test artifacts
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)

    # Restore original artifacts if they existed
    if backup_dir and backup_dir.exists():
        shutil.copytree(backup_dir, artifacts_dir)
        shutil.rmtree(backup_dir)


@pytest.fixture(scope="function")
def run_command():
    """
    Execute shell commands and return output.

    This fixture provides a conservative way to run commands,
    exactly as the bash tests did.
    """

    def _run(
        cmd: str, check: bool = True, capture_stderr: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command and return the result.

        Args:
            cmd: Command to run
            check: Whether to raise on non-zero exit code
            capture_stderr: Whether to capture stderr

        Returns:
            CompletedProcess instance with stdout, stderr, and returncode
        """
        stderr_setting = subprocess.STDOUT if capture_stderr else subprocess.PIPE

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=False,
            stdout=subprocess.PIPE,
            stderr=stderr_setting,
            text=True,
            check=check,
        )
        return result

    return _run


@pytest.fixture(scope="session")
def test_contracts_dir() -> Path:
    """Path to test Solidity contracts."""
    return Path(__file__).parent.parent / "scripts" / "solidity_tests"


@pytest.fixture(scope="session", autouse=True)
def ensure_solc_select_installed():
    """
    Ensure solc-select is installed in development mode.

    This runs once per test session to ensure the current
    development version is being tested.
    """
    # Check if solc-select is available
    result = subprocess.run(["solc-select", "--help"], capture_output=True, text=True, check=False)

    if result.returncode != 0:
        pytest.exit("solc-select is not installed. Please run: pip install -e .")


# Platform markers for conditional test execution
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "linux: mark test to run only on Linux")
    config.addinivalue_line("markers", "macos: mark test to run only on macOS")
    config.addinivalue_line("markers", "windows: mark test to run only on Windows")


def pytest_runtest_setup(item):
    """Skip tests based on platform markers."""
    if "linux" in item.keywords and sys.platform != "linux":
        pytest.skip("Test requires Linux")
    if "macos" in item.keywords and sys.platform != "darwin":
        pytest.skip("Test requires macOS")
    if "windows" in item.keywords and sys.platform != "win32":
        pytest.skip("Test requires Windows")
