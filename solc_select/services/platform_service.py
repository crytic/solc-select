"""Platform service for solc-select."""

import contextlib
import sys

from ..constants import SOLC_SELECT_DIR
from ..models.artifacts import SolcArtifactOnDisk
from ..models.platforms import Platform
from ..platform_capabilities import detect_qemu, detect_rosetta


class PlatformService:
    """Service for platform-specific operations."""

    def __init__(self, platform: Platform):
        self.platform = platform

    def get_emulation_prefix(self, artifact: SolcArtifactOnDisk) -> list[str]:
        """Get the command prefix for emulation based on artifact's emulation info."""
        if artifact.emulation is None:
            return []

        if not artifact.emulation.detector():
            raise RuntimeError(
                f"Emulation via {artifact.emulation.emulation_type} is required but not available. "
                f"Please install {artifact.emulation.emulation_type} to run this version. "
                "Refer to the solc-select README for instructions."
            )

        return artifact.emulation.command_prefix

    def warn_about_arm64_compatibility(self, force: bool = False) -> None:
        """Warn ARM64 users about compatibility and suggest solutions."""
        if self.platform.architecture != "arm64":
            return

        warning_file = SOLC_SELECT_DIR / ".arm64_warning_shown"
        if not force and warning_file.exists():
            return

        print("\n[!] WARNING: ARM64 Architecture Detected", file=sys.stderr)
        print("=" * 50, file=sys.stderr)

        show_remediation = self._print_platform_status()

        if show_remediation:
            self._print_remediation_steps()

        print("=" * 50, file=sys.stderr)
        print(file=sys.stderr)

        # Mark that we've shown the warning
        SOLC_SELECT_DIR.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(OSError):
            warning_file.touch()

    def _print_platform_status(self) -> bool:
        """Print platform-specific ARM64 status and return whether remediation is needed."""
        if self.platform.os_type == "darwin":
            print("[+] Native ARM64 binaries available for versions 0.8.5-0.8.23", file=sys.stderr)
            print("[+] Universal binaries available for versions 0.8.24+", file=sys.stderr)

            if detect_rosetta():
                print(
                    "[+] Rosetta 2 detected - will use emulation for older versions",
                    file=sys.stderr,
                )
                print("  Note: Performance will be slower for emulated versions", file=sys.stderr)
                return False

            print(
                "[!] Rosetta 2 not available - versions prior to 0.8.5 are x86_64 only and will not work",
                file=sys.stderr,
            )
            return True

        if self.platform.os_type == "linux":
            print("[+] Native ARM64 binaries available for versions 0.8.31+", file=sys.stderr)

            if detect_qemu():
                print(
                    "[+] qemu-x86_64 detected - will use emulation for versions < 0.8.31",
                    file=sys.stderr,
                )
                print("  Note: Performance will be slower for emulated versions", file=sys.stderr)
                return False

            print(
                "[!] Versions < 0.8.31 require x86_64 emulation, but qemu is not installed",
                file=sys.stderr,
            )
            return True

        return True

    def _print_remediation_steps(self) -> None:
        """Print remediation steps for ARM64 emulation setup."""
        print("\nTo use solc-select on ARM64, you can:", file=sys.stderr)
        print("  1. Install software for x86_64 emulation:", file=sys.stderr)

        if self.platform.os_type == "linux":
            print("     sudo apt-get install qemu-user  # Debian/Ubuntu", file=sys.stderr)
            print("     sudo dnf install qemu-user      # Fedora", file=sys.stderr)
            print("     sudo pacman -S qemu-user        # Arch", file=sys.stderr)
        elif self.platform.os_type == "darwin":
            print("     Use Rosetta 2 (installed automatically on Apple Silicon)", file=sys.stderr)

        print("  2. Use an x86_64 Docker container", file=sys.stderr)
        print("  3. Use a cloud-based development environment", file=sys.stderr)
