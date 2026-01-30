# SkyMarshal Agents - Structure Overview

**Total Agents**: 10
**Framework**: AWS Bedrock AgentCore + LangChain
**Status**: Template structure created

---

## Agent Directory Structure

```
agents/
├── arbitrator/          # Decision-making agent (template)
├── orchestrator/        # Main coordinator
├── crew_compliance/     # Safety: FTL compliance
├── maintenance/         # Safety: Airworthiness
├── regulatory/          # Safety: Regulations
├── network/             # Business: Network optimization
├── guest_experience/    # Business: Passenger satisfaction
├── cargo/               # Business: Cargo operations
├── finance/             # Business: Cost optimization
└── execution/           # Execution coordinator
```

## Agent Categories

### Coordination Agents (3)
1. **Orchestrator** - Workflow management
2. **Arbitrator** - Final decision making
3. **Execution** - Implementation coordination

### Safety Agents (3)
1. **Crew Compliance** - FTL regulations
2. **Maintenance** - Aircraft airworthiness
3. **Regulatory** - NOTAM/curfew/slots

### Business Agents (4)
1. **Network** - Downstream impact
2. **Guest Experience** - PAX satisfaction
3. **Cargo** - Critical shipments
4. **Finance** - Cost optimization

---

## Each Agent Contains

```
agent_name/
├── .bedrock_agentcore.yaml    # AgentCore deployment config
├── .gitignore                  # Git ignore rules
├── README.md                   # Agent-specific docs
├── pyproject.toml              # Python dependencies
├── src/
│   ├── main.py                # Agent entrypoint
│   ├── model/
│   │   └── load.py            # Model configuration
│   └── mcp_client/
│       └── client.py          # MCP integration
└── test/
    ├── __init__.py
    └── test_main.py           # Agent tests
```

---

## Development Workflow

### 1. Create Agent (Done)
```bash
python3 create_agents.py
```

### 2. Develop Locally
```bash
cd agents/agent_name
source .venv/bin/activate
agentcore dev  # Starts on localhost:8080
```

### 3. Test Locally
```bash
agentcore invoke --dev "Test prompt"
```

### 4. Deploy to AWS
```bash
agentcore configure  # Optional customization
agentcore deploy     # Deploy to Bedrock AgentCore
```

### 5. Invoke Deployed Agent
```bash
agentcore invoke "Production prompt"
```

---

## Model Distribution

All agents currently use:
- **Model**: Claude Sonnet 4.5
- **Model ID**: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Provider**: AWS Bedrock
- **Temperature**: 0.3 (consistent analysis)
- **Max Tokens**: 4096

*Can be customized per agent in `src/model/load.py`*

---

## Next Steps

1. ✅ Create agent structure from template
2. ⏳ Implement agent-specific logic
3. ⏳ Add domain knowledge bases
4. ⏳ Configure MCP tools
5. ⏳ Write comprehensive tests
6. ⏳ Deploy all agents to AgentCore
7. ⏳ Create orchestration workflow

---

**Generated**: 2026-01-30
**Status**: Agent templates created, ready for implementation
