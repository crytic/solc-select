#!/usr/bin/env bash

solc-select use 0.4.5
if [ $? != "Switched global version to 0.4.5 " ]; then
  echo "Windows minimum version failed"
  exit 255
fi

solc-select use 0.8.6
if [ $? != "Switched global version to 0.8.6 " ]; then
  echo "Windows maximum version failed"
  exit 255
fi
