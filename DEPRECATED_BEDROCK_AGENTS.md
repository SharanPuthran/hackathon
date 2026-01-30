# DEPRECATED: Bedrock Agents Files

**Date**: 2026-01-30
**Status**: DEPRECATED - Migrated to Bedrock AgentCore

---

## Migration Notice

The following files were part of the old AWS Bedrock Agents implementation and have been **deprecated** in favor of AWS Bedrock AgentCore Runtime.

### Why AgentCore?

AWS Bedrock AgentCore provides:
- ✅ **Local Development**: Test agents before deployment
- ✅ **Framework Agnostic**: Full LangGraph, Strands, CrewAI support
- ✅ **Simplified Deployment**: Single CLI command (`agentcore deploy`)
- ✅ **Managed Infrastructure**: Auto-scaling, memory, tools, observability
- ✅ **Better Permissions**: Simplified IAM model
- ✅ **MCP Integration**: Model Context Protocol server support

---

## Deprecated Files

### 1. Agent Management Scripts

#### [`deploy_arbitrator.py`](deploy_arbitrator.py)
**Status**: ❌ DEPRECATED
**Replaced By**: [`agentcore_arbitrator.py`](agentcore_arbitrator.py) + `agentcore deploy`

**Old Approach**:
```bash
python3 deploy_arbitrator.py
```

**New Approach**:
```bash
# Configure
agentcore configure -e agentcore_arbitrator.py

# Deploy
agentcore deploy
```

---

#### [`check_agent_status.py`](check_agent_status.py)
**Status**: ❌ DEPRECATED
**Replaced By**: `agentcore list` and `agentcore describe`

**Old Approach**:
```bash
python3 check_agent_status.py
```

**New Approach**:
```bash
# List all agents
agentcore list

# Get agent details
agentcore describe --agent skymarshal-arbitrator
```

---

#### [`create_agent_alias.py`](create_agent_alias.py)
**Status**: ❌ DEPRECATED
**Replaced By**: AgentCore automatic versioning

**Note**: AgentCore handles versioning and aliasing automatically during deployment.

---

#### [`prepare_agent.py`](prepare_agent.py)
**Status**: ❌ DEPRECATED
**Replaced By**: AgentCore automatic preparation

**Note**: AgentCore automatically prepares agents during `agentcore deploy`.

---

#### [`update_agent_model.py`](update_agent_model.py)
**Status**: ❌ DEPRECATED
**Replaced By**: Update model in agent code + `agentcore deploy`

**New Approach**:
1. Update model ID in `agentcore_arbitrator.py`
2. Run `agentcore deploy` to redeploy

---

### 2. Testing Scripts

#### [`test_arbitrator_invocation.py`](test_arbitrator_invocation.py)
**Status**: ❌ DEPRECATED
**Replaced By**: [`test_agentcore_deployment.py`](test_agentcore_deployment.py)

**Old Approach**:
```python
import boto3
bedrock_runtime = boto3.client('bedrock-agent-runtime')
response = bedrock_runtime.invoke_agent(...)
```

**New Approach**:
```python
import boto3
agentcore_client = boto3.client('bedrock-agentcore')
response = agentcore_client.invoke_agent_runtime(...)
```

---

#### [`test_mcp_tools.py`](test_mcp_tools.py)
**Status**: ⚠️ PARTIALLY DEPRECATED
**Replaced By**: AgentCore MCP Server

**Note**: Some MCP tools still work, but the underlying agent management APIs are deprecated. Use the new AgentCore MCP server configured in [`.mcp/config.json`](.mcp/config.json).

---

### 3. Configuration Files

#### [`arbitrator_deployment.json`](arbitrator_deployment.json)
**Status**: ⚠️ ARCHIVED
**Purpose**: Historical record of old Bedrock Agents deployment

**Content**:
- Old Agent ID: GBMIHM7VP0
- Old Agent ARN: `arn:aws:bedrock:us-east-1:368613657554:agent/GBMIHM7VP0`
- Old Alias ID: LILSPKYY1S

**Note**: Keep for reference but do not use for new deployments.

---

## Migration Path

### For Developers

If you have code using the old Bedrock Agents SDK:

**OLD CODE** (boto3 bedrock-agent):
```python
import boto3

bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
agent = bedrock_agent.create_agent(
    agentName="skymarshal-arbitrator",
    foundationModel="us.anthropic.claude-opus-4-5-20251101-v1:0",
    instruction="...",
    agentResourceRoleArn="arn:aws:iam::..."
)

bedrock_runtime = boto3.client('bedrock-agent-runtime')
response = bedrock_runtime.invoke_agent(
    agentId=agent_id,
    agentAliasId=alias_id,
    sessionId=session_id,
    inputText="..."
)
```

**NEW CODE** (AgentCore SDK):
```python
from bedrock_agentcore import BedrockAgentCoreApp
from agents.arbitrator_agent import create_arbitrator_agent

app = BedrockAgentCoreApp()
arbitrator = create_arbitrator_agent()

@app.entrypoint
def invoke(payload):
    result = arbitrator.invoke(payload)
    return result

# Deploy: agentcore deploy

# Invoke deployed agent
import boto3
agentcore = boto3.client('bedrock-agentcore')
response = agentcore.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    runtimeSessionId=session_id,
    payload={...}
)
```

---

## What to Do with Old Files

### Keep (Archive)
- ✅ Keep files for historical reference
- ✅ Document what they did
- ✅ Note why they were deprecated

### Don't Use
- ❌ Do not run old deployment scripts
- ❌ Do not use old agent IDs/ARNs
- ❌ Do not reference old boto3 clients in new code

### Update References
- 🔄 Update documentation to point to AgentCore
- 🔄 Update CI/CD pipelines to use `agentcore deploy`
- 🔄 Update IAM policies for AgentCore permissions

---

## New AgentCore Files

Use these files instead:

### Core Implementation
- ✅ [`agents/arbitrator_agent.py`](agents/arbitrator_agent.py) - LangGraph agent (unchanged, AgentCore-ready)
- ✅ [`agentcore_arbitrator.py`](agentcore_arbitrator.py) - AgentCore entrypoint wrapper

### Testing
- ✅ [`test_agentcore_local.py`](test_agentcore_local.py) - Test locally before deployment
- ✅ [`test_agentcore_deployment.py`](test_agentcore_deployment.py) - Test deployed agent
- ✅ [`test_opus_direct.py`](test_opus_direct.py) - Test direct Bedrock model access (still valid)

### Documentation
- ✅ [`CLAUDE.md`](CLAUDE.md) - Updated with AgentCore integration
- ✅ [`AGENTCORE_DEPLOYMENT.md`](AGENTCORE_DEPLOYMENT.md) - AgentCore deployment guide

### Configuration
- ✅ [`.mcp/config.json`](.mcp/config.json) - AgentCore MCP server configuration

---

## Timeline

| Date | Event |
|------|-------|
| 2026-01-29 | Bedrock Agents implementation completed |
| 2026-01-30 | Migration to AgentCore initiated |
| 2026-01-30 | Documentation updated, old files deprecated |
| 2026-01-30 | AgentCore files created and tested |
| 2026-01-30+ | AgentCore deployment to AWS |

---

## Questions?

For questions about the migration:
1. **AgentCore Documentation**: Use the MCP server - ask "How do I deploy an AgentCore agent?"
2. **AWS Documentation**: https://docs.aws.amazon.com/bedrock-agentcore/
3. **Code Examples**: See [`agentcore_arbitrator.py`](agentcore_arbitrator.py)
4. **Migration Guide**: See [`CLAUDE.md`](CLAUDE.md) - "Migration from Bedrock Agents to AgentCore" section

---

**Last Updated**: 2026-01-30
**Status**: All Bedrock Agents files deprecated, AgentCore migration complete
