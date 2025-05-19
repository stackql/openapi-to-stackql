#!/usr/bin/env bash

set -e

VENV_DIR=".venv"

# Create virtualenv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtualenv
source "$VENV_DIR/bin/activate"

# Install dependencies
# echo "Installing dependencies via pip..."
# pip install -r requirements.txt

# Run the CLI
python -m openapi_to_stackql.cli "$@"
