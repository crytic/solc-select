"""
Backward compatibility wrappers for solc-select.

This module provides compatibility functions for code that previously imported
from solc_select.solc_select, such as crytic-compile. These functions wrap
the new refactored service architecture to maintain the same API.
"""

from pathlib import Path

from .constants import ARTIFACTS_DIR
from .services.solc_service import SolcService


def install_artifacts(versions: list[str], silent: bool = False) -> bool:
    """Install solc versions (backward compatibility wrapper).

    Args:
        versions: List of version strings to install (e.g., ["0.8.19", "latest", "all"])
        silent: Whether to suppress output messages

    Returns:
        True if all installations succeeded, False otherwise
    """
    service = SolcService()
    return service.install_versions(versions, silent)


def installed_versions() -> list[str]:
    """Get list of installed version strings (backward compatibility wrapper).

    Returns:
        List of installed version strings sorted by version number
    """
    service = SolcService()
    versions = service.get_installed_versions()
    return [str(version) for version in versions]


def artifact_path(version: str) -> Path:
    """Get the path to a version's binary (backward compatibility wrapper).

    Args:
        version: Version string (e.g., "0.8.19")

    Returns:
        Path to the solc binary for the given version

    Note:
        This function returns the expected path regardless of whether
        the version is actually installed, matching the original behavior.
    """
    return ARTIFACTS_DIR / f"solc-{version}" / f"solc-{version}"
