import platform
import subprocess
import sys
from pathlib import Path
from typing import List

from packaging.version import Version


def mac_binary_is_universal(path: Path) -> bool:
    """Check if the Mac binary is Universal or not. Will throw an exception if run on non-macOS."""
    assert sys.platform == "darwin"
    result = subprocess.run(["/usr/bin/file", str(path)], capture_output=True, check=False)
    is_universal = all(
        text in result.stdout.decode() for text in ("Mach-O universal binary", "x86_64", "arm64")
    )
    return result.returncode == 0 and is_universal


def mac_can_run_intel_binaries() -> bool:
    """Check if the Mac is Intel or M1 with available Rosetta. Will throw an exception if run on non-macOS."""
    assert sys.platform == "darwin"
    if platform.machine() == "arm64":
        # M1/M2 Mac
        result = subprocess.run(["/usr/bin/pgrep", "-q", "oahd"], capture_output=True, check=False)
        return result.returncode == 0

    # Intel Mac
    return True


def sort_versions(versions: List[str]) -> List[str]:
    """Sorts a list of versions following the component order (major/minor/patch)"""
    return sorted(versions, key=Version)
