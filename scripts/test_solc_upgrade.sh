#!/usr/bin/env bash

### Install old version of solc
sudo pip3 uninstall solc-select
sudo pip3 install solc-select
old_solc_version=$(solc --version)
solc-select install 0.4.11 0.5.0 0.6.12 0.7.3 0.8.3
all_old_versions=$(solc-select versions)

### Install new version of solc
sudo python3 setup.py develop
new_solc_version=$(solc --version)
all_new_versions=$(solc-select versions)

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