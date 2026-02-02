# SkyMarshal Agent System

A multi-agent system for analyzing flight disruptions, built on AWS Bedrock AgentCore. The system uses 7 specialized agents organized in a two-phase execution model to provide comprehensive safety and business impact assessments.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Multi-Solution Arbitrator](#multi-solution-arbitrator)
- [Project Structure](#project-structure)
- [Module Organization](#module-organization)
- [Getting Started](#getting-started)
- [UV Workflow](#uv-workflow)
- [Local Development](#local-development)
- [Deployment](#deployment)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

## Overview

SkyMarshal is an intelligent flight disruption analysis system that evaluates both safety-critical and business impact factors when flights are delayed or disrupted. The system uses:

- **7 Specialized Agents**: Each agent analyzes a specific domain (crew compliance, maintenance, regulatory, network, guest experience, cargo, finance)
- **Two-Phase Execution**: Safety agents execute first, followed by business agents
- **Parallel Processing**: Agents within each phase run concurrently for optimal performance
- **AWS Bedrock AgentCore**: Serverless deployment and scaling on AWS infrastructure
- **LangGraph**: Multi-agent orchestration and coordination
- **DynamoDB Integration**: Real-time access to operational data
- **MCP Gateway**: External tool integration via Model Context Protocol

## Architecture

### Natural Language Processing

**Date Parsing and Data Extraction**

SkyMarshal agents use **LangChain structured output** to extract flight information from natural language prompts. This approach:

- ✅ **No custom parsing functions** - LangChain's `with_structured_output()` handles all extraction
- ✅ **Pydantic models** - Define structured data schemas for type safety
- ✅ **Flexible date formats** - Handles numeric (dd/mm/yyyy, yyyy-mm-dd), named (20 Jan 2026), and relative dates (yesterday, today)
- ✅ **Agent autonomy** - Each agent extracts data independently using its LLM capabilities

**Date/Time Utility**: The `get_current_datetime_tool()` provides current UTC time for resolving relative dates. It does NOT parse dates - that's handled by LangChain structured output.

**Reference**: See [LangChain Structured Output Documentation](https://docs.langchain.com/oss/python/langchain/structured-output)

### Agent Organization

**Safety Agents (Phase 1)**

- `crew_compliance` - Analyzes crew duty time, rest requirements, and regulatory compliance
- `maintenance` - Evaluates aircraft maintenance status and airworthiness
- `regulatory` - Assesses regulatory compliance (EASA, GCAA, FAA)

**Business Agents (Phase 2)**

- `network` - Analyzes network impact and downstream connections
- `guest_experience` - Evaluates passenger impact and satisfaction
- `cargo` - Assesses cargo handling and revenue implications
- `finance` - Calculates financial impact and cost analysis

### Execution Flow

```
User Request
     ↓
Orchestrator
     ↓
Phase 1: Safety Assessment (Parallel)
├── crew_compliance
├── maintenance
└── regulatory
     ↓
Safety Check
     ↓
Phase 2: Business Assessment (Parallel)
├── network
├── guest_experience
├── cargo
└── finance
     ↓
Response Aggregation
     ↓
Final Decision
```

## Multi-Solution Arbitrator

The SkyMarshal arbitrator has been enhanced to provide **1-3 ranked solution options** instead of a single decision, enabling better human-in-the-loop decision making.

### Key Features

- **Multiple Solutions**: Generates 1-3 ranked alternatives with detailed trade-off analysis
- **Multi-Dimensional Scoring**: Safety (40%), Cost (20%), Passenger Impact (20%), Network Impact (20%)
- **Recovery Plans**: Each solution includes step-by-step implementation workflow with dependencies
- **S3 Integration**: Automatic storage to knowledge base and audit buckets for historical learning
- **Decision Reports**: Generate comprehensive audit-ready reports in JSON, Markdown, or PDF formats
- **Backward Compatible**: Existing integrations continue to work without changes

### Quick Example

```python
# Arbitrate with multi-solution output
result = await arbitrate(phase1_responses, phase2_responses, llm)

# Access solution options
for solution in result.solution_options:
    print(f"{solution.title}: Score {solution.composite_score:.1f}/100")
    print(f"  Pros: {', '.join(solution.pros)}")
    print(f"  Recovery: {solution.recovery_plan.total_steps} steps")

# Get recommended solution
recommended = next(s for s in result.solution_options
                   if s.solution_id == result.recommended_solution_id)
```

### Documentation

For complete documentation on the multi-solution arbitrator, see:

- **User Guide**: [ARBITRATOR_MULTI_SOLUTION_GUIDE.md](./ARBITRATOR_MULTI_SOLUTION_GUIDE.md)
- **Design Document**: [.kiro/specs/arbitrator-multi-solution-enhancements/design.md](../../.kiro/specs/arbitrator-multi-solution-enhancements/design.md)
- **Requirements**: [.kiro/specs/arbitrator-multi-solution-enhancements/requirements.md](../../.kiro/specs/arbitrator-multi-solution-enhancements/requirements.md)

## Project Structure

```
skymarshal/
├── .bedrock_agentcore.yaml    # AgentCore deployment configuration
├── pyproject.toml             # UV project configuration and dependencies
├── uv.lock                    # Dependency lock file
├── README.md                  # This file
├── src/                       # Main source code
│   ├── main.py                # Orchestrator entrypoint
│   ├── agents/                # Agent modules
│   │   ├── __init__.py        # Agent exports
│   │   ├── crew_compliance/
│   │   │   ├── __init__.py
│   │   │   └── agent.py       # Crew compliance agent
│   │   ├── maintenance/
│   │   │   ├── __init__.py
│   │   │   └── agent.py       # Maintenance agent
│   │   ├── regulatory/
│   │   │   ├── __init__.py
│   │   │   └── agent.py       # Regulatory agent
│   │   ├── network/
│   │   │   ├── __init__.py
│   │   │   └── agent.py       # Network agent
│   │   ├── guest_experience/
│   │   │   ├── __init__.py
│   │   │   └── agent.py       # Guest experience agent
│   │   ├── cargo/
│   │   │   ├── __init__.py
│   │   │   └── agent.py       # Cargo agent
│   │   └── finance/
│   │       ├── __init__.py
│   │       └── agent.py       # Finance agent
│   ├── database/              # Database integration layer
│   │   ├── __init__.py
│   │   ├── dynamodb.py        # DynamoDB client
│   │   └── tools.py           # Database tool factories
│   ├── mcp_client/            # MCP client integration
│   │   ├── __init__.py
│   │   └── client.py          # MCP client implementation
│   ├── model/                 # Model loading utilities
│   │   ├── __init__.py
│   │   └── load.py            # Bedrock model loader
│   └── utils/                 # Shared utilities
│       ├── __init__.py
│       └── response.py        # Response aggregation
└── test/                      # Test suite
    ├── __init__.py
    ├── test_agent_imports.py  # Property-based import tests
    └── test_main.py           # Orchestrator tests
```

## Module Organization

### Agents as Separate Modules

Each agent is organized as a self-contained Python module:

```python
# Agent module structure
agents/crew_compliance/
├── __init__.py          # Exports analyze_crew_compliance
└── agent.py             # Implementation with SYSTEM_PROMPT and logic
```

**Importing agents:**

```python
# Import all agents from the agents module
from agents import (
    analyze_crew_compliance,
    analyze_maintenance,
    analyze_regulatory,
    analyze_network,
    analyze_guest_experience,
    analyze_cargo,
    analyze_finance
)
```

### Agent Interface

All agents follow a consistent async interface:

```python
async def analyze_<agent_name>(
    payload: dict,      # Request payload with disruption data
    llm: Any,          # Bedrock model instance
    mcp_tools: list    # MCP tools from gateway
) -> dict:             # Structured assessment response
    """
    Analyzes a specific aspect of flight disruption.

    Returns:
        dict: {
            "agent": str,
            "category": "safety" | "business",
            "status": "success" | "error" | "timeout",
            "result": str | dict,
            "duration_seconds": float
        }
    """
```

**Data Extraction Pattern**

Agents use LangChain structured output to extract flight information from natural language prompts:

```python
from pydantic import BaseModel, Field
from langchain_aws import ChatBedrock

# Define Pydantic model for structured data
class FlightInfo(BaseModel):
    """Flight information extracted from natural language."""
    flight_number: str = Field(description="Flight number (e.g., EY123)")
    date: str = Field(description="Flight date in ISO format (YYYY-MM-DD)")
    disruption_event: str = Field(description="Description of the disruption")

# Use LangChain structured output to extract data
llm = ChatBedrock(model_id="anthropic.claude-sonnet-4-20250514-v1:0")
structured_llm = llm.with_structured_output(FlightInfo)

# Extract from natural language prompt
user_prompt = "Flight EY123 on January 20th had a mechanical failure"
flight_info = structured_llm.invoke(user_prompt)
# Returns: FlightInfo(flight_number="EY123", date="2025-01-20", disruption_event="mechanical failure")
```

**Key Points:**

- NO custom parsing functions needed
- LangChain handles all date format conversions
- Pydantic models provide type safety and validation
- Agents autonomously extract data using their LLM capabilities

### Infrastructure Modules

**Database Layer** (`database/`)

- `DynamoDBClient`: Handles DynamoDB operations
- Tool factories: Create LangChain tools for each agent type

**MCP Client** (`mcp_client/`)

- `get_streamable_http_mcp_client()`: Returns configured MCP client
- `get_tools()`: Returns MCP tools for agent use

**Model Utilities** (`model/`)

- `load_model()`: Loads and configures Bedrock model

**Response Utilities** (`utils/`)

- `aggregate_agent_responses()`: Combines results from all agents
- `determine_status()`: Determines overall approval status

## Getting Started

### Prerequisites

- Python 3.11 or higher
- UV package manager ([installation guide](https://github.com/astral-sh/uv))
- AWS credentials configured
- Access to AWS Bedrock AgentCore
- DynamoDB tables (for operational data)
- MCP Gateway (for external tools)

### Installation

1. **Clone the repository:**

```bash
cd skymarshal_agents_new/skymarshal
```

2. **Install dependencies using UV:**

```bash
# UV will automatically create a virtual environment and install dependencies
uv sync
```

3. **Activate the virtual environment:**

```bash
source .venv/bin/activate
```

4. **Verify installation:**

```bash
uv run python3 -c "from main import app; print('✅ Installation successful')"
```

## UV Workflow

UV is a fast Python package and environment manager that replaces pip and virtualenv.

### Key UV Commands

**Dependency Management:**

```bash
# Add a new dependency
uv add <package-name>

# Add a development dependency
uv add --dev <package-name>

# Sync dependencies (install from lock file)
uv sync

# Update dependencies
uv lock --upgrade
```

**Running Commands:**

```bash
# Run a Python script
uv run python3 script.py

# Run a command-line tool
uv run pytest

# Run agentcore commands
uv run agentcore dev
uv run agentcore deploy
```

**Environment Management:**

```bash
# Create a new virtual environment (done automatically by uv sync)
uv venv

# Activate the virtual environment
source .venv/bin/activate

# Deactivate
deactivate
```

### Project Dependencies

The project uses the following key dependencies (see `pyproject.toml`):

- `bedrock-agentcore>=1.2.0` - AWS Bedrock AgentCore SDK
- `bedrock-agentcore-starter-toolkit>=0.2.8` - AgentCore starter templates
- `langchain>=1.2.7` - LangChain for tool creation
- `langgraph>=1.0.7` - Multi-agent orchestration
- `langchain-aws>=1.2.2` - AWS integrations for LangChain
- `mcp>=1.26.0` - Model Context Protocol
- `langchain-mcp-adapters>=0.2.1` - MCP adapters for LangChain
- `python-dotenv>=1.2.1` - Environment variable management
- `tiktoken>=0.11.0` - Token counting
- `aws-opentelemetry-distro>=0.10.0` - AWS observability

**Development Dependencies:**

- `pytest>=9.0.2` - Testing framework
- `pytest-asyncio>=1.3.0` - Async test support
- `hypothesis>=6.151.4` - Property-based testing

## Local Development

### Running the Development Server

Start the AgentCore development server:

```bash
# From the skymarshal/ directory
uv run agentcore dev
```

The server will start on `http://0.0.0.0:8080` (default port).

### Testing Locally

**Invoke the orchestrator:**

```bash
# In another terminal
uv run agentcore invoke --dev "Analyze flight disruption: EY123, 3hr delay"
```

**Invoke a specific agent:**

```bash
uv run agentcore invoke --dev --agent crew_compliance "Check crew compliance for 3hr delay"
```

**Test with a full payload:**

```bash
uv run agentcore invoke --dev --payload payload.json
```

### Sample Payload Structure

```json
{
  "agent": "orchestrator",
  "prompt": "Analyze this flight disruption",
  "disruption": {
    "flight_id": "1",
    "flight_number": "EY123",
    "delay_hours": 3,
    "flight": {
      "departure_airport": "AUH",
      "arrival_airport": "LHR",
      "scheduled_departure": "2024-01-15T10:00:00Z"
    },
    "weather": {
      "conditions": "Clear",
      "visibility": "10km"
    },
    "crew": [
      {
        "crew_id": "C001",
        "position": "Captain",
        "duty_hours": 8.5
      }
    ],
    "passengers": [
      {
        "passenger_id": "P001",
        "booking_class": "Business",
        "connection_flight": "EY456"
      }
    ],
    "cargo": [
      {
        "cargo_id": "CG001",
        "type": "General",
        "weight_kg": 500
      }
    ]
  }
}
```

### Running Tests

**Run all tests:**

```bash
uv run pytest
```

**Run specific test file:**

```bash
uv run pytest test/test_agent_imports.py
```

**Run with verbose output:**

```bash
uv run pytest -v
```

**Run with coverage:**

```bash
uv run pytest --cov=src --cov-report=html
```

### Code Quality

**Lint code with Ruff:**

```bash
uv run ruff check src/
```

**Format code with Ruff:**

```bash
uv run ruff format src/
```

**Fix linting issues automatically:**

```bash
uv run ruff check --fix src/
```

## Deployment

### Configure AgentCore

Before deploying, configure your agent settings:

```bash
uv run agentcore configure
```

This opens an interactive configuration wizard where you can set:

- AWS region and account
- Execution role
- Network configuration
- Observability settings
- Memory configuration

### Deploy to AWS Bedrock AgentCore

**Deploy the agent:**

```bash
uv run agentcore deploy
```

The deployment process will:

1. Package your source code
2. Upload to S3
3. Create or update the AgentCore agent
4. Configure execution role and permissions
5. Enable observability (if configured)

**Monitor deployment:**

```bash
# Check deployment status
uv run agentcore status

# View agent logs
uv run agentcore logs
```

### Invoke Deployed Agent

**Invoke the deployed agent:**

```bash
uv run agentcore invoke "Analyze flight disruption: EY123, 3hr delay"
```

**Invoke with a payload file:**

```bash
uv run agentcore invoke --payload payload.json
```

**Invoke a specific agent:**

```bash
uv run agentcore invoke --agent crew_compliance "Check crew compliance"
```

### Configuration File

The `.bedrock_agentcore.yaml` file contains deployment configuration:

```yaml
default_agent: skymarshal_Agent
agents:
  skymarshal_Agent:
    name: skymarshal_Agent
    language: python
    entrypoint: /path/to/src/main.py
    deployment_type: direct_code_deploy
    runtime_type: PYTHON_3_10
    aws:
      execution_role_auto_create: true
      account: "YOUR_ACCOUNT_ID"
      region: us-east-1
      s3_auto_create: true
      network_configuration:
        network_mode: PUBLIC
      observability:
        enabled: true
```

**Note:** Do not manually edit this file. Use `agentcore configure` to make changes.

### Checkpoint Persistence Configuration

SkyMarshal includes **checkpoint persistence** for durable state management, failure recovery, and complete audit trails. The system supports two modes:

#### Development Mode (Default)

In-memory checkpoints for fast iteration without AWS resources:

```bash
# .env
CHECKPOINT_MODE=development
```

**Features:**

- ✅ No AWS resources required
- ✅ Fast iteration and testing
- ✅ Automatic cleanup on restart
- ❌ No persistence across restarts
- ❌ No failure recovery

#### Production Mode

Durable checkpoints with DynamoDB + S3:

```bash
# .env
CHECKPOINT_MODE=production
CHECKPOINT_TABLE_NAME=SkyMarshalCheckpoints
CHECKPOINT_S3_BUCKET=skymarshal-checkpoints-<account-id>
CHECKPOINT_TTL_DAYS=90
```

**Features:**

- ✅ Durable persistence across restarts
- ✅ Failure recovery from last checkpoint
- ✅ Complete audit trail (90 days)
- ✅ Time-travel debugging
- ✅ Human-in-the-loop ready
- ✅ Automatic size-based routing (DynamoDB <350KB, S3 ≥350KB)

#### Infrastructure Setup

**Create DynamoDB Table:**

```bash
cd skymarshal_agents_new/skymarshal
uv run python scripts/create_checkpoint_table.py
```

**Create S3 Bucket:**

```bash
uv run python scripts/create_checkpoint_s3_bucket.py
```

**IAM Permissions Required:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/SkyMarshalCheckpoints"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::skymarshal-checkpoints-*/*"
    }
  ]
}
```

#### Checkpoint Usage

Checkpoints are automatically saved at key points:

- **Workflow Start**: Initial user prompt
- **Phase 1 Start/Complete**: Safety agent execution
- **Phase 2 Start/Complete**: Business agent execution
- **Phase 3 Start/Complete**: Arbitration decision
- **Agent Start/Complete/Error**: Individual agent checkpoints

**Access Thread History:**

```python
from checkpoint import CheckpointSaver

# Initialize checkpoint saver
checkpoint_saver = CheckpointSaver(mode="production")

# Get complete audit trail
history = await checkpoint_saver.get_thread_history(
    thread_id="<thread-id>",
    phase_filter="phase1",  # Optional: filter by phase
    agent_filter="crew_compliance"  # Optional: filter by agent
)

# List all checkpoints
checkpoints = await checkpoint_saver.list_checkpoints(
    thread_id="<thread-id>",
    status_filter="completed"  # Optional: filter by status
)
```

**Failure Recovery:**

```python
from checkpoint.recovery import recover_from_failure

# Recover from last successful checkpoint
result = await recover_from_failure(
    thread_id="<thread-id>",
    checkpoint_saver=checkpoint_saver
)
```

#### Migration Guide

For detailed migration instructions, see:

```python
from checkpoint.migration import migration_guide
print(migration_guide())
```

Or run migration tests:

```bash
cd skymarshal_agents_new/skymarshal
uv run python src/checkpoint/migration.py
```

**Key Points:**

- ✅ **Fully Backward Compatible**: All checkpoint parameters are optional
- ✅ **Zero Downtime**: Existing workflows continue to work
- ✅ **Gradual Migration**: Enable checkpoints incrementally
- ✅ **Easy Rollback**: Switch back to development mode anytime
- ✅ **Additive Only**: No breaking changes to existing functionality

## Common Tasks

### Adding a New Agent

1. **Create agent module:**

```bash
mkdir -p src/agents/new_agent
touch src/agents/new_agent/__init__.py
touch src/agents/new_agent/agent.py
```

2. **Implement agent in `agent.py`:**

```python
import logging
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Your agent's system prompt here...
"""

async def analyze_new_agent(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Analyzes a new aspect of flight disruption.
    """
    try:
        # Your agent logic here
        return {
            "agent": "new_agent",
            "category": "business",  # or "safety"
            "status": "success",
            "result": "Analysis result",
            "duration_seconds": 0.0
        }
    except Exception as e:
        logger.error(f"Error in new_agent: {e}")
        return {
            "agent": "new_agent",
            "category": "business",
            "status": "error",
            "error": str(e),
            "duration_seconds": 0.0
        }
```

3. **Export from `__init__.py`:**

```python
from .agent import analyze_new_agent

__all__ = ["analyze_new_agent"]
```

4. **Register in orchestrator (`src/main.py`):**

```python
from agents import analyze_new_agent

AGENT_REGISTRY = {
    # ... existing agents ...
    "new_agent": analyze_new_agent,
}

# Add to appropriate phase
BUSINESS_AGENTS = [
    # ... existing agents ...
    ("new_agent", analyze_new_agent),
]
```

5. **Create database tools (if needed) in `src/database/tools.py`:**

```python
def get_new_agent_tools() -> list:
    """Returns database tools for new agent."""
    return [
        Tool(
            name="query_new_data",
            func=lambda param: ...,
            description="Query new data"
        )
    ]
```

### Adding a New Dependency

```bash
# Add runtime dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Update lock file
uv lock
```

### Updating Dependencies

```bash
# Update all dependencies
uv lock --upgrade

# Update specific package
uv add package-name@latest

# Sync environment with updated lock file
uv sync
```

### Viewing Logs

**Local development logs:**

```bash
# Logs are printed to console when running agentcore dev
uv run agentcore dev
```

**Deployed agent logs:**

```bash
# View recent logs
uv run agentcore logs

# Follow logs in real-time
uv run agentcore logs --follow

# Filter logs by time
uv run agentcore logs --since 1h
```

### Testing Individual Agents

Create a test script to invoke a single agent:

```python
# test_single_agent.py
import asyncio
from agents.crew_compliance import analyze_crew_compliance
from model.load import load_model

async def test_agent():
    llm = load_model()
    payload = {
        "prompt": "Test crew compliance",
        "disruption": {
            "flight_id": "1",
            "delay_hours": 3
        }
    }
    result = await analyze_crew_compliance(payload, llm, [])
    print(result)

asyncio.run(test_agent())
```

Run it:

```bash
uv run python3 test_single_agent.py
```

## Troubleshooting

### Common Issues

#### Import Errors

**Problem:** `ModuleNotFoundError` when importing agents or modules

**Solution:**

```bash
# Ensure you're using uv run
uv run python3 script.py

# Or add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

#### UV Command Not Found

**Problem:** `uv: command not found`

**Solution:**

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

#### AgentCore Dev Mode Fails

**Problem:** Server fails to start or crashes

**Possible Causes:**

1. DynamoDB tables not accessible
2. MCP Gateway not running
3. AWS credentials not configured
4. Port 8080 already in use

**Solutions:**

```bash
# Check AWS credentials
aws sts get-caller-identity

# Check DynamoDB access
aws dynamodb list-tables

# Use a different port
uv run agentcore dev --port 8081

# Check logs for specific errors
uv run agentcore dev --log-level DEBUG
```

#### Deployment Fails

**Problem:** `agentcore deploy` fails

**Solutions:**

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check IAM permissions (need AgentCore permissions)
aws iam get-user

# Verify configuration
uv run agentcore configure

# Try with verbose logging
uv run agentcore deploy --verbose
```

#### Agent Timeout

**Problem:** Agent execution times out

**Solution:**
Adjust timeout in `src/main.py`:

```python
# Increase timeout from 60 to 120 seconds
result = await run_agent_safely(
    agent_name, agent_fn, payload, llm, mcp_tools, timeout=120
)
```

#### Database Connection Errors

**Problem:** Cannot connect to DynamoDB

**Solutions:**

```bash
# Check AWS credentials
aws configure list

# Verify DynamoDB endpoint
aws dynamodb describe-table --table-name your-table-name

# Check network connectivity
# Ensure security groups allow access
```

#### MCP Gateway Errors

**Problem:** MCP tools not available

**Solutions:**

```bash
# Verify MCP Gateway is running
curl http://your-mcp-gateway-url/health

# Check MCP client configuration in src/mcp_client/client.py
# Ensure gateway URL is correct
```

### Getting Help

**View AgentCore documentation:**

```bash
uv run agentcore --help
uv run agentcore deploy --help
```

**Check agent status:**

```bash
uv run agentcore status
```

**View detailed logs:**

```bash
uv run agentcore logs --verbose
```

**Test configuration:**

```bash
uv run agentcore validate
```

### Debug Mode

Enable debug logging for more detailed information:

```python
# In src/main.py or agent files
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:

```bash
export LOG_LEVEL=DEBUG
uv run agentcore dev
```

## Additional Resources

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangChain Documentation](https://python.langchain.com/)
- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [UV Documentation](https://github.com/astral-sh/uv)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Date Parsing Guide](docs/DATE_PARSING_GUIDE.md) - Comprehensive guide on how date parsing works in SkyMarshal

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Support

For issues and questions:

- Create an issue in the repository
- Contact the development team
- Check the troubleshooting section above
