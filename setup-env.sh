#!/bin/bash

# Add to ~/.bashrc or ~/.zshrc
export ECR_REGISTRY="$(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-southeast-2.amazonaws.com"
export MCP_IMAGE="$ECR_REGISTRY/best-practices-mcp:latest"

echo "Add these to your shell profile:"
echo "export ECR_REGISTRY=\"$ECR_REGISTRY\""
echo "export MCP_IMAGE=\"$MCP_IMAGE\""
