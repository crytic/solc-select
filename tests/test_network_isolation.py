"""Tests for network isolation in solc operations."""

import subprocess
from typing import Any
from unittest.mock import Mock, patch

import requests


class TestNetworkIsolation:
    """Test that solc operations don't make unnecessary network requests."""

    def test_solc_version_no_network_calls_after_install(
        self, isolated_solc_data: Any, monkeypatch: Any
    ) -> None:
        """
        Verify that executing solc doesn't make network requests
        in the Python code path from service call to subprocess.run().

        This test calls the service directly (not via CLI subprocess) so that
        monkeypatch can intercept network calls in the same Python process.

        The isolated_solc_data fixture ensures the binary path resolution works
        correctly by redirecting VIRTUAL_ENV to point to the isolated test directory.
        """
        from solc_select.services.solc_service import SolcService

        # Phase 1: Install version (network calls expected/allowed)
        service = SolcService()
        service.install_versions(["0.8.33"], silent=True)
        service.switch_global_version("0.8.33")

        # Phase 2: Track network calls and mock subprocess
        network_calls = []

        def track_network_get(self: Any, url: str, *args: Any, **kwargs: Any) -> None:
            """Track all network calls and fail immediately."""
            network_calls.append(url)
            raise RuntimeError(f"Unexpected network call to: {url}")

        # Mock Session.get to detect network access
        monkeypatch.setattr(requests.Session, "get", track_network_get)

        # Mock subprocess.run to prevent actual solc execution
        # The binary path should still be resolved correctly via isolated_solc_data
        mock_result = Mock(spec=subprocess.CompletedProcess)
        mock_result.returncode = 0
        mock_result.stdout = "solc, the solidity compiler commandline interface\nVersion: 0.8.33"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_subprocess:
            # Phase 3: Create new service instance (fresh caches) and call execute_solc
            # This ensures we test the actual code path without cached repository data
            fresh_service = SolcService()
            fresh_service.execute_solc(["--version"])

            # Phase 4: Verify results
            # Verify subprocess was called (reached the binary execution step)
            assert mock_subprocess.called, "subprocess.run should have been called"

            # Verify NO network calls were made
            assert len(network_calls) == 0, (
                f"Expected no network calls in Python code path, but found: {network_calls}"
            )
