# SkyMarshal Orchestrator - Complete Guide

## 🎯 What Is This?

The **SkyMarshal Orchestrator** is a multi-agent AI system that analyzes airline flight disruptions by coordinating **7 specialized agents** that query **AWS DynamoDB** for real-time operational data. All agents run in a **single AWS Bedrock AgentCore instance** for efficiency.

### Key Features

- ✅ **7 Specialized Agents**: Crew, Maintenance, Regulatory, Network, Guest Experience, Cargo, Finance
- ✅ **Two-Phase Execution**: Safety agents first (blocking), then business agents
- ✅ **Real-Time Data**: Queries 16 DynamoDB tables for live operational data
- ✅ **Parallel Processing**: Agents run concurrently for speed (60-90s total)
- ✅ **Comprehensive Analysis**: Safety constraints + business trade-offs + recommendations

---

## 📁 Project Structure

```
skymarshal_agents/                    # Main AgentCore project
├── src/
│   ├── main.py                       # Orchestrator entry point
│   ├── agents/                       # 7 agent implementations
│   │   ├── crew_compliance.py        # FTL limits, rest, qualifications
│   │   ├── maintenance.py            # Airworthiness, MEL, AOG
│   │   ├── regulatory.py             # Weather, NOTAMs, curfews
│   │   ├── network.py                # Rotations, connections, propagation
│   │   ├── guest_experience.py       # Passengers, rebooking, VIP
│   │   ├── cargo.py                  # Shipments, capacity, time-sensitive
│   │   └── finance.py                # Costs, revenue, compensation
│   ├── database/
│   │   ├── dynamodb.py               # DynamoDB client (singleton)
│   │   └── tools.py                  # Database tools for agents
│   ├── utils/
│   │   └── response.py               # Response aggregation
│   └── model/
│       └── load.py                   # Bedrock model loader
├── .bedrock_agentcore.yaml           # AgentCore configuration
└── pyproject.toml                    # Python dependencies

# Test Scripts (root directory)
├── test_local_orchestrator.py        # Local testing (no deployment)
├── test_orchestrator_flow.py         # Full orchestrator test
├── check_dynamodb_data.py            # DynamoDB data checker
├── run_orchestrator_test.sh          # Automated test suite
└── sample_disruption.json            # Test disruption scenario

# Documentation
├── ORCHESTRATOR_SUMMARY.md           # Quick summary (this file)
├── ORCHESTRATOR_ARCHITECTURE.md      # Detailed architecture
└── ORCHESTRATOR_TEST_GUIDE.md        # Testing guide
```

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites

```bash
# 1. AWS credentials configured
aws configure
# Region: us-east-1

# 2. Python 3.10+ installed
python3 --version

# 3. DynamoDB tables populated (see below)
```

### Run Tests

```bash
# Option 1: Automated test suite (recommended)
./run_orchestrator_test.sh

# Option 2: Manual testing
python3 check_dynamodb_data.py          # Check DynamoDB
python3 test_local_orchestrator.py      # Test locally
```

### Deploy and Test

```bash
# Deploy to AgentCore
cd skymarshal_agents
agentcore deploy

# Test deployed orchestrator
agentcore invoke "Analyze flight disruption: EY123 from AUH to LHR has 3-hour delay"
```

---

## 🗄️ DynamoDB Setup

### Required Tables (16 total)

The orchestrator queries these DynamoDB tables in `us-east-1`:

| Table                  | Used By          | Purpose                           |
| ---------------------- | ---------------- | --------------------------------- |
| Flights                | All agents       | Flight schedule, route, aircraft  |
| CrewMembers            | Crew Compliance  | Crew qualifications, type ratings |
| CrewRoster             | Crew Compliance  | Flight crew assignments           |
| AircraftAvailability   | Maintenance      | MEL items, airworthiness          |
| MaintenanceWorkOrders  | Maintenance      | Work orders, technicians          |
| MaintenanceRoster      | Maintenance      | Staff assignments                 |
| Weather                | Regulatory       | Weather forecasts                 |
| Bookings               | Guest Experience | Passenger bookings                |
| Passengers             | Guest Experience | Passenger profiles, loyalty       |
| Baggage                | Guest Experience | Baggage tracking                  |
| CargoShipments         | Cargo            | Shipment details                  |
| CargoFlightAssignments | Cargo            | Cargo-flight assignments          |
| InboundFlightImpact    | Network          | Impact analysis                   |

### Populate DynamoDB

```bash
cd database

# Generate disruption scenario data
python generators/create_disruption_scenario_v2.py

# Import to DynamoDB
python import_csv_to_dynamodb.py

# Verify data
cd ..
python check_dynamodb_data.py
```

---

## 🧪 Testing

### 1. Check DynamoDB Data

```bash
python check_dynamodb_data.py
```

**Output:**

```
✅ SUCCESS: Flights
✅ SUCCESS: Crew Members
✅ SUCCESS: Aircraft Availability
...
Tables with data: 14/14
✅ All tables have data! Ready for orchestrator testing.
```

### 2. Test Locally (No Deployment)

```bash
python test_local_orchestrator.py
```

**Tests:**

- ✅ DynamoDB connection
- ✅ Agent database tools
- ✅ Orchestrator logic
- ℹ️ Deployment instructions

### 3. Test Individual Agents

```bash
# Test specific agent
python test_orchestrator_flow.py --agent crew_compliance

# Test all agents individually
python test_orchestrator_flow.py --mode individual
```

### 4. Test Full Orchestrator

```bash
# Test complete orchestrator flow
python test_orchestrator_flow.py --mode orchestrator
```

### 5. Test Deployed Orchestrator

```bash
cd skymarshal_agents

# Start local dev server
agentcore dev  # Terminal 1

# Test in another terminal
agentcore invoke --dev "Analyze disruption"  # Terminal 2

# Or test deployed version
agentcore deploy
agentcore invoke "Analyze disruption"
```

---

## 📊 How It Works

### Execution Flow

```
1. Disruption Payload Received
   ↓
2. Load Shared Resources (Model, MCP, DynamoDB)
   ↓
3. Phase 1: Safety Agents (Parallel)
   ├── Crew Compliance → Query CrewRoster, CrewMembers
   ├── Maintenance → Query AircraftAvailability, MaintenanceWorkOrders
   └── Regulatory → Query Weather, Flights
   ↓
4. Check for Blocking Constraints
   ├── If BLOCKED → Return CANNOT_PROCEED
   └── If OK → Continue
   ↓
5. Phase 2: Business Agents (Parallel)
   ├── Network → Query Flights, InboundFlightImpact
   ├── Guest Experience → Query Bookings, Passengers, Baggage
   ├── Cargo → Query CargoShipments, CargoFlightAssignments
   └── Finance → Query Flights
   ↓
6. Aggregate Results
   ↓
7. Return Recommendations
```

### Sample Input

```json
{
  "agent": "orchestrator",
  "prompt": "Analyze this flight disruption",
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

### Sample Output

```json
{
  "timestamp": "2026-01-30T14:23:45Z",
  "workflow_status": "CAN_PROCEED_WITH_CONSTRAINTS",
  "safety_assessment": {
    "crew_compliance": {
      "assessment": "APPROVED",
      "fdp_remaining": "3.5 hours"
    },
    "maintenance": {
      "assessment": "AIRWORTHY_WITH_MEL",
      "mel_items": [{ "category": "B", "system": "Hydraulic" }]
    },
    "regulatory": {
      "assessment": "COMPLIANT",
      "curfew_status": "Within limits"
    },
    "blocking_constraints": []
  },
  "business_assessment": {
    "network": {
      "flights_affected": 2,
      "connections_at_risk": 87
    },
    "guest_experience": {
      "passengers_affected": 615,
      "vip_count": 12
    },
    "cargo": {
      "shipments_affected": 15,
      "time_sensitive": 2
    },
    "finance": {
      "revenue_at_risk": 850000,
      "compensation_liability": 125000
    }
  },
  "recommendations": [
    "Operation can proceed with constraints",
    "Consider passenger rebooking for 87 at-risk connections",
    "Monitor network propagation to 2 downstream flights"
  ]
}
```

---

## 🔧 Configuration

### AgentCore Configuration

File: `skymarshal_agents/.bedrock_agentcore.yaml`

```yaml
default_agent: Skymarshal_Agent
agents:
  Skymarshal_Agent:
    name: Skymarshal_Agent
    language: python
    runtime_type: PYTHON_3_13
    entrypoint: ./main.py
    source_path: ./src
    aws:
      execution_role_auto_create: true
      region: us-east-1
      network_configuration:
        network_mode: PUBLIC
      observability:
        enabled: true
```

### Model Configuration

File: `skymarshal_agents/src/model/load.py`

```python
def load_model():
    """Load Bedrock model"""
    return ChatBedrock(
        model_id="anthropic.claude-sonnet-4-20250514",
        region_name="us-east-1",
        temperature=0.3
    )
```

### DynamoDB Configuration

File: `skymarshal_agents/src/database/dynamodb.py`

```python
AWS_REGION = "us-east-1"

class DynamoDBClient:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        # Initialize 16 table references
        self.flights = self.dynamodb.Table('Flights')
        self.crew_members = self.dynamodb.Table('CrewMembers')
        # ... etc
```

---

## 📈 Performance

### Timing Breakdown

```
Total: 60-90 seconds
├── Resource Loading: 2-5s
├── Phase 1 (Safety): 30-45s (parallel)
│   ├── Crew Compliance: 15-25s
│   ├── Maintenance: 15-25s
│   └── Regulatory: 10-20s
├── Constraint Check: 0.1-0.5s
└── Phase 2 (Business): 30-45s (parallel)
    ├── Network: 20-30s
    ├── Guest Experience: 15-25s
    ├── Cargo: 10-20s
    └── Finance: 10-15s
```

### DynamoDB Query Performance

- **Direct key lookup**: 10-20ms
- **GSI query**: 20-50ms
- **Scan with filter**: 50-200ms

### Optimization Tips

1. Use GSI queries instead of scans
2. Increase agent timeout if needed (default: 60s)
3. Enable DynamoDB caching for frequent queries
4. Use parallel execution (already implemented)

---

## 🐛 Troubleshooting

### Issue: AWS Credentials Not Found

```bash
# Configure credentials
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### Issue: DynamoDB Tables Empty

```bash
cd database
python generators/create_disruption_scenario_v2.py
python import_csv_to_dynamodb.py
```

### Issue: Agent Timeout

Edit `skymarshal_agents/src/main.py`:

```python
result = await asyncio.wait_for(
    agent_fn(payload, llm, mcp_tools),
    timeout=120  # Increase from 60
)
```

### Issue: Model Not Available

Edit `skymarshal_agents/src/model/load.py`:

```python
model_id = "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Use available model
```

### Issue: Import Errors

```bash
cd skymarshal_agents
pip install -r ../requirements.txt
```

---

## 📚 Documentation

| Document                       | Description                      |
| ------------------------------ | -------------------------------- |
| `README_ORCHESTRATOR.md`       | This file - complete guide       |
| `ORCHESTRATOR_SUMMARY.md`      | Quick summary and commands       |
| `ORCHESTRATOR_ARCHITECTURE.md` | Detailed architecture and design |
| `ORCHESTRATOR_TEST_GUIDE.md`   | Comprehensive testing guide      |

---

## 🎯 Use Cases

### 1. Flight Delay Analysis

```bash
agentcore invoke "Analyze 3-hour delay for EY123 due to hydraulic fault"
```

**Agents analyze:**

- Crew FTL limits
- Aircraft MEL status
- Weather conditions
- Network propagation
- Passenger connections
- Cargo impact
- Financial cost

### 2. Crew Compliance Check

```bash
python test_orchestrator_flow.py --agent crew_compliance
```

**Agent queries:**

- Flight crew roster
- Crew member qualifications
- FTL calculations
- Rest requirements

### 3. Network Impact Assessment

```bash
python test_orchestrator_flow.py --agent network
```

**Agent analyzes:**

- Aircraft rotation
- Downstream flights
- Connection risks
- Propagation chains

### 4. Complete Disruption Analysis

```bash
python test_orchestrator_flow.py --mode orchestrator
```

**All agents run:**

- Safety assessment (Phase 1)
- Business assessment (Phase 2)
- Aggregated recommendations

---

## 🚀 Deployment

### Local Development

```bash
cd skymarshal_agents
agentcore dev  # Starts on http://0.0.0.0:8080
```

### Deploy to AWS

```bash
cd skymarshal_agents
agentcore deploy
```

### Invoke Deployed Agent

```bash
# Simple invocation
agentcore invoke "Analyze disruption"

# With payload
agentcore invoke --payload '{"agent": "orchestrator", "prompt": "Analyze EY123 delay"}'
```

### Monitor

```bash
# View logs
agentcore logs --tail 50

# Check status
agentcore status

# View metrics (in AWS Console)
# CloudWatch → Metrics → AgentCore
```

---

## 🔄 Workflow

### Development Workflow

1. Make changes to agent code
2. Test locally: `python test_local_orchestrator.py`
3. Test with dev server: `agentcore dev`
4. Deploy: `agentcore deploy`
5. Test deployed: `agentcore invoke`

### Testing Workflow

1. Check data: `python check_dynamodb_data.py`
2. Test agents: `python test_orchestrator_flow.py --mode individual`
3. Test orchestrator: `python test_orchestrator_flow.py --mode orchestrator`
4. Deploy and test: `agentcore deploy && agentcore invoke`

---

## 📞 Support

### Common Commands

```bash
# Check DynamoDB data
python check_dynamodb_data.py

# Test locally
python test_local_orchestrator.py

# Test specific agent
python test_orchestrator_flow.py --agent crew_compliance

# Test orchestrator
python test_orchestrator_flow.py --mode orchestrator

# Deploy
cd skymarshal_agents && agentcore deploy

# Invoke
agentcore invoke "Analyze disruption"

# Logs
agentcore logs --tail 50

# Status
agentcore status
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run tests
python test_local_orchestrator.py
```

---

## ✅ Next Steps

1. ✅ **Verify setup**: `./run_orchestrator_test.sh`
2. ✅ **Test locally**: `python test_local_orchestrator.py`
3. ✅ **Test agents**: `python test_orchestrator_flow.py --mode individual`
4. ✅ **Deploy**: `cd skymarshal_agents && agentcore deploy`
5. ✅ **Test deployed**: `agentcore invoke "Analyze disruption"`
6. ✅ **Monitor**: `agentcore logs --tail 50`
7. ✅ **Customize**: Edit `sample_disruption.json` and test

---

## 🎉 Success Criteria

You'll know the orchestrator is working when:

- ✅ `check_dynamodb_data.py` shows all tables have data
- ✅ `test_local_orchestrator.py` passes all tests
- ✅ `agentcore dev` starts without errors
- ✅ `agentcore invoke` returns comprehensive analysis
- ✅ All 7 agents execute successfully
- ✅ Response includes safety + business assessments
- ✅ Execution completes in 60-90 seconds

---

**Ready to test!** Start with `./run_orchestrator_test.sh` 🚀
