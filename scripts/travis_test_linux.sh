#!/usr/bin/env bash

sudo python3 setup.py install
solc-select install all

solc-select use 0.4.0
if [ $? != "Switched global version to 0.4.0" ]; then
  echo "Linux minimum version failed"
  exit 255
fi

solc-select use 0.8.6
if [ $? != "Switched global version to 0.8.6" ]; then
  echo "Linux maximum version failed"
  exit 255
fi
