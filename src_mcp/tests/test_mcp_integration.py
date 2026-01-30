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


@pytest.mark.asyncio
async def test_recommend_docs():
    """Test pqsoft_recommend_docs tool."""
    script_path = Path(__file__).parent.parent.parent / "run-local-mcp.sh"
    
    server_params = StdioServerParameters(
        command=str(script_path),
        args=[],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # First search to get a valid title
            search_result = await session.call_tool(
                "pqsoft_search_docs",
                arguments={"search_phrase": "testing", "limit": 1}
            )
            
            search_results = json.loads(search_result.content[0].text)
            if not search_results:
                pytest.skip("No documents found to test recommendations")
            
            title = search_results[0]["title"]
            
            # Now test recommend with that title
            result = await session.call_tool(
                "pqsoft_recommend_docs",
                arguments={"title": title}
            )
            
            assert result is not None
            # Recommendations might be empty if no similar docs exist
            if result.content:
                recommendations = json.loads(result.content[0].text)
                assert isinstance(recommendations, list)
                print(f"✓ Got {len(recommendations)} recommendations for '{title}'")
            else:
                print(f"✓ No recommendations found for '{title}' (expected if only one doc)")
