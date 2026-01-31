# Architecture Clarification: Agent Tool Organization

## Summary

This document clarifies a critical architectural decision for the SkyMarshal Multi-Round Orchestration rearchitecture: **All DynamoDB query tools must be defined within each agent's implementation file, not in centralized modules.**

## Key Decision

**DO NOT** create or use:

- `src/database/dynamodb.py` for agent query methods
- `src/database/tools.py` for tool factory functions
- Any centralized tool generation or factory pattern

**DO** implement:

- Each agent defines its own DynamoDB query tools in its `agent.py` file
- Tools are LangChain Tool objects that use boto3 directly
- Tools are co-located with agent logic for better encapsulation

## Rationale

### Benefits of Per-Agent Tool Definition

1. **Better Encapsulation**: Each agent is self-contained with its own tools
2. **Clearer Code Organization**: Tools are co-located with the agent logic that uses them
3. **Easier to Understand**: No indirection through factory functions or shared modules
4. **Simpler Testing**: Test agent and its tools together as a unit
5. **Reduced Coupling**: Agents don't depend on shared tool modules
6. **Explicit Access Control**: Each agent explicitly defines what tables it accesses

### Problems with Centralized Tools

1. **Tight Coupling**: All agents depend on shared modules
2. **Indirection**: Hard to understand what tools an agent uses
3. **Maintenance Burden**: Changes to shared modules affect all agents
4. **Testing Complexity**: Must test factory logic separately from agent logic
5. **Hidden Dependencies**: Tool access patterns not visible in agent code

## Implementation Pattern

### Each Agent Should Follow This Pattern:

```python
# In src/agents/<agent_name>/agent.py

import boto3
from langchain.tools import Tool
from database.constants import (
    FLIGHTS_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    # Other constants as needed
)

def create_<agent_name>_tools():
    """Create DynamoDB query tools for this agent"""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights_table = dynamodb.Table(FLIGHTS_TABLE)
    # Other tables as needed

    def query_flight_by_number_date(flight_number: str, scheduled_departure: str):
        """Query flights table using flight-number-date-index GSI"""
        try:
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
        except Exception as e:
            return {"error": f"Failed to query flight: {str(e)}"}

    # Define other tool functions as needed

    return [
        Tool(
            name="query_flight_by_number_date",
            description="Query flight by flight number and date. Args: flight_number (str), scheduled_departure (str in YYYY-MM-DD format)",
            func=query_flight_by_number_date
        ),
        # Other tools
    ]

async def analyze_<agent_name>(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """Main agent function"""
    # Create agent-specific tools
    db_tools = create_<agent_name>_tools()

    # Combine with MCP tools
    all_tools = db_tools + mcp_tools

    # Agent logic using tools
    # ...
```

## Table Access Matrix

Each agent should only define tools for its authorized tables:

| Agent            | Authorized Tables                                                                         |
| ---------------- | ----------------------------------------------------------------------------------------- |
| Crew Compliance  | flights, CrewRoster, CrewMembers                                                          |
| Maintenance      | flights, MaintenanceWorkOrders, MaintenanceStaff, MaintenanceRoster, AircraftAvailability |
| Regulatory       | flights, CrewRoster, MaintenanceWorkOrders, Weather                                       |
| Network          | flights, AircraftAvailability                                                             |
| Guest Experience | flights, bookings, Baggage                                                                |
| Cargo            | flights, CargoFlightAssignments, CargoShipments                                           |
| Finance          | flights, bookings, CargoFlightAssignments, MaintenanceWorkOrders                          |

## GSI Usage

All tools must use Global Secondary Indexes (GSIs) to avoid table scans:

### Required GSIs:

1. **flights table**:
   - `flight-number-date-index`: (flight_number, scheduled_departure)
   - `aircraft-registration-index`: (aircraft_registration)

2. **bookings table**:
   - `flight-id-index`: (flight_id)

3. **MaintenanceWorkOrders table**:
   - `aircraft-registration-index`: (aircraftRegistration)

### Existing GSIs:

- CrewRoster: `flight-position-index`
- CargoFlightAssignments: `flight-loading-index`, `shipment-index`
- Baggage: `booking-index`, `location-status-index`

## Constants Module

The `src/database/constants.py` module remains useful for:

- Table name constants
- GSI name constants
- Agent table access permissions (for validation)

Agents should import constants to avoid hardcoding table and GSI names:

```python
from database.constants import (
    FLIGHTS_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    AIRCRAFT_REGISTRATION_INDEX
)
```

## Updated Task Status

### Task 5: Update DynamoDB Client with New Query Methods

**Status**: NOT APPLICABLE - Tools defined per-agent

### Task 6: Create Agent Tool Factory

**Status**: NOT APPLICABLE - No centralized factory

### Tasks 8-14: Agent Updates

**Status**: These tasks now include defining DynamoDB query tools within each agent

## Migration Notes

If any existing code uses centralized tools:

1. Identify which agents use which tools
2. Move tool definitions into respective agent.py files
3. Remove dependencies on `src/database/tools.py`
4. Update imports to use constants module only
5. Test each agent independently

## Validation

To validate this architecture:

1. Check that no agent imports from `src/database/tools.py`
2. Check that each agent defines its own tools in its agent.py file
3. Verify tools only access authorized tables
4. Confirm all queries use GSIs (no table scans)
5. Test each agent's tools independently

## Questions?

If you have questions about this architecture decision, refer to:

- Requirements document: Requirement 7 (updated)
- Design document: Section 6 (updated)
- Tasks document: Tasks 5 and 6 (marked NOT APPLICABLE)
