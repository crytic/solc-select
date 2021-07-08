#!/usr/bin/env bash

use_version=$(solc-select use 0.4.5)
if [[ $use_version != "Switched global version to 0.4.5"* ]]; then
  echo "WINDOWS FAILED: minimum version"
  exit 255
fi
echo "WINDOWS SUCCESS: minimum version"

use_version=$(solc-select use 0.8.6)
if [[ $use_version != "Switched global version to 0.8.6"* ]]; then
  echo "WINDOWS FAILED: maximum version"
  exit 255
fi
echo "WINDOWS SUCCESS: maximum version"
