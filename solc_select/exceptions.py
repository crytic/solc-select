"""Custom exception classes for solc-select."""


class SolcSelectError(Exception):
    """Base exception for all solc-select errors."""


class VersionNotFoundError(SolcSelectError):
    """Raised when requested version doesn't exist or isn't available."""

    def __init__(
        self,
        version: str,
        available_versions: list[str] | None = None,
        suggestion: str | None = None,
    ):
        self.version = version
        self.available_versions = available_versions or []
        self.suggestion = suggestion

        message = f"Version '{version}' not found"
        if available_versions:
            if len(available_versions) <= 5:
                message += f". Available versions: {', '.join(available_versions)}"
            else:
                message += f". {len(available_versions)} versions available. Run 'solc-select install' to see all options"

        if suggestion:
            message += f". {suggestion}"

        super().__init__(message)


class VersionNotInstalledError(SolcSelectError):
    """Raised when trying to use a version that isn't installed."""

    def __init__(
        self,
        version: str,
        installed_versions: list[str] | None = None,
        source: str | None = None,
    ):
        self.version = version
        self.installed_versions = installed_versions or []
        self.source = source

        message = f"Version '{version}' is not installed"

        if source:
            message += f" (set by {source})"

        message += f". Run `solc-select install {version}` to install it"

        if installed_versions:
            if len(installed_versions) <= 3:
                message += f", or use one of: {', '.join(installed_versions)}"
            else:
                message += f". You have {len(installed_versions)} versions installed. Run 'solc-select versions' to see them"

        super().__init__(message)


class PlatformNotSupportedError(SolcSelectError):
    """Raised when platform is not supported for a specific version."""

    def __init__(self, version: str, platform: str, min_version: str | None = None):
        self.version = version
        self.platform = platform
        self.min_version = min_version

        message = f"Version '{version}' is not supported on {platform}"
        if min_version:
            message += f". Minimum supported version is '{min_version}'"

        super().__init__(message)


class ChecksumMismatchError(SolcSelectError):
    """Raised when downloaded file checksum doesn't match expected value."""

    def __init__(self, expected: str, actual: str, algorithm: str = "SHA256"):
        self.expected = expected
        self.actual = actual
        self.algorithm = algorithm

        super().__init__(
            f"{algorithm} checksum verification failed. "
            f"Expected: {expected}, Got: {actual}. "
            f"This could indicate a corrupted download or security issue."
        )


class InstallationError(SolcSelectError):
    """Raised when installation fails."""

    def __init__(self, version: str, reason: str):
        self.version = version
        self.reason = reason
        super().__init__(f"Failed to install version '{version}': {reason}")


class NetworkError(SolcSelectError):
    """Raised when network operations fail."""

    def __init__(
        self, operation: str, url: str | None = None, original_error: Exception | None = None
    ):
        self.operation = operation
        self.url = url
        self.original_error = original_error

        message = f"Network error during {operation}"
        if url:
            message += f" from {url}"
        if original_error:
            message += f": {original_error!s}"

        super().__init__(message)


class VersionResolutionError(SolcSelectError):
    """Raised when version resolution fails (e.g., 'latest' can't be determined)."""

    def __init__(self, requested: str, reason: str):
        self.requested = requested
        self.reason = reason
        super().__init__(f"Could not resolve version '{requested}': {reason}")


class NoVersionSetError(SolcSelectError):
    """Raised when no solc version is currently set."""

    def __init__(self) -> None:
        super().__init__(
            "No solc version set. Run `solc-select use VERSION` or set SOLC_VERSION environment variable."
        )


class ArchitectureUpgradeError(SolcSelectError):
    """Raised when architecture upgrade fails."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Failed to upgrade solc-select architecture: {reason}")
