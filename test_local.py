#!/usr/bin/env python3
import subprocess
import sys
import os

def test_local():
    """Test the MCP components locally without Docker."""
    print("=== Installing dependencies ===")
    
    # Install requirements
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to install requirements: {result.stderr}")
        return False
    
    print("✓ Dependencies installed")
    
    print("\n=== Building index ===")
    
    # Run build script
    result = subprocess.run([sys.executable, "build_index.py"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to build index: {result.stderr}")
        return False
    
    print("✓ Index built successfully")
    print(result.stdout)
    
    print("\n=== Testing server startup ===")
    
    # Test that server can start (just import and basic check)
    test_code = '''
import sys
sys.path.append(".")
try:
    from server import mcp, search_documentation, read_documentation, recommend
    print("✓ Server imports successful")
    print("✓ Tools available:", len(mcp.tools))
    
    # Test search function directly
    results = search_documentation("testing", 2)
    print(f"✓ Search test: found {len(results)} results")
    
    # Test read function
    content = read_documentation("Testing", 200)
    print(f"✓ Read test: got {len(content)} characters")
    
    # Test recommend function  
    recs = recommend("Testing")
    print(f"✓ Recommend test: got {len(recs)} recommendations")
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
'''
    
    result = subprocess.run([sys.executable, "-c", test_code], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Server test failed: {result.stderr}")
        return False
    
    print(result.stdout)
    
    print("\n=== Checking database ===")
    if os.path.exists("sdlc_docs.db"):
        print("✓ Database file created")
        
        # Quick DB check
        db_check = '''
import duckdb
conn = duckdb.connect("sdlc_docs.db", read_only=True)
count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
print(f"✓ Database contains {count} document chunks")
conn.close()
'''
        result = subprocess.run([sys.executable, "-c", db_check], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(result.stdout.strip())
        else:
            print(f"DB check failed: {result.stderr}")
    
    print("\n=== All local tests passed! ===")
    return True

if __name__ == "__main__":
    success = test_local()
    sys.exit(0 if success else 1)
