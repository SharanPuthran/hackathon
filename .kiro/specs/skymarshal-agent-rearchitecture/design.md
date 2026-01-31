# Design Document: SkyMarshal Agent Rearchitecture

## Overview

This design document describes the rearchitecture of the SkyMarshal agents system from its current monolithic structure to a modular, maintainable architecture based on the bedrock-agentcore-starter-toolkit. The new architecture will:

- Use UV for modern Python package and environment management
- Organize each agent as a separate importable Python module
- Maintain all existing functionality (7 agents, database integration, MCP client, orchestration)
- Enable incremental migration with validation at each stage
- Ensure compatibility with AWS Bedrock AgentCore deployment

The rearchitecture follows a staged migration approach: project initialization → core structure setup → agent-by-agent migration → integration testing → deployment validation.

## Architecture

### High-Level Structure

```
skymarshal_agents_new/
├── README.md                      # Project overview
└── skymarshal/                    # Main agent module
    ├── pyproject.toml             # UV-managed dependencies
    ├── uv.lock                    # Dependency lock file
    ├── .bedrock_agentcore.yaml    # AgentCore configuration
    └── src/
        ├── main.py                # Orchestrator entrypoint
        ├── __init__.py
        ├── agents/                # Agent modules
        │   ├── __init__.py
        │   ├── crew_compliance/
        │   │   ├── __init__.py
        │   │   └── agent.py
        │   ├── maintenance/
        │   │   ├── __init__.py
        │   │   └── agent.py
        │   ├── regulatory/
        │   │   ├── __init__.py
        │   │   └── agent.py
        │   ├── network/
        │   │   ├── __init__.py
        │   │   └── agent.py
        │   ├── guest_experience/
        │   │   ├── __init__.py
        │   │   └── agent.py
        │   ├── cargo/
        │   │   ├── __init__.py
        │   │   └── agent.py
        │   └── finance/
        │       ├── __init__.py
        │       └── agent.py
        ├── database/              # Database integration layer
        │   ├── __init__.py
        │   ├── dynamodb.py
        │   └── tools.py
        ├── mcp_client/            # MCP client integration
        │   ├── __init__.py
        │   └── client.py
        ├── model/                 # Model loading utilities
        │   ├── __init__.py
        │   └── load.py
        └── utils/                 # Shared utilities
            ├── __init__.py
            └── response.py
```

### Architectural Principles

1. **Modularity**: Each agent is a self-contained module with its own directory
2. **Separation of Concerns**: Clear boundaries between agents, database layer, MCP client, and orchestration
3. **Incremental Migration**: Migrate one component at a time with validation
4. **Backward Compatibility**: Maintain all existing interfaces and functionality
5. **Modern Tooling**: Use UV for fast, reliable dependency management

### Migration Stages

The rearchitecture follows these stages:

1. **Stage 1: Project Initialization**
   - Create new project structure using UV in the skymarshal/ subdirectory
   - Add bedrock-agentcore-starter-toolkit dependency
   - Configure AgentCore runtime
   - Create directory structure in skymarshal/src/
   - Validate with ruff

2. **Stage 2: Core Infrastructure**
   - Migrate database layer (dynamodb.py, tools.py) to skymarshal/src/database/
   - Migrate MCP client (client.py) to skymarshal/src/mcp_client/
   - Migrate model utilities (load.py) to skymarshal/src/model/
   - Migrate response utilities (response.py) to skymarshal/src/utils/
   - Validate with ruff and basic imports
   - Validate against Python, AgentCore, and LangGraph best practices

3. **Stage 3: Agent Migration (Safety Agents)**
   - Migrate crew_compliance agent module to skymarshal/src/agents/crew_compliance/
   - Migrate maintenance agent module to skymarshal/src/agents/maintenance/
   - Migrate regulatory agent module to skymarshal/src/agents/regulatory/
   - Validate each with ruff and local testing
   - Validate each against Python, AgentCore, and LangGraph best practices

4. **Stage 4: Agent Migration (Business Agents)**
   - Migrate network agent module to skymarshal/src/agents/network/
   - Migrate guest_experience agent module to skymarshal/src/agents/guest_experience/
   - Migrate cargo agent module to skymarshal/src/agents/cargo/
   - Migrate finance agent module to skymarshal/src/agents/finance/
   - Validate each with ruff and local testing
   - Validate each against Python, AgentCore, and LangGraph best practices

5. **Stage 5: Orchestrator Integration**
   - Migrate main.py orchestrator logic to skymarshal/src/main.py
   - Wire all agents together
   - Test full orchestration flow locally
   - Validate with agentcore development mode
   - Validate against Python, AgentCore, and LangGraph best practices

6. **Stage 6: Documentation and Deployment**
   - Update README.md
   - Document module structure
   - Document UV workflow
   - Test deployment to AgentCore

## Components and Interfaces

### 1. Orchestrator (main.py)

**Purpose**: Routes requests to appropriate agents and aggregates responses.

**Key Functions**:

- `invoke(payload)`: Main entrypoint decorated with @app.entrypoint
- `analyze_all_agents(payload, llm, mcp_tools)`: Runs all agents in two phases
- `run_agent_safely(agent_name, agent_fn, payload, llm, mcp_tools, timeout)`: Executes single agent with error handling

**Interfaces**:

```python
# Input payload structure
{
    "agent": "crew_compliance" | "orchestrator" | <agent_name>,
    "prompt": "User request...",
    "disruption": {
        "flight_id": "1",
        "flight_number": "EY123",
        "delay_hours": 3,
        ...
    }
}

# Output structure
{
    "status": "APPROVED" | "BLOCKED" | "error",
    "safety_assessments": [...],
    "business_assessments": [...],
    "timestamp": "ISO 8601",
    "total_duration_seconds": 12.5
}
```

**Agent Registry**:

```python
AGENT_REGISTRY = {
    "crew_compliance": analyze_crew_compliance,
    "maintenance": analyze_maintenance,
    "regulatory": analyze_regulatory,
    "network": analyze_network,
    "guest_experience": analyze_guest_experience,
    "cargo": analyze_cargo,
    "finance": analyze_finance,
}
```

### 2. Agent Modules

**Module Structure** (example: crew_compliance):

```
agents/crew_compliance/
├── __init__.py          # Exports analyze_crew_compliance
└── agent.py             # Implementation
```

**Agent Interface** (all agents follow this pattern):

```python
async def analyze_<agent_name>(payload: dict, llm, mcp_tools: list) -> dict:
    """
    Agent analysis function.

    Args:
        payload: Request payload with disruption data
        llm: Bedrock model instance
        mcp_tools: MCP tools from gateway

    Returns:
        dict: Structured assessment
    """
```

**Agent Implementation Pattern**:

1. Get agent-specific database tools
2. Combine with MCP tools
3. Create LangGraph agent with tools
4. Build message with system prompt + user request
5. Execute agent
6. Return structured response

**Note**: LangGraph is used for agent orchestration and management. LangChain is only used for basic functionality such as tool creation.

**System Prompt Storage**: Each agent module contains its complete system prompt as a module-level constant (e.g., `SYSTEM_PROMPT`).

### 3. Database Layer

**Files**:

- `database/dynamodb.py`: DynamoDB client implementation
- `database/tools.py`: Tool factory functions for each agent

**DynamoDB Client Interface**:

```python
class DynamoDBClient:
    def query_table(self, table_name: str, key_condition: dict) -> list
    def get_item(self, table_name: str, key: dict) -> dict
    def scan_table(self, table_name: str, filter_expression: dict = None) -> list
```

**Tool Factory Pattern**:

```python
def get_crew_compliance_tools() -> list:
    """Returns tools for crew compliance agent (LangChain Tool format for LangGraph compatibility)"""
    return [
        Tool(
            name="query_flight_crew_roster",
            func=lambda flight_id: ...,
            description="Get crew roster for a flight"
        ),
        Tool(
            name="query_crew_member_details",
            func=lambda crew_id: ...,
            description="Get crew member details"
        ),
    ]
```

### 4. MCP Client

**File**: `mcp_client/client.py`

**Interface**:

```python
def get_streamable_http_mcp_client():
    """Returns configured MCP client"""

async def get_tools() -> list:
    """Returns list of MCP tools (LangChain Tool format for LangGraph compatibility)"""
```

### 5. Model Utilities

**File**: `model/load.py`

**Interface**:

```python
def load_model():
    """Loads and returns configured Bedrock model instance"""
```

### 6. Response Utilities

**File**: `utils/response.py`

**Functions**:

```python
def aggregate_agent_responses(safety_results: list, business_results: list) -> dict:
    """Aggregates responses from all agents"""

def determine_status(results: list) -> str:
    """Determines overall status from agent results"""
    # Returns: "APPROVED" | "CANNOT_PROCEED" | "REQUIRES_ATTENTION"
```

## Data Models

### Best Practices Validation

**Purpose**: Ensure migrated code follows Python, AgentCore, and LangGraph best practices by fetching and referencing official documentation online.

**Documentation Sources**:

1. **LangGraph Official Documentation**:
   - Primary source: https://langchain-ai.github.io/langgraph/
   - Concepts: https://langchain-ai.github.io/langgraph/concepts/
   - How-to guides: https://langchain-ai.github.io/langgraph/how-tos/
   - API reference: https://langchain-ai.github.io/langgraph/reference/

2. **AgentCore Official Documentation**:
   - AWS Bedrock AgentCore documentation
   - AgentCore API reference
   - AgentCore deployment guides
   - AgentCore best practices documentation

3. **Python Best Practices**:
   - PEP 8 (Style Guide)
   - PEP 257 (Docstring Conventions)
   - Python typing documentation
   - Python asyncio documentation

**Validation Areas**:

1. **Python Best Practices**:
   - Type hints for function parameters and return values (PEP 484)
   - Proper async/await usage for asynchronous operations
   - Docstrings following PEP 257 conventions
   - Error handling with specific exception types
   - Resource management using context managers
   - Proper module organization and imports
   - Code style following PEP 8

2. **AgentCore Best Practices** (from fetched official documentation):
   - Proper use of @app.entrypoint decorator
   - Correct BedrockAgentCoreApp initialization
   - Proper configuration in .bedrock_agentcore.yaml
   - Appropriate use of AgentCore runtime features
   - Correct deployment patterns
   - Proper observability integration
   - Memory and browser service integration patterns
   - Gateway configuration for external tools

3. **LangGraph Best Practices** (from fetched official documentation):
   - Proper graph construction and state management
   - Correct use of StateGraph and MessageGraph
   - Appropriate tool integration patterns (ToolNode usage)
   - Proper error handling in graph execution
   - Correct use of checkpointing and persistence
   - Appropriate use of conditional edges and routing
   - Proper use of prebuilt components (create_react_agent, etc.)
   - Correct streaming patterns

**Validation Process**:

1. **Documentation Fetching**:
   - Use web search and fetch tools to retrieve official documentation
   - Search for specific topics: "LangGraph tool integration", "AgentCore entrypoint decorator", etc.
   - Verify documentation sources are official (langchain-ai.github.io, AWS docs)
   - Cache relevant documentation sections for reference

2. **Code Analysis**:
   - Review migrated code against fetched documentation patterns
   - Compare implementation with official examples
   - Identify usage of deprecated patterns or APIs

3. **Pattern Matching**:
   - Identify deviations from recommended patterns
   - Check for missing type hints, docstrings, error handling
   - Verify proper use of framework-specific decorators and classes
   - Check for proper async/await usage

4. **Impact Assessment**:
   - Determine if deviations affect functionality
   - Assess risk of applying improvements
   - Prioritize improvements by impact and safety

5. **Improvement Implementation**:
   - Apply improvements where safe and beneficial
   - Add type hints to function signatures
   - Add or improve docstrings
   - Replace deprecated patterns with current best practices
   - Improve error handling specificity

6. **Documentation**:
   - Record validation findings with references to official docs
   - Document improvements made
   - Note any deviations that were intentionally kept
   - Create validation report for each migration stage

**Validation Timing**:

- After migrating core infrastructure (Stage 2)
- After migrating each agent (Stages 3-4)
- After orchestrator integration (Stage 5)
- Before final deployment (Stage 6)

**Example Improvements**:

- Adding type hints: `def analyze_agent(payload: dict, llm: Any, tools: list[Tool]) -> dict:`
- Improving error handling: Replace generic `except Exception` with specific exception types
- Adding docstrings: Document function purpose, parameters, and return values
- Using AgentCore patterns: Ensure proper use of @app.entrypoint decorator per official docs
- Using LangGraph patterns: Use ToolNode for tool integration instead of manual tool calling
- Async patterns: Ensure proper use of async/await for I/O operations
- State management: Use proper TypedDict for graph state definitions

**Validation Output Format**:

For each validation, produce a report:

```markdown
## Validation Report: [Component Name]

### Documentation Sources Consulted

- [URL 1]: [Topic]
- [URL 2]: [Topic]

### Findings

1. **Issue**: [Description]
   - **Reference**: [Official doc URL and section]
   - **Current Code**: [Code snippet]
   - **Recommended**: [Improved code snippet]
   - **Action**: [Applied/Deferred/Not Applicable]

### Improvements Applied

- [List of improvements made]

### Deviations Kept

- [List of intentional deviations with justification]
```

### Agent Response Model

All agents return responses following this structure:

```python
{
    "agent": str,                    # Agent name
    "category": str,                 # "safety" or "business"
    "status": str,                   # "success" | "error" | "timeout"
    "result": str | dict,            # Agent-specific result
    "duration_seconds": float,       # Execution time
    "error": str | None,             # Error message if failed
    "error_type": str | None         # Error type if failed
}
```

### Orchestrator Response Model

```python
{
    "status": str,                   # "APPROVED" | "BLOCKED" | "error"
    "safety_assessments": list,      # Results from safety agents
    "business_assessments": list,    # Results from business agents
    "reason": str | None,            # Reason if blocked
    "timestamp": str,                # ISO 8601 timestamp
    "phase1_duration_seconds": float,
    "phase2_duration_seconds": float,
    "total_duration_seconds": float,
    "request_duration_seconds": float
}
```

### Disruption Payload Model

```python
{
    "agent": str,                    # Target agent or "orchestrator"
    "prompt": str,                   # User request
    "disruption": {
        "flight_id": str,
        "flight_number": str,
        "delay_hours": int,
        "flight": dict,              # Flight details
        "weather": dict,             # Weather data
        "crew": list,                # Crew roster
        "passengers": list,          # Passenger list
        "cargo": list,               # Cargo manifest
        ...
    }
}
```

### Database Tool Response Models

**Crew Roster Query**:

```python
{
    "flight_id": str,
    "crew_members": [
        {
            "crew_id": str,
            "position": str,
            "duty_start": str,
            "duty_end": str,
            "roster_status": str
        }
    ]
}
```

**Crew Member Details**:

```python
{
    "crew_id": str,
    "name": str,
    "base_airport": str,
    "type_ratings": list,
    "medical_cert_expiry": str,
    "license_expiry": str,
    "recency_last_flight": str
}
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Module Import Integrity

_For any_ agent module in the agents directory, importing its analysis function should succeed without errors and return a callable function.

**Validates: Requirements 2.2, 2.5**

### Property 2: Code Quality Compliance

_For all_ Python files in the project, running ruff linting should return zero errors and zero warnings.

**Validates: Requirements 4.3**

### Property 3: Structural Completeness

_For the_ rearchitected project, all required components should exist:

- Seven agent modules (crew_compliance, maintenance, regulatory, network, guest_experience, cargo, finance)
- Database layer (dynamodb.py, tools.py)
- MCP client (client.py)
- Model utilities (load.py)
- Response utilities (response.py)
- Orchestrator (main.py)
- Configuration files (pyproject.toml, uv.lock, .bedrock_agentcore.yaml)

**Validates: Requirements 2.1, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 6.5, 9.1**

### Property 4: Agent Response Structure

_For any_ agent invocation with a valid payload, the agent should return a dictionary containing the required fields: "agent", "category", "status", and either "result" or "error".

**Validates: Requirements 5.4**

### Property 5: Dependency Compatibility

_For the_ project configuration, all required dependencies should be present in pyproject.toml with compatible version constraints: bedrock-agentcore >= 1.0.3, langchain >= 1.0.3, langgraph >= 1.0.2, mcp >= 1.19.0.

**Validates: Requirements 1.2, 3.7**

### Property 6: Orchestrator Component Preservation

_For the_ orchestrator in main.py, all required components should be present:

- AGENT_REGISTRY dictionary with 7 agents
- SAFETY_AGENTS list with 3 agents
- BUSINESS_AGENTS list with 4 agents
- analyze_all_agents function
- run_agent_safely function with timeout parameter
- invoke function with @app.entrypoint decorator

**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 9.2, 9.3**

### Property 7: Database Integration Preservation

_For the_ database layer, all required components should be present:

- DynamoDBClient class with query_table, get_item, scan_table methods
- Tool factory functions for all 7 agent types (get_crew_compliance_tools, get_maintenance_tools, etc.)
- Each tool factory should return a list of tools in LangChain Tool format (for LangGraph compatibility)

**Validates: Requirements 8.1, 8.2, 8.3, 8.5**

### Property 8: AWS Configuration Completeness

_For the_ .bedrock_agentcore.yaml file, all required AWS configuration fields should be present: execution_role_auto_create, account, region, s3_auto_create, network_configuration, protocol_configuration, observability.

**Validates: Requirements 9.5**

### Property 9: Documentation Completeness

_For the_ README.md file, all required documentation sections should be present: project structure overview, module organization, UV workflow instructions, local testing instructions, and deployment instructions.

**Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5**

### Property 10: Agent System Prompt Preservation

_For any_ agent module, the SYSTEM_PROMPT constant should exist and contain the original prompt content including regulatory frameworks, calculation rules, chain-of-thought processes, and example scenarios.

**Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.5**

### Property 11: Best Practices Compliance

_For all_ migrated Python files, the code should follow Python best practices (type hints, docstrings, proper async/await), AgentCore best practices (proper decorator usage, configuration), and LangGraph best practices (proper graph construction, tool integration) as documented in official framework documentation fetched from online sources.

**Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9**

### Property 12: Documentation Source Verification

_For all_ validation activities, the documentation sources used should be official sources (langchain-ai.github.io for LangGraph, AWS official documentation for AgentCore) and should be fetched online during the validation process.

**Validates: Requirements 13.2, 13.3, 13.9**

## Error Handling

### Migration Errors

**UV Initialization Failures**:

- If UV is not installed: Provide clear error message with installation instructions
- If project initialization fails: Log error details and suggest manual initialization steps
- Mitigation: Check UV installation before starting migration

**Dependency Resolution Failures**:

- If bedrock-agentcore-starter-toolkit cannot be found: Verify package name and repository access
- If version conflicts occur: Adjust version constraints in pyproject.toml
- Mitigation: Use UV's dependency resolver to identify conflicts

**Import Errors During Migration**:

- If agent imports fail: Check module structure and **init**.py exports
- If database/MCP imports fail: Verify file paths and module names
- Mitigation: Test imports after each migration stage

### Runtime Errors

**Agent Execution Failures**:

- Timeout errors: Logged with duration, agent continues with timeout status
- Exception errors: Logged with full traceback, agent returns error response
- Mitigation: run_agent_safely wrapper provides timeout and error handling

**Database Connection Failures**:

- DynamoDB unavailable: Agent returns error response with connection details
- Query failures: Logged with query parameters, agent continues with partial data
- Mitigation: Implement retry logic with exponential backoff

**MCP Client Failures**:

- MCP server unavailable: Agent continues without MCP tools
- Tool execution failures: Logged with tool name and parameters
- Mitigation: Graceful degradation when MCP tools unavailable

### Validation Errors

**Ruff Linting Failures**:

- Syntax errors: Fix immediately before proceeding
- Style violations: Fix or configure ruff to ignore if intentional
- Import errors: Verify all imports are correct
- Mitigation: Run ruff after each file migration

**AgentCore Deployment Failures**:

- Configuration errors: Validate .bedrock_agentcore.yaml structure
- AWS credential errors: Verify AWS configuration and permissions
- Runtime errors: Check logs for specific error messages
- Mitigation: Test deployment in development mode before production

## Testing Strategy

### Dual Testing Approach

The rearchitecture will use both unit tests and property-based tests to ensure comprehensive validation:

**Unit Tests**: Verify specific examples, edge cases, and integration points

- Test specific agent imports
- Test orchestrator routing with known payloads
- Test database tool creation
- Test error handling scenarios
- Test configuration file parsing

**Property Tests**: Verify universal properties across all inputs

- Test that all agent modules can be imported (Property 1)
- Test that all code passes ruff linting (Property 2)
- Test structural completeness (Property 3)
- Test agent response structure for various payloads (Property 4)
- Test dependency compatibility (Property 5)

### Property-Based Testing Configuration

**Library**: Use `hypothesis` for Python property-based testing

**Configuration**:

- Minimum 100 iterations per property test
- Each test tagged with feature name and property number
- Tag format: `# Feature: skymarshal-agent-rearchitecture, Property N: <property_text>`

**Example Property Test**:

```python
from hypothesis import given, strategies as st
import importlib

@given(agent_name=st.sampled_from([
    "crew_compliance", "maintenance", "regulatory",
    "network", "guest_experience", "cargo", "finance"
]))
def test_agent_module_import_integrity(agent_name):
    """
    Feature: skymarshal-agent-rearchitecture, Property 1: Module Import Integrity
    For any agent module, importing its analysis function should succeed
    """
    module = importlib.import_module(f"agents.{agent_name}")
    analyze_fn = getattr(module, f"analyze_{agent_name}")
    assert callable(analyze_fn)
```

### Testing Stages

**Stage 1: Project Initialization Tests**

- Verify UV project structure created
- Verify pyproject.toml contains required dependencies
- Verify .bedrock_agentcore.yaml exists
- Run ruff on initial structure

**Stage 2: Core Infrastructure Tests**

- Test database layer imports
- Test MCP client imports
- Test model utilities imports
- Test response utilities imports
- Run ruff on migrated files

**Stage 3: Agent Migration Tests (per agent)**

- Test agent module import
- Test agent analysis function signature
- Test agent with sample payload
- Verify system prompt preserved
- Run ruff on agent files

**Stage 4: Integration Tests**

- Test orchestrator with all agents
- Test two-phase execution
- Test parallel agent execution
- Test response aggregation
- Test error handling and timeouts

**Stage 5: Deployment Tests**

- Test agentcore development mode
- Test local agent invocation
- Test deployment to AgentCore
- Verify AWS configuration

### Test Coverage Goals

- **Unit test coverage**: >80% of code lines
- **Property test coverage**: All 10 correctness properties
- **Integration test coverage**: All agent execution paths
- **End-to-end test coverage**: Full orchestrator flow with sample disruptions

### Validation Checklist

After each migration stage:

1. ✅ All files pass ruff linting (zero errors)
2. ✅ All imports succeed without errors
3. ✅ All unit tests pass
4. ✅ All property tests pass (100+ iterations each)
5. ✅ Agent responds correctly to test invocations
6. ✅ No regression in existing functionality
7. ✅ Official documentation fetched and reviewed for relevant topics
8. ✅ Code follows Python best practices (type hints, docstrings, async/await)
9. ✅ Code follows AgentCore best practices (decorators, configuration) per official docs
10. ✅ Code follows LangGraph best practices (graph construction, tool integration) per official docs
11. ✅ Validation findings documented with references to official documentation
12. ✅ Improvements applied where safe and beneficial
13. ✅ Validation report created for the migration stage
