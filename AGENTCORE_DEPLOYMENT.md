# SkyMarshal Arbitrator - AgentCore Deployment Guide

**Project**: SkyMarshal Multi-Agent System
**Component**: Arbitrator Agent
**Runtime**: AWS Bedrock AgentCore
**Model**: Claude Opus 4.5
**Framework**: LangGraph
**Date**: 2026-01-30

---

## Overview

This guide covers deploying the SkyMarshal Arbitrator Agent to **AWS Bedrock AgentCore Runtime**. AgentCore provides enterprise-grade infrastructure for AI agents with managed scaling, memory, tools, and observability.

### AgentCore Benefits

- ✅ **Local Development**: Test agents on localhost before cloud deployment
- ✅ **Framework Agnostic**: Full LangGraph support (current implementation)
- ✅ **CLI Deployment**: Single command deployment (`agentcore deploy`)
- ✅ **Managed Infrastructure**: Auto-scaling compute, no server management
- ✅ **Built-in Services**: Memory, code interpreter, browser, observability
- ✅ **MCP Integration**: Model Context Protocol server support
- ✅ **Simplified IAM**: Streamlined permissions model

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 AWS Bedrock AgentCore Runtime                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ AgentCore App (agentcore_arbitrator.py)                   │ │
│  │                                                            │ │
│  │  @app.entrypoint                                          │ │
│  │  def invoke_arbitrator(payload):                          │ │
│  │      ├─> LangGraph Arbitrator (agents/arbitrator_agent.py)│ │
│  │      │   ├─> Analyze Inputs                               │ │
│  │      │   ├─> Generate Scenarios                           │ │
│  │      │   ├─> Evaluate Scenarios                           │ │
│  │      │   ├─> Rank Scenarios                               │ │
│  │      │   ├─> Make Decision                                │ │
│  │      │   └─> Generate Rationale                           │ │
│  │      │                                                     │ │
│  │      └─> Return Decision + Rationale + Confidence         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ AWS Bedrock Runtime (Claude Opus 4.5)                     │ │
│  │ Model: us.anthropic.claude-opus-4-5-20251101-v1:0         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Built-in AgentCore Services:                                   │
│  ├─ Persistent Memory (conversation history)                    │
│  ├─ Code Interpreter (sandboxed execution)                      │
│  ├─ Browser Automation (cloud web access)                       │
│  ├─ OpenTelemetry Tracing (observability)                       │
│  └─ CloudWatch Metrics & Logs                                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    External API Clients
                    (boto3 bedrock-agentcore)
```

---

## Prerequisites

### 1. AWS Account Setup

- ✅ AWS account: `368613657554`
- ✅ Region: `us-east-1`
- ✅ Claude Opus 4.5 model access enabled in Bedrock Console

### 2. IAM Permissions

Required permissions for deployment and invocation:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-opus-4-5-20251101-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-opus-4-5-20251101-v1:0"
      ]
    },
    {
      "Sid": "AgentCoreManagement",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateAgent",
        "bedrock-agentcore:UpdateAgent",
        "bedrock-agentcore:DeleteAgent",
        "bedrock-agentcore:DescribeAgent",
        "bedrock-agentcore:ListAgents",
        "bedrock-agentcore:InvokeAgentRuntime"
      ],
      "Resource": [
        "arn:aws:bedrock-agentcore:us-east-1:368613657554:agent/*",
        "arn:aws:bedrock-agentcore:us-east-1:368613657554:agent-runtime/*"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:368613657554:log-group:/aws/bedrock-agentcore/*"
    },
    {
      "Sid": "ECRAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    }
  ]
}
```

### 3. Python Dependencies

```bash
# Install AgentCore SDK
pip install bedrock-agentcore

# Install LangGraph and AWS dependencies
pip install langgraph langchain-aws boto3

# Install AgentCore CLI (optional, for deployment)
pip install agentcore-cli
```

### 4. AWS CLI Configuration

```bash
aws configure --profile default
# AWS Access Key ID: [your-key]
# AWS Secret Access Key: [your-secret]
# Default region name: us-east-1
# Default output format: json
```

---

## Deployment Steps

### Step 1: Test Locally

Before deploying to AWS, test the agent locally:

```bash
# Start local AgentCore server
python3 agentcore_arbitrator.py

# In another terminal, run tests
python3 test_agentcore_local.py
```

**Expected Output**:
```
============================================================
SkyMarshal Arbitrator Agent - AgentCore Local Testing
============================================================
✅ PASSED: healthcheck
✅ PASSED: simple_prompt
✅ PASSED: full_arbitrator

🎉 All tests passed! Ready to deploy to AgentCore Runtime.
```

### Step 2: Configure Deployment

Configure AgentCore deployment settings:

```bash
agentcore configure -e agentcore_arbitrator.py

# Follow prompts:
# - Agent name: skymarshal-arbitrator
# - Region: us-east-1
# - Deployment method: CodeBuild (recommended)
# - Memory: 2048 MB
# - Timeout: 300 seconds
```

This creates a configuration file: `.agentcore/config.yaml`

### Step 3: Deploy to AgentCore Runtime

```bash
agentcore deploy

# Deployment will:
# 1. Package agent code and dependencies
# 2. Build container image (via CodeBuild or locally)
# 3. Push to ECR
# 4. Create AgentCore Runtime
# 5. Deploy agent
# 6. Create alias (production)
# 7. Return agent runtime ARN
```

**Expected Output**:
```
🚀 Deploying SkyMarshal Arbitrator to AgentCore Runtime...

✅ Packaging agent code...
✅ Building container image...
✅ Pushing to ECR...
✅ Creating AgentCore Runtime...
✅ Deploying agent...

🎉 Deployment Complete!

Agent Runtime ARN:
  arn:aws:bedrock-agentcore:us-east-1:368613657554:agent-runtime/skymarshal-arbitrator

Test with:
  python3 test_agentcore_deployment.py

Monitor logs:
  aws logs tail /aws/bedrock-agentcore/runtime/skymarshal-arbitrator --follow
```

### Step 4: Test Deployed Agent

Update `test_agentcore_deployment.py` with your agent runtime ARN:

```python
AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:368613657554:agent-runtime/skymarshal-arbitrator"
```

Run the test:

```bash
python3 test_agentcore_deployment.py
```

**Expected Output**:
```
============================================================
SkyMarshal Arbitrator - AgentCore Deployment Test
============================================================

✅ Decision Made Successfully!
   Scenario: RS-001 (Expedited Delay & Dispatch)
   Score: 75.9/100
   Confidence: 78%

🎉 AgentCore deployment test PASSED!
```

---

## Agent Files

### Core Implementation

1. **[`agents/arbitrator_agent.py`](agents/arbitrator_agent.py)**
   - LangGraph implementation
   - 6-node workflow: analyze → scenarios → evaluate → rank → decide → rationale
   - Uses Claude Opus 4.5 via ChatBedrock
   - **Status**: ✅ AgentCore-ready (no changes needed)

2. **[`agentcore_arbitrator.py`](agentcore_arbitrator.py)**
   - AgentCore entrypoint wrapper
   - Wraps LangGraph arbitrator with `BedrockAgentCoreApp`
   - Handles payload parsing and response formatting
   - Implements healthcheck endpoint
   - **Status**: ✅ Ready for deployment

### Testing Scripts

3. **[`test_agentcore_local.py`](test_agentcore_local.py)**
   - Tests agent running locally (localhost:8080)
   - 3 test cases: healthcheck, simple prompt, full disruption
   - **Usage**: Run before deployment

4. **[`test_agentcore_deployment.py`](test_agentcore_deployment.py)**
   - Tests agent deployed on AgentCore Runtime
   - Uses `boto3.client('bedrock-agentcore')`
   - **Usage**: Run after deployment

5. **[`test_opus_direct.py`](test_opus_direct.py)**
   - Tests direct Bedrock model access
   - Validates Claude Opus 4.5 availability
   - **Usage**: Troubleshooting model access

---

## Usage

### Invoking the Agent (Python)

```python
import boto3
import uuid
import json

# Initialize AgentCore client
agentcore = boto3.client('bedrock-agentcore', region_name='us-east-1')

# Prepare payload
payload = {
    "disruption_scenario": {
        "flight_number": "EY123",
        "route": "AUH → LHR",
        "issue": "Hydraulic system fault",
        "delay_hours": 3,
        "passengers": 615,
        "connections_at_risk": 87
    },
    "safety_assessments": {
        "crew_compliance": {"status": "APPROVED", "ftl_remaining": "3.5 hours"},
        "maintenance": {"status": "MEL_CATEGORY_B", "deferrable": True},
        "regulatory": {"status": "CURFEW_RISK", "latest_departure": "20:00"}
    },
    "business_proposals": {
        "network": {"priority": "HIGH", "downstream_impact": "$450K"},
        "guest_experience": {"compensation": "€125K", "satisfaction_risk": "MEDIUM"},
        "cargo": {"critical_shipments": 3, "offload_recommended": False},
        "finance": {"cancel_cost": "€1.2M", "delay_cost": "€210K"}
    }
}

# Invoke agent
response = agentcore.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:368613657554:agent-runtime/skymarshal-arbitrator",
    runtimeSessionId=str(uuid.uuid4()),
    payload=payload
)

# Parse result
result = json.loads(response['output'])

print(f"Decision: {result['decision']['scenario_id']}")
print(f"Rationale: {result['rationale']}")
print(f"Confidence: {result['confidence_score']}%")
```

### Invoking the Agent (CLI)

```bash
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn "arn:aws:bedrock-agentcore:us-east-1:368613657554:agent-runtime/skymarshal-arbitrator" \
  --runtime-session-id "$(uuidgen)" \
  --payload file://disruption_payload.json \
  --output json
```

---

## Monitoring & Observability

### CloudWatch Logs

View agent invocation logs:

```bash
# Tail logs in real-time
aws logs tail /aws/bedrock-agentcore/runtime/skymarshal-arbitrator --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/runtime/skymarshal-arbitrator \
  --filter-pattern "ERROR"

# Get last 50 log entries
aws logs tail /aws/bedrock-agentcore/runtime/skymarshal-arbitrator --since 1h
```

### CloudWatch Metrics

AgentCore automatically publishes metrics:

- `Invocations` - Total agent invocations
- `InvocationDuration` - Time per invocation
- `InvocationErrors` - Failed invocations
- `TokensConsumed` - Claude Opus 4.5 tokens used
- `ConcurrentExecutions` - Active agent instances

View in CloudWatch Console:
```
Namespace: AWS/BedrockAgentCore
Dimension: AgentName=skymarshal-arbitrator
```

### OpenTelemetry Tracing

AgentCore provides built-in distributed tracing:

```bash
# View traces in AWS X-Ray Console
# https://console.aws.amazon.com/xray/home?region=us-east-1
```

---

## Cost Estimation

### AgentCore Runtime Costs

| Component | Pricing | Monthly Est. |
|-----------|---------|--------------|
| **AgentCore Runtime** | $0.10 per hour (2GB memory) | ~$72 (24/7) |
| **Claude Opus 4.5 Input** | $15 per 1M tokens | $150 (10K tokens/invocation, 1K invocations) |
| **Claude Opus 4.5 Output** | $75 per 1M tokens | $375 (5K tokens/invocation, 1K invocations) |
| **CloudWatch Logs** | $0.50 per GB | $5 (10 GB/month) |
| **ECR Storage** | $0.10 per GB-month | $1 (10 GB image) |
| **Data Transfer** | $0.09 per GB (out) | $9 (100 GB/month) |
| **Total** | | **~$612/month** |

**Per Invocation**: ~$0.60 (at 1000 invocations/month)

**Optimization Tips**:
1. Use caching for common scenarios
2. Reduce prompt verbosity
3. Scale down during low traffic
4. Use CloudWatch Logs retention policies

---

## Troubleshooting

### Issue 1: Deployment Fails

**Error**: `Failed to create AgentCore Runtime`

**Solutions**:
1. Verify IAM permissions (ECR, AgentCore, CloudWatch)
2. Check AWS region is `us-east-1`
3. Ensure Claude Opus 4.5 model access is enabled
4. Review CodeBuild logs: `aws codebuild list-builds`

### Issue 2: Agent Invocation Fails

**Error**: `AccessDeniedException` or `ResourceNotFoundException`

**Solutions**:
1. Verify agent runtime ARN is correct
2. Check IAM permission: `bedrock-agentcore:InvokeAgentRuntime`
3. Ensure agent is deployed: `agentcore list`
4. Review CloudWatch logs for errors

### Issue 3: Local Testing Fails

**Error**: `ModuleNotFoundError: No module named 'bedrock_agentcore'`

**Solution**:
```bash
pip install bedrock-agentcore langgraph langchain-aws boto3
```

### Issue 4: Agent Returns Errors

**Error**: `error_type: ValueError` in response

**Solutions**:
1. Check payload structure matches expected format
2. Verify all required fields (disruption_scenario, safety_assessments, business_proposals)
3. Review agent logs in CloudWatch
4. Test with simple prompt first

---

## Management Commands

### List Agents

```bash
agentcore list
# or
aws bedrock-agentcore list-agents --region us-east-1
```

### Describe Agent

```bash
agentcore describe --agent skymarshal-arbitrator
# or
aws bedrock-agentcore describe-agent \
  --agent-id skymarshal-arbitrator \
  --region us-east-1
```

### Update Agent

```bash
# Make changes to agentcore_arbitrator.py or agents/arbitrator_agent.py
# Then redeploy
agentcore deploy
```

### Delete Agent

```bash
agentcore destroy --agent skymarshal-arbitrator
# or
aws bedrock-agentcore delete-agent \
  --agent-id skymarshal-arbitrator \
  --region us-east-1
```

---

## Integration with SkyMarshal System

The Arbitrator Agent integrates with the broader SkyMarshal multi-agent system:

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Safety Agents  │      │ Business Agents │      │ Execution Agent │
│                 │      │                 │      │                 │
│ • Crew          │      │ • Network       │      │ • API Gateway   │
│ • Maintenance   │──┬──▶│ • Guest Exp.    │──┬──▶│ • Action        │
│ • Regulatory    │  │   │ • Cargo         │  │   │   Executor      │
└─────────────────┘  │   │ • Finance       │  │   └─────────────────┘
                     │   └─────────────────┘  │
                     │                        │
                     ▼                        ▼
              ┌──────────────────────────────────┐
              │   Arbitrator Agent (AgentCore)   │
              │                                  │
              │  • Multi-criteria analysis       │
              │  • Scenario evaluation           │
              │  • Decision making               │
              │  • Rationale generation          │
              └──────────────────────────────────┘
```

---

## Next Steps

- ✅ Deploy arbitrator to AgentCore Runtime
- ⏳ Integrate with upstream safety/business agents
- ⏳ Implement AgentCore Memory for conversation history
- ⏳ Add AgentCore Gateway for tool integration
- ⏳ Deploy remaining agents (crew, maintenance, network, etc.)
- ⏳ Implement multi-agent orchestration
- ⏳ Set up production monitoring and alerting

---

## Documentation References

### AgentCore MCP Server

Query AgentCore documentation directly from Claude Code:
- **MCP Server**: Configured in [`.mcp/config.json`](.mcp/config.json)
- **Usage**: Ask "How do I use AgentCore Memory?" or "Show AgentCore Gateway examples"

### Official Documentation

- **AgentCore Developer Guide**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
- **AgentCore Python SDK**: https://github.com/aws/bedrock-agentcore-sdk-python
- **AgentCore Starter Toolkit**: https://github.com/aws/bedrock-agentcore-starter-toolkit
- **AgentCore Samples**: https://github.com/awslabs/amazon-bedrock-agentcore-samples
- **AgentCore MCP Server**: https://awslabs.github.io/mcp/servers/amazon-bedrock-agentcore-mcp-server

### Related Project Files

- [`CLAUDE.md`](CLAUDE.md) - Claude model integration guide
- [`agents/arbitrator_agent.py`](agents/arbitrator_agent.py) - LangGraph arbitrator implementation
- [`agentcore_arbitrator.py`](agentcore_arbitrator.py) - AgentCore entrypoint
- [`.mcp/config.json`](.mcp/config.json) - MCP server configuration
- [`DEPRECATED_BEDROCK_AGENTS.md`](DEPRECATED_BEDROCK_AGENTS.md) - Migration from old Bedrock Agents

---

**Last Updated**: 2026-01-30
**Status**: AgentCore implementation complete, ready for deployment
**Deployment Target**: AWS Bedrock AgentCore Runtime (us-east-1)
