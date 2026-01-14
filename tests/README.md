# solc-select Test Suite

This directory contains the pytest-based test suite for solc-select.

## Test Structure

The test suite is organized into two main categories:

### Integration Tests (`integration/`)
- End-to-end tests that verify actual CLI behavior
- Real HTTP requests, filesystem operations, and binary execution
- Platform-specific validation
- `test_compiler_versions.py` - Tests for different Solidity compiler versions
- `test_platform_specific.py` - Platform-specific boundary tests
- `test_upgrade.py` - Tests for upgrade functionality
- `test_network_isolation.py` - Verifies offline execution after installation
- `test_version_verification.py` - Version and checksum verification

## Running Tests

### Install test dependencies

```bash
# Install with all development dependencies (testing + linting)
uv pip install -e ".[dev]"
```

### Run all tests

```bash
# Run all tests (both unit and integration)
uv run pytest tests/

# Run only unit tests (fast)
uv run pytest tests/unit/ -v

# Run only integration tests (slower, requires network)
uv run pytest tests/integration/ -v
```

### Run specific test files

```bash
# Unit tests
uv run pytest tests/unit/services/test_version_manager.py
uv run pytest tests/unit/services/test_artifact_manager.py

# Integration tests
uv run pytest tests/integration/test_compiler_versions.py
uv run pytest tests/integration/test_platform_specific.py
uv run pytest tests/integration/test_upgrade.py
```

### Check test coverage

```bash
# Coverage for unit tests
uv run pytest tests/unit/ --cov=solc_select --cov-report=term-missing

# Coverage for all tests
uv run pytest tests/ --cov=solc_select --cov-report=html
```

### Run platform-specific tests

```bash
# Only run tests for current platform
pytest -m "not (linux or macos or windows)"

# Run Linux-specific tests (only works on Linux)
pytest -m linux

# Run macOS-specific tests (only works on macOS)
pytest -m macos

# Run Windows-specific tests (only works on Windows)
pytest -m windows
```

### Run tests in parallel (faster)

```bash
pytest -n auto
```

## Test Fixtures

The test suite uses different fixtures depending on the test type:

### Integration Test Fixtures (`integration/conftest.py`)
- `isolated_solc_data` - Creates isolated solc-select data environment using VIRTUAL_ENV
- `isolated_python_env` - Creates completely isolated Python environment for install/uninstall tests
- `test_contracts_dir` - Path to test Solidity contracts in `tests/solidity_tests/`
- Helper functions:
  - `run_command` - Executes shell commands for tests using `isolated_solc_data`
  - `run_in_venv` - Executes commands in isolated virtual environments

## Test Organization

| Test Module | Test Class | Description |
|------------|-------------|-------------|
| test_compiler_versions.py | TestCompilerVersions | Compiler version tests |
| test_compiler_versions.py | TestVersionSwitching | Version switching functionality tests |
| test_platform_specific.py | TestPlatformSpecific | Platform boundary tests |
| test_upgrade.py | TestUpgrade | Upgrade preservation tests |

## Test Configuration

Test configuration is defined in `pyproject.toml` under `[tool.pytest.ini_options]`, including:

- Custom markers for platform-specific tests (linux, macos, windows)
- Test discovery patterns
- Default options for verbose output and strict marker checking
