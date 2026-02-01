# Design Document

## Overview

This design extends the SkyMarshal arbitrator agent to provide multiple ranked solution options with detailed recovery plans, S3 integration for historical learning, and comprehensive decision reports. The arbitrator currently returns a single final decision; this enhancement enables human decision makers to choose from 1-3 ranked alternatives, each with complete recovery workflows, impact assessments, and scoring across multiple dimensions.

The design maintains backward compatibility with the existing three-phase orchestration workflow (initial → revision → arbitration) while adding new capabilities for multi-solution generation, recovery planning, historical learning, and audit reporting.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Phase 3: Arbitration                         │
│                                                                 │
│  ┌──────────────┐                                              │
│  │  Orchestrator│                                              │
│  │   (main.py)  │                                              │
│  └──────┬───────┘                                              │
│         │                                                       │
│         │ revised_recommendations                              │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │           Arbitrator Agent (Enhanced)                     │ │
│  │                                                           │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  1. Conflict Analysis & Constraint Validation       │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  2. Solution Generation (1-3 options)               │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  3. Multi-Dimensional Scoring                       │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  4. Recovery Plan Generation                        │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │  5. Solution Ranking & Recommendation               │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         │ ArbitratorOutput (with solution_options)             │
│         ▼                                                       │
│  ┌──────────────┐                                              │
│  │   Frontend   │                                              │
│  │  (React UI)  │                                              │
│  └──────┬───────┘                                              │
│         │                                                       │
│         │ Human selects solution                               │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         API: POST /api/select-solution                    │ │
│  └──────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         │ Store decision record                                │
│         ▼                                                       │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              S3 Storage (boto3)                           │ │
│  │                                                           │ │
│  │  • skymarshal-prod-knowledge-base-368613657554           │ │
│  │  • skymarshal-prod-decisions-368613657554                │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Orchestrator** completes Phase 2 (revision) and invokes arbitrator with revised recommendations
2. **Arbitrator** analyzes conflicts, validates constraints, generates 1-3 solution options
3. **Arbitrator** scores each solution across multiple dimensions and ranks by composite score
4. **Arbitrator** generates detailed recovery plans for each solution
5. **Arbitrator** returns enhanced output with solution_options array
6. **Frontend** displays solutions to Duty Manager for selection
7. **API Endpoint** receives human selection and creates decision record
8. **S3 Storage** persists decision record to both buckets for learning and audit

## Components and Interfaces

### 1. Enhanced Pydantic Schemas (schemas.py)

#### RecoveryStep Schema

```python
class RecoveryStep(BaseModel):
    """A single step in the recovery process"""
    step_number: int = Field(description="Sequential step number starting from 1")
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
```

#### RecoveryPlan Schema

```python
class RecoveryPlan(BaseModel):
    """Complete recovery plan for a solution"""
    solution_id: int = Field(description="ID of the solution this plan belongs to")
    total_steps: int = Field(description="Total number of steps in the plan")
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
            raise ValueError(f"Step numbers must be sequential 1..{len(v)}, got {step_numbers}")

        # Check for circular dependencies
        for step in v:
            if step.step_number in step.dependencies:
                raise ValueError(f"Step {step.step_number} cannot depend on itself")

            # Check all dependencies reference valid steps
            for dep in step.dependencies:
                if dep < 1 or dep > len(v):
                    raise ValueError(
                        f"Step {step.step_number} has invalid dependency {dep}. "
                        f"Valid range: 1..{len(v)}"
                    )
                if dep >= step.step_number:
                    raise ValueError(
                        f"Step {step.step_number} cannot depend on later step {dep}"
                    )

        return v
```

#### RecoverySolution Schema

```python
class RecoverySolution(BaseModel):
    """A single recovery solution option"""
    solution_id: int = Field(description="Unique ID: 1, 2, or 3")
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
```

#### Enhanced ArbitratorOutput Schema

```python
class ArbitratorOutput(BaseModel):
    """Enhanced output schema with multiple solution options"""

    # Existing fields (backward compatibility)
    final_decision: str = Field(description="Clear, actionable decision text")
    recommendations: List[str] = Field(description="List of specific actions to take")
    conflicts_identified: List[ConflictDetail] = Field(default_factory=list)
    conflict_resolutions: List[ResolutionDetail] = Field(default_factory=list)
    safety_overrides: List[SafetyOverride] = Field(default_factory=list)
    justification: str = Field(description="Overall justification for the decision")
    reasoning: str = Field(description="Detailed reasoning process")
    confidence: float = Field(description="Confidence score (0.0 to 1.0)", ge=0.0, le=1.0)
    timestamp: str = Field(description="ISO 8601 timestamp of decision")
    model_used: Optional[str] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)

    # NEW: Multiple solution options
    solution_options: List[RecoverySolution] = Field(
        description="1-3 ranked recovery solution options",
        min_length=1,
        max_length=3
    )
    recommended_solution_id: int = Field(
        description="ID of the recommended solution (1, 2, or 3)"
    )

    @field_validator("solution_options")
    @classmethod
    def validate_solution_options(cls, v: List[RecoverySolution]) -> List[RecoverySolution]:
        """Validate solution options are properly ranked and have unique IDs"""
        if not v:
            raise ValueError("At least one solution option must be provided")

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
    def validate_recommended_solution_id(cls, v: int, info) -> int:
        """Validate recommended solution ID exists in solution options"""
        solution_options = info.data.get("solution_options", [])
        valid_ids = [s.solution_id for s in solution_options]

        if v not in valid_ids:
            raise ValueError(
                f"Recommended solution ID {v} not found in solution options. "
                f"Valid IDs: {valid_ids}"
            )

        return v
```

### 2. Decision Record Schema (for S3 Storage)

```python
class DecisionRecord(BaseModel):
    """Record of a decision for historical learning"""

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
```

### 3. Decision Report Schema

```python
class ImpactAssessment(BaseModel):
    """Detailed impact assessment for a specific category"""
    category: str = Field(description="Impact category: safety, financial, passenger, network, cargo")
    severity: str = Field(description="Severity: low, medium, high, critical")
    description: str = Field(description="Detailed description of the impact")
    quantitative_metrics: Dict[str, Any] = Field(description="Measurable metrics")
    mitigation_strategies: List[str] = Field(description="How to mitigate this impact")


class DecisionReport(BaseModel):
    """Comprehensive decision report for download and audit"""

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
```

### 4. Enhanced Arbitrator Agent (arbitrator/agent.py)

The arbitrator agent will be enhanced with new capabilities while maintaining backward compatibility.

#### Key Functions

```python
async def arbitrate(
    revised_recommendations: dict,
    llm_opus: Optional[Any] = None
) -> dict:
    """
    Main arbitration function (enhanced).

    Now generates 1-3 solution options with recovery plans instead of
    a single decision. Maintains backward compatibility by populating
    final_decision and recommendations from the recommended solution.
    """
    # Existing logic for conflict analysis and constraint validation
    # NEW: Generate multiple solution options
    # NEW: Score each solution across dimensions
    # NEW: Generate recovery plans for each solution
    # NEW: Rank solutions by composite score
    # NEW: Populate backward-compatible fields from recommended solution
```

#### Helper Functions

```python
def _generate_solution_options(
    responses: Dict[str, Any],
    binding_constraints: List[Dict[str, Any]],
    conflicts: List[ConflictDetail],
    llm: Any
) -> List[RecoverySolution]:
    """
    Generate 1-3 distinct solution options.

    Uses the LLM to generate multiple approaches that:
    - All satisfy binding constraints
    - Represent different trade-off points
    - Are Pareto-optimal (no solution dominates another across all dimensions)
    """


def _score_solution(
    solution: Dict[str, Any],
    agent_responses: Dict[str, Any]
) -> Dict[str, float]:
    """
    Score a solution across multiple dimensions.

    Returns:
        {
            "safety_score": 0-100,
            "cost_score": 0-100,
            "passenger_score": 0-100,
            "network_score": 0-100,
            "composite_score": weighted average
        }
    """


def _generate_recovery_plan(
    solution: Dict[str, Any],
    agent_responses: Dict[str, Any],
    llm: Any
) -> RecoveryPlan:
    """
    Generate detailed recovery plan for a solution.

    Uses the LLM to create step-by-step recovery workflow with:
    - Sequential steps with dependencies
    - Responsible agents for each step
    - Success criteria and rollback procedures
    - Critical path identification
    """


def _validate_recovery_plan(plan: RecoveryPlan) -> bool:
    """
    Validate recovery plan for logical consistency.

    Checks:
    - No circular dependencies
    - All dependencies reference valid steps
    - Critical path is valid
    """


def _populate_backward_compatible_fields(
    output: ArbitratorOutput
) -> ArbitratorOutput:
    """
    Populate final_decision and recommendations from recommended solution.

    Ensures existing integrations continue to work by extracting
    the recommended solution's details into the legacy fields.
    """
```

### 5. S3 Storage Module (s3_storage.py)

New module for storing decision records to S3.

```python
import boto3
import json
from datetime import datetime
from typing import Dict, Any
from agents.schemas import DecisionRecord

# S3 bucket names
KNOWLEDGE_BASE_BUCKET = "skymarshal-prod-knowledge-base-368613657554"
DECISIONS_BUCKET = "skymarshal-prod-decisions-368613657554"


async def store_decision_to_s3(
    decision_record: DecisionRecord,
    buckets: List[str] = None
) -> Dict[str, bool]:
    """
    Store decision record to S3 buckets.

    Args:
        decision_record: The decision record to store
        buckets: List of bucket names (defaults to both KB and decisions buckets)

    Returns:
        Dict mapping bucket name to success status

    Example:
        >>> record = DecisionRecord(...)
        >>> result = await store_decision_to_s3(record)
        >>> print(result)
        {
            "skymarshal-prod-knowledge-base-368613657554": True,
            "skymarshal-prod-decisions-368613657554": True
        }
    """
    if buckets is None:
        buckets = [KNOWLEDGE_BASE_BUCKET, DECISIONS_BUCKET]

    s3_client = boto3.client('s3')
    results = {}

    # Generate S3 key with date partitioning
    dt = datetime.fromisoformat(decision_record.timestamp)
    s3_key = f"decisions/{dt.year}/{dt.month:02d}/{dt.day:02d}/{decision_record.disruption_id}.json"

    # Convert to JSON
    record_json = json.dumps(decision_record.model_dump(), indent=2)

    # Upload to each bucket
    for bucket in buckets:
        try:
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=record_json,
                ContentType='application/json',
                Metadata={
                    'disruption_type': decision_record.disruption_type,
                    'flight_number': decision_record.flight_number,
                    'selected_solution': str(decision_record.selected_solution_id),
                    'human_override': str(decision_record.human_override)
                }
            )
            results[bucket] = True
        except Exception as e:
            logger.error(f"Failed to store to {bucket}: {e}")
            results[bucket] = False

    return results


async def load_decision_from_s3(
    disruption_id: str,
    bucket: str = DECISIONS_BUCKET
) -> Optional[DecisionRecord]:
    """
    Load a decision record from S3.

    Searches all date partitions for the disruption_id.
    """
    # Implementation for loading decision records
    pass
```

### 6. API Endpoint (api/endpoints.py)

New API endpoint for recording human solution selections.

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from agents.schemas import DecisionRecord
from s3_storage import store_decision_to_s3

router = APIRouter()


class SolutionSelectionRequest(BaseModel):
    """Request body for solution selection"""
    disruption_id: str
    selected_solution_id: int
    rationale: Optional[str] = None


class SolutionSelectionResponse(BaseModel):
    """Response for solution selection"""
    status: str
    message: str
    stored_to_buckets: Dict[str, bool]


@router.post("/api/select-solution", response_model=SolutionSelectionResponse)
async def select_solution(request: SolutionSelectionRequest):
    """
    Record human's solution selection and store to S3.

    This endpoint is called when the Duty Manager selects a solution
    from the arbitrator's recommendations.

    Args:
        request: Selection request with disruption_id, selected_solution_id, rationale

    Returns:
        Response with status and confirmation

    Raises:
        HTTPException: If disruption_id not found or storage fails
    """
    try:
        # Load original arbitrator output for this disruption
        # (Implementation depends on how orchestrator stores outputs)
        arbitrator_output = await load_arbitrator_output(request.disruption_id)

        if not arbitrator_output:
            raise HTTPException(
                status_code=404,
                detail=f"Disruption {request.disruption_id} not found"
            )

        # Validate selected solution ID exists
        valid_ids = [s.solution_id for s in arbitrator_output.solution_options]
        if request.selected_solution_id not in valid_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid solution ID {request.selected_solution_id}. Valid: {valid_ids}"
            )

        # Create decision record
        decision_record = DecisionRecord(
            disruption_id=request.disruption_id,
            timestamp=arbitrator_output.timestamp,
            flight_number=extract_flight_number(arbitrator_output),
            disruption_type=extract_disruption_type(arbitrator_output),
            disruption_severity="medium",  # Could be derived from agent responses
            agent_responses=extract_agent_responses(arbitrator_output),
            solution_options=arbitrator_output.solution_options,
            recommended_solution_id=arbitrator_output.recommended_solution_id,
            conflicts_identified=arbitrator_output.conflicts_identified,
            conflict_resolutions=arbitrator_output.conflict_resolutions,
            selected_solution_id=request.selected_solution_id,
            selection_rationale=request.rationale,
            human_override=(
                request.selected_solution_id != arbitrator_output.recommended_solution_id
            )
        )

        # Store to S3
        storage_results = await store_decision_to_s3(decision_record)

        # Check if storage succeeded
        all_success = all(storage_results.values())

        return SolutionSelectionResponse(
            status="success" if all_success else "partial_success",
            message=(
                "Decision recorded for historical learning"
                if all_success
                else "Decision recorded but some storage operations failed"
            ),
            stored_to_buckets=storage_results
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record solution selection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record solution selection: {str(e)}"
        )
```

### 7. Report Generation Module (report_generator.py)

Module for generating comprehensive decision reports in multiple formats.

```python
from agents.schemas import DecisionReport, ArbitratorOutput, ImpactAssessment
from typing import Dict, Any
import json


def generate_decision_report(
    arbitrator_output: ArbitratorOutput,
    agent_responses: Dict[str, Any],
    user_prompt: str
) -> DecisionReport:
    """
    Generate comprehensive decision report from arbitrator output.

    Args:
        arbitrator_output: The arbitrator's output with solution options
        agent_responses: All agent responses from the analysis
        user_prompt: Original disruption description

    Returns:
        DecisionReport with complete analysis and audit trail
    """
    # Extract recommended solution
    recommended = next(
        s for s in arbitrator_output.solution_options
        if s.solution_id == arbitrator_output.recommended_solution_id
    )

    # Generate impact assessments
    impact_assessments = _generate_impact_assessments(
        arbitrator_output,
        agent_responses
    )

    # Extract key considerations
    key_considerations = _extract_key_considerations(
        arbitrator_output,
        agent_responses
    )

    return DecisionReport(
        report_id=f"report_{arbitrator_output.timestamp}",
        generated_at=datetime.now(timezone.utc).isoformat(),
        disruption_summary=user_prompt,
        agent_assessments=agent_responses,
        conflicts_identified=arbitrator_output.conflicts_identified,
        conflict_resolutions=arbitrator_output.conflict_resolutions,
        safety_overrides=arbitrator_output.safety_overrides,
        solution_options=arbitrator_output.solution_options,
        recommended_solution=recommended,
        impact_assessments=impact_assessments,
        decision_rationale=arbitrator_output.justification,
        key_considerations=key_considerations,
        assumptions_made=_extract_assumptions(arbitrator_output),
        uncertainties=_extract_uncertainties(arbitrator_output),
        similar_past_events=[],  # Placeholder for future KB integration
        historical_success_rates={},  # Placeholder for future KB integration
        lessons_applied=[],  # Placeholder for future KB integration
        confidence_score=arbitrator_output.confidence,
        confidence_factors=_analyze_confidence_factors(arbitrator_output),
        data_quality_assessment=_assess_data_quality(agent_responses),
        model_used=arbitrator_output.model_used or "unknown",
        processing_time=arbitrator_output.duration_seconds or 0.0,
        agents_consulted=list(agent_responses.keys())
    )


async def export_report_pdf(report: DecisionReport) -> bytes:
    """
    Export decision report as PDF.

    Uses reportlab or weasyprint to generate PDF from report data.
    """
    # Implementation for PDF generation
    pass


async def export_report_json(report: DecisionReport) -> str:
    """
    Export decision report as JSON.

    Returns formatted JSON string with proper indentation.
    """
    return report.model_dump_json(indent=2)


async def export_report_markdown(report: DecisionReport) -> str:
    """
    Export decision report as Markdown.

    Generates human-readable markdown document with sections.
    """
    md = f"""# Decision Report: {report.report_id}

**Generated:** {report.generated_at}
**Model Used:** {report.model_used}
**Processing Time:** {report.processing_time:.2f}s
**Confidence:** {report.confidence_score:.2f}

## Disruption Summary

{report.disruption_summary}

## Recommended Solution

**{report.recommended_solution.title}**

{report.recommended_solution.description}

### Scoring
- Safety: {report.recommended_solution.safety_score:.1f}/100
- Cost: {report.recommended_solution.cost_score:.1f}/100
- Passenger Impact: {report.recommended_solution.passenger_score:.1f}/100
- Network Impact: {report.recommended_solution.network_score:.1f}/100
- **Composite: {report.recommended_solution.composite_score:.1f}/100**

### Pros
{chr(10).join(f"- {pro}" for pro in report.recommended_solution.pros)}

### Cons
{chr(10).join(f"- {con}" for con in report.recommended_solution.cons)}

## All Solution Options

{_format_solutions_markdown(report.solution_options)}

## Conflicts and Resolutions

{_format_conflicts_markdown(report.conflicts_identified, report.conflict_resolutions)}

## Impact Assessments

{_format_impacts_markdown(report.impact_assessments)}

## Decision Rationale

{report.decision_rationale}

## Key Considerations

{chr(10).join(f"- {consideration}" for consideration in report.key_considerations)}

## Confidence Analysis

**Overall Confidence:** {report.confidence_score:.2f}

{_format_confidence_factors_markdown(report.confidence_factors)}

**Data Quality:** {report.data_quality_assessment}

## Agent Assessments

{_format_agent_assessments_markdown(report.agent_assessments)}
"""
    return md
```

## Data Models

### Solution Scoring Weights

The composite score is calculated as a weighted average of four dimensions:

```python
SCORING_WEIGHTS = {
    "safety": 0.40,      # 40% - Highest priority
    "cost": 0.20,        # 20% - Financial impact
    "passenger": 0.20,   # 20% - Customer impact
    "network": 0.20      # 20% - Operational impact
}

composite_score = (
    (safety_score * 0.40) +
    (cost_score * 0.20) +
    (passenger_score * 0.20) +
    (network_score * 0.20)
)
```

### Scoring Algorithms

#### Safety Score (0-100)

```python
def calculate_safety_score(solution: Dict, binding_constraints: List) -> float:
    """
    Calculate safety score based on margin above minimum requirements.

    - 100: Exceeds all safety requirements with significant margin
    - 80-99: Meets all requirements with comfortable margin
    - 60-79: Meets all requirements with minimal margin
    - 0-59: Violates one or more requirements (should be rejected)
    """
    # Check constraint satisfaction
    violations = check_constraint_violations(solution, binding_constraints)
    if violations:
        return 0.0  # Solution should be rejected

    # Calculate margin above minimum requirements
    margins = calculate_safety_margins(solution, binding_constraints)
    avg_margin = sum(margins.values()) / len(margins)

    # Convert margin to score (higher margin = higher score)
    return min(100.0, 60.0 + (avg_margin * 40.0))
```

#### Cost Score (0-100)

```python
def calculate_cost_score(solution: Dict, agent_responses: Dict) -> float:
    """
    Calculate cost score (higher score = lower cost).

    - 100: Minimal cost (< $10k)
    - 80-99: Low cost ($10k-$50k)
    - 60-79: Moderate cost ($50k-$150k)
    - 40-59: High cost ($150k-$300k)
    - 0-39: Very high cost (> $300k)
    """
    total_cost = extract_total_cost(solution, agent_responses)

    if total_cost < 10000:
        return 100.0
    elif total_cost < 50000:
        return 80.0 + ((50000 - total_cost) / 40000) * 20
    elif total_cost < 150000:
        return 60.0 + ((150000 - total_cost) / 100000) * 20
    elif total_cost < 300000:
        return 40.0 + ((300000 - total_cost) / 150000) * 20
    else:
        return max(0.0, 40.0 - ((total_cost - 300000) / 300000) * 40)
```

#### Passenger Score (0-100)

```python
def calculate_passenger_score(solution: Dict, agent_responses: Dict) -> float:
    """
    Calculate passenger impact score (higher score = less impact).

    Considers:
    - Number of passengers affected
    - Delay duration
    - Cancellation vs delay
    - Reprotection options available
    """
    passengers_affected = extract_passenger_count(solution, agent_responses)
    delay_hours = extract_delay_hours(solution)
    is_cancellation = is_flight_cancelled(solution)

    # Base score from passenger count
    if passengers_affected < 50:
        base_score = 100.0
    elif passengers_affected < 150:
        base_score = 80.0
    elif passengers_affected < 300:
        base_score = 60.0
    else:
        base_score = 40.0

    # Penalty for delay duration
    delay_penalty = min(30.0, delay_hours * 5.0)

    # Penalty for cancellation
    cancellation_penalty = 20.0 if is_cancellation else 0.0

    return max(0.0, base_score - delay_penalty - cancellation_penalty)
```

#### Network Score (0-100)

```python
def calculate_network_score(solution: Dict, agent_responses: Dict) -> float:
    """
    Calculate network impact score (higher score = less propagation).

    Considers:
    - Number of downstream flights affected
    - Connection misses
    - Aircraft rotation impact
    """
    downstream_flights = extract_downstream_flights(solution, agent_responses)
    connection_misses = extract_connection_misses(solution, agent_responses)

    # Base score from downstream impact
    if downstream_flights == 0:
        base_score = 100.0
    elif downstream_flights <= 2:
        base_score = 80.0
    elif downstream_flights <= 5:
        base_score = 60.0
    else:
        base_score = 40.0

    # Penalty for connection misses
    connection_penalty = min(30.0, connection_misses * 10.0)

    return max(0.0, base_score - connection_penalty)
```

### Recovery Plan Structure

Recovery plans follow a directed acyclic graph (DAG) structure where:

- Each step is a node
- Dependencies are directed edges
- No cycles are allowed
- Critical path is the longest path through the DAG

```
Example Recovery Plan DAG:

Step 1: Notify Crew Scheduling
    ↓
Step 2: Notify Passengers ←─────┐
    ↓                            │
Step 3: Schedule Maintenance     │
    ↓                            │
Step 4: Confirm Crew Available   │
    ↓                            │
Step 5: Update Slot Coordination │
    ↓                            │
Step 6: Final Departure Checks ──┘
    ↓
Step 7: Departure

Critical Path: 1 → 3 → 4 → 6 → 7 (longest duration)
```

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Solution Count Bounds

_For any_ arbitrator execution with valid agent responses, the number of solution options returned should be between 1 and 3 inclusive.
**Validates: Requirements 1.1**

### Property 2: Solution Ranking Invariant

_For any_ arbitrator output with multiple solutions, the solutions should be ordered by composite score in descending order (highest score first).
**Validates: Requirements 1.2**

### Property 3: Tiebreaker Consistency

_For any_ arbitrator output where two consecutive solutions have equal composite scores, the solution with the higher safety score should appear first.
**Validates: Requirements 1.3**

### Property 4: Recommended Solution Validity

_For any_ arbitrator output, the recommended_solution_id should reference a valid solution_id that exists in the solution_options list.
**Validates: Requirements 1.4**

### Property 5: Binding Constraint Satisfaction

_For any_ solution in the arbitrator output, that solution should satisfy all binding constraints from safety agents (crew_compliance, maintenance, regulatory).
**Validates: Requirements 1.5, 9.1**

### Property 6: Pareto Optimality

_For any_ arbitrator output with multiple solutions, no solution should dominate another solution across all four dimensions (safety, cost, passenger, network).
**Validates: Requirements 1.6**

### Property 7: Score Range Validation

_For any_ solution in the arbitrator output, all individual scores (safety_score, cost_score, passenger_score, network_score) should be in the range [0, 100].
**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**

### Property 8: Composite Score Calculation

_For any_ solution in the arbitrator output, the composite_score should equal the weighted average: (safety_score × 0.4) + (cost_score × 0.2) + (passenger_score × 0.2) + (network_score × 0.2), within a tolerance of 0.1.
**Validates: Requirements 2.6**

### Property 9: Solution Completeness

_For any_ solution in the arbitrator output, the solution should have non-empty pros, cons, risks lists and a non-empty estimated_duration string.
**Validates: Requirements 2.7, 2.8, 2.9, 2.10**

### Property 10: Recovery Plan Presence

_For any_ solution in the arbitrator output, the solution should have a non-null recovery_plan field with at least one step.
**Validates: Requirements 3.1**

### Property 11: Sequential Step Numbering

_For any_ recovery plan, the step numbers should be sequential starting from 1 with no gaps (i.e., [1, 2, 3, ..., N]).
**Validates: Requirements 3.2**

### Property 12: Recovery Step Completeness

_For any_ recovery step in a recovery plan, the step should have all required fields populated: step_name, description, responsible_agent, estimated_duration, action_type, success_criteria.
**Validates: Requirements 3.3, 3.4, 3.5, 3.6, 3.7**

### Property 13: No Self-Dependencies

_For any_ recovery step in a recovery plan, the step's dependencies list should not contain its own step_number.
**Validates: Requirements 10.1**

### Property 14: No Circular Dependencies

_For any_ recovery plan, there should be no circular dependency chains (i.e., the dependency graph should be a directed acyclic graph).
**Validates: Requirements 10.2**

### Property 15: Valid Dependency References

_For any_ recovery step with dependencies, all dependency step numbers should reference valid steps (i.e., be in the range [1, total_steps] and less than the current step number).
**Validates: Requirements 10.3**

### Property 16: Critical Path Validity

_For any_ recovery plan, all step numbers in the critical_path list should reference valid steps in the plan.
**Validates: Requirements 3.9, 10.4**

### Property 17: S3 Key Format

_For any_ decision record stored to S3, the S3 key should match the pattern `decisions/YYYY/MM/DD/{disruption_id}.json` where YYYY, MM, DD are extracted from the timestamp.
**Validates: Requirements 4.4**

### Property 18: S3 Metadata Presence

_For any_ decision record stored to S3, the S3 object metadata should include keys for disruption_type, flight_number, and selected_solution_id.
**Validates: Requirements 4.5**

### Property 19: Human Override Flag Consistency

_For any_ decision record, if selected_solution_id differs from recommended_solution_id, then human_override should be true; otherwise it should be false.
**Validates: Requirements 4.6**

### Property 20: JSON Format Validity

_For any_ decision record stored to S3, the stored content should be valid JSON that can be parsed back into a DecisionRecord object.
**Validates: Requirements 4.7**

### Property 21: API Error Handling

_For any_ API request to /api/select-solution with an invalid disruption_id, the response should have status code 404 and include an error message.
**Validates: Requirements 6.8**

### Property 22: Report Completeness

_For any_ generated decision report, the report should include all required sections: agent_assessments, conflicts_identified, solution_options, impact_assessments, decision_rationale.
**Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

### Property 23: Report Export Format Validity

_For any_ decision report exported as JSON, the output should be valid JSON that can be parsed back into a DecisionReport object.
**Validates: Requirements 7.7**

### Property 24: Backward Compatibility - Final Decision

_For any_ arbitrator output, the final_decision field should be populated with the description from the recommended solution.
**Validates: Requirements 8.1, 8.5**

### Property 25: Backward Compatibility - Recommendations

_For any_ arbitrator output, the recommendations field should be populated with the recommendations list from the recommended solution.
**Validates: Requirements 8.2, 8.5**

### Property 26: Constraint Violation Rejection

_For any_ potential solution that violates one or more binding constraints, that solution should not appear in the final solution_options list.
**Validates: Requirements 9.2**

## Error Handling

### Arbitrator Error Handling

1. **No Valid Solutions**: If all potential solutions violate binding constraints, return a single conservative solution recommending manual review with confidence 0.0
2. **LLM Failures**: If the LLM fails to generate solutions, fall back to a conservative single-solution response
3. **Recovery Plan Validation Failures**: If recovery plan validation detects circular dependencies, log warning and attempt to fix by removing problematic dependencies
4. **Scoring Errors**: If scoring calculation fails, use default scores (safety=100, others=50) and mark with low confidence

### S3 Storage Error Handling

1. **Bucket Access Failures**: If S3 upload fails for one bucket, continue with other bucket and return partial success status
2. **Network Errors**: Retry S3 operations up to 3 times with exponential backoff
3. **Permission Errors**: Log detailed error and return failure status with specific error message
4. **Invalid Decision Records**: Validate decision record before upload; reject invalid records with validation error

### API Endpoint Error Handling

1. **Invalid Disruption ID**: Return 404 with clear error message
2. **Invalid Solution ID**: Return 400 with list of valid solution IDs
3. **S3 Storage Failures**: Return 500 with details about which buckets failed
4. **Missing Required Fields**: Return 400 with list of missing fields
5. **Concurrent Requests**: Use optimistic locking to prevent race conditions

### Report Generation Error Handling

1. **Missing Data**: Generate report with available data and mark missing sections
2. **Export Format Errors**: Return error response with details about format issue
3. **Large Reports**: Implement pagination or streaming for very large reports
4. **PDF Generation Failures**: Fall back to JSON/Markdown export if PDF fails

## Testing Strategy

### Unit Tests

Unit tests will verify specific examples, edge cases, and error conditions:

1. **Schema Validation Tests**
   - Test RecoverySolution schema with valid and invalid data
   - Test RecoveryPlan validation catches circular dependencies
   - Test composite score validation catches incorrect calculations
   - Test DecisionRecord schema with all required fields

2. **Scoring Algorithm Tests**
   - Test safety score calculation with various margins
   - Test cost score calculation with different cost ranges
   - Test passenger score with different passenger counts and delays
   - Test network score with different downstream impacts

3. **S3 Storage Tests**
   - Test S3 key generation with various timestamps
   - Test metadata extraction from decision records
   - Test error handling for bucket access failures
   - Mock S3 client to verify correct API calls

4. **API Endpoint Tests**
   - Test successful solution selection flow
   - Test error cases (invalid IDs, missing fields)
   - Test human override flag calculation
   - Test S3 storage integration

5. **Report Generation Tests**
   - Test report generation with complete data
   - Test report generation with missing data
   - Test JSON export format
   - Test Markdown export format

### Property-Based Tests

Property-based tests will verify universal properties across all inputs using Hypothesis. Each test will run a minimum of 100 iterations with randomized inputs.

1. **Property Test: Solution Count Bounds**
   - Generate random agent responses
   - Verify arbitrator returns 1-3 solutions
   - **Feature: arbitrator-multi-solution-enhancements, Property 1: Solution count between 1 and 3**

2. **Property Test: Solution Ranking**
   - Generate random solutions with scores
   - Verify solutions are ranked by composite score descending
   - **Feature: arbitrator-multi-solution-enhancements, Property 2: Solutions ranked by composite score**

3. **Property Test: Composite Score Calculation**
   - Generate random individual scores
   - Verify composite score equals weighted average
   - **Feature: arbitrator-multi-solution-enhancements, Property 8: Composite score calculation**

4. **Property Test: Binding Constraint Satisfaction**
   - Generate random solutions and binding constraints
   - Verify all solutions satisfy all constraints
   - **Feature: arbitrator-multi-solution-enhancements, Property 5: Binding constraint satisfaction**

5. **Property Test: No Circular Dependencies**
   - Generate random recovery plans
   - Verify no circular dependency chains exist
   - **Feature: arbitrator-multi-solution-enhancements, Property 14: No circular dependencies**

6. **Property Test: Sequential Step Numbering**
   - Generate random recovery plans
   - Verify step numbers are sequential 1..N
   - **Feature: arbitrator-multi-solution-enhancements, Property 11: Sequential step numbering**

7. **Property Test: Human Override Flag**
   - Generate random decision records with various solution selections
   - Verify human_override flag matches selection vs recommendation
   - **Feature: arbitrator-multi-solution-enhancements, Property 19: Human override flag consistency**

8. **Property Test: S3 Key Format**
   - Generate random timestamps
   - Verify S3 keys match expected pattern
   - **Feature: arbitrator-multi-solution-enhancements, Property 17: S3 key format**

9. **Property Test: Backward Compatibility**
   - Generate random arbitrator outputs
   - Verify final_decision and recommendations match recommended solution
   - **Feature: arbitrator-multi-solution-enhancements, Property 24-25: Backward compatibility**

10. **Property Test: Valid Dependency References**
    - Generate random recovery steps with dependencies
    - Verify all dependency references are valid
    - **Feature: arbitrator-multi-solution-enhancements, Property 15: Valid dependency references**

### Integration Tests

1. **End-to-End Arbitration Flow**
   - Test complete flow from agent responses to arbitrator output
   - Verify all solution options are generated correctly
   - Verify recovery plans are complete and valid

2. **Solution Selection and S3 Storage**
   - Test API endpoint receives selection
   - Verify decision record is created correctly
   - Verify S3 storage to both buckets
   - Verify metadata is set correctly

3. **Report Generation and Export**
   - Test report generation from arbitrator output
   - Test export in all three formats (PDF, JSON, Markdown)
   - Verify report completeness

4. **Backward Compatibility**
   - Test that existing orchestrator integration still works
   - Verify legacy fields are populated correctly
   - Test that single-solution case works as before

### Test Configuration

All property-based tests will be configured with:

- Minimum 100 iterations per test
- Hypothesis deadline of 5000ms per example
- Shrinking enabled to find minimal failing examples
- Seed randomization for reproducibility

Test command:

```bash
cd skymarshal_agents_new/skymarshal
uv run pytest test/ -v --hypothesis-show-statistics
```
