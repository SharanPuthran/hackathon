# SkyMarshal Orchestrator Architecture

## Overview

The SkyMarshal orchestrator is a **multi-agent system** deployed as a **single AgentCore instance** that coordinates 7 specialized agents to analyze flight disruptions. All agents run within the same runtime and share access to DynamoDB for real-time operational data.

## Key Design Decisions

### 1. Single AgentCore Instance

- **All 7 agents** run in one AgentCore deployment (`skymarshal_agents`)
- **Shared resources**: Model, MCP client, DynamoDB connection pool
- **Efficient**: No inter-service communication overhead
- **Cost-effective**: Single runtime, shared memory

### 2. Two-Phase Execution

```
Phase 1: Safety Agents (Parallel)
├── Crew Compliance
├── Maintenance
└── Regulatory
     │
     ├─ If BLOCKING → Stop, return CANNOT_PROCEED
     │
     └─ If OK → Continue to Phase 2

Phase 2: Business Agents (Parallel)
├── Network
├── Guest Experience
├── Cargo
└── Finance
     │
     └─ Aggregate all results → Return recommendations
```

### 3. DynamoDB Integration

- **16 operational tables** in `us-east-1`
- **Singleton client** with connection pooling
- **Agent-specific tools** for domain queries
- **GSI optimization** for fast lookups

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AgentCore Runtime (Single Instance)               │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  Orchestrator (main.py)                      │   │
│  │  - Receives disruption payload                               │   │
│  │  - Routes to agent functions                                 │   │
│  │  - Manages execution phases                                  │   │
│  │  - Aggregates results                                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Shared Resources (Singleton)                    │   │
│  │  - Bedrock Model (Claude Sonnet 4.5)                         │   │
│  │  - MCP Client (Gateway tools)                                │   │
│  │  - DynamoDB Client (Connection pool)                         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│         ┌────────────────────┴────────────────────┐                 │
│         ▼                                          ▼                 │
│  ┌─────────────────┐                    ┌─────────────────┐        │
│  │  Safety Agents  │                    │ Business Agents │        │
│  │  (Phase 1)      │                    │  (Phase 2)      │        │
│  │                 │                    │                 │        │
│  │ • Crew          │                    │ • Network       │        │
│  │ • Maintenance   │                    │ • Guest Exp     │        │
│  │ • Regulatory    │                    │ • Cargo         │        │
│  │                 │                    │ • Finance       │        │
│  └─────────────────┘                    └─────────────────┘        │
│         │                                          │                 │
│         └────────────────────┬────────────────────┘                 │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Database Tools (tools.py)                       │   │
│  │  - Crew tools: query_flight_crew_roster()                    │   │
│  │  - Maintenance tools: check_aircraft_availability()          │   │
│  │  - Network tools: query_flight_network()                     │   │
│  │  - Guest tools: query_flight_bookings()                      │   │
│  │  - Cargo tools: query_flight_cargo_manifest()                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
└──────────────────────────────┼───────────────────────────────────────┘
                               ▼
                    ┌──────────────────────┐
                    │   AWS DynamoDB       │
                    │   (us-east-1)        │
                    │                      │
                    │  16 Tables:          │
                    │  • Flights           │
                    │  • CrewMembers       │
                    │  • CrewRoster        │
                    │  • Aircraft...       │
                    │  • Bookings          │
                    │  • Cargo...          │
                    │  • Weather           │
                    └──────────────────────┘
```

---

## Component Details

### 1. Orchestrator (`src/main.py`)

**Responsibilities:**

- Route requests to appropriate agent(s)
- Execute safety agents in parallel (Phase 1)
- Check for blocking constraints
- Execute business agents in parallel (Phase 2)
- Aggregate results using `utils/response.py`

**Key Functions:**

```python
@app.entrypoint
async def invoke(payload):
    """Main entry point for all requests"""

async def analyze_all_agents(payload, llm, mcp_tools):
    """Orchestrator: runs all agents in two phases"""

async def run_agent_safely(agent_name, agent_fn, payload, llm, mcp_tools):
    """Execute agent with timeout and error handling"""
```

**Routing Logic:**

```python
if payload["agent"] == "orchestrator":
    # Run all agents (safety → business)
    return await analyze_all_agents(payload, llm, mcp_tools)
elif payload["agent"] in AGENT_REGISTRY:
    # Run specific agent
    return await run_agent_safely(agent_name, agent_fn, payload, llm, mcp_tools)
```

---

### 2. Agent Functions (`src/agents/*.py`)

Each agent is a **Python async function** with:

- **System prompt**: Comprehensive instructions (500-1000 lines)
- **Database tools**: Domain-specific query functions
- **LangChain agent**: Combines LLM + tools for reasoning

**Agent Structure:**

```python
async def analyze_crew_compliance(payload: dict, llm, mcp_tools: list) -> dict:
    """Crew Compliance agent analysis"""

    # Get domain-specific database tools
    db_tools = get_crew_compliance_tools()

    # Create LangChain agent with MCP + DB tools
    graph = create_agent(llm, tools=mcp_tools + db_tools)

    # Build message with system prompt
    message = f"{SYSTEM_PROMPT}\n\nUSER REQUEST:\n{payload['prompt']}"

    # Run agent
    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]})

    return {
        "agent": "crew_compliance",
        "category": "safety",
        "result": result["messages"][-1].content
    }
```

**Agents:**

1. **crew_compliance.py** - FTL limits, rest, qualifications (812 lines)
2. **maintenance.py** - Airworthiness, MEL, AOG (727+ lines)
3. **regulatory.py** - Weather, NOTAMs, curfews
4. **network.py** - Rotations, connections, propagation (1301+ lines)
5. **guest_experience.py** - Passengers, rebooking, VIP
6. **cargo.py** - Shipments, capacity, time-sensitive
7. **finance.py** - Costs, revenue, compensation

---

### 3. Database Layer (`src/database/`)

#### DynamoDB Client (`dynamodb.py`)

**Singleton pattern** for connection pooling:

```python
class DynamoDBClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        # Initialize 16 table references
        self.flights = self.dynamodb.Table('Flights')
        self.crew_members = self.dynamodb.Table('CrewMembers')
        # ... etc
```

**Query Methods:**

- Direct key lookups: `get_flight(flight_id)`
- GSI queries: `query_crew_roster_by_flight(flight_id)`
- Scan with filters: `query_maintenance_workorders(aircraft_reg)`

#### Database Tools (`tools.py`)

**LangChain tool factories** for each agent:

```python
def get_crew_compliance_tools():
    """Get database tools for crew compliance agent"""
    db = DynamoDBClient()

    @tool
    def query_flight_crew_roster(flight_id: str) -> str:
        """Query crew roster for a flight from DynamoDB"""
        roster = db.query_crew_roster_by_flight(flight_id)
        return db.to_json({"flight_id": flight_id, "roster": roster})

    @tool
    def query_crew_member_details(crew_id: str) -> str:
        """Query crew member details from DynamoDB"""
        crew = db.get_crew_member(crew_id)
        return db.to_json({"crew_id": crew_id, "crew_details": crew})

    return [query_flight_crew_roster, query_crew_member_details]
```

**Tool Sets:**

- Crew Compliance: 2 tools (roster, member details)
- Maintenance: 3 tools (availability, workorders, roster)
- Regulatory: 2 tools (weather, flight details)
- Network: 2 tools (impact, flight network)
- Guest Experience: 4 tools (bookings, baggage, passenger details)
- Cargo: 2 tools (shipment tracking, manifest)
- Finance: 1 tool (flight cost analysis)

---

### 4. Response Aggregation (`src/utils/response.py`)

**Aggregates results** from all agents:

```python
def aggregate_agent_responses(safety_results, business_results):
    """Aggregate responses from all agents"""
    return {
        "timestamp": datetime.now().isoformat(),
        "workflow_status": determine_status(safety_results),
        "safety_assessment": {
            "crew_compliance": extract_result(safety_results, "crew_compliance"),
            "maintenance": extract_result(safety_results, "maintenance"),
            "regulatory": extract_result(safety_results, "regulatory"),
            "blocking_constraints": extract_blocking_constraints(safety_results)
        },
        "business_assessment": {
            "network": extract_result(business_results, "network"),
            "guest_experience": extract_result(business_results, "guest_experience"),
            "cargo": extract_result(business_results, "cargo"),
            "finance": extract_result(business_results, "finance"),
            "impact_scores": calculate_impact_scores(business_results)
        },
        "recommendations": synthesize_recommendations(safety_results, business_results)
    }
```

**Status Determination:**

```python
def determine_status(safety_results):
    """Determine if operation can proceed"""
    for result in safety_results:
        if has_blocking_violation(result):
            return "CANNOT_PROCEED"
    return "CAN_PROCEED_WITH_CONSTRAINTS"
```

---

## Execution Flow

### Request Flow

```
1. User/System sends disruption payload
   ↓
2. Orchestrator receives payload via @app.entrypoint
   ↓
3. Load shared resources (model, MCP client, DB client)
   ↓
4. Route to agent(s) based on payload["agent"]
   ↓
5a. If "orchestrator": Run all agents in two phases
5b. If specific agent: Run that agent only
   ↓
6. Phase 1: Run safety agents in parallel
   ↓
7. Check for blocking constraints
   ↓
8. If blocked: Return CANNOT_PROCEED
   If OK: Continue to Phase 2
   ↓
9. Phase 2: Run business agents in parallel
   ↓
10. Aggregate all results
   ↓
11. Return unified response with recommendations
```

### Agent Execution Flow

```
1. Agent function called with payload, llm, mcp_tools
   ↓
2. Get domain-specific database tools
   ↓
3. Create LangChain agent with tools
   ↓
4. Build message with system prompt + user request
   ↓
5. Agent executes:
   a. Reads system prompt (instructions)
   b. Analyzes user request
   c. Decides which tools to call
   d. Calls database tools (queries DynamoDB)
   e. Processes results
   f. Generates assessment
   ↓
6. Return structured result
```

### Database Query Flow

```
1. Agent decides to query database
   ↓
2. Calls tool (e.g., query_flight_crew_roster)
   ↓
3. Tool invokes DynamoDB client method
   ↓
4. Client uses boto3 to query DynamoDB
   ↓
5. DynamoDB returns data (typically 20-50ms)
   ↓
6. Client converts Decimal to float
   ↓
7. Tool returns JSON string to agent
   ↓
8. Agent parses JSON and continues reasoning
```

---

## Performance Characteristics

### Timing Breakdown

```
Total Orchestrator Execution: 60-90 seconds
├── Resource Loading: 2-5s
│   ├── Model initialization: 1-2s
│   ├── MCP client setup: 0.5-1s
│   └── DB client (singleton): 0.5-1s
│
├── Phase 1 (Safety Agents): 30-45s
│   ├── Crew Compliance: 15-25s
│   │   ├── DB queries: 2-3s (2-3 queries × 20-50ms)
│   │   └── LLM reasoning: 13-22s
│   ├── Maintenance: 15-25s
│   │   ├── DB queries: 2-4s (3-4 queries × 20-50ms)
│   │   └── LLM reasoning: 13-21s
│   └── Regulatory: 10-20s
│       ├── DB queries: 1-2s (2 queries × 20-50ms)
│       └── LLM reasoning: 9-18s
│
├── Constraint Check: 0.1-0.5s
│
└── Phase 2 (Business Agents): 30-45s
    ├── Network: 20-30s
    ├── Guest Experience: 15-25s
    ├── Cargo: 10-20s
    └── Finance: 10-15s
```

### Optimization Strategies

1. **Parallel execution**: Safety agents run concurrently (3× speedup)
2. **Singleton DB client**: Reuse connections (no reconnection overhead)
3. **GSI queries**: Fast lookups with secondary indexes (<50ms)
4. **Timeout protection**: 60s timeout per agent prevents hangs
5. **Early termination**: Stop if safety agents block (save 30-45s)

---

## Data Flow

### Input Payload

```json
{
  "agent": "orchestrator",
  "prompt": "Analyze this flight disruption...",
  "disruption": {
    "flight": {
      "flight_number": "EY123",
      "origin": { "iata": "AUH" },
      "destination": { "iata": "LHR" }
    },
    "issue_details": {
      "description": "Hydraulic system fault",
      "estimated_delay_minutes": 180
    },
    "impact": {
      "passengers_affected": 615,
      "connecting_passengers": 87
    }
  }
}
```

### DynamoDB Queries (Example)

```python
# Crew Compliance Agent
crew_roster = db.query_crew_roster_by_flight("1")
# → GSI query on CrewRoster table
# → Returns: [{"crew_id": "5", "position_id": "1", ...}, ...]

crew_details = db.get_crew_member("5")
# → Direct key lookup on CrewMembers table
# → Returns: {"crew_id": "5", "name": "John Smith", ...}

# Maintenance Agent
aircraft = db.get_aircraft_availability("A6-APX", "2026-01-30T00:00:00Z")
# → Composite key lookup on AircraftAvailability table
# → Returns: {"aircraftRegistration": "A6-APX", "mel_items_json": "[...]", ...}

# Guest Experience Agent
bookings = db.query_bookings_by_flight("1", "Confirmed")
# → GSI query on Bookings table
# → Returns: [{"booking_id": "1", "passenger_id": "1", ...}, ...]
```

### Output Response

```json
{
  "timestamp": "2026-01-30T14:23:45Z",
  "workflow_status": "CAN_PROCEED_WITH_CONSTRAINTS",
  "safety_assessment": {
    "crew_compliance": {
      "agent": "crew_compliance",
      "status": "success",
      "result": "Crew FDP analysis: 8.5 hours remaining..."
    },
    "maintenance": {...},
    "regulatory": {...},
    "blocking_constraints": []
  },
  "business_assessment": {
    "network": {...},
    "guest_experience": {...},
    "cargo": {...},
    "finance": {...},
    "impact_scores": {
      "passenger_impact": "MEDIUM",
      "network_impact": "HIGH",
      "overall_score": 65
    }
  },
  "recommendations": [
    "Operation can proceed with constraints and mitigations",
    "Consider passenger rebooking options to minimize impact",
    "Monitor network propagation and implement delay containment"
  ]
}
```

---

## Deployment

### AgentCore Configuration (`.bedrock_agentcore.yaml`)

```yaml
default_agent: Skymarshal_Agent
agents:
  Skymarshal_Agent:
    name: Skymarshal_Agent
    language: python
    entrypoint: ./main.py
    deployment_type: direct_code_deploy
    runtime_type: PYTHON_3_13
    source_path: ./src
    aws:
      execution_role_auto_create: true
      network_configuration:
        network_mode: PUBLIC
      observability:
        enabled: true
```

### Deployment Commands

```bash
# Local development
cd skymarshal_agents
agentcore dev  # Starts on http://0.0.0.0:8080

# Deploy to AWS
agentcore deploy

# Invoke
agentcore invoke "Analyze disruption"
```

---

## Testing Strategy

### 1. Unit Tests (Database Layer)

```bash
python check_dynamodb_data.py
```

- Verify DynamoDB connectivity
- Check table data availability
- Test query performance

### 2. Integration Tests (Agent Tools)

```bash
python test_local_orchestrator.py
```

- Test database tools
- Test agent functions
- Test response aggregation

### 3. End-to-End Tests (Full Orchestrator)

```bash
python test_orchestrator_flow.py --mode orchestrator
```

- Test complete orchestrator flow
- Test all agents with real disruption
- Measure performance

### 4. Individual Agent Tests

```bash
python test_orchestrator_flow.py --agent crew_compliance
```

- Test specific agent in isolation
- Verify database queries
- Check output format

---

## Monitoring and Observability

### AgentCore Observability

- **Enabled by default** in `.bedrock_agentcore.yaml`
- Traces sent to AWS X-Ray
- Metrics sent to CloudWatch

### Custom Logging

```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Running {agent_name} agent...")
logger.error(f"Agent {agent_name} error: {e}")
```

### Performance Metrics

- Agent execution duration
- Database query count
- Database query latency
- Timeout occurrences
- Error rates

---

## Future Enhancements

### 1. Caching Layer

- Cache frequent queries (flights, crew, aircraft)
- TTL: 5 minutes
- Reduce DynamoDB costs

### 2. Streaming Responses

- Stream agent results as they complete
- Don't wait for all agents
- Improve perceived latency

### 3. Constraint Registry

- Shared constraint store
- Agents publish constraints
- Arbitrator queries constraints

### 4. Agent Prioritization

- Critical agents first
- Non-critical agents optional
- Adaptive timeout based on priority

### 5. Multi-Region Support

- DynamoDB global tables
- Regional AgentCore deployments
- Latency optimization

---

## Summary

The SkyMarshal orchestrator is a **sophisticated multi-agent system** that:

- ✅ Runs **7 specialized agents** in a **single AgentCore instance**
- ✅ Executes in **two phases** (safety → business) with **parallel execution**
- ✅ Queries **16 DynamoDB tables** for real-time operational data
- ✅ Provides **comprehensive disruption analysis** in **60-90 seconds**
- ✅ Returns **unified recommendations** with safety constraints and business trade-offs

The architecture is **efficient**, **scalable**, and **cost-effective**, leveraging AWS services (AgentCore, Bedrock, DynamoDB) for a production-ready airline disruption management system.
