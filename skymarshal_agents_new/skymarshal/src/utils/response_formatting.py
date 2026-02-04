"""Response formatting utilities for concise agent-to-agent communication.

This module provides functions to truncate and format agent responses
for efficient A2A communication, reducing token usage and improving
orchestration performance.

Key Principles:
- Recommendations: max 100 chars, preserve key info
- Reasoning: max 150 chars, bullet point format
- Constraints: max 3 items, semicolon-separated
"""

from typing import Dict, Any, List, Optional

# Maximum lengths for A2A communication
# Increased to preserve business agent data for arbitrator (user confirmed token trade-off OK)
MAX_RECOMMENDATION_LENGTH = 300  # 3x increase for detailed recommendations
MAX_REASONING_LENGTH = 300       # 2x increase for full reasoning context
MAX_CONSTRAINTS_PER_AGENT = 5    # Allow more constraints to be preserved


def truncate_recommendation(rec: str, max_len: int = MAX_RECOMMENDATION_LENGTH) -> str:
    """Truncate recommendation to max length, preserving key info.

    Attempts to end at natural break points (punctuation) while
    keeping at least 60% of the allowed length.

    Args:
        rec: Full recommendation text
        max_len: Maximum allowed length (default 100)

    Returns:
        Truncated recommendation string

    Example:
        >>> truncate_recommendation("CREW_CHANGE: Captain exceeds FDP limit by 2 hours")
        'CREW_CHANGE: Captain exceeds FDP limit by 2 hours'
        >>> truncate_recommendation("A" * 150)
        'AAA...truncated...'
    """
    if not rec:
        return ""

    rec = rec.strip()
    if len(rec) <= max_len:
        return rec

    # Try to end at natural break points
    truncated = rec[:max_len]
    min_keep = int(max_len * 0.6)

    for sep in ['. ', '; ', ', ', ' - ', ' ']:
        idx = truncated.rfind(sep)
        if idx > min_keep:
            return truncated[:idx].strip()

    # No good break point, hard truncate
    return truncated.strip() + "..."


def format_reasoning_compact(reasoning: str, max_len: int = MAX_REASONING_LENGTH) -> str:
    """Convert verbose reasoning to compact bullet format.

    Extracts key sentences and formats as bullet points.

    Args:
        reasoning: Full reasoning text
        max_len: Maximum allowed length (default 150)

    Returns:
        Compact bullet-point reasoning

    Example:
        >>> format_reasoning_compact("FDP is 15 hours. Limit is 13 hours. Replacement available.")
        '* FDP: 15h * Limit: 13h * Replacement available'
    """
    if not reasoning:
        return ""

    reasoning = reasoning.strip()
    if len(reasoning) <= max_len:
        return reasoning

    # Split into sentences
    sentences = reasoning.replace('\n', '. ').split('. ')
    bullets = []
    total_len = 0

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        # Compact common phrases
        compact = _compact_phrase(sent)
        bullet = f"* {compact}"

        if total_len + len(bullet) + 2 <= max_len:
            bullets.append(bullet)
            total_len += len(bullet) + 2

    if bullets:
        return ' '.join(bullets)

    # Fallback: hard truncate original
    return reasoning[:max_len - 3] + "..."


def _compact_phrase(phrase: str) -> str:
    """Compact common verbose patterns.

    Args:
        phrase: Original phrase

    Returns:
        Compacted version
    """
    # Common replacements for aviation domain
    replacements = [
        ("Flight Duty Period", "FDP"),
        ("flight duty period", "FDP"),
        ("hours", "h"),
        ("minutes", "min"),
        ("approximately", "~"),
        ("available", "avail"),
        ("replacement", "repl"),
        ("requirement", "req"),
        ("aircraft", "A/C"),
        ("passenger", "pax"),
        ("passengers", "pax"),
        ("connection", "conn"),
        ("connections", "conns"),
        ("maintenance", "maint"),
        ("regulatory", "reg"),
        ("recommended", "rec"),
        ("immediately", "immed"),
    ]

    result = phrase
    for old, new in replacements:
        result = result.replace(old, new)

    return result


def format_constraints_compact(
    constraints: List[str],
    max_items: int = MAX_CONSTRAINTS_PER_AGENT
) -> str:
    """Convert constraint list to semicolon-separated string.

    Args:
        constraints: List of constraint strings
        max_items: Maximum number of constraints to include

    Returns:
        Semicolon-separated constraint string

    Example:
        >>> format_constraints_compact(["Min 10h rest", "A380 rating required"])
        'Min 10h rest; A380 rating required'
    """
    if not constraints:
        return ""

    # Take top constraints and join
    limited = constraints[:max_items]

    # Compact each constraint
    compacted = [_compact_phrase(c) for c in limited]

    return "; ".join(compacted)


def format_agent_response_compact(response: Dict[str, Any]) -> Dict[str, Any]:
    """Format agent response for compact A2A communication.

    Creates a new response dict with truncated fields suitable for
    passing to other agents in revision phase.

    Args:
        response: Full agent response dictionary

    Returns:
        Compact version with truncated fields

    Example:
        >>> resp = {"recommendation": "Long text...", "reasoning": "...", ...}
        >>> compact = format_agent_response_compact(resp)
        >>> len(compact["recommendation"]) <= 100
        True
    """
    return {
        "agent_name": response.get("agent_name", ""),
        "recommendation": truncate_recommendation(
            response.get("recommendation", "")
        ),
        "confidence": response.get("confidence", 0.0),
        "binding_constraints": response.get("binding_constraints", [])[:MAX_CONSTRAINTS_PER_AGENT],
        "reasoning": format_reasoning_compact(
            response.get("reasoning", "")
        ),
        "data_sources": response.get("data_sources", []),
        "extracted_flight_info": response.get("extracted_flight_info"),
        "timestamp": response.get("timestamp", ""),
        "status": response.get("status", "success"),
        "duration_seconds": response.get("duration_seconds"),
        "error": response.get("error"),
    }


def get_compact_context(collation_responses: Dict[str, Dict]) -> Dict[str, Dict]:
    """Convert full collation responses to compact context for Phase 2.

    Args:
        collation_responses: Dict of agent_name -> full response

    Returns:
        Dict of agent_name -> compact response
    """
    return {
        agent_name: format_agent_response_compact(response)
        for agent_name, response in collation_responses.items()
    }
