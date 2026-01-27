#!/bin/bash
set -e

cd "$(dirname "$0")/src_mcp"

uv sync --native-tls --quiet

DB_FILE="sdlc_docs.db"
NEEDS_REBUILD=false

if [ ! -f "$DB_FILE" ]; then
    NEEDS_REBUILD=true
else
    NEWEST_DOC=$(find ../docs -type f -name "*.md" -exec stat -f "%m %N" {} \; 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
    if [ -n "$NEWEST_DOC" ]; then
        if [ "$NEWEST_DOC" -nt "$DB_FILE" ]; then
            NEEDS_REBUILD=true
        fi
    fi
fi

if [ "$NEEDS_REBUILD" = true ]; then
    echo "Building index..." >&2
    uv run python build_index.py
fi

uv run python server.py
