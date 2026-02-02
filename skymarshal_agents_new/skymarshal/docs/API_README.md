# SkyMarshal AgentCore REST API

REST API for invoking the SkyMarshal AgentCore Runtime agent via HTTP endpoints.

## Quick Start

### Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured with SSO credentials
- AgentCore Runtime deployed (see main README)

### Authentication

The API uses AWS Signature Version 4 authentication. Configure your AWS credentials:

```bash
aws configure sso
# or
export AWS_PROFILE=your-profile
```

### API Endpoints

**Base URL**: `https://your-api-id.execute-api.us-east-1.amazonaws.com/dev/api/v1`

- `POST /invoke` - Invoke the SkyMarshal agent
- `GET /health` - Health check (no auth required)

## Usage Examples

### Basic Invocation

```bash
# Using AWS CLI to sign the request
aws apigatewayv2 invoke \
  --api-id YOUR_API_ID \
  --stage dev \
  --path /api/v1/invoke \
  --body '{"prompt":"Flight AA123 delayed 3 hours due to weather"}' \
  response.json
```

### Using curl with AWS Signature

```bash
# Install awscurl: pip install awscurl
awscurl --service execute-api \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Flight AA123 delayed 3 hours due to weather"}' \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
```

### Multi-turn Conversation

```bash
# First request - creates session
awscurl --service execute-api \
  -X POST \
  -d '{"prompt":"Flight AA123 delayed 3 hours"}' \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke

# Response includes session_id
# Use it in subsequent requests
awscurl --service execute-api \
  -X POST \
  -d '{"prompt":"What are the passenger impacts?","session_id":"550e8400-e29b-41d4-a716-446655440000"}' \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
```

### Health Check

```bash
curl https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/health
```

## Request Format

### POST /invoke

```json
{
  "prompt": "Flight AA123 delayed 3 hours due to weather",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "streaming": false
}
```

**Fields:**

- `prompt` (required): Disruption description (10-10000 characters)
- `session_id` (optional): UUID v4 for multi-turn conversations
- `streaming` (optional): Enable streaming responses (default: false)

## Response Format

### Success Response

```json
{
  "status": "success",
  "request_id": "660e8400-e29b-41d4-a716-446655440000",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "execution_time_ms": 5234,
  "timestamp": "2024-01-15T10:30:45.123Z",
  "assessment": {
    "safety_phase": {...},
    "business_phase": {...},
    "final_decision": "approved",
    "recommendations": [...]
  }
}
```

### Error Response

```json
{
  "status": "error",
  "request_id": "660e8400-e29b-41d4-a716-446655440000",
  "error_code": "TIMEOUT",
  "error_message": "Agent execution exceeded 5 minute timeout",
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

## Error Codes

| Code                | Status | Description                            |
| ------------------- | ------ | -------------------------------------- |
| `INVALID_REQUEST`   | 400    | Missing or invalid request fields      |
| `INVALID_JSON`      | 400    | Request body is not valid JSON         |
| `UNAUTHORIZED`      | 401    | Missing or invalid AWS credentials     |
| `FORBIDDEN`         | 403    | Insufficient permissions               |
| `CONNECTION_FAILED` | 502    | Failed to connect to AgentCore Runtime |
| `TIMEOUT`           | 504    | Request exceeded 5 minute timeout      |
| `INTERNAL_ERROR`    | 500    | Unexpected server error                |

## Rate Limits

- **Rate**: 100 requests per minute per client
- **Burst**: 200 requests
- **Concurrent**: 10 concurrent executions

When rate limit is exceeded, the API returns `429 Too Many Requests` with a `Retry-After` header.

## Troubleshooting

### Authentication Errors

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check IAM permissions
aws iam get-user
```

### Connection Timeouts

- Check AgentCore Runtime is deployed and healthy
- Verify Lambda function has correct IAM permissions
- Check CloudWatch logs for detailed errors

### View Logs

```bash
# Lambda invocation logs
aws logs tail /aws/lambda/skymarshal-api-invoke-dev --follow

# API Gateway logs
aws logs tail /aws/apigateway/skymarshal-api-dev --follow
```

## Deployment

See [deployment guide](../scripts/deploy_api.sh) for infrastructure setup.

```bash
# Deploy API
export AGENTCORE_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/skymarshal"
./scripts/deploy_api.sh dev
```

## OpenAPI Specification

Full API specification available at [openapi.yaml](./openapi.yaml)

## Support

For issues and questions:

- Check CloudWatch logs
- Review [main documentation](../README.md)
- Contact SkyMarshal team
