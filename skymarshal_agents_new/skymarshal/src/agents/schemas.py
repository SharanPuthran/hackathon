"""
Structured output schemas for inter-agent communication using Pydantic.

This module defines all Pydantic models used for:
1. Agent input/output schemas for multi-round orchestration
2. Structured data extraction from natural language prompts
3. Inter-agent communication and response collation
4. Validation of agent responses and execution phases

Architecture Overview
---------------------

The schema architecture supports a three-phase multi-round orchestration flow:

Phase 1 (Initial Recommendations):
    - Orchestrator sends DisruptionPayload with user_prompt to all agents
    - Agents extract FlightInfo using LangChain's with_structured_output()
    - Agents return AgentResponse with recommendations
    - Orchestrator collates responses into Collation

Phase 2 (Revision Round):
    - Orchestrator sends DisruptionPayload with other_recommendations
    - Agents review other agents' findings and revise their own
    - Agents return updated AgentResponse
    - Orchestrator collates revised responses into Collation

Phase 3 (Arbitration):
    - Arbitrator receives all revised recommendations
    - Arbitrator resolves conflicts and makes final decision
    - System returns final decision to user

Key Design Principles
---------------------

1. Natural Language Input: Agents receive raw user prompts, not structured fields
2. Autonomous Extraction: Agents use LangChain structured output to extract data
3. Type Safety: All schemas use Pydantic for validation and type checking
4. Auditability: All responses include timestamps, reasoning, and data sources
5. Safety Priority: Safety agents can provide binding_constraints

Schema Categories
-----------------

Legacy Agent Schemas (Pre-Multi-Round):
    - CrewComplianceOutput, MaintenanceOutput, RegulatoryOutput
    - NetworkOutput, GuestExperienceOutput, CargoOutput, FinanceOutput
    - OrchestratorOutput, OrchestratorValidation
    - These are maintained for backward compatibility

Multi-Round Orchestration Schemas:
    - FlightInfo: Extracted from natural language prompts
    - DisruptionPayload: Agent invocation payload
    - AgentResponse: Standardized agent response format
    - Collation: Aggregated responses from a phase

Usage Examples
--------------

Example 1: Extracting flight info from natural language
    >>> from langchain_aws import ChatBedrock
    >>> llm = ChatBedrock(model_id="anthropic.claude-sonnet-4-20250514-v1:0")
    >>> structured_llm = llm.with_structured_output(FlightInfo)
    >>> 
    >>> user_prompt = "Flight EY123 on January 20th had a mechanical failure"
    >>> flight_info = structured_llm.invoke(user_prompt)
    >>> print(flight_info)
    FlightInfo(
        flight_number='EY123',
        date='2026-01-20',
        disruption_event='mechanical failure'
    )

Example 2: Creating an agent payload for initial phase
    >>> payload = DisruptionPayload(
    ...     user_prompt="Flight EY456 yesterday was delayed due to weather",
    ...     phase="initial"
    ... )
    >>> print(payload.phase)
    'initial'
    >>> print(payload.other_recommendations)
    None

Example 3: Creating an agent payload for revision phase
    >>> initial_collation = {...}  # Results from phase 1
    >>> payload = DisruptionPayload(
    ...     user_prompt="Flight EY456 yesterday was delayed due to weather",
    ...     phase="revision",
    ...     other_recommendations=initial_collation
    ... )

Example 4: Creating an agent response
    >>> from datetime import datetime, timezone
    >>> response = AgentResponse(
    ...     agent_name="crew_compliance",
    ...     recommendation="Approve delay with crew change",
    ...     confidence=0.95,
    ...     binding_constraints=["Crew must have 10 hours rest"],
    ...     reasoning="Current crew exceeds FDP limits",
    ...     data_sources=["CrewRoster", "CrewMembers"],
    ...     extracted_flight_info={
    ...         "flight_number": "EY123",
    ...         "date": "2026-01-20",
    ...         "disruption_event": "mechanical failure"
    ...     },
    ...     timestamp=datetime.now(timezone.utc).isoformat()
    ... )

Example 5: Creating a collation
    >>> collation = Collation(
    ...     phase="initial",
    ...     responses={
    ...         "crew_compliance": crew_response,
    ...         "maintenance": maintenance_response,
    ...         # ... other agents
    ...     },
    ...     timestamp=datetime.now(timezone.utc).isoformat(),
    ...     duration_seconds=8.5
    ... )
    >>> 
    >>> # Get only successful responses
    >>> successful = collation.get_successful_responses()
    >>> 
    >>> # Get agent counts by status
    >>> counts = collation.get_agent_count()
    >>> print(counts)
    {'success': 6, 'timeout': 1, 'error': 0}

Validation Rules
----------------

FlightInfo:
    - flight_number: Must match pattern EY\d{3,4} (e.g., EY123, EY1234)
    - date: Must be in ISO 8601 format (YYYY-MM-DD)
    - disruption_event: Cannot be empty

DisruptionPayload:
    - user_prompt: Must be at least 10 characters
    - phase: Must be "initial" or "revision"
    - other_recommendations: Required in revision phase, forbidden in initial phase

AgentResponse:
    - agent_name: Must be one of the 7 known agents or "arbitrator"
    - confidence: Must be between 0.0 and 1.0
    - binding_constraints: Only safety agents can provide these
    - timestamp: Must be valid ISO 8601 format
    - status: Must be "success", "timeout", or "error"
    - duration_seconds: Must be non-negative

Collation:
    - responses: Cannot be empty, keys must match agent_name in values
    - timestamp: Must be valid ISO 8601 format
    - duration_seconds: Must be non-negative

See Also
--------
- Design Document: .kiro/specs/skymarshal-multi-round-orchestration/design.md
- Requirements: .kiro/specs/skymarshal-multi-round-orchestration/requirements.md
- LangChain Structured Output: https://docs.langchain.com/oss/python/langchain/structured-output
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
import re
from datetime import datetime

# ============================================================================
# Legacy Agent Output Schemas (Pre-Multi-Round Orchestration)
# ============================================================================
# 
# These schemas are maintained for backward compatibility with the original
# two-phase execution model (safety → business). They define structured outputs
# for each specialized agent.
#
# Note: The multi-round orchestration flow uses the AgentResponse schema instead,
# which provides a standardized format across all agents. These legacy schemas
# may be deprecated in future versions.
# ============================================================================


class CrewMember(BaseModel):
    """Crew member details"""

    crew_id: str
    crew_name: str
    duty_hours_used: float
    fdp_remaining: float
    fdp_margin_percentage: float
    location: str
    roster_status: str
    qualifications_valid: bool


class Violation(BaseModel):
    """Compliance violation details"""

    violation_id: str
    type: str
    severity: str  # "blocking" or "warning"
    affected_crew: List[str]
    description: str
    actual_value: str
    limit_value: str
    deficit: str
    regulation: str
    mitigation: Optional[str] = None


class AlternativeCrew(BaseModel):
    """Alternative crew member suggestion"""

    crew_id: str
    crew_name: str
    position: str
    tier: int
    base_airport: str
    availability: str
    margins: Dict[str, Any]
    qualifications_match: bool
    positioning_required: bool


class CrewComplianceOutput(BaseModel):
    """Structured output for Crew Compliance Agent"""

    agent: str = Field(default="crew_compliance")
    assessment: str = Field(description="APPROVED|REQUIRES_CREW_CHANGE|CANNOT_PROCEED")
    flight_id: str
    regulatory_framework: str
    timestamp: str
    crew_roster: Dict[str, Any]
    violations: List[Violation]
    alternative_crew: Optional[Dict[str, Any]] = None
    recommendations: List[str]
    latest_departure_time: Optional[str] = None
    reasoning: str
    data_source: str = Field(
        default="database_tools", description="Indicates data was retrieved from tools"
    )


class MaintenanceOutput(BaseModel):
    """Structured output for Maintenance Agent"""

    agent: str = Field(default="maintenance")
    assessment: str = Field(description="APPROVED|REQUIRES_MAINTENANCE|CANNOT_PROCEED")
    aircraft_id: str
    mel_status: str
    maintenance_constraints: List[Dict[str, Any]]
    recommendations: List[str]
    reasoning: str
    data_source: str = Field(default="database_tools")


class RegulatoryOutput(BaseModel):
    """Structured output for Regulatory Agent"""

    agent: str = Field(default="regulatory")
    assessment: str = Field(description="APPROVED|REQUIRES_WAIVER|CANNOT_PROCEED")
    regulatory_constraints: List[Dict[str, Any]]
    curfew_status: str
    slot_status: str
    recommendations: List[str]
    reasoning: str
    data_source: str = Field(default="database_tools")


class NetworkOutput(BaseModel):
    """Structured output for Network Agent"""

    agent: str = Field(default="network")
    propagation_impact: Dict[str, Any]
    connection_impact: Dict[str, Any]
    recovery_options: List[Dict[str, Any]]
    network_risk_score: float
    recommendations: List[str]
    reasoning: str
    data_source: str = Field(default="database_tools")


class GuestExperienceOutput(BaseModel):
    """Structured output for Guest Experience Agent"""

    agent: str = Field(default="guest_experience")
    passenger_impact: Dict[str, Any]
    compensation_estimate: Dict[str, Any]
    reprotection_options: List[Dict[str, Any]]
    customer_satisfaction_risk: str
    recommendations: List[str]
    reasoning: str
    data_source: str = Field(default="database_tools")


class CargoOutput(BaseModel):
    """Structured output for Cargo Agent"""

    agent: str = Field(default="cargo")
    cargo_manifest_summary: Dict[str, Any]
    cold_chain_monitoring: Dict[str, Any]
    perishable_assessment: Dict[str, Any]
    cargo_risk_score: float
    financial_exposure: Dict[str, Any]
    recommendations: List[str]
    reasoning: str
    data_source: str = Field(default="database_tools")


class FinanceOutput(BaseModel):
    """Structured output for Finance Agent"""

    agent: str = Field(default="finance")
    cost_analysis: Dict[str, Any]
    revenue_impact: Dict[str, Any]
    scenario_comparison: List[Dict[str, Any]]
    recommended_scenario: str
    net_financial_impact: float
    recommendations: List[str]
    reasoning: str
    data_source: str = Field(default="database_tools")


class OrchestratorValidation(BaseModel):
    """Validation result from orchestrator"""

    is_valid: bool
    missing_fields: List[str] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    required_fields: List[str] = Field(default_factory=list)


class OrchestratorOutput(BaseModel):
    """Structured output for Orchestrator"""

    status: str
    validation: OrchestratorValidation
    safety_assessments: List[Dict[str, Any]]
    business_assessments: List[Dict[str, Any]]
    aggregated_recommendations: List[str]
    timestamp: str
    total_duration_seconds: float


# ============================================================================
# Multi-Round Orchestration Schemas
# ============================================================================
#
# These schemas support the three-phase multi-round orchestration flow:
#
# 1. FlightInfo: Structured data extracted from natural language prompts
#    - Used with LangChain's with_structured_output() method
#    - Agents autonomously extract flight_number, date, and disruption_event
#    - Validates flight number format and date format
#
# 2. DisruptionPayload: Input payload for agent invocation
#    - Contains raw user_prompt (natural language)
#    - Specifies execution phase (initial or revision)
#    - Includes other_recommendations in revision phase
#
# 3. AgentResponse: Standardized output from all agents
#    - Replaces legacy agent-specific output schemas
#    - Includes recommendation, confidence, reasoning
#    - Safety agents can provide binding_constraints
#    - Tracks execution status, duration, and errors
#
# 4. Collation: Aggregated responses from a phase
#    - Collects all agent responses after phase execution
#    - Provides helper methods for filtering by status
#    - Tracks total phase duration
#
# Design Rationale:
# -----------------
# - Natural Language Input: Orchestrator passes raw prompts to agents without
#   parsing or extraction. Agents are responsible for understanding prompts.
#
# - Autonomous Extraction: Agents use LangChain structured output to extract
#   FlightInfo from prompts. No custom parsing functions needed.
#
# - Standardized Responses: All agents return AgentResponse format for
#   consistent collation and arbitration.
#
# - Phase-Aware Payloads: DisruptionPayload validates that revision phase
#   includes other_recommendations and initial phase does not.
#
# - Type Safety: Pydantic validation ensures data integrity throughout the
#   orchestration flow.
#
# Usage Pattern:
# --------------
# 1. Orchestrator creates DisruptionPayload with user_prompt
# 2. Agent receives payload and extracts FlightInfo using structured output
# 3. Agent queries DynamoDB using extracted flight info
# 4. Agent returns AgentResponse with recommendation
# 5. Orchestrator collates responses into Collation
# 6. Process repeats for revision phase with other_recommendations
# 7. Arbitrator receives final Collation and makes decision
#
# ============================================================================


class FlightInfo(BaseModel):
    """
    Flight information extracted from natural language prompts.
    
    This model is used with LangChain's with_structured_output() to extract
    structured flight data from user prompts like:
    - "Flight EY123 on January 20th had a mechanical failure"
    - "EY456 yesterday was delayed due to weather"
    
    The LLM automatically converts natural language dates to ISO format and
    extracts the flight number and disruption description.
    
    Attributes:
        flight_number: Flight number in format EY followed by 3-4 digits
        date: Flight date in ISO 8601 format (YYYY-MM-DD)
        disruption_event: Description of the disruption
    
    Validation:
        - flight_number: Must match pattern ^EY\d{3,4}$ (case-insensitive)
        - date: Must be valid ISO 8601 format
        - disruption_event: Cannot be empty
    
    Example:
        >>> from langchain_aws import ChatBedrock
        >>> llm = ChatBedrock(model_id="anthropic.claude-sonnet-4-20250514-v1:0")
        >>> structured_llm = llm.with_structured_output(FlightInfo)
        >>> 
        >>> # Natural language prompt
        >>> prompt = "Flight EY123 on January 20th had a mechanical failure"
        >>> 
        >>> # LLM extracts structured data
        >>> flight_info = structured_llm.invoke(prompt)
        >>> print(flight_info)
        FlightInfo(
            flight_number='EY123',
            date='2026-01-20',
            disruption_event='mechanical failure'
        )
        >>> 
        >>> # Access extracted fields
        >>> print(flight_info.flight_number)  # 'EY123'
        >>> print(flight_info.date)           # '2026-01-20'
    
    See Also:
        - DisruptionPayload: Contains the raw user_prompt
        - AgentResponse.extracted_flight_info: Stores the extracted FlightInfo
        - LangChain Structured Output: https://docs.langchain.com/oss/python/langchain/structured-output
    """

    flight_number: str = Field(
        description=(
            "Flight number in format EY followed by 3 or 4 digits (e.g., EY123, EY1234). "
            "Extract the flight number from the user's natural language prompt."
        )
    )
    date: str = Field(
        description=(
            "Flight date in ISO 8601 format (YYYY-MM-DD). "
            "Convert any date format from the prompt to ISO format. "
            "Supported input formats include: "
            "- Numeric: dd/mm/yyyy, dd-mm-yy, yyyy-mm-dd, mm/dd/yyyy "
            "- Named: 20 Jan, 20th January, January 20th 2026 "
            "- Relative: yesterday, today, tomorrow "
            "Assume European date format (dd/mm/yyyy) when ambiguous."
        )
    )
    disruption_event: str = Field(
        description=(
            "Description of the disruption event affecting the flight. "
            "Extract the disruption details from the user's prompt. "
            "Examples: delay, mechanical failure, rerouted plane, weather diversion, "
            "crew shortage, maintenance issue, etc."
        )
    )

    @field_validator("flight_number")
    @classmethod
    def validate_flight_number(cls, v: str) -> str:
        """
        Validate flight number format: EY followed by 3 or 4 digits.
        
        Args:
            v: Flight number string
            
        Returns:
            Validated flight number in uppercase
            
        Raises:
            ValueError: If flight number format is invalid
        """
        # Convert to uppercase for consistency
        v = v.upper().strip()
        
        # Check format: EY followed by 3 or 4 digits
        pattern = r"^EY\d{3,4}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid flight number format: {v}. "
                "Expected format: EY followed by 3 or 4 digits (e.g., EY123, EY1234)"
            )
        
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        """
        Validate date is in ISO 8601 format (YYYY-MM-DD).
        
        Args:
            v: Date string
            
        Returns:
            Validated date in ISO format
            
        Raises:
            ValueError: If date format is invalid
        """
        # Check if already in ISO format
        try:
            datetime.fromisoformat(v)
            return v
        except ValueError:
            raise ValueError(
                f"Invalid date format: {v}. "
                "Expected ISO 8601 format (YYYY-MM-DD). "
                "The LLM should convert natural language dates to ISO format."
            )

    @field_validator("disruption_event")
    @classmethod
    def validate_disruption_event(cls, v: str) -> str:
        """
        Validate disruption event is not empty.
        
        Args:
            v: Disruption event description
            
        Returns:
            Validated disruption event
            
        Raises:
            ValueError: If disruption event is empty
        """
        v = v.strip()
        if not v:
            raise ValueError(
                "Disruption event description cannot be empty. "
                "Please provide details about the disruption."
            )
        
        return v


class DisruptionPayload(BaseModel):
    """
    Payload for agent invocation in multi-round orchestration.
    
    This schema defines the input that agents receive from the orchestrator
    in both initial and revision phases. The orchestrator passes the raw
    user prompt without any parsing or extraction.
    
    Attributes:
        user_prompt: Natural language prompt from user (unmodified)
        phase: Execution phase - "initial" or "revision"
        other_recommendations: Other agents' recommendations (revision only)
    
    Phase Behavior:
        Initial Phase:
            - user_prompt: Contains raw disruption description
            - phase: "initial"
            - other_recommendations: Must be None
            - Agents generate independent recommendations
        
        Revision Phase:
            - user_prompt: Same raw disruption description
            - phase: "revision"
            - other_recommendations: Dict of initial recommendations
            - Agents review others' findings and revise their own
    
    Validation:
        - user_prompt: Must be at least 10 characters
        - phase: Must be "initial" or "revision"
        - other_recommendations: Required in revision, forbidden in initial
    
    Example (Initial Phase):
        >>> payload = DisruptionPayload(
        ...     user_prompt="Flight EY123 on Jan 20th had mechanical failure",
        ...     phase="initial"
        ... )
        >>> print(payload.phase)
        'initial'
        >>> print(payload.other_recommendations)
        None
    
    Example (Revision Phase):
        >>> initial_collation = {
        ...     "crew_compliance": {"recommendation": "Approve with crew change"},
        ...     "maintenance": {"recommendation": "Requires inspection"}
        ... }
        >>> payload = DisruptionPayload(
        ...     user_prompt="Flight EY123 on Jan 20th had mechanical failure",
        ...     phase="revision",
        ...     other_recommendations=initial_collation
        ... )
        >>> print(payload.phase)
        'revision'
        >>> print(len(payload.other_recommendations))
        2
    
    Design Rationale:
        The orchestrator does NOT parse or extract information from the
        user_prompt. It passes the raw prompt to agents, who are responsible
        for extraction using LangChain structured output. This keeps the
        orchestrator simple and allows agents to autonomously understand
        natural language.
    
    See Also:
        - FlightInfo: Schema for extracted flight information
        - AgentResponse: Schema for agent output
        - Collation: Schema for aggregated responses
    """

    user_prompt: str = Field(description="Natural language prompt from user")
    phase: Literal["initial", "revision"] = Field(
        description="Execution phase: initial or revision"
    )
    other_recommendations: Optional[Dict[str, Any]] = Field(
        default=None, description="Other agents' recommendations (revision phase only)"
    )

    @field_validator("user_prompt")
    @classmethod
    def validate_user_prompt(cls, v: str) -> str:
        """
        Validate user prompt is not empty.
        
        Args:
            v: User prompt string
            
        Returns:
            Validated user prompt
            
        Raises:
            ValueError: If user prompt is empty
        """
        v = v.strip()
        if not v:
            raise ValueError(
                "User prompt cannot be empty. "
                "Please provide a natural language description of the disruption."
            )
        
        # Check minimum length for meaningful prompt
        if len(v) < 10:
            raise ValueError(
                f"User prompt too short ({len(v)} characters). "
                "Please provide more details about the flight and disruption."
            )
        
        return v

    @field_validator("other_recommendations")
    @classmethod
    def validate_other_recommendations(cls, v: Optional[Dict[str, Any]], info) -> Optional[Dict[str, Any]]:
        """
        Validate other_recommendations is provided in revision phase.
        
        Args:
            v: Other recommendations dict
            info: Validation context with field values
            
        Returns:
            Validated other recommendations
            
        Raises:
            ValueError: If other_recommendations is missing in revision phase
        """
        # Get phase from validation context
        phase = info.data.get("phase")
        
        if phase == "revision" and v is None:
            raise ValueError(
                "other_recommendations is required in revision phase. "
                "Agents need to review other agents' recommendations during revision."
            )
        
        if phase == "initial" and v is not None:
            raise ValueError(
                "other_recommendations should not be provided in initial phase. "
                "Agents generate independent recommendations in the initial phase."
            )
        
        return v


class AgentResponse(BaseModel):
    """
    Standardized response format for all agents in multi-round orchestration.
    
    This schema replaces the legacy agent-specific output schemas and provides
    a consistent format for all agent responses. It supports both successful
    executions and error cases (timeout, error).
    
    Attributes:
        agent_name: Name of the agent (e.g., "crew_compliance", "maintenance")
        recommendation: Agent's recommendation text
        confidence: Confidence score from 0.0 to 1.0
        binding_constraints: Non-negotiable constraints (safety agents only)
        reasoning: Explanation of the recommendation
        data_sources: List of data sources used (e.g., ["CrewRoster", "Flights"])
        extracted_flight_info: Flight info extracted from prompt (optional)
        timestamp: ISO 8601 timestamp of response generation
        status: Execution status - "success", "timeout", or "error"
        duration_seconds: Execution duration in seconds (optional)
        error: Error message if status is "error" (optional)
    
    Agent Types:
        Safety Agents (can provide binding_constraints):
            - crew_compliance: Crew duty limits and qualifications
            - maintenance: Aircraft airworthiness and MEL compliance
            - regulatory: Curfews, slots, and regulatory requirements
        
        Business Agents (no binding_constraints):
            - network: Flight propagation and connections
            - guest_experience: Passenger impact and reprotection
            - cargo: Cargo handling and cold chain
            - finance: Cost analysis and revenue impact
    
    Validation:
        - agent_name: Must be one of 7 agents or "arbitrator"
        - confidence: Must be between 0.0 and 1.0
        - binding_constraints: Only safety agents can provide these
        - recommendation: Cannot be empty
        - reasoning: Cannot be empty
        - timestamp: Must be valid ISO 8601 format
        - status: Must be "success", "timeout", or "error"
        - duration_seconds: Must be non-negative if provided
    
    Example (Successful Response):
        >>> from datetime import datetime, timezone
        >>> response = AgentResponse(
        ...     agent_name="crew_compliance",
        ...     recommendation="Approve delay with crew change required",
        ...     confidence=0.95,
        ...     binding_constraints=[
        ...         "Crew must have minimum 10 hours rest",
        ...         "Replacement crew must be qualified on A380"
        ...     ],
        ...     reasoning="Current crew exceeds FDP limits by 2 hours",
        ...     data_sources=["CrewRoster", "CrewMembers", "Flights"],
        ...     extracted_flight_info={
        ...         "flight_number": "EY123",
        ...         "date": "2026-01-20",
        ...         "disruption_event": "mechanical failure"
        ...     },
        ...     timestamp=datetime.now(timezone.utc).isoformat(),
        ...     status="success",
        ...     duration_seconds=3.2
        ... )
    
    Example (Timeout Response):
        >>> response = AgentResponse(
        ...     agent_name="maintenance",
        ...     recommendation="Unable to complete analysis",
        ...     confidence=0.0,
        ...     reasoning="Agent execution timed out after 30 seconds",
        ...     data_sources=[],
        ...     timestamp=datetime.now(timezone.utc).isoformat(),
        ...     status="timeout",
        ...     duration_seconds=30.0,
        ...     error="Execution exceeded 30 second timeout"
        ... )
    
    Example (Error Response):
        >>> response = AgentResponse(
        ...     agent_name="network",
        ...     recommendation="Unable to complete analysis",
        ...     confidence=0.0,
        ...     reasoning="Failed to query flight data",
        ...     data_sources=[],
        ...     timestamp=datetime.now(timezone.utc).isoformat(),
        ...     status="error",
        ...     duration_seconds=1.5,
        ...     error="DynamoDB query failed: Flight not found"
        ... )
    
    Design Rationale:
        - Standardized format enables consistent collation and arbitration
        - Status field supports graceful degradation when agents fail
        - Binding constraints enforce safety-first decision making
        - Extracted flight info provides audit trail of what agent understood
        - Duration tracking enables performance monitoring
    
    See Also:
        - DisruptionPayload: Input schema for agents
        - Collation: Aggregates multiple AgentResponse objects
        - FlightInfo: Schema for extracted flight information
    """

    agent_name: str = Field(description="Name of the agent")
    recommendation: str = Field(description="Agent's recommendation")
    confidence: float = Field(
        description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0
    )
    binding_constraints: List[str] = Field(
        default_factory=list,
        description="Non-negotiable constraints (safety agents only)",
    )
    reasoning: str = Field(description="Explanation of the recommendation")
    data_sources: List[str] = Field(
        default_factory=list, description="Data sources used for analysis"
    )
    extracted_flight_info: Optional[Dict[str, Any]] = Field(
        default=None, description="Flight information extracted from prompt"
    )
    timestamp: str = Field(description="ISO 8601 timestamp")
    status: Optional[str] = Field(
        default="success", description="Execution status: success, timeout, error"
    )
    duration_seconds: Optional[float] = Field(
        default=None, description="Execution duration in seconds"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        """
        Validate agent name is one of the known agents.
        
        Args:
            v: Agent name string
            
        Returns:
            Validated agent name
            
        Raises:
            ValueError: If agent name is not recognized
        """
        valid_agents = {
            "crew_compliance",
            "maintenance",
            "regulatory",
            "network",
            "guest_experience",
            "cargo",
            "finance",
            "arbitrator"
        }
        
        v = v.strip().lower()
        if v not in valid_agents:
            raise ValueError(
                f"Invalid agent name: {v}. "
                f"Must be one of: {', '.join(sorted(valid_agents))}"
            )
        
        return v

    @field_validator("recommendation")
    @classmethod
    def validate_recommendation(cls, v: str) -> str:
        """
        Validate recommendation is not empty.
        
        Args:
            v: Recommendation string
            
        Returns:
            Validated recommendation
            
        Raises:
            ValueError: If recommendation is empty
        """
        v = v.strip()
        if not v:
            raise ValueError(
                "Recommendation cannot be empty. "
                "Agent must provide a clear recommendation."
            )
        
        return v

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        """
        Validate reasoning is not empty.
        
        Args:
            v: Reasoning string
            
        Returns:
            Validated reasoning
            
        Raises:
            ValueError: If reasoning is empty
        """
        v = v.strip()
        if not v:
            raise ValueError(
                "Reasoning cannot be empty. "
                "Agent must explain the rationale for its recommendation."
            )
        
        return v

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """
        Validate timestamp is in ISO 8601 format.
        
        Args:
            v: Timestamp string
            
        Returns:
            Validated timestamp
            
        Raises:
            ValueError: If timestamp format is invalid
        """
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(
                f"Invalid timestamp format: {v}. "
                "Expected ISO 8601 format (e.g., 2026-02-01T12:00:00Z)"
            )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> str:
        """
        Validate status is one of the allowed values.
        
        Args:
            v: Status string
            
        Returns:
            Validated status
            
        Raises:
            ValueError: If status is not recognized
        """
        if v is None:
            return "success"
        
        valid_statuses = {"success", "timeout", "error"}
        v = v.strip().lower()
        
        if v not in valid_statuses:
            raise ValueError(
                f"Invalid status: {v}. "
                f"Must be one of: {', '.join(sorted(valid_statuses))}"
            )
        
        return v

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: Optional[float]) -> Optional[float]:
        """
        Validate duration is non-negative.
        
        Args:
            v: Duration in seconds
            
        Returns:
            Validated duration
            
        Raises:
            ValueError: If duration is negative
        """
        if v is not None and v < 0:
            raise ValueError(
                f"Duration cannot be negative: {v}. "
                "Duration must be >= 0 seconds."
            )
        
        return v

    @field_validator("binding_constraints")
    @classmethod
    def validate_binding_constraints(cls, v: List[str], info) -> List[str]:
        """
        Validate binding constraints are only provided by safety agents.
        
        Args:
            v: List of binding constraints
            info: Validation context with field values
            
        Returns:
            Validated binding constraints
            
        Raises:
            ValueError: If business agent provides binding constraints
        """
        agent_name = info.data.get("agent_name", "").lower()
        safety_agents = {"crew_compliance", "maintenance", "regulatory"}
        
        if v and agent_name not in safety_agents:
            raise ValueError(
                f"Only safety agents can provide binding constraints. "
                f"Agent '{agent_name}' is not a safety agent."
            )
        
        return v


class Collation(BaseModel):
    """
    Collated responses from all agents in a phase.
    
    This schema aggregates all agent responses after a phase execution
    (initial or revision). It provides helper methods for filtering
    responses by status and analyzing agent performance.
    
    Attributes:
        phase: Execution phase - "initial" or "revision"
        responses: Dict mapping agent_name to AgentResponse
        timestamp: ISO 8601 timestamp of collation
        duration_seconds: Total phase execution duration
    
    Validation:
        - responses: Cannot be empty, keys must match agent_name in values
        - timestamp: Must be valid ISO 8601 format
        - duration_seconds: Must be non-negative
    
    Helper Methods:
        - get_successful_responses(): Returns only successful agent responses
        - get_failed_responses(): Returns only timeout/error responses
        - get_agent_count(): Returns count of agents by status
    
    Example (Initial Phase Collation):
        >>> from datetime import datetime, timezone
        >>> collation = Collation(
        ...     phase="initial",
        ...     responses={
        ...         "crew_compliance": crew_response,
        ...         "maintenance": maintenance_response,
        ...         "regulatory": regulatory_response,
        ...         "network": network_response,
        ...         "guest_experience": guest_response,
        ...         "cargo": cargo_response,
        ...         "finance": finance_response
        ...     },
        ...     timestamp=datetime.now(timezone.utc).isoformat(),
        ...     duration_seconds=8.5
        ... )
        >>> 
        >>> # Get only successful responses
        >>> successful = collation.get_successful_responses()
        >>> print(len(successful))
        6
        >>> 
        >>> # Get failed responses
        >>> failed = collation.get_failed_responses()
        >>> print(len(failed))
        1
        >>> 
        >>> # Get agent counts by status
        >>> counts = collation.get_agent_count()
        >>> print(counts)
        {'success': 6, 'timeout': 1, 'error': 0}
    
    Example (Revision Phase Collation):
        >>> collation = Collation(
        ...     phase="revision",
        ...     responses={
        ...         "crew_compliance": revised_crew_response,
        ...         "maintenance": revised_maintenance_response,
        ...         # ... other revised responses
        ...     },
        ...     timestamp=datetime.now(timezone.utc).isoformat(),
        ...     duration_seconds=7.2
        ... )
        >>> 
        >>> # Check if all agents succeeded
        >>> all_success = len(collation.get_failed_responses()) == 0
        >>> print(all_success)
        True
    
    Usage in Orchestrator:
        Phase 1 (Initial):
            1. Orchestrator invokes all agents in parallel
            2. Collects responses as they complete
            3. Creates Collation with all responses
            4. Passes collation to Phase 2
        
        Phase 2 (Revision):
            1. Orchestrator includes Phase 1 collation in payload
            2. Agents review other_recommendations
            3. Agents revise their recommendations
            4. Orchestrator creates new Collation with revised responses
            5. Passes collation to Phase 3 (Arbitration)
    
    Design Rationale:
        - Dict structure allows O(1) lookup by agent name
        - Helper methods simplify filtering and analysis
        - Status tracking enables graceful degradation
        - Duration tracking enables performance monitoring
        - Phase field maintains audit trail
    
    See Also:
        - AgentResponse: Individual agent response schema
        - DisruptionPayload: Input schema that includes collation in revision
    """

    phase: Literal["initial", "revision"] = Field(
        description="Execution phase: initial or revision"
    )
    responses: Dict[str, AgentResponse] = Field(
        description="Agent responses keyed by agent name"
    )
    timestamp: str = Field(description="ISO 8601 timestamp")
    duration_seconds: float = Field(
        description="Total phase execution duration in seconds"
    )

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """
        Validate timestamp is in ISO 8601 format.
        
        Args:
            v: Timestamp string
            
        Returns:
            Validated timestamp
            
        Raises:
            ValueError: If timestamp format is invalid
        """
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(
                f"Invalid timestamp format: {v}. "
                "Expected ISO 8601 format (e.g., 2026-02-01T12:00:00Z)"
            )

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration(cls, v: float) -> float:
        """
        Validate duration is non-negative.
        
        Args:
            v: Duration in seconds
            
        Returns:
            Validated duration
            
        Raises:
            ValueError: If duration is negative
        """
        if v < 0:
            raise ValueError(
                f"Duration cannot be negative: {v}. "
                "Duration must be >= 0 seconds."
            )
        
        return v

    @field_validator("responses")
    @classmethod
    def validate_responses(cls, v: Dict[str, AgentResponse]) -> Dict[str, AgentResponse]:
        """
        Validate responses dict is not empty and keys match agent names.
        
        Args:
            v: Responses dict
            
        Returns:
            Validated responses
            
        Raises:
            ValueError: If responses is empty or keys don't match agent names
        """
        if not v:
            raise ValueError(
                "Responses cannot be empty. "
                "At least one agent must provide a response."
            )
        
        # Validate that dict keys match agent_name in responses
        for key, response in v.items():
            if key != response.agent_name:
                raise ValueError(
                    f"Response key '{key}' does not match agent_name '{response.agent_name}'. "
                    "Dict keys must match the agent_name field in each response."
                )
        
        return v

    def get_successful_responses(self) -> Dict[str, AgentResponse]:
        """Get only successful agent responses"""
        return {
            name: response
            for name, response in self.responses.items()
            if response.status == "success"
        }

    def get_failed_responses(self) -> Dict[str, AgentResponse]:
        """Get only failed agent responses (timeout or error)"""
        return {
            name: response
            for name, response in self.responses.items()
            if response.status in ["timeout", "error"]
        }

    def get_agent_count(self) -> Dict[str, int]:
        """Get count of agents by status"""
        counts = {"success": 0, "timeout": 0, "error": 0}
        for response in self.responses.values():
            status = response.status or "success"
            counts[status] = counts.get(status, 0) + 1
        return counts
