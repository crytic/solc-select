"""
Pytest configuration and fixtures for solc-select tests.

This module provides isolated test environments that prevent
threading issues when tests run in parallel.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

import pytest


@pytest.fixture(scope="function")
def isolated_solc_data(tmp_path, monkeypatch):
    """
    Create isolated solc-select data environment for each test.

    Uses VIRTUAL_ENV to redirect solc-select to a temporary directory.
    This provides fast isolation for tests that only need solc data separation.
    """
    temp_venv = tmp_path / "venv"
    temp_venv.mkdir()

    # Redirect solc-select to use our temp directory via VIRTUAL_ENV
    monkeypatch.setenv("VIRTUAL_ENV", str(temp_venv))

    yield temp_venv


@pytest.fixture(scope="function")
def isolated_python_env(tmp_path):
    """
    Create completely isolated Python environment for tests that install/uninstall solc-select.

    Creates a real virtual environment to prevent pip install/uninstall race conditions.
    This is slower but necessary for tests like upgrade tests.
    """
    venv_path = tmp_path / "test_venv"

    # Create real virtual environment
    subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)

    # Get paths for the virtual environment
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        python_exe = venv_path / "bin" / "python"
        pip_exe = venv_path / "bin" / "pip"

    yield {
        "venv_path": venv_path,
        "python": str(python_exe),
        "pip": str(pip_exe),
        "env": {
            "VIRTUAL_ENV": str(venv_path),
            "PATH": str(venv_path / ("Scripts" if sys.platform == "win32" else "bin"))
            + os.pathsep
            + os.environ.get("PATH", ""),
        },
    }


def run_in_venv(
    venv_info: Dict, cmd: str, check: bool = True, **kwargs
) -> subprocess.CompletedProcess:
    """
    Run a command in an isolated virtual environment.

    Args:
        venv_info: Dictionary from isolated_python_env fixture
        cmd: Command to run
        check: Whether to raise on non-zero exit code
        **kwargs: Additional arguments to subprocess.run

    Returns:
        CompletedProcess instance with stdout, stderr, and returncode
    """
    env = os.environ.copy()
    env.update(venv_info["env"])

    try:
        return subprocess.run(
            cmd, shell=True, env=env, capture_output=True, text=True, check=check, **kwargs
        )
    except subprocess.CalledProcessError as e:
        print("Command failed with CalledProcessError.")
        print("Exit code:", e.returncode)
        print("Command:", e.cmd)
        print("Stdout:", e.stdout)
        print("Stderr:", e.stderr)
        raise


@pytest.fixture(scope="function")
def run_command():
    """
    Execute shell commands and return output.

    This fixture is kept for backward compatibility with tests using isolated_solc_data.
    For tests using isolated_python_env, use run_in_venv instead.
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
