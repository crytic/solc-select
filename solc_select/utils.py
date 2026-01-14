from packaging.version import Version


def sort_versions(versions: list[str]) -> list[str]:
    """Sort versions by major/minor/patch order."""
    return sorted(versions, key=Version)
