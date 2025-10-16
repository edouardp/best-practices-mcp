# Team Setup Instructions

## For Team Members

1. **Pull the image:**
```bash
aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com
docker pull ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com/best-practices-mcp:latest
```

2. **Add to Q CLI config** (`~/.aws/amazonq/mcp.json`):
```json
{
  "mcpServers": {
    "sdlc-docs": {
      "command": "docker",
      "args": ["run", "--read-only", "-i", "ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com/best-practices-mcp:latest"]
    }
  }
}
```

Replace `ACCOUNT_ID` with your actual AWS account ID.

## For Administrators

1. **Create IAM policy** using `ecr-policy.json`
2. **Attach to team role/users**
3. **Share account ID and region** with team
