"""
Pytest configuration and fixtures for solc-select tests.

This module provides isolated test environments that prevent
threading issues when tests run in parallel.
"""

import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture(scope="function")
def isolated_solc_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[Path, None, None]:
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
def isolated_python_env(tmp_path: Path) -> Generator[dict[str, Any], None, None]:
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

    # Upgrade pip in the virtual environment
    subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True)

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


@pytest.fixture(scope="session")
def test_contracts_dir() -> Path:
    """Path to test Solidity contracts."""
    return Path(__file__).parent.parent / "solidity_tests"


# Platform markers for conditional test execution
def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "linux: mark test to run only on Linux")
    config.addinivalue_line("markers", "macos: mark test to run only on macOS")
    config.addinivalue_line("markers", "windows: mark test to run only on Windows")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests based on platform markers."""
    if "linux" in item.keywords and sys.platform != "linux":
        pytest.skip("Test requires Linux")
    if "macos" in item.keywords and sys.platform != "darwin":
        pytest.skip("Test requires macOS")
    if "windows" in item.keywords and sys.platform != "win32":
        pytest.skip("Test requires Windows")
