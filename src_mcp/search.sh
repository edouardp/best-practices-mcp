#!/bin/bash

if [ $# -eq 0 ]; then
    echo "Usage: $0 <search_term>"
    echo "Example: $0 'testing'"
    exit 1
fi

SEARCH_TERM="$1"

# Detect container runtime
if command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
elif command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
else
    echo "Error: Neither docker nor podman found"
    exit 1
fi

echo "Searching for: '$SEARCH_TERM'"
echo "================================"

# Show the full server response
echo "Server response:"
RESULT=$($CONTAINER_CMD run -i sdlc-mcp 2>/dev/null << EOF
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "search-client", "version": "1.0"}}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_documentation", "arguments": {"search_phrase": "$SEARCH_TERM", "limit": 5}}}
EOF
)

echo "$RESULT"
