# ⚠️ DEPRECATED: Bedrock Agents Deployment

**This document describes the old AWS Bedrock Agents implementation.**
**Status**: DEPRECATED - Migrated to AWS Bedrock AgentCore

---

## 🔄 Migration Notice

This deployment approach has been **replaced with AWS Bedrock AgentCore**.

**New Documentation**: See [`AGENTCORE_DEPLOYMENT.md`](AGENTCORE_DEPLOYMENT.md)

**Why AgentCore?**
- ✅ Local testing before deployment
- ✅ Simplified deployment (`agentcore deploy`)
- ✅ Better IAM permissions model
- ✅ Full LangGraph support
- ✅ Built-in memory, tools, observability

**Migration Guide**: See [`DEPRECATED_BEDROCK_AGENTS.md`](DEPRECATED_BEDROCK_AGENTS.md)

---

# SkyMarshal Arbitrator Agent - Deployment Status (ARCHIVED)

**Date**: 2026-01-30 (Archived)
**Agent**: Arbitrator (Multi-criteria Decision Maker)
**Model**: Claude Opus 4.5 (us.anthropic.claude-opus-4-5-20251101-v1:0)
**Framework**: LangGraph + AWS Bedrock Agents (OLD)
**Status**: ⚠️ Deployed but invocation blocked by permissions (ARCHIVED)

---

## ✅ Completed Work

### 1. Local LangGraph Implementation

**File**: [`agents/arbitrator_agent.py`](agents/arbitrator_agent.py)

- Full LangGraph StateGraph implementation with 6 workflow nodes:
  1. `analyze_inputs` - Analyzes disruption, safety, and business inputs
  2. `generate_scenarios` - Creates 3-5 viable recovery scenarios
  3. `evaluate_scenarios` - Scores scenarios against decision criteria
  4. `rank_scenarios` - Calculates weighted scores
  5. `make_decision` - Selects optimal scenario
  6. `generate_rationale` - Creates comprehensive decision rationale

- Multi-criteria decision making with weighted scoring:
  - Safety: 40% (zero tolerance for violations)
  - Cost: 25% (minimize financial impact)
  - Passengers: 20% (customer satisfaction)
  - Network: 10% (minimize cascade effects)
  - Reputation: 5% (brand protection)

- Successfully tested locally with Claude Opus 4.5 via ChatBedrock
- Test result: Generated decision for EY123 hydraulic fault scenario
- Decision: "RS-001 (Expedited Delay & Dispatch)" with 75.9/100 score, 78% confidence

### 2. AWS Bedrock Agent Deployment

**Agent ID**: `GBMIHM7VP0`
**Agent ARN**: `arn:aws:bedrock:us-east-1:368613657554:agent/GBMIHM7VP0`
**Alias ID**: `LILSPKYY1S` (production)
**Alias ARN**: `arn:aws:bedrock:us-east-1:368613657554:agent-alias/GBMIHM7VP0/LILSPKYY1S`
**Status**: PREPARED

- Created Bedrock Agent via boto3:
  - Agent name: `skymarshal-arbitrator`
  - Foundation model: Claude Opus 4.5
  - IAM role: `arn:aws:iam::368613657554:role/skymarshal-bedrock-agent-role`
  - Description: "SkyMarshal Arbitrator - Multi-criteria decision maker using Claude Opus 4.5"

- Created production alias for the agent
- Agent successfully prepared and ready in Bedrock console

### 3. IAM Permissions Updated

**IAM Role**: `skymarshal-bedrock-agent-role`
**Policy**: `skymarshal-bedrock-agent-policy`

Permissions added:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/us.amazon.nova-premier-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-opus-4-5-20251101-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-opus-4-5-20251101-v1:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::skymarshal-prod-*",
        "arn:aws:s3:::skymarshal-prod-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:368613657554:log-group:/aws/bedrock/*"
    }
  ]
}
```

Trust policy allows `bedrock.amazonaws.com` to assume the role.

### 4. Test Scripts Created

1. **[`deploy_arbitrator.py`](deploy_arbitrator.py)** - Deploy agent to Bedrock
2. **[`test_arbitrator_invocation.py`](test_arbitrator_invocation.py)** - Test agent invocation
3. **[`check_agent_status.py`](check_agent_status.py)** - Check agent status
4. **[`create_agent_alias.py`](create_agent_alias.py)** - Create production alias
5. **[`prepare_agent.py`](prepare_agent.py)** - Prepare agent after updates
6. **[`test_opus_direct.py`](test_opus_direct.py)** - Test direct model invocation
7. **[`update_agent_model.py`](update_agent_model.py)** - Switch agent models

### 5. Verification Tests

✅ Claude Opus 4.5 is accessible in Bedrock (tested via `converse` API)
✅ Local Arbitrator agent works with LangGraph
✅ Agent created successfully in Bedrock
✅ Agent alias created successfully
✅ Agent prepared and in PREPARED status
✅ IAM role has InvokeModel permissions for Claude Opus 4.5
✅ Trust policy allows Bedrock service to assume role

---

## ⚠️ Current Blocker

### Error: Agent Invocation Access Denied

**Error Message**:
```
An error occurred (accessDeniedException) when calling the InvokeAgent operation:
Access denied when calling Bedrock. Check your request permissions and retry the request.
```

**What We've Tried**:

1. ✅ Added Claude Opus 4.5 to IAM policy (`us.anthropic.claude-opus-4-5-20251101-v1:0`)
2. ✅ Added base model ARN (`anthropic.claude-opus-4-5-20251101-v1:0`)
3. ✅ Prepared agent after each IAM policy update
4. ✅ Tested with Nova Premier (same error - not model-specific)
5. ✅ Verified direct model invocation works
6. ✅ Verified IAM trust policy is correct

**What Doesn't Work**:
- Invoking the agent via `bedrock-agent-runtime:invoke_agent`
- Error occurs when agent tries to call the foundation model
- Happens with both Claude Opus 4.5 and Nova Premier

**Possible Causes**:

1. **Missing Agent-Specific Permission**: May need additional permissions like:
   - `bedrock:RetrieveAndGenerate`
   - `bedrock:Retrieve`
   - Agent-specific IAM actions

2. **Resource-Based Policy**: The agent itself may need a resource-based policy

3. **KMS/Encryption**: If Bedrock uses KMS encryption, may need KMS permissions

4. **Service Role Propagation**: IAM changes may not have propagated to the agent yet (can take up to 10 minutes)

5. **Regional Inference Profile**: The `us.` prefix in model ID might require different permissions

6. **Agent Logging Not Enabled**: May need to explicitly configure agent logging

---

## 🔍 Debugging Steps

### Check CloudWatch Logs

```bash
aws logs tail /aws/bedrock/agents/skymarshal --since 5m --follow
```

Currently no logs appearing (agent may not be reaching execution stage).

### Verify IAM Policy

```bash
aws iam get-role-policy \
  --role-name skymarshal-bedrock-agent-role \
  --policy-name skymarshal-bedrock-agent-policy
```

### Test Agent Invocation

```bash
python3 test_arbitrator_invocation.py
```

### Direct Model Test (Works)

```bash
python3 test_opus_direct.py
```

---

## 📋 Deployment Files

| File | Purpose |
|------|---------|
| [`agents/arbitrator_agent.py`](agents/arbitrator_agent.py) | LangGraph implementation |
| [`deploy_arbitrator.py`](deploy_arbitrator.py) | Deploy to Bedrock |
| [`test_arbitrator_invocation.py`](test_arbitrator_invocation.py) | Test invocation |
| [`arbitrator_deployment.json`](arbitrator_deployment.json) | Deployment metadata |
| [`terraform/deploy-simple.tf`](terraform/deploy-simple.tf) | Infrastructure as code |

---

## 🎯 Next Steps

### Option 1: Use MCP Server (Recommended)

The MCP server (already installed) might handle agent invocations differently:

```bash
# Use MCP server to invoke agent
python3 -c "
from mcp import ClientSession
client = ClientSession(config_path='.mcp/config.json')
result = client.call_tool('invoke_agent', {
    'agentId': 'GBMIHM7VP0',
    'agentAliasId': 'LILSPKYY1S',
    'sessionId': 'test-session-001',
    'inputText': 'Analyze disruption'
})
print(result)
"
```

### Option 2: Add Broader Permissions

Temporarily add wildcard permissions to isolate the issue:

```json
{
  "Effect": "Allow",
  "Action": "bedrock:*",
  "Resource": "*"
}
```

### Option 3: Use Direct Bedrock Runtime

Instead of Bedrock Agents, use direct Bedrock Runtime API:
- Keep the LangGraph implementation in [`agents/arbitrator_agent.py`](agents/arbitrator_agent.py)
- Invoke via `bedrock-runtime` instead of `bedrock-agent-runtime`
- This avoids the agent invocation layer

### Option 4: Check AWS Support Documentation

Look for specific Bedrock Agents IAM requirements:
- https://docs.aws.amazon.com/bedrock/latest/userguide/agents-permissions.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_troubleshoot.html

### Option 5: Wait for IAM Propagation

IAM policy changes can take up to 10 minutes to propagate. Try again after waiting.

---

## 📊 Summary

### What Works

✅ LangGraph agent implementation with Claude Opus 4.5
✅ Local testing via ChatBedrock
✅ Direct model invocation via Bedrock Runtime
✅ Agent creation and preparation in Bedrock
✅ IAM role and trust policy configuration
✅ Terraform infrastructure deployment

### What Doesn't Work

❌ Agent invocation via `bedrock-agent-runtime:invoke_agent`
❌ Access denied error when agent tries to call foundation model

### Impact

- Agent is deployed and ready in Bedrock
- Cannot be invoked due to permissions issue
- Local LangGraph implementation works fine
- Can proceed with other agents while troubleshooting this one

---

## 🛠️ Workaround

Until the invocation issue is resolved, the Arbitrator agent can be used locally:

```python
from agents.arbitrator_agent import create_arbitrator_agent

arbitrator = create_arbitrator_agent()

result = arbitrator.invoke(
    disruption_scenario={...},
    safety_assessments={...},
    business_proposals={...}
)

print(result['decision'])
print(result['rationale'])
```

This provides the same decision-making logic without requiring Bedrock Agents.

---

## 📞 AWS Console Links

- **Agent**: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agents/GBMIHM7VP0
- **IAM Role**: https://console.aws.amazon.com/iam/home?region=us-east-1#/roles/skymarshal-bedrock-agent-role
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Fbedrock$252Fagents$252Fskymarshal

---

**Status**: Agent deployed and prepared, invocation blocked by permissions
**Recommendation**: Use local LangGraph implementation or try MCP server approach
**Estimated Time to Resolve**: 15-30 minutes with proper AWS IAM documentation
