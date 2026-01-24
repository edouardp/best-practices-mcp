#!/bin/bash
set -e

cd "$(dirname "$0")"

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "Error: config.json not found!"
    echo "Please run: ./scripts/deploy_stack.sh"
    exit 1
fi

# Run server
exec uv run server.py
