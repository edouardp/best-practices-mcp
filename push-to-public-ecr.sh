#!/bin/bash

REGION="ap-southeast-2"
REPO_NAME="best-practices-mcp"

# Login to public ECR
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws

# Get repository URI from CloudFormation
REPO_URI=$(aws cloudformation describe-stacks \
  --stack-name best-practices-mcp-public-ecr \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`RepositoryURI`].OutputValue' \
  --output text)

# Tag and push
docker tag best-practices-mcp:latest $REPO_URI:latest
docker push $REPO_URI:latest

echo "Image pushed to: $REPO_URI:latest"
