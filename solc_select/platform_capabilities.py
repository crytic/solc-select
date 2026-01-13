"""
Platform capability definitions for solc-select.

This module declares which platforms each device can execute binaries for,
including both native execution and emulation support (Rosetta, QEMU).
"""

import subprocess

from .models import EmulationCapability, Platform, PlatformCapability, PlatformIdentifier


# ========================================
# EMULATION DETECTORS
# ========================================


def detect_rosetta() -> bool:
    """Check if Rosetta 2 is available on macOS ARM64.

    Rosetta 2 allows macOS ARM64 to run x86_64 binaries transparently.

    Returns:
        True if Rosetta 2 daemon is running, False otherwise
    """
    try:
        result = subprocess.run(["pgrep", "-q", "oahd"], capture_output=True, check=False)
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def detect_qemu() -> bool:
    """Check if qemu-x86_64 is available on Linux ARM64.

    QEMU allows Linux ARM64 to run x86_64 binaries via emulation.

    Returns:
        True if qemu-x86_64 is in PATH, False otherwise
    """
    try:
        result = subprocess.run(
            ["which", "qemu-x86_64"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


# ========================================
# PLATFORM CAPABILITY DEFINITIONS
# ========================================


DARWIN_ARM64_CAPABILITY = PlatformCapability(
    host_platform=PlatformIdentifier("darwin", "arm64"),
    native_support=PlatformIdentifier("darwin", "arm64"),
    emulation_capabilities=[
        EmulationCapability(
            target_platform=PlatformIdentifier("darwin", "amd64"),
            emulation_type="rosetta",
            detector=detect_rosetta,
            command_prefix=[],  # Rosetta is transparent - no command prefix needed
            performance_note="Performance may be slower for x86 binaries via Rosetta",
        ),
    ],
)


LINUX_ARM64_CAPABILITY = PlatformCapability(
    host_platform=PlatformIdentifier("linux", "arm64"),
    native_support=PlatformIdentifier("linux", "arm64"),
    emulation_capabilities=[
        EmulationCapability(
            target_platform=PlatformIdentifier("linux", "amd64"),
            emulation_type="qemu",
            detector=detect_qemu,
            command_prefix=["qemu-x86_64"],  # QEMU requires explicit command prefix
            performance_note="Performance may be slower for emulated x86 binaries",
        ),
    ],
)


# ========================================
# CAPABILITY REGISTRATION
# ========================================


def register_capabilities() -> None:
    """Register all platform capabilities with the Platform class.

    This function should be called at module import time to ensure
    capabilities are available when Platform.get_capability() is called.
    """
    Platform.register_capability(DARWIN_ARM64_CAPABILITY)
    Platform.register_capability(LINUX_ARM64_CAPABILITY)


# Auto-register capabilities when module is imported
register_capabilities()
