#!/bin/bash
# Run integration tests for local MCP server

set -e

cd "$(dirname "$0")"

echo "Installing dependencies..."
uv sync --group dev

echo ""
echo "Running MCP integration tests..."
uv run pytest src_mcp/tests/test_mcp_integration.py -v
