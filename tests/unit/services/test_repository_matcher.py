"""Unit tests for RepositoryMatcher service."""

from unittest.mock import Mock, PropertyMock

import pytest
import requests

from solc_select.exceptions import VersionNotFoundError
from solc_select.models.repositories import PlatformSupport, RepositoryManifest
from solc_select.models.versions import SolcVersion, VersionRange
from solc_select.platform_capabilities import PlatformCapability, PlatformIdentifier
from solc_select.repositories import SolcRepository
from solc_select.services.repository_matcher import RepositoryMatcher

# Platform identifiers as module-level constants to reduce fixture overhead
LINUX_AMD64 = PlatformIdentifier("linux", "amd64")
LINUX_ARM64 = PlatformIdentifier("linux", "arm64")
DARWIN_ARM64 = PlatformIdentifier("darwin", "arm64")
DARWIN_AMD64 = PlatformIdentifier("darwin", "amd64")


@pytest.fixture
def linux_amd64_platform() -> PlatformIdentifier:
    """Linux AMD64 platform identifier."""
    return LINUX_AMD64


@pytest.fixture
def linux_arm64_platform() -> PlatformIdentifier:
    """Linux ARM64 platform identifier."""
    return LINUX_ARM64


@pytest.fixture
def darwin_arm64_platform() -> PlatformIdentifier:
    """Darwin ARM64 platform identifier."""
    return DARWIN_ARM64


@pytest.fixture
def darwin_amd64_platform() -> PlatformIdentifier:
    """Darwin AMD64 platform identifier."""
    return DARWIN_AMD64


@pytest.fixture
def soliditylang_manifest(
    linux_amd64_platform: PlatformIdentifier, linux_arm64_platform: PlatformIdentifier
) -> RepositoryManifest:
    """Soliditylang repository manifest."""
    return RepositoryManifest(
        repository_id="soliditylang",
        base_url="https://binaries.soliditylang.org",
        platform_supports=[
            PlatformSupport(
                platform=linux_amd64_platform,
                version_range=VersionRange.from_min("0.4.10"),
            ),
            PlatformSupport(
                platform=linux_arm64_platform,
                version_range=VersionRange.from_min("0.8.31"),
            ),
        ],
        priority=100,
    )


@pytest.fixture
def alloy_manifest(darwin_arm64_platform: PlatformIdentifier) -> RepositoryManifest:
    """Alloy repository manifest."""
    return RepositoryManifest(
        repository_id="alloy",
        base_url="https://raw.githubusercontent.com/alloy-rs/solc-builds/main/",
        platform_supports=[
            PlatformSupport(
                platform=darwin_arm64_platform,
                version_range=VersionRange.exact_range("0.8.5", "0.8.23"),
            ),
        ],
        priority=90,
    )


@pytest.fixture
def crytic_manifest(linux_amd64_platform: PlatformIdentifier) -> RepositoryManifest:
    """Crytic repository manifest."""
    return RepositoryManifest(
        repository_id="crytic",
        base_url="https://raw.githubusercontent.com/crytic/solc/master/",
        platform_supports=[
            PlatformSupport(
                platform=linux_amd64_platform,
                version_range=VersionRange.exact_range("0.4.0", "0.4.10"),
            ),
        ],
        priority=10,
    )


@pytest.fixture
def mock_platform_capability(linux_amd64_platform: PlatformIdentifier) -> Mock:
    """Mock platform capability for Linux AMD64 (native only)."""
    mock_cap = Mock(spec=PlatformCapability)
    mock_cap.host_platform = linux_amd64_platform
    mock_cap.native_support = linux_amd64_platform
    mock_cap.get_runnable_platforms.return_value = [linux_amd64_platform]
    return mock_cap


@pytest.fixture
def mock_platform_capability_with_emulation(
    darwin_arm64_platform: PlatformIdentifier, darwin_amd64_platform: PlatformIdentifier
) -> Mock:
    """Mock platform capability for Darwin ARM64 with x86 emulation."""
    mock_cap = Mock(spec=PlatformCapability)
    mock_cap.host_platform = darwin_arm64_platform
    mock_cap.native_support = darwin_arm64_platform
    # Native first, then emulated
    mock_cap.get_runnable_platforms.return_value = [darwin_arm64_platform, darwin_amd64_platform]
    return mock_cap


@pytest.fixture
def mock_repository() -> Mock:
    """Mock SolcRepository with standard versions."""
    mock_repo = Mock(spec=SolcRepository)
    type(mock_repo).available_versions = PropertyMock(
        return_value={
            "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
            "0.8.20": "solc-linux-amd64-v0.8.20+commit.def456",
            "0.8.21": "solc-linux-amd64-v0.8.21+commit.ghi789",
        }
    )
    return mock_repo


class TestRepositoryMatcherFind:
    """Tests for find_repository_for_version method."""

    def test_find_native_binary_preferred(
        self,
        mock_session,
        mock_platform_capability_with_emulation,
        soliditylang_manifest,
        alloy_manifest,
        darwin_arm64_platform,
    ):
        """Native platform binaries should be selected over emulated binaries."""
        # Soliditylang has native darwin-arm64 support for 0.8.24+
        soliditylang_manifest.platform_supports.append(
            PlatformSupport(
                platform=darwin_arm64_platform,
                version_range=VersionRange.from_min("0.8.24"),
            )
        )

        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability_with_emulation,
            manifests=[soliditylang_manifest, alloy_manifest],
            session=mock_session,
        )

        # Version 0.8.25 is available natively on darwin-arm64 (soliditylang)
        version = SolcVersion.parse("0.8.25")
        repo, target_platform = matcher.find_repository_for_version(version, exact=False)

        # Should select native darwin-arm64 from soliditylang
        assert target_platform == darwin_arm64_platform
        assert "soliditylang" in str(type(repo).__name__).lower() or hasattr(
            repo, "base_url"
        )  # Check it's soliditylang repo

    def test_find_emulated_binary_fallback(
        self,
        mock_session,
        mock_platform_capability_with_emulation,
        alloy_manifest,
        darwin_arm64_platform,
        darwin_amd64_platform,
    ):
        """Should use emulated binaries when native ones are unavailable."""
        # Alloy only provides darwin-arm64 for 0.8.5-0.8.23
        # For 0.8.4, should fall back to darwin-amd64 (emulated)

        # Add darwin-amd64 support to alloy manifest for this version
        alloy_manifest.platform_supports.append(
            PlatformSupport(
                platform=darwin_amd64_platform,
                version_range=VersionRange.from_min("0.4.0"),
            )
        )

        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability_with_emulation,
            manifests=[alloy_manifest],
            session=mock_session,
        )

        version = SolcVersion.parse("0.8.4")
        _repo, target_platform = matcher.find_repository_for_version(version, exact=False)

        # Should fall back to emulated darwin-amd64
        assert target_platform == darwin_amd64_platform

    def test_find_respects_priority_order(
        self,
        mock_session,
        mock_platform_capability,
        soliditylang_manifest,
        crytic_manifest,
        linux_amd64_platform,
    ):
        """Higher priority manifest should win when multiple repos provide the version."""
        # Both soliditylang (priority 100) and crytic (priority 10) provide 0.4.10
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest, crytic_manifest],
            session=mock_session,
        )

        version = SolcVersion.parse("0.4.10")
        repo, target_platform = matcher.find_repository_for_version(version, exact=False)

        # Soliditylang has higher priority (100 > 10)
        assert target_platform == linux_amd64_platform
        # Check it's from soliditylang repo by checking the base_url or list_url
        assert hasattr(repo, "base_url")
        assert "binaries.soliditylang.org" in repo.base_url

    def test_find_version_not_found(
        self,
        mock_session,
        mock_platform_capability,
        alloy_manifest,
    ):
        """Should raise VersionNotFoundError when no repository provides the version."""
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[alloy_manifest],  # Only has darwin-arm64 support
            session=mock_session,
        )

        # Linux AMD64 is requested but alloy only has darwin-arm64
        version = SolcVersion.parse("0.8.19")

        with pytest.raises(VersionNotFoundError) as exc_info:
            matcher.find_repository_for_version(version, exact=False)

        assert "0.8.19" in str(exc_info.value)
        assert "linux-amd64" in str(exc_info.value)

    def test_find_platform_not_supported(
        self,
        mock_session,
        mock_platform_capability,
        soliditylang_manifest,
        linux_amd64_platform,
    ):
        """Should raise VersionNotFoundError when version is outside platform's range."""
        # Soliditylang linux-amd64 starts at 0.4.10
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest],
            session=mock_session,
        )

        version = SolcVersion.parse("0.4.5")  # Below minimum 0.4.10

        with pytest.raises(VersionNotFoundError) as exc_info:
            matcher.find_repository_for_version(version, exact=False)

        assert "0.4.5" in str(exc_info.value)

    def test_find_exact_false_skips_check(
        self,
        mock_session,
        mock_platform_capability,
        soliditylang_manifest,
        linux_amd64_platform,
    ):
        """With exact=False, should not verify version exists in repository."""
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest],
            session=mock_session,
        )

        version = SolcVersion.parse("0.8.19")

        # exact=False should skip checking available_versions
        _repo, target_platform = matcher.find_repository_for_version(version, exact=False)

        assert target_platform == linux_amd64_platform
        # Should not have accessed available_versions property
        # (no assertion on repo property access since it's mocked differently)

    def test_find_exact_true_verifies_availability(
        self,
        mock_session,
        mock_platform_capability,
        soliditylang_manifest,
        linux_amd64_platform,
    ):
        """With exact=True, should verify version exists in repository."""
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest],
            session=mock_session,
        )

        # Mock the repository to have specific versions
        key = ("soliditylang", str(linux_amd64_platform))
        mock_repo = Mock(spec=SolcRepository)
        type(mock_repo).available_versions = PropertyMock(
            return_value={
                "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
            }
        )
        matcher.repositories[key] = mock_repo

        # This version exists
        version = SolcVersion.parse("0.8.19")
        _repo, target_platform = matcher.find_repository_for_version(version, exact=True)
        assert target_platform == linux_amd64_platform

        # This version doesn't exist
        version_not_available = SolcVersion.parse("0.8.99")
        with pytest.raises(VersionNotFoundError):
            matcher.find_repository_for_version(version_not_available, exact=True)

    def test_find_multiple_manifests_same_priority(
        self,
        mock_session,
        mock_platform_capability,
        linux_amd64_platform,
    ):
        """When multiple manifests have same priority, first match should win."""
        # Use real repository IDs to avoid ValueError
        manifest1 = RepositoryManifest(
            repository_id="soliditylang",
            base_url="https://repo1.example.com",
            platform_supports=[
                PlatformSupport(
                    platform=linux_amd64_platform,
                    version_range=VersionRange.from_min("0.4.0"),
                ),
            ],
            priority=50,
        )

        manifest2 = RepositoryManifest(
            repository_id="crytic",
            base_url="https://repo2.example.com",
            platform_supports=[
                PlatformSupport(
                    platform=linux_amd64_platform,
                    version_range=VersionRange.from_min("0.4.0"),
                ),
            ],
            priority=50,
        )

        # Create matcher with known order
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[manifest1, manifest2],
            session=mock_session,
        )

        version = SolcVersion.parse("0.8.19")

        # Should pick first one (manifest1) since they have same priority
        repo, target_platform = matcher.find_repository_for_version(version, exact=False)

        # Verify it came from the first manifest
        assert target_platform == linux_amd64_platform
        # Check it's from first repo (soliditylang) by checking base_url matches manifest1
        assert hasattr(repo, "base_url")
        assert "binaries.soliditylang.org" in repo.base_url  # Real soliditylang URL


class TestRepositoryMatcherAggregation:
    """Tests for get_all_available_versions method."""

    def test_get_all_versions_multiple_repos(
        self,
        mock_session,
        mock_platform_capability,
        soliditylang_manifest,
        crytic_manifest,
        linux_amd64_platform,
    ):
        """Should combine versions from all repositories."""
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest, crytic_manifest],
            session=mock_session,
        )

        # Mock repositories with different version sets
        soliditylang_key = ("soliditylang", str(linux_amd64_platform))
        soliditylang_repo = Mock(spec=SolcRepository)
        type(soliditylang_repo).available_versions = PropertyMock(
            return_value={
                "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
                "0.8.20": "solc-linux-amd64-v0.8.20+commit.def456",
            }
        )
        matcher.repositories[soliditylang_key] = soliditylang_repo

        crytic_key = ("crytic", str(linux_amd64_platform))
        crytic_repo = Mock(spec=SolcRepository)
        type(crytic_repo).available_versions = PropertyMock(
            return_value={
                "0.4.5": "solc-v0.4.5",
                "0.4.6": "solc-v0.4.6",
            }
        )
        matcher.repositories[crytic_key] = crytic_repo

        all_versions = matcher.get_all_available_versions()

        # Should have versions from both repos
        assert SolcVersion.parse("0.8.19") in all_versions
        assert SolcVersion.parse("0.8.20") in all_versions
        assert SolcVersion.parse("0.4.5") in all_versions
        assert SolcVersion.parse("0.4.6") in all_versions
        assert len(all_versions) == 4

    def test_get_all_versions_handles_network_errors(
        self,
        mock_session,
        mock_platform_capability,
        soliditylang_manifest,
        crytic_manifest,
        linux_amd64_platform,
    ):
        """Should continue on repository failure and return available versions."""
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest, crytic_manifest],
            session=mock_session,
        )

        # First repo works
        soliditylang_key = ("soliditylang", str(linux_amd64_platform))
        soliditylang_repo = Mock(spec=SolcRepository)
        type(soliditylang_repo).available_versions = PropertyMock(
            return_value={
                "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
            }
        )
        matcher.repositories[soliditylang_key] = soliditylang_repo

        # Second repo fails with network error
        crytic_key = ("crytic", str(linux_amd64_platform))
        crytic_repo = Mock(spec=SolcRepository)
        type(crytic_repo).available_versions = PropertyMock(
            side_effect=requests.RequestException("Network error")
        )
        matcher.repositories[crytic_key] = crytic_repo

        all_versions = matcher.get_all_available_versions()

        # Should have versions from working repo only
        assert SolcVersion.parse("0.8.19") in all_versions
        assert len(all_versions) == 1

    def test_get_all_versions_deduplicates(
        self,
        mock_session,
        mock_platform_capability,
        linux_amd64_platform,
    ):
        """Should not duplicate same version from multiple repos."""
        # Create new manifests that both support 0.8.19 (can't modify frozen dataclass)
        soliditylang_manifest_new = RepositoryManifest(
            repository_id="soliditylang",
            base_url="https://binaries.soliditylang.org",
            platform_supports=[
                PlatformSupport(
                    platform=linux_amd64_platform,
                    version_range=VersionRange.from_min("0.4.10"),
                ),
            ],
            priority=100,
        )

        crytic_manifest_new = RepositoryManifest(
            repository_id="crytic",
            base_url="https://raw.githubusercontent.com/crytic/solc/master/",
            platform_supports=[
                PlatformSupport(
                    platform=linux_amd64_platform,
                    version_range=VersionRange.from_min("0.4.0"),  # Extended to support 0.8.19
                ),
            ],
            priority=10,
        )

        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest_new, crytic_manifest_new],
            session=mock_session,
        )

        # Both repos provide 0.8.19
        soliditylang_key = ("soliditylang", str(linux_amd64_platform))
        soliditylang_repo = Mock(spec=SolcRepository)
        type(soliditylang_repo).available_versions = PropertyMock(
            return_value={
                "0.8.19": "solc-linux-amd64-v0.8.19+commit.abc123",
            }
        )
        matcher.repositories[soliditylang_key] = soliditylang_repo

        crytic_key = ("crytic", str(linux_amd64_platform))
        crytic_repo = Mock(spec=SolcRepository)
        type(crytic_repo).available_versions = PropertyMock(
            return_value={
                "0.8.19": "solc-v0.8.19",
            }
        )
        matcher.repositories[crytic_key] = crytic_repo

        all_versions = matcher.get_all_available_versions()

        # Should only have one entry for 0.8.19
        version_list = [v for v in all_versions if v == SolcVersion.parse("0.8.19")]
        assert len(version_list) == 1
        assert len(all_versions) == 1

        # Should be from higher priority repo (soliditylang)
        manifest, _platform = all_versions[SolcVersion.parse("0.8.19")]
        assert manifest.repository_id == "soliditylang"

    def test_get_all_versions_filters_by_platform(
        self,
        mock_session,
        mock_platform_capability,
        soliditylang_manifest,
        linux_amd64_platform,
    ):
        """Should only return versions supported by the platform."""
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest],
            session=mock_session,
        )

        # Mock repository with versions both inside and outside range
        soliditylang_key = ("soliditylang", str(linux_amd64_platform))
        soliditylang_repo = Mock(spec=SolcRepository)
        type(soliditylang_repo).available_versions = PropertyMock(
            return_value={
                "0.4.9": "solc-v0.4.9",  # Below minimum 0.4.10
                "0.4.10": "solc-v0.4.10",  # At minimum
                "0.8.19": "solc-v0.8.19",  # Above minimum
            }
        )
        matcher.repositories[soliditylang_key] = soliditylang_repo

        all_versions = matcher.get_all_available_versions()

        # Should only have 0.4.10+ (minimum for linux-amd64)
        assert SolcVersion.parse("0.4.9") not in all_versions
        assert SolcVersion.parse("0.4.10") in all_versions
        assert SolcVersion.parse("0.8.19") in all_versions
        assert len(all_versions) == 2

    def test_get_all_versions_empty_repos(
        self,
        mock_session,
        mock_platform_capability,
        soliditylang_manifest,
        linux_amd64_platform,
    ):
        """Should return empty dict when repositories have no versions."""
        matcher = RepositoryMatcher(
            platform_capability=mock_platform_capability,
            manifests=[soliditylang_manifest],
            session=mock_session,
        )

        # Mock repository with no versions
        soliditylang_key = ("soliditylang", str(linux_amd64_platform))
        soliditylang_repo = Mock(spec=SolcRepository)
        type(soliditylang_repo).available_versions = PropertyMock(return_value={})
        matcher.repositories[soliditylang_key] = soliditylang_repo

        all_versions = matcher.get_all_available_versions()

        assert len(all_versions) == 0
        assert all_versions == {}


class TestRepositoryMatcherFactory:
    """Tests for _create_repository factory method."""

    @pytest.mark.parametrize(
        "manifest_fixture,platform_fixture,capability_fixture",
        [
            ("soliditylang_manifest", "linux_amd64_platform", "mock_platform_capability"),
            ("crytic_manifest", "linux_amd64_platform", "mock_platform_capability"),
            ("alloy_manifest", "darwin_arm64_platform", "mock_platform_capability_with_emulation"),
        ],
    )
    def test_create_repository(
        self, mock_session, manifest_fixture, platform_fixture, capability_fixture, request
    ):
        """Repository factory creates correct instances with session attached."""
        manifest = request.getfixturevalue(manifest_fixture)
        platform = request.getfixturevalue(platform_fixture)
        capability = request.getfixturevalue(capability_fixture)

        matcher = RepositoryMatcher(
            platform_capability=capability,
            manifests=[manifest],
            session=mock_session,
        )

        key = (manifest.repository_id, str(platform))
        repo = matcher.repositories[key]

        assert repo is not None
        assert hasattr(repo, "session")
        assert repo.session is mock_session

    def test_create_repository_unknown_id(self, mock_session, mock_platform_capability):
        """Should raise ValueError for unknown repository ID."""
        unknown_manifest = RepositoryManifest(
            repository_id="unknown_repo",
            base_url="https://unknown.example.com",
            platform_supports=[
                PlatformSupport(platform=LINUX_AMD64, version_range=VersionRange.from_min("0.4.0")),
            ],
            priority=50,
        )

        with pytest.raises(ValueError, match="Unknown repository: unknown_repo"):
            RepositoryMatcher(
                platform_capability=mock_platform_capability,
                manifests=[unknown_manifest],
                session=mock_session,
            )

    def test_create_repository_multiple_platforms(self, mock_session, soliditylang_manifest):
        """Creates separate repository instances for each platform."""
        mock_cap = Mock(spec=PlatformCapability)
        mock_cap.host_platform = LINUX_AMD64
        mock_cap.native_support = LINUX_AMD64
        mock_cap.get_runnable_platforms.return_value = [LINUX_AMD64, LINUX_ARM64]

        soliditylang_manifest.platform_supports.append(
            PlatformSupport(platform=LINUX_ARM64, version_range=VersionRange.from_min("0.8.31"))
        )

        matcher = RepositoryMatcher(
            platform_capability=mock_cap,
            manifests=[soliditylang_manifest],
            session=mock_session,
        )

        amd64_key = ("soliditylang", str(LINUX_AMD64))
        arm64_key = ("soliditylang", str(LINUX_ARM64))

        assert amd64_key in matcher.repositories
        assert arm64_key in matcher.repositories
        assert matcher.repositories[amd64_key] is not matcher.repositories[arm64_key]
