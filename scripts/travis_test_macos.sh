#!/usr/bin/env bash

solc-select use 0.3.6
if [ $? != "Switched global version to 0.3.6 " ]; then
  echo "Mac OS X minimum version failed"
  exit 255
fi

solc-select use 0.8.6
if [ $? != "Switched global version to 0.8.6 " ]; then
  echo "Mac OS X maximum version failed"
  exit 255
fi
