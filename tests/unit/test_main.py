"""Tests for the solc-select command line parser."""

import pytest

from solc_select.__main__ import create_parser


def test_versions_rejects_unexpected_arguments():
    """`versions` takes no arguments, so extras must fail instead of being ignored."""
    parser = create_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["versions", "bogus-extra"])
    assert excinfo.value.code == 2


def test_upgrade_rejects_unexpected_arguments():
    """`upgrade` takes no arguments, so extras must fail instead of being ignored."""
    parser = create_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["upgrade", "bogus-extra"])
    assert excinfo.value.code == 2


def test_versions_accepts_no_arguments():
    """`versions` without arguments still parses."""
    parser = create_parser()
    args = parser.parse_args(["versions"])
    assert args.command == "versions"
