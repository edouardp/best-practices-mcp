"""Tests for hybrid search functionality (BM25 + Vector + Reranker)."""

import pytest


class TestBM25Search:
    """Tests for BM25 lexical search functionality."""

    def test_bm25_search_returns_results_for_exact_keywords(self) -> None:
        """BM25 should find documents containing exact query terms."""
        from sdlc_mcp.server import bm25_search
        
        results = bm25_search("testing", limit=10)
        
        assert isinstance(results, list)
        for r in results:
            assert "id" in r
            assert "content" in r
            assert "bm25_score" in r

    def test_bm25_search_empty_query_returns_empty(self) -> None:
        """BM25 should handle empty query gracefully."""
        from sdlc_mcp.server import bm25_search
        
        results = bm25_search("", limit=10)
        assert results == []

    def test_bm25_search_no_matches_returns_empty(self) -> None:
        """BM25 should return empty list when no documents match."""
        from sdlc_mcp.server import bm25_search
        
        results = bm25_search("xyznonexistentterm123", limit=10)
        assert results == []


class TestVectorSearch:
    """Tests for vector similarity search."""

    def test_vector_search_returns_results(self) -> None:
        """Vector search should return semantically similar results."""
        from sdlc_mcp.server import vector_search
        
        results = vector_search("how to write tests", limit=10)
        
        assert isinstance(results, list)
        assert len(results) > 0
        for r in results:
            assert "id" in r
            assert "content" in r
            assert "vector_score" in r


class TestReranker:
    """Tests for cross-encoder reranking functionality."""

    def test_reranker_model_loads_at_startup(self) -> None:
        """Cross-encoder reranker should be loaded and available."""
        from sdlc_mcp.server import reranker
        
        assert reranker is not None

    def test_reranker_reorders_results(self) -> None:
        """Reranker should reorder candidates by relevance score."""
        from sdlc_mcp.server import rerank_candidates
        
        candidates = [
            {"id": 1, "content": "This is about deployment pipelines"},
            {"id": 2, "content": "Unit testing best practices for Python"},
            {"id": 3, "content": "How to write effective unit tests"},
        ]
        
        reranked = rerank_candidates("unit testing", candidates, limit=3)
        
        assert len(reranked) == 3
        # All should have rerank scores
        for r in reranked:
            assert "rerank_score" in r

    def test_reranker_handles_empty_candidates(self) -> None:
        """Reranker should return empty list for empty input."""
        from sdlc_mcp.server import rerank_candidates
        
        results = rerank_candidates("any query", [], limit=10)
        assert results == []

    def test_reranker_respects_limit(self) -> None:
        """Reranker should return at most 'limit' results."""
        from sdlc_mcp.server import rerank_candidates
        
        candidates = [
            {"id": i, "content": f"Document content {i}"} 
            for i in range(20)
        ]
        
        results = rerank_candidates("test query", candidates, limit=5)
        assert len(results) <= 5


class TestHybridRetrieval:
    """Tests for hybrid BM25 + vector retrieval."""

    def test_hybrid_search_returns_results(self) -> None:
        """Hybrid search should return results."""
        from sdlc_mcp.server import bm25_search, vector_search, rerank_candidates
        
        query = "code review best practices"
        bm25_results = bm25_search(query, 30)
        vector_results = vector_search(query, 30)
        
        # Union and dedupe
        seen_ids = set()
        candidates = []
        for r in bm25_results + vector_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                candidates.append(r)
        
        reranked = rerank_candidates(query, candidates, 10)
        
        assert len(reranked) > 0

    def test_hybrid_search_deduplicates_results(self) -> None:
        """Hybrid search should not return duplicate chunks."""
        from sdlc_mcp.server import bm25_search, vector_search
        
        query = "testing strategy"
        bm25_results = bm25_search(query, 30)
        vector_results = vector_search(query, 30)
        
        # Union and dedupe
        seen_ids = set()
        candidates = []
        for r in bm25_results + vector_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                candidates.append(r)
        
        # Check no duplicates
        ids = [c["id"] for c in candidates]
        assert len(ids) == len(set(ids))

    def test_hybrid_search_keyword_query_includes_bm25_results(self) -> None:
        """Exact keyword queries should benefit from BM25."""
        from sdlc_mcp.server import bm25_search
        
        results = bm25_search("Python", limit=10)
        
        assert len(results) > 0
        # At least one result should contain the exact term
        found_exact = any("Python" in r["content"] or "python" in r["content"].lower() 
                         for r in results)
        assert found_exact


class TestFTSIndex:
    """Tests for Full Text Search index creation."""

    def test_fts_index_exists_in_database(self) -> None:
        """FTS index should be created on documents table."""
        from sdlc_mcp.server import conn
        
        # FTS creates a schema named fts_main_<table> with internal tables
        result = conn.execute("""
            SELECT * FROM duckdb_tables() 
            WHERE schema_name = 'fts_main_documents'
        """).fetchall()
        
        assert len(result) > 0, "FTS index tables should exist"


class TestIntegration:
    """End-to-end integration tests."""

    def test_end_to_end_hybrid_search(self) -> None:
        """Full pipeline: BM25 + vector + rerank should work together."""
        from sdlc_mcp.server import bm25_search, vector_search, rerank_candidates
        
        query = "deployment best practices"
        
        # Stage 1: Retrieval
        bm25_results = bm25_search(query, 30)
        vector_results = vector_search(query, 30)
        
        # Stage 2: Union and dedupe
        seen_ids = set()
        candidates = []
        for r in bm25_results + vector_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                candidates.append(r)
        
        # Stage 3: Rerank
        results = rerank_candidates(query, candidates, 5)
        
        assert isinstance(results, list)
        assert len(results) > 0
        assert len(results) <= 5

    def test_search_performance_under_threshold(self) -> None:
        """Search should complete in reasonable time (<3s including model inference)."""
        import time
        from sdlc_mcp.server import bm25_search, vector_search, rerank_candidates
        
        query = "testing and deployment"
        
        start = time.time()
        bm25_results = bm25_search(query, 30)
        vector_results = vector_search(query, 30)
        
        seen_ids = set()
        candidates = []
        for r in bm25_results + vector_results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                candidates.append(r)
        
        results = rerank_candidates(query, candidates, 10)
        elapsed = time.time() - start
        
        assert elapsed < 3.0, f"Search took {elapsed:.2f}s, should be under 3s"
