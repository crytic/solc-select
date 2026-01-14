"""Platform capability definitions for solc-select."""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlatformIdentifier:
    """Unique identifier for a platform (OS + architecture)."""

    os_type: str  # 'linux', 'darwin', 'windows'
    architecture: str  # 'amd64', 'arm64'

    def __str__(self) -> str:
        return f"{self.os_type}-{self.architecture}"


@dataclass(frozen=True)
class EmulationCapability:
    """Describes emulation support for running foreign platform binaries."""

    target_platform: PlatformIdentifier
    emulation_type: str  # 'rosetta', 'qemu'
    detector: Callable[[], bool]
    command_prefix: list[str]
    performance_note: str | None = None


@dataclass
class PlatformCapability:
    """Declares which platforms a device can execute binaries for."""

    host_platform: PlatformIdentifier
    native_support: PlatformIdentifier
    emulation_capabilities: list[EmulationCapability] = field(default_factory=list)

    def get_runnable_platforms(self) -> list[PlatformIdentifier]:
        """Get all platforms this device can execute (native first, then emulated)."""
        platforms = [self.native_support]
        for ec in self.emulation_capabilities:
            if ec.detector():
                platforms.append(ec.target_platform)
        return platforms

    def get_emulation_for_platform(self, target: PlatformIdentifier) -> EmulationCapability | None:
        """Get emulation info for a target platform, or None if native."""
        if target == self.native_support:
            return None
        return next(
            (ec for ec in self.emulation_capabilities if ec.target_platform == target),
            None,
        )


def detect_rosetta() -> bool:
    """Check if Rosetta 2 is available on macOS ARM64."""
    try:
        result = subprocess.run(["pgrep", "-q", "oahd"], capture_output=True, check=False)
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def detect_qemu() -> bool:
    """Check if qemu-x86_64 is available on Linux ARM64."""
    try:
        result = subprocess.run(
            ["which", "qemu-x86_64"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


DARWIN_ARM64_CAPABILITY = PlatformCapability(
    host_platform=PlatformIdentifier("darwin", "arm64"),
    native_support=PlatformIdentifier("darwin", "arm64"),
    emulation_capabilities=[
        EmulationCapability(
            target_platform=PlatformIdentifier("darwin", "amd64"),
            emulation_type="rosetta",
            detector=detect_rosetta,
            command_prefix=[],  # Rosetta is transparent
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
            command_prefix=["qemu-x86_64"],
            performance_note="Performance may be slower for emulated x86 binaries",
        ),
    ],
)

CAPABILITY_REGISTRY: dict[str, PlatformCapability] = {
    "darwin-arm64": DARWIN_ARM64_CAPABILITY,
    "linux-arm64": LINUX_ARM64_CAPABILITY,
}
