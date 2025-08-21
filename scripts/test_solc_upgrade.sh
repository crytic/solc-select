#!/usr/bin/env bash
set -euo pipefail

### Install old version of solc
pip3 uninstall --yes solc-select
pip3 install solc-select
solc-select use 0.8.0 --always-install
old_solc_version=$(solc --version)
solc-select install 0.4.11 0.5.0 0.6.12 0.7.3 0.8.3
all_old_versions=$(solc-select versions | sort)

### Install new version of solc
pip3 uninstall --yes solc-select
pip3 install -e .
new_solc_version=$(solc --version)
all_new_versions=$(solc-select versions | sort)

### halt if solc version is accidentally changed
if [ "$old_solc_version" != "$new_solc_version" ]; then
  echo "solc version changed"
  exit 255
fi

if [ "$all_old_versions" != "$all_new_versions" ]; then
  echo "Upgrade failed"
  exit 255
fi

echo "Upgrade successful"
