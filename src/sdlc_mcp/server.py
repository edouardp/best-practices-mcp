#!/usr/bin/env python3
"""
SDLC Documentation MCP Server

Hybrid search architecture:
1. BM25 (lexical) - exact keyword matching via DuckDB FTS
2. Vector (semantic) - conceptual similarity via embeddings  
3. Reranker (cross-encoder) - precise relevance scoring

All models loaded at startup for consistent query latency.
"""

import sys
from pathlib import Path
from typing import List, Dict

import duckdb
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from fastmcp import FastMCP

# Configuration
EMBEDDING_MODEL = 'sentence-transformers/all-mpnet-base-v2'
RERANKER_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
MAX_SEARCH_LIMIT = 50
CANDIDATE_LIMIT = 30  # Top N from each retrieval method

# Initialize MCP server
mcp = FastMCP("SDLC Docs Server")

# Load models at startup
print("Loading embedding model...", file=sys.stderr)
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

print("Loading reranker model...", file=sys.stderr)
reranker = CrossEncoder(RERANKER_MODEL)

# Connect to database
conn = duckdb.connect('sdlc_docs.db', read_only=True)
conn.execute("LOAD fts")


def bm25_search(query: str, limit: int = CANDIDATE_LIMIT) -> List[Dict]:
    """BM25 lexical search using DuckDB FTS extension."""
    if not query.strip():
        return []
    
    results = conn.execute("""
        SELECT id, title, filename, start_line, end_line, content, score
        FROM (
            SELECT *, fts_main_documents.match_bm25(id, ?) AS score
            FROM documents
        ) sq
        WHERE score IS NOT NULL
        ORDER BY score DESC
        LIMIT ?
    """, (query, limit)).fetchall()
    
    return [
        {"id": r[0], "title": r[1], "filename": r[2], "start_line": r[3], 
         "end_line": r[4], "content": r[5], "bm25_score": float(r[6])}
        for r in results
    ]


def vector_search(query: str, limit: int = CANDIDATE_LIMIT) -> List[Dict]:
    """Vector similarity search using embeddings."""
    query_embedding = embedding_model.encode(query)
    
    results = conn.execute("""
        SELECT id, title, filename, start_line, end_line, content,
               array_cosine_similarity(embedding, ?::FLOAT[768]) as similarity
        FROM documents
        ORDER BY similarity DESC
        LIMIT ?
    """, (query_embedding.tolist(), limit)).fetchall()
    
    return [
        {"id": r[0], "title": r[1], "filename": r[2], "start_line": r[3],
         "end_line": r[4], "content": r[5], "vector_score": float(r[6])}
        for r in results
    ]


def rerank_candidates(query: str, candidates: List[Dict], limit: int) -> List[Dict]:
    """Rerank candidates using cross-encoder model."""
    if not candidates:
        return []
    
    # Create query-document pairs
    pairs = [(query, c["content"]) for c in candidates]
    
    # Get reranker scores
    scores = reranker.predict(pairs)
    
    # Add scores and sort
    for c, score in zip(candidates, scores):
        c["rerank_score"] = float(score)
    
    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    return candidates[:limit]


@mcp.tool()
def pqsoft_search_docs(search_phrase: str, limit: int = 10) -> List[Dict]:
    """
    Search SDLC documentation using hybrid retrieval + reranking.
    
    Pipeline:
    1. BM25 search for keyword matches (top 30)
    2. Vector search for semantic matches (top 30)
    3. Union and deduplicate candidates
    4. Rerank with cross-encoder for final ordering
    """
    if not 1 <= limit <= MAX_SEARCH_LIMIT:
        limit = 10
    
    # Stage 1: Parallel retrieval
    bm25_results = bm25_search(search_phrase, CANDIDATE_LIMIT)
    vector_results = vector_search(search_phrase, CANDIDATE_LIMIT)
    
    # Stage 2: Union and dedupe by id
    seen_ids = set()
    candidates = []
    
    for r in bm25_results + vector_results:
        if r["id"] not in seen_ids:
            seen_ids.add(r["id"])
            candidates.append(r)
    
    # Stage 3: Rerank
    reranked = rerank_candidates(search_phrase, candidates, limit)
    
    # Format results
    return [
        {
            "rank_order": i,
            "title": r["title"],
            "filename": r["filename"],
            "start_line": r["start_line"],
            "end_line": r["end_line"],
            "content": r["content"][:400] + "..." if len(r["content"]) > 400 else r["content"],
            "similarity": r.get("rerank_score", 0.0)
        }
        for i, r in enumerate(reranked)
    ]


@mcp.tool()
def pqsoft_read_docs(documentation_path: str, start_line: int, end_line: int) -> str:
    """Read specific line range from a documentation file."""
    if not documentation_path.endswith('.md'):
        return "Error: Only .md files are allowed"
    
    if any(part.startswith('.') for part in documentation_path.split('/')):
        return "Error: Hidden files and directories are not allowed"
    
    docs_dir = Path("docs")
    file_path = docs_dir / documentation_path
    
    try:
        file_path = file_path.resolve()
        docs_dir = docs_dir.resolve()
        if not str(file_path).startswith(str(docs_dir)):
            return "Error: Path traversal not allowed"
    except Exception:
        return "Error: Invalid path"
    
    if not file_path.exists():
        return f"File not found: {documentation_path}"
    
    try:
        content = file_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        start_idx = max(0, start_line - 1)
        end_idx = min(len(lines), end_line)
        return '\n'.join(lines[start_idx:end_idx])
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.tool()
def pqsoft_recommend_docs(title: str) -> List[Dict]:
    """Get related documentation based on content similarity."""
    current_results = conn.execute(
        "SELECT content, embedding FROM documents WHERE title LIKE ? LIMIT 1",
        (f"%{title}%",)
    ).fetchone()
    
    if not current_results:
        return []
    
    current_content, current_embedding = current_results
    
    results = conn.execute("""
        SELECT DISTINCT title, content,
               array_cosine_similarity(embedding, ?::FLOAT[768]) as similarity
        FROM documents 
        WHERE title NOT LIKE ?
        ORDER BY similarity DESC
        LIMIT 5
    """, (current_embedding, f"%{title}%")).fetchall()
    
    return [
        {
            "title": r[0],
            "context": r[1][:150] + "..." if len(r[1]) > 150 else r[1],
            "similarity": float(r[2])
        }
        for r in results
    ]


def create_server() -> FastMCP:
    """Factory function for tests."""
    return mcp


if __name__ == "__main__":
    mcp.run(transport="stdio")
