#!/bin/bash

# Detect container runtime
if command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
elif command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
else
    echo "Error: Neither docker nor podman found"
    exit 1
fi

echo "=== Testing MCP Server with $CONTAINER_CMD ==="

# Test with proper MCP initialize message
echo "Testing initialize..."
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}' | $CONTAINER_CMD run -i sdlc-mcp 2>/dev/null | grep -E '^\{.*\}$'

echo -e "\nTesting tools/list..."
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}' | $CONTAINER_CMD run -i sdlc-mcp 2>/dev/null | grep -E '^\{.*\}$' | tail -1

echo -e "\n=== Test completed ==="
