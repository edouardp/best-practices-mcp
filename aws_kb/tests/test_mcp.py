#!/usr/bin/env python3
"""Test MCP server tools"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_tools():
    server_params = StdioServerParameters(
        command="python3",
        args=[str(Path(__file__).parent.parent / "server.py")],
        env={"AWS_PROFILE": "admin"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test search
            print("✅ Test 1: pqsoft_search_docs")
            result = await session.call_tool("pqsoft_search_docs", {
                "search_phrase": "python best practices",
                "limit": 3
            })
            print(f"   Found {len(result.content[0]['content'])} results")
            for i, item in enumerate(result.content[0]['content'][:2], 1):
                print(f"   {i}. {item['title']} (score: {item['similarity']:.3f})")
            
            # Test read
            print("\n✅ Test 2: pqsoft_read_docs")
            result = await session.call_tool("pqsoft_read_docs", {
                "documentation_path": "PYTHON_BEST_PRACTICES.md",
                "start_line": 1,
                "end_line": 5
            })
            print(f"   Read {len(result.content[0]['content'].split(chr(10)))} lines")
            
            # Test recommend
            print("\n✅ Test 3: pqsoft_recommend_docs")
            result = await session.call_tool("pqsoft_recommend_docs", {
                "title": "Python Best Practices"
            })
            print(f"   Found {len(result.content[0]['content'])} recommendations")
            
            print("\n🎉 All MCP tools working!")

if __name__ == '__main__':
    asyncio.run(test_tools())
