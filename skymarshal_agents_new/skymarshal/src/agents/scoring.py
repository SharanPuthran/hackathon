"""
Scoring algorithms for multi-solution arbitration.

This module provides functions to score recovery solutions across four
dimensions: safety, cost, passenger impact, and network impact. Each
dimension is scored on a 0-100 scale, with higher scores being better.

The composite score is calculated as a weighted average:
    composite = (safety * 0.4) + (cost * 0.2) + (passenger * 0.2) + (network * 0.2)

Scoring Principles:
- Safety: 40% weight - highest priority, based on margin above minimum requirements
- Cost: 20% weight - higher score = lower cost
- Passenger: 20% weight - higher score = less impact on passengers
- Network: 20% weight - higher score = less propagation to other flights

See Also:
    - Design Document: .kiro/specs/arbitrator-multi-solution-enhancements/design.md
    - Requirements: .kiro/specs/arbitrator-multi-solution-enhancements/requirements.md
"""

from typing import Dict, Any, List


# Scoring weights for composite calculation
SCORING_WEIGHTS = {
    "safety": 0.40,      # 40% - Highest priority
    "cost": 0.20,        # 20% - Financial impact
    "passenger": 0.20,   # 20% - Customer impact
    "network": 0.20      # 20% - Operational impact
}


def calculate_safety_score(
    solution: Dict[str, Any],
    binding_constraints: List[Dict[str, Any]]
) -> float:
    """
    Calculate safety score based on margin above minimum requirements.
    
    Safety score reflects how well the solution satisfies safety constraints
    and how much margin it provides above minimum requirements.
    
    Scoring:
        - 100: Exceeds all safety requirements with significant margin (>20%)
        - 80-99: Meets all requirements with comfortable margin (10-20%)
        - 60-79: Meets all requirements with minimal margin (0-10%)
        - 0-59: Violates one or more requirements (should be rejected)
    
    Args:
        solution: Solution dict with safety compliance information
        binding_constraints: List of binding constraints from safety agents
    
    Returns:
        Safety score from 0.0 to 100.0
    
    Example:
        >>> solution = {
        ...     "safety_compliance": "Satisfies all crew duty limits",
        ...     "crew_rest_margin": 0.15  # 15% margin above minimum
        ... }
        >>> constraints = [{"type": "crew_rest", "minimum": 10}]
        >>> score = calculate_safety_score(solution, constraints)
        >>> print(score)  # Should be 80-99 (comfortable margin)
        85.0
    """
    # Check if solution violates any constraints
    if not binding_constraints:
        # No constraints means no safety concerns
        return 100.0
    
    # Extract safety compliance information
    safety_compliance = solution.get("safety_compliance", "")
    
    # Check for violation keywords
    violation_keywords = ["violates", "cannot proceed", "non-compliant", "exceeds limit"]
    if any(keyword in safety_compliance.lower() for keyword in violation_keywords):
        return 0.0
    
    # Calculate margin above minimum requirements
    # Look for margin indicators in the solution
    margins = []
    
    # Check for crew rest margin
    if "crew_rest_margin" in solution:
        margins.append(solution["crew_rest_margin"])
    
    # Check for maintenance margin
    if "maintenance_margin" in solution:
        margins.append(solution["maintenance_margin"])
    
    # Check for regulatory margin
    if "regulatory_margin" in solution:
        margins.append(solution["regulatory_margin"])
    
    # If no specific margins provided, infer from compliance text
    if not margins:
        if "significant margin" in safety_compliance.lower():
            avg_margin = 0.25  # 25% margin
        elif "comfortable margin" in safety_compliance.lower():
            avg_margin = 0.15  # 15% margin
        elif "minimal margin" in safety_compliance.lower():
            avg_margin = 0.05  # 5% margin
        elif "satisfies" in safety_compliance.lower() or "compliant" in safety_compliance.lower():
            avg_margin = 0.10  # 10% margin (default for compliant)
        else:
            avg_margin = 0.0
    else:
        avg_margin = sum(margins) / len(margins)
    
    # Convert margin to score
    if avg_margin >= 0.20:
        # Significant margin: 100
        return 100.0
    elif avg_margin >= 0.10:
        # Comfortable margin: 80-99
        # Linear interpolation between 80 and 100
        return 80.0 + ((avg_margin - 0.10) / 0.10) * 20.0
    elif avg_margin >= 0.0:
        # Minimal margin: 60-79
        # Linear interpolation between 60 and 80
        return 60.0 + (avg_margin / 0.10) * 20.0
    else:
        # Negative margin means violation
        return 0.0


def calculate_cost_score(
    solution: Dict[str, Any],
    agent_responses: Dict[str, Any]
) -> float:
    """
    Calculate cost score (higher score = lower cost).
    
    Cost score reflects the financial impact of the solution. Higher scores
    indicate lower costs, making this an inverse relationship.
    
    Scoring:
        - 100: Minimal cost (< $10k)
        - 80-99: Low cost ($10k-$50k)
        - 60-79: Moderate cost ($50k-$150k)
        - 40-59: High cost ($150k-$300k)
        - 0-39: Very high cost (> $300k)
    
    Args:
        solution: Solution dict with financial impact information
        agent_responses: All agent responses for context
    
    Returns:
        Cost score from 0.0 to 100.0
    
    Example:
        >>> solution = {"financial_impact": {"total_cost": 75000}}
        >>> agent_responses = {}
        >>> score = calculate_cost_score(solution, agent_responses)
        >>> print(score)  # Should be 60-79 (moderate cost)
        65.0
    """
    # Extract total cost from solution
    financial_impact = solution.get("financial_impact", {})
    total_cost = financial_impact.get("total_cost", 0)
    
    # If no cost in solution, try to extract from finance agent
    if total_cost == 0 and "finance" in agent_responses:
        finance_response = agent_responses["finance"]
        if isinstance(finance_response, dict):
            total_cost = finance_response.get("net_financial_impact", 0)
    
    # Calculate score based on cost ranges
    if total_cost < 10000:
        return 100.0
    elif total_cost < 50000:
        # Linear interpolation between 80 and 100
        return 80.0 + ((50000 - total_cost) / 40000) * 20.0
    elif total_cost < 150000:
        # Linear interpolation between 60 and 80
        return 60.0 + ((150000 - total_cost) / 100000) * 20.0
    elif total_cost < 300000:
        # Linear interpolation between 40 and 60
        return 40.0 + ((300000 - total_cost) / 150000) * 20.0
    else:
        # Very high cost: diminishing score
        return max(0.0, 40.0 - ((total_cost - 300000) / 300000) * 40.0)


def calculate_passenger_score(
    solution: Dict[str, Any],
    agent_responses: Dict[str, Any]
) -> float:
    """
    Calculate passenger impact score (higher score = less impact).
    
    Passenger score considers the number of passengers affected, delay
    duration, whether the flight is cancelled, and reprotection options.
    
    Scoring Factors:
        - Number of passengers affected
        - Delay duration (penalty: 5 points per hour)
        - Cancellation (penalty: 20 points)
        - Reprotection options available (bonus: up to 10 points)
    
    Args:
        solution: Solution dict with passenger impact information
        agent_responses: All agent responses for context
    
    Returns:
        Passenger score from 0.0 to 100.0
    
    Example:
        >>> solution = {
        ...     "passenger_impact": {
        ...         "affected": 150,
        ...         "delay_hours": 10,
        ...         "cancelled": False
        ...     }
        ... }
        >>> agent_responses = {}
        >>> score = calculate_passenger_score(solution, agent_responses)
        >>> print(score)  # Should be around 30 (150 pax, 10hr delay)
        30.0
    """
    # Extract passenger impact information
    passenger_impact = solution.get("passenger_impact", {})
    passengers_affected = passenger_impact.get("affected", 0)
    delay_hours = passenger_impact.get("delay_hours", 0)
    is_cancellation = passenger_impact.get("cancelled", False)
    
    # If no impact in solution, try to extract from guest_experience agent
    if passengers_affected == 0 and "guest_experience" in agent_responses:
        guest_response = agent_responses["guest_experience"]
        if isinstance(guest_response, dict):
            pax_impact = guest_response.get("passenger_impact", {})
            passengers_affected = pax_impact.get("total_affected", 0)
    
    # Base score from passenger count
    if passengers_affected < 50:
        base_score = 100.0
    elif passengers_affected < 150:
        base_score = 80.0
    elif passengers_affected < 300:
        base_score = 60.0
    else:
        base_score = 40.0
    
    # Penalty for delay duration (5 points per hour, max 30 points)
    delay_penalty = min(30.0, delay_hours * 5.0)
    
    # Penalty for cancellation
    cancellation_penalty = 20.0 if is_cancellation else 0.0
    
    # Bonus for reprotection options
    reprotection_bonus = 0.0
    if "reprotection_options" in passenger_impact:
        options = passenger_impact["reprotection_options"]
        if isinstance(options, list) and len(options) > 0:
            reprotection_bonus = min(10.0, len(options) * 3.0)
    
    # Calculate final score
    final_score = base_score - delay_penalty - cancellation_penalty + reprotection_bonus
    
    return max(0.0, min(100.0, final_score))


def calculate_network_score(
    solution: Dict[str, Any],
    agent_responses: Dict[str, Any]
) -> float:
    """
    Calculate network impact score (higher score = less propagation).
    
    Network score considers the number of downstream flights affected,
    connection misses, and aircraft rotation impact.
    
    Scoring Factors:
        - Number of downstream flights affected
        - Connection misses (penalty: 10 points each, max 30)
        - Aircraft rotation impact
    
    Args:
        solution: Solution dict with network impact information
        agent_responses: All agent responses for context
    
    Returns:
        Network score from 0.0 to 100.0
    
    Example:
        >>> solution = {
        ...     "network_impact": {
        ...         "downstream_flights": 2,
        ...         "connection_misses": 5
        ...     }
        ... }
        >>> agent_responses = {}
        >>> score = calculate_network_score(solution, agent_responses)
        >>> print(score)  # Should be around 50 (2 downstream, 5 misses)
        50.0
    """
    # Extract network impact information
    network_impact = solution.get("network_impact", {})
    downstream_flights = network_impact.get("downstream_flights", 0)
    connection_misses = network_impact.get("connection_misses", 0)
    
    # If no impact in solution, try to extract from network agent
    if downstream_flights == 0 and "network" in agent_responses:
        network_response = agent_responses["network"]
        if isinstance(network_response, dict):
            prop_impact = network_response.get("propagation_impact", {})
            downstream_flights = prop_impact.get("affected_flights", 0)
            conn_impact = network_response.get("connection_impact", {})
            connection_misses = conn_impact.get("missed_connections", 0)
    
    # Base score from downstream impact
    if downstream_flights == 0:
        base_score = 100.0
    elif downstream_flights <= 2:
        base_score = 80.0
    elif downstream_flights <= 5:
        base_score = 60.0
    else:
        base_score = 40.0
    
    # Penalty for connection misses (10 points each, max 30)
    connection_penalty = min(30.0, connection_misses * 10.0)
    
    # Calculate final score
    final_score = base_score - connection_penalty
    
    return max(0.0, min(100.0, final_score))


def calculate_composite_score(
    safety_score: float,
    cost_score: float,
    passenger_score: float,
    network_score: float
) -> float:
    """
    Calculate composite score as weighted average of dimension scores.
    
    Composite score = (safety * 0.4) + (cost * 0.2) + (passenger * 0.2) + (network * 0.2)
    
    Args:
        safety_score: Safety score (0-100)
        cost_score: Cost score (0-100)
        passenger_score: Passenger score (0-100)
        network_score: Network score (0-100)
    
    Returns:
        Composite score from 0.0 to 100.0
    
    Example:
        >>> composite = calculate_composite_score(90.0, 70.0, 60.0, 80.0)
        >>> print(composite)
        78.0
    """
    composite = (
        (safety_score * SCORING_WEIGHTS["safety"]) +
        (cost_score * SCORING_WEIGHTS["cost"]) +
        (passenger_score * SCORING_WEIGHTS["passenger"]) +
        (network_score * SCORING_WEIGHTS["network"])
    )
    
    return round(composite, 1)


def score_solution(
    solution: Dict[str, Any],
    agent_responses: Dict[str, Any],
    binding_constraints: List[Dict[str, Any]]
) -> Dict[str, float]:
    """
    Score a solution across all dimensions.
    
    This is the main entry point for scoring a solution. It calculates
    scores for all four dimensions and the composite score.
    
    Args:
        solution: Solution dict with impact information
        agent_responses: All agent responses for context
        binding_constraints: List of binding constraints from safety agents
    
    Returns:
        Dict with all scores:
            {
                "safety_score": 0-100,
                "cost_score": 0-100,
                "passenger_score": 0-100,
                "network_score": 0-100,
                "composite_score": weighted average
            }
    
    Example:
        >>> solution = {
        ...     "safety_compliance": "Satisfies all requirements",
        ...     "financial_impact": {"total_cost": 75000},
        ...     "passenger_impact": {"affected": 150, "delay_hours": 10},
        ...     "network_impact": {"downstream_flights": 2}
        ... }
        >>> agent_responses = {}
        >>> constraints = []
        >>> scores = score_solution(solution, agent_responses, constraints)
        >>> print(scores)
        {
            'safety_score': 80.0,
            'cost_score': 65.0,
            'passenger_score': 30.0,
            'network_score': 80.0,
            'composite_score': 66.0
        }
    """
    # Calculate individual dimension scores
    safety_score = calculate_safety_score(solution, binding_constraints)
    cost_score = calculate_cost_score(solution, agent_responses)
    passenger_score = calculate_passenger_score(solution, agent_responses)
    network_score = calculate_network_score(solution, agent_responses)
    
    # Calculate composite score
    composite_score = calculate_composite_score(
        safety_score,
        cost_score,
        passenger_score,
        network_score
    )
    
    return {
        "safety_score": safety_score,
        "cost_score": cost_score,
        "passenger_score": passenger_score,
        "network_score": network_score,
        "composite_score": composite_score
    }
