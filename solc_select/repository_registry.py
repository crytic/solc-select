"""
Repository manifest registry for solc-select.

This module contains declarative manifests for all Solidity compiler repositories,
specifying what platforms and version ranges each repository supports.
"""

from .models import (
    PlatformIdentifier,
    PlatformSupport,
    RepositoryManifest,
    VersionRange,
)


# ========================================
# SOLIDITYLANG REPOSITORY (Primary Source)
# ========================================


SOLIDITYLANG_MANIFEST = RepositoryManifest(
    repository_id="soliditylang",
    base_url="https://binaries.soliditylang.org",
    platform_supports=[
        # Linux AMD64 - native x86_64 binaries
        PlatformSupport(
            platform=PlatformIdentifier("linux", "amd64"),
            version_range=VersionRange.from_min("0.4.10"),
            binary_format="elf",
        ),
        # Linux ARM64 - native ARM64 binaries
        PlatformSupport(
            platform=PlatformIdentifier("linux", "arm64"),
            version_range=VersionRange.from_min("0.8.31"),
            binary_format="elf",
        ),
        # macOS AMD64 - native x86_64 binaries
        PlatformSupport(
            platform=PlatformIdentifier("darwin", "amd64"),
            version_range=VersionRange.from_min("0.3.6"),
            binary_format="macho",
        ),
        # macOS ARM64 - universal binaries (0.8.24+)
        PlatformSupport(
            platform=PlatformIdentifier("darwin", "arm64"),
            version_range=VersionRange.from_min("0.8.24"),
            binary_format="universal-macho",
        ),
        # Windows AMD64 - PE binaries (0.7.2+)
        PlatformSupport(
            platform=PlatformIdentifier("windows", "amd64"),
            version_range=VersionRange.from_min("0.7.2"),
            binary_format="pe",
        ),
        # Windows AMD64 - ZIP archives (older versions)
        PlatformSupport(
            platform=PlatformIdentifier("windows", "amd64"),
            version_range=VersionRange.exact_range("0.4.1", "0.7.1"),
            binary_format="zip",
        ),
    ],
    priority=100,  # Highest priority - primary source
)


# ========================================
# ALLOY REPOSITORY (Native macOS ARM64)
# ========================================


ALLOY_MANIFEST = RepositoryManifest(
    repository_id="alloy",
    base_url="https://raw.githubusercontent.com/alloy-rs/solc-builds/main/macosx/aarch64/",
    platform_supports=[
        # macOS ARM64 - native ARM64 binaries (specific version range)
        # After 0.8.24, soliditylang provides universal binaries, so Alloy is not needed
        PlatformSupport(
            platform=PlatformIdentifier("darwin", "arm64"),
            version_range=VersionRange.exact_range("0.8.5", "0.8.23"),
            binary_format="macho",
        ),
    ],
    priority=90,  # Lower than Soliditylang - use Soliditylang when both available
)


# ========================================
# CRYTIC REPOSITORY (Legacy Linux Binaries)
# ========================================


CRYTIC_MANIFEST = RepositoryManifest(
    repository_id="crytic",
    base_url="https://raw.githubusercontent.com/crytic/solc/master/linux/amd64/",
    platform_supports=[
        # Linux AMD64 - legacy versions before Soliditylang started providing them
        PlatformSupport(
            platform=PlatformIdentifier("linux", "amd64"),
            version_range=VersionRange.exact_range("0.4.0", "0.4.10"),
            binary_format="elf",
        ),
        # Special case: 0.8.18 (missing from Soliditylang)
        PlatformSupport(
            platform=PlatformIdentifier("linux", "amd64"),
            version_range=VersionRange.exact_range("0.8.18", "0.8.18"),
            binary_format="elf",
        ),
    ],
    priority=10,  # Lowest priority - legacy fallback only
)


# ========================================
# REPOSITORY REGISTRY
# ========================================


REPOSITORY_REGISTRY: list[RepositoryManifest] = [
    SOLIDITYLANG_MANIFEST,
    ALLOY_MANIFEST,
    CRYTIC_MANIFEST,
]
