"""Revision Logic Utilities for Multi-Round Orchestration

This module provides utilities to help agents determine whether revision is needed
during Phase 2 (Revision Round) of the multi-round orchestration workflow.

Agents use these utilities to systematically evaluate other agents' recommendations
and decide whether to REVISE, CONFIRM, or STRENGTHEN their initial recommendation.
"""

import logging
from typing import Dict, Any, List, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RevisionDecision(str, Enum):
    """Possible revision decisions an agent can make"""
    REVISE = "REVISE"  # Change recommendation based on new information
    CONFIRM = "CONFIRM"  # Keep original recommendation unchanged
    STRENGTHEN = "STRENGTHEN"  # Reinforce recommendation with additional support


class RevisionReason(str, Enum):
    """Reasons for revision decisions"""
    # Reasons to REVISE
    NEW_TIMING_INFO = "new_timing_information"  # Other agents provide new delay/timing estimates
    NEW_CONSTRAINTS = "new_constraints"  # Other agents identify new operational constraints
    CONFLICTING_DATA = "conflicting_data"  # Other agents have different data that affects analysis
    SAFETY_CONCERN = "safety_concern"  # Other safety agents raise concerns
    OPERATIONAL_CHANGE = "operational_change"  # Network/maintenance changes affect domain
    
    # Reasons to CONFIRM
    NO_NEW_INFO = "no_new_information"  # Other agents don't provide relevant new information
    ALREADY_CONSIDERED = "already_considered"  # Other agents' findings already in initial analysis
    DOMAIN_INDEPENDENT = "domain_independent"  # Other agents' findings don't affect this domain
    
    # Reasons to STRENGTHEN
    REINFORCING_DATA = "reinforcing_data"  # Other agents' findings support initial recommendation
    ADDITIONAL_CONSTRAINTS = "additional_constraints"  # Other agents add supporting constraints
    CONSENSUS = "consensus"  # Multiple agents agree with initial assessment


def analyze_other_recommendations(
    agent_name: str,
    initial_recommendation: Dict[str, Any],
    other_recommendations: Dict[str, Any],
    domain_keywords: List[str]
) -> Tuple[RevisionDecision, List[RevisionReason], str]:
    """
    Analyze other agents' recommendations to determine if revision is needed.
    
    This function provides a systematic framework for agents to evaluate whether
    they should revise their initial recommendation based on other agents' findings.
    
    Args:
        agent_name: Name of the current agent (e.g., "crew_compliance")
        initial_recommendation: The agent's initial recommendation dict
        other_recommendations: Dict of other agents' recommendations
        domain_keywords: List of keywords relevant to this agent's domain
                        (e.g., ["crew", "FDP", "rest", "duty"] for crew compliance)
    
    Returns:
        Tuple of (decision, reasons, justification):
        - decision: RevisionDecision enum (REVISE, CONFIRM, or STRENGTHEN)
        - reasons: List of RevisionReason enums explaining the decision
        - justification: Human-readable explanation of the decision
    
    Example:
        >>> decision, reasons, justification = analyze_other_recommendations(
        ...     agent_name="crew_compliance",
        ...     initial_recommendation={"recommendation": "APPROVED", "confidence": 0.9},
        ...     other_recommendations={
        ...         "maintenance": {"recommendation": "3 hour delay needed", ...},
        ...         "network": {"recommendation": "Aircraft swap possible", ...}
        ...     },
        ...     domain_keywords=["crew", "FDP", "rest", "duty", "hours"]
        ... )
        >>> print(decision)
        RevisionDecision.REVISE
        >>> print(reasons)
        [RevisionReason.NEW_TIMING_INFO]
    """
    logger.info(f"Analyzing other recommendations for {agent_name}")
    
    reasons = []
    relevant_findings = []
    
    # Check each other agent's recommendation
    for other_agent, recommendation in other_recommendations.items():
        if other_agent == agent_name:
            continue  # Skip own recommendation
        
        rec_text = str(recommendation.get("recommendation", "")).lower()
        reasoning = str(recommendation.get("reasoning", "")).lower()
        combined_text = f"{rec_text} {reasoning}"
        
        # Check for domain-relevant keywords
        keywords_found = [
            kw for kw in domain_keywords
            if kw.lower() in combined_text
        ]
        
        # Also check for timing/constraint/safety keywords that are universally relevant
        universal_keywords = ["delay", "hour", "hours", "time", "cannot", "must", 
                             "required", "safety", "risk", "violation"]
        universal_found = [
            kw for kw in universal_keywords
            if kw in combined_text
        ]
        
        has_relevant_keywords = len(keywords_found) > 0 or len(universal_found) > 0
        
        if has_relevant_keywords:
            relevant_findings.append({
                "agent": other_agent,
                "recommendation": recommendation.get("recommendation", ""),
                "confidence": recommendation.get("confidence", 0.0),
                "keywords_found": keywords_found,
                "universal_keywords_found": universal_found
            })
            logger.debug(f"  Found relevant keywords from {other_agent}: domain={keywords_found}, universal={universal_found}")
    
    # Analyze timing-related information
    timing_keywords = ["delay", "delayed", "postpone", "reschedule", "schedule change"]
    has_new_timing = any(
        any(kw in str(rec.get("recommendation", "")).lower() or kw in str(rec.get("reasoning", "")).lower() 
            for kw in timing_keywords)
        for rec in other_recommendations.values()
    )
    
    # Analyze constraint-related information
    constraint_keywords = ["cannot", "must", "required", "constraint", "limit", "restriction"]
    has_new_constraints = any(
        any(kw in str(rec.get("recommendation", "")).lower() for kw in constraint_keywords)
        for rec in other_recommendations.values()
    )
    
    # Analyze safety-related information (for safety agents)
    safety_keywords = ["safety", "unsafe", "risk", "hazard", "violation", "compliance"]
    has_safety_concerns = any(
        any(kw in str(rec.get("recommendation", "")).lower() for kw in safety_keywords)
        for rec in other_recommendations.values()
    )
    
    # Analyze reinforcing information
    initial_rec_text = str(initial_recommendation.get("recommendation", "")).lower()
    has_reinforcing = any(
        _check_agreement(initial_rec_text, str(rec.get("recommendation", "")).lower())
        for rec in other_recommendations.values()
    )
    
    # Decision logic
    if not relevant_findings:
        # No relevant information from other agents
        decision = RevisionDecision.CONFIRM
        reasons.append(RevisionReason.NO_NEW_INFO)
        justification = (
            f"No relevant information found in other agents' recommendations "
            f"that affects {agent_name} domain. Initial recommendation remains valid."
        )
    
    elif has_new_timing and agent_name in ["crew_compliance", "maintenance", "network"]:
        # Timing changes affect crew FDP, maintenance windows, and network propagation
        # Check this BEFORE reinforcing to ensure timing changes trigger recalculation
        decision = RevisionDecision.REVISE
        reasons.append(RevisionReason.NEW_TIMING_INFO)
        justification = (
            f"Other agents provided new timing information (delays, schedule changes) "
            f"that affects {agent_name} calculations. Revision needed to recalculate "
            f"based on updated timing."
        )
    
    elif has_new_constraints:
        # New constraints from other agents
        decision = RevisionDecision.REVISE
        reasons.append(RevisionReason.NEW_CONSTRAINTS)
        justification = (
            f"Other agents identified new operational constraints that may affect "
            f"{agent_name} assessment. Revision needed to incorporate these constraints."
        )
    
    elif has_safety_concerns and agent_name in ["crew_compliance", "maintenance", "regulatory"]:
        # Safety concerns raised by other agents
        decision = RevisionDecision.REVISE
        reasons.append(RevisionReason.SAFETY_CONCERN)
        justification = (
            f"Other agents raised safety concerns that require {agent_name} to "
            f"re-evaluate initial recommendation with additional safety considerations."
        )
    
    elif has_reinforcing and len(relevant_findings) > 0:
        # Other agents' findings support initial recommendation
        decision = RevisionDecision.STRENGTHEN
        reasons.append(RevisionReason.REINFORCING_DATA)
        justification = (
            f"Other agents' findings ({len(relevant_findings)} agents) support and "
            f"reinforce {agent_name} initial recommendation. Strengthening assessment "
            f"with additional supporting evidence."
        )
    
    elif len(relevant_findings) > 0:
        # Relevant findings but unclear impact
        decision = RevisionDecision.REVISE
        reasons.append(RevisionReason.OPERATIONAL_CHANGE)
        justification = (
            f"Other agents provided relevant operational information ({len(relevant_findings)} agents) "
            f"that may affect {agent_name} assessment. Revision needed to evaluate impact."
        )
    
    else:
        # Default to confirm if no clear reason to revise
        decision = RevisionDecision.CONFIRM
        reasons.append(RevisionReason.ALREADY_CONSIDERED)
        justification = (
            f"Other agents' findings were already considered in {agent_name} initial "
            f"analysis. No new information warrants revision."
        )
    
    logger.info(f"  Decision for {agent_name}: {decision.value}")
    logger.info(f"  Reasons: {[r.value for r in reasons]}")
    logger.info(f"  Relevant findings from {len(relevant_findings)} agents")
    
    return decision, reasons, justification


def _check_agreement(text1: str, text2: str) -> bool:
    """
    Check if two recommendation texts are in agreement.
    
    Args:
        text1: First recommendation text (lowercase)
        text2: Second recommendation text (lowercase)
    
    Returns:
        bool: True if recommendations appear to agree
    """
    # Positive agreement indicators
    positive_keywords = ["approved", "proceed", "acceptable", "within limits", "compliant", "ok", "acceptable"]
    text1_positive = any(kw in text1 for kw in positive_keywords)
    text2_positive = any(kw in text2 for kw in positive_keywords)
    
    # Negative agreement indicators (both recommend against proceeding)
    negative_keywords = ["cannot", "requires change", "violation", "exceeds", "insufficient", 
                        "requires_crew_change", "requires crew change", "crew change required",
                        "cannot_proceed", "cannot proceed", "requires_inspection", "requires inspection",
                        "delay required", "delay requires", "crew duty limits", "fdp limit", "exceeded"]
    text1_negative = any(kw in text1 for kw in negative_keywords)
    text2_negative = any(kw in text2 for kw in negative_keywords)
    
    # Agreement if both positive or both negative
    return (text1_positive and text2_positive) or (text1_negative and text2_negative)


def format_revision_statement(
    decision: RevisionDecision,
    reasons: List[RevisionReason],
    justification: str,
    initial_recommendation: str,
    revised_recommendation: str = None
) -> str:
    """
    Format a clear revision statement for the agent's response.
    
    Args:
        decision: The revision decision made
        reasons: List of reasons for the decision
        justification: Detailed justification
        initial_recommendation: The agent's initial recommendation
        revised_recommendation: The revised recommendation (if decision is REVISE)
    
    Returns:
        str: Formatted revision statement for inclusion in agent response
    
    Example:
        >>> statement = format_revision_statement(
        ...     decision=RevisionDecision.REVISE,
        ...     reasons=[RevisionReason.NEW_TIMING_INFO],
        ...     justification="Maintenance agent reported 3-hour delay...",
        ...     initial_recommendation="APPROVED with 2h margin",
        ...     revised_recommendation="REQUIRES_CREW_CHANGE due to FDP limit"
        ... )
        >>> print(statement)
        **REVISION DECISION: REVISE**
        
        Initial Recommendation: APPROVED with 2h margin
        Revised Recommendation: REQUIRES_CREW_CHANGE due to FDP limit
        ...
    """
    if decision == RevisionDecision.REVISE:
        if not revised_recommendation:
            revised_recommendation = "[Revised recommendation not provided]"
        
        statement = f"""**REVISION DECISION: {decision.value}**

Initial Recommendation: {initial_recommendation}
Revised Recommendation: {revised_recommendation}

Reasons for Revision:
{_format_reasons_list(reasons)}

Justification:
{justification}

This revision was made after reviewing other agents' recommendations and identifying 
new information that affects this domain's assessment."""
    
    elif decision == RevisionDecision.CONFIRM:
        statement = f"""**REVISION DECISION: {decision.value}**

Initial Recommendation: {initial_recommendation}
Confirmed Recommendation: {initial_recommendation}

Reasons for Confirmation:
{_format_reasons_list(reasons)}

Justification:
{justification}

After reviewing other agents' recommendations, the initial assessment remains valid 
and no revision is warranted."""
    
    else:  # STRENGTHEN
        statement = f"""**REVISION DECISION: {decision.value}**

Initial Recommendation: {initial_recommendation}
Strengthened Recommendation: {initial_recommendation}

Reasons for Strengthening:
{_format_reasons_list(reasons)}

Justification:
{justification}

Other agents' findings provide additional support for the initial recommendation, 
strengthening confidence in this assessment."""
    
    return statement


def _format_reasons_list(reasons: List[RevisionReason]) -> str:
    """Format a list of revision reasons as bullet points."""
    reason_descriptions = {
        RevisionReason.NEW_TIMING_INFO: "New timing information from other agents",
        RevisionReason.NEW_CONSTRAINTS: "New operational constraints identified",
        RevisionReason.CONFLICTING_DATA: "Conflicting data from other agents",
        RevisionReason.SAFETY_CONCERN: "Safety concerns raised by other agents",
        RevisionReason.OPERATIONAL_CHANGE: "Operational changes affecting this domain",
        RevisionReason.NO_NEW_INFO: "No new relevant information from other agents",
        RevisionReason.ALREADY_CONSIDERED: "Other agents' findings already considered",
        RevisionReason.DOMAIN_INDEPENDENT: "Other agents' findings don't affect this domain",
        RevisionReason.REINFORCING_DATA: "Other agents' findings support initial assessment",
        RevisionReason.ADDITIONAL_CONSTRAINTS: "Additional supporting constraints identified",
        RevisionReason.CONSENSUS: "Multiple agents agree with initial assessment",
    }
    
    return "\n".join([
        f"- {reason_descriptions.get(reason, reason.value)}"
        for reason in reasons
    ])


# Domain-specific keyword sets for each agent
AGENT_DOMAIN_KEYWORDS = {
    "crew_compliance": [
        "crew", "FDP", "flight duty period", "rest", "duty", "hours",
        "pilot", "captain", "first officer", "cabin crew", "fatigue",
        "qualification", "type rating", "recency", "medical certificate"
    ],
    "maintenance": [
        "maintenance", "aircraft", "MEL", "airworthiness", "inspection",
        "repair", "work order", "technician", "defect", "serviceability",
        "registration", "tail number", "component", "system"
    ],
    "regulatory": [
        "regulatory", "regulation", "compliance", "curfew", "slot",
        "weather", "NOTAM", "restriction", "authority", "permit",
        "EASA", "GCAA", "FAA", "CAA", "approval"
    ],
    "network": [
        "network", "propagation", "connection", "rotation", "aircraft swap",
        "downstream", "upstream", "schedule", "delay impact", "ripple effect",
        "fleet", "utilization", "positioning"
    ],
    "guest_experience": [
        "passenger", "guest", "booking", "rebooking", "compensation",
        "VIP", "elite", "frequent flyer", "baggage", "mishandled",
        "customer", "satisfaction", "service recovery"
    ],
    "cargo": [
        "cargo", "shipment", "freight", "cold chain", "perishable",
        "temperature", "hazardous", "dangerous goods", "loading",
        "weight", "balance", "commodity"
    ],
    "finance": [
        "cost", "revenue", "financial", "expense", "compensation",
        "refund", "rebooking cost", "operational cost", "fuel",
        "crew cost", "passenger revenue", "cargo revenue"
    ]
}


def get_domain_keywords(agent_name: str) -> List[str]:
    """
    Get domain-specific keywords for an agent.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        List of domain-specific keywords
    """
    return AGENT_DOMAIN_KEYWORDS.get(agent_name, [])
