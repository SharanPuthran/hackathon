"""Structured output schemas for inter-agent communication using Pydantic"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator
import re
from datetime import datetime


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


class FlightInfo(BaseModel):
    """
    Flight information extracted from natural language prompts.
    
    This model is used with LangChain's with_structured_output() to extract
    structured flight data from user prompts like:
    - "Flight EY123 on January 20th had a mechanical failure"
    - "EY456 yesterday was delayed due to weather"
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
    """Payload for agent invocation in multi-round orchestration"""

    user_prompt: str = Field(description="Natural language prompt from user")
    phase: Literal["initial", "revision"] = Field(
        description="Execution phase: initial or revision"
    )
    other_recommendations: Optional[Dict[str, Any]] = Field(
        default=None, description="Other agents' recommendations (revision phase only)"
    )


class AgentResponse(BaseModel):
    """Structured response from an agent"""

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


class Collation(BaseModel):
    """Collated responses from all agents in a phase"""

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
