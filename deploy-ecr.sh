#!/bin/bash

STACK_NAME="best-practices-mcp-ecr"
REGION="ap-southeast-2"

# Get organization ID
ORG_ID=$(aws organizations describe-organization --query 'Organization.Id' --output text 2>/dev/null)

if [ -z "$ORG_ID" ]; then
  echo "Error: Could not retrieve Organization ID"
  exit 1
fi

echo "Deploying ECR stack with Organization ID: $ORG_ID"

aws cloudformation deploy \
  --template-file ecr-template.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides OrganizationId=$ORG_ID \
  --region $REGION \
  --capabilities CAPABILITY_IAM

# Get repository URI
REPO_URI=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`RepositoryURI`].OutputValue' \
  --output text)

echo "Repository URI: $REPO_URI"
