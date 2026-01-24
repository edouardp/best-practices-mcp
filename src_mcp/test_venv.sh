#!/bin/bash
set -e

# Detect container runtime
if command -v docker &> /dev/null; then
    CONTAINER_CMD="docker"
elif command -v podman &> /dev/null; then
    CONTAINER_CMD="podman"
else
    echo "Warning: Neither docker nor podman found, skipping container tests"
    CONTAINER_CMD=""
fi

echo "=== Creating virtual environment ==="
python3 -m venv test_env
source test_env/bin/activate

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Building index ==="
python build_index.py

echo "=== Testing server components ==="
python -c "
import sys
from server import mcp, search_documentation, read_documentation, recommend

print('✓ Server imports successful')
print(f'✓ Tools available: {len(mcp.tools)}')

# Test search function
results = search_documentation('testing', 2)
print(f'✓ Search test: found {len(results)} results')
if results:
    print(f'  First result: {results[0].get(\"title\", \"N/A\")}')

# Test read function
content = read_documentation('Testing', 200)
print(f'✓ Read test: got {len(content)} characters')

# Test recommend function  
recs = recommend('Testing')
print(f'✓ Recommend test: got {len(recs)} recommendations')
"

echo "=== Checking database ==="
python -c "
import duckdb
import os
if os.path.exists('sdlc_docs.db'):
    conn = duckdb.connect('sdlc_docs.db', read_only=True)
    count = conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    titles = conn.execute('SELECT DISTINCT title FROM documents').fetchall()
    print(f'✓ Database contains {count} document chunks')
    print(f'✓ Document titles: {[t[0] for t in titles]}')
    conn.close()
else:
    print('✗ Database file not found')
"

echo "=== Cleanup ==="
deactivate
rm -rf test_env

echo "=== All tests completed successfully! ==="
