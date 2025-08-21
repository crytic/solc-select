# Contributing to solc-select 

Hi! Welcome to solc-select. 

## Bug Reports and Feature Suggestions 

Bug reports and feature suggestions can be submitted to our issue tracker. For bug reports, attaching the contract that caused the bug will help us in debugging and resolving the issue quickly. If you find a security vulnerability, do not open an issue; email opensource@trailofbits.com instead.

## Questions
Questions can be submitted to the issue tracker, but you may get a faster response if you ask in our [chat room](https://slack.empirehacking.nyc/) (in the #ethereum channel).

## Code 
solc-select uses the pull request contribution model. Please make an account on Github, fork this repo, and submit code contributions via pull request. For more documentation, look [here](https://guides.github.com/activities/forking/).

Some pull request guidelines:

- Work from the [`dev`](https://github.com/crytic/solc-select/dev) branch. We performed extensive tests prior to merging anything to `master`, working from `dev` will allow us to merge your work faster.
- Minimize irrelevant changes (formatting, whitespace, etc) to code that would otherwise not be touched by this patch. Save formatting or style corrections for a separate pull request that does not make any semantic changes.
- When possible, large changes should be split up into smaller focused pull requests.
- Fill out the pull request description with a summary of what your patch does, key changes that have been made, and any further points of discussion, if applicable.
- Title your pull request with a brief description of what it's changing. "Fixes #123" is a good comment to add to the description, but makes for an unclear title on its own.

## Development Setup

### Setting up the Development Environment

#### Using uv (recommended - fastest)

```bash
git clone https://github.com/crytic/solc-select.git
cd solc-select
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

#### Using pip

```bash
git clone https://github.com/crytic/solc-select.git
cd solc-select
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

#### Using make

```bash
git clone https://github.com/crytic/solc-select.git
cd solc-select
make dev
```

### Code Quality

We use automated tools to maintain code quality. Several linters and security checkers are run on all PRs.

To run them locally:

```bash
# Code formatting and linting
ruff check .           # Check for linting issues
ruff format --check .  # Check formatting
ruff format .          # Auto-format code

# Type checking (optional but recommended)
pip install pylint
pylint solc_select --rcfile pyproject.toml
```

## Running Tests

Tests use pytest and can be run locally:

```bash
# Install development dependencies (includes pytest)
pip install -e ".[dev]"

# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_compiler_versions.py

# Run tests with verbose output
pytest tests/ -v

# Skip slow tests (upgrade test) and platform boundary tests
pytest tests/ -k "not version_boundaries" -m "not slow"

# Tests also run automatically in GitHub Actions on all platforms
```

## Updating Your Fork

To keep your fork up to date with the latest changes:

```bash
git remote add upstream https://github.com/crytic/solc-select.git
git fetch upstream
git checkout dev
git merge upstream/dev
```
