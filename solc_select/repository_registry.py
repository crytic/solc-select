"""Repository manifest registry for solc-select."""

from .models.repositories import PlatformSupport, RepositoryManifest
from .models.versions import VersionRange
from .platform_capabilities import PlatformIdentifier

SOLIDITYLANG_MANIFEST = RepositoryManifest(
    repository_id="soliditylang",
    base_url="https://binaries.soliditylang.org",
    platform_supports=[
        PlatformSupport(
            platform=PlatformIdentifier("linux", "amd64"),
            version_range=VersionRange.from_min("0.4.10"),
        ),
        PlatformSupport(
            platform=PlatformIdentifier("linux", "arm64"),
            version_range=VersionRange.from_min("0.8.31"),
        ),
        PlatformSupport(
            platform=PlatformIdentifier("darwin", "amd64"),
            version_range=VersionRange.from_min("0.3.6"),
        ),
        PlatformSupport(
            platform=PlatformIdentifier("darwin", "arm64"),
            version_range=VersionRange.from_min("0.8.24"),
        ),
        PlatformSupport(
            platform=PlatformIdentifier("windows", "amd64"),
            version_range=VersionRange.from_min("0.7.2"),
        ),
        PlatformSupport(
            platform=PlatformIdentifier("windows", "amd64"),
            version_range=VersionRange.exact_range("0.4.1", "0.7.1"),
        ),
    ],
    priority=100,
)

ALLOY_MANIFEST = RepositoryManifest(
    repository_id="alloy",
    base_url="https://raw.githubusercontent.com/alloy-rs/solc-builds/main/macosx/aarch64/",
    platform_supports=[
        PlatformSupport(
            platform=PlatformIdentifier("darwin", "arm64"),
            version_range=VersionRange.exact_range("0.8.5", "0.8.23"),
        ),
    ],
    priority=90,
)

CRYTIC_MANIFEST = RepositoryManifest(
    repository_id="crytic",
    base_url="https://raw.githubusercontent.com/crytic/solc/master/linux/amd64/",
    platform_supports=[
        PlatformSupport(
            platform=PlatformIdentifier("linux", "amd64"),
            version_range=VersionRange.exact_range("0.4.0", "0.4.10"),
        ),
        PlatformSupport(
            platform=PlatformIdentifier("linux", "amd64"),
            version_range=VersionRange.exact_range("0.8.18", "0.8.18"),
        ),
    ],
    priority=10,
)

REPOSITORY_REGISTRY: list[RepositoryManifest] = [
    SOLIDITYLANG_MANIFEST,
    ALLOY_MANIFEST,
    CRYTIC_MANIFEST,
]
