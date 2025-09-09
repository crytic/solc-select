import argparse
import subprocess
import sys

from .constants import (
    ARTIFACTS_DIR,
    INSTALL_VERSIONS,
    SHOW_VERSIONS,
    UPGRADE,
    USE_VERSION,
)
from .solc_select import (
    current_version,
    get_emulation_prefix,
    get_installable_versions,
    halt_incompatible_system,
    halt_old_architecture,
    install_artifacts,
    installed_versions,
    switch_global_version,
    upgrade_architecture,
    valid_install_arg,
    valid_version,
)
from .utils import sort_versions


# pylint: disable=too-many-branches
def solc_select() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        help="Allows users to install and quickly switch between Solidity compiler versions",
        dest="command",
    )
    parser_install = subparsers.add_parser(
        "install", help="list and install available solc versions"
    )
    parser_install.add_argument(
        INSTALL_VERSIONS,
        help='specific versions you want to install "0.4.25", "all" or "latest"',
        nargs="*",
        default=[],
        type=valid_install_arg,
    )
    parser_use = subparsers.add_parser("use", help="change the version of global solc compiler")
    parser_use.add_argument(
        USE_VERSION, help="solc version you want to use (eg: 0.4.25)", type=valid_version, nargs="?"
    )
    parser_use.add_argument("--always-install", action="store_true")
    parser_use = subparsers.add_parser("versions", help="prints out all installed solc versions")
    parser_use.add_argument(SHOW_VERSIONS, nargs="*", help=argparse.SUPPRESS)
    parser_use = subparsers.add_parser("upgrade", help="upgrades solc-select")
    parser_use.add_argument(UPGRADE, nargs="*", help=argparse.SUPPRESS)

    args = parser.parse_args()

    if args.command == "install":
        versions = args.INSTALL_VERSIONS
        if not versions:
            print("Available versions to install:")
            for version in get_installable_versions():
                print(version)
        else:
            status = install_artifacts(versions)
            sys.exit(0 if status else 1)

    elif args.command == "use":
        switch_global_version(args.USE_VERSION, args.always_install, silent=False)

    elif args.command == "versions":
        versions_installed = installed_versions()
        if versions_installed:
            (current_ver, source) = (None, None)
            try:
                res = current_version()
                if res:
                    (current_ver, source) = res
            except argparse.ArgumentTypeError:
                # No version is currently set, that's ok
                res = None
            for version in sort_versions(versions_installed):
                if res and version == current_ver:
                    print(f"{version} (current, set by {source})")
                else:
                    print(version)
        else:
            print(
                "No solc version installed. Run `solc-select install --help` for more information"
            )
    elif args.command == "upgrade":
        upgrade_architecture()
    else:
        parser.parse_args(["--help"])
        sys.exit(0)


def solc() -> None:
    if not installed_versions():
        switch_global_version(version="latest", always_install=True, silent=True)
    res = current_version()
    if res:
        (version, _) = res
        path = ARTIFACTS_DIR.joinpath(f"solc-{version}", f"solc-{version}")
        halt_old_architecture(path)
        halt_incompatible_system(path)

        # Use emulation if needed for ARM64 systems
        cmd = get_emulation_prefix() + [str(path)] + sys.argv[1:]

        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
    else:
        sys.exit(1)
