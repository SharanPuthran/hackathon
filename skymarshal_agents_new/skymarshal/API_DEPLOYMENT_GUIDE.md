# AgentCore REST API - Deployment Guide

## Overview

This guide walks through deploying the SkyMarshal AgentCore REST API to AWS.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with SSO credentials
3. **Terraform** installed (>= 1.0)
4. **AgentCore Runtime** already deployed
5. **Python 3.11+** and **uv** installed

## Step 1: Get AgentCore Runtime ARN

First, get the ARN of your deployed AgentCore Runtime:

```bash
# List deployed runtimes
uv run agentcore status

# Or use AWS CLI
aws bedrock-agentcore list-runtimes --region us-east-1
```

Copy the ARN, it should look like:

```
arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/skymarshal
```

## Step 2: Set Environment Variables

```bash
export AGENTCORE_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/skymarshal"
export AWS_REGION="us-east-1"
```

## Step 3: Deploy Infrastructure

```bash
cd skymarshal_agents_new/skymarshal

# Run deployment script
./scripts/deploy_api.sh dev
```

The script will:

1. Package Lambda functions with dependencies
2. Deploy infrastructure using Terraform
3. Create DynamoDB table for sessions
4. Set up API Gateway with endpoints
5. Configure IAM roles and permissions
6. Output API endpoint URLs

## Step 4: Verify Deployment

After deployment completes, you'll see output like:

```
═══════════════════════════════════════════════════════════
API Endpoints:
═══════════════════════════════════════════════════════════
Base URL:    https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/api/v1
Invoke:      https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
Health:      https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/api/v1/health
═══════════════════════════════════════════════════════════
```

Test the health endpoint:

```bash
curl https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "dependencies": {
    "dynamodb": "healthy",
    "agentcore": "healthy"
  }
}
```

## Step 5: Test API Invocation

Install awscurl for AWS Signature V4 authentication:

```bash
pip install awscurl
```

Test the invoke endpoint:

```bash
awscurl --service execute-api \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Flight AA123 delayed 3 hours due to weather"}' \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
```

## Step 6: Monitor Logs

View Lambda logs:

```bash
# Invoke function logs
aws logs tail /aws/lambda/skymarshal-api-invoke-dev --follow

# Health check logs
aws logs tail /aws/lambda/skymarshal-api-health-dev --follow
```

## Troubleshooting

### Issue: "Failed to connect to AgentCore Runtime"

**Solution**: Verify Lambda has correct IAM permissions:

```bash
# Check Lambda role
aws iam get-role --role-name skymarshal-api-lambda-role-dev

# Verify AgentCore Runtime ARN is correct
aws lambda get-function-configuration \
  --function-name skymarshal-api-invoke-dev \
  --query 'Environment.Variables.AGENTCORE_RUNTIME_ARN'
```

### Issue: "DynamoDB table not found"

**Solution**: Verify table was created:

```bash
aws dynamodb describe-table --table-name skymarshal-sessions-dev
```

### Issue: "401 Unauthorized"

**Solution**: Ensure AWS credentials are configured:

```bash
aws sts get-caller-identity
aws configure sso
```

## Cleanup

To remove all deployed resources:

```bash
cd infrastructure
terraform destroy \
  -var="aws_region=$AWS_REGION" \
  -var="agentcore_runtime_arn=$AGENTCORE_RUNTIME_ARN" \
  -var="environment=dev"
```

## Next Steps

1. **Configure Frontend**: Update frontend to use the API endpoint
2. **Set up Monitoring**: Configure CloudWatch alarms
3. **Production Deployment**: Deploy to production environment
4. **Rate Limiting**: Adjust rate limits based on usage
5. **Custom Domain**: Set up custom domain with Route53

## API Documentation

See [API_README.md](docs/API_README.md) for complete API documentation.

## Support

For issues:

- Check CloudWatch logs
- Review Terraform state
- Verify IAM permissions
- Contact SkyMarshal team
