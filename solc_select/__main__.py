import argparse
import sys

from .constants import (
    INSTALL_VERSIONS,
    SHOW_VERSIONS,
    UPGRADE,
    USE_VERSION,
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
        installable = service.get_installable_versions()
        for version in installable:
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
    if installed:
        try:
            current_version, source = service.get_current_version()
        except (NoVersionSetError, VersionNotInstalledError):
            # No version is currently set or not installed, that's ok for the versions command
            current_version = None

        installed_strs = [str(v) for v in installed]
        for version_str in sort_versions(installed_strs):
            if current_version and version_str == str(current_version):
                print(f"{version_str} (current, set by {source})")
            else:
                print(version_str)
    else:
        print("No solc version installed. Run `solc-select install --help` for more information")


def solc_select_upgrade(service: SolcService) -> None:
    """Handle the upgrade command."""
    service.upgrade_architecture()


def solc_select() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        help="Allows users to install and quickly switch between Solidity compiler versions",
        dest="command",
    )

    # Install command
    parser_install = subparsers.add_parser(
        "install", help="list and install available solc versions"
    )
    parser_install.add_argument(
        INSTALL_VERSIONS,
        help='specific versions you want to install "0.4.25", "all" or "latest"',
        nargs="*",
        default=[],
    )

    # Use command
    parser_use = subparsers.add_parser("use", help="change the version of global solc compiler")
    parser_use.add_argument(
        USE_VERSION, help="solc version you want to use (eg: 0.4.25)", nargs="?"
    )
    parser_use.add_argument("--always-install", action="store_true")

    # Versions command
    parser_versions = subparsers.add_parser(
        "versions", help="prints out all installed solc versions"
    )
    parser_versions.add_argument(SHOW_VERSIONS, nargs="*", help=argparse.SUPPRESS)

    # Upgrade command
    parser_upgrade = subparsers.add_parser("upgrade", help="upgrades solc-select")
    parser_upgrade.add_argument(UPGRADE, nargs="*", help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Create service instance
    service = SolcService()

    try:
        if args.command == "install":
            solc_select_install(service, args.INSTALL_VERSIONS)

        elif args.command == "use":
            if not args.USE_VERSION:
                parser.error("the following arguments are required: USE_VERSION")
            solc_select_use(service, args.USE_VERSION, args.always_install)

        elif args.command == "versions":
            solc_select_versions(service)

        elif args.command == "upgrade":
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
        print("\nOperation cancelled by user", file=sys.stderr)
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
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error executing solc: {e}", file=sys.stderr)
        sys.exit(1)
