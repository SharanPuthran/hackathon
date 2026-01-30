# Execution Agent

**Category**: Coordination
**Model**: global.anthropic.claude-sonnet-4-5-20250929-v1:0
**Description**: Execution coordinator and implementation manager

## Overview

This agent is part of the SkyMarshal multi-agent airline disruption management system.

**Role**: Execution coordinator and implementation manager

**Tool**: `coordinate_execution`

## Development

### Local Testing

1. Activate virtual environment:
```bash
source .venv/bin/activate
```

2. Start local development server:
```bash
agentcore dev
```

3. In another terminal, invoke the agent:
```bash
agentcore invoke --dev "Analyze flight EY123 disruption"
```

### Deployment

1. Configure deployment (optional):
```bash
agentcore configure
```

2. Deploy to AWS Bedrock AgentCore:
```bash
agentcore deploy
```

3. Invoke deployed agent:
```bash
agentcore invoke "Analyze flight EY123 disruption"
```

## Input Format

```json
{
  "prompt": "Analyze this disruption",
  "disruption": {
    "flight_number": "EY123",
    "route": "AUH → LHR",
    "issue": "Technical fault",
    "delay_hours": 3
  }
}
```

## Output Format

```json
{
  "agent": "execution",
  "category": "coordination",
  "result": "Detailed analysis from execution perspective"
}
```

## Integration

This agent integrates with:
- AWS Bedrock Claude Models
- AgentCore Runtime
- MCP Servers (Model Context Protocol)
- LangChain agent framework

## Next Steps

1. Implement agent-specific logic in `src/main.py`
2. Add domain-specific knowledge base integration
3. Configure MCP tools for specialized data access
4. Add comprehensive tests in `test/`
5. Deploy to AgentCore Runtime

---

**Part of**: SkyMarshal Multi-Agent System
**Status**: Template created, needs implementation
