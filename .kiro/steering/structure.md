# Project Structure

## Repository Layout

```
skymarshal/
├── skymarshal_agents_new/skymarshal/    # Main agent system (active)
├── agents_old/                          # Legacy agent implementations
├── database/                            # Database setup and tools
├── frontend/                            # React frontend
├── src/                                 # Alternative orchestrator implementation
└── terraform/                           # Infrastructure as code
```

## Active Agent System

**Location**: `skymarshal_agents_new/skymarshal/`

```
skymarshal/
├── .bedrock_agentcore.yaml    # AgentCore deployment config
├── pyproject.toml             # UV project config
├── uv.lock                    # Dependency lock file
├── src/
│   ├── main.py                # Orchestrator entrypoint
│   ├── agents/                # Agent modules
│   │   ├── crew_compliance/
│   │   ├── maintenance/
│   │   ├── regulatory/
│   │   ├── network/
│   │   ├── guest_experience/
│   │   ├── cargo/
│   │   └── finance/
│   ├── database/              # DynamoDB integration
│   │   ├── dynamodb.py
│   │   └── tools.py
│   ├── mcp_client/            # MCP client
│   │   └── client.py
│   ├── model/                 # Model loading
│   │   └── load.py
│   └── utils/                 # Shared utilities
│       └── response.py
└── test/                      # Test suite
    ├── test_agent_imports.py
    └── test_main.py
```

## Agent Module Pattern

Each agent is a self-contained module:

```
agents/<agent_name>/
├── __init__.py          # Exports analyze_<agent_name>
└── agent.py             # Implementation with SYSTEM_PROMPT
```

All agents follow the same async interface:

```python
async def analyze_<agent_name>(
    payload: dict,      # Request with disruption data
    llm: Any,          # Bedrock model instance
    mcp_tools: list    # MCP tools
) -> dict:             # Structured assessment
```

## Database Structure

**Location**: `database/`

```
database/
├── schema/
│   └── database_schema.sql    # PostgreSQL/DynamoDB schema
├── generators/                # Data generation scripts
├── manager/
│   └── database.py            # Database manager
├── create_dynamodb_tables.py  # Table creation
└── import_csv_to_dynamodb.py  # Data import
```

## Frontend Structure

**Location**: `frontend/`

```
frontend/
├── components/                # React components
│   ├── AgentAvatar.tsx
│   ├── AgentMessage.tsx
│   ├── ArbitratorPanel.tsx
│   ├── Background.tsx
│   ├── InputBar.tsx
│   ├── LandingPage.tsx
│   └── OrchestrationView.tsx
├── App.tsx                    # Main app component
├── index.tsx                  # Entry point
├── package.json
└── vite.config.ts
```

## Specs Directory

**Location**: `.kiro/specs/`

Contains feature specifications following the spec-driven development methodology:

```
.kiro/specs/<feature-name>/
├── requirements.md    # Requirements document
├── design.md         # Design document
└── tasks.md          # Implementation tasks
```

## Key Files

- `skymarshal_agents_new/skymarshal/src/main.py` - Main orchestrator with agent registry and phase execution
- `skymarshal_agents_new/skymarshal/.bedrock_agentcore.yaml` - AgentCore deployment configuration
- `skymarshal_agents_new/skymarshal/pyproject.toml` - Project dependencies and metadata
- `database/create_dynamodb_tables.py` - DynamoDB table setup
- `README.md` - Root project overview
- `skymarshal_agents_new/skymarshal/README.md` - Agent system documentation

## Import Conventions

```python
# Agent imports (from agents module)
from agents import (
    analyze_crew_compliance,
    analyze_maintenance,
    analyze_regulatory,
    analyze_network,
    analyze_guest_experience,
    analyze_cargo,
    analyze_finance
)

# Database imports
from database.dynamodb import DynamoDBClient
from database.tools import get_crew_compliance_tools

# MCP client imports
from mcp_client.client import get_streamable_http_mcp_client

# Model imports
from model.load import load_model

# Utility imports
from utils.response import aggregate_agent_responses, determine_status
```

## Working Directory

When working on the agent system, always operate from:

```bash
cd skymarshal_agents_new/skymarshal
```

All UV and AgentCore commands should be run from this directory.
