"""
Platform service for solc-select.

This module handles platform-specific operations including emulation support,
compatibility checks, and ARM64 warnings.
"""

import contextlib
import sys
from pathlib import Path

from ..constants import SOLC_SELECT_DIR
from ..models import Platform, SolcVersion


class PlatformService:
    """Service for platform-specific operations."""

    def __init__(self, platform: Platform):
        self.platform = platform

    def get_emulation_prefix(self) -> list[str]:
        """Get the command prefix for emulation if needed.

        Returns:
            List of command components to prepend for emulation
        """
        if self.platform.architecture != "arm64":
            return []

        # On macOS, let Rosetta handle it automatically
        if self.platform.os_type == "darwin":
            return []

        # On Linux, use qemu if available
        if self.platform.os_type == "linux" and self.platform.has_qemu():
            return ["qemu-x86_64"]

        return []

    def can_run_binary(self, binary_path: Path, version: SolcVersion) -> bool:
        """Check if we can run a binary on this platform.

        Args:
            binary_path: Path to the binary
            version: Version of the binary

        Returns:
            True if binary can be executed, False otherwise
        """
        # Delegate to platform's binary compatibility check
        return self.platform.can_run_binary(binary_path)

    def validate_binary_compatibility(self, binary_path: Path, version: SolcVersion) -> None:
        """Validate that a binary can be executed on this platform.

        Args:
            binary_path: Path to the binary to validate
            version: Version of the binary

        Raises:
            RuntimeError: If binary cannot be executed
        """
        if not binary_path.exists():
            raise RuntimeError("solc-select is out of date. Please run `solc-select upgrade`")

        if not self.can_run_binary(binary_path, version):
            if self.platform.os_type == "darwin" and self.platform.architecture == "arm64":
                raise RuntimeError(
                    "solc binaries previous to 0.8.5 for macOS are Intel-only. "
                    "Please install Rosetta on your Mac to continue. "
                    "Refer to the solc-select README for instructions."
                )
            else:
                raise RuntimeError(
                    f"Cannot execute solc binary for version {version} on {self.platform.os_type}-{self.platform.architecture}"
                )

    def warn_about_arm64_compatibility(self, force: bool = False) -> None:
        """Warn ARM64 users about compatibility and suggest solutions.

        Args:
            force: Whether to show warning even if already shown before
        """
        if self.platform.architecture != "arm64":
            return

        # Check if we've already warned
        warning_file = SOLC_SELECT_DIR.joinpath(".arm64_warning_shown")
        if not force and warning_file.exists():
            return

        print("\n⚠️  WARNING: ARM64 Architecture Detected", file=sys.stderr)
        print("=" * 50, file=sys.stderr)

        show_remediation = False

        if self.platform.os_type == "darwin":
            print("✓ Native ARM64 binaries available for versions 0.8.5-0.8.23", file=sys.stderr)
            print("✓ Universal binaries available for versions 0.8.24+", file=sys.stderr)

            if self.platform.has_rosetta():
                print(
                    "✓ Rosetta 2 detected - will use emulation for older versions", file=sys.stderr
                )
                print("  Note: Performance will be slower for emulated versions", file=sys.stderr)
            else:
                print(
                    "⚠ Rosetta 2 not available - versions prior to 0.8.5 are x86_64 only and will not work",
                    file=sys.stderr,
                )
                show_remediation = True

        elif self.platform.os_type == "linux":
            if self.platform.has_qemu():
                print(
                    "✓ qemu-x86_64 detected - will use emulation for x86 binaries", file=sys.stderr
                )
                print("  Note: Performance will be slower than native execution", file=sys.stderr)
            else:
                print("✗ solc binaries are x86_64 only, and qemu is not installed", file=sys.stderr)
                show_remediation = True
        else:
            show_remediation = True

        if show_remediation:
            print("\nTo use solc-select on ARM64, you can:", file=sys.stderr)
            print("  1. Install software for x86_64 emulation:", file=sys.stderr)

            if self.platform.os_type == "linux":
                print(
                    "     sudo apt-get install qemu-user-static  # Debian/Ubuntu", file=sys.stderr
                )
                print("     sudo dnf install qemu-user-static      # Fedora", file=sys.stderr)
                print("     sudo pacman -S qemu-user-static        # Arch", file=sys.stderr)
            elif self.platform.os_type == "darwin":
                print(
                    "     Use Rosetta 2 (installed automatically on Apple Silicon)", file=sys.stderr
                )

            print("  2. Use an x86_64 Docker container", file=sys.stderr)
            print("  3. Use a cloud-based development environment", file=sys.stderr)

        print("=" * 50, file=sys.stderr)
        print(file=sys.stderr)

        # Mark that we've shown the warning
        SOLC_SELECT_DIR.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            warning_file.touch()
