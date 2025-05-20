#!/usr/bin/env bash

set -e

VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
  echo "📦 Creating virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

if ! pip show pyyaml > /dev/null 2>&1; then
  echo "📥 Installing PyYAML..."
  pip install pyyaml
fi

# Run the standalone pre_process.py script
python3 config/snowflake/pre_process.py "$1"

mv $1/stream.yaml $1/streams.yaml
