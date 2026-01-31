# SkyMarshal Orchestrator - Quick Summary

## What You Have

A **multi-agent orchestrator** running in a **single AgentCore instance** that analyzes flight disruptions by coordinating **7 specialized agents**, all querying **DynamoDB** for real-time data.

## Architecture

```
Single AgentCore Instance (skymarshal_agents/)
│
├── Orchestrator (main.py)
│   ├── Phase 1: Safety Agents (Parallel)
│   │   ├── Crew Compliance → Queries CrewRoster, CrewMembers
│   │   ├── Maintenance → Queries AircraftAvailability, MaintenanceWorkOrders
│   │   └── Regulatory → Queries Weather, Flights
│   │
│   └── Phase 2: Business Agents (Parallel)
│       ├── Network → Queries Flights, InboundFlightImpact
│       ├── Guest Experience → Queries Bookings, Passengers, Baggage
│       ├── Cargo → Queries CargoShipments, CargoFlightAssignments
│       └── Finance → Queries Flights (for cost analysis)
│
└── DynamoDB (16 tables in us-east-1)
```

## How It Works

1. **Disruption arrives** → Orchestrator receives payload
2. **Phase 1 (Safety)** → 3 agents run in parallel, query DynamoDB
3. **Constraint check** → If blocking violation → STOP
4. **Phase 2 (Business)** → 4 agents run in parallel, query DynamoDB
5. **Aggregation** → Combine all results → Return recommendations

## Testing the Orchestrator

### Quick Test (5 minutes)

```bash
# 1. Check DynamoDB data
python check_dynamodb_data.py

# 2. Test locally
python test_local_orchestrator.py

# 3. Deploy and test
cd skymarshal_agents
agentcore dev  # Terminal 1
agentcore invoke --dev "Analyze disruption"  # Terminal 2
```

### Full Test (15 minutes)

```bash
# Test complete orchestrator flow
python test_orchestrator_flow.py --mode orchestrator

# Test individual agents
python test_orchestrator_flow.py --mode individual

# Test specific agent
python test_orchestrator_flow.py --agent crew_compliance
```

## Key Files

| File                                         | Purpose                     |
| -------------------------------------------- | --------------------------- |
| `skymarshal_agents/src/main.py`              | Orchestrator entry point    |
| `skymarshal_agents/src/agents/*.py`          | 7 agent implementations     |
| `skymarshal_agents/src/database/dynamodb.py` | DynamoDB client (singleton) |
| `skymarshal_agents/src/database/tools.py`    | Database tools for agents   |
| `skymarshal_agents/src/utils/response.py`    | Response aggregation        |
| `sample_disruption.json`                     | Test disruption scenario    |
| `test_local_orchestrator.py`                 | Local testing script        |
| `test_orchestrator_flow.py`                  | Full orchestrator test      |
| `check_dynamodb_data.py`                     | DynamoDB data checker       |

## Sample Disruption Test

**Input:**

```json
{
  "agent": "orchestrator",
  "disruption": {
    "flight": {
      "flight_number": "EY123",
      "origin": "AUH",
      "destination": "LHR"
    },
    "issue_details": {
      "description": "Hydraulic fault",
      "estimated_delay_minutes": 180
    },
    "impact": { "passengers_affected": 615, "connecting_passengers": 87 }
  }
}
```

**Expected Output:**

```json
{
  "workflow_status": "CAN_PROCEED_WITH_CONSTRAINTS",
  "safety_assessment": {
    "crew_compliance": "8.5h FDP remaining, within limits",
    "maintenance": "MEL Category B deferral available",
    "regulatory": "Within LHR curfew (23:00 UTC)"
  },
  "business_assessment": {
    "network": "2 downstream flights affected, 87 connections at risk",
    "guest_experience": "615 passengers, 12 VIP require handling",
    "cargo": "15 shipments, 2 time-sensitive",
    "finance": "$850K revenue risk, $125K compensation"
  },
  "recommendations": [...]
}
```

## Performance

- **Total time**: 60-90 seconds
- **Phase 1 (Safety)**: 30-45 seconds (parallel)
- **Phase 2 (Business)**: 30-45 seconds (parallel)
- **DynamoDB queries**: 20-50ms each
- **Agent timeout**: 60 seconds max

## DynamoDB Tables Used

| Agent            | Tables Queried                                                 |
| ---------------- | -------------------------------------------------------------- |
| Crew Compliance  | CrewRoster, CrewMembers                                        |
| Maintenance      | AircraftAvailability, MaintenanceWorkOrders, MaintenanceRoster |
| Regulatory       | Weather, Flights                                               |
| Network          | Flights, InboundFlightImpact                                   |
| Guest Experience | Bookings, Passengers, Baggage                                  |
| Cargo            | CargoShipments, CargoFlightAssignments                         |
| Finance          | Flights                                                        |

## Next Steps

1. ✅ **Verify setup**: `python check_dynamodb_data.py`
2. ✅ **Test locally**: `python test_local_orchestrator.py`
3. ✅ **Deploy**: `cd skymarshal_agents && agentcore deploy`
4. ✅ **Test deployed**: `agentcore invoke "Analyze disruption"`
5. ✅ **Monitor**: `agentcore logs --tail 50`

## Common Issues

### No DynamoDB Data

```bash
cd database
python generators/create_disruption_scenario_v2.py
python import_csv_to_dynamodb.py
```

### AWS Credentials

```bash
aws configure
# Region: us-east-1
```

### Agent Timeout

Increase timeout in `main.py`:

```python
timeout=120  # Increase from 60
```

## Documentation

- **Full Architecture**: `ORCHESTRATOR_ARCHITECTURE.md`
- **Testing Guide**: `ORCHESTRATOR_TEST_GUIDE.md`
- **This Summary**: `ORCHESTRATOR_SUMMARY.md`

## Quick Commands

```bash
# Check data
python check_dynamodb_data.py

# Test locally
python test_local_orchestrator.py

# Test orchestrator
python test_orchestrator_flow.py --mode orchestrator

# Test specific agent
python test_orchestrator_flow.py --agent crew_compliance

# Deploy
cd skymarshal_agents && agentcore deploy

# Invoke
agentcore invoke "Analyze disruption"

# Logs
agentcore logs --tail 50
```

---

**Ready to test!** Start with `python check_dynamodb_data.py` to verify your setup.
