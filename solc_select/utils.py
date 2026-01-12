from packaging.version import Version


def sort_versions(versions: list[str]) -> list[str]:
    """Sorts a list of versions following the component order (major/minor/patch)"""
    return sorted(versions, key=Version)
