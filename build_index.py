#!/usr/bin/env python3
"""
SDLC Documentation Indexer

This script builds a searchable vector database from markdown documentation files.
It runs at Docker build time to create embeddings that enable semantic search.

Architecture Decision: We use local CPU-based embeddings (thenlper/gte-small) to avoid
network dependencies and ensure the container is fully self-contained. This trades
some accuracy for reliability and portability.

Database Choice: DuckDB provides an embedded SQL database with native vector support,
eliminating the need for separate vector database infrastructure while maintaining
good performance for our use case (< 1000 documents).
"""

import os
from pathlib import Path
from typing import List, Dict

import duckdb
import numpy as np
from sentence_transformers import SentenceTransformer


def chunk_text(text: str, chunk_size: int = 300, overlap_lines: int = 2) -> List[Dict]:
    """
    Split markdown text into overlapping chunks with heading context.
    
    Why chunking is necessary:
    - Embedding models have token limits (typically 512 tokens)
    - Smaller chunks provide more precise search results
    - Overlap prevents information loss at boundaries
    
    Why we track headings:
    - Provides semantic context for each chunk
    - Improves embedding quality by including document structure
    - Helps users understand where content comes from
    
    Args:
        text: The full markdown document text
        chunk_size: Target number of words per chunk (not strict due to line boundaries)
        overlap_lines: Number of lines to overlap between chunks for continuity
    
    Returns:
        List of dicts with 'text', 'start_line', and 'end_line' keys
        
    Implementation notes:
    - We split on lines rather than words to preserve markdown structure
    - Heading context is prepended to each chunk for better embeddings
    - Line numbers track the original document position for read_documentation tool
    """
    lines = text.split('\n')
    chunks = []
    current_chunk = []
    current_words = 0
    start_line = 1
    current_line = 1
    
    # Track current heading hierarchy for context
    # Why dict instead of list: Makes it clear which heading level we're tracking
    current_headings = {'h1': '', 'h2': '', 'h3': ''}
    
    # Store last few lines for overlap between chunks
    # Why overlap: Prevents losing context when content spans chunk boundaries
    overlap_buffer = []
    
    for line in lines:
        # Update heading context as we encounter new headings
        # Why track all three levels: Provides full document hierarchy context
        if line.startswith('# '):
            current_headings['h1'] = line
            current_headings['h2'] = ''  # Reset lower levels
            current_headings['h3'] = ''
        elif line.startswith('## '):
            current_headings['h2'] = line
            current_headings['h3'] = ''  # Reset lower level
        elif line.startswith('### '):
            current_headings['h3'] = line
        
        words = line.split()
        
        # Check if we should start a new chunk
        # Why check current_chunk: Prevents creating empty chunks
        if current_words + len(words) > chunk_size and current_chunk:
            # Build heading context to prepend to chunk
            # Why prepend headings: Gives embedding model document structure context
            heading_context = []
            if current_headings['h1']:
                heading_context.append(current_headings['h1'])
            if current_headings['h2']:
                heading_context.append(current_headings['h2'])
            if current_headings['h3']:
                heading_context.append(current_headings['h3'])
            
            # Combine heading context with chunk content
            # Why empty string: Creates visual separation between headings and content
            chunk_with_context = heading_context + [''] + current_chunk
            
            chunks.append({
                'text': '\n'.join(chunk_with_context),
                'start_line': start_line,
                'end_line': current_line - 1
            })
            
            # Prepare overlap for next chunk
            # Why slice from end: Most recent lines are most relevant for continuity
            overlap_buffer = (current_chunk[-overlap_lines:] 
                            if len(current_chunk) >= overlap_lines 
                            else current_chunk)
            
            # Start new chunk with overlap
            current_chunk = overlap_buffer.copy()
            current_words = sum(len(l.split()) for l in current_chunk)
            start_line = current_line - len(overlap_buffer)
        
        current_chunk.append(line)
        current_words += len(words)
        current_line += 1
    
    # Handle final chunk (always exists if document has content)
    if current_chunk:
        heading_context = []
        if current_headings['h1']:
            heading_context.append(current_headings['h1'])
        if current_headings['h2']:
            heading_context.append(current_headings['h2'])
        if current_headings['h3']:
            heading_context.append(current_headings['h3'])
        
        chunk_with_context = heading_context + [''] + current_chunk
        
        chunks.append({
            'text': '\n'.join(chunk_with_context),
            'start_line': start_line,
            'end_line': current_line - 1
        })
    
    return chunks


def process_markdown_files() -> None:
    """
    Process all markdown files in docs/ directory and build vector database.
    
    Why this runs at build time:
    - Embeddings are expensive to compute (CPU-intensive)
    - Results are deterministic for same input
    - Avoids startup delay when container runs
    - Database is immutable after build (read-only at runtime)
    
    Database schema design:
    - id: Primary key for efficient lookups
    - title: Human-readable document name (from filename)
    - filename: Relative path for read_documentation tool
    - start_line/end_line: Precise location tracking
    - content: Original text for display in search results
    - embedding: 384-dimensional vector for semantic search
    
    Why FLOAT[384]: thenlper/gte-small produces 384-dimensional embeddings
    """
    docs_dir = Path("docs")
    
    # Create sample docs if none exist
    # Why: Provides working example out of the box for testing
    if not docs_dir.exists():
        print("No docs directory found, creating sample docs...")
        create_sample_docs()
    
    # Load embedding model
    # Why thenlper/gte-small: Good balance of quality vs size/speed for CPU inference
    # Why load once: Model loading is expensive, reuse for all documents
    print("Loading embedding model...")
    model = SentenceTransformer('thenlper/gte-small')
    
    # Initialize database
    # Why DuckDB: Embedded database with native vector support, no separate server needed
    conn = duckdb.connect('sdlc_docs.db')
    
    # Create table with vector column
    # Why IF NOT EXISTS: Allows script to be re-run safely
    # Why FLOAT[384]: Fixed-size array for efficient vector operations
    conn.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            title TEXT,
            filename TEXT,
            start_line INTEGER,
            end_line INTEGER,
            content TEXT,
            embedding FLOAT[384]
        )
    """)
    
    doc_id = 0
    
    # Process all markdown files recursively
    # Why **/*.md: Supports nested directory structure
    for md_file in docs_dir.glob("**/*.md"):
        # Skip files in hidden directories (starting with .)
        # Why: Prevents indexing .git, .vscode, etc.
        if any(part.startswith('.') for part in md_file.parts):
            continue
            
        relative_path = str(md_file.relative_to(docs_dir))
        print(f"Processing {relative_path}")
        
        # Read file content
        # Why utf-8: Standard encoding for markdown files
        content = md_file.read_text(encoding='utf-8')
        
        # Generate human-readable title from filename
        # Why replace: Convert kebab-case and snake_case to Title Case
        title = md_file.stem.replace('_', ' ').replace('-', ' ').title()
        
        # Split document into chunks
        chunks = chunk_text(content)
        
        for chunk_info in chunks:
            chunk_text_content = chunk_info['text']
            
            # Skip very short chunks (likely just headings or whitespace)
            # Why 50 chars: Arbitrary threshold, too short to be meaningful
            if len(chunk_text_content.strip()) < 50:
                continue
            
            # Generate embedding for this chunk
            # Why encode each chunk: Provides more precise search than whole-document embeddings
            # Returns numpy array of shape (384,)
            embedding = model.encode(chunk_text_content)
            
            # Insert into database
            # Why tolist(): DuckDB expects Python list, not numpy array
            conn.execute("""
                INSERT INTO documents (id, title, filename, start_line, end_line, content, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (doc_id, title, relative_path, chunk_info['start_line'], 
                  chunk_info['end_line'], chunk_text_content, embedding.tolist()))
            
            doc_id += 1
    
    # Commit and close
    # Why explicit close: Ensures database is properly flushed to disk
    conn.close()
    print(f"Indexed {doc_id} document chunks")


def create_sample_docs() -> None:
    """
    Create sample SDLC documentation for demonstration purposes.
    
    Why sample docs:
    - Provides working example without requiring user content
    - Useful for testing and validation
    - Shows expected markdown structure
    
    Content choice: Representative SDLC topics that demonstrate search capabilities
    """
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    
    # Sample documents covering common SDLC topics
    # Why these topics: Demonstrate variety of content types and search scenarios
    sample_docs = {
        "code_review_best_practices.md": """# Code Review Best Practices

## Overview
Code reviews are essential for maintaining code quality and knowledge sharing.

## Guidelines
- Review code within 24 hours of submission
- Focus on logic, readability, and maintainability
- Provide constructive feedback with examples
- Check for security vulnerabilities and performance issues

## Process
1. Create pull request with clear description
2. Assign reviewers based on expertise
3. Address feedback promptly
4. Require approval before merging""",

        "testing_strategy.md": """# Testing Strategy

## Test Pyramid
- Unit tests: 70% of test coverage
- Integration tests: 20% of test coverage  
- End-to-end tests: 10% of test coverage

## Best Practices
- Write tests before code (TDD)
- Maintain test independence
- Use descriptive test names
- Mock external dependencies
- Aim for 80%+ code coverage

## Continuous Testing
- Run tests on every commit
- Fail fast on test failures
- Maintain test environment parity""",

        "deployment_practices.md": """# Deployment Best Practices

## CI/CD Pipeline
- Automated builds on code changes
- Staged deployments (dev → staging → prod)
- Rollback capabilities
- Blue-green deployments for zero downtime

## Release Management
- Semantic versioning
- Feature flags for gradual rollouts
- Database migration strategies
- Monitoring and alerting post-deployment

## Security
- Secrets management
- Infrastructure as code
- Vulnerability scanning
- Access controls and audit logs"""
    }
    
    for filename, content in sample_docs.items():
        (docs_dir / filename).write_text(content)


if __name__ == "__main__":
    process_markdown_files()
