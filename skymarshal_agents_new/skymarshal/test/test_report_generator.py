"""
Tests for Report Generation Module

This module tests the report generation functionality including:
- Report generation from arbitrator output
- Impact assessment extraction
- Solution comparison generation
- Report export in multiple formats (JSON, Markdown, PDF)
- Report validation and completeness checking
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from agents.schemas import (
    ArbitratorOutput,
    RecoverySolution,
    RecoveryPlan,
    RecoveryStep,
    ConflictDetail,
    ResolutionDetail,
    DecisionReport,
    ImpactAssessment
)
from agents.report_generator import (
    generate_decision_report,
    get_report_metadata,
    validate_report_completeness,
    export_report_json,
    export_report_markdown,
    export_report_pdf,
    export_report
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_recovery_plan() -> RecoveryPlan:
    """Create a sample recovery plan for testing."""
    return RecoveryPlan(
        solution_id=1,
        total_steps=3,
        estimated_total_duration="30 minutes",
        steps=[
            RecoveryStep(
                step_number=1,
                step_name="Contact Standby Crew",
                description="Contact standby crew members for assignment",
                responsible_agent="crew_scheduling",
                estimated_duration="15 minutes",
                dependencies=[],
                automation_possible=True,
                action_type="notify",
                parameters={"crew_type": "standby"},
                success_criteria="Crew contacted and confirmed availability",
                rollback_procedure="Cancel crew assignment"
            ),
            RecoveryStep(
                step_number=2,
                step_name="Assign Replacement Crew",
                description="Assign replacement crew to flight",
                responsible_agent="crew_scheduling",
                estimated_duration="10 minutes",
                dependencies=[1],
                automation_possible=True,
                action_type="schedule",
                parameters={"flight_number": "EY123"},
                success_criteria="Crew assigned in system",
                rollback_procedure="Revert to original crew"
            ),
            RecoveryStep(
                step_number=3,
                step_name="Update Flight Manifest",
                description="Update flight manifest with new crew",
                responsible_agent="operations",
                estimated_duration="5 minutes",
                dependencies=[2],
                automation_possible=True,
                action_type="coordinate",
                parameters={"manifest_id": "M123"},
                success_criteria="Manifest updated and verified",
                rollback_procedure="Restore original manifest"
            )
        ],
        critical_path=[1, 2, 3],
        contingency_plans=[
            {"scenario": "Standby crew unavailable", "action": "Delay flight by 2 hours"}
        ]
    )


@pytest.fixture
def sample_solution(sample_recovery_plan: RecoveryPlan) -> RecoverySolution:
    """Create a sample recovery solution for testing."""
    return RecoverySolution(
        solution_id=1,
        title="Assign Standby Crew",
        description="Use standby crew to replace fatigued crew members",
        safety_score=95.0,
        cost_score=80.0,
        passenger_score=85.0,
        network_score=90.0,
        composite_score=89.0,
        safety_compliance="All crew rest requirements met with 2-hour margin",
        passenger_impact={
            "affected_count": 180,
            "delay_hours": 1.5,
            "cancellation_flag": False,
            "rebooking_required": False
        },
        financial_impact={
            "crew_costs": 5000.0,
            "passenger_compensation": 2000.0,
            "operational_costs": 3000.0,
            "total_cost": 10000.0
        },
        network_impact={
            "downstream_flights": 2,
            "connection_misses": 5,
            "recovery_time": "2 hours"
        },
        estimated_duration="30 minutes",
        confidence=0.92,
        pros=[
            "Minimal passenger impact",
            "Quick resolution",
            "No cancellations required"
        ],
        cons=[
            "Additional crew costs",
            "Slight delay to departure"
        ],
        risks=[
            "Standby crew may not be immediately available",
            "Weather could cause further delays"
        ],
        recommendations=[
            "Contact standby crew immediately",
            "Prepare passenger communication",
            "Monitor weather conditions"
        ],
        recovery_plan=sample_recovery_plan
    )


@pytest.fixture
def sample_arbitrator_output(sample_solution: RecoverySolution) -> ArbitratorOutput:
    """Create a sample arbitrator output for testing."""
    solution2 = RecoverySolution(
        solution_id=2,
        title="Delay Flight 4 Hours",
        description="Delay flight to allow current crew to rest",
        safety_score=98.0,
        cost_score=60.0,
        passenger_score=50.0,
        network_score=40.0,
        composite_score=69.0,
        safety_compliance="All crew rest requirements met with 4-hour margin",
        passenger_impact={
            "affected_count": 180,
            "delay_hours": 4.0,
            "cancellation_flag": False,
            "rebooking_required": True
        },
        financial_impact={
            "crew_costs": 0.0,
            "passenger_compensation": 15000.0,
            "operational_costs": 8000.0,
            "total_cost": 23000.0
        },
        network_impact={
            "downstream_flights": 5,
            "connection_misses": 20,
            "recovery_time": "6 hours"
        },
        estimated_duration="4 hours",
        confidence=0.95,
        pros=["Maximum safety margin", "No crew costs"],
        cons=["Significant passenger impact", "High compensation costs"],
        risks=["Passenger dissatisfaction", "Network disruption"],
        recommendations=["Arrange hotel accommodations", "Rebook connecting passengers"],
        recovery_plan=RecoveryPlan(
            solution_id=2,
            total_steps=1,
            estimated_total_duration="4 hours",
            steps=[
                RecoveryStep(
                    step_number=1,
                    step_name="Delay Flight",
                    description="Delay flight to allow crew rest",
                    responsible_agent="operations",
                    estimated_duration="4 hours",
                    dependencies=[],
                    automation_possible=False,
                    action_type="schedule",
                    parameters={"delay_hours": 4},
                    success_criteria="Flight rescheduled"
                )
            ],
            critical_path=[1],
            contingency_plans=[]
        )
    )
    
    return ArbitratorOutput(
        final_decision="Assign standby crew to replace fatigued crew members",
        recommendations=[
            "Contact standby crew immediately",
            "Prepare passenger communication",
            "Monitor weather conditions",
            "Update flight manifest"
        ],
        conflicts_identified=[
            ConflictDetail(
                conflict_type="safety_vs_business",
                agents_involved=["crew_compliance", "finance"],
                description="Crew compliance requires standby crew, finance prefers delay"
            )
        ],
        conflict_resolutions=[
            ResolutionDetail(
                conflict_description="Crew compliance requires standby crew, finance prefers delay",
                resolution="Prioritize safety and passenger experience over cost",
                rationale="Safety is non-negotiable, and passenger impact is significant with 4-hour delay",
                agents_affected=["crew_compliance", "finance"]
            )
        ],
        confidence=0.92,
        reasoning="Flight EY123 crew has exceeded FDP limits. Two viable solutions: "
                  "assign standby crew (fast, moderate cost) or delay 4 hours (slow, high cost). "
                  "Standby crew option provides best balance of safety, cost, and passenger experience.",
        justification="Standby crew assignment satisfies all safety requirements while minimizing "
                     "passenger impact and network disruption. The additional crew cost is justified "
                     "by avoiding significant passenger compensation and network recovery costs.",
        timestamp=datetime(2026, 2, 1, 10, 30, 0).isoformat(),
        solution_options=[sample_solution, solution2],
        recommended_solution_id=1
    )


# ============================================================================
# Report Generation Tests
# ============================================================================

def test_generate_decision_report_basic(sample_arbitrator_output: ArbitratorOutput):
    """Test basic report generation with all required fields."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    assert report.report_id == "RPT-DISR-2026-001"
    assert report.disruption_id == "DISR-2026-001"
    assert report.flight_number == "EY123"
    assert report.disruption_type == "crew"
    assert report.timestamp == sample_arbitrator_output.timestamp
    assert report.confidence == sample_arbitrator_output.confidence
    assert len(report.solution_options) == 2
    assert report.recommended_solution_id == 1


def test_generate_decision_report_executive_summary(sample_arbitrator_output: ArbitratorOutput):
    """Test executive summary generation."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    assert "EY123" in report.executive_summary
    assert "crew" in report.executive_summary
    assert "2 solution options" in report.executive_summary
    assert "Assign Standby Crew" in report.executive_summary
    assert "89.0/100" in report.executive_summary or "89.0" in report.executive_summary
    assert "92%" in report.executive_summary


def test_generate_decision_report_impact_assessments(sample_arbitrator_output: ArbitratorOutput):
    """Test impact assessment extraction."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    # Should have assessments for safety, passenger, financial, network
    assert len(report.impact_assessments) >= 4
    
    categories = [a.category for a in report.impact_assessments]
    assert "safety" in categories
    assert "passenger" in categories
    assert "financial" in categories
    assert "network" in categories
    
    # Check passenger assessment details
    passenger_assessment = next(a for a in report.impact_assessments if a.category == "passenger")
    assert passenger_assessment.affected_count == 180
    assert "180 passengers" in passenger_assessment.description


def test_generate_decision_report_solution_comparison(sample_arbitrator_output: ArbitratorOutput):
    """Test solution comparison generation."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    assert report.solution_comparison is not None
    assert "solutions" in report.solution_comparison
    assert len(report.solution_comparison["solutions"]) == 2
    
    # Check first solution details
    sol1 = report.solution_comparison["solutions"][0]
    assert sol1["solution_id"] == 1
    assert sol1["title"] == "Assign Standby Crew"
    assert sol1["composite_score"] == 89.0
    assert sol1["safety_score"] == 95.0


def test_generate_decision_report_conflict_analysis(sample_arbitrator_output: ArbitratorOutput):
    """Test conflict analysis extraction."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    assert report.conflict_analysis is not None
    assert report.conflict_analysis["total_conflicts"] == 1
    assert "safety_vs_business" in report.conflict_analysis["conflicts_by_type"]
    assert report.conflict_analysis["conflicts_by_type"]["safety_vs_business"] == 1
    
    # Check resolution summary
    assert len(report.conflict_analysis["resolution_summary"]) == 1
    resolution = report.conflict_analysis["resolution_summary"][0]
    assert "crew" in resolution["conflict"].lower()
    assert "safety" in resolution["rationale"].lower()


def test_generate_decision_report_flight_extraction(sample_arbitrator_output: ArbitratorOutput):
    """Test automatic flight number extraction from reasoning."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001"
        # No flight_number or disruption_type provided
    )
    
    # Should extract EY123 from reasoning text
    assert report.flight_number == "EY123"
    assert report.disruption_type == "crew"


def test_generate_decision_report_missing_data():
    """Test report generation with minimal arbitrator output."""
    minimal_output = ArbitratorOutput(
        final_decision="Cancel flight",
        recommendations=["Rebook passengers"],
        conflicts_identified=[],
        conflict_resolutions=[],
        confidence=0.8,
        reasoning="Insufficient crew available",
        justification="No viable alternatives",
        timestamp=datetime(2026, 2, 1, 10, 30, 0).isoformat(),
        solution_options=None,
        recommended_solution_id=None
    )
    
    report = generate_decision_report(
        arbitrator_output=minimal_output,
        disruption_id="DISR-2026-002",
        flight_number="EY456",
        disruption_type="crew"
    )
    
    assert report.report_id == "RPT-DISR-2026-002"
    assert len(report.solution_options) == 0
    assert report.recommended_solution_id is None
    assert "0 solution options" in report.executive_summary


# ============================================================================
# Report Metadata and Validation Tests
# ============================================================================

def test_get_report_metadata(sample_arbitrator_output: ArbitratorOutput):
    """Test report metadata extraction."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    metadata = get_report_metadata(report)
    
    assert metadata["report_id"] == "RPT-DISR-2026-001"
    assert metadata["disruption_id"] == "DISR-2026-001"
    assert metadata["flight_number"] == "EY123"
    assert metadata["disruption_type"] == "crew"
    assert metadata["solution_count"] == 2
    assert metadata["recommended_solution_id"] == 1
    assert metadata["confidence"] == 0.92


def test_validate_report_completeness_complete(sample_arbitrator_output: ArbitratorOutput):
    """Test validation of complete report."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    validation = validate_report_completeness(report)
    
    assert validation["executive_summary"] is True
    assert validation["solution_options"] is True
    assert validation["recommended_solution"] is True
    assert validation["impact_assessments"] is True
    assert validation["solution_comparison"] is True
    assert validation["justification"] is True
    assert validation["reasoning"] is True


def test_validate_report_completeness_incomplete():
    """Test validation of incomplete report."""
    minimal_output = ArbitratorOutput(
        final_decision="Cancel flight",
        recommendations=["Rebook passengers"],  # At least one recommendation required
        conflicts_identified=[],
        conflict_resolutions=[],
        confidence=0.8,
        reasoning="Insufficient crew available",
        justification="No viable alternatives",
        timestamp=datetime(2026, 2, 1, 10, 30, 0).isoformat(),
        solution_options=None,
        recommended_solution_id=None
    )
    
    report = generate_decision_report(
        arbitrator_output=minimal_output,
        disruption_id="DISR-2026-002",
        flight_number="EY456",
        disruption_type="crew"
    )
    
    validation = validate_report_completeness(report)
    
    assert validation["solution_options"] is False
    assert validation["recommended_solution"] is False
    # reasoning and justification are present, so they should be True
    assert validation["reasoning"] is True
    assert validation["justification"] is True


# ============================================================================
# Report Export Tests
# ============================================================================

def test_export_report_json(sample_arbitrator_output: ArbitratorOutput):
    """Test JSON export format."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    json_str = export_report_json(report)
    
    # Should be valid JSON
    import json
    parsed = json.loads(json_str)
    
    assert parsed["report_id"] == "RPT-DISR-2026-001"
    assert parsed["disruption_id"] == "DISR-2026-001"
    assert parsed["flight_number"] == "EY123"
    assert len(parsed["solution_options"]) == 2
    assert parsed["recommended_solution_id"] == 1


def test_export_report_markdown(sample_arbitrator_output: ArbitratorOutput):
    """Test Markdown export format."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    md_str = export_report_markdown(report)
    
    # Check for key sections
    assert "# Decision Report: RPT-DISR-2026-001" in md_str
    assert "## Executive Summary" in md_str
    assert "## Solution Options" in md_str
    assert "## Impact Assessment" in md_str
    assert "## Conflict Analysis" in md_str
    assert "## Decision Justification" in md_str
    
    # Check for solution details
    assert "### Solution 1: Assign Standby Crew" in md_str
    assert "⭐ **RECOMMENDED**" in md_str
    assert "**Composite Score:** 89.0/100" in md_str
    
    # Check for impact assessments
    assert "### Safety Impact" in md_str
    assert "### Passenger Impact" in md_str
    assert "### Financial Impact" in md_str
    assert "### Network Impact" in md_str


def test_export_report_pdf(sample_arbitrator_output: ArbitratorOutput):
    """Test PDF export (placeholder implementation)."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    pdf_bytes = export_report_pdf(report)
    
    # Should return bytes
    assert isinstance(pdf_bytes, bytes)
    
    # Placeholder returns Markdown as bytes
    pdf_str = pdf_bytes.decode('utf-8')
    assert "PDF Placeholder" in pdf_str
    assert "Decision Report: RPT-DISR-2026-001" in pdf_str


def test_export_report_unified_json(sample_arbitrator_output: ArbitratorOutput):
    """Test unified export function with JSON format."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    json_str = export_report(report, format="json")
    
    import json
    parsed = json.loads(json_str)
    assert parsed["report_id"] == "RPT-DISR-2026-001"


def test_export_report_unified_markdown(sample_arbitrator_output: ArbitratorOutput):
    """Test unified export function with Markdown format."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    md_str = export_report(report, format="markdown")
    
    assert "# Decision Report: RPT-DISR-2026-001" in md_str


def test_export_report_unified_invalid_format(sample_arbitrator_output: ArbitratorOutput):
    """Test unified export function with invalid format."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    with pytest.raises(ValueError, match="Unsupported format"):
        export_report(report, format="xml")


def test_export_report_to_file(sample_arbitrator_output: ArbitratorOutput, tmp_path):
    """Test exporting report to file."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    # Export JSON to file
    json_path = tmp_path / "report.json"
    result = export_report(report, format="json", output_path=str(json_path))
    
    assert result == str(json_path)
    assert json_path.exists()
    
    # Verify file content
    import json
    with open(json_path, 'r') as f:
        parsed = json.load(f)
    assert parsed["report_id"] == "RPT-DISR-2026-001"
    
    # Export Markdown to file
    md_path = tmp_path / "report.md"
    result = export_report(report, format="markdown", output_path=str(md_path))
    
    assert result == str(md_path)
    assert md_path.exists()
    
    # Verify file content
    with open(md_path, 'r') as f:
        content = f.read()
    assert "# Decision Report: RPT-DISR-2026-001" in content


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_report_with_no_conflicts():
    """Test report generation with no conflicts."""
    output = ArbitratorOutput(
        final_decision="Proceed with flight",
        recommendations=["Monitor weather"],
        conflicts_identified=[],
        conflict_resolutions=[],
        confidence=0.95,
        reasoning="All systems normal",
        justification="No issues detected",
        timestamp=datetime(2026, 2, 1, 10, 30, 0).isoformat(),
        solution_options=None,
        recommended_solution_id=None
    )
    
    report = generate_decision_report(
        arbitrator_output=output,
        disruption_id="DISR-2026-003",
        flight_number="EY789",
        disruption_type="none"
    )
    
    assert report.conflict_analysis["total_conflicts"] == 0
    assert len(report.conflict_analysis["conflicts_by_type"]) == 0
    assert len(report.conflict_analysis["resolution_summary"]) == 0


def test_report_with_trade_offs(sample_arbitrator_output: ArbitratorOutput):
    """Test trade-off analysis in solution comparison."""
    report = generate_decision_report(
        arbitrator_output=sample_arbitrator_output,
        disruption_id="DISR-2026-001",
        flight_number="EY123",
        disruption_type="crew"
    )
    
    # Should identify trade-offs between solutions
    assert "trade_offs" in report.solution_comparison
    trade_offs = report.solution_comparison["trade_offs"]
    
    # Should have at least one trade-off identified
    assert len(trade_offs) > 0


def test_report_recommendations_summary_truncation():
    """Test that recommendations summary is truncated to top 5."""
    output = ArbitratorOutput(
        final_decision="Complex recovery",
        recommendations=[
            "Step 1",
            "Step 2",
            "Step 3",
            "Step 4",
            "Step 5",
            "Step 6",
            "Step 7",
            "Step 8"
        ],
        conflicts_identified=[],
        conflict_resolutions=[],
        confidence=0.85,
        reasoning="Complex situation",
        justification="Multiple steps required",
        timestamp=datetime(2026, 2, 1, 10, 30, 0).isoformat(),
        solution_options=None,
        recommended_solution_id=None
    )
    
    report = generate_decision_report(
        arbitrator_output=output,
        disruption_id="DISR-2026-004",
        flight_number="EY999",
        disruption_type="complex"
    )
    
    # Should only include top 5 recommendations
    lines = report.recommendations_summary.split('\n')
    recommendation_lines = [l for l in lines if l.startswith('- ')]
    assert len(recommendation_lines) == 5
