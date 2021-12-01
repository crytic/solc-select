import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile
import os
import shutil
import re
import sys
import urllib.request
from distutils.version import StrictVersion

home_dir = Path.home()
solc_select_dir = home_dir.joinpath(".solc-select")
artifacts_dir = solc_select_dir.joinpath("artifacts")
Path.mkdir(artifacts_dir, parents=True, exist_ok=True)


def halt_old_architecture(path: Path) -> None:
    if not Path.is_file(path):
        raise argparse.ArgumentTypeError(
            "solc-select is out of date. Please run `solc-select update`"
        )


def upgrade_architecture() -> None:
    currently_installed = installed_versions()
    if len(currently_installed) > 0:
        if Path.is_file(artifacts_dir.joinpath(f"solc-{currently_installed[0]}")):
            shutil.rmtree(artifacts_dir)
            Path.mkdir(artifacts_dir, exist_ok=True)
            install_artifacts(currently_installed)
            print("solc-select is now up to date! 🎉")
        else:
            raise argparse.ArgumentTypeError("solc-select is already up to date")
    else:
        raise argparse.ArgumentTypeError("Run `solc-select install --help` for more information")


def current_version() -> (str, str):
    version = os.environ.get("SOLC_VERSION")
    source = "SOLC_VERSION"
    if version:
        if version not in installed_versions():
            raise argparse.ArgumentTypeError(
                f"Version '{version}' not installed (set by {source}). Run `solc-select install {version}`."
            )
    else:
        source = solc_select_dir.joinpath("global-version")
        if Path.is_file(source):
            with open(source) as f:
                version = f.read()
        else:
            raise argparse.ArgumentTypeError(
                "No solc version set. Run `solc-select use VERSION` or set SOLC_VERSION environment variable."
            )
    return (version, source)


def installed_versions() -> [str]:
    return [
        f.replace("solc-", "") for f in sorted(os.listdir(artifacts_dir)) if f.startswith("solc-")
    ]


def install_artifacts(versions: [str]) -> None:
    releases = get_available_versions()

    for version, artifact in releases.items():
        if "all" not in versions:
            if versions and version not in versions:
                continue

        (url, _) = get_url(version, artifact)
        artifact_file_dir = artifacts_dir.joinpath(f"solc-{version}")
        Path.mkdir(artifact_file_dir, parents=True, exist_ok=True)
        print(f"Installing '{version}'...")
        urllib.request.urlretrieve(url, artifact_file_dir.joinpath(f"solc-{version}"))

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
        print(f"Version '{version}' installed.")


def is_older_linux(version: str) -> bool:
    return soliditylang_platform() == "linux-amd64" and StrictVersion(version) <= StrictVersion(
        "0.4.10"
    )


def is_older_windows(version: str) -> bool:
    return soliditylang_platform() == "windows-amd64" and StrictVersion(version) <= StrictVersion(
        "0.7.1"
    )


def verify_checksum(version: str) -> None:
    (sha256_hash, keccak256_hash) = get_soliditylang_checksums(version)

    # calculate sha256 and keccak256 checksum of the local file
    with open(artifacts_dir.joinpath(f"solc-{version}", f"solc-{version}"), "rb") as f:
        sha256_factory = hashlib.sha256()
        keccak_factory = hashlib.sha3_256()

        # 1024000(~1MB chunk)
        for chunk in iter(lambda: f.read(1024000), b''):
            sha256_factory.update(chunk)
            keccak_factory.update(chunk)

        local_sha256_file_hash = f"0x{sha256_factory.hexdigest()}"
        local_keccak256_file_hash = f"0x{keccak_factory.hexdigest()}"

    if sha256_hash != local_sha256_file_hash and \
            keccak256_hash != local_keccak256_file_hash:
        raise argparse.ArgumentTypeError(
            f"Error: Checksum mismatch {soliditylang_platform()} - {version}"
        )


def get_soliditylang_checksums(version: str):
    (_, list_url) = get_url(version=version)
    list_json = urllib.request.urlopen(list_url).read()
    builds = json.loads(list_json)["builds"]
    matches = list(filter(lambda b: b["version"] == version, builds))

    if not matches or not matches[0]["sha256"]:
        raise argparse.ArgumentTypeError(
            f"Error: Unable to retrieve checksum for {soliditylang_platform()} - {version}"
        )

    return matches[0]["sha256"], matches[0]["keccak256"]


def get_url(version: str = "", artifact: str = "") -> (str, str):
    if soliditylang_platform() == "linux-amd64":
        if version != "" and is_older_linux(version):
            return (
                f"https://raw.githubusercontent.com/crytic/solc/master/linux/amd64/{artifact}",
                "https://raw.githubusercontent.com/crytic/solc/new-list-json/linux/amd64/list.json",
            )
    return (
        f"https://binaries.soliditylang.org/{soliditylang_platform()}/{artifact}",
        f"https://binaries.soliditylang.org/{soliditylang_platform()}/list.json",
    )


def switch_global_version(version: str, always_install: bool) -> None:
    if version in installed_versions():
        with open(f"{solc_select_dir}/global-version", "w") as f:
            f.write(version)
        print("Switched global version to", version)
    elif version in get_available_versions():
        if always_install:
            install_artifacts(version)
            switch_global_version(version, always_install)
        else:
            raise argparse.ArgumentTypeError(f"'{version}' must be installed prior to use.")
    else:
        raise argparse.ArgumentTypeError(f"Unknown version '{version}'")


def valid_version(version: str) -> str:
    match = re.search(r"^(\d+)\.(\d+)\.(\d+)$", version)

    if match is None:
        raise argparse.ArgumentTypeError(f"Invalid version '{version}'.")

    earliest_release = {"macosx-amd64": "0.3.6", "linux-amd64": "0.4.0", "windows-amd64": "0.4.5"}

    if StrictVersion(version) < StrictVersion(earliest_release[soliditylang_platform()]):
        raise argparse.ArgumentTypeError(
            f"Invalid version - only solc versions above '{earliest_release[soliditylang_platform()]}' are available"
        )

    (_, list_url) = get_url()
    list_json = urllib.request.urlopen(list_url).read()
    latest_release = json.loads(list_json)["latestRelease"]
    if StrictVersion(version) > StrictVersion(latest_release):
        raise argparse.ArgumentTypeError(
            f"Invalid version '{latest_release}' is the latest available version"
        )

    return version


def valid_install_arg(arg: str) -> str:
    if arg == "all":
        return arg
    return valid_version(arg)


def get_installable_versions() -> [str]:
    installable = list(set(get_available_versions()) - set(installed_versions()))
    installable.sort(key=StrictVersion)
    return installable


def get_available_versions() -> [str]:
    (_, list_url) = get_url()
    list_json = urllib.request.urlopen(list_url).read()
    available_releases = json.loads(list_json)["releases"]
    if soliditylang_platform() == "linux-amd64":
        available_releases.update(get_additional_linux_versions())
    return available_releases


def get_additional_linux_versions() -> [str]:
    if soliditylang_platform() == "linux-amd64":
        # This is just to be dynamic, but figure out a better way to do this.
        (_, list_url) = get_url(version="0.4.10")
        github_json = urllib.request.urlopen(list_url).read()
        return json.loads(github_json)["releases"]
    return []


def soliditylang_platform() -> str:
    if sys.platform.startswith("linux"):
        platform = "linux-amd64"
    elif sys.platform == "darwin":
        platform = "macosx-amd64"
    elif sys.platform == "win32" or sys.platform == "cygwin":
        platform = "windows-amd64"
    else:
        raise argparse.ArgumentTypeError("Unsupported platform")
    return platform
