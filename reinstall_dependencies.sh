#!/bin/bash
# Script to reinstall dependencies with the correct versions

echo "Uninstalling potentially conflicting packages..."
pip uninstall -y openai httpx

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Installation complete. Try running the test scripts again." 