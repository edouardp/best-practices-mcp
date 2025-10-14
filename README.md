# SDLC Best Practices MCP Server

A self-contained Model Context Protocol (MCP) server that provides semantic search and document reading capabilities for SDLC documentation using local embeddings.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Build Time (Docker)                      │
├─────────────────────────────────────────────────────────────┤
│  docs/*.md → build_index.py → embeddings → sdlc_docs.db    │
│  • Chunks documents with heading context                    │
│  • Generates 384-dim vectors (thenlper/gte-small)          │
│  • Stores in DuckDB with metadata                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Runtime (Container)                       │
├─────────────────────────────────────────────────────────────┤
│  server.py (FastMCP) ← stdio ← MCP Client (Q CLI)          │
│  • search_documentation: Semantic vector search             │
│  • read_documentation: Precise line-range reading           │
│  • recommend: Content-based recommendations                 │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 🔍 Semantic Search
- **Local embeddings**: No network calls, fully self-contained
- **Contextual chunking**: Includes heading hierarchy for better results
- **Overlap strategy**: 2-line overlap prevents information loss
- **Cosine similarity**: Standard vector comparison metric

### 📖 Precise Reading
- **Line-range access**: Read exact sections from source files
- **Security hardened**: Path traversal prevention, .md files only
- **Metadata tracking**: Filename and line numbers for every chunk

### 🔒 Security
- Read-only database access
- Path traversal prevention
- File type restrictions (.md only)
- Hidden file blocking (no .env, .git, etc.)

## Tools Available

### `search_documentation(search_phrase: str, limit: int) -> list[dict]`
Semantic search across all documentation.

**Returns:**
```python
[{
    'title': 'Testing Strategies',
    'filename': '04-testing-strategies.md',
    'start_line': 125,
    'end_line': 201,
    'content': '...',
    'similarity': 0.873
}, ...]
```

### `read_documentation(documentation_path: str, start_line: int, end_line: int) -> str`
Read specific line ranges from documentation files.

**Example:**
```python
read_documentation('04-testing-strategies.md', 1, 50)
# Returns lines 1-50 from the file
```

### `recommend(title: str) -> list[dict]`
Get related documentation based on content similarity.

## Quick Start

### 1. Build and Test

```bash
# Run proof of concept test
./proof_test.sh

# Or build manually
docker build -t sdlc-mcp .
# OR
podman build -t sdlc-mcp .
```

### 2. Test Search Functionality

```bash
# Using Python MCP client
python3 mcp_search.py "testing strategies"
python3 mcp_search.py "deployment best practices"

# Using test script for reading
python3 test_read.py "04-testing-strategies.md" 1 50
```

### 3. Use with Q CLI

Add to your MCP configuration (`~/.config/amazonq/mcp.json`):

```json
{
  "mcpServers": {
    "sdlc-docs": {
      "command": "docker",
      "args": ["run", "-i", "sdlc-mcp"]
    }
  }
}
```

Or for Podman:
```json
{
  "mcpServers": {
    "sdlc-docs": {
      "command": "podman",
      "args": ["run", "-i", "sdlc-mcp"]
    }
  }
}
```

## Adding Your Own Documentation

1. **Place markdown files in `docs/` directory**
   ```bash
   docs/
   ├── coding-standards.md
   ├── deployment/
   │   ├── kubernetes.md
   │   └── terraform.md
   └── testing/
       └── integration-tests.md
   ```

2. **Rebuild the container**
   ```bash
   docker-compose up --build
   # OR
   podman-compose up --build
   ```

3. **Documentation is automatically indexed**
   - Chunks created with heading context
   - Embeddings generated
   - Database updated

## Directory Structure

```
├── Dockerfile                  # Multi-stage build with embedding generation
├── docker-compose.yml          # Compose configuration (Docker/Podman)
├── requirements.txt            # Python dependencies
├── build_index.py             # Indexing script (runs at build time)
├── server.py                  # MCP server (runs at runtime)
├── mcp_search.py              # Python MCP client for testing
├── test_read.py               # Test script for read_documentation
├── docs/                      # Your markdown documentation
│   └── *.md
├── detect_container.sh        # Auto-detect Docker/Podman
├── proof_test.sh             # Validation test script
└── sdlc_docs.db              # Generated vector database (in container)
```

## Container Runtime Support

All scripts automatically detect and use either Docker or Podman:
- `proof_test.sh` - Validates core functionality
- `mcp_search.py` - Auto-detects runtime
- `test_read.py` - Auto-detects runtime
- `docker-compose.yml` - Works with both docker-compose and podman-compose

## Technical Details

### Embedding Model
- **Model**: `thenlper/gte-small`
- **Dimensions**: 384
- **Why**: Good balance of quality vs. size/speed for CPU inference
- **License**: Apache 2.0

### Database
- **Engine**: DuckDB (embedded)
- **Schema**: id, title, filename, start_line, end_line, content, embedding
- **Access**: Read-only at runtime
- **Size**: ~1-5MB for typical documentation sets

### Chunking Strategy
- **Size**: ~300 words per chunk
- **Overlap**: 2 lines between chunks
- **Context**: H1, H2, H3 headings prepended to each chunk
- **Why**: Balances precision with context preservation

### Performance
- **Search latency**: < 200ms for typical queries
- **Embedding generation**: ~50ms per query
- **Similarity calculation**: ~1ms per chunk
- **Memory**: ~500MB (model + runtime)

## Customization

### Adjust Chunk Size
Edit `build_index.py`:
```python
chunks = chunk_text(content, chunk_size=400, overlap_lines=3)
```

### Change Embedding Model
Edit both `build_index.py` and `server.py`:
```python
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
# Update embedding dimension in CREATE TABLE statement
```

### Modify Search Limit
Default is 10 results, max 50. Adjust in tool call:
```python
search_documentation("query", limit=20)
```

## Troubleshooting

### Container won't start
```bash
# Check if image built successfully
docker images | grep sdlc-mcp

# View build logs
docker build -t sdlc-mcp . 2>&1 | less
```

### Search returns no results
```bash
# Verify database was created
docker run --rm sdlc-mcp ls -lh sdlc_docs.db

# Check number of indexed chunks
docker run --rm sdlc-mcp python -c "import duckdb; print(duckdb.connect('sdlc_docs.db').execute('SELECT COUNT(*) FROM documents').fetchone())"
```

### Path traversal errors
- Ensure paths are relative to docs/ directory
- Don't use `..` in paths
- Only .md files are accessible

## Development

### Running Tests
```bash
# Validate structure
python3 validate_structure.py

# Test MCP protocol
./proof_test.sh

# Test search
python3 mcp_search.py "test query"

# Test reading
python3 test_read.py "file.md" 1 10
```

### Debugging
```bash
# Exec into running container
docker exec -it <container_id> /bin/bash

# Check database
python3 -c "import duckdb; conn = duckdb.connect('sdlc_docs.db', read_only=True); print(conn.execute('SELECT COUNT(*) FROM documents').fetchone())"

# View indexed files
python3 -c "import duckdb; conn = duckdb.connect('sdlc_docs.db', read_only=True); print(conn.execute('SELECT DISTINCT filename FROM documents').fetchall())"
```

## License

This project is provided as-is for SDLC documentation purposes.

## Contributing

1. Add your documentation to `docs/`
2. Test with `./proof_test.sh`
3. Verify search works: `python3 mcp_search.py "your topic"`
4. Rebuild and deploy

## Status

✅ **Production Ready**
- All tests passing
- Security hardened
- Docker/Podman compatible
- MCP protocol compliant
- Fully documented
