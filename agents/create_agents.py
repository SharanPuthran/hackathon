#!/usr/bin/env python3
"""
Script to create all SkyMarshal agents from the arbitrator template
Creates 10 agents total with proper AgentCore structure
"""

import os
import shutil
from pathlib import Path
from typing import Dict, List

# Define all agents needed for SkyMarshal
AGENTS = {
    "orchestrator": {
        "category": "coordination",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Main coordinator and workflow manager for SkyMarshal system",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "coordinate_workflow"
    },
    "crew_compliance": {
        "category": "safety",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Flight and Duty Time Limitations (FTL) compliance checker",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "check_ftl_compliance"
    },
    "maintenance": {
        "category": "safety",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Aircraft airworthiness and MEL compliance checker",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "check_airworthiness"
    },
    "regulatory": {
        "category": "safety",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Regulatory constraints and NOTAM checker",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "check_regulations"
    },
    "network": {
        "category": "business",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Network optimization and downstream impact analyzer",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "analyze_network_impact"
    },
    "guest_experience": {
        "category": "business",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Passenger satisfaction and compensation analyzer",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "analyze_guest_impact"
    },
    "cargo": {
        "category": "business",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Cargo operations and critical shipment analyzer",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "analyze_cargo_impact"
    },
    "finance": {
        "category": "business",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Financial impact and cost optimization analyzer",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "analyze_financial_impact"
    },
    "execution": {
        "category": "coordination",
        "model": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "description": "Execution coordinator and implementation manager",
        "mcp_endpoint": "https://mcp.exa.ai/mcp",
        "tool_name": "coordinate_execution"
    }
}


def create_agent_from_template(agent_name: str, agent_config: Dict) -> None:
    """
    Create a new agent directory structure from arbitrator template

    Args:
        agent_name: Name of the agent (e.g., 'orchestrator')
        agent_config: Configuration dictionary for the agent
    """
    base_path = Path(__file__).parent
    template_path = base_path / "arbitrator"
    new_agent_path = base_path / agent_name

    print(f"\n{'='*60}")
    print(f"Creating {agent_name} agent...")
    print(f"{'='*60}")

    # Skip if already exists
    if new_agent_path.exists():
        print(f"⚠️  {agent_name} already exists, skipping...")
        return

    # Create new agent directory
    new_agent_path.mkdir(parents=True, exist_ok=True)

    # Copy directory structure (excluding venv and cache)
    for item in template_path.iterdir():
        if item.name in ['.venv', '__pycache__', '.git', 'uv.lock']:
            continue

        dest = new_agent_path / item.name

        if item.is_dir():
            shutil.copytree(item, dest, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(item, dest)

    # Update main.py with agent-specific configuration
    update_main_py(new_agent_path, agent_name, agent_config)

    # Update model/load.py with agent-specific model
    update_model_load(new_agent_path, agent_config)

    # Update .bedrock_agentcore.yaml
    update_agentcore_config(new_agent_path, agent_name)

    # Update README.md
    update_readme(new_agent_path, agent_name, agent_config)

    print(f"✅ {agent_name} agent created successfully!")


def update_main_py(agent_path: Path, agent_name: str, config: Dict) -> None:
    """Update main.py with agent-specific logic"""
    main_file = agent_path / "src" / "main.py"

    tool_name = config['tool_name']
    description = config['description']

    content = f'''from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from langchain.tools import tool
from bedrock_agentcore import BedrockAgentCoreApp
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

# Define agent-specific function tool
@tool
def {tool_name}(input_data: str) -> str:
    """
    {description}

    Args:
        input_data: JSON string containing disruption scenario and relevant data

    Returns:
        JSON string containing agent analysis and recommendations
    """
    # TODO: Implement {agent_name} logic
    return f"{agent_name.replace('_', ' ').title()} analysis: {{input_data}}"

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_streamable_http_mcp_client()

# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Instantiate model
llm = load_model()

@app.entrypoint
async def invoke(payload):
    """
    {agent_name.replace('_', ' ').title()} Agent Entrypoint

    Processes disruption scenarios and provides {config['category']} analysis
    """
    # Load MCP Tools
    tools = await mcp_client.get_tools()

    # Define the agent with {agent_name} tools
    graph = create_agent(llm, tools=tools + [{tool_name}])

    # Process the user prompt
    prompt = payload.get("prompt", f"Analyze this disruption as {agent_name.replace('_', ' ')}")

    # Include disruption data if provided
    disruption = payload.get("disruption", {{}})

    # Build context-aware message
    message = f"""{{prompt}}

Disruption Data:
{{disruption}}

Provide analysis from the perspective of {agent_name.replace('_', ' ')} ({config['category']}).
"""

    # Run the agent
    result = await graph.ainvoke({{"messages": [HumanMessage(content=message)]}})

    # Return result
    return {{
        "agent": "{agent_name}",
        "category": "{config['category']}",
        "result": result["messages"][-1].content
    }}

if __name__ == "__main__":
    # Run local development server on port 8080
    app.run()
'''

    main_file.write_text(content)
    print(f"  ✓ Updated main.py for {agent_name}")


def update_model_load(agent_path: Path, config: Dict) -> None:
    """Update model/load.py with agent-specific model"""
    model_file = agent_path / "src" / "model" / "load.py"

    model_id = config['model']

    content = f'''from langchain_aws import ChatBedrock

# Model configuration for this agent
MODEL_ID = "{model_id}"

def load_model() -> ChatBedrock:
    """
    Get Bedrock model client.
    Uses IAM authentication via the execution role.

    Model: {model_id}
    Provider: AWS Bedrock
    """
    return ChatBedrock(
        model_id=MODEL_ID,
        model_kwargs={{
            "max_tokens": 4096,
            "temperature": 0.3,  # Lower for consistent analysis
        }}
    )
'''

    model_file.write_text(content)
    print(f"  ✓ Updated model/load.py")


def update_agentcore_config(agent_path: Path, agent_name: str) -> None:
    """Update .bedrock_agentcore.yaml with agent name"""
    config_file = agent_path / ".bedrock_agentcore.yaml"

    if config_file.exists():
        content = config_file.read_text()
        # Replace agent name references
        content = content.replace('arbitrator_Agent', f'{agent_name}_Agent')
        content = content.replace('arbitrator/src', f'{agent_name}/src')
        config_file.write_text(content)
        print(f"  ✓ Updated .bedrock_agentcore.yaml")


def update_readme(agent_path: Path, agent_name: str, config: Dict) -> None:
    """Create agent-specific README"""
    readme_file = agent_path / "README.md"

    content = f'''# {agent_name.replace('_', ' ').title()} Agent

**Category**: {config['category'].title()}
**Model**: {config['model']}
**Description**: {config['description']}

## Overview

This agent is part of the SkyMarshal multi-agent airline disruption management system.

**Role**: {config['description']}

**Tool**: `{config['tool_name']}`

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
{{
  "prompt": "Analyze this disruption",
  "disruption": {{
    "flight_number": "EY123",
    "route": "AUH → LHR",
    "issue": "Technical fault",
    "delay_hours": 3
  }}
}}
```

## Output Format

```json
{{
  "agent": "{agent_name}",
  "category": "{config['category']}",
  "result": "Detailed analysis from {agent_name} perspective"
}}
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
'''

    readme_file.write_text(content)
    print(f"  ✓ Updated README.md")


def create_agents_overview() -> None:
    """Create overview documentation for all agents"""
    base_path = Path(__file__).parent
    overview_file = base_path / "AGENTS_STRUCTURE.md"

    content = '''# SkyMarshal Agents - Structure Overview

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
'''

    overview_file.write_text(content)
    print(f"\n✅ Created AGENTS_STRUCTURE.md overview")


def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("SkyMarshal Agent Generator")
    print("Creating 9 agents from arbitrator template")
    print("="*60)

    # Create all agents
    for agent_name, agent_config in AGENTS.items():
        create_agent_from_template(agent_name, agent_config)

    # Create overview documentation
    create_agents_overview()

    print("\n" + "="*60)
    print("✅ All agents created successfully!")
    print("="*60)
    print("\nNext steps:")
    print("1. cd agents/<agent_name>")
    print("2. Install dependencies: uv sync")
    print("3. Test locally: agentcore dev")
    print("4. Deploy: agentcore deploy")
    print("\nSee agents/AGENTS_STRUCTURE.md for complete overview")


if __name__ == "__main__":
    main()
