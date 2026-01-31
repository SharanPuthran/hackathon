"""Response aggregation utilities for SkyMarshal orchestrator"""

from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def aggregate_agent_responses(
    safety_results: List[Dict[str, Any]], business_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate responses from all agents into unified format.

    Args:
        safety_results: Results from safety agents (crew_compliance, maintenance, regulatory)
        business_results: Results from business agents (network, guest_experience, cargo, finance)

    Returns:
        dict: Unified response with safety constraints and business trade-offs
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "workflow_status": determine_status(safety_results),
        "safety_assessment": {
            "crew_compliance": extract_result(safety_results, "crew_compliance"),
            "maintenance": extract_result(safety_results, "maintenance"),
            "regulatory": extract_result(safety_results, "regulatory"),
            "blocking_constraints": extract_blocking_constraints(safety_results),
        },
        "business_assessment": {
            "network": extract_result(business_results, "network"),
            "guest_experience": extract_result(business_results, "guest_experience"),
            "cargo": extract_result(business_results, "cargo"),
            "finance": extract_result(business_results, "finance"),
            "impact_scores": calculate_impact_scores(business_results),
        },
        "recommendations": synthesize_recommendations(safety_results, business_results),
    }


def determine_status(safety_results: List[Dict[str, Any]]) -> str:
    """
    Determine if operation can proceed based on safety assessments.

    Args:
        safety_results: Results from safety agents

    Returns:
        str: "CAN_PROCEED_WITH_CONSTRAINTS" or "CANNOT_PROCEED"
    """
    for result in safety_results:
        if result.get("status") == "error":
            logger.warning(f"Safety agent {result.get('agent')} returned error")
            return "CANNOT_PROCEED"

        # Check if result contains blocking violations
        if has_blocking_violation(result):
            logger.warning(f"Blocking violation detected in {result.get('agent')}")
            return "CANNOT_PROCEED"

    return "CAN_PROCEED_WITH_CONSTRAINTS"


def extract_result(results: List[Dict[str, Any]], agent_name: str) -> Dict[str, Any]:
    """
    Extract result for a specific agent from results list.

    Args:
        results: List of agent results
        agent_name: Name of agent to extract

    Returns:
        dict: Agent result or empty dict if not found
    """
    for result in results:
        if result.get("agent") == agent_name:
            return result

    return {"agent": agent_name, "status": "not_found"}


def extract_blocking_constraints(
    safety_results: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Extract all blocking constraints from safety agents.

    Args:
        safety_results: Results from safety agents

    Returns:
        list: List of blocking constraints
    """
    constraints = []

    for result in safety_results:
        # Parse agent result for blocking constraints
        result_text = result.get("result", "")

        # Check for common blocking keywords
        if any(
            keyword in result_text.lower()
            for keyword in [
                "cannot proceed",
                "blocking",
                "critical",
                "safety violation",
                "unsafe",
                "prohibited",
            ]
        ):
            constraints.append(
                {
                    "agent": result.get("agent"),
                    "category": result.get("category"),
                    "constraint": result_text[:500],  # First 500 chars
                    "severity": "BLOCKING",
                }
            )

    return constraints


def has_blocking_violation(assessment: Dict[str, Any]) -> bool:
    """
    Check if assessment contains blocking constraints.

    Args:
        assessment: Agent assessment result

    Returns:
        bool: True if blocking violation detected
    """
    result_text = assessment.get("result", "")

    # Check for blocking keywords
    blocking_keywords = [
        "cannot proceed",
        "blocking constraint",
        "safety violation",
        "unsafe operation",
        "prohibited",
        "ftl violation",
        "crew unavailable",
        "aircraft aog",
        "airworthiness issue",
        "curfew violation",
    ]

    return any(keyword in result_text.lower() for keyword in blocking_keywords)


def calculate_impact_scores(business_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate impact scores from business assessments.

    Args:
        business_results: Results from business agents

    Returns:
        dict: Impact scores by category
    """
    # Placeholder for impact score calculation
    # In production, this would parse agent results and calculate numeric scores
    return {
        "passenger_impact": "MEDIUM",
        "network_impact": "HIGH",
        "cargo_impact": "LOW",
        "financial_impact": "MEDIUM",
        "overall_score": 65,  # Out of 100
    }


def synthesize_recommendations(
    safety_results: List[Dict[str, Any]], business_results: List[Dict[str, Any]]
) -> List[str]:
    """
    Synthesize recommendations from all agent assessments.

    Args:
        safety_results: Results from safety agents
        business_results: Results from business agents

    Returns:
        list: List of recommendations
    """
    recommendations = []

    # Check if operation can proceed
    if determine_status(safety_results) == "CANNOT_PROCEED":
        recommendations.append(
            "CRITICAL: Operation cannot proceed due to safety constraints"
        )
        recommendations.append(
            "Review blocking constraints and remediate before proceeding"
        )
    else:
        recommendations.append("Operation can proceed with constraints and mitigations")

    # Add agent-specific recommendations (placeholder)
    recommendations.append("Consider passenger rebooking options to minimize impact")
    recommendations.append(
        "Monitor network propagation and implement delay containment"
    )
    recommendations.append("Ensure cargo prioritization for time-sensitive shipments")

    return recommendations
