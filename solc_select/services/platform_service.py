"""
Platform service for solc-select.

This module handles platform-specific operations including emulation support,
compatibility checks, and ARM64 warnings.
"""

import contextlib
import sys
from pathlib import Path

from ..constants import SOLC_SELECT_DIR
from ..models import Platform, SolcArtifact


class PlatformService:
    """Service for platform-specific operations."""

    def __init__(self, platform: Platform):
        self.platform = platform

    def get_emulation_prefix(self, artifact: SolcArtifact) -> list[str]:
        """Get the command prefix for emulation based on artifact's emulation info.

        Args:
            artifact: Artifact with emulation information

        Returns:
            List of command components to prepend for emulation

        Raises:
            RuntimeError: If emulation required but not available
        """
        # If no emulation needed (native binary), return empty list
        if artifact.emulation is None:
            return []

        # Check if emulation is available
        if not artifact.emulation.detector():
            raise RuntimeError(
                f"Emulation via {artifact.emulation.emulation_type} is required but not available. "
                f"Please install {artifact.emulation.emulation_type} to run this version."
            )

        return artifact.emulation.command_prefix

    def validate_binary_compatibility(self, binary_path: Path, artifact: SolcArtifact) -> None:
        """Validate that a binary can be executed on this platform.

        Args:
            binary_path: Path to the binary to validate
            artifact: Artifact with emulation information

        Raises:
            RuntimeError: If binary cannot be executed
        """
        if not binary_path.exists():
            raise RuntimeError("solc-select is out of date. Please run `solc-select upgrade`")

        # If emulation is required, check if it's available
        if artifact.emulation is not None:
            if not artifact.emulation.detector():
                if self.platform.os_type == "darwin" and self.platform.architecture == "arm64":
                    raise RuntimeError(
                        "solc binaries previous to 0.8.5 for macOS are Intel-only. "
                        "Please install Rosetta on your Mac to continue. "
                        "Refer to the solc-select README for instructions."
                    )
                elif self.platform.os_type == "linux" and self.platform.architecture == "arm64":
                    raise RuntimeError(
                        "solc binaries previous to 0.8.31 for Linux are Intel-only. "
                        "Please install QEMU on your computer to continue. "
                        "Refer to the solc-select README for instructions."
                    )
                else:
                    raise RuntimeError(
                        f"Cannot execute solc binary for version {artifact.version} "
                        f"on {self.platform.os_type}-{self.platform.architecture}. "
                        f"Emulation via {artifact.emulation.emulation_type} is required but not available."
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

        # Import here to avoid circular import
        from ..platform_capabilities import detect_qemu, detect_rosetta

        print("\n⚠️  WARNING: ARM64 Architecture Detected", file=sys.stderr)
        print("=" * 50, file=sys.stderr)

        show_remediation = False

        if self.platform.os_type == "darwin":
            print("✓ Native ARM64 binaries available for versions 0.8.5-0.8.23", file=sys.stderr)
            print("✓ Universal binaries available for versions 0.8.24+", file=sys.stderr)

            if detect_rosetta():
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
            print("✓ Native ARM64 binaries available for versions 0.8.31+", file=sys.stderr)

            if detect_qemu():
                print(
                    "✓ qemu-x86_64 detected - will use emulation for versions < 0.8.31",
                    file=sys.stderr,
                )
                print("  Note: Performance will be slower for emulated versions", file=sys.stderr)
            else:
                print(
                    "⚠ Versions < 0.8.31 require x86_64 emulation, but qemu is not installed",
                    file=sys.stderr,
                )
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
