import os
from pathlib import Path

# DIRs path
if "VIRTUAL_ENV" in os.environ:
    HOME_DIR = Path(os.environ["VIRTUAL_ENV"])
else:
    HOME_DIR = Path.home()
SOLC_SELECT_DIR = HOME_DIR.joinpath(".solc-select")
ARTIFACTS_DIR = SOLC_SELECT_DIR.joinpath("artifacts")

# CLI Commands
INSTALL_COMMAND = "install"
USE_COMMAND = "use"
VERSIONS_COMMAND = "versions"
UPGRADE_COMMAND = "upgrade"

# soliditylang.org platform strings
LINUX_AMD64 = "linux-amd64"
LINUX_ARM64 = "linux-arm64"
MACOSX_AMD64 = "macosx-amd64"
WINDOWS_AMD64 = "windows-amd64"

# earliest releases supported in each platform
EARLIEST_RELEASE = {
    "macosx-amd64": "0.3.6",
    "linux-amd64": "0.4.10",
    "linux-arm64": "0.8.31",
    "windows-amd64": "0.4.1",
}

# earliest releases supported in each platform (with emulation when required)
EARLIEST_RELEASE_OS = {
    "macosx": "0.3.6",
    "linux": "0.4.0",
    "windows": "0.4.1",
}

# crytic/solc repo URLs
CRYTIC_SOLC_ARTIFACTS = "https://raw.githubusercontent.com/crytic/solc/master/linux/amd64/"
CRYTIC_SOLC_JSON = (
    "https://raw.githubusercontent.com/crytic/solc/new-list-json/linux/amd64/list.json"
)

# alloy-rs/solc-builds repo URLs
ALLOY_SOLC_ARTIFACTS = "https://raw.githubusercontent.com/alloy-rs/solc-builds/203ef20a24a6c2cb763e1c8c4c1836e85db2512d/macosx/aarch64/"
ALLOY_SOLC_JSON = "https://raw.githubusercontent.com/alloy-rs/solc-builds/203ef20a24a6c2cb763e1c8c4c1836e85db2512d/macosx/aarch64/list.json"

# Alloy ARM64 repo version range (0.8.24+ are universal binaries on soliditylang.org)
ALLOY_ARM64_MIN_VERSION = "0.8.5"
ALLOY_ARM64_MAX_VERSION = "0.8.23"
