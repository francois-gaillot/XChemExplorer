#!/bin/bash

export XChemExplorer_DIR=$(dirname "$(realpath $0)")
source $XChemExplorer_DIR/setup-scripts/xce.setup-sh

ccp4-python $XChemExplorer_DIR/XChemExplorer.py
