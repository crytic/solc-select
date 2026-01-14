"""Fixtures for unit tests with mocking."""

from unittest.mock import Mock

import pytest
import requests

from solc_select.infrastructure.filesystem import FilesystemManager
from solc_select.models.platforms import Platform
from solc_select.models.versions import SolcVersion
from solc_select.repositories import SolcRepository


@pytest.fixture
def mock_session():
    """Mock requests.Session for HTTP calls."""
    return Mock(spec=requests.Session)


@pytest.fixture
def mock_filesystem():
    """Mock FilesystemManager."""
    return Mock(spec=FilesystemManager)


@pytest.fixture
def mock_platform():
    """Mock Platform (linux-amd64 by default)."""
    return Platform("linux", "amd64")


@pytest.fixture
def mock_repository():
    """Mock SolcRepository with common version set."""
    mock = Mock(spec=SolcRepository)
    mock.available_versions = {
        SolcVersion("0.8.19"): "solc-linux-amd64-v0.8.19+commit.abc123",
        SolcVersion("0.8.20"): "solc-linux-amd64-v0.8.20+commit.def456",
        SolcVersion("0.8.21"): "solc-linux-amd64-v0.8.21+commit.ghi789",
    }
    mock.latest_version = SolcVersion("0.8.21")
    return mock


@pytest.fixture
def sample_versions():
    """Sample version list for testing."""
    return [
        SolcVersion("0.8.19"),
        SolcVersion("0.8.20"),
        SolcVersion("0.8.21"),
    ]


@pytest.fixture
def temp_artifacts_dir(tmp_path, monkeypatch):
    """Temporary artifacts directory for testing filesystem operations."""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    monkeypatch.setattr("solc_select.constants.ARTIFACTS_DIR", artifacts_dir)
    return artifacts_dir


@pytest.fixture
def temp_solc_select_dir(tmp_path, monkeypatch):
    """Temporary solc-select directory for testing."""
    solc_select_dir = tmp_path / ".solc-select"
    solc_select_dir.mkdir()
    artifacts_dir = solc_select_dir / "artifacts"
    artifacts_dir.mkdir()

    # Patch constants module
    monkeypatch.setattr("solc_select.constants.SOLC_SELECT_DIR", solc_select_dir)
    monkeypatch.setattr("solc_select.constants.ARTIFACTS_DIR", artifacts_dir)

    # Patch where constants are imported in filesystem module
    monkeypatch.setattr("solc_select.infrastructure.filesystem.ARTIFACTS_DIR", artifacts_dir)
    monkeypatch.setattr("solc_select.infrastructure.filesystem.SOLC_SELECT_DIR", solc_select_dir)

    return solc_select_dir
