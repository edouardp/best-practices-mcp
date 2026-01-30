#!/usr/bin/env python3
"""Integration tests for local MCP server using MCP client library."""

import pytest
from pathlib import Path
import json

# Requires: pip install mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_search_docs():
    """Test pqsoft_search_docs tool."""
    script_path = Path(__file__).parent.parent.parent / "run-local-mcp.sh"
    
    server_params = StdioServerParameters(
        command=str(script_path),
        args=[],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool(
                "pqsoft_search_docs",
                arguments={"search_phrase": "testing strategies", "limit": 5}
            )
            
            assert result is not None
            assert len(result.content) > 0
            
            results = json.loads(result.content[0].text)
            assert isinstance(results, list)
            assert len(results) <= 5
            
            if results:
                assert "title" in results[0]
                assert "filename" in results[0]
                assert "content" in results[0]
                print(f"✓ Found {len(results)} results, top: {results[0]['title']}")


@pytest.mark.asyncio
async def test_read_docs():
    """Test pqsoft_read_docs tool."""
    script_path = Path(__file__).parent.parent.parent / "run-local-mcp.sh"
    
    server_params = StdioServerParameters(
        command=str(script_path),
        args=[],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            result = await session.call_tool(
                "pqsoft_read_docs",
                arguments={
                    "documentation_path": "README.md",
                    "start_line": 1,
                    "end_line": 10
                }
            )
            
            assert result is not None
            assert len(result.content) > 0
            content = result.content[0].text
            assert len(content) > 0
            print(f"✓ Read {len(content)} characters")
