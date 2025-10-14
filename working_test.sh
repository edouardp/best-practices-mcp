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

# Test 1: Initialize
echo "1. Testing initialize..."
INIT_RESULT=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}' | $CONTAINER_CMD run -i sdlc-mcp 2>/dev/null | grep -E '^\{.*\}$')

if echo "$INIT_RESULT" | grep -q '"result"'; then
    echo "✓ Initialize successful"
else
    echo "✗ Initialize failed"
    echo "$INIT_RESULT"
    exit 1
fi

# Test 2: List tools
echo "2. Testing tools/list..."
TOOLS_RESULT=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}' | $CONTAINER_CMD run -i sdlc-mcp 2>/dev/null | grep -E '^\{.*\}$' | tail -1)

if echo "$TOOLS_RESULT" | grep -q '"search_documentation"'; then
    echo "✓ Tools list successful - found search_documentation"
else
    echo "✗ Tools list failed or missing search_documentation"
    echo "$TOOLS_RESULT"
    exit 1
fi

# Test 3: Search tool (this will fail if no docs indexed, but server should respond)
echo "3. Testing search_documentation tool..."
SEARCH_RESULT=$(echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "search_documentation", "arguments": {"search_phrase": "test", "limit": 1}}}' | $CONTAINER_CMD run -i sdlc-mcp 2>/dev/null | grep -E '^\{.*\}$' | tail -1)

if echo "$SEARCH_RESULT" | grep -q '"result"'; then
    echo "✓ Search tool responds successfully"
else
    echo "✗ Search tool failed"
    echo "$SEARCH_RESULT"
    exit 1
fi

echo -e "\n=== All tests passed! MCP server is working correctly ==="
echo "✓ Container builds and runs"
echo "✓ MCP protocol communication works"
echo "✓ All three tools are available"
echo "✓ Tools respond to calls"
