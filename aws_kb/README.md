# AWS Knowledge Base MCP Server

AWS-native MCP server for SDLC documentation using AWS Bedrock Knowledge Base with S3 Vectors and built-in reranking.

## Architecture

```
docs/*.md → S3 Bucket → Knowledge Base (S3 Vectors + Titan Embeddings)
                              ↓
                    Retrieve API (with reranking)
                              ↓
                    MCP Server (boto3)
                              ↓
            3 Tools: search, read, recommend
```

## Features

- **S3 Vectors**: 90% cost reduction vs traditional vector databases
- **Built-in Reranking**: Cohere Rerank 3.5 or Amazon Rerank 1.0
- **Titan Embeddings**: Automatic embedding generation
- **Dual Storage**: Original docs in S3 for reading, vectors for search
- **CloudFormation**: Infrastructure as code

## Prerequisites

1. **AWS CLI** configured with credentials
   ```bash
   aws configure
   ```

2. **Python 3.11+** with uv
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **jq** for JSON processing
   ```bash
   brew install jq  # macOS
   ```

4. **AWS Permissions**:
   - CloudFormation full access
   - S3 full access
   - Bedrock full access
   - IAM role creation
   - OpenSearch Serverless access

## Setup

### 1. Deploy Infrastructure

```bash
cd aws_kb/scripts
./deploy_stack.sh
```

This creates:
- S3 bucket for documents
- Knowledge Base with S3 Vectors
- OpenSearch Serverless collection
- IAM roles and policies
- DataSource configuration

Outputs are saved to `aws_kb/config.json`.

### 2. Sync Documentation

```bash
cd aws_kb/scripts
python3 sync_docs.py
```

This:
- Uploads all `docs/*.md` files to S3
- Triggers Knowledge Base ingestion
- Waits for completion (~2-5 minutes)

### 3. Install Python Dependencies

```bash
cd aws_kb
uv venv
source .venv/bin/activate
uv pip install fastmcp boto3
```

### 4. Configure MCP

Add to `~/.aws/amazonq/mcp.json`:

```json
{
  "mcpServers": {
    "aws-kb-docs": {
      "command": "/absolute/path/to/best-practices-mcp/aws_kb/server.py"
    }
  }
}
```

Replace with your actual path.

## Tools

### `pqsoft_search_docs(search_phrase: str, limit: int = 10)`

Hybrid search with reranking.

**Example:**
```python
pqsoft_search_docs("testing strategies", limit=5)
```

**Returns:**
```python
[{
    'title': 'Testing Strategies',
    'filename': '04-testing-strategies.md',
    'start_line': 1,
    'end_line': 150,
    'content': '...',
    'similarity': 0.873
}, ...]
```

### `pqsoft_read_docs(documentation_path: str, start_line: int, end_line: int)`

Read specific line ranges from S3.

**Example:**
```python
pqsoft_read_docs('04-testing-strategies.md', 1, 50)
```

**Security:**
- Only `.md` files
- No path traversal (`..`)
- No hidden files (`.`)

### `pqsoft_recommend_docs(title: str)`

Find related documents.

**Example:**
```python
pqsoft_recommend_docs('Testing Strategies')
```

**Returns:** Top 5 similar documents with scores.

## Cost Considerations

### S3 Vectors
- **Storage**: ~$0.023/GB/month (S3 Standard)
- **Embeddings**: ~$0.0001 per 1K tokens (Titan)
- **Typical**: <$1/month for small doc sets

### Reranking
- **Cohere Rerank 3.5**: ~$0.002 per 1K tokens
- **Amazon Rerank 1.0**: ~$0.0025 per 1K tokens
- **Typical**: <$0.10/month for moderate usage

### OpenSearch Serverless
- **OCU**: ~$0.24/hour per OCU
- **Minimum**: 2 OCUs = ~$350/month
- **Note**: Most expensive component

**Total Estimated Cost**: ~$350-400/month

## Configuration

### Change Reranker Model

Edit `cloudformation/kb-infrastructure.yaml`:

```yaml
Parameters:
  RerankerModelId:
    Default: 'amazon.rerank-v1:0'  # or 'cohere.rerank-v3-5:0'
```

Redeploy:
```bash
./scripts/deploy_stack.sh
```

### Change Region

Edit `scripts/deploy_stack.sh`:

```bash
REGION="us-east-1"  # Change from ap-southeast-2
```

**Note**: Verify model availability in target region.

## Troubleshooting

### Stack deployment fails

```bash
# Check CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name sdlc-docs-kb-stack \
  --region ap-southeast-2
```

### Ingestion fails

```bash
# Check ingestion job status
aws bedrock-agent get-ingestion-job \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID> \
  --ingestion-job-id <JOB_ID> \
  --region ap-southeast-2
```

### Search returns no results

1. Verify ingestion completed:
   ```bash
   python3 scripts/sync_docs.py
   ```

2. Check S3 bucket has files:
   ```bash
   aws s3 ls s3://<BUCKET_NAME>/ --region ap-southeast-2
   ```

3. Test Knowledge Base directly:
   ```bash
   aws bedrock-agent-runtime retrieve \
     --knowledge-base-id <KB_ID> \
     --retrieval-query text="test" \
     --region ap-southeast-2
   ```

### Permission errors

Verify IAM role has:
- `bedrock:InvokeModel` for embeddings and reranker
- `s3:GetObject` and `s3:ListBucket` for documents
- `aoss:*` for OpenSearch Serverless

## Development

### Test Search

```bash
cd aws_kb/tests
python3 test_search.py
```

### Test Reading

```bash
cd aws_kb/tests
python3 test_read.py
```

### Test Recommendations

```bash
cd aws_kb/tests
python3 test_recommend.py
```

## Cleanup

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack \
  --stack-name sdlc-docs-kb-stack \
  --region ap-southeast-2

# Empty and delete S3 bucket
aws s3 rm s3://<BUCKET_NAME> --recursive --region ap-southeast-2
aws s3 rb s3://<BUCKET_NAME> --region ap-southeast-2
```

## Comparison with Local Implementation

| Feature      | Local (src_mcp)       | AWS (aws_kb) |
| ------------ | --------------------- | ------------ |
| Vector Store | DuckDB                | S3 Vectors   |
| Embeddings   | sentence-transformers | Titan        |
| Search       | BM25 + Vector         | Vector only  |
| Reranking    | cross-encoder         | Bedrock      |
| Cost         | $0                    | ~$350/month  |
| Latency      | <200ms                | ~500ms       |
| Scalability  | Limited               | Unlimited    |
| Maintenance  | Manual                | Managed      |

## License

This project is provided as-is for SDLC documentation purposes.

## Status

✅ **Production Ready**
- CloudFormation validated
- All tools implemented
- Security hardened
- Fully documented
