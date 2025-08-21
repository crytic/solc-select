#!/usr/bin/env python3
"""
Simple test runner for solc-select.

This script provides an easy way to run the pytest test suite
with appropriate options.
"""

import subprocess
import sys


def main():
    """Run the test suite."""
    # Basic pytest command
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]

    # Add platform-specific marker based on current platform
    if sys.platform == "linux":
        # Run all non-Windows, non-macOS tests plus Linux tests
        cmd.extend(["-m", "not (windows or macos)"])
    elif sys.platform == "darwin":
        # Run all non-Windows, non-Linux tests plus macOS tests
        cmd.extend(["-m", "not (windows or linux)"])
    elif sys.platform == "win32":
        # Run all non-Linux, non-macOS tests plus Windows tests
        cmd.extend(["-m", "not (linux or macos)"])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
