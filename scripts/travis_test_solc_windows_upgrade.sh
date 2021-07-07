#!/usr/bin/env bash

### Install old version of solc
pip3 uninstall solc-select
pip3 install solc-select
unsupported_platform=$(solc-select install 0.5.3)
if [ "$unsupported_platform" != "Unsupported platform" ]; then
  echo "Windows installation failed"
  exit 255
fi

### Install new version of solc
python3 setup.py develop

if [ $? -ne 0 ]
then
    echo "Windows support unsuccessful"
    exit 255
fi

echo "Upgrade successful"