#!/usr/bin/env python3
"""
MCP Search Client

A Python client that demonstrates proper MCP protocol communication
for searching SDLC documentation.

Why this exists:
- Shows correct MCP protocol handshake (initialize + initialized)
- Provides command-line interface for testing
- Demonstrates how to parse MCP responses
- Useful for debugging and validation

Protocol flow:
1. Send initialize request with client info
2. Send initialized notification (required by spec)
3. Send tool call request
4. Parse JSON-RPC responses
"""

import subprocess
import json
import sys
import shutil
from typing import Optional, List, Dict, Any


def get_container_cmd() -> str:
    """
    Detect available container runtime (Docker or Podman).
    
    Why auto-detect:
    - Works on different systems without configuration
    - Podman is drop-in Docker replacement
    - Fails gracefully if neither is available
    
    Returns:
        "docker" or "podman"
        
    Raises:
        SystemExit if neither is found
    """
    if shutil.which("docker"):
        return "docker"
    elif shutil.which("podman"):
        return "podman"
    else:
        print("Error: Neither docker nor podman found", file=sys.stderr)
        sys.exit(1)


def search_docs(search_term: str, limit: int = 5) -> Any:
    """
    Search documentation using MCP protocol.
    
    MCP Protocol Implementation:
    1. initialize: Establishes protocol version and capabilities
    2. initialized: Notification that client is ready (no response expected)
    3. tools/call: Invokes the pqsoft_search_docs tool
    
    Why stdio transport:
    - Standard MCP transport mechanism
    - Works with containerized servers
    - Simple pipe-based communication
    
    Args:
        search_term: Natural language search query
        limit: Maximum number of results
    
    Returns:
        Search results as list of dicts, or error dict
        
    Error handling:
    - Returns error dict rather than raising exceptions
    - Allows caller to handle errors gracefully
    """
    container_cmd = get_container_cmd()
    
    # Start container with stdio pipes
    # Why -i flag: Interactive mode, keeps stdin open
    # Why text=True: Handle strings instead of bytes
    process = subprocess.Popen(
        [container_cmd, "run", "-i", "best-practices-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Build MCP messages
        # Why separate messages: MCP protocol requires specific sequence
        
        # 1. Initialize request
        # Why clientInfo: Required by MCP spec, identifies this client
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "python-search-client", "version": "1.0"}
            }
        }
        
        # 2. Initialized notification
        # Why no id: Notifications don't expect responses
        # Why required: MCP spec requires this after initialize
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        # 3. Tool call request
        # Why id=2: Must be unique, different from initialize
        search_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "pqsoft_search_docs",
                "arguments": {
                    "search_phrase": search_term,
                    "limit": limit
                }
            }
        }
        
        # Send all messages
        # Why send all at once: Reduces round trips, server buffers input
        messages = [init_msg, initialized_msg, search_msg]
        for msg in messages:
            json_str = json.dumps(msg) + "\n"
            process.stdin.write(json_str)
        
        # Close stdin to signal we're done sending
        # Why close: Tells server no more input coming
        process.stdin.close()
        
        # Read all responses
        # Why read all: Server may send multiple responses
        responses = []
        for line in process.stdout:
            line = line.strip()
            if line and line.startswith('{'):
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    # Skip malformed lines (shouldn't happen)
                    continue
        
        # Find search response (id=2)
        # Why check id: Multiple responses, need to find the right one
        for response in responses:
            if response.get('id') == 2:
                if 'result' in response:
                    # Extract tool result from MCP response structure
                    # MCP wraps tool results in content array
                    content = response['result'].get('content', [])
                    if content and 'text' in content[0]:
                        # Tool returns JSON string, parse it
                        results = json.loads(content[0]['text'])
                        return results
                    else:
                        return {"error": "No content in response"}
                elif 'error' in response:
                    return {"error": response['error']['message']}
        
        return {"error": "No search response received"}
        
    finally:
        # Always clean up process
        # Why terminate: Ensures container stops even on error
        process.terminate()
        process.wait()


def format_results(results: Any, search_term: str) -> None:
    """
    Format and display search results in human-readable form.
    
    Why separate formatting:
    - Separates data retrieval from presentation
    - Makes it easy to change output format
    - Could be extended to support JSON output
    
    Args:
        results: Search results from search_docs()
        search_term: Original search query (for display)
    """
    print(f"Search results for: '{search_term}'")
    print("=" * 50)
    
    # Handle error responses
    if isinstance(results, dict) and 'error' in results:
        print(f"❌ Error: {results['error']}")
        return
    
    # Handle empty results
    if not results:
        print("No results found")
        return
    
    # Display each result
    # Why enumerate: Provides user-friendly numbering
    for i, result in enumerate(results, 1):
        title = result.get('title', 'Unknown')
        filename = result.get('filename', 'Unknown')
        start_line = result.get('start_line', 0)
        end_line = result.get('end_line', 0)
        similarity = result.get('similarity', 0)
        content = result.get('content', 'No content')
        
        # Format output
        # Why show file location: Enables user to read full content
        # Why show similarity: Indicates confidence/relevance
        print(f"\n{i}. {title}")
        print(f"   File: {filename} (lines {start_line}-{end_line})")
        print(f"   Similarity: {similarity:.3f}")
        print(f"   Content: {content[:150]}{'...' if len(content) > 150 else ''}")


if __name__ == "__main__":
    # Command-line interface
    # Why argparse not used: Simple single-argument script
    if len(sys.argv) != 2:
        print("Usage: python3 mcp_search.py <search_term>")
        print("Example: python3 mcp_search.py 'testing'")
        sys.exit(1)
    
    search_term = sys.argv[1]
    results = search_docs(search_term)
    format_results(results, search_term)
