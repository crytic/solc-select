import os
from pathlib import Path

# DIRs path
if "VIRTUAL_ENV" in os.environ:
    HOME_DIR = Path(os.environ["VIRTUAL_ENV"])
else:
    HOME_DIR = Path.home()
SOLC_SELECT_DIR = HOME_DIR.joinpath(".solc-select")
ARTIFACTS_DIR = SOLC_SELECT_DIR.joinpath("artifacts")

# CLI Flags
INSTALL_VERSIONS = "INSTALL_VERSIONS"
USE_VERSION = "USE_VERSION"
SHOW_VERSIONS = "SHOW_VERSIONS"
UPGRADE = "UPGRADE"

LINUX_AMD64 = "linux-amd64"
MACOSX_AMD64 = "macosx-amd64"
WINDOWS_AMD64 = "windows-amd64"

EARLIEST_RELEASE = {"macosx-amd64": "0.3.6", "linux-amd64": "0.4.0", "windows-amd64": "0.4.5"}
