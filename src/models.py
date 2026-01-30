"""Data models for SkyMarshal"""

from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any
from datetime import datetime
import uuid


# ============================================================
# CORE EVENT MODELS
# ============================================================

class DisruptionEvent(BaseModel):
    """Disruption event trigger"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    flight_id: int
    flight_number: str
    aircraft_id: str
    aircraft_code: str
    origin: str
    destination: str
    scheduled_departure: datetime
    disruption_type: Literal["technical", "crew", "weather", "atc", "other"]
    description: str
    severity: Literal["low", "medium", "high", "critical"]


# ============================================================
# SAFETY CONSTRAINT MODELS
# ============================================================

class SafetyConstraint(BaseModel):
    """Safety constraint from safety agents"""
    constraint_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    constraint_type: str
    agent_name: str
    binding: bool = True
    affected_resources: List[str] = []
    restriction: str
    reasoning: str  # Chain-of-thought output
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================
# IMPACT ASSESSMENT MODELS
# ============================================================

class ImpactAssessment(BaseModel):
    """Impact assessment from business agents"""
    agent_name: str
    pax_affected: int = 0
    pax_connections_at_risk: int = 0
    elite_pax: int = 0
    cost_estimate: float = 0
    delay_estimate: int = 0
    network_impact_score: float = 0
    cargo_at_risk_kg: float = 0
    temp_controlled_cargo: bool = False
    details: Dict[str, Any] = {}
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================
# RECOVERY PROPOSAL MODELS
# ============================================================

class Action(BaseModel):
    """Individual action in a recovery scenario"""
    action_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    target: str
    parameters: Dict[str, Any] = {}
    description: str


class RecoveryProposal(BaseModel):
    """Recovery proposal from business agent"""
    proposal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    title: str
    description: str
    actions: List[Action]
    estimated_impact: Dict[str, float] = {}
    rationale: str
    timestamp: datetime = Field(default_factory=datetime.now)


class DebateEntry(BaseModel):
    """Debate entry during option formulation"""
    agent_name: str
    round: int
    phase: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


# ============================================================
# SCENARIO MODELS
# ============================================================

class RecoveryScenario(BaseModel):
    """Complete recovery scenario"""
    scenario_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    actions: List[Action]
    estimated_delay: int
    pax_impacted: int
    cost_estimate: float
    confidence: float
    source_proposals: List[str] = []  # Proposal IDs


class OutcomePrediction(BaseModel):
    """Predicted outcomes for a scenario"""
    pax_satisfaction: float  # 0-1 scale
    cost: float
    delay_minutes: int
    secondary_disruptions: int
    execution_reliability: float  # 0-1 scale
    confidence: float  # 0-1 scale


class ScoredScenario(BaseModel):
    """Scenario with score"""
    scenario: RecoveryScenario
    score: float
    prediction: OutcomePrediction


class RankedScenario(BaseModel):
    """Ranked scenario with explanation"""
    rank: int
    scenario: RecoveryScenario
    score: float
    confidence: float
    explanation: str
    pros: List[str]
    cons: List[str]
    sensitivity: Dict[str, float] = {}
    constraint_compliance: Dict[str, bool] = {}


# ============================================================
# HUMAN DECISION MODELS
# ============================================================

class HumanDecision(BaseModel):
    """Human approval decision"""
    chosen_scenario_id: str
    was_override: bool
    override_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    decision_maker: str


# ============================================================
# EXECUTION MODELS
# ============================================================

class ExecutionEvent(BaseModel):
    """Execution event log"""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    agent: str
    action: Action
    status: Literal["started", "progress", "completed", "failed"]
    details: Dict[str, Any] = {}


class ExecutionResult(BaseModel):
    """Complete execution result"""
    scenario_id: str
    actions_completed: int
    actions_failed: int
    execution_time: float
    events: List[ExecutionEvent]
    success: bool


# ============================================================
# HISTORICAL DATA MODELS
# ============================================================

class DisruptionOutcomes(BaseModel):
    """Actual outcomes of a disruption"""
    pax_satisfaction: float
    actual_cost: float
    actual_delay_minutes: int
    secondary_disruptions: int
    execution_success_rate: float
    nps_delta: float
    safety_violations: int = 0


class HistoricalDisruption(BaseModel):
    """Historical disruption record"""
    disruption_id: str
    event_type: str
    timestamp: datetime
    flight_context: Dict[str, Any]
    safety_constraints: List[SafetyConstraint]
    impact_assessments: Dict[str, ImpactAssessment]
    scenarios_evaluated: List[RecoveryScenario]
    chosen_scenario: RecoveryScenario
    arbitrator_rank: int
    human_override: bool
    override_reason: Optional[str]
    outcomes: DisruptionOutcomes
    lessons_learned: List[str] = []


# ============================================================
# STATE MODELS
# ============================================================

class SkyMarshalState(BaseModel):
    """Complete state for LangGraph workflow"""
    # Core data
    disruption: DisruptionEvent
    current_phase: str = "trigger"
    phase_history: List[str] = []
    
    # Agent outputs
    safety_constraints: List[SafetyConstraint] = []
    impact_assessments: Dict[str, ImpactAssessment] = {}
    agent_proposals: List[RecoveryProposal] = []
    debate_log: List[DebateEntry] = []
    
    # Arbitrator outputs
    valid_scenarios: List[RecoveryScenario] = []
    ranked_scenarios: List[RankedScenario] = []
    
    # Human decision
    human_decision: Optional[HumanDecision] = None
    
    # Execution
    execution_results: List[ExecutionResult] = []
    
    # Control flow
    guardrail_triggered: bool = False
    escalation_required: bool = False
    guardrail_triggers: List[str] = []
    
    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        arbitrary_types_allowed = True
