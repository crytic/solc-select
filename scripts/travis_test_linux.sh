#!/usr/bin/env bash

sudo python3 setup.py install
solc-select install all

use_version=$(solc-select use 0.4.0)
if [[ $use_version != *"Switched global version to 0.4.0"* ]]; then
  echo "LINUX FAILED: minimum version"
  exit 255
fi
echo "LINUX SUCCESS: minimum version"

use_version=$(solc-select use 0.8.6)
if [[ $use_version != *"Switched global version to 0.8.6"* ]]; then
  echo "LINUX FAILED: maximum version"
  exit 255
fi

echo "LINUX SUCCESS: maximum version"