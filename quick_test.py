#!/usr/bin/env python3
import subprocess
import json
import shutil
import sys
import time

def get_container_cmd():
    if shutil.which("docker"):
        return "docker"
    elif shutil.which("podman"):
        return "podman"
    else:
        print("Error: Neither docker nor podman found")
        sys.exit(1)

def quick_test():
    container_cmd = get_container_cmd()
    print(f"Using {container_cmd}")
    
    # Quick test - just send one message
    print("Starting container for quick test...")
    
    try:
        # Start container with timeout
        process = subprocess.Popen(
            [container_cmd, "run", "-i", "sdlc-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("Sending initialize message...")
        init_msg = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}}}
        
        json_msg = json.dumps(init_msg) + "\n"
        process.stdin.write(json_msg)
        process.stdin.flush()
        
        print("Waiting for response (5 second timeout)...")
        
        # Wait for response with timeout
        import select
        ready, _, _ = select.select([process.stdout], [], [], 5.0)
        
        if ready:
            response_line = process.stdout.readline()
            if response_line:
                response = json.loads(response_line)
                print(f"✓ Got response: {response.get('id')}")
                return True
            else:
                print("✗ Empty response")
        else:
            print("✗ Timeout waiting for response")
            
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        try:
            process.terminate()
            process.wait(timeout=2)
        except:
            process.kill()
    
    return False

if __name__ == "__main__":
    success = quick_test()
    sys.exit(0 if success else 1)
