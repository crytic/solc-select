#!/usr/bin/env bash

use_version=$(solc-select use 0.3.6)
if [[ $use_version != "Switched global version to 0.3.6"* ]]; then
  echo "Mac OS X minimum version failed"
  exit 255
fi

use_version=$(solc-select use 0.8.6)
if [[ $use_version != "Switched global version to 0.8.6" ]]; then
  echo "Mac OS X maximum version failed"
  exit 255
fi
