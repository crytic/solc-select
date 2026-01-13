"""
Platform capability definitions for solc-select.

This module declares which platforms each device can execute binaries for,
including both native execution and emulation support (Rosetta, QEMU).
"""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field

# ========================================
# CAPABILITY DATACLASSES
# ========================================


@dataclass(frozen=True)
class PlatformIdentifier:
    """Unique identifier for a platform (OS + architecture).

    Examples: 'linux-amd64', 'darwin-arm64', 'windows-amd64'
    """

    os_type: str  # 'linux', 'darwin', 'windows'
    architecture: str  # 'amd64', 'arm64', '386'


@dataclass(frozen=True)
class EmulationCapability:
    """Describes emulation support for running foreign platform binaries.

    Example: Linux ARM64 can run linux-amd64 binaries via QEMU.
    """

    target_platform: PlatformIdentifier  # Platform that can be emulated
    emulation_type: str  # 'rosetta', 'qemu'
    detector: Callable[[], bool]  # Function to check if emulation available
    command_prefix: list[str]  # Command prefix for emulation (e.g., ["qemu-x86_64"])
    performance_note: str | None = None  # Warning message for users


@dataclass
class PlatformCapability:
    """Declares which platforms a device can execute binaries for.

    Supports both native execution and emulated platforms.

    Example for Linux ARM64 with QEMU:
        - native_support: linux-arm64
        - emulation_capabilities: [linux-amd64 via QEMU]
    """

    host_platform: PlatformIdentifier  # The actual hardware platform
    native_support: PlatformIdentifier  # Always can run native binaries
    emulation_capabilities: list[EmulationCapability] = field(default_factory=list)

    def get_runnable_platforms(self) -> list[PlatformIdentifier]:
        """Get all platforms this device can execute, prioritized.

        Returns native first, then emulated platforms (only if emulator available).

        Returns:
            List of PlatformIdentifier, native first
        """
        platforms = [self.native_support]

        # Add emulated platforms with available emulators
        for ec in self.emulation_capabilities:
            if ec.detector():
                platforms.append(ec.target_platform)

        return platforms

    def get_emulation_for_platform(self, target: PlatformIdentifier) -> EmulationCapability | None:
        """Get emulation info for a target platform.

        Args:
            target: Platform to check

        Returns:
            EmulationCapability if target requires emulation, None if native
        """
        if target == self.native_support:
            return None
        return next(
            (ec for ec in self.emulation_capabilities if ec.target_platform == target),
            None,
        )


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
