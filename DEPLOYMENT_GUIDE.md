# SkyMarshal Deployment Guide

## Overview

This guide provides deployment instructions for the SkyMarshal multi-agent airline disruption management system, including both the backend agent system and the React frontend application.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     SkyMarshal System                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Frontend (React)          Backend (Python)                 │
│  ├─ S3 + CloudFront       ├─ AWS Bedrock AgentCore         │
│  ├─ Static Hosting        ├─ LangGraph Orchestration       │
│  └─ Global CDN            ├─ 7 Specialized Agents          │
│                           └─ DynamoDB Data Layer            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Links

- **Frontend Deployment**: See [`frontend/DEPLOYMENT.md`](frontend/DEPLOYMENT.md) for comprehensive frontend deployment guide
- **Backend Deployment**: See [`skymarshal_agents_new/skymarshal/README.md`](skymarshal_agents_new/skymarshal/README.md) for agent system setup
- **Database Setup**: See [`database/README.md`](database/README.md) for DynamoDB configuration

---

## Frontend Deployment

### Prerequisites

- Node.js 18+
- npm 9+
- AWS CLI v2
- AWS account with S3 and CloudFront permissions
- jq (JSON processor)

### Quick Start

```bash
# 1. Configure AWS credentials
aws sso login
# or
aws configure

# 2. Set up environment variables
cd frontend
cp .env.example .env
# Edit .env with your API keys

# 3. Deploy
cd ..
./deploy.sh
```

### What Gets Deployed

- **S3 Bucket**: `skymarshal-frontend-368613657554`
  - Static website hosting enabled
  - Public read access for CloudFront
  - Configured for SPA routing

- **CloudFront Distribution**:
  - Global CDN with HTTPS
  - Compression enabled
  - Custom error response for SPA routing (404 → index.html)
  - Cache optimization for static assets

### Deployment Time

- **First deployment**: 25-40 minutes (includes CloudFront propagation)
- **Subsequent deployments**: 5-10 minutes

### Access Your Application

After deployment completes, access your application at the CloudFront URL:

```
https://d1234567890abc.cloudfront.net
```

The URL is displayed in the deployment output and saved in `deploy-config.json`.

### Detailed Documentation

For comprehensive deployment instructions, troubleshooting, and advanced topics, see:

**📖 [Frontend Deployment Guide](frontend/DEPLOYMENT.md)**

This guide includes:

- Detailed prerequisites and setup
- Step-by-step deployment process
- Environment variable configuration
- Troubleshooting common issues
- Advanced topics (custom domains, CI/CD, monitoring)
- Security best practices
- Performance optimization

---

## Backend Deployment

### Prerequisites

- Python 3.11+
- UV package manager
- AWS Bedrock access
- DynamoDB tables configured

### Quick Start

```bash
# 1. Navigate to agent system
cd skymarshal_agents_new/skymarshal

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env with AWS credentials and configuration

# 4. Deploy to AgentCore
uv run agentcore deploy
```

### What Gets Deployed

- **AgentCore Runtime**: Serverless agent execution environment
- **7 Specialized Agents**:
  - Crew Compliance Agent
  - Maintenance Agent
  - Regulatory Agent
  - Network Agent
  - Guest Experience Agent
  - Cargo Agent
  - Finance Agent
- **Orchestrator**: LangGraph-based multi-agent coordinator
- **DynamoDB Integration**: Real-time operational data access

### Testing Deployment

```bash
# Test locally
uv run agentcore invoke --dev "Flight EY123 delayed 3 hours due to mechanical issue"

# Test deployed version
uv run agentcore invoke "Flight EY123 delayed 3 hours due to mechanical issue"

# View logs
uv run agentcore logs
```

---

## Database Setup

### DynamoDB Tables

The system requires the following DynamoDB tables:

1. **flights** - Flight schedules and status
2. **passengers** - Passenger information
3. **bookings** - Flight reservations
4. **crew_members** - Crew roster
5. **crew_roster** - Crew assignments
6. **cargo_shipments** - Cargo tracking
7. **aircraft_types** - Aircraft configurations
8. **airports** - Airport master data

### Create Tables

```bash
cd database
python3 create_dynamodb_tables.py
```

### Import Sample Data

```bash
# Generate synthetic data
python3 generate_data.py

# Import to DynamoDB
python3 import_csv_to_dynamodb.py
```

### Verify Tables

```bash
# List tables
aws dynamodb list-tables --region us-east-1

# Check table status
aws dynamodb describe-table --table-name flights --region us-east-1
```

---

## Environment Configuration

### Frontend Environment Variables

Create `frontend/.env`:

```bash
# Required: Gemini API Key
VITE_GEMINI_API_KEY=your_gemini_api_key_here
```

### Backend Environment Variables

Create `skymarshal_agents_new/skymarshal/.env`:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=default

# Bedrock Configuration
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# DynamoDB Configuration
DYNAMODB_ENDPOINT=https://dynamodb.us-east-1.amazonaws.com

# MCP Gateway (if using)
MCP_GATEWAY_URL=https://your-mcp-gateway-url
```

---

## Deployment Verification

### Frontend Verification

```bash
# Test main page
curl -I https://your-cloudfront-domain.cloudfront.net

# Test SPA routing
curl -I https://your-cloudfront-domain.cloudfront.net/dashboard

# Expected: HTTP/2 200 for both
```

### Backend Verification

```bash
cd skymarshal_agents_new/skymarshal

# Check AgentCore status
uv run agentcore status

# Test agent invocation
uv run agentcore invoke "Test disruption scenario"

# View recent logs
uv run agentcore logs --tail 50
```

### Database Verification

```bash
# Check table item counts
aws dynamodb scan --table-name flights --select COUNT --region us-east-1

# Query sample data
aws dynamodb get-item \
  --table-name flights \
  --key '{"flight_id": {"S": "FLT-001"}}' \
  --region us-east-1
```

---

## Monitoring and Logging

### Frontend Monitoring

- **CloudFront Metrics**: AWS Console → CloudFront → Monitoring
- **S3 Access Logs**: Enable in S3 bucket settings
- **CloudWatch Alarms**: Set up for error rates and latency

### Backend Monitoring

- **AgentCore Logs**: `uv run agentcore logs`
- **CloudWatch Logs**: `/aws/bedrock-agentcore/runtime/skymarshal`
- **DynamoDB Metrics**: AWS Console → DynamoDB → Metrics

### Key Metrics to Monitor

1. **Frontend**:
   - CloudFront cache hit ratio (target: >80%)
   - 4xx/5xx error rates (target: <1%)
   - Origin response time (target: <500ms)

2. **Backend**:
   - Agent execution time (target: <30s)
   - DynamoDB read/write capacity
   - Bedrock API latency

---

## Troubleshooting

### Frontend Issues

See detailed troubleshooting in [`frontend/DEPLOYMENT.md`](frontend/DEPLOYMENT.md#troubleshooting)

Common issues:

- AWS authentication failures → Run `aws sso login`
- Missing environment variables → Check `frontend/.env`
- Build failures → Run `npm install` and `npm run build`
- Stale content → Create CloudFront invalidation

### Backend Issues

Common issues:

- AgentCore deployment fails → Check AWS Bedrock permissions
- Agent timeouts → Increase timeout in `.bedrock_agentcore.yaml`
- DynamoDB access errors → Verify IAM role permissions
- Model access denied → Request Bedrock model access in AWS Console

### Database Issues

Common issues:

- Table not found → Run `create_dynamodb_tables.py`
- Insufficient capacity → Increase provisioned capacity or use on-demand
- Access denied → Check IAM permissions for DynamoDB

---

## Cost Estimation

### Frontend Costs (Monthly)

- **S3 Storage**: ~$0.50 (20 GB)
- **S3 Requests**: ~$0.40 (100K requests)
- **CloudFront**: ~$8.50 (100 GB transfer)
- **Total**: ~$10/month for moderate traffic

### Backend Costs (Monthly)

- **AgentCore Runtime**: Pay per invocation
- **Bedrock API**: ~$0.015 per 1K input tokens, ~$0.075 per 1K output tokens
- **DynamoDB**: ~$1.25 per million read requests (on-demand)
- **Estimated**: $50-200/month depending on usage

### Cost Optimization Tips

1. **Frontend**:
   - Use appropriate cache TTLs
   - Enable compression
   - Limit CloudFront edge locations if needed

2. **Backend**:
   - Use efficient prompts to reduce token usage
   - Implement caching for repeated queries
   - Use DynamoDB on-demand pricing for variable workloads

---

## Security Best Practices

### Frontend Security

- ✅ HTTPS only (CloudFront enforces)
- ✅ API keys restricted to specific domains
- ✅ No sensitive data in client code
- ✅ Regular dependency updates (`npm audit`)

### Backend Security

- ✅ IAM roles with least privilege
- ✅ Secrets in AWS Secrets Manager
- ✅ VPC endpoints for DynamoDB (optional)
- ✅ CloudTrail logging enabled

### Database Security

- ✅ Encryption at rest (DynamoDB default)
- ✅ Encryption in transit (TLS)
- ✅ Fine-grained access control (IAM)
- ✅ Backup and point-in-time recovery enabled

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy SkyMarshal
on:
  push:
    branches: [main]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: "18"
      - name: Deploy Frontend
        run: |
          cd frontend
          npm ci
          npm run build
        env:
          VITE_GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Deploy to AWS
        run: ./deploy.sh prod

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Deploy AgentCore
        run: |
          cd skymarshal_agents_new/skymarshal
          uv sync
          uv run agentcore deploy
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
```

---

## Rollback Procedures

### Frontend Rollback

```bash
# Option 1: Redeploy previous version
git checkout <previous-commit>
./deploy.sh

# Option 2: Restore from S3 versioning (if enabled)
aws s3api list-object-versions --bucket skymarshal-frontend-368613657554

# Option 3: Manual file restoration
aws s3 cp s3://backup-bucket/dist/ s3://skymarshal-frontend-368613657554/ --recursive
```

### Backend Rollback

```bash
cd skymarshal_agents_new/skymarshal

# Redeploy previous version
git checkout <previous-commit>
uv run agentcore deploy

# Or use AgentCore versioning
uv run agentcore rollback --version <version-id>
```

---

## Support and Resources

### Documentation

- **Frontend Deployment**: [`frontend/DEPLOYMENT.md`](frontend/DEPLOYMENT.md)
- **Agent System**: [`skymarshal_agents_new/skymarshal/README.md`](skymarshal_agents_new/skymarshal/README.md)
- **AWS Bedrock AgentCore**: [Official Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- **LangGraph**: [Official Documentation](https://langchain-ai.github.io/langgraph/)

### AWS Resources

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [AWS DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)

### Getting Help

1. Check troubleshooting sections in documentation
2. Review AWS CloudWatch logs
3. Check AWS Service Health Dashboard
4. Contact AWS Support (if you have a support plan)

---

## Quick Reference

### Essential Commands

```bash
# Frontend
./deploy.sh                                    # Deploy frontend
aws cloudfront create-invalidation ...         # Clear cache

# Backend
cd skymarshal_agents_new/skymarshal
uv run agentcore deploy                        # Deploy agents
uv run agentcore invoke "test"                 # Test deployment
uv run agentcore logs                          # View logs

# Database
cd database
python3 create_dynamodb_tables.py              # Create tables
aws dynamodb scan --table-name flights ...     # Query data
```

### Important URLs

- **Frontend**: `https://<cloudfront-domain>.cloudfront.net`
- **AWS Console**: `https://console.aws.amazon.com/`
- **CloudFront Console**: `https://console.aws.amazon.com/cloudfront/`
- **DynamoDB Console**: `https://console.aws.amazon.com/dynamodb/`

---

**Last Updated**: January 2024  
**Version**: 1.0.0  
**Project**: SkyMarshal Multi-Agent Disruption Management System
