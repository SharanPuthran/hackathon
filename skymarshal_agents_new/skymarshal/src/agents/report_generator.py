"""
Report Generation Module

This module provides functions for generating comprehensive decision reports
from arbitrator outputs. Reports include all assessments, impacts, trade-offs,
and decision rationale for audit and regulatory compliance.

Key Features:
- Generate comprehensive decision reports
- Extract impact assessments by category
- Format reports for human readability
- Support multiple export formats (JSON, Markdown, PDF)
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from agents.schemas import (
    DecisionReport,
    ImpactAssessment,
    ArbitratorOutput,
    RecoverySolution
)

logger = logging.getLogger(__name__)


def generate_decision_report(
    arbitrator_output: ArbitratorOutput,
    disruption_id: str,
    flight_number: Optional[str] = None,
    disruption_type: Optional[str] = None
) -> DecisionReport:
    """
    Generate a comprehensive decision report from arbitrator output.
    
    This function creates a complete audit-ready report that includes:
    - Executive summary
    - All solution options with detailed analysis
    - Impact assessments by category
    - Conflict resolutions
    - Decision rationale and confidence
    
    Args:
        arbitrator_output: The arbitrator's decision output
        disruption_id: Unique identifier for the disruption
        flight_number: Flight number (optional, extracted if not provided)
        disruption_type: Type of disruption (optional, extracted if not provided)
        
    Returns:
        DecisionReport with complete analysis
        
    Example:
        >>> output = ArbitratorOutput(...)
        >>> report = generate_decision_report(
        ...     output,
        ...     disruption_id="DISR-2026-001",
        ...     flight_number="EY123",
        ...     disruption_type="crew"
        ... )
        >>> print(report.executive_summary)
    """
    # Extract flight number if not provided
    if not flight_number:
        flight_number = _extract_flight_number_from_output(arbitrator_output)
    
    # Extract disruption type if not provided
    if not disruption_type:
        disruption_type = _extract_disruption_type_from_output(arbitrator_output)
    
    # Generate executive summary
    executive_summary = _generate_executive_summary(
        arbitrator_output,
        flight_number,
        disruption_type
    )
    
    # Extract impact assessments
    impact_assessments = _extract_impact_assessments(arbitrator_output)
    
    # Generate solution comparison
    solution_comparison = _generate_solution_comparison(arbitrator_output)
    
    # Extract conflict analysis
    conflict_analysis = _extract_conflict_analysis(arbitrator_output)
    
    # Generate recommendations summary
    recommendations_summary = _generate_recommendations_summary(arbitrator_output)
    
    # Create decision report
    report = DecisionReport(
        report_id=f"RPT-{disruption_id}",
        disruption_id=disruption_id,
        flight_number=flight_number,
        disruption_type=disruption_type,
        timestamp=arbitrator_output.timestamp,
        executive_summary=executive_summary,
        solution_options=arbitrator_output.solution_options or [],
        recommended_solution_id=arbitrator_output.recommended_solution_id,
        impact_assessments=impact_assessments,
        conflict_resolutions=arbitrator_output.conflict_resolutions,
        solution_comparison=solution_comparison,
        conflict_analysis=conflict_analysis,
        recommendations_summary=recommendations_summary,
        confidence=arbitrator_output.confidence,
        justification=arbitrator_output.justification,
        reasoning=arbitrator_output.reasoning
    )
    
    logger.info(f"Generated decision report {report.report_id} for disruption {disruption_id}")
    
    return report


def _extract_flight_number_from_output(output: ArbitratorOutput) -> str:
    """Extract flight number from arbitrator output."""
    import re
    
    # Search in reasoning and justification
    text = (output.reasoning or "") + " " + (output.justification or "")
    pattern = r'\b[A-Z]{2}\d{3,4}\b'
    
    match = re.search(pattern, text)
    if match:
        return match.group(0)
    
    return "UNKNOWN"


def _extract_disruption_type_from_output(output: ArbitratorOutput) -> str:
    """Extract disruption type from arbitrator output."""
    text = ((output.reasoning or "") + " " + (output.justification or "")).lower()
    
    if "crew" in text or "fdp" in text or "duty" in text:
        return "crew"
    elif "maintenance" in text or "aircraft" in text or "mechanical" in text:
        return "maintenance"
    elif "weather" in text:
        return "weather"
    elif "regulatory" in text or "curfew" in text or "slot" in text:
        return "regulatory"
    else:
        return "other"


def _generate_executive_summary(
    output: ArbitratorOutput,
    flight_number: str,
    disruption_type: str
) -> str:
    """Generate executive summary for the report."""
    solution_count = len(output.solution_options) if output.solution_options else 0
    
    # Find recommended solution
    recommended = None
    if output.solution_options and output.recommended_solution_id:
        recommended = next(
            (s for s in output.solution_options if s.solution_id == output.recommended_solution_id),
            None
        )
    
    summary_parts = [
        f"Flight {flight_number} experienced a {disruption_type} disruption.",
        f"The arbitrator analyzed the situation and generated {solution_count} solution options.",
    ]
    
    if recommended:
        summary_parts.append(
            f"The recommended solution is '{recommended.title}' "
            f"(composite score: {recommended.composite_score:.1f}/100)."
        )
    
    summary_parts.append(
        f"Decision confidence: {output.confidence:.0%}."
    )
    
    return " ".join(summary_parts)


def _extract_impact_assessments(output: ArbitratorOutput) -> List[ImpactAssessment]:
    """Extract impact assessments from solution options."""
    assessments = []
    
    if not output.solution_options:
        return assessments
    
    # Get recommended solution for primary assessment
    recommended = next(
        (s for s in output.solution_options if s.solution_id == output.recommended_solution_id),
        output.solution_options[0] if output.solution_options else None
    )
    
    if not recommended:
        return assessments
    
    # Safety impact
    assessments.append(ImpactAssessment(
        category="safety",
        severity="low" if recommended.safety_score >= 90 else "medium" if recommended.safety_score >= 70 else "high",
        description=recommended.safety_compliance,
        affected_count=0,
        estimated_cost=0.0,
        mitigation_steps=[]
    ))
    
    # Passenger impact
    passenger_impact = recommended.passenger_impact
    assessments.append(ImpactAssessment(
        category="passenger",
        severity="high" if passenger_impact.get("cancellation_flag") else "medium" if passenger_impact.get("delay_hours", 0) > 4 else "low",
        description=f"{passenger_impact.get('affected_count', 0)} passengers affected, {passenger_impact.get('delay_hours', 0)} hour delay",
        affected_count=passenger_impact.get("affected_count", 0),
        estimated_cost=0.0,
        mitigation_steps=[]
    ))
    
    # Financial impact
    financial_impact = recommended.financial_impact
    assessments.append(ImpactAssessment(
        category="financial",
        severity="high" if financial_impact.get("total_cost", 0) > 150000 else "medium" if financial_impact.get("total_cost", 0) > 50000 else "low",
        description=f"Total cost: ${financial_impact.get('total_cost', 0):,.0f}",
        affected_count=0,
        estimated_cost=financial_impact.get("total_cost", 0),
        mitigation_steps=[]
    ))
    
    # Network impact
    network_impact = recommended.network_impact
    assessments.append(ImpactAssessment(
        category="network",
        severity="high" if network_impact.get("downstream_flights", 0) > 5 else "medium" if network_impact.get("downstream_flights", 0) > 2 else "low",
        description=f"{network_impact.get('downstream_flights', 0)} downstream flights affected, {network_impact.get('connection_misses', 0)} connection misses",
        affected_count=network_impact.get("downstream_flights", 0),
        estimated_cost=0.0,
        mitigation_steps=[]
    ))
    
    return assessments


def _generate_solution_comparison(output: ArbitratorOutput) -> Dict[str, Any]:
    """Generate solution comparison table."""
    if not output.solution_options:
        return {}
    
    comparison = {
        "solutions": [],
        "score_breakdown": {},
        "trade_offs": []
    }
    
    for solution in output.solution_options:
        comparison["solutions"].append({
            "solution_id": solution.solution_id,
            "title": solution.title,
            "composite_score": solution.composite_score,
            "safety_score": solution.safety_score,
            "cost_score": solution.cost_score,
            "passenger_score": solution.passenger_score,
            "network_score": solution.network_score,
            "estimated_duration": solution.estimated_duration,
            "confidence": solution.confidence
        })
    
    # Identify trade-offs
    if len(output.solution_options) >= 2:
        sol1 = output.solution_options[0]
        sol2 = output.solution_options[1]
        
        if sol1.safety_score > sol2.safety_score and sol1.cost_score < sol2.cost_score:
            comparison["trade_offs"].append(
                f"{sol1.title} prioritizes safety over cost compared to {sol2.title}"
            )
        
        if sol1.passenger_score > sol2.passenger_score and sol1.network_score < sol2.network_score:
            comparison["trade_offs"].append(
                f"{sol1.title} minimizes passenger impact at the expense of network disruption"
            )
    
    return comparison


def _extract_conflict_analysis(output: ArbitratorOutput) -> Dict[str, Any]:
    """Extract conflict analysis from arbitrator output."""
    analysis = {
        "total_conflicts": len(output.conflicts_identified),
        "conflicts_by_type": {},
        "resolution_summary": []
    }
    
    # Count conflicts by type
    for conflict in output.conflicts_identified:
        conflict_type = conflict.conflict_type
        if conflict_type not in analysis["conflicts_by_type"]:
            analysis["conflicts_by_type"][conflict_type] = 0
        analysis["conflicts_by_type"][conflict_type] += 1
    
    # Summarize resolutions
    for resolution in output.conflict_resolutions:
        analysis["resolution_summary"].append({
            "conflict": resolution.conflict_description,
            "resolution": resolution.resolution,
            "rationale": resolution.rationale
        })
    
    return analysis


def _generate_recommendations_summary(output: ArbitratorOutput) -> str:
    """Generate recommendations summary."""
    if not output.recommendations:
        return "No specific recommendations provided."
    
    summary_parts = [
        "Key recommendations:",
        *[f"- {rec}" for rec in output.recommendations[:5]]  # Limit to top 5
    ]
    
    return "\n".join(summary_parts)


def get_report_metadata(report: DecisionReport) -> Dict[str, Any]:
    """
    Extract metadata from a decision report.
    
    Args:
        report: The decision report
        
    Returns:
        Dict with report metadata
    """
    return {
        "report_id": report.report_id,
        "disruption_id": report.disruption_id,
        "flight_number": report.flight_number,
        "disruption_type": report.disruption_type,
        "timestamp": report.timestamp,
        "solution_count": len(report.solution_options),
        "recommended_solution_id": report.recommended_solution_id,
        "confidence": report.confidence
    }


def validate_report_completeness(report: DecisionReport) -> Dict[str, bool]:
    """
    Validate that a report contains all required sections.
    
    Args:
        report: The decision report to validate
        
    Returns:
        Dict mapping section names to completeness status
    """
    return {
        "executive_summary": bool(report.executive_summary),
        "solution_options": len(report.solution_options) > 0,
        "recommended_solution": report.recommended_solution_id is not None,
        "impact_assessments": len(report.impact_assessments) > 0,
        "conflict_resolutions": True,  # Optional
        "solution_comparison": bool(report.solution_comparison),
        "justification": bool(report.justification),
        "reasoning": bool(report.reasoning)
    }



# ============================================================================
# Report Export Functions
# ============================================================================

def export_report_json(report: DecisionReport) -> str:
    """
    Export decision report as JSON.
    
    Args:
        report: The decision report to export
        
    Returns:
        JSON string representation of the report
        
    Example:
        >>> report = DecisionReport(...)
        >>> json_str = export_report_json(report)
        >>> with open("report.json", "w") as f:
        ...     f.write(json_str)
    """
    import json
    
    # Convert to dict and serialize
    report_dict = report.model_dump()
    
    # Pretty print with indentation
    json_str = json.dumps(report_dict, indent=2, default=str)
    
    logger.info(f"Exported report {report.report_id} to JSON ({len(json_str)} bytes)")
    
    return json_str


def export_report_markdown(report: DecisionReport) -> str:
    """
    Export decision report as Markdown.
    
    Args:
        report: The decision report to export
        
    Returns:
        Markdown string representation of the report
        
    Example:
        >>> report = DecisionReport(...)
        >>> md_str = export_report_markdown(report)
        >>> with open("report.md", "w") as f:
        ...     f.write(md_str)
    """
    lines = []
    
    # Header
    lines.append(f"# Decision Report: {report.report_id}")
    lines.append("")
    lines.append(f"**Flight:** {report.flight_number}")
    lines.append(f"**Disruption ID:** {report.disruption_id}")
    lines.append(f"**Disruption Type:** {report.disruption_type}")
    lines.append(f"**Timestamp:** {report.timestamp}")
    lines.append(f"**Confidence:** {report.confidence:.0%}")
    lines.append("")
    
    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(report.executive_summary)
    lines.append("")
    
    # Solution Options
    if report.solution_options:
        lines.append("## Solution Options")
        lines.append("")
        
        for solution in report.solution_options:
            is_recommended = solution.solution_id == report.recommended_solution_id
            marker = " ⭐ **RECOMMENDED**" if is_recommended else ""
            
            lines.append(f"### Solution {solution.solution_id}: {solution.title}{marker}")
            lines.append("")
            lines.append(f"**Description:** {solution.description}")
            lines.append("")
            lines.append(f"**Composite Score:** {solution.composite_score:.1f}/100")
            lines.append(f"- Safety: {solution.safety_score:.1f}/100")
            lines.append(f"- Cost: {solution.cost_score:.1f}/100")
            lines.append(f"- Passenger: {solution.passenger_score:.1f}/100")
            lines.append(f"- Network: {solution.network_score:.1f}/100")
            lines.append("")
            lines.append(f"**Estimated Duration:** {solution.estimated_duration}")
            lines.append(f"**Confidence:** {solution.confidence:.0%}")
            lines.append("")
            
            # Pros
            if solution.pros:
                lines.append("**Pros:**")
                for pro in solution.pros:
                    lines.append(f"- {pro}")
                lines.append("")
            
            # Cons
            if solution.cons:
                lines.append("**Cons:**")
                for con in solution.cons:
                    lines.append(f"- {con}")
                lines.append("")
            
            # Risks
            if solution.risks:
                lines.append("**Risks:**")
                for risk in solution.risks:
                    lines.append(f"- {risk}")
                lines.append("")
            
            # Recommendations
            if solution.recommendations:
                lines.append("**Action Steps:**")
                for i, rec in enumerate(solution.recommendations, 1):
                    lines.append(f"{i}. {rec}")
                lines.append("")
    
    # Impact Assessments
    if report.impact_assessments:
        lines.append("## Impact Assessment")
        lines.append("")
        
        for assessment in report.impact_assessments:
            lines.append(f"### {assessment.category.title()} Impact")
            lines.append("")
            lines.append(f"**Severity:** {assessment.severity.upper()}")
            lines.append(f"**Description:** {assessment.description}")
            if assessment.affected_count > 0:
                lines.append(f"**Affected Count:** {assessment.affected_count}")
            if assessment.estimated_cost > 0:
                lines.append(f"**Estimated Cost:** ${assessment.estimated_cost:,.2f}")
            lines.append("")
    
    # Conflict Analysis
    if report.conflict_analysis:
        lines.append("## Conflict Analysis")
        lines.append("")
        
        total = report.conflict_analysis.get("total_conflicts", 0)
        lines.append(f"**Total Conflicts Identified:** {total}")
        lines.append("")
        
        if report.conflict_analysis.get("conflicts_by_type"):
            lines.append("**Conflicts by Type:**")
            for conflict_type, count in report.conflict_analysis["conflicts_by_type"].items():
                lines.append(f"- {conflict_type}: {count}")
            lines.append("")
        
        if report.conflict_analysis.get("resolution_summary"):
            lines.append("**Resolutions:**")
            for resolution in report.conflict_analysis["resolution_summary"]:
                lines.append(f"- **Conflict:** {resolution['conflict']}")
                lines.append(f"  **Resolution:** {resolution['resolution']}")
                lines.append(f"  **Rationale:** {resolution['rationale']}")
                lines.append("")
    
    # Solution Comparison
    if report.solution_comparison and report.solution_comparison.get("trade_offs"):
        lines.append("## Trade-off Analysis")
        lines.append("")
        for trade_off in report.solution_comparison["trade_offs"]:
            lines.append(f"- {trade_off}")
        lines.append("")
    
    # Justification
    lines.append("## Decision Justification")
    lines.append("")
    lines.append(report.justification)
    lines.append("")
    
    # Detailed Reasoning
    lines.append("## Detailed Reasoning")
    lines.append("")
    lines.append(report.reasoning)
    lines.append("")
    
    # Footer
    lines.append("---")
    lines.append(f"*Report generated at {report.timestamp}*")
    
    markdown_str = "\n".join(lines)
    
    logger.info(f"Exported report {report.report_id} to Markdown ({len(markdown_str)} bytes)")
    
    return markdown_str


def export_report_pdf(report: DecisionReport) -> bytes:
    """
    Export decision report as PDF.
    
    Note: This is a placeholder implementation. For production use, integrate
    a PDF generation library like ReportLab or WeasyPrint.
    
    Args:
        report: The decision report to export
        
    Returns:
        PDF bytes (currently returns Markdown as bytes as placeholder)
        
    Example:
        >>> report = DecisionReport(...)
        >>> pdf_bytes = export_report_pdf(report)
        >>> with open("report.pdf", "wb") as f:
        ...     f.write(pdf_bytes)
    """
    logger.warning(
        f"PDF export for report {report.report_id} is using placeholder implementation. "
        "For production, integrate a PDF generation library."
    )
    
    # Placeholder: Return Markdown as bytes
    # In production, use a library like:
    # - ReportLab: https://www.reportlab.com/
    # - WeasyPrint: https://weasyprint.org/
    # - pdfkit: https://github.com/JazzCore/python-pdfkit
    
    markdown_str = export_report_markdown(report)
    
    # Add PDF header comment
    pdf_placeholder = f"% PDF Placeholder - Convert this Markdown to PDF\n\n{markdown_str}"
    
    return pdf_placeholder.encode('utf-8')


def export_report(
    report: DecisionReport,
    format: str = "json",
    output_path: Optional[str] = None
) -> str:
    """
    Export decision report in specified format.
    
    Args:
        report: The decision report to export
        format: Export format - "json", "markdown", or "pdf"
        output_path: Optional file path to write to
        
    Returns:
        Exported content as string (or path if output_path provided)
        
    Raises:
        ValueError: If format is not supported
        
    Example:
        >>> report = DecisionReport(...)
        >>> # Export to string
        >>> json_str = export_report(report, format="json")
        >>> # Export to file
        >>> export_report(report, format="markdown", output_path="report.md")
    """
    # Validate format
    valid_formats = ["json", "markdown", "md", "pdf"]
    if format.lower() not in valid_formats:
        raise ValueError(
            f"Unsupported format: {format}. "
            f"Valid formats: {', '.join(valid_formats)}"
        )
    
    # Export based on format
    if format.lower() == "json":
        content = export_report_json(report)
        mode = "w"
    elif format.lower() in ["markdown", "md"]:
        content = export_report_markdown(report)
        mode = "w"
    elif format.lower() == "pdf":
        content = export_report_pdf(report)
        mode = "wb"
    else:
        raise ValueError(f"Unsupported format: {format}")
    
    # Write to file if path provided
    if output_path:
        write_mode = mode
        if isinstance(content, bytes):
            with open(output_path, write_mode) as f:
                f.write(content)
        else:
            with open(output_path, write_mode, encoding='utf-8') as f:
                f.write(content)
        
        logger.info(f"Exported report {report.report_id} to {output_path}")
        return output_path
    
    # Return content as string
    if isinstance(content, bytes):
        return content.decode('utf-8')
    return content
