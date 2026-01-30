# SkyMarshal - Architecture & Design Document

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Dashboard   │  │ Scenario     │  │ Audit Log    │  │
│  │  (Streamlit) │  │ Visualizer   │  │ Viewer       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ WebSocket / REST API
┌──────────────────────────▼──────────────────────────────┐
│                   Orchestration Layer                    │
│  ┌────────────────────────────────────────────────────┐ │
│  │         LangGraph State Machine                    │ │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          │ │
│  │  │Phase1│─>│Phase2│─>│Phase3│─>│Phase4│─> ...    │ │
│  │  └──────┘  └──────┘  └──────┘  └──────┘          │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Shared Memory (Redis/In-Memory)            │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                      Agent Layer                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │   Safety    │  │  Business   │  │  Execution  │     │
│  │   Agents    │  │   Agents    │  │   Agents    │     │
│  │  (3 agents) │  │  (4 agents) │  │  (5 agents) │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Skymarshal Arbitrator                      │ │
│  │  - Constraint Enforcement                          │ │
│  │  - Scenario Ranking                                │ │
│  │  - Historical Learning                             │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                   Integration Layer                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   LLM    │  │   MCP    │  │Historical│              │
│  │ Provider │  │  Stubs   │  │    DB    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction Flow

```
Trigger Event
      │
      ▼
┌──────────────────┐
│  Orchestrator    │◄────────────┐
│  (LangGraph)     │             │
└────────┬─────────┘             │
         │                       │
         ├─► Phase 1: Trigger   │
         │                       │
         ├─► Phase 2: Safety    │
         │   ┌──────────────┐   │
         │   │ Crew Agent   │   │
         │   │ Maint Agent  │───┤ Write to
         │   │ Reg Agent    │   │ Shared Memory
         │   └──────────────┘   │
         │                       │
         ├─► Phase 3: Impact    │
         │   ┌──────────────┐   │
         │   │ Network Agt  │   │
         │   │ Guest Agt    │───┤
         │   │ Cargo Agt    │   │
         │   │ Finance Agt  │   │
         │   └──────────────┘   │
         │                       │
         ├─► Phase 4: Options   │
         │   (Same agents)───────┤
         │                       │
         ├─► Phase 5: Arbitrate │
         │   ┌──────────────┐   │
         │   │ Skymarshal   │◄──┤ Read from
         │   │ Arbitrator   │───┤ Shared Memory
         │   └──────────────┘   │
         │                       │
         ├─► Phase 6: HITL      │
         │   (Wait for human)────┤
         │                       │
         ├─► Phase 7: Execute   │
         │   ┌──────────────┐   │
         │   │ Execution    │   │
         │   │ Agents       │───┤
         │   └──────────────┘   │
         │                       │
         └─► Phase 8: Learning  │
             (Store audit log)───┘
```

---

## 2. LangGraph Implementation

### 2.1 State Schema

```python
from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
import operator

class SkyMarshalState(TypedDict):
    # Core event
    disruption: DisruptionEvent

    # Phase tracking
    current_phase: str
    phase_history: List[str]

    # Agent outputs
    safety_constraints: Annotated[List[SafetyConstraint], operator.add]
    impact_assessments: Dict[str, ImpactAssessment]
    agent_proposals: Annotated[List[RecoveryProposal], operator.add]
    debate_log: Annotated[List[DebateEntry], operator.add]

    # Arbitrator outputs
    valid_scenarios: List[RecoveryScenario]
    ranked_scenarios: List[RankedScenario]

    # Human decision
    human_decision: Optional[HumanDecision]

    # Execution
    execution_log: Annotated[List[ExecutionEvent], operator.add]

    # Metadata
    timestamp: str
    guardrail_triggers: List[str]
    escalation_required: bool
```

### 2.2 Graph Definition

```python
def create_skymarshal_graph() -> StateGraph:
    workflow = StateGraph(SkyMarshalState)

    # Define nodes
    workflow.add_node("trigger", handle_trigger)
    workflow.add_node("safety_assessment", run_safety_agents)
    workflow.add_node("impact_assessment", run_impact_assessment)
    workflow.add_node("option_formulation", run_option_formulation)
    workflow.add_node("arbitration", run_arbitrator)
    workflow.add_node("human_approval", wait_for_human)
    workflow.add_node("execution", run_execution_agents)
    workflow.add_node("learning", store_learning)

    # Guardrail nodes
    workflow.add_node("escalate", handle_escalation)
    workflow.add_node("timeout_handler", handle_timeout)

    # Define edges
    workflow.add_edge("trigger", "safety_assessment")
    workflow.add_conditional_edges(
        "safety_assessment",
        check_safety_completion,
        {
            "complete": "impact_assessment",
            "timeout": "timeout_handler",
            "escalate": "escalate"
        }
    )
    workflow.add_edge("impact_assessment", "option_formulation")
    workflow.add_conditional_edges(
        "option_formulation",
        check_debate_completion,
        {
            "complete": "arbitration",
            "continue_debate": "option_formulation",
            "timeout": "arbitration"  # Force to arbitration
        }
    )
    workflow.add_conditional_edges(
        "arbitration",
        check_valid_scenarios,
        {
            "has_scenarios": "human_approval",
            "no_scenarios": "escalate"
        }
    )
    workflow.add_conditional_edges(
        "human_approval",
        check_human_decision,
        {
            "approved": "execution",
            "override": "execution",
            "reject": "option_formulation"  # Request alternatives
        }
    )
    workflow.add_edge("execution", "learning")
    workflow.add_edge("learning", END)

    # Set entry point
    workflow.set_entry_point("trigger")

    return workflow.compile()
```

### 2.3 Node Implementations

#### Phase 1: Trigger
```python
async def handle_trigger(state: SkyMarshalState) -> SkyMarshalState:
    """Initialize disruption and prepare shared context"""
    disruption = state["disruption"]

    # Initialize shared memory
    shared_memory.set(disruption.event_id, {
        "disruption": disruption,
        "safety_constraints": [],
        "impact_assessments": {},
        "scenarios": [],
        "execution_log": []
    })

    state["current_phase"] = "trigger"
    state["phase_history"] = ["trigger"]
    state["timestamp"] = datetime.now().isoformat()

    return state
```

#### Phase 2: Safety Assessment
```python
async def run_safety_agents(state: SkyMarshalState) -> SkyMarshalState:
    """Execute all safety agents with mandatory completion"""

    safety_agents = [
        CrewComplianceAgent(),
        MaintenanceAgent(),
        RegulatoryAgent()
    ]

    constraints = []
    timeout_seconds = 60

    # Run all safety agents in parallel with timeout
    tasks = [
        asyncio.wait_for(
            agent.assess(state["disruption"]),
            timeout=timeout_seconds
        )
        for agent in safety_agents
    ]

    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Timeout or error: Assume most restrictive
                logger.error(f"Safety agent {i} failed: {result}")
                constraints.append(create_conservative_constraint(safety_agents[i]))
            else:
                constraints.extend(result)

        # Update shared memory with immutable constraints
        shared_memory.set_constraints(state["disruption"].event_id, constraints)

        state["safety_constraints"] = constraints
        state["current_phase"] = "safety_assessment"

    except Exception as e:
        logger.critical(f"Safety assessment failed: {e}")
        state["escalation_required"] = True
        state["guardrail_triggers"].append("safety_assessment_failure")

    return state
```

#### Phase 3: Impact Assessment
```python
async def run_impact_assessment(state: SkyMarshalState) -> SkyMarshalState:
    """Business agents quantify impacts WITHOUT proposing solutions"""

    business_agents = [
        NetworkAgent(),
        GuestExperienceAgent(),
        CargoAgent(),
        FinanceAgent()
    ]

    impact_assessments = {}

    # Prepare context for agents
    context = {
        "disruption": state["disruption"],
        "safety_constraints": state["safety_constraints"]
    }

    # Run impact assessments in parallel
    tasks = [agent.assess_impact(context) for agent in business_agents]
    results = await asyncio.gather(*tasks)

    for agent, assessment in zip(business_agents, results):
        impact_assessments[agent.name] = assessment

    # Share impacts in memory
    shared_memory.update_impacts(
        state["disruption"].event_id,
        impact_assessments
    )

    state["impact_assessments"] = impact_assessments
    state["current_phase"] = "impact_assessment"

    return state
```

#### Phase 4: Option Formulation
```python
async def run_option_formulation(state: SkyMarshalState) -> SkyMarshalState:
    """Business agents propose solutions and debate"""

    business_agents = [
        NetworkAgent(),
        GuestExperienceAgent(),
        CargoAgent(),
        FinanceAgent()
    ]

    debate_round = len([d for d in state.get("debate_log", [])
                       if d.phase == "option_formulation"]) // len(business_agents)

    max_rounds = 3

    if debate_round >= max_rounds:
        # Timeout guardrail
        state["guardrail_triggers"].append("debate_timeout")
        return state

    # Prepare full context
    context = {
        "disruption": state["disruption"],
        "safety_constraints": state["safety_constraints"],
        "impact_assessments": state["impact_assessments"],
        "previous_proposals": state.get("agent_proposals", []),
        "debate_log": state.get("debate_log", [])
    }

    # Each agent proposes or critiques
    new_proposals = []
    new_debate_entries = []

    for agent in business_agents:
        if debate_round == 0:
            # First round: Generate proposals
            proposal = await agent.propose_solution(context)
            new_proposals.append(proposal)
        else:
            # Later rounds: Critique and refine
            critique = await agent.critique_proposals(context)
            new_debate_entries.append(DebateEntry(
                agent=agent.name,
                round=debate_round,
                phase="option_formulation",
                content=critique
            ))

    state["agent_proposals"] = state.get("agent_proposals", []) + new_proposals
    state["debate_log"] = state.get("debate_log", []) + new_debate_entries
    state["current_phase"] = "option_formulation"

    return state
```

#### Phase 5: Arbitration
```python
async def run_arbitrator(state: SkyMarshalState) -> SkyMarshalState:
    """Skymarshal validates, composes, and ranks scenarios"""

    arbitrator = SkyMarshalArbitrator()

    context = {
        "disruption": state["disruption"],
        "safety_constraints": state["safety_constraints"],
        "impact_assessments": state["impact_assessments"],
        "agent_proposals": state["agent_proposals"],
        "debate_log": state["debate_log"]
    }

    # Step 1: Validate all proposals against constraints
    valid_proposals = arbitrator.validate_proposals(
        state["agent_proposals"],
        state["safety_constraints"]
    )

    # Step 2: Compose scenarios
    scenarios = arbitrator.compose_scenarios(valid_proposals)

    # Guardrail: Ensure at least one valid scenario
    if not scenarios:
        logger.warning("No valid scenarios from proposals")
        scenarios = [arbitrator.create_conservative_baseline(context)]

    # Step 3: Score using historical data
    scored_scenarios = await arbitrator.score_scenarios(scenarios, context)

    # Step 4: Rank and explain
    ranked_scenarios = arbitrator.rank_and_explain(scored_scenarios)

    state["valid_scenarios"] = scenarios
    state["ranked_scenarios"] = ranked_scenarios[:3]  # Top 3
    state["current_phase"] = "arbitration"

    return state
```

---

## 3. Agent Architecture

### 3.1 Base Agent Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseAgent(ABC):
    def __init__(self, name: str, llm_client: Any):
        self.name = name
        self.llm = llm_client
        self.system_prompt = self._load_system_prompt()

    @abstractmethod
    def _load_system_prompt(self) -> str:
        """Load agent-specific system prompt"""
        pass

    async def invoke(self, user_prompt: str, context: Dict[str, Any]) -> str:
        """Call LLM with system + user prompt"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self._format_prompt(user_prompt, context)}
        ]

        response = await self.llm.chat(messages)
        return response.content

    def _format_prompt(self, prompt: str, context: Dict[str, Any]) -> str:
        """Format prompt with context"""
        return f"{prompt}\n\nContext:\n{json.dumps(context, indent=2)}"
```

### 3.2 Safety Agent (Chain-of-Thought)

```python
class CrewComplianceAgent(BaseAgent):
    def _load_system_prompt(self) -> str:
        return """You are the Crew Compliance Safety Agent for airline operations.

Your role is to enforce Flight and Duty Time Limitations (FTL) regulations.

CRITICAL: You MUST use chain-of-thought reasoning for all assessments.

For each disruption scenario, think through:
1. Current crew duty status (flight duty period start, current hours)
2. Proposed recovery implications on duty time
3. Applicable FTL regulations (EU/US/Local)
4. Rest requirements if duty extended
5. Crew qualifications and recency
6. Final binding constraints

Output your reasoning step-by-step, then declare constraints.

Format:
<thinking>
Step 1: [Analysis]
Step 2: [Regulation check]
...
</thinking>

<constraints>
- Constraint 1: [Description]
- Constraint 2: [Description]
</constraints>
"""

    async def assess(self, disruption: DisruptionEvent) -> List[SafetyConstraint]:
        """Assess crew constraints with chain-of-thought"""

        prompt = f"""Assess crew compliance for this disruption:

Flight: {disruption.flight_number}
Aircraft: {disruption.aircraft_id}
Scheduled Departure: {disruption.scheduled_departure}
Issue: {disruption.description}

Current crew duty status: [Load from crew system]
Recovery options being considered: [Brief summary]

Use step-by-step reasoning to determine all crew-related constraints.
"""

        context = {"disruption": disruption.dict()}
        response = await self.invoke(prompt, context)

        # Parse response for constraints
        constraints = self._parse_constraints(response)
        return constraints

    def _parse_constraints(self, llm_response: str) -> List[SafetyConstraint]:
        """Extract structured constraints from LLM response"""
        # Parse <constraints> section
        # Convert to SafetyConstraint objects
        pass
```

### 3.3 Business Agent (Two-Phase)

```python
class GuestExperienceAgent(BaseAgent):
    def _load_system_prompt(self) -> str:
        return """You are the Guest Experience Agent for airline disruption management.

Your goal: Protect passenger satisfaction and loyalty.

You operate in TWO phases:

PHASE 1 - Impact Assessment:
- Quantify passengers affected
- Identify misconnections
- Count elite status passengers
- Estimate NPS impact
- DO NOT propose solutions yet

PHASE 2 - Solution Proposals:
- Propose rebooking strategies
- Consider compensation levels
- Optimize for guest satisfaction
- Reference peer agent impacts
- Debate and refine with other agents

Always reference safety constraints (you cannot violate them).
"""

    async def assess_impact(self, context: Dict[str, Any]) -> ImpactAssessment:
        """Phase 1: Quantify guest experience impact"""

        prompt = """Analyze the guest experience impact of this disruption.

Provide ONLY quantified impacts, NO solutions.

Required metrics:
- Total passengers affected
- Number of misconnections
- Elite status passengers impacted
- Estimated NPS delta
- Vulnerable passengers (unaccompanied minors, PRM)

Use structured format.
"""

        response = await self.invoke(prompt, context)
        return self._parse_impact_assessment(response)

    async def propose_solution(self, context: Dict[str, Any]) -> RecoveryProposal:
        """Phase 2: Propose guest-focused recovery options"""

        prompt = """Based on the impact assessment and peer agent impacts, propose recovery options.

Consider:
1. Safety constraints (cannot be violated)
2. Network impact from Network Agent
3. Cargo constraints from Cargo Agent
4. Financial trade-offs from Finance Agent

Propose 1-2 guest-focused recovery strategies that optimize for NPS while respecting constraints.
"""

        response = await self.invoke(prompt, context)
        return self._parse_proposal(response)

    async def critique_proposals(self, context: Dict[str, Any]) -> str:
        """Phase 2 (debate): Critique peer proposals"""

        prompt = """Review the recovery proposals from other agents.

Provide constructive critique from a guest experience perspective:
- Which proposals protect passengers best?
- What guest satisfaction risks do you see?
- What improvements would you suggest?

Be specific and reference proposal IDs.
"""

        response = await self.invoke(prompt, context)
        return response
```

---

## 4. Skymarshal Arbitrator Design

### 4.1 Core Responsibilities

```python
class SkyMarshalArbitrator:
    def __init__(self, llm_client: Any, historical_db: HistoricalDatabase):
        self.llm = llm_client
        self.history = historical_db
        self.system_prompt = self._load_system_prompt()

    def validate_proposals(
        self,
        proposals: List[RecoveryProposal],
        constraints: List[SafetyConstraint]
    ) -> List[RecoveryProposal]:
        """Hard filter: Reject any proposal violating constraints"""

        valid_proposals = []

        for proposal in proposals:
            violations = self._check_violations(proposal, constraints)

            if not violations:
                valid_proposals.append(proposal)
            else:
                logger.info(f"Rejected proposal {proposal.id}: {violations}")

        return valid_proposals

    def _check_violations(
        self,
        proposal: RecoveryProposal,
        constraints: List[SafetyConstraint]
    ) -> List[str]:
        """Check if proposal violates any safety constraint"""
        violations = []

        for constraint in constraints:
            if self._violates_constraint(proposal, constraint):
                violations.append(f"Violates {constraint.constraint_type}")

        return violations

    def compose_scenarios(
        self,
        valid_proposals: List[RecoveryProposal]
    ) -> List[RecoveryScenario]:
        """Combine compatible proposals into complete scenarios"""

        # Use LLM to intelligently combine sub-proposals
        # Each scenario must address all aspects: network, pax, cargo, finance

        scenarios = []

        # Strategy 1: Single-agent dominant scenarios
        for proposal in valid_proposals:
            scenario = self._build_scenario_from_proposal(proposal, valid_proposals)
            scenarios.append(scenario)

        # Strategy 2: Hybrid scenarios (if compatible)
        hybrid_scenarios = self._find_compatible_combinations(valid_proposals)
        scenarios.extend(hybrid_scenarios)

        return scenarios

    async def score_scenarios(
        self,
        scenarios: List[RecoveryScenario],
        context: Dict[str, Any]
    ) -> List[ScoredScenario]:
        """Use historical data to predict scenario outcomes"""

        scored = []

        for scenario in scenarios:
            # Find similar historical disruptions
            similar = self.history.find_similar(context["disruption"], limit=10)

            # Use LLM to predict outcomes based on historical patterns
            prediction = await self._predict_outcomes(scenario, similar)

            # Calculate multi-objective score
            score = self._calculate_score(prediction)

            scored.append(ScoredScenario(
                scenario=scenario,
                score=score,
                confidence=prediction.confidence,
                prediction=prediction
            ))

        return scored

    def rank_and_explain(
        self,
        scored_scenarios: List[ScoredScenario]
    ) -> List[RankedScenario]:
        """Rank scenarios and generate explanations"""

        # Sort by score
        sorted_scenarios = sorted(
            scored_scenarios,
            key=lambda x: x.score,
            reverse=True
        )

        ranked = []

        for rank, scored in enumerate(sorted_scenarios, start=1):
            explanation = self._generate_explanation(scored, rank)
            sensitivity = self._calculate_sensitivity(scored)

            ranked.append(RankedScenario(
                rank=rank,
                scenario=scored.scenario,
                score=scored.score,
                confidence=scored.confidence,
                explanation=explanation,
                sensitivity=sensitivity
            ))

        return ranked

    async def _predict_outcomes(
        self,
        scenario: RecoveryScenario,
        historical_cases: List[HistoricalDisruption]
    ) -> OutcomePrediction:
        """Use LLM + historical data to predict scenario outcomes"""

        prompt = f"""Predict the outcomes of this recovery scenario based on historical similar disruptions.

Scenario: {scenario.description}
Actions: {scenario.actions}

Historical similar cases:
{self._format_historical_cases(historical_cases)}

Predict:
1. Passenger satisfaction (0-1)
2. Total cost
3. Delay minutes
4. Secondary disruptions
5. Execution reliability (0-1)

Provide confidence score (0-1) based on historical similarity.
"""

        response = await self.llm.chat([
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ])

        return self._parse_prediction(response.content)

    def _calculate_score(self, prediction: OutcomePrediction) -> float:
        """Multi-objective scoring function"""

        weights = {
            "pax_satisfaction": 0.30,
            "cost_efficiency": 0.25,
            "delay_minimization": 0.25,
            "execution_reliability": 0.20
        }

        # Normalize metrics to 0-1 scale
        normalized = {
            "pax_satisfaction": prediction.pax_satisfaction,
            "cost_efficiency": 1.0 - min(prediction.cost / 100000, 1.0),
            "delay_minimization": 1.0 - min(prediction.delay_minutes / 300, 1.0),
            "execution_reliability": prediction.execution_reliability
        }

        score = sum(normalized[k] * weights[k] for k in weights.keys())

        return score

    def create_conservative_baseline(
        self,
        context: Dict[str, Any]
    ) -> RecoveryScenario:
        """Fallback: Generate safe, conservative scenario"""

        return RecoveryScenario(
            scenario_id=str(uuid.uuid4()),
            title="Conservative Baseline: Flight Cancellation",
            description="Cancel flight and provide full passenger protection",
            actions=[
                Action(type="cancel_flight"),
                Action(type="rebook_all_passengers"),
                Action(type="hotel_vouchers"),
                Action(type="compensation")
            ],
            estimated_delay=0,  # Cancelled
            pax_impacted=context["impact_assessments"]["pax"].pax_affected,
            cost_estimate=50000,  # Conservative estimate
            confidence=1.0  # Always safe
        )
```

---

## 5. Guardrails Implementation

### 5.1 No-Consensus Handler

```python
class NoConsensusGuardrail:
    def __init__(self, max_debate_rounds: int = 3):
        self.max_rounds = max_debate_rounds

    def check_debate_completion(self, state: SkyMarshalState) -> str:
        """Determine if debate should continue or timeout"""

        debate_entries = state.get("debate_log", [])
        current_round = self._calculate_round(debate_entries)

        if current_round >= self.max_rounds:
            logger.warning(f"Debate timeout at round {current_round}")
            return "timeout"

        # Check for convergence signals
        if self._has_convergence(debate_entries):
            return "complete"

        return "continue_debate"

    def _has_convergence(self, debate_log: List[DebateEntry]) -> bool:
        """Detect if agents are converging (optional optimization)"""
        # Could use LLM to analyze debate for convergence signals
        # For now, rely on round limit
        return False
```

### 5.2 Safety Timeout Handler

```python
async def handle_timeout(state: SkyMarshalState) -> SkyMarshalState:
    """Handle safety agent timeout with conservative fallback"""

    logger.error("Safety agent timeout occurred")

    # Identify which agents timed out
    completed_agents = len(state.get("safety_constraints", []))
    expected_agents = 3

    if completed_agents < expected_agents:
        # Add most restrictive constraints for missing agents
        for i in range(expected_agents - completed_agents):
            state["safety_constraints"].append(
                SafetyConstraint(
                    constraint_type="timeout_conservative",
                    binding=True,
                    restriction="Conservative fallback due to agent timeout",
                    reasoning="Timeout: Assuming most restrictive"
                )
            )

    state["guardrail_triggers"].append("safety_timeout")
    state["escalation_required"] = True

    # Continue to next phase but flag for human review
    return state
```

### 5.3 No Valid Scenarios Handler

```python
async def handle_escalation(state: SkyMarshalState) -> SkyMarshalState:
    """Handle critical failures requiring human intervention"""

    logger.critical("Escalation triggered")

    # Prepare escalation package
    escalation_context = {
        "reason": state["guardrail_triggers"],
        "disruption": state["disruption"],
        "safety_constraints": state["safety_constraints"],
        "attempted_proposals": state.get("agent_proposals", []),
        "timestamp": datetime.now().isoformat()
    }

    # Notify duty manager
    await notify_duty_manager_urgent(escalation_context)

    # Halt execution and wait for human guidance
    state["escalation_required"] = True
    state["current_phase"] = "escalated"

    return state
```

---

## 6. Data Schemas

### 6.1 Core Data Models

```python
from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from datetime import datetime

class DisruptionEvent(BaseModel):
    event_id: str
    timestamp: datetime
    flight_number: str
    aircraft_id: str
    origin: str
    destination: str
    scheduled_departure: datetime
    disruption_type: Literal["technical", "crew", "weather", "atc", "other"]
    description: str
    severity: Literal["low", "medium", "high", "critical"]

class SafetyConstraint(BaseModel):
    constraint_type: str
    binding: bool = True
    affected_resources: List[str] = []
    restriction: str
    reasoning: str  # Chain-of-thought output

class ImpactAssessment(BaseModel):
    agent_name: str
    pax_affected: int = 0
    cost_estimate: float = 0
    delay_estimate: int = 0
    network_impact: float = 0
    details: Dict[str, Any]

class RecoveryProposal(BaseModel):
    proposal_id: str
    agent_name: str
    title: str
    actions: List[Action]
    estimated_impact: Dict[str, float]
    rationale: str

class Action(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    target: str
    parameters: Dict[str, Any]

class RecoveryScenario(BaseModel):
    scenario_id: str
    title: str
    description: str
    actions: List[Action]
    estimated_delay: int
    pax_impacted: int
    cost_estimate: float
    confidence: float

class RankedScenario(BaseModel):
    rank: int
    scenario: RecoveryScenario
    score: float
    confidence: float
    explanation: str
    pros: List[str]
    cons: List[str]
    sensitivity: Dict[str, float]

class HumanDecision(BaseModel):
    chosen_scenario_id: str
    was_override: bool
    override_reason: Optional[str]
    timestamp: datetime
    decision_maker: str

class ExecutionEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime
    agent: str
    action: Action
    status: Literal["started", "progress", "completed", "failed"]
    details: Dict[str, Any]
```

---

## 7. Historical Learning System

### 7.1 Historical Database Schema

```python
class HistoricalDisruption(BaseModel):
    disruption_id: str
    event_type: str
    timestamp: datetime

    # Context
    flight_context: Dict[str, Any]
    safety_constraints: List[SafetyConstraint]
    impact_assessments: Dict[str, ImpactAssessment]

    # Decision process
    scenarios_evaluated: List[RecoveryScenario]
    chosen_scenario: RecoveryScenario
    arbitrator_rank: int
    human_override: bool
    override_reason: Optional[str]

    # Outcomes
    outcomes: DisruptionOutcomes
    lessons_learned: List[str]

class DisruptionOutcomes(BaseModel):
    pax_satisfaction: float  # 0-1 scale
    actual_cost: float
    actual_delay_minutes: int
    secondary_disruptions: int
    execution_success_rate: float
    nps_delta: float
```

### 7.2 Similarity Search

```python
class HistoricalDatabase:
    def find_similar(
        self,
        disruption: DisruptionEvent,
        limit: int = 10
    ) -> List[HistoricalDisruption]:
        """Find similar historical disruptions for predictive analysis"""

        # Feature extraction
        features = self._extract_features(disruption)

        # Vector similarity search (could use embeddings)
        similar = self.db.query(
            filter={
                "disruption_type": disruption.disruption_type,
                "severity": {"$in": [disruption.severity, self._adjacent_severity(disruption.severity)]}
            },
            limit=limit * 2
        )

        # Rank by feature similarity
        ranked = sorted(
            similar,
            key=lambda x: self._similarity_score(features, self._extract_features(x)),
            reverse=True
        )

        return ranked[:limit]

    def _extract_features(self, disruption: DisruptionEvent) -> Dict[str, Any]:
        return {
            "disruption_type": disruption.disruption_type,
            "severity": disruption.severity,
            "time_of_day": disruption.scheduled_departure.hour,
            "day_of_week": disruption.scheduled_departure.weekday(),
            "origin": disruption.origin,
            "destination": disruption.destination
        }
```

---

## 8. Demo Implementation

### 8.1 Demo Scenario

```python
DEMO_DISRUPTION = DisruptionEvent(
    event_id="demo_001",
    timestamp=datetime.now(),
    flight_number="EY551",
    aircraft_id="A6-BND",
    origin="LHR",
    destination="AUH",
    scheduled_departure=datetime.now() + timedelta(hours=2),
    disruption_type="technical",
    description="Hydraulic system failure detected during pre-flight check",
    severity="high"
)
```

### 8.2 Streamlit Dashboard Structure

```python
import streamlit as st

def render_dashboard():
    st.title("🛫 SkyMarshal - Disruption Management")

    # Phase tracker
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Phase", state["current_phase"])
    with col2:
        st.metric("Time Elapsed", f"{elapsed}s")
    with col3:
        st.metric("Status", "Processing" if running else "Complete")

    # Safety Constraints (locked)
    st.subheader("🔒 Safety Constraints")
    for constraint in state["safety_constraints"]:
        with st.expander(f"{constraint.constraint_type}"):
            st.write(constraint.restriction)
            st.caption(constraint.reasoning)

    # Impact Assessments
    st.subheader("📊 Impact Assessment")
    cols = st.columns(4)
    for i, (agent, impact) in enumerate(state["impact_assessments"].items()):
        with cols[i]:
            st.metric(agent, impact.pax_affected, delta=impact.cost_estimate)

    # Agent Debate
    if state["debate_log"]:
        st.subheader("💬 Agent Debate")
        for entry in state["debate_log"]:
            st.chat_message(entry.agent).write(entry.content)

    # Ranked Scenarios
    if state["ranked_scenarios"]:
        st.subheader("🎯 Recommended Scenarios")
        for scenario in state["ranked_scenarios"]:
            with st.expander(f"#{scenario.rank}: {scenario.scenario.title}"):
                st.write(scenario.explanation)
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Pros:**")
                    for pro in scenario.pros:
                        st.write(f"✅ {pro}")
                with col2:
                    st.write("**Cons:**")
                    for con in scenario.cons:
                        st.write(f"⚠️ {con}")

                if st.button("Approve", key=f"approve_{scenario.rank}"):
                    approve_scenario(scenario)

    # Execution Log
    if state["execution_log"]:
        st.subheader("⚙️ Execution Progress")
        for event in state["execution_log"]:
            st.write(f"{event.timestamp}: {event.agent} - {event.action.type} - {event.status}")
```

---

## 9. Implementation Checklist

### Day 1
- [ ] Set up LangGraph project structure
- [ ] Implement SkyMarshalState schema
- [ ] Create base orchestrator graph
- [ ] Implement shared memory system
- [ ] Build BaseAgent class
- [ ] Create 3 safety agents with chain-of-thought
- [ ] Test Phase 1-2 flow

### Day 2
- [ ] Implement 4 business agents (two-phase)
- [ ] Build debate protocol
- [ ] Implement SkyMarshalArbitrator core
- [ ] Add constraint validation
- [ ] Create scenario composition logic
- [ ] Implement historical scoring
- [ ] Test Phase 3-5 flow

### Day 3
- [ ] Build 5 execution agents
- [ ] Create MCP stubs
- [ ] Implement no-consensus guardrails
- [ ] Build Streamlit dashboard
- [ ] Add real-time updates
- [ ] Create demo scenarios
- [ ] Polish and test full flow

---

This architecture provides a complete blueprint for implementing SkyMarshal with clear separation of concerns, proper guardrails, and independent orchestration control.
