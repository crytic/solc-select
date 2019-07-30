#!/bin/bash

function install_solc {
    solc="$SSELECT_INSTALL_DIR/usr/bin/solc-${1}"
    curl -s -f -L "https://github.com/ethereum/solidity/releases/download/${1}/solc-static-linux" -o "$solc" && chmod +x "$solc" && echo "Installed solc-${1}"
}

function solc_releases {
  curl --silent "https://api.github.com/repos/ethereum/solidity/releases" |
    grep '"tag_name":' |
    sed -E 's/.*"([^"]+)".*/\1/'
}

if [ ! -z "$SSELECT_INSTALL_DIR" ]; then
  echo "Installing solc versions into $SSELECT_INSTALL_DIR/usr/bin"
fi

for tag in $(solc_releases); do
    install_solc "$tag" || true
done
