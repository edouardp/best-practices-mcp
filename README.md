# SDLC Best Practices MCP Servers

Two Model Context Protocol (MCP) servers providing search and document reading capabilities for SDLC documentation:

1. **Local MCP Server** (`src_mcp/`) - Self-contained with local embeddings and reranking
2. **AWS Knowledge Base MCP Server** (`aws_kb/`) - Cloud-native using AWS Bedrock and S3 Vectors

## Quick Start

### Local MCP Server (Recommended for Development)
```bash
./run-local-mcp.sh
```
- ✅ Zero cost, runs locally
- ✅ Fast (<200ms queries)
- ✅ No AWS account needed
- ✅ Hybrid search with reranking

### AWS Knowledge Base MCP Server (Production)
```bash
./run-awskb-mcp.sh
```
- ✅ Scalable, managed infrastructure
- ✅ S3 Vectors (90% cost reduction)
- ✅ Auto-syncs docs when changed
- ⚠️ Requires AWS account (~$0.10-0.20/month)

## Architecture Comparison

### Local MCP Server (`src_mcp/`)

```
┌─────────────────────────────────────────────────────────────┐
│                     Build Time                              │
├─────────────────────────────────────────────────────────────┤
│  docs/*.md → build_index.py → sdlc_docs.db                  │
│  • Chunks documents with heading context                    │
│  • Generates 768-dim vectors (all-mpnet-base-v2)            │
│  • Creates BM25 full-text search index                      │
│  • Stores in DuckDB with metadata                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Runtime (Query)                          │
├─────────────────────────────────────────────────────────────┤
│  Query → Hybrid Retrieval → Reranker → Results              │
│                                                             │
│  Stage 1: Parallel Retrieval                                │
│    • BM25 search (exact keywords) → top 30                  │
│    • Vector search (semantic) → top 30                      │
│                                                             │
│  Stage 2: Union + Deduplicate                               │
│    • Merge results by chunk ID                              │
│                                                             │
│  Stage 3: Cross-Encoder Reranking                           │
│    • ms-marco-MiniLM-L-6-v2 scores (query, doc) pairs       │
│    • Return top K by relevance                              │
└─────────────────────────────────────────────────────────────┘
```

### AWS Knowledge Base MCP Server (`aws_kb/`)

```
┌─────────────────────────────────────────────────────────────┐
│                   Infrastructure                            │
├─────────────────────────────────────────────────────────────┤
│  docs/*.md → S3 Bucket → Knowledge Base                     │
│  • Titan Embeddings v2 (1024-dim)                           │
│  • S3 Vectors for storage                                   │
│  • Fixed-size chunking (200 tokens)                         │
│  • Auto-ingestion on sync                                   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Runtime (Query)                          │
├─────────────────────────────────────────────────────────────┤
│  Query → Knowledge Base Retrieve API → Results              │
│  • Vector search with cosine similarity                     │
│  • Reranking not available in ap-southeast-2                │
│  • Documents read directly from S3                          │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 🔍 Hybrid Search (Local) / Vector Search (AWS)
- **Local**: BM25 + Vector + Cross-encoder reranking
- **AWS**: Vector search with Titan Embeddings
- **Both**: Semantic similarity for natural language queries

### 📖 Precise Reading
- **Line-range access**: Read exact sections from source files
- **Security hardened**: Path traversal prevention, .md files only
- **Metadata tracking**: Filename and line numbers for every chunk

### 🔒 Security
- Read-only database/S3 access
- Path traversal prevention
- File type restrictions (.md only)
- Hidden file blocking (no .env, .git, etc.)

## Tools Available

### `pqsoft_search_docs(search_phrase: str, limit: int) -> list[dict]`
Hybrid search across all documentation using BM25 + vectors + reranking.

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

### `pqsoft_read_docs(documentation_path: str, start_line: int, end_line: int) -> str`
Read specific line ranges from documentation files.

**Example:**
```python
pqsoft_read_docs('04-testing-strategies.md', 1, 50)
# Returns lines 1-50 from the file
```

### `pqsoft_recommend_docs(title: str) -> list[dict]`
Get related documentation based on content similarity.

## Development & Testing

### Local MCP Server

```bash
# Run the server
./run-local-mcp.sh

# Test search
cd src_mcp
python3 mcp_search.py "testing strategies"
```

### AWS Knowledge Base MCP Server

```bash
# Deploy infrastructure (one-time setup)
cd aws_kb/scripts
./deploy_stack.sh

# Create vector bucket and index (one-time setup)
uv run create_vector_bucket.py
uv run create_vector_index.py

# Sync documents and run server
cd ../..
./run-awskb-mcp.sh
```

See `aws_kb/README.md` and `aws_kb/QUICKSTART.md` for detailed AWS setup instructions.

### 2. Test Search Functionality

```bash
# Local MCP
cd src_mcp
python3 mcp_search.py "testing strategies"
python3 mcp_search.py "deployment best practices"

# Using test script for reading
python3 test_read.py "04-testing-strategies.md" 1 50
```

### 3. Use with Q CLI

Add to your MCP configuration (`~/.aws/amazonq/mcp.json`):

**Local MCP Server:**
```json
{
  "mcpServers": {
    "sdlc-docs-local": {
      "command": "/absolute/path/to/best-practices-mcp/run-local-mcp.sh"
    }
  }
}
```

**AWS Knowledge Base MCP Server:**
```json
{
  "mcpServers": {
    "sdlc-docs-aws": {
      "command": "/absolute/path/to/best-practices-mcp/run-awskb-mcp.sh",
      "env": {
        "AWS_PROFILE": "your-profile-name"
      }
    }
  }
}
```

Replace `/absolute/path/to/best-practices-mcp/` with your actual project path.

## Local Development

### Prerequisites

Install [uv](https://docs.astral.sh/uv/):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Running Locally

**Local MCP Server:**
```bash
./run-local-mcp.sh
```

The script automatically:
- Installs dependencies via `uv sync`
- Builds/rebuilds the index if `docs/` files are newer than `sdlc_docs.db`
- Starts the MCP server

**AWS Knowledge Base MCP Server:**
```bash
./run-awskb-mcp.sh
```

The script automatically:
- Installs dependencies via `uv sync`
- Syncs docs to S3 if changed
- Starts the MCP server

**Note:** Both servers automatically rebuild/resync when documentation files change, ensuring search results stay current.

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

2. **Restart the MCP server**
   - Local: `./run-local-mcp.sh` (auto-rebuilds index)
   - AWS: `./run-awskb-mcp.sh` (auto-syncs to S3)

3. **Documentation is automatically indexed**
   - Chunks created with heading context
   - Embeddings generated
   - Database/Knowledge Base updated

## Directory Structure

```
├── run-local-mcp.sh           # Start local MCP server
├── run-awskb-mcp.sh           # Start AWS KB MCP server
├── src_mcp/                   # Local MCP implementation
│   ├── server.py              # FastMCP server
│   ├── build_index.py         # Index builder
│   ├── pyproject.toml         # Dependencies
│   └── sdlc_docs.db           # Vector database (generated)
├── aws_kb/                    # AWS Knowledge Base implementation
│   ├── server.py              # FastMCP server
│   ├── cloudformation/        # Infrastructure as code
│   ├── scripts/               # Deployment and sync scripts
│   ├── tests/                 # Test scripts
│   ├── README.md              # Detailed AWS setup guide
│   ├── QUICKSTART.md          # Quick start guide
│   ├── IMPLEMENTATION.md      # Implementation details
│   └── CODE_REVIEW.md         # Code review and improvements
├── docs/                      # Your markdown documentation
│   └── *.md
└── README.md                  # This file
```

## Technical Details

### Local MCP Server
- **Embedding Model**: sentence-transformers/all-mpnet-base-v2 (768-dim)
- **Database**: DuckDB (embedded, read-only at runtime)
- **Search**: BM25 + Vector + Cross-encoder reranking
- **Size**: ~1-5MB database for typical documentation sets

### AWS Knowledge Base MCP Server
- **Embedding Model**: Amazon Titan Embeddings v2 (1024-dim)
- **Vector Store**: S3 Vectors (90% cost reduction vs traditional DBs)
- **Search**: Vector search with cosine similarity
- **Infrastructure**: CloudFormation-managed, fully serverless

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
pqsoft_search_docs("query", limit=20)
```

## Troubleshooting

### Container won't start
```bash
# Check if image built successfully
docker images | grep best-practices-mcp

# View build logs
docker build -t best-practices-mcp . 2>&1 | less
```

### Search returns no results
```bash
# Verify database was created
docker run --rm best-practices-mcp ls -lh sdlc_docs.db

# Check number of indexed chunks
docker run --rm best-practices-mcp python -c "import duckdb; print(duckdb.connect('sdlc_docs.db', read_only=True).execute('SELECT COUNT(*) FROM documents').fetchone())"
```

### Path traversal errors
- Ensure paths are relative to docs/ directory
- Don't use `..` in paths
## Customization

### Adjust Chunk Size
Edit `src_mcp/build_index.py`:
```python
chunks = chunk_text(content, chunk_size=400, overlap_lines=3)
```

### Change Embedding Model
Edit both `src_mcp/build_index.py` and `src_mcp/server.py`:
```python
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
# Update embedding dimension in CREATE TABLE statement
```

### Modify Search Limit
Default is 10 results, max 50. Adjust in tool call:
```python
pqsoft_search_docs("query", limit=20)
```

## Troubleshooting

### Local MCP Server
```bash
# Check if database exists
ls -lh src_mcp/sdlc_docs.db

# Rebuild index
cd src_mcp && uv run python build_index.py

# Check indexed documents
cd src_mcp && python3 -c "import duckdb; conn = duckdb.connect('sdlc_docs.db', read_only=True); print(conn.execute('SELECT DISTINCT filename FROM documents').fetchall())"
```

### AWS Knowledge Base MCP Server
```bash
# Check config
cat aws_kb/config.json

# Manually sync docs
cd aws_kb && uv run python scripts/sync_docs.py

# Check ingestion status
aws bedrock-agent list-ingestion-jobs --knowledge-base-id <KB_ID> --data-source-id <DS_ID> --region ap-southeast-2
```

See `aws_kb/README.md` for detailed AWS troubleshooting.

## Comparison: Local vs AWS

| Feature      | Local (src_mcp)               | AWS (aws_kb)                    |
| ------------ | ----------------------------- | ------------------------------- |
| Cost         | $0                            | ~$0.10-0.20/month               |
| Setup        | 2 min                         | 10 min                          |
| Latency      | <200ms                        | ~500ms                          |
| Scalability  | Limited                       | Unlimited                       |
| Maintenance  | Manual rebuild                | Automatic                       |
| Dependencies | sentence-transformers, DuckDB | boto3 only                      |
| Vector Store | DuckDB                        | S3 Vectors                      |
| Embeddings   | all-mpnet-base-v2             | Titan                           |
| Reranking    | ms-marco-MiniLM               | Not available in ap-southeast-2 |

## License

This project is provided as-is for SDLC documentation purposes.

## Contributing

1. Add your documentation to `docs/`
2. Test with local server: `./run-local-mcp.sh`
3. Verify search works
4. Commit and push

## Status

✅ **Production Ready**
- All tests passing
- Security hardened
- Two deployment options
- MCP protocol compliant
- Fully documented
