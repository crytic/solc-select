"""Unit tests for version-related domain models."""

import pytest

from solc_select.models.versions import SolcVersion, VersionRange


class TestVersionRange:
    """Tests for VersionRange domain model."""

    @pytest.mark.parametrize(
        "version,expected",
        [
            ("0.8.10", True),  # Within bounds
            ("0.8.0", True),  # Exact minimum (inclusive)
            ("0.8.20", True),  # Exact maximum (inclusive)
            ("0.7.6", False),  # Below minimum
            ("0.8.21", False),  # Above maximum
        ],
    )
    def test_contains_bounded_range(self, version: str, expected: bool) -> None:
        """VersionRange with both bounds should be inclusive [min, max]."""
        version_range = VersionRange(
            min_version=SolcVersion("0.8.0"),
            max_version=SolcVersion("0.8.20"),
        )
        assert version_range.contains(SolcVersion(version)) == expected

    def test_contains_unbounded_min(self) -> None:
        """None as minimum means no lower bound."""
        version_range = VersionRange(min_version=None, max_version=SolcVersion("0.8.20"))
        assert version_range.contains(SolcVersion("0.4.0"))
        assert version_range.contains(SolcVersion("0.8.20"))
        assert not version_range.contains(SolcVersion("0.8.21"))

    def test_contains_unbounded_max(self) -> None:
        """None as maximum means no upper bound."""
        version_range = VersionRange(min_version=SolcVersion("0.8.0"), max_version=None)
        assert version_range.contains(SolcVersion("0.8.0"))
        assert version_range.contains(SolcVersion("0.9.0"))
        assert not version_range.contains(SolcVersion("0.7.6"))

    def test_contains_unbounded_both(self) -> None:
        """None for both means all versions are valid."""
        version_range = VersionRange(min_version=None, max_version=None)
        assert version_range.contains(SolcVersion("0.4.0"))
        assert version_range.contains(SolcVersion("0.9.0"))

    def test_from_min_factory(self) -> None:
        """Creates open-ended range [min, infinity)."""
        version_range = VersionRange.from_min("0.8.5")
        assert version_range.min_version == SolcVersion("0.8.5")
        assert version_range.max_version is None
        assert version_range.contains(SolcVersion("0.8.5"))
        assert not version_range.contains(SolcVersion("0.8.4"))

    def test_exact_range_factory(self) -> None:
        """Creates closed range [min, max]."""
        version_range = VersionRange.exact_range("0.8.5", "0.8.23")
        assert version_range.min_version == SolcVersion("0.8.5")
        assert version_range.max_version == SolcVersion("0.8.23")
        assert version_range.contains(SolcVersion("0.8.5"))
        assert version_range.contains(SolcVersion("0.8.23"))
        assert not version_range.contains(SolcVersion("0.8.4"))
        assert not version_range.contains(SolcVersion("0.8.24"))


class TestSolcVersion:
    """Tests for SolcVersion domain model."""

    def test_parse_valid_version(self) -> None:
        """Parse valid version string."""
        version = SolcVersion.parse("0.8.19")
        assert version == SolcVersion("0.8.19")
        assert isinstance(version, SolcVersion)

    def test_parse_latest_raises_error(self) -> None:
        """Parse 'latest' should raise ValueError with clear message."""
        with pytest.raises(ValueError) as exc_info:
            SolcVersion.parse("latest")
        assert "Cannot parse 'latest'" in str(exc_info.value)
        assert "resolve to actual version first" in str(exc_info.value)

    def test_version_comparison(self) -> None:
        """SolcVersion should support comparison operations."""
        v1 = SolcVersion("0.8.19")
        v2 = SolcVersion("0.8.20")
        v3 = SolcVersion("0.8.19")

        assert v1 < v2
        assert v2 > v1
        assert v1 == v3
        assert v1 <= v3
        assert v1 >= v3
        assert v1 != v2
