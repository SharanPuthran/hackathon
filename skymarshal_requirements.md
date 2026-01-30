# SkyMarshal - Technical Requirements Specification

## Document Control

**Version**: 1.0
**Status**: Draft
**Date**: 2026-01-29
**Purpose**: Hackathon Implementation

---

## 1. Functional Requirements

### 1.1 Orchestrator Requirements

#### FR-ORC-001: Independent Turn Management
**Priority**: CRITICAL
**Description**: Orchestrator MUST control all agent turn-taking independent of Arbitrator logic

**Acceptance Criteria**:
- Orchestrator maintains phase state machine
- Orchestrator decides which agents execute in each phase
- Arbitrator has NO direct control over agent turns
- Phase transitions only after Orchestrator validation

**Implementation**:
```python
class Orchestrator:
    def manage_phase(self, phase: Phase) -> PhaseResult:
        # Orchestrator decides agent order
        # Arbitrator only evaluates results
        pass
```

#### FR-ORC-002: Shared Memory Management
**Priority**: CRITICAL
**Description**: Maintain accessible shared context for all agents

**Acceptance Criteria**:
- All agents read from shared memory
- Agents write structured outputs to shared memory
- Immutable safety constraints after Phase 2
- Version-controlled state updates

**Data Schema**:
```python
class SharedMemory(BaseModel):
    disruption: DisruptionEvent
    safety_constraints: List[SafetyConstraint]
    impact_assessments: Dict[str, ImpactAssessment]
    scenarios: List[RecoveryScenario]
    human_decision: Optional[HumanDecision]
    execution_log: List[ExecutionStep]
```

#### FR-ORC-003: Phase Coordination
**Priority**: CRITICAL
**Description**: Execute 8-phase workflow with mandatory checkpoints

**Phases**:
1. Trigger Reception
2. Safety Assessment (blocking)
3. Impact Assessment
4. Option Formulation
5. Arbitration
6. Human Approval (blocking)
7. Execution
8. Learning

**Blocking Rules**:
- Cannot proceed past Phase 2 until ALL safety agents complete
- Cannot proceed past Phase 6 without human approval
- Each phase timeout triggers escalation

### 1.2 Safety Agent Requirements

#### FR-SAF-001: Crew Compliance Agent
**Priority**: CRITICAL
**Description**: Enforce flight and duty time limitations

**Constraints to Check**:
- Flight duty period (FDP) limits by sectors
- Rest period requirements (minimum hours)
- Crew qualifications for aircraft type
- Recency requirements (90-day rule)

**Output Format**:
```python
class CrewConstraint(BaseModel):
    constraint_type: Literal["duty_limit", "rest_required", "qualification", "recency"]
    affected_crew: List[str]  # Crew IDs
    restriction: str  # Human-readable
    binding: bool = True  # Always True for safety
    reasoning: str  # Chain-of-thought output
```

**Chain-of-Thought Prompting**:
```
You are the Crew Compliance Agent. Analyze this disruption step-by-step:
1. Current crew duty status for flight [X]
2. Proposed recovery option duty implications
3. FTL regulations that apply
4. Rest requirements if extended duty
5. Final constraint determination

Think through each step carefully before declaring constraints.
```

#### FR-SAF-002: Aircraft Maintenance Agent
**Priority**: CRITICAL
**Description**: Determine aircraft airworthiness and availability

**Constraints to Check**:
- MEL item category (A/B/C/D)
- AOG status determination
- Required maintenance actions before flight
- Aircraft release conditions

**Output Format**:
```python
class MaintenanceConstraint(BaseModel):
    aircraft_id: str
    mel_items: List[MELItem]
    airworthy: bool
    restrictions: List[str]
    required_actions: List[str]
    estimated_release: Optional[datetime]
    reasoning: str
```

#### FR-SAF-003: Regulatory Agent
**Priority**: CRITICAL
**Description**: Apply all regulatory constraints

**Constraints to Check**:
- Active NOTAMs for route
- Airport curfews and slot restrictions
- ATC flow control
- Overflight and landing rights

**Output Format**:
```python
class RegulatoryConstraint(BaseModel):
    constraint_type: Literal["notam", "curfew", "atc", "rights"]
    affected_airports: List[str]
    time_windows: List[TimeWindow]
    restrictions: List[str]
    reasoning: str
```

#### FR-SAF-004: Mandatory Completion
**Priority**: CRITICAL
**Description**: All safety agents MUST complete before proceeding

**Rules**:
- Orchestrator waits for all 3 safety agents
- Timeout: 60 seconds per safety agent
- On timeout: Assume most restrictive constraint
- On failure: Halt process and escalate to human

### 1.3 Business Agent Requirements

#### FR-BUS-001: Two-Phase Operation
**Priority**: CRITICAL
**Description**: Business agents operate in two distinct phases

**Phase A: Impact Assessment** (No solutions)
- Quantify impact based on facts only
- Share structured impact data
- No recovery proposals yet

**Phase B: Option Formulation** (Solutions)
- Propose recovery options
- Consider safety constraints + peer impacts
- Debate and critique peer proposals

#### FR-BUS-002: Network Agent
**Priority**: HIGH
**Description**: Assess and minimize network propagation

**Impact Assessment Output**:
```python
class NetworkImpact(BaseModel):
    downstream_flights: int
    affected_rotations: int
    fleet_utilization_impact: float
    critical_connections: List[str]
    propagation_risk: Literal["low", "medium", "high"]
```

**Recovery Proposals**:
- Aircraft swap scenarios
- Schedule compression options
- Alternative routing

#### FR-BUS-003: Guest Experience Agent
**Priority**: HIGH
**Description**: Protect passenger connections and satisfaction

**Impact Assessment Output**:
```python
class GuestImpact(BaseModel):
    pax_affected: int
    misconnections: int
    elite_pax: int
    nps_impact_estimate: float
    vulnerable_pax: int  # unaccompanied minors, PRM
```

**Recovery Proposals**:
- Rebooking strategies (own metal vs interline)
- Compensation levels
- Hotel and meal arrangements

#### FR-BUS-004: Cargo Agent
**Priority**: HIGH
**Description**: Preserve high-value and perishable cargo

**Impact Assessment Output**:
```python
class CargoImpact(BaseModel):
    total_awbs: int
    high_yield_awbs: int
    perishable_awbs: int
    cold_chain_at_risk: bool
    revenue_at_risk: float
```

**Recovery Proposals**:
- Re-routing options
- Offload priority rankings
- Cold-chain protection measures

#### FR-BUS-005: Finance Agent
**Priority**: HIGH
**Description**: Optimize cost and revenue trade-offs

**Impact Assessment Output**:
```python
class FinanceImpact(BaseModel):
    direct_costs: float
    revenue_loss: float
    compensation_liability: float
    long_term_impact: float
    total_exposure: float
```

**Recovery Proposals**:
- Cost-optimized scenarios
- Revenue protection strategies
- Short vs long-term trade-off analysis

#### FR-BUS-006: Agent Debate Protocol
**Priority**: MEDIUM
**Description**: Structured debate between business agents

**Debate Rounds**:
- Max 3 rounds per scenario
- Each agent can critique peer proposals
- Must reference specific impacts or constraints
- LLM summarizes debate for Arbitrator

**Consensus Criteria**:
- Not required for proceeding
- Disagreements passed to Arbitrator
- Arbitrator makes final ranking decision

### 1.4 Arbitrator Requirements

#### FR-ARB-001: Constraint Enforcement
**Priority**: CRITICAL
**Description**: Reject any scenario violating safety constraints

**Validation Rules**:
```python
def validate_scenario(scenario: RecoveryScenario,
                     constraints: List[SafetyConstraint]) -> bool:
    for constraint in constraints:
        if scenario.violates(constraint):
            return False  # Hard reject
    return True
```

**Zero Tolerance**: No partial violations, no overrides

#### FR-ARB-002: Scenario Composition
**Priority**: HIGH
**Description**: Synthesize valid scenarios from agent proposals

**Process**:
1. Collect all business agent proposals
2. Filter out constraint violations
3. Combine compatible sub-proposals
4. Generate scenario variants
5. Ensure at least 1 valid scenario exists

**Minimum Viable Solution**:
- If no ideal scenarios exist, create conservative baseline
- Conservative baseline: Cancel flight + full PAX protection

#### FR-ARB-003: Historical Learning
**Priority**: HIGH
**Description**: Use past disruptions to rank scenarios

**Historical Features**:
- Similar disruption type
- Similar network impact
- Similar time of day
- Similar resource constraints

**Scoring Function**:
```python
def score_scenario(scenario: RecoveryScenario,
                   history: List[HistoricalDisruption]) -> float:
    similar = find_similar_disruptions(scenario, history)

    weights = {
        "pax_satisfaction": 0.30,
        "cost_efficiency": 0.25,
        "network_stability": 0.25,
        "execution_reliability": 0.20
    }

    return weighted_score(scenario, similar, weights)
```

#### FR-ARB-004: Explainability
**Priority**: HIGH
**Description**: Provide clear rationale for each ranked scenario

**Explanation Components**:
```python
class ScenarioExplanation(BaseModel):
    rank: int
    confidence: float  # 0.0 to 1.0
    rationale: str  # Human-readable explanation
    pros: List[str]
    cons: List[str]
    constraint_compliance: Dict[str, bool]
    historical_precedent: Optional[str]
    sensitivity_analysis: Dict[str, float]  # What-if variations
```

**Sensitivity Analysis**:
- Impact if constraint relaxed
- Impact if different time window
- Impact if additional resources available

#### FR-ARB-005: Ranking Output
**Priority**: HIGH
**Description**: Return top-3 scenarios with full context

**Ranking Criteria** (in order):
1. Safety constraint compliance (mandatory)
2. Historical performance (predictive)
3. Multi-objective optimization score
4. Execution feasibility

### 1.5 No-Consensus Guardrails

#### FR-NCG-001: Debate Timeout
**Priority**: CRITICAL
**Description**: Prevent infinite debate loops

**Rules**:
- Max 3 debate rounds
- Max 5 minutes per round
- On timeout: Pass all proposals to Arbitrator
- Arbitrator decides without further input

#### FR-NCG-002: No Valid Scenarios
**Priority**: CRITICAL
**Description**: Handle case where all scenarios violate constraints

**Fallback Process**:
1. Alert Orchestrator
2. Create conservative baseline (flight cancellation)
3. Request human intervention
4. DO NOT proceed with invalid scenario

#### FR-NCG-003: Partial Agreement
**Priority**: HIGH
**Description**: Execute agreed components even if full consensus missing

**Example**:
- All agents agree: Cancel flight
- Debate: Rebooking strategy differs
- Action: Cancel flight, escalate rebooking to human

#### FR-NCG-004: Escalation Triggers
**Priority**: HIGH
**Description**: Automatic escalation conditions

**Triggers**:
- Safety agent timeout
- Zero valid scenarios
- High confidence discrepancy between agents
- Human request for escalation

**Escalation Actions**:
- Pause execution
- Compile full context package
- Alert Duty Manager
- Wait for human guidance

### 1.6 Human-in-the-Loop Requirements

#### FR-HITL-001: Mandatory Approval
**Priority**: CRITICAL
**Description**: No execution without human approval

**Approval Interface**:
- Display top-3 scenarios
- Show full explanation for each
- Require explicit selection or override
- Capture rationale for decision

#### FR-HITL-002: Override Capability
**Priority**: HIGH
**Description**: Human can override Arbitrator ranking

**Override Options**:
- Select lower-ranked scenario
- Request alternative scenarios
- Provide custom instructions
- Abort operation

**Override Tracking**:
```python
class HumanDecision(BaseModel):
    chosen_scenario_id: str
    was_override: bool
    override_reason: Optional[str]
    timestamp: datetime
    decision_maker: str
```

#### FR-HITL-003: Real-time Updates
**Priority**: MEDIUM
**Description**: Keep human informed during processing

**Update Events**:
- Safety constraints published
- Impact assessments complete
- Scenarios ranked and ready
- Execution progress
- Completion confirmation

### 1.7 Execution Agent Requirements

#### FR-EXE-001: MCP Integration
**Priority**: HIGH
**Description**: Execute via Model Context Protocol services

**MCP Services Required**:
- PSS (Passenger Service System)
- CRS (Crew Rostering System)
- MRO (Maintenance, Repair, Operations)
- CMS (Cargo Management System)
- Notification Service

**Stub Implementation for Hackathon**:
```python
class MCPService:
    async def execute_action(self, action: Action) -> ActionResult:
        # Simulated delay
        await asyncio.sleep(random.uniform(0.5, 2.0))
        # Return success with mock data
        return ActionResult(success=True, data={...})
```

#### FR-EXE-002: Atomic Operations
**Priority**: HIGH
**Description**: Ensure execution consistency

**Transaction Model**:
- Group related actions (e.g., tail swap + crew reassign)
- Execute as transaction
- Rollback on failure
- Log all attempts

#### FR-EXE-003: Progress Streaming
**Priority**: MEDIUM
**Description**: Real-time execution visibility

**Stream Events**:
```python
class ExecutionEvent(BaseModel):
    timestamp: datetime
    agent: str
    action: str
    status: Literal["started", "progress", "completed", "failed"]
    details: Dict[str, Any]
```

### 1.8 Learning Requirements

#### FR-LRN-001: Audit Log Capture
**Priority**: HIGH
**Description**: Complete immutable record of disruption

**Log Contents**:
- Full agent conversation history
- All scenarios evaluated
- Human decision and rationale
- Execution results
- Final KPIs

**Storage Format**: JSON, append-only

#### FR-LRN-002: Historical Database
**Priority**: HIGH
**Description**: Maintain searchable historical disruptions

**Schema**:
```python
class HistoricalDisruption(BaseModel):
    disruption_id: str
    event_type: str
    context: Dict[str, Any]
    safety_constraints: List[SafetyConstraint]
    scenarios: List[RecoveryScenario]
    chosen_scenario: RecoveryScenario
    human_override: bool
    outcomes: DisruptionOutcomes
    lessons_learned: List[str]
```

#### FR-LRN-003: Predictive Model Updates
**Priority**: MEDIUM
**Description**: Continuous improvement of Arbitrator scoring

**Update Frequency**: Weekly or after N disruptions
**Metrics to Track**:
- Scenario acceptance rate
- Human override rate
- Outcome quality (PAX sat, cost, delay)
- Prediction accuracy

---

## 2. Non-Functional Requirements

### 2.1 Performance Requirements

#### NFR-PERF-001: Response Time
**Target**: < 3 minutes from trigger to scenarios
**Breakdown**:
- Safety assessment: < 60 seconds
- Impact assessment: < 30 seconds
- Option formulation: < 45 seconds
- Arbitration: < 30 seconds
- Buffer: 15 seconds

#### NFR-PERF-002: Concurrent Disruptions
**Target**: Handle 3 concurrent disruptions
**Implementation**: Separate state per disruption

#### NFR-PERF-003: LLM Latency
**Target**: < 10 seconds per agent response
**Strategy**: Use Sonnet 4.5 for speed

### 2.2 Reliability Requirements

#### NFR-REL-001: Safety Constraint Violations
**Target**: 0 violations (hard requirement)
**Validation**: Dual validation before execution

#### NFR-REL-002: System Availability
**Target**: 99.9% uptime
**Strategy**: Graceful degradation, human escalation

#### NFR-REL-003: Data Integrity
**Target**: 100% audit log completeness
**Strategy**: Append-only logs, checksums

### 2.3 Security Requirements

#### NFR-SEC-001: Authentication
**Requirement**: Duty Manager authentication required
**Method**: OAuth2 or API key

#### NFR-SEC-002: Authorization
**Requirement**: Role-based access control
**Roles**:
- Duty Manager: Approve/override
- Observer: View-only
- Admin: System configuration

#### NFR-SEC-003: Audit Trails
**Requirement**: Immutable logs
**Method**: Cryptographic signatures

### 2.4 Usability Requirements

#### NFR-USE-001: Explainability
**Requirement**: All decisions must be explainable to non-technical users
**Method**: Plain language summaries

#### NFR-USE-002: Response Time Visibility
**Requirement**: Show progress during processing
**Method**: Real-time status updates

#### NFR-USE-003: Override Ease
**Requirement**: Human can override in < 30 seconds
**Method**: Clear UI with one-click approval

---

## 3. Data Requirements

### 3.1 Input Data

#### DR-IN-001: Disruption Event
```python
class DisruptionEvent(BaseModel):
    event_id: str
    timestamp: datetime
    flight_number: str
    aircraft_id: str
    origin: str
    destination: str
    scheduled_departure: datetime
    disruption_type: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]
```

#### DR-IN-002: Flight Context
- Current PAX manifest
- Cargo AWB list
- Crew assignments
- Aircraft status
- Network connections

#### DR-IN-003: Historical Data
- Past disruptions (min 100 examples)
- Scenario outcomes
- KPI metrics

### 3.2 Output Data

#### DR-OUT-001: Recovery Scenario
```python
class RecoveryScenario(BaseModel):
    scenario_id: str
    title: str
    description: str
    actions: List[Action]
    estimated_delay: int
    pax_impacted: int
    cost_estimate: float
    confidence: float
    pros: List[str]
    cons: List[str]
```

#### DR-OUT-002: Execution Results
```python
class ExecutionResult(BaseModel):
    scenario_id: str
    actions_completed: int
    actions_failed: int
    execution_time: float
    kpis: Dict[str, float]
    audit_log: List[ExecutionEvent]
```

---

## 4. Integration Requirements

### 4.1 LangGraph Integration

#### IR-LG-001: State Machine
**Requirement**: Use LangGraph for orchestration flow
**Nodes**: One per phase + agent groups
**Edges**: Conditional transitions based on phase completion

#### IR-LG-002: State Schema
```python
from langgraph.graph import StateGraph

class SkyMarshalState(TypedDict):
    disruption: DisruptionEvent
    current_phase: str
    safety_constraints: List[SafetyConstraint]
    impact_assessments: Dict[str, ImpactAssessment]
    scenarios: List[RecoveryScenario]
    human_decision: Optional[HumanDecision]
    execution_results: List[ExecutionResult]
```

### 4.2 LLM Integration

#### IR-LLM-001: Model Selection
**Safety Agents**: Claude Sonnet 4.5 (chain-of-thought)
**Business Agents**: Claude Sonnet 4.5
**Arbitrator**: Claude Sonnet 4.5 with extended context

#### IR-LLM-002: Prompt Templates
**Requirement**: Structured prompt templates for each agent
**Format**: System message + few-shot examples + task

### 4.3 Frontend Integration

#### IR-FE-001: WebSocket Connection
**Requirement**: Real-time updates to dashboard
**Events**: Phase changes, agent outputs, execution progress

#### IR-FE-002: API Endpoints
```
POST /disruption/trigger
GET /disruption/{id}/status
POST /disruption/{id}/approve
POST /disruption/{id}/override
GET /disruption/{id}/audit-log
```

---

## 5. Testing Requirements

### 5.1 Unit Testing
- Test each agent in isolation
- Mock shared memory
- Validate output schemas

### 5.2 Integration Testing
- Test full orchestration flow
- Test no-consensus scenarios
- Test escalation triggers

### 5.3 Demo Scenarios
**Scenario 1**: Hydraulic failure (aircraft swap)
**Scenario 2**: Crew timeout (crew swap)
**Scenario 3**: Weather diversion (multi-airport)

---

## 6. Implementation Priorities

### Phase 1: Core Infrastructure (Day 1)
- [ ] Project structure
- [ ] LangGraph orchestrator skeleton
- [ ] Shared memory implementation
- [ ] Basic agent framework

### Phase 2: Safety Agents (Day 1-2)
- [ ] Crew Compliance Agent
- [ ] Maintenance Agent
- [ ] Regulatory Agent
- [ ] Chain-of-thought prompts

### Phase 3: Business Agents (Day 2)
- [ ] Network Agent
- [ ] Guest Experience Agent
- [ ] Cargo Agent
- [ ] Finance Agent
- [ ] Two-phase implementation

### Phase 4: Arbitrator (Day 2-3)
- [ ] Constraint validation
- [ ] Scenario composition
- [ ] Historical scoring
- [ ] Explainability

### Phase 5: Execution & Frontend (Day 3)
- [ ] MCP stubs
- [ ] Execution agents
- [ ] Streamlit dashboard
- [ ] Real-time updates

### Phase 6: Demo Polish (Day 3)
- [ ] Demo scenarios
- [ ] Visualization
- [ ] Audit logs
- [ ] Presentation prep

---

## 7. Success Criteria

### Functional
- [x] All 8 phases execute correctly
- [x] Safety constraints never violated
- [x] Human approval required and captured
- [x] Minimum 1 valid scenario always exists

### Demo
- [x] 5-7 minute end-to-end demo
- [x] Clear visualization of agent interaction
- [x] Explainable recommendations
- [x] Smooth execution with MCP logs

### Technical
- [x] Zero safety violations
- [x] < 3 minute response time
- [x] Complete audit trails
- [x] No-consensus guardrails functional
