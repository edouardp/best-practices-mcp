#!/bin/bash

REPO_NAME="best-practices-mcp"
REGION="ap-southeast-2"

# Replace with actual account IDs
ACCOUNT_IDS=("123456789012" "234567890123")

# Build principal ARNs
PRINCIPALS=""
for account in "${ACCOUNT_IDS[@]}"; do
  PRINCIPALS="$PRINCIPALS\"arn:aws:iam::$account:root\","
done
PRINCIPALS=${PRINCIPALS%,}  # Remove trailing comma

# Create policy JSON
cat > temp-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCrossAccountPull",
      "Effect": "Allow",
      "Principal": {
        "AWS": [$PRINCIPALS]
      },
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ]
    }
  ]
}
EOF

# Apply policy
aws ecr set-repository-policy \
  --repository-name $REPO_NAME \
  --policy-text file://temp-policy.json \
  --region $REGION

rm temp-policy.json
echo "Cross-account policy applied to $REPO_NAME"
