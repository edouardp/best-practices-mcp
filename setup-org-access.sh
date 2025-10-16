#!/bin/bash

REPO_NAME="best-practices-mcp"
REGION="ap-southeast-2"

# Get your organization ID
ORG_ID=$(aws organizations describe-organization --query 'Organization.Id' --output text 2>/dev/null)

if [ -z "$ORG_ID" ]; then
  echo "Error: Could not retrieve Organization ID. Ensure you have organizations:DescribeOrganization permission."
  exit 1
fi

echo "Using Organization ID: $ORG_ID"

# Create policy with org ID
cat > temp-org-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowOrganizationAccess",
      "Effect": "Allow",
      "Principal": "*",
      "Action": [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Condition": {
        "ForAnyValue:StringEquals": {
          "aws:PrincipalOrgID": "$ORG_ID"
        }
      }
    }
  ]
}
EOF

# Apply policy
aws ecr set-repository-policy \
  --repository-name $REPO_NAME \
  --policy-text file://temp-org-policy.json \
  --region $REGION

rm temp-org-policy.json
echo "Organization-wide policy applied to $REPO_NAME for org $ORG_ID"
