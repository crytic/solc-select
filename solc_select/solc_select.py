import argparse
import contextlib
import hashlib
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zipfile import ZipFile

from Crypto.Hash import keccak
from packaging.version import Version

from .constants import (
    ALLOY_ARM64_MAX_VERSION,
    ALLOY_ARM64_MIN_VERSION,
    ALLOY_SOLC_ARTIFACTS,
    ALLOY_SOLC_JSON,
    ARTIFACTS_DIR,
    CRYTIC_SOLC_ARTIFACTS,
    CRYTIC_SOLC_JSON,
    EARLIEST_RELEASE,
    LINUX_AMD64,
    MACOSX_AMD64,
    SOLC_SELECT_DIR,
    WINDOWS_AMD64,
)
from .utils import (
    create_http_session,
    get_arch,
    mac_binary_is_native,
    mac_binary_is_universal,
    mac_can_run_intel_binaries,
)

Path.mkdir(ARTIFACTS_DIR, parents=True, exist_ok=True)


def check_emulation_available() -> bool:
    """Check if x86_64 emulation is available."""
    if get_arch() != "arm64":
        return False

    # On macOS, check for Rosetta 2
    if sys.platform == "darwin":
        return mac_can_run_intel_binaries()

    # On Linux, check for qemu-x86_64
    try:
        result = subprocess.run(
            ["which", "qemu-x86_64"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except (FileNotFoundError, OSError):
        return False


def get_emulation_prefix() -> List[str]:
    """Get the command prefix for emulation if needed."""
    if get_arch() != "arm64":
        return []

    # On macOS, let Rosetta handle it automatically
    if sys.platform == "darwin":
        return []

    # On Linux, use qemu
    if sys.platform.startswith("linux") and check_emulation_available():
        return ["qemu-x86_64"]

    return []


def warn_about_arm64(force: bool = False) -> None:
    """Warn ARM64 users about compatibility and suggest solutions."""
    if get_arch() != "arm64":
        return

    # Check if we've already warned
    warning_file = SOLC_SELECT_DIR.joinpath(".arm64_warning_shown")
    if not force and warning_file.exists():
        return

    print("\n⚠️  WARNING: ARM64 Architecture Detected", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    show_remediation = False

    if sys.platform == "darwin":
        print("✓ Native ARM64 binaries available for versions 0.8.5-0.8.23", file=sys.stderr)
        print("✓ Universal binaries available for versions 0.8.24+", file=sys.stderr)
        if check_emulation_available():
            print("✓ Rosetta 2 detected - will use emulation for older versions", file=sys.stderr)
            print("  Note: Performance will be slower for emulated versions", file=sys.stderr)
        else:
            print(
                "⚠ Rosetta 2 not available - versions prior to 0.8.5 are x86_64 only and will not work",
                file=sys.stderr,
            )
            show_remediation = True
    elif sys.platform == "linux":
        if check_emulation_available():
            print("✓ qemu-x86_64 detected - will use emulation for x86 binaries", file=sys.stderr)
            print("  Note: Performance will be slower than native execution", file=sys.stderr)
        else:
            print("✗ solc binaries are x86_64 only, and qemu is not installed", file=sys.stderr)
            show_remediation = True
    else:
        show_remediation = True

    if show_remediation:
        print("\nTo use solc-select on ARM64, you can:", file=sys.stderr)
        print("  1. Install software for x86_64 emulation:", file=sys.stderr)
        if sys.platform == "linux":
            print("     sudo apt-get install qemu-user-static  # Debian/Ubuntu", file=sys.stderr)
            print("     sudo dnf install qemu-user-static      # Fedora", file=sys.stderr)
            print("     sudo pacman -S qemu-user-static        # Arch", file=sys.stderr)
        elif sys.platform == "darwin":
            print("     Use Rosetta 2 (installed automatically on Apple Silicon)", file=sys.stderr)
        print("  2. Use an x86_64 Docker container", file=sys.stderr)
        print("  3. Use a cloud-based development environment", file=sys.stderr)
    print("=" * 50, file=sys.stderr)
    print(file=sys.stderr)

    # Mark that we've shown the warning
    with contextlib.suppress(OSError):
        warning_file.touch()


def halt_old_architecture(path: Path) -> None:
    if not Path.is_file(path):
        raise argparse.ArgumentTypeError(
            "solc-select is out of date. Please run `solc-select upgrade`"
        )


def halt_incompatible_system(path: Path) -> None:
    if soliditylang_platform() == MACOSX_AMD64:
        # If Rosetta is available, we can run all solc versions
        if mac_can_run_intel_binaries():
            return

        # If this is a newer universal solc (>=0.8.24) we can always run it
        # https://github.com/ethereum/solidity/issues/12291#issuecomment-2223328961
        if mac_binary_is_universal(path):
            return

        # If the binary is native to this architecture, we can run it
        if mac_binary_is_native(path):
            return

        raise argparse.ArgumentTypeError(
            "solc binaries previous to 0.8.5 for macOS are Intel-only. Please install Rosetta on your Mac to continue. Refer to the solc-select README for instructions."
        )
    # TODO: check for Linux aarch64 (e.g. RPi), presence of QEMU+binfmt


def upgrade_architecture() -> None:
    currently_installed = installed_versions()
    if len(currently_installed) > 0:
        if Path.is_file(ARTIFACTS_DIR.joinpath(f"solc-{currently_installed[0]}")):
            shutil.rmtree(ARTIFACTS_DIR)
            Path.mkdir(ARTIFACTS_DIR, exist_ok=True)
            install_artifacts(currently_installed)
            print("solc-select is now up to date! 🎉")
        else:
            print("solc-select is already up to date")
    else:
        raise argparse.ArgumentTypeError("Run `solc-select install --help` for more information")


def current_version() -> Tuple[str, str]:
    source = "SOLC_VERSION"
    version = os.environ.get(source)
    if not version:
        source_path = SOLC_SELECT_DIR.joinpath("global-version")
        source = source_path.as_posix()
        if Path.is_file(source_path):
            with open(source_path, encoding="utf-8") as f:
                version = f.read().strip()
        else:
            raise argparse.ArgumentTypeError(
                "No solc version set. Run `solc-select use VERSION` or set SOLC_VERSION environment variable."
            )
    versions = installed_versions()
    if version not in versions:
        raise argparse.ArgumentTypeError(
            f"\nVersion '{version}' not installed (set by {source})."
            f"\nRun `solc-select install {version}`."
            f"\nOr use one of the following versions: {versions}"
        )
    return version, source


def installed_versions() -> List[str]:
    return [
        f.replace("solc-", "") for f in sorted(os.listdir(ARTIFACTS_DIR)) if f.startswith("solc-")
    ]


def artifact_path(version: str) -> Path:
    return ARTIFACTS_DIR.joinpath(f"solc-{version}", f"solc-{version}")


def install_artifacts(versions: List[str], silent: bool = False) -> bool:
    # Warn ARM64 users about compatibility on first install
    if get_arch() == "arm64" and not silent:
        warn_about_arm64()

    releases = get_available_versions()
    versions = [get_latest_release() if ver == "latest" else ver for ver in versions]

    if "all" not in versions:
        not_available_versions = list(set(versions).difference([*releases]))
        if not_available_versions:
            print(f"{', '.join(not_available_versions)} solc versions are not available.")
            return False

    already_installed = installed_versions()
    for version, artifact in releases.items():
        if "all" not in versions:
            if versions and version not in versions:
                continue

        artifact_file_dir = ARTIFACTS_DIR.joinpath(f"solc-{version}")

        if version in already_installed:
            if os.listdir(artifact_file_dir):
                if not silent:
                    print(f"Version '{version}' is already installed, skipping...")
                continue

        (url, _) = get_url(version, artifact)

        if is_linux_0818(version):
            url = CRYTIC_SOLC_ARTIFACTS + artifact
            print(url)

        Path.mkdir(artifact_file_dir, parents=True, exist_ok=True)
        if not silent:
            print(f"Installing solc '{version}'...")
        session = create_http_session()
        response = session.get(url)
        response.raise_for_status()

        with open(artifact_file_dir.joinpath(f"solc-{version}"), "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        verify_checksum(version)

        if is_older_windows(version):
            with ZipFile(artifact_file_dir.joinpath(f"solc-{version}"), "r") as zip_ref:
                zip_ref.extractall(path=artifact_file_dir)
                zip_ref.close()
            Path.unlink(artifact_file_dir.joinpath(f"solc-{version}"))
            Path(artifact_file_dir.joinpath("solc.exe")).rename(
                Path(artifact_file_dir.joinpath(f"solc-{version}")),
            )
        else:
            Path.chmod(artifact_file_dir.joinpath(f"solc-{version}"), 0o775)
        if not silent:
            print(f"Version '{version}' installed.")
    return True


def is_older_linux(version: str) -> bool:
    return soliditylang_platform() == LINUX_AMD64 and Version(version) <= Version("0.4.10")


def is_linux_0818(version: str) -> bool:
    return soliditylang_platform() == LINUX_AMD64 and Version(version) == Version("0.8.18")


def is_older_windows(version: str) -> bool:
    return soliditylang_platform() == WINDOWS_AMD64 and Version(version) <= Version("0.7.1")


def is_alloy_aarch64_version(version: str) -> bool:
    return (
        sys.platform == "darwin"
        and get_arch() == "arm64"
        and Version(ALLOY_ARM64_MIN_VERSION) <= Version(version) <= Version(ALLOY_ARM64_MAX_VERSION)
    )


def verify_checksum(version: str) -> None:
    (sha256_hash, keccak256_hash) = get_soliditylang_checksums(version)

    # calculate sha256 and keccak256 checksum of the local file
    with open(ARTIFACTS_DIR.joinpath(f"solc-{version}", f"solc-{version}"), "rb") as f:
        sha256_factory = hashlib.sha256()
        keccak_factory = keccak.new(digest_bits=256)

        # 1024000(~1MB chunk)
        for chunk in iter(lambda: f.read(1024000), b""):
            sha256_factory.update(chunk)
            keccak_factory.update(chunk)

        local_sha256_file_hash = sha256_factory.hexdigest()
        local_keccak256_file_hash = keccak_factory.hexdigest()

    if sha256_hash != local_sha256_file_hash:
        raise argparse.ArgumentTypeError(
            f"Error: SHA256 checksum mismatch {soliditylang_platform()} - {version}"
        )

    if keccak256_hash is not None and keccak256_hash != local_keccak256_file_hash:
        raise argparse.ArgumentTypeError(
            f"Error: Keccak256 checksum mismatch {soliditylang_platform()} - {version}"
        )


def get_soliditylang_checksums(version: str) -> Tuple[str, Optional[str]]:
    (_, list_url) = get_url(version=version)
    session = create_http_session()
    response = session.get(list_url)
    response.raise_for_status()
    builds = response.json()["builds"]
    matches = list(filter(lambda b: b["version"] == version and "prerelease" not in b, builds))

    if not matches or not matches[0]["sha256"]:
        raise argparse.ArgumentTypeError(
            f"Error: Unable to retrieve checksum for {soliditylang_platform()} - {version}"
        )

    sha256_hash = matches[0]["sha256"]
    keccak256_hash = matches[0].get("keccak256")

    # Normalize checksums by removing 0x prefix if present
    if sha256_hash and sha256_hash.startswith("0x"):
        sha256_hash = sha256_hash[2:]
    if keccak256_hash and keccak256_hash.startswith("0x"):
        keccak256_hash = keccak256_hash[2:]

    return sha256_hash, keccak256_hash


def get_url(version: str = "", artifact: str = "") -> Tuple[str, str]:
    if soliditylang_platform() == LINUX_AMD64:
        if version != "" and is_older_linux(version):
            return (
                CRYTIC_SOLC_ARTIFACTS + artifact,
                CRYTIC_SOLC_JSON,
            )
    elif sys.platform == "darwin" and get_arch() == "arm64":
        if version != "" and is_alloy_aarch64_version(version):
            return (
                ALLOY_SOLC_ARTIFACTS + artifact,
                ALLOY_SOLC_JSON,
            )
        else:
            # Fall back to Intel binaries for versions outside supported range
            return (
                f"https://binaries.soliditylang.org/{MACOSX_AMD64}/{artifact}",
                f"https://binaries.soliditylang.org/{MACOSX_AMD64}/list.json",
            )
    return (
        f"https://binaries.soliditylang.org/{soliditylang_platform()}/{artifact}",
        f"https://binaries.soliditylang.org/{soliditylang_platform()}/list.json",
    )


def switch_global_version(version: str, always_install: bool, silent: bool = False) -> None:
    if version == "latest":
        version = get_latest_release()

    # Check version against platform minimum even if installed
    if version in installed_versions():
        with open(f"{SOLC_SELECT_DIR}/global-version", "w", encoding="utf-8") as f:
            f.write(version)
        if not silent:
            print("Switched global version to", version)
    elif version in get_available_versions():
        if always_install:
            install_artifacts([version], silent)
            switch_global_version(version, always_install, silent)
        else:
            raise argparse.ArgumentTypeError(f"'{version}' must be installed prior to use.")
    else:
        raise argparse.ArgumentTypeError(f"Unknown version '{version}'")


def valid_version(version: str) -> str:
    if version in installed_versions():
        return version
    latest_release = get_latest_release()
    if version == "latest":
        return latest_release
    match = re.search(r"^(\d+)\.(\d+)\.(\d+)$", version)

    if match is None:
        raise argparse.ArgumentTypeError(f"Invalid version '{version}'.")

    if Version(version) < Version(EARLIEST_RELEASE[soliditylang_platform()]):
        raise argparse.ArgumentTypeError(
            f"Invalid version - only solc versions above '{EARLIEST_RELEASE[soliditylang_platform()]}' are available"
        )

    # pylint: disable=consider-using-with
    if Version(version) > Version(latest_release):
        raise argparse.ArgumentTypeError(
            f"Invalid version '{latest_release}' is the latest available version"
        )

    return version


def valid_install_arg(arg: str) -> str:
    if arg == "all":
        return arg
    return valid_version(arg)


def get_installable_versions() -> List[str]:
    installable = list(set(get_available_versions()) - set(installed_versions()))
    installable.sort(key=Version)
    return installable


def get_available_versions() -> Dict[str, str]:
    session = create_http_session()
    (_, list_url) = get_url()
    response = session.get(list_url)
    response.raise_for_status()
    available_releases = response.json()["releases"]

    if soliditylang_platform() == LINUX_AMD64:
        (_, list_url) = get_url(version=EARLIEST_RELEASE[LINUX_AMD64])
        response = session.get(list_url)
        response.raise_for_status()
        additional_linux_versions = response.json()["releases"]
        available_releases.update(additional_linux_versions)
    elif sys.platform == "darwin" and get_arch() == "arm64":
        # Fetch Alloy versions for ARM64 Darwin
        response = session.get(ALLOY_SOLC_JSON)
        response.raise_for_status()
        alloy_releases = response.json()["releases"]
        # Filter to only include versions in the supported range (0.8.24+ are already universal)
        filtered_alloy_releases = {
            version: release
            for version, release in alloy_releases.items()
            if Version(ALLOY_ARM64_MIN_VERSION)
            <= Version(version)
            <= Version(ALLOY_ARM64_MAX_VERSION)
        }
        available_releases.update(filtered_alloy_releases)

    return available_releases


def soliditylang_platform() -> str:
    if sys.platform.startswith("linux"):
        platform = LINUX_AMD64
    elif sys.platform == "darwin":
        platform = MACOSX_AMD64
    elif sys.platform in ["win32", "cygwin"]:
        platform = WINDOWS_AMD64
    else:
        raise argparse.ArgumentTypeError("Unsupported platform")
    return platform


def get_latest_release() -> str:
    session = create_http_session()
    (_, list_url) = get_url()
    response = session.get(list_url)
    response.raise_for_status()
    latest_release = response.json()["latestRelease"]
    return latest_release
