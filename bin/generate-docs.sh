#!/usr/bin/env bash
set -e

VENV_DIR=".venv"
DOC_GEN_DIR="doc_gen"
REQUIREMENTS_FILE="requirements-doc-gen.txt"

# Create requirements file if it doesn't exist
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Creating $REQUIREMENTS_FILE with required packages..."
    cat > "$REQUIREMENTS_FILE" << EOF
psycopg
pyyaml
EOF
fi

# Create virtualenv if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtualenv
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install dependencies
echo "Installing documentation generator dependencies..."
pip install -r "$REQUIREMENTS_FILE"

# Check if provider name was provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <provider_name>"
    echo "Example: $0 digitalocean"
    exit 1
fi

PROVIDER_NAME="$1"
echo "Generating documentation for provider: $PROVIDER_NAME"

# Run the documentation generator
python "$DOC_GEN_DIR/doc_generator.py" "$PROVIDER_NAME"

# Deactivate virtualenv
deactivate

echo "Documentation generation complete for $PROVIDER_NAME!"
echo "Results are available in provider_docs/${PROVIDER_NAME}-docs/"