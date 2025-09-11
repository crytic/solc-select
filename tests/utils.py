"""
Utility functions for solc-select tests.

This module contains helper functions that are not pytest fixtures
but are used across multiple test files.
"""

import os
import subprocess
from typing import Any, Dict


def run_in_venv(
    venv_info: Dict[str, Any], cmd: str, check: bool = True, **kwargs: Any
) -> subprocess.CompletedProcess[str]:
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


def run_command(
    cmd: str, check: bool = True, capture_stderr: bool = True
) -> subprocess.CompletedProcess[str]:
    """
    Execute shell commands and return output.

    This function is kept for backward compatibility with tests using isolated_solc_data.
    For tests using isolated_python_env, use run_in_venv instead.

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
