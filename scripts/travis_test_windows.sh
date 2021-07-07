#!/usr/bin/env bash

use_version=$(solc-select use 0.4.5)
if [[ $use_version != "Switched global version to 0.4.5"* ]]; then
  echo "Windows minimum version failed"
  exit 255
fi

use_version=$(solc-select use 0.8.6)
if [[ $use_version != "Switched global version to 0.8.6"* ]]; then
  echo "Windows maximum version failed"
  exit 255
fi

echo "Windows min/max versions successful"