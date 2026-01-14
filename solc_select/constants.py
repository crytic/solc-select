import os
from pathlib import Path

# Directory paths
HOME_DIR = Path(os.environ.get("VIRTUAL_ENV", Path.home()))
SOLC_SELECT_DIR = HOME_DIR / ".solc-select"
ARTIFACTS_DIR = SOLC_SELECT_DIR / "artifacts"

# CLI commands
INSTALL_COMMAND = "install"
USE_COMMAND = "use"
VERSIONS_COMMAND = "versions"
UPGRADE_COMMAND = "upgrade"

# soliditylang.org platform strings
LINUX_AMD64 = "linux-amd64"
LINUX_ARM64 = "linux-arm64"
MACOSX_AMD64 = "macosx-amd64"
WINDOWS_AMD64 = "windows-amd64"

# crytic/solc repo URLs
CRYTIC_SOLC_ARTIFACTS = "https://raw.githubusercontent.com/crytic/solc/master/linux/amd64/"
CRYTIC_SOLC_JSON = (
    "https://raw.githubusercontent.com/crytic/solc/new-list-json/linux/amd64/list.json"
)

# alloy-rs/solc-builds repo URLs
ALLOY_SOLC_ARTIFACTS = "https://raw.githubusercontent.com/alloy-rs/solc-builds/203ef20a24a6c2cb763e1c8c4c1836e85db2512d/macosx/aarch64/"
ALLOY_SOLC_JSON = "https://raw.githubusercontent.com/alloy-rs/solc-builds/203ef20a24a6c2cb763e1c8c4c1836e85db2512d/macosx/aarch64/list.json"
