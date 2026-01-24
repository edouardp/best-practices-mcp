#!/bin/bash
set -e

cd "$(dirname "$0")/aws_kb"

# Check if config exists
if [ ! -f "config.json" ]; then
    echo "Error: config.json not found!"
    echo "Please run: ./aws_kb/scripts/deploy_stack.sh"
    exit 1
fi

# Sync dependencies
uv sync --quiet

# Check if docs need syncing
DOCS_DIR="../docs"
SYNC_MARKER=".last_sync"

if [ ! -f "$SYNC_MARKER" ] || [ "$DOCS_DIR" -nt "$SYNC_MARKER" ]; then
    echo "Docs changed, syncing to Knowledge Base..."
    ./scripts/sync_docs.sh
    touch "$SYNC_MARKER"
fi

# Run server
uv run python server.py
