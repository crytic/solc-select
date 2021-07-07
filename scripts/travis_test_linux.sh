#!/usr/bin/env bash

sudo python3 setup.py install
solc-select install all

use_version=$(solc-select use 0.4.0)
if [[ $use_version != *"Switched global version to 0.4.0"* ]]; then
  echo "Linux minimum version failed"
  exit 255
fi

use_version=$(solc-select use 0.8.6)
if [[ $use_version != *"Switched global version to 0.8.6"* ]]; then
  echo "Linux maximum version failed"
  exit 255
fi

echo "Linux min/max versions successful"