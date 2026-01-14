"""Platform-related domain models."""

import platform
import sys
from dataclasses import dataclass

from ..constants import LINUX_AMD64, LINUX_ARM64, MACOSX_AMD64, WINDOWS_AMD64
from ..platform_capabilities import CAPABILITY_REGISTRY, PlatformCapability, PlatformIdentifier


@dataclass(frozen=True)
class Platform:
    """Represents a target platform for Solidity compilation."""

    os_type: str  # 'linux', 'darwin', 'windows'
    architecture: str  # 'amd64', 'arm64'

    def __post_init__(self) -> None:
        valid_os = {"linux", "darwin", "windows"}
        valid_arch = {"amd64", "arm64"}
        if self.os_type not in valid_os:
            raise ValueError(f"Invalid OS type: {self.os_type}")
        if self.architecture not in valid_arch:
            raise ValueError(f"Invalid architecture: {self.architecture}")

    def get_capability(self) -> PlatformCapability:
        """Get the capability declaration for this platform."""
        identifier = self.to_identifier()
        return CAPABILITY_REGISTRY.get(str(identifier), self._create_default_capability())

    def _create_default_capability(self) -> PlatformCapability:
        """Create default capability (native-only, no emulation)."""
        platform_id = self.to_identifier()
        return PlatformCapability(
            host_platform=platform_id,
            native_support=platform_id,
            emulation_capabilities=[],
        )

    def to_identifier(self) -> PlatformIdentifier:
        """Convert to a PlatformIdentifier."""
        return PlatformIdentifier(self.os_type, self.architecture)

    @classmethod
    def current(cls) -> "Platform":
        """Get the current system platform."""
        os_mapping = {
            "linux": "linux",
            "darwin": "darwin",
            "win32": "windows",
            "cygwin": "windows",
        }
        os_type = os_mapping.get(sys.platform)
        if os_type is None:
            raise ValueError(f"Unsupported platform: {sys.platform}")
        return cls(os_type=os_type, architecture=cls._get_arch())

    @staticmethod
    def _get_arch() -> str:
        """Get the current system architecture."""
        machine = platform.machine().lower()
        arch_mapping = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }
        return arch_mapping.get(machine, machine)

    def get_soliditylang_key(self) -> str:
        """Get the platform key used by binaries.soliditylang.org."""
        platform_keys = {
            ("linux", "amd64"): LINUX_AMD64,
            ("linux", "arm64"): LINUX_ARM64,
            ("darwin", "amd64"): MACOSX_AMD64,
            ("darwin", "arm64"): MACOSX_AMD64,
            ("windows", "amd64"): WINDOWS_AMD64,
        }
        key = platform_keys.get((self.os_type, self.architecture))
        if key is None:
            raise ValueError(
                f"Unsupported platform combination: {self.os_type}-{self.architecture}"
            )
        return key
