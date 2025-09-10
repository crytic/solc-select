from typing import List

from packaging.version import Version


def sort_versions(versions: List[str]) -> List[str]:
    """Sorts a list of versions following the component order (major/minor/patch)"""
    return sorted(versions, key=Version)
