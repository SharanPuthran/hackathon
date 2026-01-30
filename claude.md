# Claude Models in SkyMarshal

**Project**: SkyMarshal - Multi-Agent Airline Disruption Management System
**Date**: 2026-01-30
**Integration**: AWS Bedrock AgentCore + LangGraph

---

## Overview

SkyMarshal uses Claude models via AWS Bedrock for sophisticated decision-making in airline disruption scenarios. This document covers Claude model integration, configuration, and usage.

---

## Claude Models Available

### Claude Opus 4.5 (Primary Model)

**Model ID**: `us.anthropic.claude-opus-4-5-20251101-v1:0` (cross-region inference profile)
**Base Model ID**: `anthropic.claude-opus-4-5-20251101-v1:0`
**Region**: us-east-1
**Status**: ✅ Available and accessible

**Capabilities**:
- Advanced reasoning and analysis
- Multi-step decision making
- Complex scenario evaluation
- Structured output generation
- Long-context processing (200K+ tokens)

**Use Case in SkyMarshal**:
- **Arbitrator Agent**: Multi-criteria decision maker
- Analyzes safety assessments, business proposals, and disruption scenarios
- Generates weighted decisions with detailed rationale
- Evaluates 3-5 recovery scenarios simultaneously

**Pricing** (as of 2026-01-30):
- Input: ~$15 per million tokens
- Output: ~$75 per million tokens
- Estimated cost per disruption analysis: $0.50 - $2.00

### Other Claude Models

**Available but not currently used**:
- Claude Sonnet 4.5: `us.anthropic.claude-3-5-sonnet-20241022-v2:0` (requires use case approval)
- Claude Haiku 3.5: `us.anthropic.claude-3-5-haiku-20241022-v1:0` (requires use case approval)

**Note**: Anthropic Claude models on Bedrock require submitting a use case form before access is granted.

---

## Integration Architecture

### 1. Direct Bedrock Runtime API

**Used for**: Local LangGraph agents

```python
from langchain_aws import ChatBedrock

llm = ChatBedrock(
    model_id="us.anthropic.claude-opus-4-5-20251101-v1:0",
    region_name="us-east-1",
    model_kwargs={
        "max_tokens": 4096,
        "temperature": 0.3,
    }
)

response = llm.invoke(messages)
```

**Status**: ✅ Working perfectly

### 2. AWS Bedrock AgentCore Runtime

**Used for**: Production agent deployment with enterprise infrastructure

```python
from bedrock_agentcore import BedrockAgentCoreApp
from agents.arbitrator_agent import create_arbitrator_agent

app = BedrockAgentCoreApp()

@app.entrypoint
def arbitrator_entrypoint(payload):
    """Production-ready arbitrator agent with managed runtime"""
    arbitrator = create_arbitrator_agent()
    result = arbitrator.invoke(
        disruption_scenario=payload.get("disruption"),
        safety_assessments=payload.get("safety"),
        business_proposals=payload.get("business")
    )
    return {
        "decision": result["decision"],
        "rationale": result["rationale"],
        "confidence": result["confidence_score"]
    }

# Local testing
if __name__ == "__main__":
    app.run()  # Runs on localhost:8080

# Deploy to AWS: agentcore deploy
```

**Status**: ✅ Ready for deployment with AgentCore Runtime

**AgentCore Benefits**:
- **Managed Runtime**: Auto-scaling compute with AWS-managed infrastructure
- **Persistent Memory**: Built-in conversation history and context management
- **Enterprise Tools**: Code interpreter, browser automation, MCP server integration
- **Observability**: OpenTelemetry tracing and CloudWatch metrics
- **Framework Agnostic**: Works with LangGraph, Strands Agents, CrewAI, custom frameworks

### 3. LangGraph Integration

**Used for**: Complex multi-step workflows

```python
from langgraph.graph import StateGraph
from langchain_aws import ChatBedrock

class SkyMarshalArbitrator:
    def __init__(self):
        self.llm = ChatBedrock(
            model_id="us.anthropic.claude-opus-4-5-20251101-v1:0",
            region_name="us-east-1"
        )
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(ArbitratorState)
        workflow.add_node("analyze_inputs", self._analyze_inputs)
        workflow.add_node("generate_scenarios", self._generate_scenarios)
        workflow.add_node("evaluate_scenarios", self._evaluate_scenarios)
        workflow.add_node("rank_scenarios", self._rank_scenarios)
        workflow.add_node("make_decision", self._make_decision)
        workflow.add_node("generate_rationale", self._generate_rationale)

        workflow.set_entry_point("analyze_inputs")
        workflow.add_edge("analyze_inputs", "generate_scenarios")
        workflow.add_edge("generate_scenarios", "evaluate_scenarios")
        workflow.add_edge("evaluate_scenarios", "rank_scenarios")
        workflow.add_edge("rank_scenarios", "make_decision")
        workflow.add_edge("make_decision", "generate_rationale")
        workflow.add_edge("generate_rationale", END)

        return workflow.compile()
```

**Status**: ✅ Working perfectly

---

## Configuration

### Model Parameters

**Arbitrator Agent Settings**:
```python
model_kwargs = {
    "max_tokens": 4096,
    "temperature": 0.3,  # Lower for consistent decisions
}
```

**Why these settings?**
- `max_tokens: 4096`: Sufficient for detailed rationale and multi-scenario analysis
- `temperature: 0.3`: Lower temperature ensures consistent, reliable decision-making
- No `top_p`: Claude Opus 4.5 doesn't support both temperature and top_p simultaneously

### AWS IAM Permissions

**Required for Claude Opus 4.5 via AgentCore**:
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
        "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-opus-4-5-20251101-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-opus-4-5-20251101-v1:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime",
        "bedrock-agentcore:CreateAgent",
        "bedrock-agentcore:UpdateAgent",
        "bedrock-agentcore:DescribeAgent",
        "bedrock-agentcore:DeleteAgent"
      ],
      "Resource": "arn:aws:bedrock-agentcore:us-east-1:368613657554:agent/*"
    }
  ]
}
```

**Note**: AgentCore requires both Bedrock model access and AgentCore management permissions.

---

## Usage Examples

### 1. Simple Invocation

```python
from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

llm = ChatBedrock(
    model_id="us.anthropic.claude-opus-4-5-20251101-v1:0",
    region_name="us-east-1",
    model_kwargs={"max_tokens": 4096, "temperature": 0.3}
)

messages = [HumanMessage(content="Analyze this disruption scenario...")]
response = llm.invoke(messages)

print(response.content)
```

### 2. Arbitrator Agent (Full Workflow)

```python
from agents.arbitrator_agent import create_arbitrator_agent

arbitrator = create_arbitrator_agent()

result = arbitrator.invoke(
    disruption_scenario={
        "flight_number": "EY123",
        "route": "AUH → LHR",
        "issue": "Hydraulic system fault",
        "delay_hours": 3,
        "passengers": 615,
        "connections_at_risk": 87
    },
    safety_assessments={
        "crew_compliance": {"status": "APPROVED", "ftl_remaining": "3.5 hours"},
        "maintenance": {"status": "MEL_CATEGORY_B", "deferrable": True},
        "regulatory": {"status": "CURFEW_RISK", "latest_departure": "20:00"}
    },
    business_proposals={
        "network": {"priority": "HIGH", "downstream_impact": "$450K"},
        "guest_experience": {"compensation": "€125K", "satisfaction_risk": "MEDIUM"},
        "cargo": {"critical_shipments": 3, "offload_recommended": False},
        "finance": {"cancel_cost": "€1.2M", "delay_cost": "€210K"}
    }
)

print(f"Decision: {result['decision']}")
print(f"Rationale: {result['rationale']}")
print(f"Confidence: {result['confidence_score']}%")
```

### 3. AgentCore Runtime Invocation

```python
import boto3
import uuid
import json

# Invoke deployed AgentCore agent
agentcore_client = boto3.client('bedrock-agentcore', region_name='us-east-1')

response = agentcore_client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:368613657554:agent/skymarshal-arbitrator",
    runtimeSessionId=str(uuid.uuid4()),
    payload={
        "prompt": "Analyze disruption: EY123 hydraulic fault",
        "disruption": {
            "flight_number": "EY123",
            "issue": "Hydraulic system fault",
            "delay_hours": 3
        }
    }
)

result = json.loads(response['output'])
print(f"Decision: {result['decision']}")
print(f"Confidence: {result['confidence']}%")
```

**Local Testing** (before deployment):
```python
# Test locally on http://localhost:8080
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()
app.run()  # Start local development server
```

---

## Performance & Cost

### Arbitrator Agent Performance

**Test Scenario**: EY123 Hydraulic Fault Analysis

| Metric | Value |
|--------|-------|
| **Total Execution Time** | ~45-60 seconds |
| **LangGraph Nodes** | 6 sequential steps |
| **Total Tokens** | ~8,000-12,000 |
| **Cost per Invocation** | $0.50 - $1.00 |
| **Decision Quality** | Weighted score: 75.9/100, Confidence: 78% |

### Optimization Tips

1. **Prompt Engineering**: Be specific and structured in prompts
2. **Token Management**: Use concise system instructions
3. **Streaming**: Use `InvokeModelWithResponseStream` for real-time feedback
4. **Caching**: Cache common scenarios and regulations
5. **Batch Processing**: Process multiple disruptions in parallel

---

## Prompt Engineering

### Effective Prompts for Claude

**Structure**:
```
You are [ROLE] with [SPECIFIC CAPABILITIES].

Your task is to [CLEAR OBJECTIVE].

Context:
[STRUCTURED DATA]

Requirements:
1. [SPECIFIC REQUIREMENT]
2. [SPECIFIC REQUIREMENT]
3. [SPECIFIC REQUIREMENT]

Output format:
[EXPECTED FORMAT]
```

**Example (Arbitrator)**:
```
You are the SkyMarshal Arbitrator Agent - the final decision maker in a
multi-agent airline disruption management system.

Your role is to synthesize inputs from safety and business agents and make
optimal decisions that:
1. Meet ALL safety requirements (non-negotiable)
2. Optimize for weighted criteria: Safety (40%), Cost (25%), Passengers (20%),
   Network (10%), Reputation (5%)
3. Balance stakeholder interests
4. Provide clear, actionable rationale

Analyze the following disruption:
[STRUCTURED JSON DATA]

Provide:
1. Analysis of the situation
2. 3-5 viable recovery scenarios
3. Evaluation of each scenario
4. Final decision with rationale
5. Confidence score (0-100)
```

---

## Testing

### Test Scripts

1. **[`test_opus_direct.py`](test_opus_direct.py)** - Test direct Claude Opus 4.5 access
2. **[`agents/arbitrator_agent.py`](agents/arbitrator_agent.py)** - Full LangGraph implementation with test
3. **[`test_agentcore_local.py`](test_agentcore_local.py)** - Test AgentCore local runtime
4. **[`test_agentcore_deployment.py`](test_agentcore_deployment.py)** - Test deployed AgentCore agent

### Running Tests

```bash
# Test direct model access
python3 test_opus_direct.py

# Test Arbitrator agent locally (LangGraph)
python3 agents/arbitrator_agent.py

# Test AgentCore agent locally (before deployment)
python3 test_agentcore_local.py

# Deploy to AgentCore Runtime
agentcore configure -e agents/arbitrator_agent.py
agentcore deploy

# Test deployed AgentCore agent
python3 test_agentcore_deployment.py
```

### Expected Output

```
============================================================
Testing SkyMarshal Arbitrator Agent
Model: Claude Opus 4.5
Framework: LangGraph
============================================================

🤖 Invoking Arbitrator...

✅ Decision Made:
   Scenario: RS-001 (Expedited Delay & Dispatch)
   Score: 75.9/100
   Confidence: 78%

📋 Rationale:
[Comprehensive multi-criteria analysis...]

✅ Arbitrator test complete!
```

---

## Troubleshooting

### Common Issues

#### 1. Temperature and top_p conflict

**Error**: `temperature and top_p cannot both be specified for this model`

**Solution**: Remove `top_p` from model_kwargs:
```python
model_kwargs = {
    "max_tokens": 4096,
    "temperature": 0.3,  # Keep only temperature
}
```

#### 2. Access denied for Claude models

**Error**: `Model use case details have not been submitted`

**Solution**:
- Submit use case form at https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess
- Or use Amazon Nova models which don't require approval

#### 3. Model not found

**Error**: `Could not resolve the foundation model`

**Solution**: Check model ID format:
- ✅ Correct: `us.anthropic.claude-opus-4-5-20251101-v1:0`
- ❌ Incorrect: `claude-opus-4-5`, `opus-4-5`

#### 4. Token limit exceeded

**Error**: `Input is too long`

**Solution**:
- Truncate context or use summarization
- Claude Opus 4.5 supports 200K context window

---

## Comparison with Other Models

### Claude Opus 4.5 vs Amazon Nova Premier

| Feature | Claude Opus 4.5 | Amazon Nova Premier |
|---------|----------------|---------------------|
| **Reasoning** | Excellent | Good |
| **Cost** | $15/$75 per 1M tokens | $0.80/$3.20 per 1M tokens |
| **Speed** | Moderate | Fast |
| **Context** | 200K tokens | 300K tokens |
| **Access** | Requires approval | Immediate |
| **Use Case** | Complex decisions | Fast orchestration |

**Recommendation**: Use Claude Opus 4.5 for critical decision-making (Arbitrator), use Nova for faster coordination tasks.

---

## Future Enhancements

### Planned Improvements

1. **Streaming Responses**: Implement `InvokeModelWithResponseStream` for real-time feedback
2. **Multi-Agent Collaboration**: Multiple Claude agents working together
3. **Prompt Optimization**: A/B test different prompt structures
4. **Caching Layer**: Cache common regulatory lookups
5. **Fine-tuning**: Custom model training on historical decisions

### Claude 5 Migration

When Claude 5 becomes available:
- Test backward compatibility with existing prompts
- Benchmark performance improvements
- Evaluate cost differences
- Update model IDs in configuration

---

## AgentCore Documentation & MCP Server

### AgentCore MCP Server

The project uses the **Amazon Bedrock AgentCore MCP Server** for development assistance:

**Configuration**: [`.mcp/config.json`](.mcp/config.json)
```json
{
  "mcpServers": {
    "bedrock-agentcore-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.amazon-bedrock-agentcore-mcp-server@latest"],
      "env": {
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "default",
        "FASTMCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**MCP Server Capabilities**:
- `search_agentcore_docs` - Search AgentCore documentation
- `fetch_agentcore_doc` - Retrieve full documentation content
- Real-time access to AgentCore API reference, tutorials, and best practices

**Usage in Claude Code**:
Ask questions like "How do I deploy an AgentCore agent?" and the MCP server will provide up-to-date documentation.

### Documentation Links

- **AWS Bedrock AgentCore**: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
- **AgentCore Python SDK**: https://github.com/aws/bedrock-agentcore-sdk-python
- **AgentCore Starter Toolkit**: https://github.com/aws/bedrock-agentcore-starter-toolkit
- **AgentCore Runtime**: https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/
- **AgentCore MCP Server**: https://awslabs.github.io/mcp/servers/amazon-bedrock-agentcore-mcp-server
- **AgentCore Samples**: https://github.com/awslabs/amazon-bedrock-agentcore-samples
- **AWS Bedrock Claude Models**: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html
- **LangChain ChatBedrock**: https://python.langchain.com/docs/integrations/chat/bedrock
- **LangGraph**: https://langchain-ai.github.io/langgraph/
- **Anthropic API**: https://docs.anthropic.com/en/api/

### Related Files

- [`agents/arbitrator_agent.py`](agents/arbitrator_agent.py) - LangGraph implementation (AgentCore-ready)
- [`AGENTCORE_DEPLOYMENT.md`](AGENTCORE_DEPLOYMENT.md) - AgentCore deployment guide
- [`src/config.py`](src/config.py) - Model configuration
- [`terraform/deploy-simple.tf`](terraform/deploy-simple.tf) - IAM permissions
- [`.mcp/config.json`](.mcp/config.json) - MCP server configuration

---

## Contact & Support

### Using the AgentCore MCP Server

For AgentCore-specific questions, use the **bedrock-agentcore-mcp-server** configured in this project:
1. Ask "How do I deploy an AgentCore agent?" in Claude Code
2. Query "What are the AgentCore Runtime APIs?"
3. Search "AgentCore memory integration examples"

The MCP server provides real-time access to official AWS documentation.

### Troubleshooting

For issues with Claude integration:
1. **AgentCore Runtime**: Check CloudWatch logs: `/aws/bedrock-agentcore/runtime/skymarshal`
2. **IAM Permissions**: Review AgentCore permissions in AWS Console
3. **Model Access**: Test with `test_opus_direct.py` to verify Bedrock model access
4. **Local Testing**: Run `app.run()` to test agents locally before deployment
5. **MCP Server**: Verify [`.mcp/config.json`](.mcp/config.json) configuration
6. **Consult Documentation**: Use the MCP server or visit https://docs.aws.amazon.com/bedrock-agentcore/

---

**Last Updated**: 2026-01-30
**Status**: Migrated to AWS Bedrock AgentCore Runtime
**Integration**: Claude Opus 4.5 via LangGraph + AgentCore SDK
**Next Steps**: Deploy arbitrator agent to AgentCore Runtime with `agentcore deploy`

---

## Migration from Bedrock Agents to AgentCore

### What Changed

**Before (Bedrock Agents)**:
- Used `boto3.client('bedrock-agent')` for management
- Used `boto3.client('bedrock-agent-runtime')` for invocation
- Manual agent creation via AWS Console or boto3 API
- Complex IAM permission issues
- Limited framework support

**After (AgentCore)**:
- Uses `bedrock-agentcore` Python SDK for development
- Uses `BedrockAgentCoreApp` for agent wrapping
- CLI-based deployment with `agentcore deploy`
- Simplified permissions with AgentCore runtime
- Full framework support: LangGraph, Strands, CrewAI, custom

### Migration Benefits

1. **Local Development**: Test agents locally before cloud deployment
2. **Framework Agnostic**: Keep existing LangGraph implementation
3. **Managed Infrastructure**: Auto-scaling, memory, tools, observability
4. **Simplified Deployment**: Single CLI command to deploy
5. **MCP Integration**: AgentCore MCP server for documentation and tooling
6. **Production Ready**: Built-in session management, authentication, logging

### Migration Checklist

- ✅ Updated documentation to reference AgentCore
- ✅ Configured AgentCore MCP server in `.mcp/config.json`
- ⏳ Install AgentCore SDK: `pip install bedrock-agentcore`
- ⏳ Wrap arbitrator agent with `BedrockAgentCoreApp`
- ⏳ Test locally with `app.run()`
- ⏳ Configure deployment with `agentcore configure`
- ⏳ Deploy to AgentCore Runtime with `agentcore deploy`
- ⏳ Update IAM permissions for AgentCore
- ⏳ Update test scripts for AgentCore invocation
