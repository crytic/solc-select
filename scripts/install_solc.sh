#!/bin/bash

function install_solc {
    solc="/usr/bin/solc-${1}"
    curl -L "https://github.com/ethereum/solidity/releases/download/${1}/solc-static-linux" > "$solc"
    chmod +x "$solc"
}

for ((i=11;i<=25;i++)); do
    install_solc v0.4."$i"
done
for ((i=0;i<=5;i++)); do
    install_solc v0.5."$i"
done
