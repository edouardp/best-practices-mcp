#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../config.json"
DOCS_DIR="$SCRIPT_DIR/../../docs"

# Load config
BUCKET_NAME=$(jq -r '.bucket_name' "$CONFIG_FILE")
KB_ID=$(jq -r '.knowledge_base_id' "$CONFIG_FILE")
DS_ID=$(jq -r '.data_source_id' "$CONFIG_FILE")
REGION=$(jq -r '.region' "$CONFIG_FILE")

echo "Syncing documents from $DOCS_DIR to s3://$BUCKET_NAME/"

# Sync only .md files, delete removed files
SYNC_OUTPUT=$(aws s3 sync "$DOCS_DIR" "s3://$BUCKET_NAME/" \
    --exclude '*' \
    --include '*.md' \
    --delete \
    --region "$REGION" 2>&1)

echo "$SYNC_OUTPUT"

# Check if any files were synced
if [ -z "$SYNC_OUTPUT" ]; then
    echo "No changes detected, skipping ingestion"
    exit 0
fi

echo "Sync complete!"

# Start ingestion
echo "Starting Knowledge Base ingestion..."
JOB_ID=$(aws bedrock-agent start-ingestion-job \
    --knowledge-base-id "$KB_ID" \
    --data-source-id "$DS_ID" \
    --region "$REGION" \
    --query 'ingestionJob.ingestionJobId' \
    --output text)

echo "Ingestion job started: $JOB_ID"

# Poll for completion
while true; do
    STATUS=$(aws bedrock-agent get-ingestion-job \
        --knowledge-base-id "$KB_ID" \
        --data-source-id "$DS_ID" \
        --ingestion-job-id "$JOB_ID" \
        --region "$REGION" \
        --query 'ingestionJob.status' \
        --output text)
    
    echo "  Status: $STATUS"
    
    if [ "$STATUS" = "COMPLETE" ]; then
        echo "Ingestion complete!"
        exit 0
    elif [ "$STATUS" = "FAILED" ]; then
        echo "Ingestion failed!"
        exit 1
    fi
    
    sleep 10
done
