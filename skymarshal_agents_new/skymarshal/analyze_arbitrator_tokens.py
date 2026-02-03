"""
Analyze arbitrator input token sources and identify reduction opportunities.

This script examines the actual prompt sent to the arbitrator and breaks down
token usage by component to identify optimization opportunities.
"""

import json
import re
from typing import Dict, Any


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using simple heuristic.
    
    Claude tokenization is roughly:
    - 1 token ≈ 4 characters for English text
    - 1 token ≈ 0.75 words
    
    Args:
        text: Text to estimate tokens for
        
    Returns:
        Estimated token count
    """
    # Use character-based estimate (more accurate for mixed content)
    return len(text) // 4


def analyze_agent_responses(responses: Dict[str, Any]) -> Dict[str, int]:
    """
    Analyze token usage in agent responses.
    
    Args:
        responses: Dict of agent responses
        
    Returns:
        Dict of component -> token count
    """
    breakdown = {}
    
    for agent_name, response in responses.items():
        if not isinstance(response, dict):
            continue
            
        # Recommendation
        rec = response.get('recommendation', '')
        breakdown[f"{agent_name}_recommendation"] = estimate_tokens(rec)
        
        # Reasoning
        reasoning = response.get('reasoning', '')
        breakdown[f"{agent_name}_reasoning"] = estimate_tokens(reasoning)
        
        # Binding constraints
        constraints = response.get('binding_constraints', [])
        constraints_text = '\n'.join(constraints)
        breakdown[f"{agent_name}_constraints"] = estimate_tokens(constraints_text)
        
        # Data sources (usually small)
        data_sources = response.get('data_sources', [])
        sources_text = ', '.join(data_sources)
        breakdown[f"{agent_name}_data_sources"] = estimate_tokens(sources_text)
    
    return breakdown


def analyze_phase_comparison(initial_responses: Dict[str, Any], 
                             revised_responses: Dict[str, Any]) -> int:
    """
    Estimate tokens used in phase comparison text.
    
    Args:
        initial_responses: Phase 1 responses
        revised_responses: Phase 2 responses
        
    Returns:
        Estimated token count for phase comparison
    """
    # Phase comparison includes:
    # - Headers and structure (~200 tokens)
    # - Changed agents section (full text for each changed agent)
    # - Unchanged agents section (summary only)
    # - Summary statistics (~100 tokens)
    
    total_tokens = 300  # Base structure
    
    all_agents = set(initial_responses.keys()) | set(revised_responses.keys())
    
    for agent_name in all_agents:
        initial = initial_responses.get(agent_name, {})
        revised = revised_responses.get(agent_name, {})
        
        if isinstance(initial, dict) and isinstance(revised, dict):
            initial_rec = initial.get('recommendation', '')
            revised_rec = revised.get('recommendation', '')
            
            if initial_rec != revised_rec:
                # Changed agent - includes both recommendations
                total_tokens += estimate_tokens(initial_rec[:200])
                total_tokens += estimate_tokens(revised_rec[:200])
                total_tokens += 50  # Metadata and formatting
            else:
                # Unchanged agent - summary only
                total_tokens += estimate_tokens(revised_rec[:100])
                total_tokens += 20  # Metadata
    
    return total_tokens


def analyze_kb_context(kb_docs_count: int = 5) -> int:
    """
    Estimate tokens used in Knowledge Base context.
    
    Args:
        kb_docs_count: Number of KB documents retrieved
        
    Returns:
        Estimated token count for KB context
    """
    # KB context includes:
    # - Headers and metadata (~100 tokens)
    # - Document excerpts (400 chars each = ~100 tokens)
    # - Source citations (~50 tokens per doc)
    # - Decision guidance summary (~200 tokens)
    
    base_tokens = 300  # Headers and guidance
    per_doc_tokens = 150  # 100 for content + 50 for metadata
    
    return base_tokens + (kb_docs_count * per_doc_tokens)


def analyze_system_prompt() -> int:
    """
    Estimate tokens in arbitrator system prompt.
    
    Returns:
        Estimated token count
    """
    # System prompt includes:
    # - Role and priority definitions (~100 tokens)
    # - Workflow steps (~200 tokens)
    # - Decision rules (~150 tokens)
    # - Confidence guidelines (~200 tokens)
    # - Output format instructions (~300 tokens)
    # - Phase evolution instructions (~200 tokens)
    
    return 1150


def analyze_emergency_scenario():
    """
    Analyze token usage for the emergency scenario (pilot on fire).
    """
    print("=" * 80)
    print("ARBITRATOR INPUT TOKEN ANALYSIS - Emergency Scenario")
    print("=" * 80)
    print()
    
    # Simulate the emergency scenario responses
    # Based on the actual JSON provided
    
    responses_phase2 = {
        "crew_compliance": {
            "recommendation": "IMMEDIATE MEDICAL EVACUATION + CREW REPLACEMENT: Pilot on fire requires emergency medical response; incapacitated crew member unfit for duty; replacement pilot required before next departure; coordinate with medical/ops for emergency services",
            "confidence": 0.85,
            "binding_constraints": [
                "Incapacitated crew member unfit for duty per medical standards",
                "Minimum crew complement required for flight operations",
                "Type-rated replacement pilot required"
            ],
            "reasoning": "CRITICAL SAFETY EMERGENCY: Pilot on fire indicates severe medical emergency requiring immediate evacuation and treatment. CREW INCAPACITATION: Affected pilot is medically unfit for any flight duties; immediate removal from roster and replacement mandatory. REGULATORY COMPLIANCE: Incapacitated crew violates fitness-for-duty requirements; cannot operate with compromised crew. OPERATIONAL IMPACT: Flight data unavailable but crew replacement is NON-NEGOTIABLE regardless of schedule. COORDINATION: Align with maintenance (AOG), regulatory (emergency declared), and network (priority emergency) responses. NEXT STEPS: Activate standby crew at AUH; medical transport for injured pilot; incident investigation per safety protocols.",
            "data_sources": ["flights", "CrewRoster", "CrewMembers"]
        },
        "maintenance": {
            "recommendation": "AIRCRAFT INSPECTION REQUIRED: Post-emergency fire event mandates airworthiness inspection before next dispatch",
            "confidence": 0.8,
            "binding_constraints": [
                "Fire damage assessment mandatory",
                "Airworthiness certificate validation",
                "Safety equipment inspection"
            ],
            "reasoning": "Fire event (pilot on fire) requires immediate aircraft safety inspection per regulatory requirements. Emergency landing/arrival triggers mandatory airworthiness review of all fire suppression systems, cockpit environment, oxygen systems. Aircraft status unknown until post-incident inspection completed - assume AOG until cleared. Flight data unavailable but emergency nature confirmed by all agents - maintenance inspection non-negotiable. Post-fire inspection scope: cockpit fire detection/suppression systems, electrical systems, oxygen system integrity, structural damage assessment. Estimated inspection time: 4-8 hours minimum before RTS determination possible.",
            "data_sources": ["DynamoDB queries via tools"]
        },
        "regulatory": {
            "recommendation": "COMPLIANT: Emergency operations override all regulatory constraints; AUH arrival cleared under ICAO Annex 2 emergency authority",
            "confidence": 0.8,
            "binding_constraints": [
                "Emergency declared - all regulatory restrictions waived",
                "Medical/fire response coordination required",
                "Post-incident investigation mandatory"
            ],
            "reasoning": "Emergency Authority: ICAO Annex 2 Section 2.3.1 - aircraft in emergency may deviate from any regulation to extent necessary. AUH (OMAA) Status: No NOTAMs restricting emergency operations; airport equipped for medical emergencies. Regulatory Waiver: Curfews, slots, airspace restrictions automatically waived under emergency declaration. Post-Event Compliance: Mandatory occurrence reporting per UAE GCAA regulations within 72 hours. Coordination Required: Emergency services, medical response, fire brigade on standby at AUH.",
            "data_sources": ["DynamoDB queries"]
        },
        "network": {
            "recommendation": "SUSPEND NETWORK ANALYSIS | DEFER TO EMERGENCY PROTOCOLS",
            "confidence": 0.8,
            "binding_constraints": [],
            "reasoning": "Safety > Network Efficiency: Pilot medical emergency overrides all propagation calculations. No rotation analysis required: Aircraft will be AOG pending emergency response. Connection protection irrelevant: Flight will not continue normal operations. Recovery scenarios N/A: Emergency landing protocols take precedence.",
            "data_sources": ["flights", "AircraftAvailability"]
        },
        "guest_experience": {
            "recommendation": "No recommendation provided",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": "No reasoning provided",
            "data_sources": []
        },
        "cargo": {
            "recommendation": "No recommendation provided",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": "No reasoning provided",
            "data_sources": []
        },
        "finance": {
            "recommendation": "No recommendation provided",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": "No reasoning provided",
            "data_sources": []
        }
    }
    
    # Analyze agent responses
    print("1. AGENT RESPONSES (Phase 2)")
    print("-" * 80)
    
    agent_breakdown = analyze_agent_responses(responses_phase2)
    
    # Group by component type
    total_recommendations = sum(v for k, v in agent_breakdown.items() if 'recommendation' in k)
    total_reasoning = sum(v for k, v in agent_breakdown.items() if 'reasoning' in k)
    total_constraints = sum(v for k, v in agent_breakdown.items() if 'constraints' in k)
    total_sources = sum(v for k, v in agent_breakdown.items() if 'data_sources' in k)
    
    print(f"Recommendations:      {total_recommendations:>6} tokens")
    print(f"Reasoning:            {total_reasoning:>6} tokens")
    print(f"Binding Constraints:  {total_constraints:>6} tokens")
    print(f"Data Sources:         {total_sources:>6} tokens")
    print(f"{'':->80}")
    print(f"TOTAL AGENT DATA:     {sum(agent_breakdown.values()):>6} tokens")
    print()
    
    # Detailed breakdown by agent
    print("   Breakdown by Agent:")
    for agent in ["crew_compliance", "maintenance", "regulatory", "network"]:
        agent_total = sum(v for k, v in agent_breakdown.items() if k.startswith(agent))
        print(f"   - {agent:20s}: {agent_total:>5} tokens")
    print()
    
    # Phase comparison
    print("2. PHASE COMPARISON (Phase 1 vs Phase 2)")
    print("-" * 80)
    
    # Simulate Phase 1 responses (slightly different)
    responses_phase1 = {k: v.copy() for k, v in responses_phase2.items()}
    # Modify slightly to simulate changes
    for agent in ["crew_compliance", "maintenance", "regulatory", "network"]:
        if agent in responses_phase1:
            responses_phase1[agent]["recommendation"] = responses_phase1[agent]["recommendation"][:200] + " (initial)"
    
    phase_comparison_tokens = analyze_phase_comparison(responses_phase1, responses_phase2)
    print(f"Phase Evolution Text: {phase_comparison_tokens:>6} tokens")
    print()
    
    # Knowledge Base context
    print("3. KNOWLEDGE BASE CONTEXT")
    print("-" * 80)
    kb_tokens = analyze_kb_context(kb_docs_count=5)
    print(f"KB Documents (5):     {kb_tokens:>6} tokens")
    print()
    
    # System prompt
    print("4. SYSTEM PROMPT")
    print("-" * 80)
    system_tokens = analyze_system_prompt()
    print(f"System Instructions:  {system_tokens:>6} tokens")
    print()
    
    # User prompt structure
    print("5. USER PROMPT STRUCTURE")
    print("-" * 80)
    structure_tokens = 200  # Headers, formatting, task instructions
    print(f"Headers & Structure:  {structure_tokens:>6} tokens")
    print()
    
    # Total
    print("=" * 80)
    print("TOTAL INPUT TOKENS")
    print("=" * 80)
    total_input = (
        sum(agent_breakdown.values()) +
        phase_comparison_tokens +
        kb_tokens +
        system_tokens +
        structure_tokens
    )
    print(f"Agent Responses:      {sum(agent_breakdown.values()):>6} tokens ({sum(agent_breakdown.values())/total_input*100:>5.1f}%)")
    print(f"Phase Comparison:     {phase_comparison_tokens:>6} tokens ({phase_comparison_tokens/total_input*100:>5.1f}%)")
    print(f"KB Context:           {kb_tokens:>6} tokens ({kb_tokens/total_input*100:>5.1f}%)")
    print(f"System Prompt:        {system_tokens:>6} tokens ({system_tokens/total_input*100:>5.1f}%)")
    print(f"Structure:            {structure_tokens:>6} tokens ({structure_tokens/total_input*100:>5.1f}%)")
    print(f"{'':->80}")
    print(f"TOTAL:                {total_input:>6} tokens")
    print()
    
    # Optimization opportunities
    print("=" * 80)
    print("OPTIMIZATION OPPORTUNITIES")
    print("=" * 80)
    print()
    
    print("HIGH IMPACT (30-50% reduction):")
    print("-" * 80)
    
    # Reasoning is the biggest component
    reasoning_savings = int(total_reasoning * 0.7)  # 70% reduction possible
    print(f"1. Compress Reasoning Text")
    print(f"   Current: {total_reasoning} tokens")
    print(f"   Target:  {total_reasoning - reasoning_savings} tokens (70% reduction)")
    print(f"   Savings: {reasoning_savings} tokens")
    print(f"   Method:  Bullet points, abbreviations, remove redundancy")
    print()
    
    # Recommendations can be shortened
    rec_savings = int(total_recommendations * 0.4)  # 40% reduction
    print(f"2. Truncate Recommendations")
    print(f"   Current: {total_recommendations} tokens")
    print(f"   Target:  {total_recommendations - rec_savings} tokens (40% reduction)")
    print(f"   Savings: {rec_savings} tokens")
    print(f"   Method:  Max 100 chars, remove verbose phrases")
    print()
    
    # Phase comparison can be simplified
    phase_savings = int(phase_comparison_tokens * 0.5)  # 50% reduction
    print(f"3. Simplify Phase Comparison")
    print(f"   Current: {phase_comparison_tokens} tokens")
    print(f"   Target:  {phase_comparison_tokens - phase_savings} tokens (50% reduction)")
    print(f"   Savings: {phase_savings} tokens")
    print(f"   Method:  Show only changed agents, compact format")
    print()
    
    print("MEDIUM IMPACT (20-30% reduction):")
    print("-" * 80)
    
    # KB context can be reduced
    kb_savings = int(kb_tokens * 0.4)  # 40% reduction
    print(f"4. Reduce KB Documents")
    print(f"   Current: {kb_tokens} tokens (5 documents)")
    print(f"   Target:  {kb_tokens - kb_savings} tokens (3 documents)")
    print(f"   Savings: {kb_savings} tokens")
    print(f"   Method:  Retrieve fewer documents, truncate excerpts")
    print()
    
    # System prompt can be compressed
    system_savings = int(system_tokens * 0.3)  # 30% reduction
    print(f"5. Compress System Prompt")
    print(f"   Current: {system_tokens} tokens")
    print(f"   Target:  {system_tokens - system_savings} tokens (30% reduction)")
    print(f"   Savings: {system_savings} tokens")
    print(f"   Method:  Remove verbose instructions, use XML tags")
    print()
    
    # Skip inactive agents
    inactive_agents = ["guest_experience", "cargo", "finance"]
    inactive_tokens = sum(
        sum(v for k, v in agent_breakdown.items() if k.startswith(agent))
        for agent in inactive_agents
    )
    print(f"6. Skip Inactive Agents")
    print(f"   Current: {inactive_tokens} tokens (3 agents with no data)")
    print(f"   Target:  0 tokens")
    print(f"   Savings: {inactive_tokens} tokens")
    print(f"   Method:  Don't include agents with 0.0 confidence")
    print()
    
    # Total savings
    total_savings = (
        reasoning_savings +
        rec_savings +
        phase_savings +
        kb_savings +
        system_savings +
        inactive_tokens
    )
    
    print("=" * 80)
    print(f"TOTAL POTENTIAL SAVINGS: {total_savings} tokens ({total_savings/total_input*100:.1f}%)")
    print(f"OPTIMIZED INPUT:         {total_input - total_savings} tokens")
    print(f"TIME SAVINGS:            ~{total_savings / 35:.1f} seconds (at 35 tokens/sec)")
    print("=" * 80)


if __name__ == "__main__":
    analyze_emergency_scenario()
