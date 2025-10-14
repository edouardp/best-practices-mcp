#!/usr/bin/env python3
import subprocess
import json
import sys
import shutil

def get_container_cmd():
    if shutil.which("docker"):
        return "docker"
    elif shutil.which("podman"):
        return "podman"
    else:
        print("Error: Neither docker nor podman found")
        sys.exit(1)

def read_docs(documentation_path, start_line, end_line):
    container_cmd = get_container_cmd()
    
    process = subprocess.Popen(
        [container_cmd, "run", "-i", "sdlc-mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "python-read-client", "version": "1.0"}
            }
        }
        
        initialized_msg = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        read_msg = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "pqsoft_read_docs",
                "arguments": {
                    "documentation_path": documentation_path,
                    "start_line": start_line,
                    "end_line": end_line
                }
            }
        }
        
        messages = [init_msg, initialized_msg, read_msg]
        for msg in messages:
            json_str = json.dumps(msg) + "\n"
            process.stdin.write(json_str)
        process.stdin.close()
        
        responses = []
        for line in process.stdout:
            line = line.strip()
            if line and line.startswith('{'):
                try:
                    responses.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        
        for response in responses:
            if response.get('id') == 2:
                if 'result' in response:
                    content = response['result'].get('content', [])
                    if content and 'text' in content[0]:
                        # pqsoft_read_docs returns a string, not JSON
                        return content[0]['text']
                    else:
                        return "No content in response"
                elif 'error' in response:
                    return f"Error: {response['error']['message']}"
        
        return "No read response received"
        
    finally:
        process.terminate()
        process.wait()

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 test_read.py <file_path> <start_line> <end_line>")
        print("Example: python3 test_read.py '04-testing-strategies.md' 1 50")
        sys.exit(1)
    
    file_path = sys.argv[1]
    start_line = int(sys.argv[2])
    end_line = int(sys.argv[3])
    
    result = read_docs(file_path, start_line, end_line)
    
    print(f"Content from {file_path} (lines {start_line}-{end_line}):")
    print("=" * 60)
    print(result)
