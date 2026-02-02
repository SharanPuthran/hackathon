# SkyMarshal API - Quick Reference Card

## 🌐 API Endpoints

```
Base URL: https://82gmbnz8x1.execute-api.us-east-1.amazonaws.com/dev/api/v1

Health:   GET  /health  (no auth)
Invoke:   POST /invoke  (AWS IAM auth required)
```

## 🔑 Authentication

**Method**: AWS Signature Version 4

**Using awscurl**:

```bash
pip install awscurl

awscurl --service execute-api \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Your prompt here"}' \
  https://82gmbnz8x1.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
```

## 📝 Request Format

```json
{
  "prompt": "Flight AA123 delayed 3 hours due to weather",
  "session_id": "optional-uuid-for-multi-turn"
}
```

## 📤 Response Format

```json
{
  "status": "success",
  "request_id": "uuid",
  "session_id": "uuid",
  "execution_time_ms": 5234,
  "timestamp": "2026-02-02T...",
  "assessment": {
    "safety_phase": { ... },
    "business_phase": { ... },
    "final_decision": "approved",
    "recommendations": [ ... ]
  }
}
```

## 🚦 Rate Limits

- **Rate**: 100 requests/second
- **Burst**: 200 requests
- **Timeout**: 5 minutes per request

## 📊 Monitoring

**CloudWatch Logs**:

```bash
# AgentCore logs
aws logs tail /aws/bedrock-agentcore/runtimes/skymarshal_Agent-cn8OdHGjgz-DEFAULT --follow

# Lambda logs
aws logs tail /aws/lambda/skymarshal-api-invoke-dev --follow
```

**Dashboard**:

```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core
```

## 🔧 Common Commands

**Test Health**:

```bash
curl https://82gmbnz8x1.execute-api.us-east-1.amazonaws.com/dev/api/v1/health
```

**Invoke Agent**:

```bash
awscurl --service execute-api \
  -X POST \
  -d '{"prompt":"Flight delayed"}' \
  https://82gmbnz8x1.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke
```

**Deploy Updates**:

```bash
cd skymarshal_agents_new/skymarshal
uv run agentcore deploy
```

**View Status**:

```bash
uv run agentcore status
```

## 🆘 Troubleshooting

| Issue                   | Solution                                             |
| ----------------------- | ---------------------------------------------------- |
| 401 Unauthorized        | Check AWS credentials: `aws sts get-caller-identity` |
| 504 Timeout             | Check Lambda logs for errors                         |
| 429 Too Many Requests   | Reduce request rate or increase limits               |
| 503 Service Unavailable | Check AgentCore Runtime status                       |

## 📚 Documentation

- **Full Guide**: `API_DEPLOYMENT_GUIDE.md`
- **OpenAPI Spec**: `docs/openapi.yaml`
- **Complete Summary**: `COMPLETE_DEPLOYMENT_SUMMARY.md`

## 🔗 Resources

**Agent ARN**:

```
arn:aws:bedrock-agentcore:us-east-1:368613657554:runtime/skymarshal_Agent-cn8OdHGjgz
```

**DynamoDB Table**:

```
skymarshal-sessions-dev
```

**Lambda Functions**:

```
skymarshal-api-invoke-dev
skymarshal-api-health-dev
```

**IAM Role**:

```
skymarshal-api-lambda-role-dev
```

---

**Status**: ✅ OPERATIONAL  
**Region**: us-east-1  
**Environment**: dev
