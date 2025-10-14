#!/usr/bin/env python3
import subprocess
import json
import time
import sys
import shutil

def get_container_cmd():
    """Detect available container runtime."""
    if shutil.which("docker"):
        return "docker"
    elif shutil.which("podman"):
        return "podman"
    else:
        print("Error: Neither docker nor podman found")
        sys.exit(1)

def run_command(cmd, capture_output=True):
    """Run shell command and return result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout

def test_mcp_server():
    """Test the MCP server functionality."""
    container_cmd = get_container_cmd()
    print(f"=== Using {container_cmd} ===")
    
    print("=== Building image ===")
    print("Building container image (this may take a few minutes)...")
    build_result = subprocess.run(f"{container_cmd} build -t sdlc-mcp .", shell=True, capture_output=True, text=True)
    if build_result.returncode != 0:
        print(f"Build failed: {build_result.stderr}")
        return False
    print("✓ Build successful")
    
    print("\n=== Testing MCP server ===")
    
    # Start container
    print("Starting MCP server container...")
    process = subprocess.Popen(
        [container_cmd, "run", "-i", "sdlc-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    def send_message(msg, test_name):
        print(f"Sending {test_name} message...")
        json_msg = json.dumps(msg) + "\n"
        process.stdin.write(json_msg)
        process.stdin.flush()
        print(f"Waiting for {test_name} response...")
        response_line = process.stdout.readline()
        if response_line:
            print(f"Received {test_name} response")
            return json.loads(response_line)
        else:
            print(f"No response for {test_name}")
            return None
    
    try:
        # 1. Initialize
        print("\n1. Testing initialize...")
        init_msg = {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}}
        }
        response = send_message(init_msg, "initialize")
        if response and 'result' in response:
            print("✓ Initialize successful")
        else:
            print("✗ Initialize failed")
            return False
        
        # 2. Test search_documentation
        print("\n2. Testing search_documentation...")
        search_msg = {
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": "search_documentation", "arguments": {"search_phrase": "code review", "limit": 3}}
        }
        response = send_message(search_msg, "search")
        if response and 'result' in response:
            content = response['result'].get('content', [])
            if content and content[0].get('text'):
                results = json.loads(content[0]['text'])
                print(f"✓ Search returned {len(results)} results")
                if results:
                    print(f"  Top result: {results[0].get('title', 'N/A')}")
            else:
                print("✗ Search returned no content")
                return False
        else:
            print("✗ Search failed")
            return False
        
        # 3. Test read_documentation
        print("\n3. Testing read_documentation...")
        read_msg = {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "read_documentation", "arguments": {"title": "Code Review", "max_length": 500}}
        }
        response = send_message(read_msg, "read")
        if response and 'result' in response:
            content = response['result'].get('content', [])
            if content and content[0].get('text'):
                doc_content = json.loads(content[0]['text'])
                print(f"✓ Read returned {len(doc_content)} characters")
            else:
                print("✗ Read returned no content")
                return False
        else:
            print("✗ Read failed")
            return False
        
        # 4. Test recommend
        print("\n4. Testing recommend...")
        rec_msg = {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": "recommend", "arguments": {"title": "Testing"}}
        }
        response = send_message(rec_msg, "recommend")
        if response and 'result' in response:
            content = response['result'].get('content', [])
            if content and content[0].get('text'):
                recommendations = json.loads(content[0]['text'])
                print(f"✓ Recommend returned {len(recommendations)} recommendations")
                if recommendations:
                    print(f"  Top recommendation: {recommendations[0].get('title', 'N/A')}")
            else:
                print("✗ Recommend returned no content")
                return False
        else:
            print("✗ Recommend failed")
            return False
    
    except Exception as e:
        print(f"✗ Test error: {e}")
        return False
    finally:
        print("Terminating container...")
        process.terminate()
        process.wait()
    
    print("\n=== All MCP tools tested successfully! ===")
    return True

if __name__ == "__main__":
    success = test_mcp_server()
    sys.exit(0 if success else 1)
