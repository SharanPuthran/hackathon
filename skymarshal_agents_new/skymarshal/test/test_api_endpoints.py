"""
Unit tests for API endpoints module.

Tests the API endpoint functionality for solution selection including:
- Solution selection request handling
- Validation of disruption IDs and solution IDs
- S3 storage integration
- Error handling for invalid requests
- Disruption status retrieval
- Health check endpoint

Uses pytest and mocking to test without actual AWS services.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from agents.schemas import (
    ArbitratorOutput,
    RecoverySolution,
    RecoveryPlan,
    RecoveryStep,
    ConflictDetail,
    ResolutionDetail
)
from api.endpoints import (
    SolutionSelectionRequest,
    SolutionSelectionResponse,
    register_arbitrator_output,
    get_arbitrator_output,
    handle_solution_selection,
    get_disruption_status,
    health_check,
    _extract_flight_number,
    _extract_disruption_type
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_recovery_solution():
    """Create a sample recovery solution."""
    recovery_step = RecoveryStep(
        step_number=1,
        step_name="Notify Crew",
        description="Notify crew of schedule change",
        responsible_agent="crew_scheduling",
        dependencies=[],
        estimated_duration="15 minutes",
        automation_possible=True,
        action_type="notify",
        parameters={"crew_ids": ["C001", "C002"]},
        success_criteria="Crew acknowledged notification"
    )
    
    recovery_plan = RecoveryPlan(
        solution_id=1,
        total_steps=1,
        estimated_total_duration="15 minutes",
        steps=[recovery_step],
        critical_path=[1],
        contingency_plans=[]
    )
    
    return RecoverySolution(
        solution_id=1,
        title="Conservative Safety-First Approach",
        description="Delay flight to allow full crew rest",
        recommendations=["Delay flight 10 hours", "Arrange crew rest facilities"],
        safety_compliance="Full compliance with FDP regulations",
        passenger_impact={"affected_count": 180, "delay_hours": 10, "cancellation_flag": False},
        financial_impact={"total_cost": 180000, "breakdown": {"crew": 50000, "passenger": 130000}},
        network_impact={"downstream_flights": 3, "connection_misses": 12},
        safety_score=100.0,
        cost_score=40.0,
        passenger_score=55.0,
        network_score=50.0,
        composite_score=69.0,  # 100*0.4 + 40*0.2 + 55*0.2 + 50*0.2 = 69.0
        pros=["Full regulatory compliance", "Zero safety risk"],
        cons=["High cost", "Significant passenger impact"],
        risks=["Potential customer dissatisfaction"],
        confidence=0.95,
        estimated_duration="10 hours",
        recovery_plan=recovery_plan
    )


@pytest.fixture
def sample_arbitrator_output(sample_recovery_solution):
    """Create a sample arbitrator output with multiple solutions."""
    # Create second solution with higher score (will be ranked first)
    solution2 = sample_recovery_solution.model_copy()
    solution2.solution_id = 2
    solution2.title = "Crew Change with Minimal Delay"
    solution2.description = "Source replacement crew to minimize delay"
    solution2.safety_score = 95.0
    solution2.cost_score = 65.0
    solution2.passenger_score = 70.0
    solution2.network_score = 75.0
    solution2.composite_score = 72.0  # 95*0.4 + 65*0.2 + 70*0.2 + 75*0.2 = 72.0
    solution2.recovery_plan.solution_id = 2
    
    # Create third solution with lowest score
    solution3 = sample_recovery_solution.model_copy()
    solution3.solution_id = 3
    solution3.title = "Flight Cancellation"
    solution3.description = "Cancel flight and rebook all passengers"
    solution3.safety_score = 100.0
    solution3.cost_score = 30.0
    solution3.passenger_score = 40.0
    solution3.network_score = 45.0
    solution3.composite_score = 65.0  # 100*0.4 + 30*0.2 + 40*0.2 + 45*0.2 = 65.0
    solution3.recovery_plan.solution_id = 3
    
    # Order solutions by composite score (highest first): solution2 (72), solution1 (69), solution3 (65)
    return ArbitratorOutput(
        final_decision="Recommend crew change with minimal delay",
        recommendations=["Source replacement crew", "Minimize delay"],
        conflicts_identified=[
            ConflictDetail(
                conflict_id="C1",
                conflict_type="safety_vs_business",
                agents_involved=["crew_compliance", "network"],
                description="Crew rest requirement conflicts with network optimization",
                severity="high"
            )
        ],
        conflict_resolutions=[
            ResolutionDetail(
                conflict_description="Crew rest requirement conflicts with network optimization",
                resolution="Safety constraint takes priority",
                rationale="FDP regulations are non-negotiable"
            )
        ],
        safety_overrides=[],
        justification="Flight EY123 crew exceeds FDP limits. Crew change provides best balance.",
        reasoning="Crew has 13.5 hours duty time, exceeds 11-hour limit by 2.5 hours.",
        confidence=0.95,
        timestamp=datetime.now(timezone.utc).isoformat(),
        solution_options=[solution2, sample_recovery_solution, solution3],  # Ordered by score
        recommended_solution_id=2  # Highest score solution
    )


@pytest.fixture(autouse=True)
def clear_arbitrator_outputs():
    """Clear arbitrator outputs before each test."""
    from api.endpoints import _arbitrator_outputs
    _arbitrator_outputs.clear()
    yield
    _arbitrator_outputs.clear()


# ============================================================================
# Registration and Retrieval Tests
# ============================================================================

def test_register_and_get_arbitrator_output(sample_arbitrator_output):
    """
    Test registering and retrieving arbitrator output.
    
    Validates: Requirements 6.1-6.3
    """
    # Register output
    register_arbitrator_output("DISR-2026-001", sample_arbitrator_output)
    
    # Retrieve output
    retrieved = get_arbitrator_output("DISR-2026-001")
    
    # Verify it matches
    assert retrieved is not None
    assert retrieved.final_decision == sample_arbitrator_output.final_decision
    assert len(retrieved.solution_options) == 3
    assert retrieved.recommended_solution_id == 2


def test_get_nonexistent_arbitrator_output():
    """
    Test retrieving non-existent arbitrator output returns None.
    
    Validates: Requirements 6.3
    """
    retrieved = get_arbitrator_output("NONEXISTENT-ID")
    assert retrieved is None


# ============================================================================
# Solution Selection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_successful_solution_selection(sample_arbitrator_output):
    """
    Test successful solution selection flow.
    
    Validates: Requirements 6.1-6.4
    """
    # Register arbitrator output
    register_arbitrator_output("DISR-2026-001", sample_arbitrator_output)
    
    # Create selection request (select recommended solution)
    request = SolutionSelectionRequest(
        disruption_id="DISR-2026-001",
        selected_solution_id=2,  # Recommended solution
        rationale="Best balance of safety and cost"
    )
    
    # Mock S3 storage
    with patch('api.endpoints.store_decision_to_s3', new_callable=AsyncMock) as mock_store:
        mock_store.return_value = {
            "skymarshal-prod-knowledge-base-368613657554": True,
            "skymarshal-prod-decisions-368613657554": True
        }
        
        # Handle selection
        response = await handle_solution_selection(request)
        
        # Verify response
        assert response.status == "success"
        assert response.stored_to_buckets["skymarshal-prod-knowledge-base-368613657554"] is True
        assert response.stored_to_buckets["skymarshal-prod-decisions-368613657554"] is True
        
        # Verify store_decision_to_s3 was called
        assert mock_store.called
        decision_record = mock_store.call_args[0][0]
        assert decision_record.disruption_id == "DISR-2026-001"
        assert decision_record.selected_solution_id == 2
        assert decision_record.human_override is False  # Selected = recommended


@pytest.mark.asyncio
async def test_solution_selection_with_human_override(sample_arbitrator_output):
    """
    Test solution selection with human override (selected != recommended).
    
    Validates: Requirements 4.6, 6.4
    """
    # Register arbitrator output
    register_arbitrator_output("DISR-2026-001", sample_arbitrator_output)
    
    # Select different solution than recommended (recommended is 2, select 1)
    request = SolutionSelectionRequest(
        disruption_id="DISR-2026-001",
        selected_solution_id=1,  # Not the recommended solution (2)
        rationale="Lower cost is more important in this case"
    )
    
    # Mock S3 storage
    with patch('api.endpoints.store_decision_to_s3', new_callable=AsyncMock) as mock_store:
        mock_store.return_value = {
            "skymarshal-prod-knowledge-base-368613657554": True,
            "skymarshal-prod-decisions-368613657554": True
        }
        
        # Handle selection
        response = await handle_solution_selection(request)
        
        # Verify response
        assert response.status == "success"
        
        # Verify human_override flag is set
        decision_record = mock_store.call_args[0][0]
        assert decision_record.selected_solution_id == 1
        assert decision_record.recommended_solution_id == 2
        assert decision_record.human_override is True  # Selected != recommended


@pytest.mark.asyncio
async def test_solution_selection_disruption_not_found():
    """
    Test error handling when disruption ID not found.
    
    Validates: Requirements 6.8 (Property 21)
    """
    request = SolutionSelectionRequest(
        disruption_id="NONEXISTENT-ID",
        selected_solution_id=1,
        rationale="Test"
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="Disruption .* not found"):
        await handle_solution_selection(request)


@pytest.mark.asyncio
async def test_solution_selection_no_solution_options(sample_arbitrator_output):
    """
    Test error handling when arbitrator output has no solution options.
    
    Validates: Requirements 6.8 (Property 21)
    """
    # Create output without solution options (legacy mode)
    output = sample_arbitrator_output.model_copy()
    output.solution_options = None
    
    register_arbitrator_output("DISR-2026-001", output)
    
    request = SolutionSelectionRequest(
        disruption_id="DISR-2026-001",
        selected_solution_id=1,
        rationale="Test"
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="does not have solution options"):
        await handle_solution_selection(request)


@pytest.mark.asyncio
async def test_solution_selection_invalid_solution_id(sample_arbitrator_output):
    """
    Test error handling when selected solution ID is invalid.
    
    Validates: Requirements 6.8 (Property 21)
    """
    register_arbitrator_output("DISR-2026-001", sample_arbitrator_output)
    
    request = SolutionSelectionRequest(
        disruption_id="DISR-2026-001",
        selected_solution_id=99,  # Invalid ID
        rationale="Test"
    )
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="Invalid solution ID"):
        await handle_solution_selection(request)


@pytest.mark.asyncio
async def test_solution_selection_partial_storage_failure(sample_arbitrator_output):
    """
    Test handling of partial storage failure.
    
    Validates: Requirements 6.8
    """
    register_arbitrator_output("DISR-2026-001", sample_arbitrator_output)
    
    request = SolutionSelectionRequest(
        disruption_id="DISR-2026-001",
        selected_solution_id=1,
        rationale="Test"
    )
    
    # Mock partial storage failure
    with patch('api.endpoints.store_decision_to_s3', new_callable=AsyncMock) as mock_store:
        mock_store.return_value = {
            "skymarshal-prod-knowledge-base-368613657554": True,
            "skymarshal-prod-decisions-368613657554": False  # Failed
        }
        
        # Handle selection
        response = await handle_solution_selection(request)
        
        # Verify partial success status
        assert response.status == "partial_success"
        assert "some storage operations failed" in response.message.lower()


# ============================================================================
# Extraction Helper Tests
# ============================================================================

def test_extract_flight_number(sample_arbitrator_output):
    """
    Test flight number extraction from arbitrator output.
    
    Validates: Requirements 6.5
    """
    flight_number = _extract_flight_number(sample_arbitrator_output)
    assert flight_number == "EY123"


def test_extract_flight_number_no_match():
    """
    Test flight number extraction when no match found.
    
    Validates: Requirements 6.5
    """
    output = ArbitratorOutput(
        final_decision="Test decision",
        recommendations=["Manual review required"],
        conflicts_identified=[],
        conflict_resolutions=[],
        safety_overrides=[],
        justification="No flight number mentioned",
        reasoning="Test reasoning",
        confidence=0.5,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    flight_number = _extract_flight_number(output)
    assert flight_number == "UNKNOWN"


def test_extract_disruption_type(sample_arbitrator_output):
    """
    Test disruption type extraction from arbitrator output.
    
    Validates: Requirements 6.6
    """
    disruption_type = _extract_disruption_type(sample_arbitrator_output)
    assert disruption_type == "crew"


def test_extract_disruption_type_maintenance():
    """
    Test disruption type extraction for maintenance issues.
    
    Validates: Requirements 6.6
    """
    output = ArbitratorOutput(
        final_decision="Test decision",
        recommendations=["Conduct maintenance inspection"],
        conflicts_identified=[],
        conflict_resolutions=[],
        safety_overrides=[],
        justification="Aircraft requires maintenance inspection",
        reasoning="Mechanical failure detected",
        confidence=0.5,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    disruption_type = _extract_disruption_type(output)
    assert disruption_type == "maintenance"


# ============================================================================
# Disruption Status Tests
# ============================================================================

def test_get_disruption_status(sample_arbitrator_output):
    """
    Test retrieving disruption status.
    
    Validates: Requirements 6.7
    """
    register_arbitrator_output("DISR-2026-001", sample_arbitrator_output)
    
    status = get_disruption_status("DISR-2026-001")
    
    assert status["disruption_id"] == "DISR-2026-001"
    assert status["solution_count"] == 3
    assert status["recommended_solution_id"] == 2
    assert status["confidence"] == 0.95


def test_get_disruption_status_not_found():
    """
    Test error handling when disruption not found.
    
    Validates: Requirements 6.7
    """
    with pytest.raises(ValueError, match="Disruption .* not found"):
        get_disruption_status("NONEXISTENT-ID")


# ============================================================================
# Health Check Tests
# ============================================================================

def test_health_check():
    """
    Test health check endpoint.
    
    Validates: Requirements 6.7
    """
    result = health_check()
    
    assert result["status"] == "healthy"
    assert "timestamp" in result
    assert result["registered_disruptions"] == 0


def test_health_check_with_registered_disruptions(sample_arbitrator_output):
    """
    Test health check with registered disruptions.
    
    Validates: Requirements 6.7
    """
    register_arbitrator_output("DISR-2026-001", sample_arbitrator_output)
    register_arbitrator_output("DISR-2026-002", sample_arbitrator_output)
    
    result = health_check()
    
    assert result["status"] == "healthy"
    assert result["registered_disruptions"] == 2


# ============================================================================
# Request Validation Tests
# ============================================================================

def test_solution_selection_request_validation():
    """
    Test SolutionSelectionRequest validation.
    
    Validates: Requirements 6.2
    """
    # Valid request
    request = SolutionSelectionRequest(
        disruption_id="DISR-2026-001",
        selected_solution_id=1,
        rationale="Test rationale"
    )
    assert request.disruption_id == "DISR-2026-001"
    assert request.selected_solution_id == 1
    
    # Request without rationale (optional)
    request2 = SolutionSelectionRequest(
        disruption_id="DISR-2026-002",
        selected_solution_id=2
    )
    assert request2.rationale is None


def test_solution_selection_request_missing_fields():
    """
    Test SolutionSelectionRequest with missing required fields.
    
    Validates: Requirements 6.2
    """
    from pydantic import ValidationError
    
    # Missing disruption_id
    with pytest.raises(ValidationError):
        SolutionSelectionRequest(
            selected_solution_id=1,
            rationale="Test"
        )
    
    # Missing selected_solution_id
    with pytest.raises(ValidationError):
        SolutionSelectionRequest(
            disruption_id="DISR-2026-001",
            rationale="Test"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
