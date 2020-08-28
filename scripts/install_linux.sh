#!/bin/bash

export SSELECT_INSTALL_DIR="$HOME/.solc-select"

if [ ! -d "$SSELECT_INSTALL_DIR" ]; then
    echo "Creating install dir ${SSELECT_INSTALL_DIR}"
    mkdir $SSELECT_INSTALL_DIR
else
    echo "Install dir ${SSELECT_INSTALL_DIR} exists"
fi

BIN_DIR="$SSELECT_INSTALL_DIR/usr/bin"
if [ ! -d $BIN_DIR ]; then
    mkdir -p $BIN_DIR
fi

bash ./install_solc.sh


SOLC_SELECT_SCRIPT="$BIN_DIR/solc-select"
cp ./solc-select $SOLC_SELECT_SCRIPT
chmod +x $SOLC_SELECT_SCRIPT

$SOLC_SELECT_SCRIPT --list | grep -v nightly | tail -n1 | xargs $SOLC_SELECT_SCRIPT

SOLC_RUNNER_SCRIPT="$BIN_DIR/solc-runner"
cp ./solc $SOLC_RUNNER_SCRIPT
chmod +x $SOLC_RUNNER_SCRIPT

SOLC_SCRIPT="$SSELECT_INSTALL_DIR/solc"
cp ../bin/solc $SOLC_SCRIPT

cp completion.sh $SSELECT_INSTALL_DIR

echo "Installed solc into $SOLC_SCRIPT."
echo ""
echo "Add the following lines to your .bashrc file:"
echo "  export PATH=$SSELECT_INSTALL_DIR:\$PATH"
echo "  source $SELECT_INSTALL_DIR\\completion.sh"
