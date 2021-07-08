#!/usr/bin/env bash

use_version=$(solc-select use 0.3.6)
if [[ $use_version != "Switched global version to 0.3.6"* ]]; then
  echo "OS X FAILED: minimum version"
  exit 255
fi
echo "OS X SUCCESS: minimum version"

use_version=$(solc-select use 0.8.6)
if [[ $use_version != "Switched global version to 0.8.6" ]]; then
  echo "OS X FAILED: maximum version"
  exit 255
fi
echo "OS X SUCCESS: maximum version"

solc-select use 0.4.5  &> /dev/null
solc scripts/solidity_tests/solc045_success.sol