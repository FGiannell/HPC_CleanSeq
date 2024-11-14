#!/bin/bash

echo "Downloading centrifuge ..."
cd $SCRATCH
git clone https://github.com/DaehwanKimLab/centrifuge
cd centrifuge
echo "Centrifuge downloaded."

echo "Compiling Centrifuge ..."
make
echo "Centrifuge compiled."

echo "Creating the python virtual environment for recentrifuge ..."
python3 -m venv recenv
source recenv/bin/activate
echo "Python environment created successfully."

echo "Installing Recentrifuge and Rextract in the python environment ..."
pip install recentrifuge
echo "Recentrifuge and Rextract installed successfully."

