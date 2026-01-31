# SkyMarshal Orchestrator Flow Diagram

## Complete System Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER / SYSTEM                                   │
│                                                                              │
│  Sends disruption payload:                                                   │
│  {                                                                           │
│    "agent": "orchestrator",                                                  │
│    "disruption": {                                                           │
│      "flight": {"flight_number": "EY123", ...},                             │
│      "issue_details": {"delay_minutes": 180, ...}                           │
│    }                                                                         │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AWS BEDROCK AGENTCORE RUNTIME                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                  ORCHESTRATOR (main.py)                             │    │
│  │                                                                     │    │
│  │  @app.entrypoint                                                    │    │
│  │  async def invoke(payload):                                         │    │
│  │      1. Load shared resources (model, MCP, DB)                      │    │
│  │      2. Route to agent(s)                                           │    │
│  │      3. Execute phases                                              │    │
│  │      4. Aggregate results                                           │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │              SHARED RESOURCES (Singleton)                           │    │
│  │                                                                     │    │
│  │  • Bedrock Model: Claude Sonnet 4.5                                │    │
│  │  • MCP Client: Gateway tools                                       │    │
│  │  • DynamoDB Client: Connection pool                                │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    PHASE 1: SAFETY AGENTS                           │    │
│  │                      (Parallel Execution)                           │    │
│  │                                                                     │    │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │    │
│  │  │ Crew Compliance  │  │   Maintenance    │  │   Regulatory     │ │    │
│  │  │                  │  │                  │  │                  │ │    │
│  │  │ • Query crew     │  │ • Query aircraft │  │ • Query weather  │ │    │
│  │  │   roster         │  │   availability   │  │ • Check curfews  │ │    │
│  │  │ • Check FTL      │  │ • Check MEL      │  │ • Verify slots   │ │    │
│  │  │ • Verify quals   │  │ • Assess AOG     │  │                  │ │    │
│  │  │                  │  │                  │  │                  │ │    │
│  │  │ Duration: 15-25s │  │ Duration: 15-25s │  │ Duration: 10-20s │ │    │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘ │    │
│  │           │                     │                     │             │    │
│  │           └─────────────────────┴─────────────────────┘             │    │
│  │                                 │                                   │    │
│  └─────────────────────────────────┼───────────────────────────────────┘    │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │              CONSTRAINT CHECK (response.py)                         │    │
│  │                                                                     │    │
│  │  def determine_status(safety_results):                             │    │
│  │      if has_blocking_violation(result):                            │    │
│  │          return "CANNOT_PROCEED"                                   │    │
│  │      return "CAN_PROCEED_WITH_CONSTRAINTS"                         │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                    ┌───────────────┴───────────────┐                        │
│                    ▼                               ▼                        │
│         ┌──────────────────┐           ┌──────────────────┐                │
│         │   BLOCKED        │           │   OK TO PROCEED  │                │
│         │                  │           │                  │                │
│         │ Return:          │           │ Continue to      │                │
│         │ CANNOT_PROCEED   │           │ Phase 2          │                │
│         │                  │           │                  │                │
│         │ Skip Phase 2     │           │                  │                │
│         └──────────────────┘           └──────────────────┘                │
│                                                 │                           │
│                                                 ▼                           │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                  PHASE 2: BUSINESS AGENTS                           │    │
│  │                    (Parallel Execution)                             │    │
│  │                                                                     │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────┐ │    │
│  │  │   Network    │  │    Guest     │  │    Cargo     │  │Finance │ │    │
│  │  │              │  │  Experience  │  │              │  │        │ │    │
│  │  │ • Rotations  │  │ • Bookings   │  │ • Shipments  │  │ • Cost │ │    │
│  │  │ • Connections│  │ • Passengers │  │ • Manifest   │  │ • Rev  │ │    │
│  │  │ • Propagation│  │ • Baggage    │  │ • Priority   │  │        │ │    │
│  │  │              │  │              │  │              │  │        │ │    │
│  │  │ 20-30s       │  │ 15-25s       │  │ 10-20s       │  │ 10-15s │ │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────┘ │    │
│  │         │                 │                 │               │       │    │
│  │         └─────────────────┴─────────────────┴───────────────┘       │    │
│  │                                 │                                   │    │
│  └─────────────────────────────────┼───────────────────────────────────┘    │
│                                    ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │            RESULT AGGREGATION (response.py)                         │    │
│  │                                                                     │    │
│  │  def aggregate_agent_responses(safety, business):                  │    │
│  │      return {                                                      │    │
│  │          "workflow_status": status,                                │    │
│  │          "safety_assessment": {...},                               │    │
│  │          "business_assessment": {...},                             │    │
│  │          "recommendations": [...]                                  │    │
│  │      }                                                              │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED RESPONSE                                     │
│                                                                              │
│  {                                                                           │
│    "timestamp": "2026-01-30T14:23:45Z",                                     │
│    "workflow_status": "CAN_PROCEED_WITH_CONSTRAINTS",                       │
│    "safety_assessment": {                                                   │
│      "crew_compliance": {...},                                              │
│      "maintenance": {...},                                                  │
│      "regulatory": {...},                                                   │
│      "blocking_constraints": []                                             │
│    },                                                                        │
│    "business_assessment": {                                                 │
│      "network": {...},                                                      │
│      "guest_experience": {...},                                             │
│      "cargo": {...},                                                        │
│      "finance": {...}                                                       │
│    },                                                                        │
│    "recommendations": [...]                                                 │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Query Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENT EXECUTION                                 │
│                                                                              │
│  Agent decides to query database                                             │
│  Example: "I need to check crew roster for flight 1"                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE TOOL INVOCATION                             │
│                                                                              │
│  Tool: query_flight_crew_roster(flight_id="1")                              │
│  Defined in: src/database/tools.py                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      DYNAMODB CLIENT (Singleton)                             │
│                                                                              │
│  Method: db.query_crew_roster_by_flight("1")                                │
│  Defined in: src/database/dynamodb.py                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            BOTO3 SDK                                         │
│                                                                              │
│  crew_roster.query(                                                          │
│      IndexName='flight-position-index',                                      │
│      KeyConditionExpression='flight_id = :fid',                             │
│      ExpressionAttributeValues={':fid': '1'}                                │
│  )                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AWS DYNAMODB (us-east-1)                             │
│                                                                              │
│  Table: CrewRoster                                                           │
│  GSI: flight-position-index                                                  │
│  Query time: 20-50ms                                                         │
│                                                                              │
│  Returns:                                                                    │
│  [                                                                           │
│    {"crew_id": "5", "position_id": "1", "duty_start": "06:00", ...},       │
│    {"crew_id": "6", "position_id": "2", "duty_start": "06:00", ...}        │
│  ]                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA TRANSFORMATION                                  │
│                                                                              │
│  1. Convert Decimal to float (DynamoDB uses Decimal)                        │
│  2. Format as JSON string                                                   │
│  3. Return to agent                                                         │
│                                                                              │
│  Result:                                                                     │
│  {                                                                           │
│    "flight_id": "1",                                                        │
│    "crew_count": 2,                                                         │
│    "roster": [...]                                                          │
│  }                                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT CONTINUES REASONING                            │
│                                                                              │
│  Agent parses JSON result and continues analysis:                            │
│  "I found 2 crew members. Now I need to check their FTL limits..."         │
│                                                                              │
│  Next query: query_crew_member_details(crew_id="5")                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Timing Diagram

```
Time (seconds)
0s    ┌─────────────────────────────────────────────────────────────────┐
      │ Resource Loading                                                 │
      │ • Model initialization                                           │
      │ • MCP client setup                                               │
      │ • DynamoDB client (singleton)                                    │
5s    └─────────────────────────────────────────────────────────────────┘
      │
      ▼
      ┌─────────────────────────────────────────────────────────────────┐
      │ PHASE 1: Safety Agents (Parallel)                               │
      │                                                                  │
      │ ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
      │ │ Crew Compliance  │  │   Maintenance    │  │  Regulatory    │ │
      │ │                  │  │                  │  │                │ │
      │ │ 0-5s:  Load      │  │ 0-5s:  Load      │  │ 0-3s:  Load    │ │
      │ │ 5-10s: Query DB  │  │ 5-12s: Query DB  │  │ 3-6s:  Query DB│ │
      │ │ 10-25s: Analyze  │  │ 12-25s: Analyze  │  │ 6-20s: Analyze │ │
      │ └──────────────────┘  └──────────────────┘  └────────────────┘ │
      │                                                                  │
50s   └─────────────────────────────────────────────────────────────────┘
      │
      ▼
      ┌─────────────────────────────────────────────────────────────────┐
      │ Constraint Check (0.5s)                                          │
51s   └─────────────────────────────────────────────────────────────────┘
      │
      ▼
      ┌─────────────────────────────────────────────────────────────────┐
      │ PHASE 2: Business Agents (Parallel)                             │
      │                                                                  │
      │ ┌────────┐  ┌────────────┐  ┌──────────┐  ┌─────────────────┐ │
      │ │Network │  │Guest Exp   │  │  Cargo   │  │    Finance      │ │
      │ │        │  │            │  │          │  │                 │ │
      │ │0-5s:   │  │0-4s: Load  │  │0-3s: Load│  │0-2s: Load       │ │
      │ │Load    │  │4-10s: Query│  │3-7s: Qry │  │2-5s: Query      │ │
      │ │5-15s:  │  │10-25s: Anlz│  │7-20s:Anlz│  │5-15s: Analyze   │ │
      │ │Query   │  │            │  │          │  │                 │ │
      │ │15-30s: │  │            │  │          │  │                 │ │
      │ │Analyze │  │            │  │          │  │                 │ │
      │ └────────┘  └────────────┘  └──────────┘  └─────────────────┘ │
      │                                                                  │
90s   └─────────────────────────────────────────────────────────────────┘
      │
      ▼
      ┌─────────────────────────────────────────────────────────────────┐
      │ Result Aggregation (1s)                                          │
91s   └─────────────────────────────────────────────────────────────────┘
      │
      ▼
      ┌─────────────────────────────────────────────────────────────────┐
      │ Return Response                                                  │
      └─────────────────────────────────────────────────────────────────┘

Total: 60-90 seconds (typical: 75 seconds)
```

---

## Agent-Database Mapping

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CREW COMPLIANCE AGENT                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tools:                                                                       │
│  • query_flight_crew_roster(flight_id)                                      │
│  • query_crew_member_details(crew_id)                                       │
│                                                                              │
│ DynamoDB Tables:                                                             │
│  • CrewRoster (GSI: flight-position-index)                                  │
│  • CrewMembers (Direct key lookup)                                          │
│                                                                              │
│ Typical Queries: 2-3 per disruption                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          MAINTENANCE AGENT                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tools:                                                                       │
│  • check_aircraft_availability(aircraft_reg, valid_from)                    │
│  • query_maintenance_workorders(aircraft_reg)                               │
│  • query_maintenance_roster(workorder_id)                                   │
│                                                                              │
│ DynamoDB Tables:                                                             │
│  • AircraftAvailability (Composite key)                                     │
│  • MaintenanceWorkOrders (Scan with filter)                                 │
│  • MaintenanceRoster (GSI: workorder-shift-index)                           │
│                                                                              │
│ Typical Queries: 3-4 per disruption                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                          REGULATORY AGENT                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tools:                                                                       │
│  • query_weather_forecast(airport_code, forecast_time)                      │
│  • query_flight_details(flight_id)                                          │
│                                                                              │
│ DynamoDB Tables:                                                             │
│  • Weather (Composite key)                                                  │
│  • Flights (Direct key lookup)                                              │
│                                                                              │
│ Typical Queries: 2-3 per disruption                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           NETWORK AGENT                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tools:                                                                       │
│  • query_inbound_flight_impact(scenario)                                    │
│  • query_flight_network(flight_id)                                          │
│                                                                              │
│ DynamoDB Tables:                                                             │
│  • InboundFlightImpact (Direct key lookup)                                  │
│  • Flights (Direct key lookup)                                              │
│                                                                              │
│ Typical Queries: 2-3 per disruption                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                      GUEST EXPERIENCE AGENT                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tools:                                                                       │
│  • query_passenger_bookings(passenger_id)                                   │
│  • query_flight_bookings(flight_id, status)                                 │
│  • query_passenger_baggage(booking_id)                                      │
│  • get_passenger_details(passenger_id)                                      │
│                                                                              │
│ DynamoDB Tables:                                                             │
│  • Bookings (GSI: passenger-flight-index, flight-status-index)              │
│  • Passengers (Direct key lookup)                                           │
│  • Baggage (GSI: booking-index)                                             │
│                                                                              │
│ Typical Queries: 3-5 per disruption                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            CARGO AGENT                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tools:                                                                       │
│  • track_cargo_shipment(shipment_id)                                        │
│  • query_flight_cargo_manifest(flight_id, loading_status)                   │
│                                                                              │
│ DynamoDB Tables:                                                             │
│  • CargoShipments (Direct key lookup)                                       │
│  • CargoFlightAssignments (GSI: shipment-index, flight-loading-index)       │
│                                                                              │
│ Typical Queries: 2-3 per disruption                                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           FINANCE AGENT                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tools:                                                                       │
│  • query_flight_for_cost_analysis(flight_id)                                │
│                                                                              │
│ DynamoDB Tables:                                                             │
│  • Flights (Direct key lookup)                                              │
│                                                                              │
│ Typical Queries: 1-2 per disruption                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Decision Flow

```
                    ┌─────────────────────┐
                    │  Disruption Arrives │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Run Safety Agents  │
                    └──────────┬──────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
    ┌───────────────────────┐    ┌───────────────────────┐
    │  Blocking Violation?  │    │  All Agents Success?  │
    └───────────┬───────────┘    └───────────┬───────────┘
                │                             │
        ┌───────┴───────┐             ┌───────┴───────┐
        │               │             │               │
        ▼               ▼             ▼               ▼
    ┌─────┐         ┌─────┐      ┌─────┐         ┌─────┐
    │ YES │         │ NO  │      │ YES │         │ NO  │
    └──┬──┘         └──┬──┘      └──┬──┘         └──┬──┘
       │               │             │               │
       ▼               │             │               ▼
┌─────────────┐        │             │        ┌─────────────┐
│   BLOCKED   │        │             │        │   ERROR     │
│             │        │             │        │             │
│ Return:     │        │             │        │ Return:     │
│ CANNOT_     │        │             │        │ Partial     │
│ PROCEED     │        │             │        │ Results     │
└─────────────┘        │             │        └─────────────┘
                       │             │
                       └──────┬──────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ Run Business Agents │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ Aggregate Results   │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ Generate            │
                   │ Recommendations     │
                   └──────────┬──────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │ Return Complete     │
                   │ Assessment          │
                   └─────────────────────┘
```

---

This visual guide helps understand the complete flow of the SkyMarshal orchestrator system!
