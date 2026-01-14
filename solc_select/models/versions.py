"""Version-related domain models."""

from dataclasses import dataclass

from packaging.version import Version


class SolcVersion(Version):
    """Represents a Solidity compiler version."""

    @classmethod
    def parse(cls, version_str: str) -> "SolcVersion":
        """Parse a version string into a SolcVersion instance."""
        if version_str == "latest":
            raise ValueError("Cannot parse 'latest' - resolve to actual version first")
        return cls(version_str)


@dataclass(frozen=True)
class VersionRange:
    """Inclusive version range [min, max]. None means unbounded."""

    min_version: SolcVersion | None = None
    max_version: SolcVersion | None = None

    def contains(self, version: SolcVersion) -> bool:
        """Check if version is within range (inclusive)."""
        above_minimum = self.min_version is None or version >= self.min_version
        below_maximum = self.max_version is None or version <= self.max_version
        return above_minimum and below_maximum

    @classmethod
    def from_min(cls, min_ver: str) -> "VersionRange":
        """Create range with only minimum version."""
        return cls(min_version=SolcVersion.parse(min_ver), max_version=None)

    @classmethod
    def exact_range(cls, min_ver: str, max_ver: str) -> "VersionRange":
        """Create exact range [min, max]."""
        return cls(
            min_version=SolcVersion.parse(min_ver),
            max_version=SolcVersion.parse(max_ver),
        )
