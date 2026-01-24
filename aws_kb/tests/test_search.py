#!/usr/bin/env python3
"""Test pqsoft_search_docs tool"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_search():
    server_params = StdioServerParameters(
        command="python3",
        args=[str(Path(__file__).parent.parent / "server.py")]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Basic search
            print("Test 1: Basic search for 'testing'")
            result = await session.call_tool("pqsoft_search_docs", {
                "search_phrase": "testing strategies",
                "limit": 5
            })
            print(f"  Found {len(result.content)} results")
            assert len(result.content) > 0, "Should return results"
            
            # Test 2: Limit parameter
            print("Test 2: Search with limit=3")
            result = await session.call_tool("pqsoft_search_docs", {
                "search_phrase": "deployment",
                "limit": 3
            })
            print(f"  Found {len(result.content)} results")
            assert len(result.content) <= 3, "Should respect limit"
            
            # Test 3: Verify result structure
            print("Test 3: Verify result structure")
            result = await session.call_tool("pqsoft_search_docs", {
                "search_phrase": "best practices",
                "limit": 1
            })
            item = result.content[0]
            assert 'title' in item, "Should have title"
            assert 'filename' in item, "Should have filename"
            assert 'content' in item, "Should have content"
            assert 'similarity' in item, "Should have similarity score"
            print("  ✓ All fields present")
            
            print("\n✅ All search tests passed!")

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_search())
