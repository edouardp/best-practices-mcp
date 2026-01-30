# Recommendations for `pqsoft_recommend_docs` Improvement

Based on analysis of AWS Documentation MCP's `aws___recommend` tool.

## Current Implementation
- Single recommendation type: content similarity
- Fixed limit of 5 results
- Basic error handling (returns empty list)
- Truncates context at 150 characters

## AWS MCP Approach

### 1. Multiple Recommendation Types
AWS provides 4 distinct recommendation categories:
- **Highly Rated**: Popular pages within the same service
- **New**: Recently added pages (useful for discovering new features)
- **Similar**: Content-based similarity (semantic search)
- **Journey**: Pages commonly viewed next by other users

### 2. Rich Result Metadata
Each recommendation includes:
- `url`: Direct link to the document
- `title`: Page title
- `context`: Brief description/summary (not just truncated content)

### 3. Input Flexibility
- Accepts full documentation URLs
- Handles various input formats gracefully

## Implemented Improvements (Quick Wins)

✅ **Configurable Limit**
- Added `limit` parameter (default: 5, max: 20)
- Validates and caps the limit

✅ **Better Error Handling**
- Returns helpful error message when document not found
- Provides suggestions based on partial title match
- No more silent empty list returns

✅ **Richer Results**
- Increased context from 150 to 200 characters
- Added `filename` to results for better navigation
- Rounded similarity scores to 3 decimal places

✅ **Improved Query**
- Fetches filename along with content and embedding
- More informative result structure

## Future Enhancements (Not Implemented)

### 1. Multiple Recommendation Types
```python
def pqsoft_recommend_docs(
    title: str, 
    limit: int = 5,
    recommendation_type: str = "similar"  # "similar", "popular", "recent", "all"
) -> List[Dict]:
```

**Implementation approach:**
- Add `view_count` column to track popularity
- Add `created_date` and `last_modified` timestamps
- Implement different query strategies per type

### 2. Better Context Extraction
Instead of truncating content:
- Extract first paragraph or summary section
- Include H1/H2 headings as context
- Use sentence boundaries for cleaner truncation

### 3. URL-Based Input
Accept both title and URL/path:
```python
def pqsoft_recommend_docs(
    identifier: str,  # Can be title, filename, or path
    limit: int = 5
) -> List[Dict]:
```

### 4. Popularity Tracking
Add schema changes:
```sql
ALTER TABLE documents ADD COLUMN view_count INTEGER DEFAULT 0;
ALTER TABLE documents ADD COLUMN last_accessed TIMESTAMP;
```

Track access in search/read functions:
```python
conn.execute("UPDATE documents SET view_count = view_count + 1 WHERE title = ?", (title,))
```

### 5. Recency Tracking
Add to build_index.py:
```python
import os
from datetime import datetime

file_mtime = os.path.getmtime(filepath)
created_date = datetime.fromtimestamp(file_mtime)
```

### 6. Journey Recommendations
Track document co-occurrence:
```sql
CREATE TABLE document_transitions (
    from_doc TEXT,
    to_doc TEXT,
    count INTEGER,
    PRIMARY KEY (from_doc, to_doc)
);
```

## Testing the Improvements

Run the integration test:
```bash
./test-local-mcp.sh
```

The test now:
- Searches for a document first
- Uses the found title for recommendations
- Handles empty results gracefully
- Validates the new result structure with filename

## Summary

**Immediate value added:**
- Configurable result limits
- Helpful error messages with suggestions
- Richer result metadata (filename included)
- Better user experience when document not found

**Future potential:**
- Multiple recommendation strategies (popular, recent, journey)
- Smarter context extraction
- Usage analytics and tracking
- More flexible input handling
