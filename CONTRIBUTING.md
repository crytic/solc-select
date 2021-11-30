# Contribuing to solc-select 

Hi! Welcome to solc-select. 

## Bug Reports and Feature Suggestions 

Bug reports and feature suggestions can be submitted to our issue tracker. For bug reports, attaching the contract that caused the bug will help us in debugging and resolving the issue quickly. If you find a security vulnerability, do not open an issue; email opensource@trailofbits.com instead.

## Questions
Questions can be submitted to the issue tracker, but you may get a faster response if you ask in our [chat room](https://empireslacking.herokuapp.com/) (in the #ethereum channel).

## Code 
solc-select uses the pull request contribution model. Please make an account on Github, fork this repo, and submit code contributions via pull request. For more documentation, look [here](https://guides.github.com/activities/forking/).

Some pull request guidelines:

- Work from the [`dev`](https://github.com/crytic/solc-select/dev) branch. We performed extensive tests prior to merging anything to `master`, working from `dev` will allow us to merge your work faster.
- Minimize irrelevant changes (formatting, whitespace, etc) to code that would otherwise not be touched by this patch. Save formatting or style corrections for a separate pull request that does not make any semantic changes.
- When possible, large changes should be split up into smaller focused pull requests.
- Fill out the pull request description with a summary of what your patch does, key changes that have been made, and any further points of discussion, if applicable.
- Title your pull request with a brief description of what it's changing. "Fixes #123" is a good comment to add to the description, but makes for an unclear title on its own.

## Linters

Several linters and security checkers are run on the PRs.

To run them locally in the root dir of the repository:

- `pylint solc_select --rcfile pyproject.toml`
- `black . --config pyproject.toml`

We use pylint `2.8.2` black `20.8b1`.

## Running Tests

These tests can be run locally by using the  `bash test_{linux | macos | windows}.sh` respective scripts. 

These will also run in a github workflow on each platform.

## Developer Environment

```bash
pip3 install virtualenvwrapper
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv --python=`which python3` solc-select-dev
git clone https://github.com/crytic/solc-select.git
cd solc-select 
python setup.py develop
```

Start a shell using the solc-select virutal environment by running:

```bash
workon solc-select-dev
```

Update `solc-select` by running `git pull` from the `solc-select/` directory.
