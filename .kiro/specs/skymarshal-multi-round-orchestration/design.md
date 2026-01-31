# Design Document: SkyMarshal Multi-Round Orchestration

## Overview

This design document specifies the architecture for rearchitecting the SkyMarshal agent system from a two-phase execution model (safety → business) to a three-phase multi-round orchestration flow (initial recommendations → revision → arbitration). The new architecture improves decision quality through iterative refinement, implements sophisticated conflict resolution via a dedicated arbitrator agent, and optimizes data access patterns through improved DynamoDB schema design and agent-specific tool organization.

### Key Design Goals

1. **Multi-Round Deliberation**: Enable agents to refine recommendations based on cross-functional insights
2. **Intelligent Arbitration**: Resolve conflicts with safety-first principles using advanced reasoning
3. **Optimized Data Access**: Minimize query latency through strategic GSI placement
4. **Flexible Input Parsing**: Accept natural language date formats and disruption descriptions
5. **Maintainable Tool Organization**: Centralize agent permissions and table access patterns
6. **Complete Auditability**: Preserve full decision chains for regulatory compliance

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         End User                                 │
│  (Provides: Natural language prompt with flight, date, event)   │
│  Example: "Flight EY123 on Jan 20th had a mechanical failure"   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Orchestrator                                │
│  - Receives natural language prompt                              │
│  - Adds phase-specific instructions                              │
│  - Passes augmented prompt to agents                             │
│  - Three-phase execution coordination                            │
│  - Response collation only                                       │
│  - NO parsing, validation, or lookups                            │
└─────┬───────────────────────────────────────────────────────────┘
      │
      ├──────────────────────────────────────────────────────────┐
      │                                                            │
      ▼                                                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 1: Initial Recommendations              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Safety  │  │  Safety  │  │  Safety  │  │ Business │       │
│  │  Agent 1 │  │  Agent 2 │  │  Agent 3 │  │ Agents   │       │
│  │  (Crew)  │  │  (Maint) │  │  (Reg)   │  │ (4 more) │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│       │              │              │              │             │
│  Each agent:                                                     │
│  - Receives user prompt + instructions                           │
│  - Extracts flight info using structured output                 │
│  - Performs flight lookup                                       │
│  - Queries operational data                                     │
│  - Generates recommendation                                     │
│       │              │              │              │             │
│       └──────────────┴──────────────┴──────────────┘            │
│                          │                                       │
│                          ▼                                       │
│                   Collation 1                                    │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 2: Revision Round                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Agent 1 │  │  Agent 2 │  │  Agent 3 │  │  Agent N │       │
│  │ (Reviews │  │ (Reviews │  │ (Reviews │  │ (Reviews │       │
│  │  others) │  │  others) │  │  others) │  │  others) │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│       │              │              │              │             │
│       └──────────────┴──────────────┴──────────────┘            │
│                          │                                       │
│                          ▼                                       │
│                   Collation 2                                    │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 3: Arbitration                          │
│                                                                   │
│                    ┌──────────────┐                              │
│                    │  Arbitrator  │                              │
│                    │  (Opus 4.5)  │                              │
│                    │              │                              │
│                    │ - Conflict   │                              │
│                    │   Resolution │                              │
│                    │ - Safety     │                              │
│                    │   Priority   │                              │
│                    │ - Final      │                              │
│                    │   Decision   │                              │
│                    └──────────────┘                              │
│                          │                                       │
│                          ▼                                       │
│                  Final Response                                  │
└─────────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      End User                                    │
│  (Receives: recommendations, justification, reasoning)           │
└─────────────────────────────────────────────────────────────────┘
```

### Execution Flow

1. **Input Reception**: Orchestrator receives natural language prompt from user
2. **Phase 1 - Initial**:
   - Orchestrator adds instruction: "Please analyze this disruption and provide your initial recommendation"
   - All 7 agents receive augmented prompt, extract flight info, perform lookups, and analyze in parallel (async)
3. **Collation 1**: Orchestrator aggregates initial recommendations
4. **Phase 2 - Revision**:
   - Orchestrator adds instruction: "Review other agents' recommendations and revise if needed"
   - Orchestrator includes initial collation in the prompt
   - All 7 agents review and revise in parallel (async)
5. **Collation 2**: Orchestrator aggregates revised recommendations
6. **Phase 3 - Arbitration**: Arbitrator resolves conflicts and decides
7. **Response**: Return final decision to user

**Key Principle**: The orchestrator is a pure coordinator - it adds instructions to guide agents but does NOT parse input, extract fields, validate data, or perform any database lookups. All data extraction and querying is performed by individual agents.

## Components and Interfaces

### 1. Orchestrator

**Location**: `src/main.py`

**Responsibilities**:

- Accept natural language prompt from user
- Add phase-specific instructions to the user prompt
- Pass augmented prompt to all agents
- Invoke agents in three phases (initial, revision, arbitration)
- Collate agent responses after each phase
- Return final arbitrated decision to user
- Maintain audit trail of all phases

**NOT Responsible For**:

- Parsing or extracting fields from user input
- Validating flight numbers or dates
- Performing any database lookups or queries
- Data transformation or normalization

**CRITICAL DESIGN PRINCIPLE**: The orchestrator is a pure coordinator that operates on natural language prompts. It adds instructions to guide agents on how to process the prompt (e.g., "provide your initial recommendation" or "review other agents' recommendations and revise if needed"), but does NOT parse, extract, or validate the user's input. All data extraction and querying is performed autonomously by individual agents using their LLM capabilities and agent-specific tools.

**Interface**:

```python
async def handle_disruption(
    user_prompt: str
) -> dict:
    """
    Main entry point for disruption analysis.

    Args:
        user_prompt: Natural language prompt containing flight number,
                    date, and disruption description
                    Example: "Flight EY123 on January 20th had a mechanical failure"

    Returns:
        {
            "status": "success" | "error",
            "final_decision": dict,
            "audit_trail": list[dict],
            "timestamp": str
        }
    """
```

**Key Methods**:

```python
async def phase1_initial_recommendations(
    user_prompt: str
) -> dict:
    """
    Invoke all 7 agents in parallel with the user prompt plus instructions.

    Augmented prompt format:
        "{user_prompt}\n\nPlease analyze this disruption and provide your initial
        recommendation from your domain perspective."

    Agents are responsible for extracting flight info and performing lookups.
    Returns collated initial recommendations.
    """

async def phase2_revision_round(
    user_prompt: str,
    initial_collation: dict
) -> dict:
    """
    Invoke all 7 agents with user prompt, initial recommendations, and revision instructions.

    Augmented prompt format:
        "{user_prompt}\n\nOther agents have provided the following recommendations:
        {initial_collation}\n\nPlease review these recommendations and determine
        whether to revise your initial recommendation."

    Agents review others' recommendations and revise their own.
    Returns collated revised recommendations.
    """

async def phase3_arbitration(
    revised_collation: dict
) -> dict:
    """
    Invoke arbitrator with all revised recommendations.
    Returns final decision.
    """
```

### 2. Structured Output for Data Extraction

**Approach**: Agents use LangChain structured output to extract flight information from natural language prompts.

**Reference**: [LangChain Structured Output Documentation](https://docs.langchain.com/oss/python/langchain/structured-output)

**Pattern**: Each agent defines Pydantic models for the data it needs to extract, then uses LangChain's `with_structured_output()` to parse the natural language prompt into structured data.

**Example**:

```python
from pydantic import BaseModel, Field
from langchain_aws import ChatBedrock

class FlightInfo(BaseModel):
    """Structured flight information extracted from natural language."""
    flight_number: str = Field(description="Flight number (e.g., EY123)")
    date: str = Field(description="Flight date in ISO format (YYYY-MM-DD)")
    disruption_event: str = Field(description="Description of the disruption")

# Agent uses structured output to extract data
llm = ChatBedrock(model_id="anthropic.claude-sonnet-4-20250514-v1:0")
structured_llm = llm.with_structured_output(FlightInfo)

# Extract flight info from natural language prompt
flight_info = structured_llm.invoke(user_prompt)
# Returns: FlightInfo(flight_number="EY123", date="2025-01-20", disruption_event="mechanical failure")
```

**Key Principles**:

- NO custom extraction tools or parsing functions needed
- LangGraph agents handle data processing autonomously using their LLM capabilities
- Pydantic models define the structure of extracted data
- LangChain's structured output handles the extraction automatically
- Agents can define additional Pydantic models for other data structures they need

**Date/Time Utility** (`src/utils/datetime_tool.py`):

A simple utility provides current date/time for agents that need to resolve relative dates. The tool is created using LangChain's `@tool` decorator:

```python
from langchain_core.tools import tool

@tool
def get_current_datetime_tool() -> str:
    """Returns current UTC datetime for date resolution.

    Use this tool when you need to resolve relative dates like 'yesterday',
    'today', or 'tomorrow', or when you need the current date/time for context.

    Returns:
        str: Current UTC datetime in ISO 8601 format
    """
    return datetime.now(timezone.utc).isoformat()
```

This utility is available as a tool for agents but is NOT used for parsing - LangChain structured output handles all date parsing from natural language. The `@tool` decorator automatically creates a LangChain Tool with the function name and docstring as the tool's name and description.

### 3. Agent Interface

**Location**: `src/agents/<agent_name>/agent.py`

All agents follow a consistent async interface:

```python
async def analyze_<agent_name>(
    payload: dict,
    llm: ChatBedrock,
    tools: list
) -> dict:
    """
    Analyze disruption from agent's perspective.

    Args:
        payload: {
            "user_prompt": str,  # Raw natural language prompt
            "phase": "initial" | "revision",
            "other_recommendations": dict  # Only in revision phase
        }
        llm: Bedrock model instance (ChatBedrock)
        tools: Agent-specific DynamoDB query tools (LangChain Tool objects)

    Returns:
        {
            "agent_name": str,
            "recommendation": str,
            "confidence": float,
            "binding_constraints": list[str],  # Safety agents only
            "reasoning": str,
            "data_sources": list[str],
            "extracted_flight_info": {  # What agent extracted from prompt
                "flight_number": str,
                "date": str,
                "disruption_event": str
            }
        }

    Implementation Pattern:
        1. Define Pydantic model for structured data extraction
        2. Use llm.with_structured_output(Model) to extract flight info
        3. Create agent-specific DynamoDB query tools
        4. Let LangGraph agent autonomously use tools during reasoning
        5. Return structured response

    Example:
        class FlightInfo(BaseModel):
            flight_number: str
            date: str
            disruption_event: str

        structured_llm = llm.with_structured_output(FlightInfo)
        flight_info = structured_llm.invoke(payload["user_prompt"])

        # Agent uses flight_info and tools to generate recommendation
    """
```

**Agent-Specific Behavior**:

**Phase 1 (Initial)**:

- Receive raw natural language prompt from orchestrator
- Use LangChain structured output with Pydantic models to extract flight information
- LangGraph agent autonomously processes the prompt and extracts structured data
- Query flights table using extracted flight number and date
- Query relevant DynamoDB tables using flight_id
- Generate initial recommendation

**Phase 2 (Revision)**:

- Receive all initial recommendations from other agents
- Review other agents' findings
- Revise own recommendation if warranted
- Maintain domain priorities

**CRITICAL**: Agents are responsible for understanding and extracting information from natural language prompts. The orchestrator does NOT pre-process, parse, or extract any information. Each agent uses LangChain's structured output capabilities (see [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)) to autonomously extract structured data from natural language. NO custom extraction tools or parsing methods are needed - LangGraph agents handle all data processing using Pydantic dataclasses and LangChain's `with_structured_output()` method.

### 4. Arbitrator Agent

**Location**: `src/agents/arbitrator/agent.py`

**Model**: Claude Opus 4.5 (cross-region inference)

**Interface**:

```python
async def arbitrate(
    revised_recommendations: dict,
    llm_opus: Any
) -> dict:
    """
    Resolve conflicts and make final decision.

    Args:
        revised_recommendations: All agent recommendations after revision
        llm_opus: Opus 4.5 model instance

    Returns:
        {
            "final_decision": str,
            "recommendations": list[str],
            "conflicts_identified": list[dict],
            "conflict_resolutions": list[dict],
            "safety_overrides": list[dict],
            "justification": str,
            "reasoning": str,
            "confidence": float
        }
    """
```

**Arbitration Logic**:

1. **Identify Conflicts**: Compare agent recommendations for contradictions
2. **Safety Priority**: Extract binding constraints from safety agents
3. **Conflict Resolution**:
   - Safety vs Business: Always choose safety
   - Safety vs Safety: Choose most conservative
   - Business vs Business: Balance operational impact
4. **Decision Synthesis**: Generate coherent final recommendation
5. **Justification**: Explain all conflict resolutions

**Structured Output Schema**:

```python
class ArbitratorDecision(BaseModel):
    final_decision: str
    recommendations: list[str]
    conflicts_identified: list[ConflictDetail]
    conflict_resolutions: list[ResolutionDetail]
    safety_overrides: list[SafetyOverride]
    justification: str
    reasoning: str
    confidence: float
```

### 5. Database Client

**Location**: `src/database/dynamodb.py`

**ARCHITECTURE NOTE**: The DynamoDB client is a singleton that provides low-level table access. However, **agents do NOT use this client directly**. Instead, each agent defines its own DynamoDB query tools as LangChain Tool objects within its agent.py file.

**Purpose**: Provide connection pooling and table references for agents to use when defining their own tools.

**Usage Pattern**:

```python
# In agent.py file
import boto3
from langchain_core.tools import tool
from database.constants import FLIGHTS_TABLE, FLIGHT_NUMBER_DATE_INDEX

# Each agent defines its own tools using the @tool decorator
# This is the recommended LangChain pattern for creating tools

@tool
def query_flight_by_number_date(flight_number: str, scheduled_departure: str) -> dict:
    """Query flight by flight number and date using GSI.

    Args:
        flight_number: Flight number (e.g., EY123)
        scheduled_departure: Scheduled departure date in ISO format (YYYY-MM-DD)

    Returns:
        Flight record dict or None if not found
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights_table = dynamodb.Table(FLIGHTS_TABLE)

    response = flights_table.query(
        IndexName=FLIGHT_NUMBER_DATE_INDEX,
        KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
        ExpressionAttributeValues={
            ":fn": flight_number,
            ":sd": scheduled_departure,
        },
    )
    items = response.get("Items", [])
    return items[0] if items else None
```

**Note**: The `@tool` decorator is the recommended way to create LangChain tools. It automatically:

- Uses the function name as the tool name
- Uses the docstring as the tool description
- Infers the input schema from type hints
- Creates a Tool object that can be passed to agents

### 6. Agent Tool Definition Pattern

**ARCHITECTURE DECISION**: Each agent defines its own DynamoDB query tools directly in its agent.py file using the `@tool` decorator. There is NO centralized tool factory or shared tool module.

**Rationale**:

- Better encapsulation - each agent is self-contained
- Clearer code organization - tools are co-located with agent logic
- Easier to understand - no indirection through factory functions
- Simpler testing - test agent and its tools together
- LangGraph agents can use tools autonomously during reasoning
- `@tool` decorator is the recommended LangChain pattern for tool creation

**Table Access Matrix**:

| Agent            | Tables                                                                                    |
| ---------------- | ----------------------------------------------------------------------------------------- |
| Crew Compliance  | flights, CrewRoster, CrewMembers                                                          |
| Maintenance      | flights, MaintenanceWorkOrders, MaintenanceStaff, MaintenanceRoster, AircraftAvailability |
| Regulatory       | flights, CrewRoster, MaintenanceWorkOrders, Weather                                       |
| Network          | flights, AircraftAvailability                                                             |
| Guest Experience | flights, bookings, Baggage                                                                |
| Cargo            | flights, CargoFlightAssignments, CargoShipments                                           |
| Finance          | flights, bookings, CargoFlightAssignments, MaintenanceWorkOrders                          |

**Implementation Pattern**:

Each agent.py file should:

1. Define Pydantic models for structured data extraction
2. Define DynamoDB query tools as LangChain Tool objects
3. Use LangChain structured output to extract flight info from natural language
4. Let LangGraph agent autonomously use tools during reasoning
5. Only access tables authorized for that agent
6. Use GSI names from constants module for consistency

**Example Structure**:

```python
# In src/agents/crew_compliance/agent.py

import boto3
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_aws import ChatBedrock
from database.constants import (
    FLIGHTS_TABLE,
    CREW_ROSTER_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_POSITION_INDEX
)

# Define structured output model
class FlightInfo(BaseModel):
    """Flight information extracted from natural language."""
    flight_number: str = Field(description="Flight number")
    date: str = Field(description="Flight date in ISO format")
    disruption_event: str = Field(description="Disruption description")

# Define DynamoDB query tools using @tool decorator
# This is the recommended LangChain pattern

@tool
def query_flight(flight_number: str, date: str) -> dict:
    """Query flight by flight number and date using GSI.

    Args:
        flight_number: Flight number (e.g., EY123)
        date: Flight date in ISO format (YYYY-MM-DD)

    Returns:
        Flight record dict or None if not found
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights = dynamodb.Table(FLIGHTS_TABLE)

    response = flights.query(
        IndexName=FLIGHT_NUMBER_DATE_INDEX,
        KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
        ExpressionAttributeValues={":fn": flight_number, ":sd": date}
    )
    items = response.get("Items", [])
    return items[0] if items else None

@tool
def query_crew_roster(flight_id: str) -> list[dict]:
    """Query crew roster for a flight using GSI.

    Args:
        flight_id: Unique flight identifier

    Returns:
        List of crew member assignments for the flight
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    crew_roster = dynamodb.Table(CREW_ROSTER_TABLE)

    response = crew_roster.query(
        IndexName=FLIGHT_POSITION_INDEX,
        KeyConditionExpression="flight_id = :fid",
        ExpressionAttributeValues={":fid": flight_id}
    )
    return response.get("Items", [])

# Agent implementation
async def analyze_crew_compliance(payload: dict, llm: ChatBedrock, mcp_tools: list):
    """
    Analyze crew compliance for a disruption.

    The agent receives a natural language prompt and autonomously:
    1. Extracts flight info using structured output
    2. Queries DynamoDB using tools
    3. Generates recommendation
    """
    user_prompt = payload["user_prompt"]

    # Extract structured data from natural language
    structured_llm = llm.with_structured_output(FlightInfo)
    flight_info = structured_llm.invoke(user_prompt)

    # Tools are defined above using @tool decorator
    tools = [query_flight, query_crew_roster]

    # LangGraph agent uses tools autonomously during reasoning
    # Agent logic here...

    return {
        "agent_name": "crew_compliance",
        "recommendation": "...",
        "confidence": 0.95,
        "extracted_flight_info": flight_info.model_dump()
    }
```

**Key Points**:

- Agents use Pydantic models + `with_structured_output()` for data extraction
- Tools are created using the `@tool` decorator (recommended LangChain pattern)
- The decorator automatically creates Tool objects from functions with type hints and docstrings
- NO custom parsing functions or extraction tools needed
- LangGraph agents autonomously decide when to use DynamoDB query tools
- Data flows through Pydantic dataclasses for type safety
- See [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output) for details

### 7. Table Constants

**Location**: `src/database/constants.py`

**Purpose**: Centralize table names and GSI names

```python
# Table names
FLIGHTS_TABLE = "flights"
BOOKINGS_TABLE = "bookings"
CREW_ROSTER_TABLE = "CrewRoster"
CREW_MEMBERS_TABLE = "CrewMembers"
MAINTENANCE_WORK_ORDERS_TABLE = "MaintenanceWorkOrders"
MAINTENANCE_STAFF_TABLE = "MaintenanceStaff"
MAINTENANCE_ROSTER_TABLE = "MaintenanceRoster"
AIRCRAFT_AVAILABILITY_TABLE = "AircraftAvailability"
CARGO_FLIGHT_ASSIGNMENTS_TABLE = "CargoFlightAssignments"
CARGO_SHIPMENTS_TABLE = "CargoShipments"
BAGGAGE_TABLE = "Baggage"
WEATHER_TABLE = "Weather"

# GSI names
FLIGHT_NUMBER_DATE_INDEX = "flight-number-date-index"
AIRCRAFT_REGISTRATION_INDEX = "aircraft-registration-index"
FLIGHT_ID_INDEX = "flight-id-index"
FLIGHT_POSITION_INDEX = "flight-position-index"
FLIGHT_LOADING_INDEX = "flight-loading-index"
BOOKING_INDEX = "booking-index"

# Agent table access
AGENT_TABLE_ACCESS = {
    "crew_compliance": [
        FLIGHTS_TABLE,
        CREW_ROSTER_TABLE,
        CREW_MEMBERS_TABLE
    ],
    "maintenance": [
        FLIGHTS_TABLE,
        MAINTENANCE_WORK_ORDERS_TABLE,
        MAINTENANCE_STAFF_TABLE,
        MAINTENANCE_ROSTER_TABLE,
        AIRCRAFT_AVAILABILITY_TABLE
    ],
    "regulatory": [
        FLIGHTS_TABLE,
        CREW_ROSTER_TABLE,
        MAINTENANCE_WORK_ORDERS_TABLE,
        WEATHER_TABLE
    ],
    "network": [
        FLIGHTS_TABLE,
        AIRCRAFT_AVAILABILITY_TABLE
    ],
    "guest_experience": [
        FLIGHTS_TABLE,
        BOOKINGS_TABLE,
        BAGGAGE_TABLE
    ],
    "cargo": [
        FLIGHTS_TABLE,
        CARGO_FLIGHT_ASSIGNMENTS_TABLE,
        CARGO_SHIPMENTS_TABLE
    ],
    "finance": [
        FLIGHTS_TABLE,
        BOOKINGS_TABLE,
        CARGO_FLIGHT_ASSIGNMENTS_TABLE,
        MAINTENANCE_WORK_ORDERS_TABLE
    ]
}
```

## Data Models

### DynamoDB Schema Updates

**New GSIs Required**:

1. **flights table**:
   - `flight-number-date-index`: (flight_number, scheduled_departure)
   - `aircraft-registration-index`: (aircraft_registration)

2. **bookings table**:
   - `flight-id-index`: (flight_id)

3. **MaintenanceWorkOrders table**:
   - `aircraft-registration-index`: (aircraftRegistration)

**Existing GSIs (Maintained)**:

- CrewRoster: `flight-position-index`
- CargoFlightAssignments: `flight-loading-index`, `shipment-index`
- Baggage: `booking-index`, `location-status-index`

### Query Patterns

**Pattern 1: Flight Lookup**

```
User Input: flight_number + date
↓
Query: flights.flight-number-date-index
↓
Result: flight_id
```

**Pattern 2: Crew Data**

```
flight_id
↓
Query: CrewRoster.flight-position-index
↓
Result: crew assignments
```

**Pattern 3: Passenger Data**

```
flight_id
↓
Query: bookings.flight-id-index
↓
Result: passenger bookings
```

**Pattern 4: Baggage Data**

```
flight_id
↓
Query: bookings.flight-id-index → booking_ids
↓
Query: Baggage.booking-index (for each booking_id)
↓
Result: baggage records
```

**Pattern 5: Maintenance Data**

```
flight_id
↓
Query: flights → aircraft_registration
↓
Query: MaintenanceWorkOrders.aircraft-registration-index
↓
Result: maintenance work orders
```

**Pattern 6: Cargo Data**

```
flight_id
↓
Query: CargoFlightAssignments.flight-loading-index → shipment_ids
↓
Query: CargoShipments (by shipment_id)
↓
Result: cargo shipment details
```

### Agent Payload Schema

```python
class DisruptionPayload(BaseModel):
    user_prompt: str  # Raw natural language input
    phase: Literal["initial", "revision"]
    other_recommendations: Optional[dict] = None  # Only in revision phase

class AgentResponse(BaseModel):
    agent_name: str
    recommendation: str
    confidence: float
    binding_constraints: list[str] = []  # Safety agents only
    reasoning: str
    data_sources: list[str]
    extracted_flight_info: dict  # What agent extracted from prompt
    timestamp: str

class Collation(BaseModel):
    phase: Literal["initial", "revision"]
    responses: dict[str, AgentResponse]
    timestamp: str
```

### Arbitrator Input/Output Schema

```python
class ConflictDetail(BaseModel):
    agents_involved: list[str]
    conflict_type: Literal["safety_vs_business", "safety_vs_safety", "business_vs_business"]
    description: str

class ResolutionDetail(BaseModel):
    conflict: ConflictDetail
    resolution: str
    rationale: str

class SafetyOverride(BaseModel):
    safety_agent: str
    binding_constraint: str
    overridden_recommendations: list[str]

class ArbitratorInput(BaseModel):
    revised_recommendations: dict[str, AgentResponse]
    user_prompt: str  # Original prompt for context

class ArbitratorOutput(BaseModel):
    final_decision: str
    recommendations: list[str]
    conflicts_identified: list[ConflictDetail]
    conflict_resolutions: list[ResolutionDetail]
    safety_overrides: list[SafetyOverride]
    justification: str
    reasoning: str
    confidence: float
    timestamp: str
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Orchestrator Instruction Augmentation Invariant

**Validates: Requirements 1.6, 1.7, 9.2, 9.3, 9.4**

For all user prompts `p`, the orchestrator SHALL augment `p` with phase-specific instructions but NOT parse or extract data:

```
∀ prompt p, ∀ agent a, ∀ phase ph:
  orchestrator.invoke(a, p, ph) →
  a.receives(p + instruction(ph)) ∧
  user_content(p) == original_prompt ∧
  orchestrator.parses(p) = false
```

**Test Strategy**: Verify that agents receive the user's original prompt plus instructions, with no parsing, extraction, or data modification of the user's content.

### Property 2: Agent Autonomy Property

**Validates: Requirements 1.7, 2.1, 2.7**

All data extraction and lookups SHALL be performed by agents using LangChain structured output, not the orchestrator:

```
∀ operation o ∈ {parse, extract, validate, lookup}:
  orchestrator.performs(o) = false ∧
  agent.performs(o) = true ∧
  agent.uses_structured_output(o) = true
```

**Test Strategy**: Verify orchestrator code contains no parsing logic, validation logic, or database query calls. Verify agents use `with_structured_output()` for data extraction.

### Property 3: Flight Lookup Consistency

**Validates: Requirements 2.2, 2.3, 2.4**

When multiple agents extract the same flight information from a prompt, they SHALL retrieve the same flight_id:

```
∀ agents a1, a2, ∀ prompt p:
  a1.extract_flight(p) == a2.extract_flight(p) →
  a1.lookup_flight() == a2.lookup_flight()
```

**Test Strategy**: Generate prompts with flight information, invoke multiple agents, verify all agents identify the same flight_id.

### Property 4: GSI Query Optimization

**Validates: Requirements 3.6, 4.1-4.12**

All queries SHALL use GSIs and never perform table scans:

```
∀ query q: q.uses_gsi = true ∧ q.table_scan = false
```

**Test Strategy**: Monitor DynamoDB query metrics to ensure no table scans occur during agent execution.

### Property 5: Agent Table Access Restriction

**Validates: Requirements 7.1-7.8**

Agents SHALL only access their authorized tables:

```
∀ agent a, ∀ table t:
  a.queries(t) → t ∈ AGENT_TABLE_ACCESS[a.name]
```

**Test Strategy**: Attempt unauthorized table access from each agent, verify access is denied.

### Property 6: Three-Phase Execution Order

**Validates: Requirements 9, 10, 11**

The system SHALL execute phases in strict order: initial → revision → arbitration:

```
∀ execution e:
  e.phase1_complete → e.phase2_start ∧
  e.phase2_complete → e.phase3_start ∧
  ¬(e.phase2_start ∧ ¬e.phase1_complete) ∧
  ¬(e.phase3_start ∧ ¬e.phase2_complete)
```

**Test Strategy**: Verify phase transitions occur in order and no phase starts before the previous completes.

### Property 7: Parallel Agent Execution

**Validates: Requirements 9.1, 10.6**

Within each phase, all agents SHALL execute concurrently:

```
∀ phase p, ∀ agents a1, a2 ∈ p:
  start_time(a1) ≈ start_time(a2) ∧
  ¬(a1.complete → a2.start)
```

**Test Strategy**: Measure agent start times within a phase, verify they start within a small time window (< 100ms).

### Property 8: Safety Priority Invariant

**Validates: Requirements 11.3, 11.4, 13.1-13.3**

Safety agent binding constraints SHALL always be satisfied in the final decision:

```
∀ safety_agent s, ∀ binding_constraint c ∈ s.constraints:
  final_decision.satisfies(c) = true
```

**Test Strategy**: Generate scenarios where safety and business agents conflict, verify final decision always satisfies safety constraints.

### Property 9: Conservative Conflict Resolution

**Validates: Requirements 11.4, 11.5, 13.4**

When safety agents conflict, the arbitrator SHALL choose the most conservative option:

```
∀ safety_agents s1, s2, ∀ conflict c:
  s1.recommendation ≠ s2.recommendation →
  final_decision = most_conservative(s1.recommendation, s2.recommendation)
```

**Test Strategy**: Create conflicts between safety agents (e.g., crew compliance vs maintenance), verify arbitrator selects the more conservative option.

### Property 10: Audit Trail Completeness

**Validates: Requirements 15.1-15.5**

The system SHALL preserve a complete audit trail from input to final decision:

```
∀ execution e:
  audit_trail(e) = {
    user_prompt,
    phase1_responses,
    phase2_responses,
    arbitrator_decision,
    timestamps
  } ∧ all_fields_present(audit_trail(e))
```

**Test Strategy**: Execute disruption analysis, verify audit trail contains all required fields and can reconstruct the complete decision chain.

### Property 11: Graceful Degradation

**Validates: Requirements 16.1-16.5**

When agents fail, the system SHALL continue with available responses:

```
∀ execution e, ∀ failed_agents F:
  |F| < total_agents →
  e.continues_with(available_agents) ∧
  e.logs_failures(F)
```

**Test Strategy**: Simulate agent failures (timeout, exception), verify orchestrator continues and logs failures appropriately.

### Property 12: Structured Output Consistency

**Validates: Requirements 1.4, 1.8, 1.9, 1.10**

Agents SHALL use LangChain structured output to consistently extract data from natural language:

```
∀ prompts p1, p2 representing same flight f:
  agent.extract_with_structured_output(p1) == agent.extract_with_structured_output(p2) == f
```

**Test Strategy**: Provide the same flight information in different natural language phrasings, verify agents extract the same structured data using Pydantic models and `with_structured_output()`.

## Implementation Validation

### Unit Testing Strategy

1. **Orchestrator Tests**:
   - Verify prompt passthrough without modification
   - Verify no parsing/validation logic exists
   - Verify phase execution order
   - Verify collation logic

2. **Agent Tests**:
   - Test structured output extraction using Pydantic models
   - Test `with_structured_output()` with various natural language phrasings
   - Test GSI query construction
   - Test table access restrictions
   - Test recommendation generation
   - Verify agents use LangChain structured output, not custom parsing

3. **Arbitrator Tests**:
   - Test conflict identification
   - Test safety priority enforcement
   - Test conservative decision selection
   - Test structured output generation

4. **Database Tests**:
   - Verify GSI creation and activation
   - Validate GSI key schemas match requirements
   - Test GSI queries don't perform table scans
   - Test query patterns for each agent
   - Verify no table scans occur
   - Test foreign key relationship validation
   - Validate all required attributes present
   - Check data type consistency

### Integration Testing Strategy

1. **End-to-End Flow**:
   - Submit natural language prompt
   - Verify three-phase execution
   - Verify final decision structure
   - Verify audit trail completeness

2. **Multi-Agent Coordination**:
   - Test parallel execution within phases
   - Test collation accuracy
   - Test revision round with cross-agent insights

3. **Conflict Resolution**:
   - Test safety vs business conflicts
   - Test safety vs safety conflicts
   - Test conservative decision selection

### Property-Based Testing Strategy

1. **Prompt Invariance**: Generate random natural language prompts, verify orchestrator passes them unchanged
2. **Flight Lookup Consistency**: Generate prompts with same flight info in different phrasings, verify agents extract consistent structured data using `with_structured_output()`
3. **Structured Output Parsing**: Generate diverse natural language descriptions, verify Pydantic models extract correct data
4. **Safety Priority**: Generate random agent recommendations with safety constraints, verify arbitrator always satisfies safety
5. **Graceful Degradation**: Randomly fail agents, verify system continues with available responses

## Deployment Considerations

### Database Migration

1. Create new GSIs on existing tables (non-destructive)
2. Wait for GSI activation before deploying new code
3. Validate GSI configuration:
   - Verify all required GSIs exist
   - Check GSI status is ACTIVE
   - Validate GSI key schemas match design
   - Test sample queries use GSIs (no table scans)
4. Validate data integrity:
   - Check all required attributes present
   - Verify foreign key relationships
   - Identify and fix orphaned records
5. Validate GSI performance with sample queries
6. Monitor query latency and adjust provisioned capacity

### Agent Deployment

1. Deploy agents with updated tool configurations
2. Validate table access permissions
3. Test structured output extraction with sample prompts
4. Verify Pydantic models correctly extract flight information
5. Monitor agent execution times and timeout rates
6. Validate LangChain `with_structured_output()` integration

### Orchestrator Deployment

1. Deploy simplified orchestrator (no parsing logic)
2. Validate three-phase execution flow
3. Monitor collation performance
4. Test error handling and fallbacks

### Arbitrator Deployment

1. Configure Opus 4.5 cross-region inference endpoint
2. Test structured input/output schemas
3. Validate conflict resolution logic
4. Monitor arbitration latency

### Rollback Strategy

1. Keep existing two-phase orchestrator as fallback
2. Feature flag to switch between old and new flows
3. Monitor error rates and decision quality
4. Gradual rollout with canary deployment

## Performance Targets

- **Phase 1 (Initial)**: < 10 seconds for all 7 agents
- **Phase 2 (Revision)**: < 10 seconds for all 7 agents
- **Phase 3 (Arbitration)**: < 5 seconds
- **Total End-to-End**: < 30 seconds
- **Database Query Latency**: < 100ms per query (using GSIs)
- **Agent Timeout**: 30 seconds per agent
- **Concurrent Agent Execution**: All agents start within 100ms of each other

## Monitoring and Observability

### Key Metrics

1. **Execution Metrics**:
   - Phase execution times
   - Agent success/failure rates
   - Timeout rates per agent
   - End-to-end latency

2. **Database Metrics**:
   - Query latency per GSI
   - Table scan occurrences (should be 0)
   - Throttling events
   - Read capacity utilization

3. **Decision Quality Metrics**:
   - Safety constraint satisfaction rate
   - Conflict resolution frequency
   - Arbitrator confidence scores
   - Revision rate (how often agents revise)

4. **Error Metrics**:
   - Agent failure rates
   - Database query failures
   - Arbitrator failures
   - Fallback invocations

### Logging Strategy

1. **Structured Logging**: All logs in JSON format with correlation IDs
2. **Audit Trail**: Complete decision chain logged for every execution
3. **Performance Logging**: Timing data for each phase and agent
4. **Error Logging**: Detailed error context for debugging

### Alerting

1. **Critical Alerts**:
   - Arbitrator failure rate > 1%
   - Safety constraint violations
   - Database table scans detected
   - End-to-end latency > 60 seconds

2. **Warning Alerts**:
   - Agent timeout rate > 10%
   - Phase execution time > target
   - Database query latency > 200ms
   - Conflict resolution rate > 50%
