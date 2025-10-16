#!/bin/bash

STACK_NAME="best-practices-mcp-public-ecr"
REGION="ap-southeast-2"

# Replace with your actual corporate IP ranges
CORPORATE_IPS="203.0.113.0/24,198.51.100.0/24"

echo "Deploying public ECR with IP restrictions: $CORPORATE_IPS"

aws cloudformation deploy \
  --template-file ecr-public-template.yaml \
  --stack-name $STACK_NAME \
  --parameter-overrides CorporateIPRanges=$CORPORATE_IPS \
  --region $REGION

# Get repository URI
REPO_URI=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`RepositoryURI`].OutputValue' \
  --output text)

echo "Public Repository URI: $REPO_URI"
echo "Usage: docker pull $REPO_URI"
