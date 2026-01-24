#!/bin/bash
set -e

# Detect container runtime
if command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
elif command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
else
    echo "Error: Neither docker nor podman found"
    exit 1
fi

echo "=== Using $CONTAINER_CMD ==="
echo "=== Building image ==="
$CONTAINER_CMD build -t sdlc-mcp .

echo -e "\n=== Testing MCP server ==="

# Test with a simple search
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_documentation", "arguments": {"search_phrase": "testing", "limit": 2}}}' | $CONTAINER_CMD run -i sdlc-mcp | head -10

echo -e "\n=== Test completed ==="
