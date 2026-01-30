# SkyMarshal Agents - Complete Implementation

**Framework**: AWS Bedrock AgentCore + LangChain
**Total Agents**: 10
**Status**: All agent templates created ✅
**Created**: 2026-01-30

---

## 🎯 Quick Overview

SkyMarshal uses a **multi-agent architecture** with 10 specialized agents working together to manage airline disruptions:

```
┌─────────────────────────────────────────────────────┐
│           ORCHESTRATOR AGENT                        │
│         (Workflow Coordination)                     │
└─────────────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ SAFETY   │  │ BUSINESS │  │ARBITRATOR│
  │ AGENTS   │  │ AGENTS   │  │  AGENT   │
  │   (3)    │  │   (4)    │  │   (1)    │
  └──────────┘  └──────────┘  └──────────┘
        │             │             │
        └─────────────┼─────────────┘
                      ▼
        ┌─────────────────────────┐
        │   EXECUTION AGENT       │
        │   (Implementation)      │
        └─────────────────────────┘
```

---

## 📁 Agent Directory Structure

```
agents/
├── arbitrator/          ✅ Decision-making agent
├── orchestrator/        ✅ Main workflow coordinator
├── crew_compliance/     ✅ Safety: FTL compliance
├── maintenance/         ✅ Safety: Aircraft airworthiness
├── regulatory/          ✅ Safety: Regulatory constraints
├── network/             ✅ Business: Network optimization
├── guest_experience/    ✅ Business: Passenger satisfaction
├── cargo/               ✅ Business: Cargo operations
├── finance/             ✅ Business: Cost optimization
└── execution/           ✅ Execution coordinator
```

---

## 🏗️ Agent Categories

### Coordination Agents (3)

| Agent | Role | Tool |
|-------|------|------|
| [orchestrator](orchestrator/) | Main workflow coordinator | `coordinate_workflow` |
| [arbitrator](arbitrator/) | Final decision maker | `make_decision` |
| [execution](execution/) | Implementation coordinator | `coordinate_execution` |

### Safety Agents (3)

| Agent | Role | Tool |
|-------|------|------|
| [crew_compliance](crew_compliance/) | FTL regulations checker | `check_ftl_compliance` |
| [maintenance](maintenance/) | Aircraft airworthiness | `check_airworthiness` |
| [regulatory](regulatory/) | Regulatory constraints | `check_regulations` |

### Business Agents (4)

| Agent | Role | Tool |
|-------|------|------|
| [network](network/) | Network optimization | `analyze_network_impact` |
| [guest_experience](guest_experience/) | Passenger satisfaction | `analyze_guest_impact` |
| [cargo](cargo/) | Cargo operations | `analyze_cargo_impact` |
| [finance](finance/) | Cost optimization | `analyze_financial_impact` |

---

## 🚀 Quick Start

### Prerequisites

```bash
# Install AgentCore CLI
pip install bedrock-agentcore-starter-toolkit

# Verify installation
agentcore --version
```

### Test Agent Locally

```bash
# Navigate to any agent
cd orchestrator

# Install dependencies
uv sync

# Start local server (localhost:8080)
agentcore dev

# In another terminal, test the agent
agentcore invoke --dev "Analyze flight EY123 delayed 3 hours"
```

### Deploy Agent to AWS

```bash
cd orchestrator
agentcore configure  # Optional
agentcore deploy
agentcore invoke "Analyze flight EY123"
```

---

## 📋 Agent Structure

Each agent directory contains:

```
agent_name/
├── .bedrock_agentcore.yaml    # AgentCore config
├── README.md                   # Agent docs
├── pyproject.toml              # Dependencies
├── src/
│   ├── main.py                # Entrypoint
│   ├── model/load.py          # Model config
│   └── mcp_client/client.py   # MCP integration
└── test/
    └── test_main.py           # Tests
```

---

## 🔧 Development Workflow

### 1. Implement Agent Logic

Edit `src/main.py`:

```python
@tool
def your_agent_tool(input_data: str) -> str:
    """Implement agent-specific logic here"""
    # TODO: Add your implementation
    pass
```

### 2. Configure Model

Edit `src/model/load.py` to customize model:

```python
# Use different model per agent
MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

### 3. Test Locally

```bash
agentcore dev
agentcore invoke --dev "Test input"
```

### 4. Deploy

```bash
agentcore deploy
```

---

## 🌐 Model Configuration

All agents currently use **Claude Sonnet 4.5**:

```python
MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

You can customize per agent in `src/model/load.py`:
- **Opus 4.5**: Complex reasoning (Arbitrator, Orchestrator)
- **Sonnet 4.5**: Balanced performance (Safety, Business agents)
- **Haiku 3.5**: Fast, cost-effective (simple tasks)
- **Nova Pro**: AWS-native option

---

## 📊 Input/Output Format

### Input

```json
{
  "prompt": "Analyze this disruption",
  "disruption": {
    "flight_number": "EY123",
    "route": "AUH → LHR",
    "issue": "Hydraulic fault",
    "delay_hours": 3
  }
}
```

### Output

```json
{
  "agent": "agent_name",
  "category": "safety|business|coordination",
  "result": "Analysis and recommendations"
}
```

---

## 🚢 Deploy All Agents

Create `deploy_all.sh`:

```bash
#!/bin/bash
for agent in orchestrator crew_compliance maintenance regulatory \
             network guest_experience cargo finance arbitrator execution; do
    echo "Deploying $agent..."
    cd "$agent" && agentcore deploy && cd ..
done
```

Run:
```bash
chmod +x deploy_all.sh
./deploy_all.sh
```

---

## 📚 Documentation

- [AGENTS_STRUCTURE.md](AGENTS_STRUCTURE.md) - Detailed architecture
- [../CLAUDE.md](../CLAUDE.md) - Claude model integration
- [../AGENTCORE_DEPLOYMENT.md](../AGENTCORE_DEPLOYMENT.md) - Deployment guide

Individual agent READMEs:
- [orchestrator/README.md](orchestrator/README.md)
- [crew_compliance/README.md](crew_compliance/README.md)
- [maintenance/README.md](maintenance/README.md)
- [regulatory/README.md](regulatory/README.md)
- [network/README.md](network/README.md)
- [guest_experience/README.md](guest_experience/README.md)
- [cargo/README.md](cargo/README.md)
- [finance/README.md](finance/README.md)
- [arbitrator/README.md](arbitrator/README.md)
- [execution/README.md](execution/README.md)

---

## 🔄 Regenerate Agents

If you need to recreate the agent structure:

```bash
# From agents/ directory
python3 create_agents.py
```

This will create all 9 agents from the arbitrator template.

---

## 📈 Next Steps

1. ✅ Create all agent templates
2. ⏳ Implement agent-specific logic
3. ⏳ Add domain knowledge bases
4. ⏳ Configure MCP tools
5. ⏳ Write tests
6. ⏳ Deploy all agents
7. ⏳ Create orchestration workflow

---

## 🛠️ Useful Commands

```bash
# Test all agents locally
for agent in */; do cd "$agent" && agentcore dev & cd ..; done

# Deploy all agents
for agent in */; do cd "$agent" && agentcore deploy && cd ..; done

# Check deployment status
aws bedrock-agentcore list-agents --region us-east-1

# View logs
aws logs tail /aws/bedrock-agentcore/runtime/agent_name --follow
```

---

**Status**: ✅ All 10 agent templates created successfully
**Created**: 2026-01-30
**Generator**: [create_agents.py](create_agents.py)
