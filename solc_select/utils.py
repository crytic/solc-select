import platform
import subprocess
import sys
from pathlib import Path
from typing import List

import requests
from packaging.version import Version
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def create_http_session() -> requests.Session:
    """Create a new HTTP session with retry logic for rate limits and server errors."""
    session = requests.Session()

    # Configure retry strategy for 429s and server errors
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set standard timeouts (connect_timeout, read_timeout)
    session.timeout = (10, 60)  # 10s connection, 60s read for downloads

    return session


def get_arch() -> str:
    """Get the current system architecture."""
    machine = platform.machine().lower()
    if machine in ["x86_64", "amd64"]:
        return "amd64"
    elif machine in ["aarch64", "arm64"]:
        return "arm64"
    elif machine in ["i386", "i686"]:
        return "386"
    return machine


def mac_binary_is_universal(path: Path) -> bool:
    """Check if the Mac binary is Universal or not. Will throw an exception if run on non-macOS."""
    assert sys.platform == "darwin"
    result = subprocess.run(["/usr/bin/file", str(path)], capture_output=True, check=False)
    is_universal = all(
        text in result.stdout.decode() for text in ("Mach-O universal binary", "x86_64", "arm64")
    )
    return result.returncode == 0 and is_universal


def mac_binary_is_native(path: Path):
    """Check if the Mac binary matches the current system architecture. Will throw an exception if run on non-macOS."""
    assert sys.platform == "darwin"
    result = subprocess.run(["/usr/bin/file", str(path)], capture_output=True, check=False)
    output = result.stdout.decode()

    arch_in_file = "arm64" if get_arch() == "arm64" else "x86_64"
    is_native = "Mach-O" in output and arch_in_file in output
    return result.returncode == 0 and is_native


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
