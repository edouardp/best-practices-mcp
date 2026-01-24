#!/usr/bin/env python3
"""Test pqsoft_read_docs tool"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_read():
    server_params = StdioServerParameters(
        command="python3",
        args=[str(Path(__file__).parent.parent / "server.py")]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test 1: Read first 10 lines
            print("Test 1: Read first 10 lines of a document")
            result = await session.call_tool("pqsoft_read_docs", {
                "documentation_path": "01-coding-standards.md",
                "start_line": 1,
                "end_line": 10
            })
            lines = result.content.split('\n')
            print(f"  Read {len(lines)} lines")
            assert len(lines) == 10, "Should read exactly 10 lines"
            
            # Test 2: Read middle section
            print("Test 2: Read middle section (lines 20-30)")
            result = await session.call_tool("pqsoft_read_docs", {
                "documentation_path": "01-coding-standards.md",
                "start_line": 20,
                "end_line": 30
            })
            lines = result.content.split('\n')
            print(f"  Read {len(lines)} lines")
            assert len(lines) == 11, "Should read 11 lines (20-30 inclusive)"
            
            # Test 3: Security - reject path traversal
            print("Test 3: Security - reject path traversal")
            try:
                await session.call_tool("pqsoft_read_docs", {
                    "documentation_path": "../secrets.md",
                    "start_line": 1,
                    "end_line": 10
                })
                assert False, "Should reject path traversal"
            except Exception as e:
                print(f"  ✓ Correctly rejected: {e}")
            
            # Test 4: Security - reject non-md files
            print("Test 4: Security - reject non-md files")
            try:
                await session.call_tool("pqsoft_read_docs", {
                    "documentation_path": "config.json",
                    "start_line": 1,
                    "end_line": 10
                })
                assert False, "Should reject non-md files"
            except Exception as e:
                print(f"  ✓ Correctly rejected: {e}")
            
            print("\n✅ All read tests passed!")

if __name__ == '__main__':
    import asyncio
    asyncio.run(test_read())
