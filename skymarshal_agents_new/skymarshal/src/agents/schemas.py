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


# ============================================================================
# Arbitrator Schemas
# ============================================================================
#
# These schemas define the input and output for the arbitrator agent in
# Phase 3 of the multi-round orchestration flow. The arbitrator receives
# all revised agent recommendations and makes the final decision by:
#
# 1. Identifying conflicts between agent recommendations
# 2. Extracting binding constraints from safety agents
# 3. Applying safety-first decision rules
# 4. Generating final decision with justification
# 5. Providing complete audit trail
#
# Decision Rules:
# ---------------
# 1. Safety vs Business: Always choose safety constraint
# 2. Safety vs Safety: Choose most conservative option
# 3. Business vs Business: Balance operational impact
#
# Usage Pattern:
# --------------
# 1. Orchestrator creates ArbitratorInput with revised recommendations
# 2. Arbitrator analyzes conflicts and applies decision rules
# 3. Arbitrator returns ArbitratorOutput with final decision
# 4. System returns final decision to user
#
# ============================================================================


class ConflictDetail(BaseModel):
    """
    Details of a conflict between agent recommendations.
    
    This schema captures information about conflicts identified by the
    arbitrator during Phase 3. Conflicts occur when agents provide
    contradictory or incompatible recommendations.
    
    Attributes:
        agents_involved: Names of agents involved in the conflict
        conflict_type: Type of conflict (safety_vs_business, safety_vs_safety, business_vs_business)
        description: Human-readable description of the conflict
    
    Conflict Types:
        safety_vs_business:
            - Safety agent's binding constraint conflicts with business recommendation
            - Example: Crew requires 10-hour rest vs Network wants 2-hour delay
            - Resolution: Always choose safety constraint
        
        safety_vs_safety:
            - Multiple safety agents have conflicting requirements
            - Example: Crew can operate with 8-hour rest vs Maintenance requires 12-hour inspection
            - Resolution: Choose most conservative option
        
        business_vs_business:
            - Business agents have conflicting recommendations
            - Example: Network wants cancellation vs Guest Experience wants delay
            - Resolution: Balance operational impact
    
    Example:
        >>> conflict = ConflictDetail(
        ...     agents_involved=["crew_compliance", "network"],
        ...     conflict_type="safety_vs_business",
        ...     description=(
        ...         "Crew Compliance requires 10-hour rest period, but Network "
        ...         "recommends 2-hour delay to minimize propagation impact"
        ...     )
        ... )
    
    See Also:
        - ResolutionDetail: How the conflict was resolved
        - SafetyOverride: Safety constraints that overrode business recommendations
        - ArbitratorOutput: Contains list of ConflictDetail objects
    """
    
    agents_involved: List[str] = Field(
        description="Names of agents involved in the conflict"
    )
    conflict_type: Literal["safety_vs_business", "safety_vs_safety", "business_vs_business"] = Field(
        description="Type of conflict: safety_vs_business, safety_vs_safety, or business_vs_business"
    )
    description: str = Field(
        description="Human-readable description of the conflict"
    )
    
    @field_validator("agents_involved")
    @classmethod
    def validate_agents_involved(cls, v: List[str]) -> List[str]:
        """
        Validate at least 2 agents are involved in a conflict.
        
        Args:
            v: List of agent names
            
        Returns:
            Validated list of agent names
            
        Raises:
            ValueError: If fewer than 2 agents are involved
        """
        if len(v) < 2:
            raise ValueError(
                f"A conflict must involve at least 2 agents, got {len(v)}. "
                "Conflicts occur between agent recommendations."
            )
        
        return v
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """
        Validate description is not empty.
        
        Args:
            v: Description string
            
        Returns:
            Validated description
            
        Raises:
            ValueError: If description is empty
        """
        v = v.strip()
        if not v:
            raise ValueError(
                "Conflict description cannot be empty. "
                "Provide a clear explanation of the conflict."
            )
        
        return v


class ResolutionDetail(BaseModel):
    """
    Details of how a conflict was resolved by the arbitrator.
    
    This schema captures the arbitrator's decision-making process for
    each conflict. It explains what conflict was resolved, how it was
    resolved, and the rationale behind the resolution.
    
    Attributes:
        conflict_description: Description of the conflict that was resolved
        resolution: How the conflict was resolved
        rationale: Reasoning behind the resolution
    
    Example (Safety vs Business):
        >>> resolution = ResolutionDetail(
        ...     conflict_description=(
        ...         "Crew Compliance requires 10-hour rest vs Network wants 2-hour delay"
        ...     ),
        ...     resolution="Enforce 10-hour crew rest requirement",
        ...     rationale=(
        ...         "Safety constraint takes priority over business optimization. "
        ...         "Crew duty limits are non-negotiable regulatory requirements."
        ...     )
        ... )
    
    Example (Safety vs Safety):
        >>> resolution = ResolutionDetail(
        ...     conflict_description=(
        ...         "Crew can operate with 8-hour rest vs Maintenance requires 12-hour inspection"
        ...     ),
        ...     resolution="Enforce 12-hour maintenance inspection",
        ...     rationale=(
        ...         "Choose most conservative option when safety agents conflict. "
        ...         "12-hour inspection provides higher safety margin."
        ...     )
        ... )
    
    Example (Business vs Business):
        >>> resolution = ResolutionDetail(
        ...     conflict_description=(
        ...         "Network recommends cancellation vs Guest Experience recommends delay"
        ...     ),
        ...     resolution="Delay flight by 4 hours with passenger reprotection",
        ...     rationale=(
        ...         "Balance operational impact: delay affects 150 passengers but "
        ...         "cancellation would affect 3 downstream flights (450 passengers total)"
        ...     )
        ... )
    
    See Also:
        - ConflictDetail: Details of the conflict
        - ArbitratorOutput: Contains list of ResolutionDetail objects
    """
    
    conflict_description: str = Field(
        description="Description of the conflict that was resolved"
    )
    resolution: str = Field(
        description="How the conflict was resolved"
    )
    rationale: str = Field(
        description="Reasoning behind the resolution"
    )
    
    @field_validator("conflict_description", "resolution", "rationale")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """
        Validate field is not empty.
        
        Args:
            v: Field value
            
        Returns:
            Validated field value
            
        Raises:
            ValueError: If field is empty
        """
        v = v.strip()
        if not v:
            raise ValueError(
                "Resolution detail fields cannot be empty. "
                "Provide complete information about conflict resolution."
            )
        
        return v


class SafetyOverride(BaseModel):
    """
    Details of a safety constraint overriding business recommendations.
    
    This schema captures cases where a safety agent's binding constraint
    takes priority over business agent recommendations. Safety overrides
    are a critical part of the audit trail and demonstrate safety-first
    decision making.
    
    Attributes:
        safety_agent: Name of the safety agent providing the constraint
        binding_constraint: The binding constraint that was enforced
        overridden_recommendations: Business recommendations that were overridden
    
    Safety Agents:
        - crew_compliance: Crew duty limits, rest requirements, qualifications
        - maintenance: Aircraft airworthiness, MEL compliance
        - regulatory: Curfews, slots, regulatory requirements
    
    Example:
        >>> override = SafetyOverride(
        ...     safety_agent="crew_compliance",
        ...     binding_constraint="Crew must have minimum 10 hours rest before next duty",
        ...     overridden_recommendations=[
        ...         "Network: Delay flight by only 2 hours to minimize propagation",
        ...         "Finance: Minimize delay costs by reducing rest period"
        ...     ]
        ... )
    
    Design Rationale:
        Safety overrides are explicitly tracked to:
        - Demonstrate compliance with safety-first principles
        - Provide audit trail for regulatory review
        - Explain why business-optimal solutions were not chosen
        - Document non-negotiable safety constraints
    
    See Also:
        - ConflictDetail: Details of the conflict
        - ResolutionDetail: How the conflict was resolved
        - ArbitratorOutput: Contains list of SafetyOverride objects
    """
    
    safety_agent: str = Field(
        description="Name of the safety agent providing the constraint"
    )
    binding_constraint: str = Field(
        description="The binding constraint that was enforced"
    )
    overridden_recommendations: List[str] = Field(
        description="Business recommendations that were overridden"
    )
    
    @field_validator("safety_agent")
    @classmethod
    def validate_safety_agent(cls, v: str) -> str:
        """
        Validate safety agent is one of the known safety agents.
        
        Args:
            v: Safety agent name
            
        Returns:
            Validated safety agent name
            
        Raises:
            ValueError: If not a safety agent
        """
        safety_agents = {"crew_compliance", "maintenance", "regulatory"}
        v = v.strip().lower()
        
        if v not in safety_agents:
            raise ValueError(
                f"Invalid safety agent: {v}. "
                f"Must be one of: {', '.join(sorted(safety_agents))}"
            )
        
        return v
    
    @field_validator("binding_constraint")
    @classmethod
    def validate_binding_constraint(cls, v: str) -> str:
        """
        Validate binding constraint is not empty.
        
        Args:
            v: Binding constraint string
            
        Returns:
            Validated binding constraint
            
        Raises:
            ValueError: If binding constraint is empty
        """
        v = v.strip()
        if not v:
            raise ValueError(
                "Binding constraint cannot be empty. "
                "Provide the specific safety requirement that was enforced."
            )
        
        return v
    
    @field_validator("overridden_recommendations")
    @classmethod
    def validate_overridden_recommendations(cls, v: List[str]) -> List[str]:
        """
        Validate at least one recommendation was overridden.
        
        Args:
            v: List of overridden recommendations
            
        Returns:
            Validated list of overridden recommendations
            
        Raises:
            ValueError: If no recommendations were overridden
        """
        if not v:
            raise ValueError(
                "At least one recommendation must be overridden. "
                "Safety overrides occur when safety constraints conflict with business recommendations."
            )
        
        return v


class ArbitratorInput(BaseModel):
    """
    Input schema for the arbitrator agent in Phase 3.
    
    This schema defines the input that the arbitrator receives from the
    orchestrator after Phase 2 (revision round) completes. It contains
    all revised agent recommendations and the original user prompt for
    context.
    
    Attributes:
        revised_recommendations: Dict of all agent responses after revision
        user_prompt: Original natural language prompt from user (for context)
    
    Usage Pattern:
        1. Orchestrator completes Phase 2 (revision round)
        2. Orchestrator creates ArbitratorInput with revised recommendations
        3. Orchestrator invokes arbitrator with input
        4. Arbitrator analyzes conflicts and makes final decision
        5. Arbitrator returns ArbitratorOutput
    
    Example:
        >>> from datetime import datetime, timezone
        >>> arbitrator_input = ArbitratorInput(
        ...     revised_recommendations={
        ...         "crew_compliance": AgentResponse(
        ...             agent_name="crew_compliance",
        ...             recommendation="Cannot proceed - crew exceeds FDP",
        ...             confidence=0.95,
        ...             binding_constraints=["Crew must have 10 hours rest"],
        ...             reasoning="Current crew at 13.5 hours duty time",
        ...             data_sources=["CrewRoster", "CrewMembers"],
        ...             timestamp=datetime.now(timezone.utc).isoformat()
        ...         ),
        ...         "maintenance": AgentResponse(
        ...             agent_name="maintenance",
        ...             recommendation="Approved - aircraft airworthy",
        ...             confidence=0.98,
        ...             reasoning="All systems operational, no MEL items",
        ...             data_sources=["MaintenanceWorkOrders"],
        ...             timestamp=datetime.now(timezone.utc).isoformat()
        ...         ),
        ...         # ... other agents
        ...     },
        ...     user_prompt="Flight EY123 on January 20th had a mechanical failure"
        ... )
    
    Validation:
        - revised_recommendations: Cannot be empty, must contain agent responses
        - user_prompt: Must be at least 10 characters
    
    Design Rationale:
        - Includes user_prompt for context in arbitration
        - Uses dict structure for O(1) agent lookup
        - Accepts either Collation object or dict of AgentResponse objects
        - Provides flexibility in how orchestrator passes data
    
    See Also:
        - AgentResponse: Individual agent response schema
        - Collation: Aggregated responses from Phase 2
        - ArbitratorOutput: Output schema for arbitrator
    """
    
    revised_recommendations: Dict[str, AgentResponse] = Field(
        description="All agent responses after revision round"
    )
    user_prompt: str = Field(
        description="Original natural language prompt from user (for context)"
    )
    
    @field_validator("revised_recommendations")
    @classmethod
    def validate_revised_recommendations(cls, v: Dict[str, AgentResponse]) -> Dict[str, AgentResponse]:
        """
        Validate revised recommendations is not empty.
        
        Args:
            v: Revised recommendations dict
            
        Returns:
            Validated revised recommendations
            
        Raises:
            ValueError: If revised recommendations is empty
        """
        if not v:
            raise ValueError(
                "Revised recommendations cannot be empty. "
                "Arbitrator requires agent responses to make a decision."
            )
        
        return v
    
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
                "Arbitrator needs context from the original disruption description."
            )
        
        if len(v) < 10:
            raise ValueError(
                f"User prompt too short ({len(v)} characters). "
                "Provide the complete original disruption description."
            )
        
        return v


# ============================================================================
# Multi-Solution Enhancement Schemas
# ============================================================================
#
# These schemas extend the arbitrator to provide multiple ranked solution
# options with detailed recovery plans, S3 integration for historical
# learning, and comprehensive decision reports.
#
# Key Components:
# - RecoveryStep: Individual step in recovery workflow
# - RecoveryPlan: Complete recovery workflow with dependencies
# - RecoverySolution: Solution option with scoring and recovery plan
#
# These schemas must be defined BEFORE ArbitratorOutput since ArbitratorOutput
# references RecoverySolution in its solution_options field.
# ============================================================================


class RecoveryStep(BaseModel):
    """
    A single step in the recovery process.
    
    Recovery steps form a directed acyclic graph (DAG) where each step
    can depend on one or more previous steps. Steps are executed in
    dependency order to implement the recovery solution.
    
    Attributes:
        step_number: Sequential step number starting from 1
        step_name: Short descriptive name for the step
        description: Detailed description of what this step accomplishes
        responsible_agent: Agent or system responsible for execution
        dependencies: Step numbers that must complete before this step
        estimated_duration: Estimated time to complete (e.g., '15 minutes', '2 hours')
        automation_possible: Whether this step can be automated
        action_type: Type of action (notify, rebook, schedule, coordinate, etc.)
        parameters: Parameters needed for execution
        success_criteria: How to verify step completed successfully
        rollback_procedure: What to do if this step fails (optional)
    """
    
    step_number: int = Field(description="Sequential step number starting from 1", ge=1)
    step_name: str = Field(description="Short descriptive name for the step")
    description: str = Field(description="Detailed description of what this step accomplishes")
    responsible_agent: str = Field(description="Agent or system responsible for execution")
    dependencies: List[int] = Field(
        default_factory=list,
        description="Step numbers that must complete before this step"
    )
    estimated_duration: str = Field(description="Estimated time to complete (e.g., '15 minutes', '2 hours')")
    automation_possible: bool = Field(description="Whether this step can be automated")
    action_type: str = Field(description="Type of action: notify, rebook, schedule, coordinate, etc.")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters needed for execution"
    )
    success_criteria: str = Field(description="How to verify step completed successfully")
    rollback_procedure: Optional[str] = Field(
        default=None,
        description="What to do if this step fails"
    )
    
    @field_validator("step_name", "description", "responsible_agent", "estimated_duration", "action_type", "success_criteria")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate field is not empty"""
        v = v.strip()
        if not v:
            raise ValueError("Recovery step fields cannot be empty")
        return v


class RecoveryPlan(BaseModel):
    """
    Complete recovery plan for a solution.
    
    A recovery plan defines the complete workflow for implementing a
    solution, including all steps, dependencies, and contingency plans.
    The plan forms a directed acyclic graph (DAG) with no circular
    dependencies.
    
    Attributes:
        solution_id: ID of the solution this plan belongs to
        total_steps: Total number of steps in the plan
        estimated_total_duration: Total estimated duration for all steps
        steps: Ordered list of recovery steps
        critical_path: Step numbers on the critical path (longest dependency chain)
        contingency_plans: Contingency plans for handling failures
    
    Validation:
        - Steps must be sequential 1..N with no gaps
        - No step can depend on itself
        - No circular dependency chains
        - All dependency references must be valid
        - Dependencies must reference earlier steps only
    """
    
    solution_id: int = Field(description="ID of the solution this plan belongs to", ge=1, le=3)
    total_steps: int = Field(description="Total number of steps in the plan", ge=1)
    estimated_total_duration: str = Field(description="Total estimated duration for all steps")
    steps: List[RecoveryStep] = Field(description="Ordered list of recovery steps")
    critical_path: List[int] = Field(
        description="Step numbers on the critical path (longest dependency chain)"
    )
    contingency_plans: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Contingency plans for handling failures"
    )
    
    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: List[RecoveryStep]) -> List[RecoveryStep]:
        """Validate recovery steps for logical consistency"""
        if not v:
            raise ValueError("Recovery plan must have at least one step")
        
        # Check step numbers are sequential
        step_numbers = [step.step_number for step in v]
        expected = list(range(1, len(v) + 1))
        if step_numbers != expected:
            raise ValueError(
                f"Step numbers must be sequential 1..{len(v)}, got {step_numbers}"
            )
        
        # Check for self-dependencies and circular dependencies
        for step in v:
            # No self-dependencies
            if step.step_number in step.dependencies:
                raise ValueError(
                    f"Step {step.step_number} cannot depend on itself"
                )
            
            # Check all dependencies reference valid steps
            for dep in step.dependencies:
                if dep < 1 or dep > len(v):
                    raise ValueError(
                        f"Step {step.step_number} has invalid dependency {dep}. "
                        f"Valid range: 1..{len(v)}"
                    )
                # Dependencies must reference earlier steps
                if dep >= step.step_number:
                    raise ValueError(
                        f"Step {step.step_number} cannot depend on later step {dep}"
                    )
        
        # Check for circular dependencies using topological sort
        graph = {step.step_number: step.dependencies for step in v}
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: int) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step_num in graph:
            if step_num not in visited:
                if has_cycle(step_num):
                    raise ValueError(
                        "Recovery plan contains circular dependencies"
                    )
        
        return v
    
    @field_validator("critical_path")
    @classmethod
    def validate_critical_path(cls, v: List[int], info) -> List[int]:
        """Validate critical path references valid steps"""
        steps = info.data.get("steps", [])
        if not steps:
            return v
        
        valid_step_numbers = {step.step_number for step in steps}
        for step_num in v:
            if step_num not in valid_step_numbers:
                raise ValueError(
                    f"Critical path contains invalid step number {step_num}. "
                    f"Valid steps: {sorted(valid_step_numbers)}"
                )
        
        return v


class RecoverySolution(BaseModel):
    """
    A single recovery solution option.
    
    Each solution represents a distinct approach to handling the disruption,
    with different trade-offs across safety, cost, passenger impact, and
    network impact dimensions. Solutions are scored and ranked to help
    decision makers choose the best option.
    
    Attributes:
        solution_id: Unique ID (1, 2, or 3)
        title: Short descriptive title
        description: Detailed description of the solution
        recommendations: Specific action steps (high-level)
        safety_compliance: How this solution satisfies safety constraints
        passenger_impact: Passenger impact details
        financial_impact: Financial impact details
        network_impact: Network propagation details
        safety_score: Safety score 0-100
        cost_score: Cost score 0-100 (higher = lower cost)
        passenger_score: Passenger score 0-100 (higher = less impact)
        network_score: Network score 0-100 (higher = less propagation)
        composite_score: Weighted average score
        pros: Advantages of this solution
        cons: Disadvantages of this solution
        risks: Potential risks
        confidence: Confidence in this solution 0.0-1.0
        estimated_duration: Time to implement (e.g., '6 hours')
        recovery_plan: Detailed step-by-step recovery plan
    
    Scoring:
        Composite score = (safety * 0.4) + (cost * 0.2) + (passenger * 0.2) + (network * 0.2)
        All scores are in range [0, 100]
    """
    
    solution_id: int = Field(description="Unique ID: 1, 2, or 3", ge=1, le=3)
    title: str = Field(description="Short descriptive title")
    description: str = Field(description="Detailed description of the solution")
    recommendations: List[str] = Field(description="Specific action steps (high-level)")
    
    # Compliance and Impact
    safety_compliance: str = Field(description="How this solution satisfies safety constraints")
    passenger_impact: Dict[str, Any] = Field(description="Passenger impact details")
    financial_impact: Dict[str, Any] = Field(description="Financial impact details")
    network_impact: Dict[str, Any] = Field(description="Network propagation details")
    
    # Multi-Dimensional Scoring
    safety_score: float = Field(description="Safety score 0-100", ge=0.0, le=100.0)
    cost_score: float = Field(description="Cost score 0-100 (higher = lower cost)", ge=0.0, le=100.0)
    passenger_score: float = Field(description="Passenger score 0-100 (higher = less impact)", ge=0.0, le=100.0)
    network_score: float = Field(description="Network score 0-100 (higher = less propagation)", ge=0.0, le=100.0)
    composite_score: float = Field(description="Weighted average score", ge=0.0, le=100.0)
    
    # Trade-off Analysis
    pros: List[str] = Field(description="Advantages of this solution")
    cons: List[str] = Field(description="Disadvantages of this solution")
    risks: List[str] = Field(description="Potential risks")
    
    # Metadata
    confidence: float = Field(description="Confidence in this solution 0.0-1.0", ge=0.0, le=1.0)
    estimated_duration: str = Field(description="Time to implement (e.g., '6 hours')")
    
    # Recovery Plan
    recovery_plan: RecoveryPlan = Field(description="Detailed step-by-step recovery plan")
    
    @field_validator("composite_score")
    @classmethod
    def validate_composite_score(cls, v: float, info) -> float:
        """Validate composite score matches weighted average"""
        # Get individual scores from validation context
        safety = info.data.get("safety_score", 0)
        cost = info.data.get("cost_score", 0)
        passenger = info.data.get("passenger_score", 0)
        network = info.data.get("network_score", 0)
        
        # Calculate expected composite (40% safety, 20% cost, 20% passenger, 20% network)
        expected = (safety * 0.4) + (cost * 0.2) + (passenger * 0.2) + (network * 0.2)
        
        # Allow small floating point tolerance
        if abs(v - expected) > 0.1:
            raise ValueError(
                f"Composite score {v} does not match weighted average {expected:.2f}. "
                "Expected: 40% safety + 20% cost + 20% passenger + 20% network"
            )
        
        return v
    
    @field_validator("title", "description", "safety_compliance", "estimated_duration")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Validate field is not empty"""
        v = v.strip()
        if not v:
            raise ValueError("Solution fields cannot be empty")
        return v
    
    @field_validator("recommendations", "pros", "cons", "risks")
    @classmethod
    def validate_list_not_empty(cls, v: List[str]) -> List[str]:
        """Validate list has at least one item"""
        if not v:
            raise ValueError("Solution lists (recommendations, pros, cons, risks) cannot be empty")
        return v


class ArbitratorOutput(BaseModel):
    """
    Output schema for the arbitrator agent in Phase 3.
    
    This schema defines the final decision output from the arbitrator after
    analyzing all agent recommendations and resolving conflicts. It provides
    a complete audit trail of the decision-making process.
    
    Attributes:
        final_decision: Clear, actionable decision text
        recommendations: List of specific actions to take
        conflicts_identified: All conflicts found between agents
        conflict_resolutions: How each conflict was resolved
        safety_overrides: Safety constraints that overrode business recommendations
        justification: Overall explanation of the decision
        reasoning: Detailed reasoning process
        confidence: Confidence score (0.0 to 1.0)
        timestamp: ISO 8601 timestamp of decision
        model_used: Model ID used for arbitration (e.g., Opus 4.5 or Sonnet 4.5)
        duration_seconds: Arbitration duration in seconds
    
    Confidence Scoring:
        - 0.9-1.0: All agents agree, no conflicts, clear decision
        - 0.7-0.9: Minor conflicts resolved, clear safety constraints
        - 0.5-0.7: Significant conflicts, but safety constraints clear
        - 0.3-0.5: Complex conflicts, uncertain business impacts
        - 0.0-0.3: Major conflicts, missing critical information
    
    Example (Safety vs Business Conflict):
        >>> from datetime import datetime, timezone
        >>> output = ArbitratorOutput(
        ...     final_decision=(
        ...         "Flight must be delayed to allow crew 10-hour rest period. "
        ...         "Alternative crew or flight cancellation required."
        ...     ),
        ...     recommendations=[
        ...         "Delay flight by 10 hours to satisfy crew rest requirement",
        ...         "Source alternative qualified crew if available",
        ...         "If no crew available, cancel flight and rebook passengers",
        ...         "Notify passengers of delay/cancellation immediately"
        ...     ],
        ...     conflicts_identified=[
        ...         ConflictDetail(
        ...             agents_involved=["crew_compliance", "network"],
        ...             conflict_type="safety_vs_business",
        ...             description=(
        ...                 "Crew Compliance requires 10-hour rest vs "
        ...                 "Network wants 2-hour delay"
        ...             )
        ...         )
        ...     ],
        ...     conflict_resolutions=[
        ...         ResolutionDetail(
        ...             conflict_description="Crew rest vs network propagation",
        ...             resolution="Enforce 10-hour crew rest requirement",
        ...             rationale="Safety constraint takes priority over business optimization"
        ...         )
        ...     ],
        ...     safety_overrides=[
        ...         SafetyOverride(
        ...             safety_agent="crew_compliance",
        ...             binding_constraint="Crew must have 10 hours rest",
        ...             overridden_recommendations=[
        ...                 "Network: Delay 2 hours to minimize propagation"
        ...             ]
        ...         )
        ...     ],
        ...     justification=(
        ...         "Safety constraints are non-negotiable. Crew duty limits "
        ...         "are regulatory requirements that cannot be compromised."
        ...     ),
        ...     reasoning=(
        ...         "Analyzed conflict between crew rest requirement and network "
        ...         "optimization. Applied Rule 1 (Safety vs Business): always "
        ...         "choose safety constraint. Network impact is significant but "
        ...         "acceptable compared to safety risk."
        ...     ),
        ...     confidence=0.95,
        ...     timestamp=datetime.now(timezone.utc).isoformat(),
        ...     model_used="us.anthropic.claude-opus-4-5-20250514-v1:0",
        ...     duration_seconds=4.2
        ... )
    
    Example (No Conflicts):
        >>> output = ArbitratorOutput(
        ...     final_decision="Approve 2-hour delay with passenger notification",
        ...     recommendations=[
        ...         "Delay flight by 2 hours for maintenance completion",
        ...         "Notify all passengers of delay",
        ...         "Provide meal vouchers for affected passengers"
        ...     ],
        ...     conflicts_identified=[],
        ...     conflict_resolutions=[],
        ...     safety_overrides=[],
        ...     justification="All agents agree on 2-hour delay approach",
        ...     reasoning="No conflicts detected. All safety and business agents support delay.",
        ...     confidence=0.98,
        ...     timestamp=datetime.now(timezone.utc).isoformat(),
        ...     model_used="us.anthropic.claude-opus-4-5-20250514-v1:0",
        ...     duration_seconds=2.8
        ... )
    
    Validation:
        - final_decision: Cannot be empty
        - recommendations: Must contain at least one recommendation
        - justification: Cannot be empty
        - reasoning: Cannot be empty
        - confidence: Must be between 0.0 and 1.0
        - timestamp: Must be valid ISO 8601 format
        - duration_seconds: Must be non-negative
    
    Design Rationale:
        - Provides complete audit trail for regulatory compliance
        - Explicitly tracks safety overrides for transparency
        - Documents all conflicts and resolutions
        - Includes model information for reproducibility
        - Confidence score indicates decision certainty
    
    See Also:
        - ArbitratorInput: Input schema for arbitrator
        - ConflictDetail: Details of conflicts
        - ResolutionDetail: How conflicts were resolved
        - SafetyOverride: Safety constraints that took priority
    """
    
    final_decision: str = Field(
        description="Clear, actionable decision text"
    )
    recommendations: List[str] = Field(
        description="List of specific actions to take"
    )
    conflicts_identified: List[ConflictDetail] = Field(
        default_factory=list,
        description="Conflicts identified between agents"
    )
    conflict_resolutions: List[ResolutionDetail] = Field(
        default_factory=list,
        description="How each conflict was resolved"
    )
    safety_overrides: List[SafetyOverride] = Field(
        default_factory=list,
        description="Safety constraints that overrode business recommendations"
    )
    justification: str = Field(
        description="Overall justification for the decision"
    )
    reasoning: str = Field(
        description="Detailed reasoning process"
    )
    confidence: float = Field(
        description="Confidence score (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    timestamp: str = Field(
        description="ISO 8601 timestamp of decision"
    )
    model_used: Optional[str] = Field(
        default=None,
        description="Model ID used for arbitration (e.g., Opus 4.5 or Sonnet 4.5)"
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Arbitration duration in seconds"
    )
    
    # NEW: Multiple solution options (arbitrator-multi-solution-enhancements)
    solution_options: Optional[List[RecoverySolution]] = Field(
        default=None,
        description="1-3 ranked recovery solution options (None for backward compatibility)"
    )
    recommended_solution_id: Optional[int] = Field(
        default=None,
        description="ID of the recommended solution (1, 2, or 3)"
    )
    
    # NEW: Phase evolution analysis (arbitrator-dual-phase-input)
    recommendation_evolution: Optional["RecommendationEvolution"] = Field(
        default=None,
        description="Analysis of how recommendations evolved between Phase 1 and Phase 2"
    )
    phases_considered: List[str] = Field(
        default_factory=lambda: ["phase2"],
        description="Which phases were available for decision making (e.g., ['phase1', 'phase2'])"
    )
    
    @field_validator("final_decision", "justification", "reasoning")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """
        Validate field is not empty.
        
        Args:
            v: Field value
            
        Returns:
            Validated field value
            
        Raises:
            ValueError: If field is empty
        """
        v = v.strip()
        if not v:
            raise ValueError(
                "Arbitrator output fields cannot be empty. "
                "Provide complete decision information."
            )
        
        return v
    
    @field_validator("recommendations")
    @classmethod
    def validate_recommendations(cls, v: List[str]) -> List[str]:
        """
        Validate at least one recommendation is provided.
        
        Args:
            v: List of recommendations
            
        Returns:
            Validated list of recommendations
            
        Raises:
            ValueError: If no recommendations provided
        """
        if not v:
            raise ValueError(
                "At least one recommendation must be provided. "
                "Arbitrator must specify actionable steps."
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
    
    @field_validator("solution_options")
    @classmethod
    def validate_solution_options(cls, v: Optional[List[RecoverySolution]]) -> Optional[List[RecoverySolution]]:
        """Validate solution options are properly ranked and have unique IDs"""
        if v is None:
            return v
        
        # Treat empty list as None for backward compatibility
        if not v:
            return None
        
        if len(v) > 3:
            raise ValueError(f"Maximum 3 solution options allowed, got {len(v)}")
        
        # Check solution IDs are unique and sequential
        solution_ids = [s.solution_id for s in v]
        expected_ids = list(range(1, len(v) + 1))
        if sorted(solution_ids) != expected_ids:
            raise ValueError(
                f"Solution IDs must be unique and sequential 1..{len(v)}, got {solution_ids}"
            )
        
        # Check solutions are ranked by composite score (descending)
        scores = [s.composite_score for s in v]
        if scores != sorted(scores, reverse=True):
            raise ValueError(
                f"Solutions must be ranked by composite score (highest first). "
                f"Got scores: {scores}"
            )
        
        return v
    
    @field_validator("recommended_solution_id")
    @classmethod
    def validate_recommended_solution_id(cls, v: Optional[int], info) -> Optional[int]:
        """Validate recommended solution ID exists in solution options"""
        if v is None:
            return v
        
        solution_options = info.data.get("solution_options")
        
        # If solution_options is None or empty, recommended_solution_id must also be None
        if solution_options is None or len(solution_options) == 0:
            raise ValueError(
                "recommended_solution_id cannot be set when solution_options is None or empty. "
                "Both must be None in error scenarios, or both must be populated in success scenarios."
            )
        
        valid_ids = [s.solution_id for s in solution_options]
        if v not in valid_ids:
            raise ValueError(
                f"Recommended solution ID {v} not found in solution options. "
                f"Valid IDs: {valid_ids}"
            )
        
        return v





# ============================================================================
# S3 Storage and Reporting Schemas
# ============================================================================
#
# These schemas support S3 storage for historical learning and comprehensive
# decision reporting for audit trails.
#
# - DecisionRecord: Historical record stored in S3
# - ImpactAssessment: Detailed impact analysis
# - DecisionReport: Comprehensive audit report
#
# ============================================================================


class DecisionRecord(BaseModel):
    """
    Record of a decision for historical learning and S3 storage.
    
    This schema captures the complete decision-making process including
    all agent responses, solution options, human selection, and eventual
    outcomes. Records are stored in S3 for historical learning and audit.
    
    S3 Storage:
        Records are stored in two buckets:
        - skymarshal-prod-knowledge-base-368613657554 (for historical learning)
        - skymarshal-prod-decisions-368613657554 (for audit trail)
        
        Key format: decisions/YYYY/MM/DD/{disruption_id}.json
    """
    
    # Disruption Context
    disruption_id: str = Field(description="Unique identifier for this disruption event")
    timestamp: str = Field(description="ISO 8601 timestamp of decision")
    flight_number: str = Field(description="Flight number (e.g., EY123)")
    disruption_type: str = Field(description="Type of disruption (e.g., mechanical, weather, crew)")
    disruption_severity: str = Field(description="Severity: low, medium, high, critical")
    
    # Agent Recommendations
    agent_responses: Dict[str, Any] = Field(description="All agent responses from analysis")
    
    # Arbitrator Analysis
    solution_options: List[RecoverySolution] = Field(description="All solution options presented")
    recommended_solution_id: int = Field(description="Arbitrator's recommended solution")
    conflicts_identified: List[ConflictDetail] = Field(default_factory=list)
    conflict_resolutions: List[ResolutionDetail] = Field(default_factory=list)
    
    # Human Decision
    selected_solution_id: int = Field(description="Solution ID selected by human")
    selection_rationale: Optional[str] = Field(
        default=None,
        description="Why human chose this solution"
    )
    human_override: bool = Field(
        description="True if human selected different solution than recommended"
    )
    
    # Outcome (filled in later after execution)
    outcome_status: Optional[str] = Field(
        default=None,
        description="Outcome: success, partial_success, failure"
    )
    actual_delay: Optional[float] = Field(
        default=None,
        description="Actual delay in hours"
    )
    actual_cost: Optional[float] = Field(
        default=None,
        description="Actual cost incurred"
    )
    lessons_learned: Optional[str] = Field(
        default=None,
        description="Post-incident analysis and lessons"
    )
    
    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is in ISO 8601 format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(
                f"Invalid timestamp format: {v}. "
                "Expected ISO 8601 format"
            )


class ImpactAssessment(BaseModel):
    """
    Detailed impact assessment for a specific category.
    
    Impact assessments provide structured analysis of how the disruption
    and proposed solutions affect different operational areas.
    """
    
    category: str = Field(description="Impact category: safety, financial, passenger, network, cargo")
    severity: str = Field(description="Severity: low, medium, high, critical")
    description: str = Field(description="Detailed description of the impact")
    quantitative_metrics: Dict[str, Any] = Field(description="Measurable metrics")
    mitigation_strategies: List[str] = Field(description="How to mitigate this impact")
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of the known categories"""
        valid_categories = {"safety", "financial", "passenger", "network", "cargo"}
        v = v.strip().lower()
        if v not in valid_categories:
            raise ValueError(
                f"Invalid impact category: {v}. "
                f"Must be one of: {', '.join(sorted(valid_categories))}"
            )
        return v
    
    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate severity is one of the known levels"""
        valid_severities = {"low", "medium", "high", "critical"}
        v = v.strip().lower()
        if v not in valid_severities:
            raise ValueError(
                f"Invalid severity: {v}. "
                f"Must be one of: {', '.join(sorted(valid_severities))}"
            )
        return v


class DecisionReport(BaseModel):
    """
    Comprehensive decision report for download and audit.
    
    This schema provides a complete audit trail of the decision-making
    process, including all agent assessments, conflicts, solutions,
    and the final decision rationale. Reports can be exported in
    multiple formats (PDF, JSON, Markdown).
    """
    
    # Header
    report_id: str = Field(description="Unique report identifier")
    generated_at: str = Field(description="ISO 8601 timestamp of report generation")
    disruption_summary: str = Field(description="Summary of the disruption event")
    
    # Agent Analysis Section
    agent_assessments: Dict[str, Dict[str, Any]] = Field(
        description="All agent responses and assessments"
    )
    
    # Conflict Analysis Section
    conflicts_identified: List[ConflictDetail] = Field(default_factory=list)
    conflict_resolutions: List[ResolutionDetail] = Field(default_factory=list)
    safety_overrides: List[SafetyOverride] = Field(default_factory=list)
    
    # Solution Options Section
    solution_options: List[RecoverySolution] = Field(description="All solution options")
    recommended_solution: RecoverySolution = Field(description="The recommended solution")
    
    # Impact Analysis Section
    impact_assessments: List[ImpactAssessment] = Field(description="Detailed impact analysis")
    
    # Decision Rationale Section
    decision_rationale: str = Field(description="Overall decision rationale")
    key_considerations: List[str] = Field(description="Key factors in the decision")
    assumptions_made: List[str] = Field(description="Assumptions made during analysis")
    uncertainties: List[str] = Field(description="Areas of uncertainty")
    
    # Historical Context Section (placeholder for future KB integration)
    similar_past_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Similar past disruption events"
    )
    historical_success_rates: Dict[str, float] = Field(
        default_factory=dict,
        description="Success rates for different solution types"
    )
    lessons_applied: List[str] = Field(
        default_factory=list,
        description="Lessons from past events applied here"
    )
    
    # Confidence Analysis Section
    confidence_score: float = Field(description="Overall confidence 0.0-1.0", ge=0.0, le=1.0)
    confidence_factors: Dict[str, str] = Field(
        description="Factors affecting confidence (positive and negative)"
    )
    data_quality_assessment: str = Field(description="Assessment of data quality")
    
    # Metadata
    model_used: str = Field(description="Model used for arbitration")
    processing_time: float = Field(description="Processing time in seconds")
    agents_consulted: List[str] = Field(description="List of agents consulted")
    
    @field_validator("generated_at")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp is in ISO 8601 format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(
                f"Invalid timestamp format: {v}. "
                "Expected ISO 8601 format"
            )


# ============================================================================
# Phase Evolution Schemas (Dual-Phase Input Enhancement)
# ============================================================================
#
# These schemas support the dual-phase input enhancement for the arbitrator,
# enabling analysis of how agent recommendations evolved between Phase 1
# (initial) and Phase 2 (revised).
#
# Key Concepts:
# - Convergence: Agents moving toward agreement (positive signal)
# - Divergence: Agents moving apart (warning signal)
# - Stability: Unchanged recommendations (high confidence signal)
# - New Constraints: Binding constraints added in Phase 2 (critical signal)
#
# ============================================================================


class AgentEvolution(BaseModel):
    """
    Evolution of a single agent's recommendation between Phase 1 and Phase 2.
    
    This model tracks how an agent's recommendation changed during the
    multi-round orchestration process, providing insights into:
    - Whether the agent changed their recommendation
    - The direction of change (convergence, divergence, or stability)
    - Changes to binding constraints
    
    Attributes:
        agent_name: Name of the agent
        phase1_recommendation: Phase 1 recommendation text (None if not in Phase 1)
        phase2_recommendation: Phase 2 recommendation text
        phase1_confidence: Phase 1 confidence score (None if not in Phase 1)
        phase2_confidence: Phase 2 confidence score
        change_type: Classification of how the recommendation changed
        binding_constraints_added: Binding constraints added in Phase 2
        binding_constraints_removed: Binding constraints removed in Phase 2
        change_summary: Human-readable summary of the change
    
    Change Types:
        - unchanged: Recommendation stayed the same
        - converged: Agent moved toward agreement with others
        - diverged: Agent moved further from others
        - new_in_phase2: Agent only present in Phase 2
        - dropped_in_phase2: Agent only present in Phase 1
    
    Example:
        >>> evolution = AgentEvolution(
        ...     agent_name="network",
        ...     phase1_recommendation="Delay 2 hours to minimize propagation",
        ...     phase2_recommendation="Delay 10 hours to satisfy crew rest",
        ...     phase1_confidence=0.85,
        ...     phase2_confidence=0.90,
        ...     change_type="converged",
        ...     binding_constraints_added=[],
        ...     binding_constraints_removed=[],
        ...     change_summary="Network agent revised delay from 2h to 10h after seeing crew constraints"
        ... )
    """
    
    agent_name: str = Field(description="Name of the agent")
    phase1_recommendation: Optional[str] = Field(
        default=None,
        description="Phase 1 recommendation text (None if agent not in Phase 1)"
    )
    phase2_recommendation: str = Field(
        description="Phase 2 recommendation text"
    )
    phase1_confidence: Optional[float] = Field(
        default=None,
        description="Phase 1 confidence score",
        ge=0.0,
        le=1.0
    )
    phase2_confidence: float = Field(
        description="Phase 2 confidence score",
        ge=0.0,
        le=1.0
    )
    change_type: Literal["unchanged", "converged", "diverged", "new_in_phase2", "dropped_in_phase2"] = Field(
        description="Classification of how the recommendation changed"
    )
    binding_constraints_added: List[str] = Field(
        default_factory=list,
        description="Binding constraints added in Phase 2"
    )
    binding_constraints_removed: List[str] = Field(
        default_factory=list,
        description="Binding constraints removed in Phase 2"
    )
    change_summary: str = Field(
        description="Human-readable summary of the change"
    )
    
    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v: str) -> str:
        """Validate agent name is one of the known agents."""
        valid_agents = {
            "crew_compliance", "maintenance", "regulatory",
            "network", "guest_experience", "cargo", "finance",
            "arbitrator"
        }
        v = v.lower().strip()
        if v not in valid_agents:
            raise ValueError(
                f"Invalid agent name: {v}. "
                f"Must be one of: {', '.join(sorted(valid_agents))}"
            )
        return v
    
    @field_validator("change_summary")
    @classmethod
    def validate_change_summary(cls, v: str) -> str:
        """Validate change summary is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Change summary cannot be empty")
        return v


class RecommendationEvolution(BaseModel):
    """
    Complete evolution analysis across all agents between Phase 1 and Phase 2.
    
    This model aggregates the evolution of all agent recommendations,
    providing a high-level view of how the multi-round process influenced
    the final recommendations.
    
    Attributes:
        phases_available: Which phases were provided (e.g., ["phase1", "phase2"])
        agents_changed: Count of agents that changed recommendations
        agents_unchanged: Count of agents with stable recommendations
        convergence_detected: Whether agents showed convergence pattern
        divergence_detected: Whether agents showed divergence pattern
        evolution_details: Detailed evolution for each agent
        analysis_summary: Overall summary of recommendation evolution
    
    Interpretation:
        - High convergence + low divergence: Consensus building (positive)
        - High divergence: Unresolved conflicts (requires attention)
        - High stability: Strong initial recommendations (high confidence)
        - Many new constraints: New information discovered (critical)
    
    Example:
        >>> evolution = RecommendationEvolution(
        ...     phases_available=["phase1", "phase2"],
        ...     agents_changed=3,
        ...     agents_unchanged=4,
        ...     convergence_detected=True,
        ...     divergence_detected=False,
        ...     evolution_details=[...],
        ...     analysis_summary="3 agents revised recommendations toward consensus"
        ... )
    """
    
    phases_available: List[str] = Field(
        description="Which phases were provided (e.g., ['phase1', 'phase2'])"
    )
    agents_changed: int = Field(
        description="Count of agents that changed recommendations",
        ge=0
    )
    agents_unchanged: int = Field(
        description="Count of agents with stable recommendations",
        ge=0
    )
    convergence_detected: bool = Field(
        description="Whether agents showed convergence pattern"
    )
    divergence_detected: bool = Field(
        description="Whether agents showed divergence pattern"
    )
    evolution_details: List[AgentEvolution] = Field(
        default_factory=list,
        description="Detailed evolution for each agent"
    )
    analysis_summary: str = Field(
        description="Overall summary of recommendation evolution"
    )
    
    @field_validator("phases_available")
    @classmethod
    def validate_phases_available(cls, v: List[str]) -> List[str]:
        """Validate phases are valid."""
        valid_phases = {"phase1", "phase2"}
        for phase in v:
            if phase not in valid_phases:
                raise ValueError(
                    f"Invalid phase: {phase}. Must be one of: {', '.join(valid_phases)}"
                )
        return v
    
    @field_validator("analysis_summary")
    @classmethod
    def validate_analysis_summary(cls, v: str) -> str:
        """Validate analysis summary is not empty."""
        v = v.strip()
        if not v:
            raise ValueError("Analysis summary cannot be empty")
        return v

