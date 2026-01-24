# Quick Start Guide

## Prerequisites
- AWS CLI configured with credentials
- Python 3.11+
- uv installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- jq installed (`brew install jq`)

## Setup (5 minutes)

### 1. Deploy Infrastructure
```bash
cd aws_kb/scripts
./deploy_stack.sh
```
Wait ~3-5 minutes for CloudFormation stack creation.

### 2. Sync Documents
```bash
python3 sync_docs.py
```
Wait ~2-5 minutes for Knowledge Base ingestion.

### 3. Test the Server
```bash
cd ..
./run.sh
```

In another terminal:
```bash
cd aws_kb/tests
python3 test_search.py
python3 test_read.py
python3 test_recommend.py
```

### 4. Configure Q CLI

Add to `~/.aws/amazonq/mcp.json`:
```json
{
  "mcpServers": {
    "aws-kb-docs": {
      "command": "/absolute/path/to/best-practices-mcp/aws_kb/run.sh"
    }
  }
}
```

## Usage

Ask Q CLI:
- "Search the SDLC docs for testing strategies"
- "Read lines 1-50 from 04-testing-strategies.md"
- "What documents are related to deployment best practices?"

## Cleanup

```bash
aws cloudformation delete-stack --stack-name sdlc-docs-kb-stack --region ap-southeast-2
```

## Troubleshooting

See [README.md](README.md#troubleshooting) for detailed troubleshooting steps.
