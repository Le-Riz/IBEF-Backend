#!/usr/bin/env bash

# TODO: Remove hatch and just use venv

set -euo pipefail

if [ -d ".venv" ]; then
    echo "Virtual environment already exists. Skipping creation."
else
    python3 -m venv .venv
    echo "Virtual environment created successfully."
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
fi