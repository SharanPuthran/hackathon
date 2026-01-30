# SkyMarshal - Agentic Airline Disruption Management System

## Executive Summary

SkyMarshal is a multi-agent AI system designed to handle airline operational disruptions through intelligent coordination of safety, business, and execution concerns. The system enforces hard safety constraints while optimizing business outcomes and automating recovery actions under human supervision.

## Core Principles

1. **Safety First**: Non-negotiable safety constraints declared by specialized agents
2. **Human-in-the-Loop**: Duty Manager approval required before execution
3. **Explainable AI**: All decisions include clear rationale and confidence scores
4. **Auditability**: Complete audit trail for regulatory compliance
5. **Orchestrator Independence**: Turn management separate from arbitration logic

## System Architecture

```
┌─────────────────────────────────────────┐
│     Human Duty Manager (HITL)          │
│         Approve / Override              │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Orchestrator                    │
│  - Turn management (independent)        │
│  - Phase coordination                   │
│  - Information collection               │
│  - Shared memory management             │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Skymarshal Arbitrator              │
│  - Constraint enforcement               │
│  - Scenario synthesis                   │
│  - Historical learning                  │
│  - Ranking & explainability             │
│  (Does NOT control turn-taking)         │
└────────────────┬────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼────┐  ┌───▼────┐  ┌───▼────┐
│ SAFETY │  │BUSINESS│  │EXECUTION│
│ AGENTS │  │ AGENTS │  │ AGENTS  │
└────────┘  └────────┘  └─────────┘
```

## Agent Roster

### Safety & Compliance Agents (Mandatory, Non-negotiable)
**Use chain-of-thought reasoning for all decisions**

1. **Crew Compliance Agent**
   - Duty time limits (FTL regulations)
   - Rest period requirements
   - Crew qualifications and ratings
   - Output: Binding crew constraints

2. **Aircraft Maintenance Agent**
   - MEL (Minimum Equipment List) compliance
   - AOG (Aircraft on Ground) status
   - Airworthiness release conditions
   - Output: Aircraft availability constraints

3. **Regulatory Agent**
   - NOTAMs (Notices to Airmen)
   - Airport curfews
   - ATC slot restrictions
   - Bilateral agreements and overflight rights
   - Output: Regulatory constraints

### Business Optimization Agents (Trade-off Negotiation)
**Two-phase operation: Impact Assessment → Solution Proposals**

1. **Network Agent**
   - Downstream flight propagation
   - Aircraft rotation impact
   - Fleet utilization metrics
   - Output: Network impact quantification + recovery options

2. **Guest Experience Agent**
   - Passenger connections at risk
   - Loyalty tier impacts (status holders)
   - NPS (Net Promoter Score) implications
   - Output: PAX impact assessment + rebooking strategies

3. **Cargo Agent**
   - High-yield shipment exposure
   - Perishable freight (cold chain)
   - AWB (Air Waybill) priority classification
   - Output: Cargo risk assessment + re-routing options

4. **Finance Agent**
   - Direct costs (fuel, crew, compensation)
   - Revenue impact (missed connections, cargo)
   - Short vs long-term trade-offs
   - Output: Financial impact + cost-optimized scenarios

### Execution & Recovery Agents (MCP-driven)

1. **Flight Scheduling Agent**
   - Tail swap execution
   - Rotation updates
   - Slot management and coordination

2. **Crew Recovery Agent**
   - Crew pairing adjustments
   - Deadhead arrangements
   - Reserve crew activation

3. **Guest Recovery Agent**
   - PSS (Passenger Service System) re-issuance
   - Hotel and voucher booking
   - Compensation processing

4. **Cargo Recovery Agent**
   - AWB modifications
   - Cold-chain re-routing
   - Priority shipment handling

5. **Communications Agent**
   - Passenger notifications (targeted)
   - Crew updates
   - Operational communications

## Orchestration Flow

### Phase-based Execution (Orchestrator Controlled)

**Phase 1: Trigger**
- Input: Speech-to-text or system event
- Example: "EY551 LHR→AUH has hydraulic issue, cannot depart"

**Phase 2: Safety Assessment (Mandatory)**
- Safety agents publish binding constraints
- Use chain-of-thought reasoning
- All safety agents must complete before proceeding
- Output: Locked constraint set

**Phase 3: Impact Assessment**
- Business agents analyze and quantify impacts
- NO solutions proposed yet
- Share structured impact data
- Output: Impact assessment reports

**Phase 4: Option Formulation & Debate**
- Business agents propose recovery options
- Consider safety constraints + peer impacts
- LLM-assisted debate and critique
- Output: Candidate recovery scenarios

**Phase 5: Arbitration**
- Skymarshal enforces all safety constraints
- Compose valid scenarios from agent proposals
- Score using historical knowledge base
- Rank scenarios by multi-criteria optimization
- Output: Top-3 ranked scenarios with rationale

**Phase 6: Human-in-the-Loop**
- Duty Manager reviews recommendations
- Each scenario shows:
  - Clear rationale
  - Confidence score
  - Sensitivity analysis
  - Constraint compliance proof
- Manager approves, overrides, or requests alternatives

**Phase 7: Execution**
- Execution agents perform MCP operations
- Streaming logs show real-time progress
- Confirmation and validation checks
- Output: Executed actions with audit trail

**Phase 8: Learning**
- Store complete disruption log
- Capture human decisions and overrides
- Update historical knowledge base
- Feed post-mortem training data

## Key Design Decisions

### 1. Orchestrator Independence
**Problem**: Arbitrator must not control turn-taking
**Solution**:
- Orchestrator manages all phase transitions
- Orchestrator decides which agents speak and when
- Arbitrator only evaluates and ranks after agents complete
- Clean separation of concerns

### 2. No-Consensus Guardrails
**Problem**: What if agents cannot agree or debate stalls?
**Solutions**:
- **Time-based timeout**: Max debate rounds per phase
- **Fallback to conservative**: Default to safest option
- **Escalation to human**: Force HITL intervention
- **Minimum viable solution**: Always maintain at least one valid scenario
- **Partial execution**: Execute agreed components, flag contested items

**Guardrail Rules**:
```python
if debate_rounds > MAX_ROUNDS:
    trigger_consensus_timeout()
if no_valid_scenarios:
    escalate_to_human_with_context()
if partial_agreement:
    execute_agreed_actions_only()
```

### 3. Mandatory Agent Completion
**Problem**: Safety agents must complete before proceeding
**Solution**:
- Orchestrator blocks phase transition until all safety agents respond
- Safety agents use chain-of-thought prompting for thorough analysis
- Timeout triggers alert but does NOT skip safety checks
- Conservative fallback: If agent fails, assume most restrictive constraint

### 4. Shared Memory Architecture
**Purpose**: All agents access common context
**Structure**:
```python
{
    "disruption": {
        "event_id": "...",
        "flight": "...",
        "trigger": "...",
        "timestamp": "..."
    },
    "safety_constraints": {
        "crew": [...],
        "maintenance": [...],
        "regulatory": [...]
    },
    "impact_assessments": {
        "network": {...},
        "pax": {...},
        "cargo": {...},
        "finance": {...}
    },
    "scenarios": [...],
    "human_decision": {...},
    "execution_log": [...]
}
```

### 5. Historical Data & Predictive Analysis
**Purpose**: Learn from past disruptions
**Usage**:
- Arbitrator uses historical patterns for ranking
- Predict downstream impacts based on similar past events
- Confidence scoring based on historical accuracy
- Post-mortem analysis to improve future decisions

**Data Structure**:
```python
{
    "disruption_id": "...",
    "context": {...},
    "safety_constraints": [...],
    "scenarios_evaluated": [...],
    "chosen_scenario": {...},
    "human_override": true/false,
    "outcomes": {
        "pax_satisfied": 0.85,
        "cost": 45000,
        "delay_minutes": 120,
        "secondary_disruptions": 2
    }
}
```

## Technology Stack

### Core Framework
- **LangGraph**: State machine orchestration, explicit control flow
- **Python 3.11+**: Primary language
- **Pydantic**: Data validation and shared schemas

### LLM & AI
- **Claude Sonnet 4.5** or **GPT-4o**: Agent reasoning
- **Chain-of-thought prompting**: Safety agents
- **Few-shot learning**: Historical case examples

### Data & Memory
- **Redis** or **In-memory dict**: Shared state during execution
- **PostgreSQL**: Historical data store
- **JSON schemas**: Agent communication protocol

### MCP Integration
- **FastAPI**: REST API stubs for MCP services
- Mock endpoints for:
  - PSS (Passenger Service System)
  - Crew Rostering System
  - Maintenance System
  - Cargo Management
  - Notification Service

### Frontend
- **Streamlit** or **React**: Demo dashboard
- Real-time updates via WebSocket
- Scenario visualization
- Audit log viewer

## Success Metrics

### Technical
- Safety constraint violations: **0 (hard requirement)**
- Response time: < 3 minutes from trigger to scenarios
- Scenario quality: Top-3 include optimal solution 95%+ of time
- System uptime: 99.9%

### Business
- Average delay reduction: 30%
- Passenger satisfaction: +15 NPS points
- Cost per disruption: -25%
- Secondary disruptions: -40%

### Operational
- Human override rate: < 20%
- Scenario acceptance rate: > 80%
- Audit completeness: 100%
- Learning cycle: Weekly model updates

## Demo Flow (5-7 minutes)

1. **Trigger Event** (0:30)
   - Show speech transcript: "EY551 has hydraulic failure"
   - Display event details on dashboard

2. **Safety Assessment** (1:00)
   - Safety agents publish constraints
   - Show "locked" constraints panel
   - Display chain-of-thought reasoning

3. **Impact Assessment** (1:00)
   - Business agents share quantified impacts
   - No solutions yet, just facts
   - Show structured impact cards

4. **Agent Debate** (1:30)
   - Show 2-3 rounds of proposal exchange
   - Display LLM-summarized critiques
   - Highlight constraint enforcement

5. **Arbitration** (1:00)
   - Skymarshal presents Top-3 scenarios
   - Show rationale, confidence, sensitivity
   - Display historical comparison

6. **Human Approval** (0:30)
   - Duty Manager reviews and approves Scenario #2
   - Show decision rationale entry

7. **Execution** (1:30)
   - Stream MCP action logs
   - Show: Tail swap confirmed
   - Show: 47 PAX rebooked
   - Show: Cargo AWB updated
   - Show: Hotels booked
   - Show: Notifications sent

8. **Results** (0:30)
   - Display audit log
   - Show KPI delta vs baseline
   - Highlight learning capture

## Risk Mitigation

### Safety Override Risk
**Risk**: Business agents propose unsafe solutions
**Mitigation**:
- Arbitrator hard-rejects constraint violations
- Safety constraints immutable once published
- Dual validation before execution

### Data Quality Risk
**Risk**: Incomplete or inaccurate input data
**Mitigation**:
- Conservative assumptions when data missing
- Provenance tracking for all inputs
- Confidence scoring based on data quality

### Over-Automation Risk
**Risk**: System executes without proper oversight
**Mitigation**:
- Mandatory HITL approval for all scenarios
- No automatic execution
- Clear escalation paths

### Auditability Risk
**Risk**: Decisions not traceable
**Mitigation**:
- Immutable audit logs
- Complete agent conversation history
- Scenario provenance tracking
- Human decision rationale capture

## Future Enhancements

1. **Multi-disruption coordination**: Handle cascading events
2. **Real-time optimization**: Adjust plans as situation evolves
3. **Predictive disruption**: Anticipate issues before they occur
4. **Crew preference learning**: Optimize for crew satisfaction
5. **Multi-airline coordination**: Interline recovery scenarios
