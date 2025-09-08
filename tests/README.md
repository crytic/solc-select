# solc-select Test Suite

This directory contains the pytest-based test suite for solc-select.

## Test Structure

- `conftest.py` - Pytest configuration and fixtures for test isolation
- `test_compiler_versions.py` - Tests for different Solidity compiler versions
- `test_platform_specific.py` - Platform-specific boundary tests
- `test_upgrade.py` - Tests for upgrade functionality

## Running Tests

### Install test dependencies

```bash
# Install with all development dependencies (testing + linting)
pip install -e ".[dev]"
```

### Run all tests

```bash
pytest
```

### Run specific test files

```bash
pytest tests/test_compiler_versions.py
pytest tests/test_platform_specific.py
pytest tests/test_upgrade.py
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

The test suite uses several fixtures to ensure proper isolation:

- `isolated_solc_data` - Creates isolated solc-select data environment using VIRTUAL_ENV
- `isolated_python_env` - Creates completely isolated Python environment for install/uninstall tests
- `test_contracts_dir` - Path to test Solidity contracts in `tests/solidity_tests/`

### Helper Functions

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
