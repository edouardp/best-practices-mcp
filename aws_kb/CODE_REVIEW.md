# Code Review: AWS Knowledge Base MCP Server

## Critical Issues (Must Fix)

### 1. **Error Handling - Missing Exception Handling**
**Location**: `server.py` - all three tools
**Issue**: No try-except blocks for AWS API calls
**Risk**: Unhandled boto3 exceptions will crash the MCP server
**Fix**:
```python
@mcp.tool()
def pqsoft_search_docs(search_phrase: str, limit: int = 10) -> list[dict]:
    try:
        response = bedrock_runtime.retrieve(...)
        # ... process results
    except bedrock_runtime.exceptions.ResourceNotFoundException as e:
        raise ValueError(f"Knowledge Base not found: {e}")
    except bedrock_runtime.exceptions.ThrottlingException:
        raise ValueError("Rate limited, please try again")
    except Exception as e:
        raise ValueError(f"Search failed: {e}")
```

### 2. **Security - Hardcoded Credentials Risk**
**Location**: `server.py` - boto3 client initialization
**Issue**: No explicit AWS profile/credentials handling
**Risk**: May use wrong AWS credentials in production
**Fix**: Add explicit credential handling with environment variables
```python
session = boto3.Session(
    profile_name=os.environ.get('AWS_PROFILE'),
    region_name=config['region']
)
bedrock_runtime = session.client('bedrock-agent-runtime')
```

### 3. **Resource Management - File Handle Leak**
**Location**: `server.py:load_config()`, `sync_docs.py:load_config()`
**Issue**: File not closed if exception occurs
**Fix**:
```python
def load_config():
    config_path = Path(__file__).parent / 'config.json'
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        raise ValueError(f"Config file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config: {e}")
```

### 4. **Input Validation - Missing Limit Bounds**
**Location**: `server.py:pqsoft_search_docs()`
**Issue**: No validation on `limit` parameter
**Risk**: Could request 10,000 results and cause timeout/cost issues
**Fix**:
```python
def pqsoft_search_docs(search_phrase: str, limit: int = 10) -> list[dict]:
    if not 1 <= limit <= 50:
        raise ValueError("Limit must be between 1 and 50")
    if not search_phrase or not search_phrase.strip():
        raise ValueError("Search phrase cannot be empty")
```

## High Priority Issues

### 5. **Reliability - No Retry Logic**
**Location**: `sync_docs.py:start_ingestion()`
**Issue**: Infinite loop with no timeout or max retries
**Risk**: Script hangs forever if ingestion stalls
**Fix**:
```python
MAX_RETRIES = 60  # 10 minutes
retries = 0
while retries < MAX_RETRIES:
    status = bedrock.get_ingestion_job(...)
    state = status['ingestionJob']['status']
    if state in ['COMPLETE', 'FAILED']:
        break
    retries += 1
    time.sleep(10)

if retries >= MAX_RETRIES:
    print("Ingestion timeout!")
    sys.exit(1)
```

### 7. **Observability - No Logging**
**Location**: All Python files
**Issue**: Uses print() instead of proper logging
**Impact**: Can't control log levels or format
**Fix**:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Syncing documents...")
logger.error("Ingestion failed", exc_info=True)
```

### 8. **Configuration - Secrets in config.json**
**Location**: `config.json` (not in repo, but referenced)
**Issue**: Config file contains AWS resource IDs
**Risk**: If committed, exposes infrastructure details
**Fix**: Add to .gitignore (already done) + document in README

## Medium Priority Issues

### 9. **Code Quality - Global State**
**Location**: `server.py` - module-level config and clients
**Issue**: Config loaded at import time, not lazy
**Impact**: Fails immediately if config.json missing, even for --help
**Fix**:
```python
_config = None
_bedrock_runtime = None
_s3 = None

def get_config():
    global _config
    if _config is None:
        _config = load_config()
    return _config

def get_bedrock_client():
    global _bedrock_runtime
    if _bedrock_runtime is None:
        config = get_config()
        _bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=config['region'])
    return _bedrock_runtime
```

### 10. **Testing - No Unit Tests**
**Location**: `aws_kb/tests/` - only integration tests
**Issue**: Can't test individual functions without AWS
**Fix**: Add unit tests with mocked boto3 clients
```python
# tests/test_server_unit.py
from unittest.mock import Mock, patch
import pytest

@patch('server.bedrock_runtime')
def test_search_docs_handles_empty_results(mock_client):
    mock_client.retrieve.return_value = {'retrievalResults': []}
    results = pqsoft_search_docs("test", 10)
    assert results == []
```

### 11. **Documentation - Missing Docstring Details**
**Location**: All tool functions
**Issue**: Docstrings don't describe parameters or return values
**Fix**:
```python
def pqsoft_search_docs(search_phrase: str, limit: int = 10) -> list[dict]:
    """Search SDLC documentation using vector retrieval.
    
    Args:
        search_phrase: Query text to search for
        limit: Maximum number of results (1-50, default 10)
        
    Returns:
        List of dicts with keys: title, filename, start_line, end_line, content, similarity
        
    Raises:
        ValueError: If search_phrase is empty or limit is out of range
    """
```

### 12. **CloudFormation - Missing Deletion Policy**
**Location**: `kb-infrastructure.yaml` - DocumentsBucket
**Issue**: S3 bucket will fail to delete if it contains objects
**Fix**:
```yaml
DocumentsBucket:
  Type: AWS::S3::Bucket
  DeletionPolicy: Retain  # Or add lifecycle policy to empty bucket
  Properties:
    # ...
```

## Low Priority Issues

### 13. **Code Style - Inconsistent String Quotes**
**Location**: Various files
**Issue**: Mix of single and double quotes
**Fix**: Use double quotes consistently (or run `black` formatter)

### 14. **Type Hints - Missing Return Type Annotations**
**Location**: `sync_docs.py`, helper functions
**Issue**: Functions missing return type hints
**Fix**:
```python
def load_config() -> dict:
def sync_docs(config: dict) -> None:
def start_ingestion(config: dict) -> None:
```

### 15. **Performance - Redundant API Calls**
**Location**: `server.py:pqsoft_recommend_docs()`
**Issue**: Makes 2 API calls (search + similar)
**Optimization**: Could use single call with higher limit and filter client-side

### 16. **Maintainability - Magic Numbers**
**Location**: Various files
**Issue**: Hardcoded values like 1000, 10, 5
**Fix**:
```python
MAX_CONTENT_LENGTH = 1000  # chars for similarity query
DEFAULT_SEARCH_LIMIT = 10
MAX_RECOMMENDATIONS = 5
```

## Best Practices Alignment

### ✅ Good Practices Already Followed
1. **Security**: Path traversal prevention in `pqsoft_read_docs`
2. **Security**: File type restrictions (.md only)
3. **Infrastructure as Code**: CloudFormation for all resources
4. **Dependency Management**: Using uv with pyproject.toml
5. **Documentation**: Comprehensive README and QUICKSTART
6. **Separation of Concerns**: Scripts separated by function

### ❌ Missing Best Practices
1. **No health check endpoint** for monitoring
2. **No metrics/telemetry** (CloudWatch, X-Ray)
3. **No rate limiting** on MCP tools
4. **No request validation** beyond basic checks
5. **No circuit breaker** for AWS API failures
6. **No graceful degradation** if KB unavailable

## Priority Recommendations

### Must Do (Before Production)
1. Add exception handling to all AWS API calls
2. Add input validation with bounds checking
3. Add timeout to ingestion polling loop
4. Add proper logging instead of print()
5. Add unit tests with mocked AWS clients

### Should Do (Next Sprint)
6. Add retry logic with exponential backoff
7. Add CloudFormation DeletionPolicy
8. Add health check mechanism
9. Document error codes and troubleshooting

### Nice to Have (Future)
11. Add CloudWatch metrics
12. Add X-Ray tracing
13. Implement rate limiting
14. Add circuit breaker pattern
15. Create performance benchmarks

## Estimated Effort
- Critical fixes: 4-6 hours
- High priority: 6-8 hours
- Medium priority: 8-12 hours
- Low priority: 4-6 hours

**Total**: ~22-32 hours for full compliance
