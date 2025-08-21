# solc-select Test Suite

This directory contains the pytest-based test suite for solc-select, converted from the original bash scripts.

## Test Structure

- `conftest.py` - Pytest configuration and fixtures for test isolation
- `test_compiler_versions.py` - Tests for different Solidity compiler versions (from test_solc.sh)
- `test_platform_specific.py` - Platform-specific boundary tests (from test_linux.sh, test_macos.sh, test_windows.sh)
- `test_upgrade.py` - Tests for upgrade functionality (from test_solc_upgrade.sh)

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

### Skip slow tests (like upgrade test)
```bash
pytest -m "not slow"
```

## Test Fixtures

The test suite uses several fixtures to ensure proper isolation:

- `backup_current_version` - Backs up and restores the current solc version
- `clean_artifacts` - Provides complete isolation by backing up all installed versions
- `run_command` - Executes shell commands exactly as the bash tests did
- `test_contracts_dir` - Path to test Solidity contracts

## Comparison with Bash Tests

The pytest tests are designed to be a conservative 1:1 conversion of the bash tests:

| Bash Script | Pytest Module | Description |
|------------|---------------|-------------|
| test_solc.sh | test_compiler_versions.py | Compiler version tests |
| test_linux.sh | test_platform_specific.py::TestLinuxSpecific | Linux boundary tests |
| test_macos.sh | test_platform_specific.py::TestMacOSSpecific | macOS boundary tests |
| test_windows.sh | test_platform_specific.py::TestWindowsSpecific | Windows boundary tests |
| test_solc_upgrade.sh | test_upgrade.py | Upgrade preservation tests |

The tests maintain the exact same:
- Command execution patterns
- Error message checking
- Version installation behavior
- Platform-specific constraints