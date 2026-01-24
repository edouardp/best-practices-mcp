#!/usr/bin/env python3
"""Test pqsoft_recommend_docs tool"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_recommend():
    server_params = StdioServerParameters(
        command="python3",
        args=[str(Path(__file__).parent.parent / "server.py")]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Get recommendations for a document
            print("Test 1: Get recommendations for 'Testing Strategies'")
            result = await session.call_tool("pqsoft_recommend_docs", {
                "title": "Testing Strategies"
            })
            print(f"  Found {len(result.content)} recommendations")
            assert len(result.content) > 0, "Should return recommendations"
            assert len(result.content) <= 5, "Should return max 5 recommendations"
            
            # Test 2: Verify result structure
            print("Test 2: Verify recommendation structure")
            result = await session.call_tool("pqsoft_recommend_docs", {
                "title": "Coding Standards"
            })
            if len(result.content) > 0:
                item = result.content[0]
                assert 'title' in item, "Should have title"
                assert 'filename' in item, "Should have filename"
                assert 'content' in item, "Should have content"
                assert 'similarity' in item, "Should have similarity score"
                print("  ✓ All fields present")
            
            # Test 3: Verify original document is excluded
            print("Test 3: Verify original document excluded from recommendations")
            result = await session.call_tool("pqsoft_recommend_docs", {
                "title": "Deployment Best Practices"
            })
            for item in result.content:
                assert 'Deployment Best Practices' not in item['title'], \
                    "Original document should be excluded"
            print("  ✓ Original document correctly excluded")
            
            print("\n✅ All recommendation tests passed!")

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_recommend())
