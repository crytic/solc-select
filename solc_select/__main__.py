import argparse
import sys

from .constants import (
    INSTALL_COMMAND,
    UPGRADE_COMMAND,
    USE_COMMAND,
    VERSIONS_COMMAND,
)
from .exceptions import (
    ChecksumMismatchError,
    InstallationError,
    NetworkError,
    NoVersionSetError,
    PlatformNotSupportedError,
    SolcSelectError,
    VersionNotFoundError,
    VersionNotInstalledError,
    VersionResolutionError,
)
from .services.solc_service import SolcService
from .utils import sort_versions


def solc_select_install(service: SolcService, versions: list[str]) -> None:
    """Handle the install command."""
    if not versions:
        print("Available versions to install:")
        for version in service.get_installable_versions():
            print(str(version))
    else:
        success = service.install_versions(versions)
        sys.exit(0 if success else 1)


def solc_select_use(service: SolcService, version: str, always_install: bool) -> None:
    """Handle the use command."""
    service.switch_global_version(version, always_install, silent=False)


def solc_select_versions(service: SolcService) -> None:
    """Handle the versions command."""
    installed = service.get_installed_versions()
    if not installed:
        print("No solc version installed. Run `solc-select install --help` for more information")
        return

    try:
        current_version, source = service.get_current_version()
    except (NoVersionSetError, VersionNotInstalledError):
        current_version = None

    for version_str in sort_versions([str(v) for v in installed]):
        if current_version and version_str == str(current_version):
            print(f"{version_str} (current, set by {source})")
        else:
            print(version_str)


def solc_select_upgrade(service: SolcService) -> None:
    """Handle the upgrade command."""
    service.upgrade_architecture()


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        help="Allows users to install and quickly switch between Solidity compiler versions",
        dest="command",
    )

    parser_install = subparsers.add_parser(
        INSTALL_COMMAND, help="list and install available solc versions"
    )
    parser_install.add_argument(
        "versions",
        help='specific versions you want to install "0.4.25", "all" or "latest"',
        nargs="*",
        default=[],
    )

    parser_use = subparsers.add_parser(
        USE_COMMAND, help="change the version of global solc compiler"
    )
    parser_use.add_argument("version", help="solc version you want to use (eg: 0.4.25)", nargs="?")
    parser_use.add_argument("--always-install", action="store_true")

    parser_versions = subparsers.add_parser(
        VERSIONS_COMMAND, help="prints out all installed solc versions"
    )
    parser_versions.add_argument("versions", nargs="*", help=argparse.SUPPRESS)

    parser_upgrade = subparsers.add_parser(UPGRADE_COMMAND, help="upgrades solc-select")
    parser_upgrade.add_argument("upgrade", nargs="*", help=argparse.SUPPRESS)

    return parser


def solc_select() -> None:
    parser = create_parser()
    args = parser.parse_args()
    service = SolcService()

    try:
        if args.command == INSTALL_COMMAND:
            solc_select_install(service, args.versions)
        elif args.command == USE_COMMAND:
            if not args.version:
                parser.error("the following arguments are required: version")
            solc_select_use(service, args.version, args.always_install)
        elif args.command == VERSIONS_COMMAND:
            solc_select_versions(service)
        elif args.command == UPGRADE_COMMAND:
            solc_select_upgrade(service)
        else:
            parser.parse_args(["--help"])
            sys.exit(0)

    except VersionNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        if e.available_versions:
            print("Hint: Run 'solc-select install' to see all available versions", file=sys.stderr)
        sys.exit(1)
    except ChecksumMismatchError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Hint: Try downloading again or report this issue if it persists", file=sys.stderr)
        sys.exit(1)
    except (InstallationError, NetworkError) as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Hint: Check your network connection and try again", file=sys.stderr)
        sys.exit(1)
    except PlatformNotSupportedError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Hint: Use a newer version that supports your platform", file=sys.stderr)
        sys.exit(1)
    except VersionResolutionError as e:
        print(f"Error: {e}", file=sys.stderr)
        print("Hint: Check your network connection or specify a specific version", file=sys.stderr)
        sys.exit(1)
    except SolcSelectError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def solc() -> None:
    """CLI entry point for solc executable."""
    service = SolcService()

    try:
        service.execute_solc(sys.argv[1:])
    except KeyboardInterrupt:
        print("\nOperation cancelled", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error executing solc: {e}", file=sys.stderr)
        sys.exit(1)
