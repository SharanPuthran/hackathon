# 🚀 Deploy Your AgentCore REST API

## All Tasks Complete! ✅

All 16 implementation tasks have been completed successfully. Your REST API is ready to deploy.

## Your AgentCore Runtime

**Runtime ARN**:

```
arn:aws:bedrock-agentcore:us-east-1:368613657554:runtime/skymarshal_Agent-cn8OdHGjgz
```

## Deploy Now (3 Simple Steps)

### Step 1: Set Environment Variable

```bash
export AGENTCORE_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-east-1:368613657554:runtime/skymarshal_Agent-cn8OdHGjgz"
```

### Step 2: Run Deployment Script

```bash
cd skymarshal_agents_new/skymarshal
./scripts/deploy_api.sh dev
```

This will:

- ✅ Package Lambda functions
- ✅ Deploy infrastructure with Terraform
- ✅ Create DynamoDB table
- ✅ Set up API Gateway
- ✅ Configure IAM roles
- ✅ Output your API endpoint URLs

### Step 3: Get Your API Endpoint

After deployment completes, you'll see:

```
═══════════════════════════════════════════════════════════
API Endpoints:
═══════════════════════════════════════════════════════════
Base URL:    https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1
Invoke:      https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
Health:      https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/health
═══════════════════════════════════════════════════════════
```

## Test Your API

### 1. Test Health Endpoint (No Auth Required)

```bash
curl https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "dependencies": {
    "dynamodb": "healthy",
    "agentcore": "healthy"
  }
}
```

### 2. Invoke the Agent (Requires AWS Auth)

First, install awscurl:

```bash
pip install awscurl
```

Then invoke:

```bash
awscurl --service execute-api \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Flight AA123 delayed 3 hours due to weather"}' \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
```

### 3. Multi-turn Conversation

```bash
# First request - creates session
awscurl --service execute-api \
  -X POST \
  -d '{"prompt":"Flight AA123 delayed 3 hours"}' \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke

# Use the session_id from response in next request
awscurl --service execute-api \
  -X POST \
  -d '{"prompt":"What are the passenger impacts?","session_id":"YOUR_SESSION_ID"}' \
  https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
```

## What You Get

### API Features

- ✅ HTTP POST endpoint for agent invocation
- ✅ AWS IAM authentication (Signature V4)
- ✅ Session management for conversations
- ✅ Request validation and sanitization
- ✅ Automatic retries with exponential backoff
- ✅ 5-minute timeout protection
- ✅ Rate limiting (100 requests/minute)
- ✅ CORS support
- ✅ Health check endpoint

### Infrastructure

- ✅ API Gateway REST API
- ✅ Lambda functions (Python 3.11)
- ✅ DynamoDB table for sessions
- ✅ IAM roles with least privilege
- ✅ CloudWatch logging
- ✅ Terraform managed

### Documentation

- ✅ OpenAPI 3.0 specification
- ✅ Complete API usage guide
- ✅ Deployment guide
- ✅ Example requests/responses

## View Logs

```bash
# Lambda invocation logs
aws logs tail /aws/lambda/skymarshal-api-invoke-dev --follow

# Health check logs
aws logs tail /aws/lambda/skymarshal-api-health-dev --follow
```

## Troubleshooting

### Issue: Terraform not installed

```bash
# macOS
brew install terraform

# Or download from: https://www.terraform.io/downloads
```

### Issue: AWS credentials not configured

```bash
aws configure sso
# or
aws configure
```

### Issue: Permission denied on scripts

```bash
chmod +x scripts/*.sh
```

## Documentation

- **API Usage**: [docs/API_README.md](docs/API_README.md)
- **Deployment Guide**: [API_DEPLOYMENT_GUIDE.md](API_DEPLOYMENT_GUIDE.md)
- **OpenAPI Spec**: [docs/openapi.yaml](docs/openapi.yaml)
- **Implementation Details**: [API_IMPLEMENTATION_COMPLETE.md](API_IMPLEMENTATION_COMPLETE.md)

## Architecture

```
External App → API Gateway → Lambda → AgentCore Runtime → SkyMarshal Agents
                    ↓
                DynamoDB (Sessions)
```

## Next Steps After Deployment

1. **Integrate with Frontend**: Update your React app to use the API endpoint
2. **Set up Monitoring**: Configure CloudWatch alarms
3. **Production Deploy**: Run `./scripts/deploy_api.sh prod`
4. **Custom Domain**: Set up Route53 custom domain
5. **Rate Limits**: Adjust based on usage patterns

## Support

Need help?

- Check [API_DEPLOYMENT_GUIDE.md](API_DEPLOYMENT_GUIDE.md)
- Review CloudWatch logs
- Verify IAM permissions
- Check Terraform state

---

**Ready to deploy?** Run the commands above! 🚀
