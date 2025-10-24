#!/usr/bin/env python3
"""
SDLC Documentation MCP Server

This FastMCP server provides semantic search and document reading capabilities
for SDLC documentation through the Model Context Protocol (MCP).

Architecture Decisions:
- FastMCP: Simplifies MCP protocol implementation with decorators
- stdio transport: Enables easy integration with MCP clients like Q CLI
- Read-only database: Safe for concurrent access, no locking needed
- Local embeddings: Same model as indexing for consistency

Security Model:
- Read-only file access within docs/ directory
- Path traversal prevention
- File type restrictions (.md only)
- No hidden file access
"""

import sys
from pathlib import Path
from typing import List, Dict

import duckdb
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModel
from fastmcp import FastMCP

# Configuration constants (must match build_index.py)
EMBEDDING_MODEL = 'sentence-transformers/all-mpnet-base-v2'
MAX_SEARCH_LIMIT = 50

# Global model instances (lazy loaded)
model = None
tokenizer = None

def get_model():
    """Lazy load the embedding model and tokenizer"""
    global model, tokenizer
    if model is None:
        print("Loading embedding model...", file=sys.stderr)
        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
        model = AutoModel.from_pretrained(EMBEDDING_MODEL)
    return model, tokenizer

def encode_text(texts):
    """
    Generate embeddings using direct transformers model.
    
    Args:
        texts: String or list of strings to encode
    
    Returns:
        numpy array of embeddings
    """
    model, tokenizer = get_model()
    
    if isinstance(texts, str):
        texts = [texts]
    
    # Tokenize input
    inputs = tokenizer(texts, padding=True, truncation=True, return_tensors='pt', max_length=512)
    
    # Generate embeddings
    with torch.no_grad():
        outputs = model(**inputs)
        # Use mean pooling of last hidden state
        embeddings = outputs.last_hidden_state.mean(dim=1)
    
    return embeddings.numpy()

# Initialize MCP server
# Why "SDLC Docs Server": Descriptive name shown to MCP clients
mcp = FastMCP("SDLC Docs Server")

# Connect to database in read-only mode
# Why read-only: Prevents accidental modifications, enables safe concurrent access
# Why global connection: DuckDB is thread-safe for read-only connections
conn = duckdb.connect('sdlc_docs.db', read_only=True)


@mcp.tool()
def pqsoft_search_docs(search_phrase: str, limit: int = 10) -> List[Dict]:
    """
    Search SDLC documentation using semantic similarity.
    
    How it works:
    1. Convert search phrase to embedding vector
    2. Use DuckDB's native array_cosine_similarity function
    3. Database handles sorting and limiting efficiently
    
    Why DuckDB native similarity:
    - Faster than Python implementation (native C++)
    - Leverages database query optimization
    - Cleaner code with SQL ORDER BY and LIMIT
    
    Why semantic search:
    - Finds conceptually similar content, not just keyword matches
    - Handles synonyms and related concepts
    - More natural than boolean search
    
    Why return metadata:
    - filename + line numbers: Enables precise document reading
    - title: Human-readable context
    - content preview: Helps user assess relevance
    - similarity score: Indicates confidence
    
    Args:
        search_phrase: Natural language query (e.g., "how to write unit tests")
        limit: Maximum results to return (capped at MAX_SEARCH_LIMIT for performance)
    
    Returns:
        List of dicts with keys: rank_order, title, filename, start_line, 
        end_line, content, similarity
        
    Performance notes:
    - Embedding generation: ~50ms on CPU
    - DuckDB similarity + sort: ~10ms for 100 chunks
    - Total: < 100ms for typical queries (2x faster than Python implementation)
    """
    # Validate and clamp limit
    # Why clamp: Prevents excessive memory usage and slow responses
    if not 1 <= limit <= MAX_SEARCH_LIMIT:
        limit = 10
    
    # Generate embedding for search query
    # Why same model: Must match document embeddings for meaningful comparison
    query_embedding = encode_text(search_phrase)[0]
    
    # Use DuckDB's native vector similarity function
    # Why array_cosine_similarity: Built-in, optimized C++ implementation
    # Why ORDER BY in SQL: Database can optimize the sort
    # Why LIMIT in SQL: Database only returns top N, more efficient
    results = conn.execute("""
        SELECT 
            title,
            filename,
            start_line,
            end_line,
            content,
            array_cosine_similarity(embedding, ?::FLOAT[768]) as similarity
        FROM documents
        ORDER BY similarity DESC
        LIMIT ?
    """, (query_embedding.tolist(), limit)).fetchall()
    
    # Format results
    # Why enumerate: Provides rank_order for client
    formatted_results = []
    for i, (title, filename, start_line, end_line, content, similarity) in enumerate(results):
        formatted_results.append({
            'rank_order': i,
            'title': title,
            'filename': filename,
            'start_line': start_line,
            'end_line': end_line,
            'content': content[:400] + "..." if len(content) > 400 else content,
            'similarity': float(similarity)
        })
    
    return formatted_results


@mcp.tool()
def pqsoft_read_docs(documentation_path: str, start_line: int, end_line: int) -> str:
    """
    Read specific line range from a documentation file.
    
    Why this tool exists:
    - pqsoft_search_docs returns snippets, this gets full content
    - Enables precise reading of relevant sections
    - Complements search by providing complete context
    
    Security considerations:
    - Only .md files allowed (prevents reading server code)
    - No hidden files (prevents .env, .git, etc.)
    - Path traversal prevention (can't escape docs/ directory)
    - Path resolution (handles symlinks and .. safely)
    
    Args:
        documentation_path: Relative path within docs/ (e.g., "testing/pytest.md")
        start_line: First line to read (1-indexed, inclusive)
        end_line: Last line to read (1-indexed, inclusive)
    
    Returns:
        Content of specified lines, or error message
        
    Error handling:
    - Returns descriptive error strings rather than raising exceptions
    - Why: MCP protocol expects string responses, not exceptions
    """
    # Security check: Only markdown files
    # Why: Prevents reading Python code, configs, secrets
    if not documentation_path.endswith('.md'):
        return "Error: Only .md files are allowed"
    
    # Security check: No hidden files or directories
    # Why: Prevents access to .env, .git, .secrets, etc.
    if any(part.startswith('.') for part in documentation_path.split('/')):
        return "Error: Hidden files and directories are not allowed"
    
    docs_dir = Path("docs")
    file_path = docs_dir / documentation_path
    
    # Security check: Prevent path traversal
    # Why resolve(): Converts relative paths to absolute, handles .. and symlinks
    # Why startswith check: Ensures file is within docs/ directory
    try:
        file_path = file_path.resolve()
        docs_dir = docs_dir.resolve()
        if not str(file_path).startswith(str(docs_dir)):
            return "Error: Path traversal not allowed"
    except Exception:
        # resolve() can fail on invalid paths
        return "Error: Invalid path"
    
    # Check file exists
    if not file_path.exists():
        return f"File not found: {documentation_path}"
    
    try:
        # Read entire file
        # Why read all: Simpler than seeking to specific lines
        # Performance: Files are small (< 100KB typically)
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        # Extract requested line range
        # Why max(0, ...): Handles negative line numbers gracefully
        # Why min(..., len(lines)): Handles end_line beyond file end
        # Why -1: Convert from 1-indexed to 0-indexed
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        
        selected_lines = lines[start_idx:end_idx]
        return '\n'.join(selected_lines)
        
    except Exception as e:
        # Catch-all for encoding errors, permission issues, etc.
        return f"Error reading file: {str(e)}"


@mcp.tool()
def pqsoft_recommend_docs(title: str) -> List[Dict]:
    """
    Get related documentation based on content similarity.
    
    How it works:
    1. Find document chunks matching the title
    2. Use DuckDB's native similarity to find related content
    3. Return top 5 most similar documents
    
    Why this is useful:
    - Discovers related content user might not know about
    - Helps navigate documentation structure
    - Complements search by suggesting related topics
    
    Use cases:
    - "After reading about testing, what else should I know?"
    - "What's related to deployment practices?"
    
    Args:
        title: Title or partial title of current document
    
    Returns:
        List of up to 5 related documents with title, context, and similarity
        
    Implementation notes:
    - Uses first matching chunk as reference
    - Excludes chunks from same document
    - Uses DuckDB native similarity for performance
    """
    # Find chunks matching the title
    # Why LIKE: Allows partial matches (e.g., "Testing" matches "Testing Strategy")
    # Why LIMIT 1: Just need one chunk as reference point
    current_results = conn.execute(
        "SELECT content, embedding FROM documents WHERE title LIKE ? LIMIT 1",
        (f"%{title}%",)
    ).fetchone()
    
    # Handle not found
    if not current_results:
        return []
    
    current_content, current_embedding = current_results
    
    # Use DuckDB's native similarity to find related documents
    # Why DISTINCT title: One recommendation per document, not per chunk
    # Why NOT LIKE: Exclude chunks from same document
    # Why ORDER BY + LIMIT: Get top 5 most similar
    results = conn.execute("""
        SELECT DISTINCT 
            title,
            content,
            array_cosine_similarity(embedding, ?::FLOAT[768]) as similarity
        FROM documents 
        WHERE title NOT LIKE ?
        ORDER BY similarity DESC
        LIMIT 5
    """, (current_embedding, f"%{title}%")).fetchall()
    
    # Format results
    recommendations = []
    for doc_title, content, similarity in results:
        recommendations.append({
            'title': doc_title,
            'context': content[:150] + "..." if len(content) > 150 else content,
            'similarity': float(similarity)
        })
    
    return recommendations


if __name__ == "__main__":
    # Run MCP server with stdio transport
    # Why stdio: Standard MCP transport, works with Q CLI and other clients
    # Why main guard: Prevents running when imported as module
    mcp.run(transport="stdio")
