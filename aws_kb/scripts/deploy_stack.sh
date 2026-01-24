#!/bin/bash
set -e

STACK_NAME="sdlc-docs-kb-stack"
TEMPLATE_FILE="$(dirname "$0")/../cloudformation/kb-infrastructure.yaml"
CONFIG_FILE="$(dirname "$0")/../config.json"
REGION="ap-southeast-2"

echo "Deploying CloudFormation stack: $STACK_NAME"

aws cloudformation deploy \
  --template-file "$TEMPLATE_FILE" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --region "$REGION" \
  --no-fail-on-empty-changeset

echo "Extracting stack outputs..."

OUTPUTS=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --query 'Stacks[0].Outputs' \
  --output json)

BUCKET_NAME=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="BucketName") | .OutputValue')
KB_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="KnowledgeBaseId") | .OutputValue')
DS_ID=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="DataSourceId") | .OutputValue')
RERANKER_ARN=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="RerankerModelArn") | .OutputValue')
REGION_OUT=$(echo "$OUTPUTS" | jq -r '.[] | select(.OutputKey=="Region") | .OutputValue')

cat > "$CONFIG_FILE" <<EOF
{
  "bucket_name": "$BUCKET_NAME",
  "knowledge_base_id": "$KB_ID",
  "data_source_id": "$DS_ID",
  "reranker_model_arn": "$RERANKER_ARN",
  "region": "$REGION_OUT"
}
EOF

echo "Configuration saved to $CONFIG_FILE"
echo "Deployment complete!"
