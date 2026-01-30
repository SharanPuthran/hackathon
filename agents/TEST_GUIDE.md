# SkyMarshal Agents - Testing Guide

**Purpose**: Test all 10 agents with relevant disruption scenarios
**Status**: Ready for testing

---

## 🚀 Quick Start

### Option 1: Automated Test Suite (Recommended)

Run the automated test script that tests all agents sequentially:

```bash
cd /Users/sharanputhran/Learning/Hackathon/agents
./test_all_agents.sh
```

This will:
1. Test each agent with a relevant scenario
2. Start/stop servers automatically
3. Display results for each agent
4. Generate a summary report

### Option 2: Manual Testing (Individual Agents)

Test agents one at a time for detailed inspection.

---

## 📋 Test Scenarios by Agent

### 1. Orchestrator Agent

**Start server**:
```bash
cd orchestrator
agentcore dev
```

**Test query** (in another terminal):
```bash
agentcore invoke --dev "Analyze disruption: Flight EY123 from AUH to LHR has a hydraulic system fault causing a 3-hour delay. 615 passengers onboard, 87 at risk of missing connections."
```

**Expected behavior**: Should coordinate workflow, identify phases, and route to appropriate agents.

---

### 2. Crew Compliance Agent (Safety)

**Start server**:
```bash
cd crew_compliance
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Check FTL compliance: Flight EY123 delayed 3 hours. Current crew duty time: 9.5 hours. Original flight duty period: 11 hours. Proposed new FDP: 14 hours. Captain has 850 flight hours this year."
```

**Expected output**:
- Assessment: REQUIRES_CREW_CHANGE (14hr exceeds 13hr FDP limit)
- Constraints: duty_limit violation
- Regulation: EASA FTL CAT.OP.MPA.210
- Recommendation: Replace crew or reduce delay

---

### 3. Maintenance Agent (Safety)

**Start server**:
```bash
cd maintenance
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Assess airworthiness: Flight EY123 has Hydraulic System 2 fault. System 1 and backup operational. 3-hour repair time estimated. Aircraft: Boeing 787-9. MEL item 29-51-01."
```

**Expected output**:
- Assessment: AIRWORTHY_WITH_MEL
- MEL category: B (rectify within 3 days)
- Deferrable: Yes
- Restrictions: No Cat II/III approaches
- Recommendation: Defer per MEL or repair now

---

### 4. Regulatory Agent (Safety)

**Start server**:
```bash
cd regulatory
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Check regulatory compliance: Flight EY123 to London Heathrow (LHR). Original arrival: 22:30 local time. With 3-hour delay, new arrival: 01:30 local time. Check curfew restrictions and slot availability."
```

**Expected output**:
- Assessment: CURFEW_RISK (01:30 violates LHR 23:00-06:00 curfew)
- Latest departure: 20:00 local to arrive by 23:00
- Severity: BLOCKING
- Recommendation: Cannot depart with 3hr delay, must cancel or reduce delay

---

### 5. Network Agent (Business)

**Start server**:
```bash
cd network
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Analyze network impact: Flight EY123 delayed 3 hours. 87 passengers connecting to 12 downstream flights at LHR hub. Key connections: EY12 to JFK (35 PAX), EY456 to SYD (22 PAX). Revenue at risk: estimated \$450,000."
```

**Expected output**:
- Connections at risk: 87
- Downstream flights affected: 12
- Revenue at risk: $450,000
- Priority: HIGH
- Recommendations: Protect high-value connections, rebook on partner airlines

---

### 6. Guest Experience Agent (Business)

**Start server**:
```bash
cd guest_experience
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Assess passenger impact: Flight EY123, 615 passengers affected by 3-hour delay. Passenger breakdown: 48 Business Class, 127 elite frequent flyers (Gold/Platinum), 8 special needs (PRM/UMNR). Flight is EU261 eligible. Calculate compensation and service recovery."
```

**Expected output**:
- Total affected: 615 PAX
- EU261 compensation: €400 per PAX = €246,000 total
- Premium/Elite: 175 passengers requiring priority service
- Service recovery: Meals, lounge access, hotel for connections
- Satisfaction risk: HIGH

---

### 7. Cargo Agent (Business)

**Start server**:
```bash
cd cargo
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Analyze cargo impact: Flight EY123 carrying 12,500 kg cargo. Critical shipments: 1 pharmaceutical (temperature-controlled, time-sensitive), 2 high-value e-commerce (SLA: next-day delivery). Assess offload requirements for 3-hour delay."
```

**Expected output**:
- Total weight: 12,500 kg
- Critical shipments: 3
- Revenue at risk: $85,000
- Offload required: NO (3hr delay acceptable)
- Recommendation: Monitor pharmaceutical temp, notify e-commerce customers

---

### 8. Finance Agent (Business)

**Start server**:
```bash
cd finance
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Calculate financial impact: Flight EY123, 3-hour delay scenario vs cancellation. 615 PAX × €400 EU261. Network impact: \$210K. Compare delay costs vs cancellation costs (estimated \$1.2M). Provide cost-benefit analysis."
```

**Expected output**:
- Delay scenario cost: ~$508,000
  - Direct costs: $52,000
  - EU261: €246,000
  - Network: $210,000
- Cancellation cost: ~$1,174,000
- Recommendation: DELAY (saves $666,000)
- Confidence: HIGH

---

### 9. Arbitrator Agent (Coordination)

**Start server**:
```bash
cd arbitrator
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Make final decision: Flight EY123 disruption. Safety assessments: Crew APPROVED (within FTL), Maintenance AIRWORTHY_WITH_MEL, Regulatory CURFEW_RISK. Business impacts: Network \$450K revenue risk, Guest €246K compensation, Cargo \$85K risk, Finance \$508K delay cost vs \$1.17M cancel. Recommend optimal scenario."
```

**Expected output**:
- Selected scenario: Most likely CANCELLATION (due to CURFEW_RISK blocking)
- Weighted score analysis
- Safety compliance verification
- Detailed rationale
- Human approval required: YES

---

### 10. Execution Agent (Coordination)

**Start server**:
```bash
cd execution
agentcore dev
```

**Test query**:
```bash
agentcore invoke --dev "Coordinate execution: Implement decision for Flight EY123. Scenario: Expedited hydraulic repair (3 hours), delay flight, protect 65 high-value connections, provide EU261 compensation, arrange meals/hotels for affected passengers. Break down into executable tasks."
```

**Expected output**:
- Task breakdown:
  - T001: Dispatch maintenance crew
  - T002: Notify operations control center
  - T003: Rebook 65 connecting passengers
  - T004: Process EU261 compensation
  - T005: Arrange meals/hotels
- Timeline with deadlines
- Task owners assigned
- Status tracking

---

## 🔧 Troubleshooting

### Agent won't start

```bash
# Install dependencies
cd <agent_name>
uv sync

# Check Python version (must be 3.10+)
python --version

# Try running directly
python src/main.py
```

### Port 8080 already in use

```bash
# Find and kill process on port 8080
lsof -ti:8080 | xargs kill -9

# Or use a different port (edit .bedrock_agentcore.yaml)
```

### "Command not found: agentcore"

```bash
# Install AgentCore CLI
pip install bedrock-agentcore-starter-toolkit

# Verify installation
agentcore --version
```

### MCP connection errors

MCP server connection is optional. Agents will work without external MCP servers.

---

## 📊 Test Results Template

Create a test results document:

```markdown
# Agent Test Results - [Date]

## Orchestrator
- ✅ Started successfully
- ✅ Processed query
- ⚠️ Response: [paste response]
- Notes: [any observations]

## Crew Compliance
- ✅ Started successfully
- ✅ Processed query
- ✅ Response: [paste response]
- Notes: [any observations]

[... repeat for all agents ...]

## Summary
- Total agents tested: 10
- Passed: X
- Failed: Y
- Issues found: [list]
```

---

## 🎯 Success Criteria

For each agent test, verify:

✅ **Agent starts** without errors
✅ **Accepts query** and processes it
✅ **Returns response** in expected format
✅ **Response includes**:
   - Agent name
   - Category (safety/business/coordination)
   - Analysis or decision
   - Reasoning
✅ **System prompt applied** (check if response reflects domain knowledge)

---

## 📝 Quick Test Commands

Copy-paste ready commands for each agent:

```bash
# Test Orchestrator
cd orchestrator && agentcore dev &
sleep 5 && agentcore invoke --dev "Analyze disruption: Flight EY123, 3hr delay" && kill %1

# Test Crew Compliance
cd ../crew_compliance && agentcore dev &
sleep 5 && agentcore invoke --dev "Check FTL: crew at 9.5hr duty, 3hr delay proposed" && kill %1

# Test Maintenance
cd ../maintenance && agentcore dev &
sleep 5 && agentcore invoke --dev "Assess airworthiness: Hydraulic fault, MEL deferrable" && kill %1

# Test Regulatory
cd ../regulatory && agentcore dev &
sleep 5 && agentcore invoke --dev "Check curfew: LHR arrival 01:30 with 3hr delay" && kill %1

# Test Network
cd ../network && agentcore dev &
sleep 5 && agentcore invoke --dev "Analyze network: 87 connections at risk, \$450K revenue" && kill %1

# Test Guest Experience
cd ../guest_experience && agentcore dev &
sleep 5 && agentcore invoke --dev "Calculate passenger impact: 615 PAX, EU261 eligible" && kill %1

# Test Cargo
cd ../cargo && agentcore dev &
sleep 5 && agentcore invoke --dev "Assess cargo: 12.5T, 3 critical shipments" && kill %1

# Test Finance
cd ../finance && agentcore dev &
sleep 5 && agentcore invoke --dev "Calculate costs: delay vs cancel, EU261 €246K" && kill %1

# Test Arbitrator
cd ../arbitrator && agentcore dev &
sleep 5 && agentcore invoke --dev "Make decision: all safety approved, \$508K delay cost" && kill %1

# Test Execution
cd ../execution && agentcore dev &
sleep 5 && agentcore invoke --dev "Execute: repair hydraulics, delay 3hr, protect connections" && kill %1
```

---

## 🚀 Next Steps After Testing

1. **Document Results**: Record which agents work correctly
2. **Fix Issues**: Update agents that fail or return incorrect responses
3. **Refine Prompts**: Improve system prompts based on test results
4. **Add Logic**: Implement the TODO sections in each agent's main.py
5. **Deploy**: Once all tests pass, deploy to AWS with `agentcore deploy`

---

**Created**: 2026-01-30
**Status**: Ready for testing
**Test Script**: [test_all_agents.sh](test_all_agents.sh)
