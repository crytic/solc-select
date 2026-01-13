"""Version-related domain models."""

from dataclasses import dataclass

from packaging.version import Version


@dataclass(frozen=True)
class VersionRange:
    """Inclusive version range [min, max].

    None means unbounded in that direction.
    """

    min_version: "SolcVersion | None" = None  # None = no lower bound
    max_version: "SolcVersion | None" = None  # None = no upper bound

    def contains(self, version: "SolcVersion") -> bool:
        """Check if version is within range (inclusive).

        Args:
            version: Version to check

        Returns:
            True if version is in [min, max], False otherwise
        """
        above_minimum = self.min_version is None or version >= self.min_version
        below_maximum = self.max_version is None or version <= self.max_version
        return above_minimum and below_maximum

    @classmethod
    def from_min(cls, min_ver: str) -> "VersionRange":
        """Create range with only minimum version.

        Args:
            min_ver: Minimum version string

        Returns:
            VersionRange from min_ver to infinity
        """
        # Import here to avoid circular import
        return cls(min_version=SolcVersion.parse(min_ver), max_version=None)

    @classmethod
    def exact_range(cls, min_ver: str, max_ver: str) -> "VersionRange":
        """Create exact range [min, max].

        Args:
            min_ver: Minimum version string
            max_ver: Maximum version string

        Returns:
            VersionRange from min_ver to max_ver (inclusive)
        """
        return cls(
            min_version=SolcVersion.parse(min_ver),
            max_version=SolcVersion.parse(max_ver),
        )


class SolcVersion(Version):
    """Represents a Solidity compiler version, inheriting from packaging.Version."""

    @classmethod
    def parse(cls, version_str: str) -> "SolcVersion":
        """Parse a version string into a SolcVersion instance.

        Args:
            version_str: Version string like '0.8.19'

        Returns:
            SolcVersion instance

        Raises:
            ValueError: If version string format is invalid
        """
        if version_str == "latest":
            raise ValueError("Cannot parse 'latest' - resolve to actual version first")

        # Let packaging.Version handle the parsing and validation
        return cls(version_str)
