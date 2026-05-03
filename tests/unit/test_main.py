"""Tests for the CLI entry point in solc_select.__main__."""

from unittest.mock import patch

import pytest

from solc_select.__main__ import solc_select


@pytest.fixture
def patched_service():
    """Patch SolcService so we can assert on switch_global_version calls."""
    with patch("solc_select.__main__.SolcService") as service_cls:
        yield service_cls.return_value


class TestUseCommand:
    """Tests for the `solc-select use` CLI command."""

    def test_use_defaults_to_auto_install(self, patched_service, monkeypatch):
        """`solc-select use 0.8.19` auto-installs by default."""
        monkeypatch.setattr("sys.argv", ["solc-select", "use", "0.8.19"])

        solc_select()

        patched_service.switch_global_version.assert_called_once_with(
            "0.8.19", auto_install=True, silent=False
        )

    def test_use_offline_disables_auto_install(self, patched_service, monkeypatch):
        """`--offline` flips auto_install to False."""
        monkeypatch.setattr("sys.argv", ["solc-select", "use", "0.8.19", "--offline"])

        solc_select()

        patched_service.switch_global_version.assert_called_once_with(
            "0.8.19", auto_install=False, silent=False
        )

    def test_use_always_install_is_deprecated_noop(self, patched_service, monkeypatch, capsys):
        """The legacy `--always-install` flag still parses but warns and is a no-op."""
        monkeypatch.setattr("sys.argv", ["solc-select", "use", "0.8.19", "--always-install"])

        solc_select()

        patched_service.switch_global_version.assert_called_once_with(
            "0.8.19", auto_install=True, silent=False
        )
        captured = capsys.readouterr()
        assert "--always-install is deprecated" in captured.err

    def test_use_offline_overrides_legacy_always_install(self, patched_service, monkeypatch):
        """`--offline` wins even if the deprecated `--always-install` is also passed."""
        monkeypatch.setattr(
            "sys.argv",
            ["solc-select", "use", "0.8.19", "--always-install", "--offline"],
        )

        solc_select()

        patched_service.switch_global_version.assert_called_once_with(
            "0.8.19", auto_install=False, silent=False
        )
