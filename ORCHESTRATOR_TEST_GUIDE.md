# SkyMarshal Orchestrator Testing Guide

## Overview

The SkyMarshal orchestrator is a multi-agent system that analyzes flight disruptions by coordinating 7 specialized agents:

**Safety Agents (Phase 1 - Parallel):**

1. **Crew Compliance** - FTL limits, rest requirements, qualifications
2. **Maintenance** - Aircraft airworthiness, MEL items, AOG status
3. **Regulatory** - Weather, NOTAMs, curfews, slots

**Business Agents (Phase 2 - Parallel):** 4. **Network** - Aircraft rotations, connections, propagation impact 5. **Guest Experience** - Passenger rebooking, VIP handling, baggage 6. **Cargo** - Shipment tracking, time-sensitive cargo, capacity 7. **Finance** - Cost analysis, revenue impact, compensation

All agents query **DynamoDB** for real-time operational data.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator (main.py)                    │
│  - Routes requests to agents                                 │
│  - Runs safety agents first (parallel)                       │
│  - Checks for blocking constraints                           │
│  - Runs business agents (parallel)                           │
│  - Aggregates results                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │         DynamoDB (16 Tables)            │
        │  - Flights, Crew, Aircraft, Passengers  │
        │  - Bookings, Cargo, Weather, etc.       │
        └─────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────┐
        │      Agent Database Tools (tools.py)     │
        │  - Crew tools (roster, qualifications)   │
        │  - Maintenance tools (MEL, workorders)   │
        │  - Network tools (rotations, impact)     │
        │  - Guest tools (bookings, baggage)       │
        │  - Cargo tools (shipments, manifest)     │
        └─────────────────────────────────────────┘
```

---

## Prerequisites

### 1. AWS Setup

```bash
# Configure AWS credentials
aws configure
# Region: us-east-1
# Access Key: Your AWS access key
# Secret Key: Your AWS secret key

# Verify credentials
aws sts get-caller-identity
```

### 2. DynamoDB Tables

Ensure these tables exist and are populated:

- Flights
- CrewMembers
- CrewRoster
- AircraftAvailability
- MaintenanceWorkOrders
- MaintenanceRoster
- Weather
- Bookings
- Baggage
- Passengers
- CargoShipments
- CargoFlightAssignments
- InboundFlightImpact

### 3. Python Environment

```bash
cd skymarshal_agents
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r ../requirements.txt
```

---

## Testing Methods

### Method 1: Local Testing (Recommended First)

Test database connectivity and orchestrator logic without deploying:

```bash
# Run local test suite
python test_local_orchestrator.py
```

This will:

1. ✅ Test DynamoDB connection
2. ✅ Test agent database tools
3. ✅ Test orchestrator aggregation logic
4. ℹ️ Provide deployment instructions

**Expected Output:**

```
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀
SKYMARSHAL LOCAL ORCHESTRATOR TEST
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀

STEP 1: Testing DynamoDB Connection
================================================================================
✅ DynamoDB client initialized
   Region: us-east-1

Testing basic queries:
1. Query Flight (ID=1):
   ✅ Found flight: EY123
      Route: AUH → LHR
...
```

---

### Method 2: AgentCore Local Development

Run the orchestrator locally with AgentCore dev server:

```bash
# Terminal 1: Start dev server
cd skymarshal_agents
agentcore dev
# Server starts on http://0.0.0.0:8080

# Terminal 2: Test with sample disruption
agentcore invoke --dev "Analyze this flight disruption: EY123 from AUH to LHR has a 3-hour delay due to hydraulic system fault"

# Or test specific agent
agentcore invoke --dev --payload '{"agent": "crew_compliance", "prompt": "Check crew FTL for flight 1"}'
```

**Expected Output:**

```
Invoking agent with payload...
Response:
{
  "timestamp": "2026-01-30T14:23:45Z",
  "workflow_status": "CAN_PROCEED_WITH_CONSTRAINTS",
  "safety_assessment": {
    "crew_compliance": {...},
    "maintenance": {...},
    "regulatory": {...}
  },
  "business_assessment": {
    "network": {...},
    "guest_experience": {...},
    "cargo": {...},
    "finance": {...}
  },
  "recommendations": [...]
}
```

---

### Method 3: Full Orchestrator Test (After Deployment)

Test the complete flow with the provided test script:

```bash
# Run comprehensive test
python test_orchestrator_flow.py --mode orchestrator

# Test individual agents
python test_orchestrator_flow.py --mode individual

# Test specific agent
python test_orchestrator_flow.py --agent crew_compliance

# Test both modes
python test_orchestrator_flow.py --mode both
```

---

### Method 4: AgentCore Cloud Deployment

Deploy to AWS and test in production:

```bash
# Deploy to AgentCore
cd skymarshal_agents
agentcore deploy

# Test deployed agent
agentcore invoke "Analyze flight disruption for EY123"

# Check agent status
agentcore status

# View logs
agentcore logs
```

---

## Sample Test Scenarios

### Scenario 1: Basic Disruption (sample_disruption.json)

```json
{
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
```

**Expected Agent Responses:**

- **Crew Compliance**: Check FTL limits, verify 8.5h remaining is sufficient
- **Maintenance**: Assess hydraulic system, check MEL Category B deferral
- **Regulatory**: Verify LHR curfew compliance (23:00 UTC)
- **Network**: Calculate propagation to 2 downstream flights
- **Guest Experience**: Identify 87 at-risk connections, 12 VIP passengers
- **Cargo**: Track 15 shipments, prioritize 2 time-sensitive
- **Finance**: Estimate $850K revenue risk, $125K compensation

---

### Scenario 2: Test Specific Agent

```bash
# Test crew compliance agent
python test_orchestrator_flow.py --agent crew_compliance
```

**Payload:**

```json
{
  "agent": "crew_compliance",
  "prompt": "Analyze crew FTL for flight 1 with 3-hour delay",
  "disruption": {
    "flight_id": "1",
    "delay_hours": 3
  }
}
```

**Expected Queries:**

1. `query_flight_crew_roster(flight_id="1")` → Get crew roster
2. `query_crew_member_details(crew_id="5")` → Get captain details
3. `query_crew_member_details(crew_id="6")` → Get first officer details

**Expected Output:**

```json
{
  "agent": "crew_compliance",
  "assessment": "APPROVED",
  "crew_roster": {
    "captain": {
      "crew_id": "5",
      "fdp_remaining": 3.5,
      "qualifications_valid": true
    }
  },
  "violations": [],
  "recommendations": ["Crew can operate with 3-hour delay"]
}
```

---

### Scenario 3: Test Network Agent

```bash
python test_orchestrator_flow.py --agent network
```

**Expected Queries:**

1. `query_flight_network(flight_id="1")` → Get flight details
2. `query_inbound_flight_impact(scenario="DISR-001")` → Get impact analysis

**Expected Output:**

```json
{
  "agent": "network",
  "propagation_impact": {
    "flights_affected": 2,
    "total_delay_minutes": 270,
    "connections_at_risk": 87
  },
  "recovery_options": [
    {
      "option": "tail_swap",
      "cost_reduction": 89,
      "feasibility": 92
    }
  ]
}
```

---

## Troubleshooting

### Issue: Database Connection Failed

**Symptoms:**

```
❌ Database connectivity test FAILED: Unable to locate credentials
```

**Solution:**

```bash
# Configure AWS credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

---

### Issue: No Data Found in DynamoDB

**Symptoms:**

```
⚠️  No flight data found
⚠️  No crew roster found
```

**Solution:**

```bash
# Check if tables are populated
cd database
python show_disruption_scenario_v2.py

# If empty, generate data
python generators/create_disruption_scenario_v2.py

# Import to DynamoDB
python import_csv_to_dynamodb.py
```

---

### Issue: Agent Timeout

**Symptoms:**

```
⏱ crew_compliance timeout after 60s
```

**Solution:**

1. Increase timeout in `main.py`:

```python
result = await asyncio.wait_for(
    agent_fn(payload, llm, mcp_tools),
    timeout=120  # Increase from 60 to 120
)
```

2. Check DynamoDB query performance
3. Verify network connectivity to AWS

---

### Issue: Model Not Available

**Symptoms:**

```
Error: Model 'anthropic.claude-sonnet-4-20250514' not available
```

**Solution:**

1. Check model availability in your AWS region
2. Update `src/model/load.py` to use available model:

```python
model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"
```

---

## Monitoring and Debugging

### View Agent Logs

```bash
# Local dev server logs
cd skymarshal_agents
agentcore dev --verbose

# Deployed agent logs
agentcore logs --tail 100
```

### Check DynamoDB Queries

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run test
python test_local_orchestrator.py
```

### Measure Performance

```bash
# Time orchestrator execution
time python test_orchestrator_flow.py --mode orchestrator

# Check individual agent duration
python test_orchestrator_flow.py --mode individual
```

---

## Expected Performance

| Metric             | Target | Typical |
| ------------------ | ------ | ------- |
| Database query     | <50ms  | 20-30ms |
| Agent execution    | <60s   | 15-45s  |
| Orchestrator total | <120s  | 60-90s  |
| Safety phase       | <60s   | 30-45s  |
| Business phase     | <60s   | 30-45s  |

---

## Next Steps

1. ✅ Run `python test_local_orchestrator.py` to verify setup
2. ✅ Test individual agents with `test_orchestrator_flow.py --agent <name>`
3. ✅ Deploy with `agentcore deploy`
4. ✅ Test full orchestrator flow
5. ✅ Monitor performance and optimize queries
6. ✅ Add custom disruption scenarios
7. ✅ Integrate with frontend (if available)

---

## Quick Reference Commands

```bash
# Local testing
python test_local_orchestrator.py

# Test specific agent
python test_orchestrator_flow.py --agent crew_compliance

# Test all agents individually
python test_orchestrator_flow.py --mode individual

# Test orchestrator flow
python test_orchestrator_flow.py --mode orchestrator

# Deploy to AgentCore
cd skymarshal_agents && agentcore deploy

# Invoke deployed agent
agentcore invoke "Analyze disruption"

# Check status
agentcore status

# View logs
agentcore logs --tail 50
```

---

## Support

For issues or questions:

1. Check logs: `agentcore logs`
2. Verify DynamoDB data: `python database/show_disruption_scenario_v2.py`
3. Test database tools: `python test_local_orchestrator.py`
4. Review agent prompts in `src/agents/*.py`
5. Check AWS credentials: `aws sts get-caller-identity`
