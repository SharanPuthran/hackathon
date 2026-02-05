"""
Arbitrator Agent

The arbitrator resolves conflicts between agent recommendations and makes final decisions
using Claude Opus 4.5 with cross-region inference. It enforces safety-first principles
and conservative decision-making for safety conflicts.

Key Responsibilities:
- Identify conflicts between agent recommendations
- Extract binding constraints from safety agents
- Apply safety-first decision rules
- Generate final decision with justification
- Provide complete audit trail of conflict resolutions

Safety Priority Rules:
1. Safety vs Business: Always choose safety
2. Safety vs Safety: Choose most conservative
3. Business vs Business: Balance operational impact
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import boto3
from botocore.exceptions import ClientError

from langchain_aws import ChatBedrock
from langchain_core.messages import HumanMessage

# Import arbitrator schemas from centralized schemas module
from agents.schemas import (
    ConflictDetail,
    ResolutionDetail,
    SafetyOverride,
    ArbitratorInput,
    ArbitratorOutput,
    RecoverySolution,
    RecoveryPlan,
    RecoveryStep,
    AgentEvolution,
    RecommendationEvolution
)

# Import scoring functions
from agents.scoring import score_solution

# Import knowledge base client for historical precedent
from agents.arbitrator.knowledge_base import get_knowledge_base_client

logger = logging.getLogger(__name__)

# Knowledge Base ID for historical disruption data
KNOWLEDGE_BASE_ID = "UDONMVCXEW"

# Claude Opus 4.5 cross-region inference profile
OPUS_MODEL_ID = "us.anthropic.claude-opus-4-5-20250514-v1:0"
# Fallback models in priority order
SONNET_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
HAIKU_MODEL_ID = "us.anthropic.claude-haiku-4-5-20250929-v1:0"
NOVA_PREMIER_MODEL_ID = "us.amazon.nova-premier-v1:0"
NOVA_PRO_MODEL_ID = "us.amazon.nova-pro-v1:0"

# Arbitrator model priority (will try in order) - Opus 4.5 primary, Sonnet 4.5 fallback only
ARBITRATOR_MODEL_PRIORITY = [
    {
        "id": OPUS_MODEL_ID,
        "name": "Claude Opus 4.5",
        "temperature": 0.1,
        "max_tokens": 16384,
        "reason": "Most powerful reasoning for complex arbitration"
    },
    {
        "id": SONNET_MODEL_ID,
        "name": "Claude Sonnet 4.5",
        "temperature": 0.1,
        "max_tokens": 12000,  # Increased for complex schema
        "reason": "Excellent reasoning fallback"
    }
]

# Cache for tested models
_arbitrator_tested_models = {}


# ============================================================================
# System Prompt for Arbitrator
# ============================================================================

# Compact phase evolution - single line for agent parsing
PHASE_EVOLUTION_INSTRUCTIONS = """<evolution>converge=weight_high|diverge=investigate|stable=high_conf</evolution>"""

# Solution structure guidance for the LLM - explains the complex nested schema
SOLUTION_STRUCTURE_GUIDANCE = """
<SOLUTION_GENERATION>
MANDATORY: You MUST generate 1-3 RecoverySolution objects in the solution_options array.
This is NON-NEGOTIABLE. Every arbitration MUST produce at least one solution.

<solution_schema>
Each solution MUST include ALL of these fields:
- solution_id: int (1, 2, or 3) - unique ID for this solution
- title: str - short descriptive title (max 50 chars)
- description: str - detailed description of the approach
- recommendations: List[str] - 3-5 specific action steps
- safety_compliance: str - how this satisfies safety constraints
- passenger_impact: Dict with keys: affected_count (int), delay_hours (float), cancellation_flag (bool)
- financial_impact: Dict with keys: total_cost (int), breakdown (Dict)
- network_impact: Dict with keys: downstream_flights (int), connection_misses (int)
- safety_score: float 0-100 (higher = safer)
- cost_score: float 0-100 (higher = lower cost)
- passenger_score: float 0-100 (higher = less impact)
- network_score: float 0-100 (higher = less propagation)
- composite_score: float (calculated: safety*0.4 + cost*0.2 + pax*0.2 + network*0.2)
- pros: List[str] - 2-3 advantages
- cons: List[str] - 2-3 disadvantages
- risks: List[str] - 2-3 potential risks
- confidence: float 0.0-1.0
- estimated_duration: str (e.g., "4 hours", "6 hours")
- recovery_plan: RecoveryPlan object (see below)
</solution_schema>

<recovery_plan_schema>
recovery_plan MUST include:
- solution_id: int (must match parent solution_id)
- total_steps: int (count of steps)
- estimated_total_duration: str
- steps: List[RecoveryStep] - at least 2 steps
- critical_path: List[int] - step numbers on critical path
- contingency_plans: List[Dict] - can be empty []
</recovery_plan_schema>

<recovery_step_schema>
Each step MUST include:
- step_number: int (sequential starting from 1)
- step_name: str - short name
- description: str - what this step accomplishes
- responsible_agent: str - who executes (e.g., "crew_scheduling", "ops_control", "guest_services")
- dependencies: List[int] - step numbers this depends on ([] for first step)
- estimated_duration: str (e.g., "15 minutes", "1 hour")
- automation_possible: bool
- action_type: str (notify, rebook, schedule, coordinate, review)
- parameters: Dict - can be {}
- success_criteria: str - how to verify completion
- rollback_procedure: Optional[str] - can be null
</recovery_step_schema>
</SOLUTION_GENERATION>
"""

# Complete solution example for the LLM to follow
SOLUTION_EXAMPLE = """
<SOLUTION_EXAMPLE>
Example solution_options for a crew FDP violation scenario:

{
  "solution_options": [
    {
      "solution_id": 1,
      "title": "Delay with Crew Change",
      "description": "Delay flight 2 hours while replacement crew positions from standby",
      "recommendations": [
        "Activate standby Captain from AUH base",
        "Delay departure by 2 hours",
        "Notify passengers of delay",
        "Arrange meal vouchers for affected passengers"
      ],
      "safety_compliance": "Fully satisfies FDP limits with 3-hour margin for replacement crew",
      "passenger_impact": {"affected_count": 280, "delay_hours": 2.0, "cancellation_flag": false},
      "financial_impact": {"total_cost": 85000, "breakdown": {"crew_positioning": 15000, "compensation": 70000}},
      "network_impact": {"downstream_flights": 1, "connection_misses": 12},
      "safety_score": 95.0,
      "cost_score": 65.0,
      "passenger_score": 60.0,
      "network_score": 75.0,
      "composite_score": 76.0,
      "pros": ["Maintains safety compliance", "Minimal network impact", "Flight operates"],
      "cons": ["2-hour delay", "Passenger compensation required"],
      "risks": ["Standby crew may have traffic delays", "Weather could worsen"],
      "confidence": 0.85,
      "estimated_duration": "2.5 hours",
      "recovery_plan": {
        "solution_id": 1,
        "total_steps": 3,
        "estimated_total_duration": "2.5 hours",
        "steps": [
          {
            "step_number": 1,
            "step_name": "Activate Standby Crew",
            "description": "Contact and confirm standby Captain availability",
            "responsible_agent": "crew_scheduling",
            "dependencies": [],
            "estimated_duration": "15 minutes",
            "automation_possible": true,
            "action_type": "coordinate",
            "parameters": {"crew_type": "Captain", "base": "AUH"},
            "success_criteria": "Standby crew confirmed and en route",
            "rollback_procedure": "Escalate to reserve crew list"
          },
          {
            "step_number": 2,
            "step_name": "Notify Passengers",
            "description": "Send delay notification via SMS and app",
            "responsible_agent": "guest_services",
            "dependencies": [1],
            "estimated_duration": "10 minutes",
            "automation_possible": true,
            "action_type": "notify",
            "parameters": {"channel": "sms,app", "delay_hours": 2},
            "success_criteria": "Notifications sent to all passengers",
            "rollback_procedure": null
          },
          {
            "step_number": 3,
            "step_name": "Confirm Crew Arrival",
            "description": "Verify replacement crew arrived and ready",
            "responsible_agent": "ops_control",
            "dependencies": [1],
            "estimated_duration": "90 minutes",
            "automation_possible": false,
            "action_type": "review",
            "parameters": {},
            "success_criteria": "Crew checked in and briefed",
            "rollback_procedure": "Activate second standby or consider cancellation"
          }
        ],
        "critical_path": [1, 3],
        "contingency_plans": [{"trigger": "Standby unavailable", "action": "Escalate to home reserve list"}]
      }
    }
  ],
  "recommended_solution_id": 1
}
</SOLUTION_EXAMPLE>
"""

# System prompt for Arbitrator - includes critical requirement for solution generation
ARBITRATOR_SYSTEM_PROMPT = """<role>arbitrator</role>

<DATA_POLICY>
ONLY_USE: tools|KB:UDONMVCXEW|agent_inputs
NEVER: assume|fabricate|use_LLM_knowledge|external_lookup|guess_missing_data
ON_DATA_GAP: report_error|request_clarification
</DATA_POLICY>

<rules>
P1: Safety > Business = ALWAYS choose safety
P2: Safety vs Safety = Choose MOST CONSERVATIVE option
P3: Business vs Business = Pareto optimization (balance tradeoffs)
</rules>

<weights>safety:40|cost:20|pax:20|network:20</weights>

<confidence_scoring>
0.9-1.0: All agents agree, no conflicts
0.7-0.9: Minor conflicts resolved
0.5-0.7: Significant conflicts, safety clear
less than 0.5: ESCALATE to human
</confidence_scoring>

<CRITICAL_REQUIREMENT>
YOU MUST GENERATE solution_options WITH 1-3 RecoverySolution OBJECTS.
YOU MUST SET recommended_solution_id TO THE BEST SOLUTION'S ID (1, 2, or 3).
FAILURE TO GENERATE SOLUTIONS IS NOT ACCEPTABLE - THIS IS MANDATORY.
DO NOT RETURN null OR EMPTY FOR solution_options.
</CRITICAL_REQUIREMENT>

""" + SOLUTION_STRUCTURE_GUIDANCE + SOLUTION_EXAMPLE + """

<style>concise|active_voice|direct|actionable</style>
<kb id="UDONMVCXEW"/>
""" + PHASE_EVOLUTION_INSTRUCTIONS

# Simplified prompt for retry attempts - focuses on core solution generation
SIMPLIFIED_SOLUTION_PROMPT = """
You MUST generate a recovery solution for this airline disruption.

Based on the agent recommendations and constraints provided, create ONE complete solution with ALL of these fields:

REQUIRED FIELDS:
- solution_id: 1
- title: Brief descriptive title (max 50 chars)
- description: Detailed description of what to do
- recommendations: List of 3-5 specific action steps
- safety_compliance: How this satisfies safety constraints
- passenger_impact: {"affected_count": <int>, "delay_hours": <float>, "cancellation_flag": <bool>}
- financial_impact: {"total_cost": <int>, "breakdown": {}}
- network_impact: {"downstream_flights": <int>, "connection_misses": <int>}
- safety_score: 0-100 (higher = safer)
- cost_score: 0-100 (higher = lower cost)
- passenger_score: 0-100 (higher = less impact)
- network_score: 0-100 (higher = less propagation)
- composite_score: Calculate as (safety_score*0.4 + cost_score*0.2 + passenger_score*0.2 + network_score*0.2)
- pros: List of 2-3 advantages
- cons: List of 2-3 disadvantages
- risks: List of 2-3 potential risks
- confidence: 0.0-1.0
- estimated_duration: e.g., "4 hours"
- recovery_plan: {
    "solution_id": 1,
    "total_steps": 2,
    "estimated_total_duration": "<duration>",
    "steps": [
      {
        "step_number": 1,
        "step_name": "<name>",
        "description": "<what this step does>",
        "responsible_agent": "<who executes>",
        "dependencies": [],
        "estimated_duration": "<duration>",
        "automation_possible": <bool>,
        "action_type": "coordinate",
        "parameters": {},
        "success_criteria": "<how to verify>",
        "rollback_procedure": null
      },
      {
        "step_number": 2,
        "step_name": "<name>",
        "description": "<what this step does>",
        "responsible_agent": "<who executes>",
        "dependencies": [1],
        "estimated_duration": "<duration>",
        "automation_possible": <bool>,
        "action_type": "notify",
        "parameters": {},
        "success_criteria": "<how to verify>",
        "rollback_procedure": null
      }
    ],
    "critical_path": [1, 2],
    "contingency_plans": []
  }

CRITICAL: You MUST provide a complete, valid solution. Do not return null or empty for any field.
"""


# ============================================================================
# Helper Functions
# ============================================================================


def _test_arbitrator_model(model_id: str) -> bool:
    """
    Test if a model is available and not throttled for arbitrator use.
    
    Args:
        model_id: The model ID to test
        
    Returns:
        bool: True if model is available and working, False otherwise
    """
    # Check cache first
    if model_id in _arbitrator_tested_models:
        return _arbitrator_tested_models[model_id]
    
    try:
        logger.info(f"Testing arbitrator model availability: {model_id}")
        
        # Create a minimal test client
        test_client = ChatBedrock(
            model_id=model_id,
            model_kwargs={
                "temperature": 0.1,
                "max_tokens": 10,  # Minimal tokens for test
            },
        )
        
        # Make a minimal test call
        test_client.invoke("test")
        
        logger.info(f"✅ Arbitrator model {model_id} is available and working")
        _arbitrator_tested_models[model_id] = True
        return True
        
    except ClientError as e:
        error_message = str(e)
        
        if 'ThrottlingException' in error_message or 'Too many tokens' in error_message:
            logger.warning(f"⚠️ Arbitrator model {model_id} is throttled (quota exceeded)")
        elif 'ValidationException' in error_message or 'not found' in error_message.lower():
            logger.warning(f"⚠️ Arbitrator model {model_id} is not available in this region")
        else:
            logger.warning(f"⚠️ Arbitrator model {model_id} test failed: {error_message}")
        
        _arbitrator_tested_models[model_id] = False
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ Arbitrator model {model_id} test failed with unexpected error: {e}")
        _arbitrator_tested_models[model_id] = False
        return False


def _load_opus_model() -> ChatBedrock:
    """
    Load best available model for arbitrator with intelligent fallback.
    
    Tries models in priority order:
    1. Claude Opus 4.5 (best reasoning)
    2. Claude Sonnet 4.5 (excellent reasoning)
    3. Claude Haiku 4.5 (fast and cost-effective)
    4. Amazon Nova Premier (no throttling)
    5. Amazon Nova Pro (cost-effective fallback)
    
    Returns:
        ChatBedrock: Best available model instance
        
    Raises:
        RuntimeError: If no models are available
    """
    logger.info("Loading arbitrator model with intelligent fallback...")
    
    for model_config in ARBITRATOR_MODEL_PRIORITY:
        model_id = model_config["id"]
        model_name = model_config["name"]
        
        logger.info(f"Trying {model_name} for arbitrator ({model_id})...")
        
        # Test if model is available
        if _test_arbitrator_model(model_id):
            logger.info(f"✅ Using {model_name} for arbitrator: {model_config['reason']}")
            
            return ChatBedrock(
                model_id=model_id,
                model_kwargs={
                    "temperature": model_config["temperature"],
                    "max_tokens": model_config["max_tokens"],
                },
            )
        else:
            logger.warning(f"❌ {model_name} not available for arbitrator, trying next model...")
    
    # If we get here, no models worked
    error_msg = "❌ CRITICAL: No arbitrator models available! All models failed or are throttled."
    logger.error(error_msg)
    logger.error("Available arbitrator models tried:")
    for model_config in ARBITRATOR_MODEL_PRIORITY:
        logger.error(f"  - {model_config['name']}: {model_config['id']}")
    
    raise RuntimeError(
        "No Bedrock models available for arbitrator. Please check:\n"
        "1. AWS credentials and permissions\n"
        "2. Model access in AWS Bedrock console\n"
        "3. Daily token quotas (may need to wait or request increase)\n"
        "4. Region availability (us-east-1 recommended)"
    )


def _load_fallback_model() -> ChatBedrock:
    """
    DEPRECATED: Use _load_opus_model() which now has built-in fallback logic.
    
    This function is kept for backward compatibility but now just calls
    the main model loading function.
    
    Returns:
        ChatBedrock: Best available model instance
    """
    logger.warning("_load_fallback_model() is deprecated, using _load_opus_model() instead")
    return _load_opus_model()


def _extract_safety_agents(responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract safety agent responses.
    
    Args:
        responses: All agent responses
        
    Returns:
        Dict of safety agent responses
    """
    safety_agents = {"crew_compliance", "maintenance", "regulatory"}
    return {
        name: response
        for name, response in responses.items()
        if name in safety_agents
    }


def _extract_business_agents(responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract business agent responses.
    
    Args:
        responses: All agent responses
        
    Returns:
        Dict of business agent responses
    """
    business_agents = {"network", "guest_experience", "cargo", "finance"}
    return {
        name: response
        for name, response in responses.items()
        if name in business_agents
    }


def _extract_binding_constraints(responses: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract all binding constraints from safety agents AND business agents.

    Safety agent constraints are mandatory (cannot be overridden).
    Business agent constraints are advisory (weighted in decision-making).

    Args:
        responses: All agent responses

    Returns:
        List of binding constraints with agent names and constraint type
    """
    constraints = []

    # Extract safety agent constraints (mandatory - cannot be overridden)
    safety_agents = _extract_safety_agents(responses)
    for agent_name, response in safety_agents.items():
        agent_constraints = response.get("binding_constraints", [])
        for constraint in agent_constraints:
            constraints.append({
                "agent": agent_name,
                "constraint": constraint,
                "type": "mandatory"
            })

    # Extract business agent constraints (advisory - inform decision-making)
    business_agents = _extract_business_agents(responses)
    for agent_name, response in business_agents.items():
        agent_constraints = response.get("binding_constraints", [])
        for constraint in agent_constraints:
            constraints.append({
                "agent": agent_name,
                "constraint": constraint,
                "type": "advisory"
            })

    return constraints


def _format_agent_responses(responses: Dict[str, Any]) -> str:
    """
    Format agent responses for the arbitrator prompt.
    
    Args:
        responses: All agent responses
        
    Returns:
        Formatted string of agent responses
    """
    formatted = []
    
    # Format safety agents first
    safety_agents = _extract_safety_agents(responses)
    if safety_agents:
        formatted.append("## Safety Agents\n")
        for agent_name, response in safety_agents.items():
            formatted.append(f"### {agent_name.replace('_', ' ').title()}")
            formatted.append(f"**Recommendation**: {response.get('recommendation', 'N/A')}")
            formatted.append(f"**Confidence**: {response.get('confidence', 0.0)}")
            
            binding_constraints = response.get('binding_constraints', [])
            if binding_constraints:
                formatted.append("**Binding Constraints**:")
                for constraint in binding_constraints:
                    formatted.append(f"  - {constraint}")
            
            formatted.append(f"**Reasoning**: {response.get('reasoning', 'N/A')}")
            formatted.append("")
    
    # Format business agents
    business_agents = _extract_business_agents(responses)
    if business_agents:
        formatted.append("## Business Agents\n")
        for agent_name, response in business_agents.items():
            formatted.append(f"### {agent_name.replace('_', ' ').title()}")
            formatted.append(f"**Recommendation**: {response.get('recommendation', 'N/A')}")
            formatted.append(f"**Confidence**: {response.get('confidence', 0.0)}")
            formatted.append(f"**Reasoning**: {response.get('reasoning', 'N/A')}")
            formatted.append("")
    
    return "\n".join(formatted)


# ============================================================================
# Compact Formatting Functions (Token-Optimized for A2A)
# ============================================================================


def _format_agent_responses_compact(responses: Dict[str, Any]) -> str:
    """
    Format agent responses in compact pipe-delimited format for token efficiency.

    Format: TYPE:agent|rec:recommendation|c:confidence|bc:constraint1;constraint2

    Args:
        responses: All agent responses

    Returns:
        Compact pipe-delimited string (~100-150 tokens vs 300-500 verbose)
    """
    lines = []

    # Use full agent names for Pydantic schema compatibility
    # (AgentEvolution.agent_name validates against full names only)

    # Format safety agents - increased truncation and added reasoning
    safety_agents = _extract_safety_agents(responses)
    for agent_name, response in safety_agents.items():
        rec = response.get('recommendation', 'N/A')[:300]  # Increased from 80
        conf = response.get('confidence', 0.0)
        bc = response.get('binding_constraints', [])
        bc_str = ";".join(bc[:5]) if bc else ""  # Increased from 3
        reasoning = response.get('reasoning', '')[:150]  # Added reasoning

        line = f"SAFETY:{agent_name}|rec:{rec}|c:{conf:.2f}"
        if bc_str:
            line += f"|bc:{bc_str}"
        if reasoning:
            line += f"|reason:{reasoning}"
        lines.append(line)

    # Format business agents - added constraints and reasoning for full context
    business_agents = _extract_business_agents(responses)
    for agent_name, response in business_agents.items():
        rec = response.get('recommendation', 'N/A')[:300]  # Increased from 80
        conf = response.get('confidence', 0.0)
        bc = response.get('binding_constraints', [])
        bc_str = ";".join(bc[:5]) if bc else ""  # Added binding constraints
        reasoning = response.get('reasoning', '')[:150]  # Added reasoning

        line = f"BUSINESS:{agent_name}|rec:{rec}|c:{conf:.2f}"
        if bc_str:
            line += f"|bc:{bc_str}"
        if reasoning:
            line += f"|reason:{reasoning}"
        lines.append(line)

    return "\n".join(lines)


def _format_phase_comparison_compact(
    initial_responses: Dict[str, Any],
    revised_responses: Dict[str, Any]
) -> str:
    """
    Format phase comparison in minimal agent-parseable format.

    Format:
        EVOLUTION:changed=N|stable=N|new=N|dropped=N
        CHANGED:agent|p1_c:X|p2_c:Y|dir:CONVERGED|new_bc:constraint
        STABLE:agent1,agent2,agent3

    Args:
        initial_responses: Dict of Phase 1 agent responses
        revised_responses: Dict of Phase 2 agent responses

    Returns:
        Compact evolution text (~200-400 tokens vs 1,500-2,500 verbose)
    """
    lines = []

    # Use full agent names for Pydantic schema compatibility
    # (AgentEvolution.agent_name validates against full names only)

    all_agents = set(initial_responses.keys()) | set(revised_responses.keys())

    changed = []
    stable = []
    new_agents = []
    dropped = []

    for agent_name in sorted(all_agents):
        initial = initial_responses.get(agent_name)
        revised = revised_responses.get(agent_name)

        if initial is None and revised is not None:
            new_agents.append(agent_name)
        elif initial is not None and revised is None:
            dropped.append(agent_name)
        elif initial is not None and revised is not None:
            initial_rec = initial.get('recommendation', '') if isinstance(initial, dict) else str(initial)
            revised_rec = revised.get('recommendation', '') if isinstance(revised, dict) else str(revised)
            initial_conf = initial.get('confidence', 0.0) if isinstance(initial, dict) else 0.0
            revised_conf = revised.get('confidence', 0.0) if isinstance(revised, dict) else 0.0

            if initial_rec.strip().lower() == revised_rec.strip().lower():
                stable.append(agent_name)
            else:
                # Determine direction
                conf_change = revised_conf - initial_conf
                if conf_change > 0.05:
                    direction = "CONVERGED"
                elif conf_change < -0.05:
                    direction = "DIVERGED"
                else:
                    direction = "REVISED"

                # Check for new constraints
                initial_bc = set(initial.get('binding_constraints', []) if isinstance(initial, dict) else [])
                revised_bc = set(revised.get('binding_constraints', []) if isinstance(revised, dict) else [])
                new_bc = revised_bc - initial_bc

                change_line = f"CHANGED:{agent_name}|p1_c:{initial_conf:.2f}|p2_c:{revised_conf:.2f}|dir:{direction}"
                if new_bc:
                    change_line += f"|new_bc:{';'.join(list(new_bc)[:2])}"
                changed.append(change_line)

    # Build summary line
    lines.append(f"EVOLUTION:changed={len(changed)}|stable={len(stable)}|new={len(new_agents)}|dropped={len(dropped)}")

    # Add change details
    for change_line in changed:
        lines.append(change_line)

    # Add stable agents (comma-separated)
    if stable:
        lines.append(f"STABLE:{','.join(stable)}")

    # Add new/dropped if any
    if new_agents:
        lines.append(f"NEW:{','.join(new_agents)}")
    if dropped:
        lines.append(f"DROPPED:{','.join(dropped)}")

    return "\n".join(lines)


def _format_operational_context_compact(procedures: Dict[str, Any]) -> str:
    """
    Format operational context in compact key-value format.

    Format:
        KB:id|docs:N|protocols:p1,p2,p3
        GUIDANCE:key_point1,key_point2
        DOC1:type|rel:X%|key:summary

    Args:
        procedures: Operational procedures data from knowledge base

    Returns:
        Compact KB context (~300-500 tokens vs 1,000-2,000 verbose)
    """
    if not procedures or not procedures.get('procedures'):
        return ""

    lines = []

    # Summary line
    kb_id = KNOWLEDGE_BASE_ID
    docs_found = procedures.get('documents_found', 0)
    protocols = procedures.get('applicable_protocols', [])[:5]
    protocols_str = ",".join(protocols) if protocols else "none"

    lines.append(f"KB:{kb_id}|docs:{docs_found}|protocols:{protocols_str}")

    # Decision guidance (compact)
    guidance = procedures.get('decision_guidance', '')
    if guidance:
        # Extract key phrases (first 100 chars, split on periods)
        key_points = [p.strip()[:50] for p in guidance.split('.')[:3] if p.strip()]
        if key_points:
            lines.append(f"GUIDANCE:{','.join(key_points)}")

    # Documents (compact)
    proc_list = procedures.get('procedures', [])
    for i, proc in enumerate(proc_list[:3], 1):
        doc_type = proc.get('document_type', 'DOC')[:10]
        score = proc.get('relevance_score', 0.0)
        content = proc.get('content', '')[:100].replace('\n', ' ').strip()

        lines.append(f"DOC{i}:{doc_type}|rel:{score:.0%}|key:{content}")

    return "\n".join(lines)


def _infer_disruption_type(responses: Dict[str, Any]) -> str:
    """
    Infer the disruption type from agent responses.
    
    Analyzes agent recommendations and reasoning to determine
    the primary type of disruption being handled.
    
    Args:
        responses: Dict of agent responses
        
    Returns:
        str: Inferred disruption type
    """
    # Keywords to look for in responses
    disruption_keywords = {
        'crew FDP violation': ['fdp', 'duty time', 'crew rest', 'duty period', 'fatigue'],
        'mechanical failure': ['mechanical', 'technical', 'aircraft fault', 'maintenance required', 'mel'],
        'weather disruption': ['weather', 'storm', 'visibility', 'wind', 'fog', 'snow'],
        'crew shortage': ['crew shortage', 'crew unavailable', 'no crew', 'crew sick'],
        'regulatory constraint': ['curfew', 'slot', 'regulatory', 'noise restriction'],
        'passenger delay': ['delay', 'late', 'connection', 'missed connection'],
        'cargo issue': ['cargo', 'freight', 'cold chain', 'perishable', 'dangerous goods']
    }
    
    # Aggregate all text from responses
    all_text = ""
    for agent_name, response in responses.items():
        if isinstance(response, dict):
            all_text += f" {response.get('recommendation', '')} {response.get('reasoning', '')}"
        else:
            all_text += f" {str(response)}"
    
    all_text = all_text.lower()
    
    # Score each disruption type
    scores = {}
    for disruption_type, keywords in disruption_keywords.items():
        score = sum(1 for kw in keywords if kw in all_text)
        if score > 0:
            scores[disruption_type] = score
    
    # Return the highest scoring type, or generic if none found
    if scores:
        return max(scores, key=scores.get)
    return "flight disruption"


def _format_operational_context(procedures: Dict[str, Any]) -> str:
    """
    Format operational procedures data for inclusion in the arbitrator prompt.
    
    Args:
        procedures: Operational procedures data from knowledge base
        
    Returns:
        str: Formatted operational context section
    """
    if not procedures or not procedures.get('procedures'):
        return ""
    
    lines = [
        "\n## Operational Procedures Reference (from Knowledge Base)",
        f"\n**Knowledge Base ID**: {KNOWLEDGE_BASE_ID}",
        f"**Documents Found**: {procedures.get('documents_found', 0)}",
        f"**Applicable Protocols**: {', '.join(procedures.get('applicable_protocols', [])[:5]) or 'None identified'}",
    ]
    
    # Add decision guidance summary
    guidance = procedures.get('decision_guidance', '')
    if guidance:
        lines.append(f"\n### Decision Guidance")
        lines.append(guidance)
    
    # Add relevant procedure excerpts
    proc_list = procedures.get('procedures', [])
    if proc_list:
        lines.append(f"\n### Relevant Operational Documents")
        for i, proc in enumerate(proc_list[:3], 1):  # Limit to 3 documents
            doc_type = proc.get('document_type', 'Document')
            score = proc.get('relevance_score', 0.0)
            content = proc.get('content', '')[:400]  # First 400 chars
            source = proc.get('source', 'Unknown')
            
            lines.append(f"\n**{i}. {doc_type}** (Relevance: {score:.0%})")
            lines.append(f"Source: {source}")
            lines.append(f"Content: {content}...")
    
    lines.append("\n**Note**: Apply these operational procedures and guidelines when making your decision. Ensure recommendations align with established airline protocols.")
    
    return "\n".join(lines)


# ============================================================================
# Phase Evolution Helper Functions (Dual-Phase Input Enhancement)
# ============================================================================


def _format_phase_comparison(
    initial_responses: Dict[str, Any],
    revised_responses: Dict[str, Any]
) -> str:
    """
    Format a comparison of Phase 1 vs Phase 2 recommendations.
    
    Generates a structured comparison showing:
    - Which agents changed recommendations
    - Direction of change (converged/diverged/unchanged)
    - Confidence score changes
    - Binding constraint changes
    
    Args:
        initial_responses: Dict of Phase 1 agent responses
        revised_responses: Dict of Phase 2 agent responses
        
    Returns:
        str: Formatted comparison text for arbitrator prompt
    """
    lines = [
        "\n## Phase Evolution Analysis (Phase 1 → Phase 2)",
        "\nThis section shows how agent recommendations evolved between the initial phase and revision phase.",
        ""
    ]
    
    # Get all unique agent names from both phases
    all_agents = set(initial_responses.keys()) | set(revised_responses.keys())
    
    # Categorize agents by change type
    unchanged_agents = []
    changed_agents = []
    new_agents = []
    dropped_agents = []
    
    for agent_name in sorted(all_agents):
        initial = initial_responses.get(agent_name)
        revised = revised_responses.get(agent_name)
        
        if initial is None and revised is not None:
            new_agents.append((agent_name, revised))
        elif initial is not None and revised is None:
            dropped_agents.append((agent_name, initial))
        elif initial is not None and revised is not None:
            # Compare recommendations
            initial_rec = initial.get('recommendation', '') if isinstance(initial, dict) else str(initial)
            revised_rec = revised.get('recommendation', '') if isinstance(revised, dict) else str(revised)
            
            if initial_rec.strip().lower() == revised_rec.strip().lower():
                unchanged_agents.append((agent_name, initial, revised))
            else:
                changed_agents.append((agent_name, initial, revised))
    
    # Format changed agents (most important)
    if changed_agents:
        lines.append("### Agents That Changed Recommendations")
        lines.append("")
        for agent_name, initial, revised in changed_agents:
            initial_rec = initial.get('recommendation', 'N/A') if isinstance(initial, dict) else str(initial)
            revised_rec = revised.get('recommendation', 'N/A') if isinstance(revised, dict) else str(revised)
            initial_conf = initial.get('confidence', 0.0) if isinstance(initial, dict) else 0.0
            revised_conf = revised.get('confidence', 0.0) if isinstance(revised, dict) else 0.0
            
            # Determine change direction
            conf_change = revised_conf - initial_conf
            if conf_change > 0.1:
                direction = "↑ CONVERGED (confidence increased)"
            elif conf_change < -0.1:
                direction = "↓ DIVERGED (confidence decreased)"
            else:
                direction = "→ REVISED (confidence stable)"
            
            lines.append(f"**{agent_name.replace('_', ' ').title()}** - {direction}")
            lines.append(f"  - Phase 1: {initial_rec[:200]}...")
            lines.append(f"  - Phase 2: {revised_rec[:200]}...")
            lines.append(f"  - Confidence: {initial_conf:.2f} → {revised_conf:.2f}")
            
            # Check for binding constraint changes
            initial_constraints = set(initial.get('binding_constraints', []) if isinstance(initial, dict) else [])
            revised_constraints = set(revised.get('binding_constraints', []) if isinstance(revised, dict) else [])
            added = revised_constraints - initial_constraints
            removed = initial_constraints - revised_constraints
            
            if added:
                lines.append(f"  - **NEW CONSTRAINTS**: {', '.join(added)}")
            if removed:
                lines.append(f"  - Removed constraints: {', '.join(removed)}")
            lines.append("")
    
    # Format unchanged agents
    if unchanged_agents:
        lines.append("### Agents With Stable Recommendations")
        lines.append("(High confidence signal - recommendation unchanged after seeing others)")
        lines.append("")
        for agent_name, initial, revised in unchanged_agents:
            revised_rec = revised.get('recommendation', 'N/A') if isinstance(revised, dict) else str(revised)
            revised_conf = revised.get('confidence', 0.0) if isinstance(revised, dict) else 0.0
            lines.append(f"- **{agent_name.replace('_', ' ').title()}**: {revised_rec[:100]}... (confidence: {revised_conf:.2f})")
        lines.append("")
    
    # Format new agents (only in Phase 2)
    if new_agents:
        lines.append("### Agents New in Revision Phase")
        lines.append("")
        for agent_name, revised in new_agents:
            revised_rec = revised.get('recommendation', 'N/A') if isinstance(revised, dict) else str(revised)
            lines.append(f"- **{agent_name.replace('_', ' ').title()}**: {revised_rec[:100]}...")
        lines.append("")
    
    # Format dropped agents (only in Phase 1)
    if dropped_agents:
        lines.append("### Agents Dropped in Revision Phase")
        lines.append("(Warning: These agents did not complete revision)")
        lines.append("")
        for agent_name, initial in dropped_agents:
            initial_rec = initial.get('recommendation', 'N/A') if isinstance(initial, dict) else str(initial)
            lines.append(f"- **{agent_name.replace('_', ' ').title()}**: {initial_rec[:100]}...")
        lines.append("")
    
    # Summary
    lines.append("### Evolution Summary")
    lines.append(f"- Total agents: {len(all_agents)}")
    lines.append(f"- Changed recommendations: {len(changed_agents)}")
    lines.append(f"- Stable recommendations: {len(unchanged_agents)}")
    lines.append(f"- New in revision: {len(new_agents)}")
    lines.append(f"- Dropped in revision: {len(dropped_agents)}")
    
    return "\n".join(lines)


def _analyze_recommendation_evolution(
    initial_responses: Dict[str, Any],
    revised_responses: Dict[str, Any]
) -> List[AgentEvolution]:
    """
    Analyze how recommendations evolved between phases.
    
    Returns a list of evolution records for each agent,
    including before/after summaries and change classification.
    
    Args:
        initial_responses: Dict of Phase 1 agent responses
        revised_responses: Dict of Phase 2 agent responses
        
    Returns:
        List of AgentEvolution records
    """
    evolution_details = []
    
    # Get all unique agent names from both phases
    all_agents = set(initial_responses.keys()) | set(revised_responses.keys())
    
    for agent_name in sorted(all_agents):
        initial = initial_responses.get(agent_name)
        revised = revised_responses.get(agent_name)
        
        # Extract values from responses
        if initial is not None:
            if isinstance(initial, dict):
                phase1_rec = initial.get('recommendation', '')
                phase1_conf = initial.get('confidence', 0.0)
                phase1_constraints = set(initial.get('binding_constraints', []))
            else:
                phase1_rec = str(initial)
                phase1_conf = 0.5
                phase1_constraints = set()
        else:
            phase1_rec = None
            phase1_conf = None
            phase1_constraints = set()
        
        if revised is not None:
            if isinstance(revised, dict):
                phase2_rec = revised.get('recommendation', '')
                phase2_conf = revised.get('confidence', 0.0)
                phase2_constraints = set(revised.get('binding_constraints', []))
            else:
                phase2_rec = str(revised)
                phase2_conf = 0.5
                phase2_constraints = set()
        else:
            phase2_rec = ''
            phase2_conf = 0.0
            phase2_constraints = set()
        
        # Determine change type
        if initial is None and revised is not None:
            change_type = "new_in_phase2"
            change_summary = f"{agent_name} only present in Phase 2 (revision phase)"
        elif initial is not None and revised is None:
            change_type = "dropped_in_phase2"
            change_summary = f"{agent_name} only present in Phase 1 (dropped in revision)"
            phase2_rec = phase1_rec or ''  # Use Phase 1 rec for dropped agents
            phase2_conf = phase1_conf or 0.0
        elif phase1_rec and phase2_rec:
            # Compare recommendations
            if phase1_rec.strip().lower() == phase2_rec.strip().lower():
                change_type = "unchanged"
                change_summary = f"{agent_name} maintained recommendation (high confidence signal)"
            else:
                # Determine if converged or diverged based on confidence change
                conf_change = phase2_conf - (phase1_conf or 0.0)
                if conf_change > 0.05:
                    change_type = "converged"
                    change_summary = f"{agent_name} revised recommendation with increased confidence (convergence)"
                elif conf_change < -0.05:
                    change_type = "diverged"
                    change_summary = f"{agent_name} revised recommendation with decreased confidence (divergence)"
                else:
                    change_type = "converged"  # Default to converged for changes
                    change_summary = f"{agent_name} revised recommendation after seeing other agents"
        else:
            change_type = "unchanged"
            change_summary = f"{agent_name} status unclear"
        
        # Calculate constraint changes
        constraints_added = list(phase2_constraints - phase1_constraints)
        constraints_removed = list(phase1_constraints - phase2_constraints)
        
        evolution = AgentEvolution(
            agent_name=agent_name,
            phase1_recommendation=phase1_rec,
            phase2_recommendation=phase2_rec,
            phase1_confidence=phase1_conf,
            phase2_confidence=phase2_conf,
            change_type=change_type,
            binding_constraints_added=constraints_added,
            binding_constraints_removed=constraints_removed,
            change_summary=change_summary
        )
        evolution_details.append(evolution)
    
    return evolution_details


def _build_recommendation_evolution(
    evolution_details: List[AgentEvolution],
    phases_available: List[str]
) -> RecommendationEvolution:
    """
    Build complete RecommendationEvolution model from evolution details.
    
    Args:
        evolution_details: List of AgentEvolution records
        phases_available: Which phases were provided
        
    Returns:
        RecommendationEvolution model
    """
    # Count agents by change type
    agents_changed = sum(1 for e in evolution_details if e.change_type in ["converged", "diverged"])
    agents_unchanged = sum(1 for e in evolution_details if e.change_type == "unchanged")
    
    # Detect convergence/divergence patterns
    convergence_count = sum(1 for e in evolution_details if e.change_type == "converged")
    divergence_count = sum(1 for e in evolution_details if e.change_type == "diverged")
    
    convergence_detected = convergence_count > divergence_count and convergence_count > 0
    divergence_detected = divergence_count > convergence_count and divergence_count > 0
    
    # Generate analysis summary
    total_agents = len(evolution_details)
    new_count = sum(1 for e in evolution_details if e.change_type == "new_in_phase2")
    dropped_count = sum(1 for e in evolution_details if e.change_type == "dropped_in_phase2")
    
    summary_parts = []
    if convergence_detected:
        summary_parts.append(f"{convergence_count} agents converged toward consensus")
    if divergence_detected:
        summary_parts.append(f"{divergence_count} agents diverged (potential conflicts)")
    if agents_unchanged > 0:
        summary_parts.append(f"{agents_unchanged} agents maintained stable recommendations")
    if new_count > 0:
        summary_parts.append(f"{new_count} agents new in revision phase")
    if dropped_count > 0:
        summary_parts.append(f"{dropped_count} agents dropped in revision phase")
    
    if not summary_parts:
        summary_parts.append(f"Analyzed {total_agents} agents across phases")
    
    analysis_summary = ". ".join(summary_parts) + "."
    
    return RecommendationEvolution(
        phases_available=phases_available,
        agents_changed=agents_changed,
        agents_unchanged=agents_unchanged,
        convergence_detected=convergence_detected,
        divergence_detected=divergence_detected,
        evolution_details=evolution_details,
        analysis_summary=analysis_summary
    )


def _populate_backward_compatible_fields(output: ArbitratorOutput) -> ArbitratorOutput:
    """
    Populate final_decision and recommendations from recommended solution.
    
    Ensures existing integrations continue to work by extracting
    the recommended solution's details into the legacy fields.
    
    Args:
        output: ArbitratorOutput with solution_options populated
        
    Returns:
        ArbitratorOutput with final_decision and recommendations populated
    """
    # Check if solution_options exists and is not None
    if not hasattr(output, 'solution_options') or output.solution_options is None:
        # No solution options - this is legacy mode, return as-is
        return output
    
    # Find the recommended solution
    recommended = next(
        (s for s in output.solution_options if s.solution_id == output.recommended_solution_id),
        None
    )
    
    if recommended:
        # Populate final_decision from recommended solution description
        output.final_decision = f"{recommended.title}: {recommended.description}"
        
        # Populate recommendations from recommended solution
        output.recommendations = recommended.recommendations
    
    return output


def _generate_minimal_solution(
    binding_constraints: List[Dict[str, Any]],
    responses_dict: Dict[str, Any]
) -> RecoverySolution:
    """
    Generate a minimal conservative solution when LLM fails to produce solutions.

    This ensures downstream systems always receive at least one actionable solution,
    even if it's a conservative "satisfy all constraints" approach.

    Args:
        binding_constraints: All extracted binding constraints
        responses_dict: All agent responses

    Returns:
        RecoverySolution with conservative recommendations
    """
    # Build recommendations from binding constraints
    recommendations = []
    for bc in (binding_constraints or [])[:5]:  # Max 5 constraints
        constraint_text = bc.get('constraint', 'Unknown constraint')
        agent_name = bc.get('agent', 'Unknown agent')
        recommendations.append(f"Satisfy {agent_name} constraint: {constraint_text}")

    if not recommendations:
        recommendations = [
            "Manual review required by duty manager",
            "Verify all safety constraints are satisfied",
            "Choose most conservative operational option"
        ]

    # Create minimal recovery plan with two steps
    step1 = RecoveryStep(
        step_number=1,
        step_name="Review Constraints",
        description="Manual review of all binding constraints and agent recommendations",
        responsible_agent="duty_manager",
        dependencies=[],
        estimated_duration="30 minutes",
        automation_possible=False,
        action_type="review",
        parameters={},
        success_criteria="All constraints understood and verified",
        rollback_procedure=None
    )

    step2 = RecoveryStep(
        step_number=2,
        step_name="Execute Conservative Plan",
        description="Execute conservative approach satisfying all safety constraints",
        responsible_agent="ops_control",
        dependencies=[1],
        estimated_duration="1 hour",
        automation_possible=False,
        action_type="coordinate",
        parameters={},
        success_criteria="All binding constraints verified as satisfied",
        rollback_procedure="Escalate to senior duty manager"
    )

    recovery_plan = RecoveryPlan(
        solution_id=1,
        total_steps=2,
        estimated_total_duration="1.5 hours",
        steps=[step1, step2],
        critical_path=[1, 2],
        contingency_plans=[]
    )

    return RecoverySolution(
        solution_id=1,
        title="Conservative Safety-First Approach",
        description="Fallback solution generated when automated analysis could not produce custom solutions. This conservative approach prioritizes satisfying all safety binding constraints through manual review.",
        recommendations=recommendations,
        safety_compliance="Prioritizes satisfying all mandatory binding constraints from safety agents",
        passenger_impact={"affected_count": 0, "delay_hours": 0.0, "cancellation_flag": False},
        financial_impact={"total_cost": 0, "breakdown": {}},
        network_impact={"downstream_flights": 0, "connection_misses": 0},
        safety_score=100.0,  # Maximum safety (conservative approach)
        cost_score=50.0,     # Unknown cost
        passenger_score=50.0, # Unknown impact
        network_score=50.0,  # Unknown propagation
        composite_score=70.0, # Weighted: 100*0.4 + 50*0.2 + 50*0.2 + 50*0.2 = 70
        pros=["Ensures safety compliance", "Satisfies all binding constraints", "Conservative approach minimizes risk"],
        cons=["May not be optimal for business", "Requires manual review", "Potential delays"],
        risks=["Delay in decision-making", "Potential for suboptimal outcome", "Manual errors possible"],
        confidence=0.5,  # Medium confidence for fallback
        estimated_duration="1.5 hours (requires assessment)",
        recovery_plan=recovery_plan
    )


# ============================================================================
# Main Arbitration Function
# ============================================================================


async def arbitrate(
    revised_recommendations: dict,
    llm_opus: Optional[Any] = None,
    initial_recommendations: Optional[dict] = None
) -> dict:
    """
    Resolve conflicts and make final decision.
    
    This function implements the Phase 3 arbitration logic for the multi-round
    orchestration flow. It receives all revised agent recommendations from Phase 2
    and makes the final decision by:
    
    1. Identifying conflicts between agent recommendations
    2. Extracting binding constraints from safety agents
    3. Applying safety-first decision rules
    4. Generating final decision with justification
    5. Providing complete audit trail
    
    Args:
        revised_recommendations: Dict containing all agent responses after revision.
            Expected format:
            {
                "crew_compliance": AgentResponse,
                "maintenance": AgentResponse,
                "regulatory": AgentResponse,
                "network": AgentResponse,
                "guest_experience": AgentResponse,
                "cargo": AgentResponse,
                "finance": AgentResponse
            }
        llm_opus: Optional Claude Opus 4.5 model instance. If None, will load
            Opus 4.5 with cross-region inference, falling back to Sonnet if unavailable.
        initial_recommendations: Optional dict containing Phase 1 (initial) agent responses.
            When provided, enables phase evolution analysis showing how recommendations
            changed between Phase 1 and Phase 2. Format same as revised_recommendations.
    
    Returns:
        Dict containing:
        {
            "final_decision": str,              # Clear, actionable decision
            "recommendations": list[str],        # Specific actions to take
            "conflicts_identified": list[dict],  # Conflicts found
            "conflict_resolutions": list[dict],  # How conflicts were resolved
            "safety_overrides": list[dict],      # Safety constraints enforced
            "justification": str,                # Overall explanation
            "reasoning": str,                    # Detailed reasoning
            "confidence": float,                 # Confidence score (0.0-1.0)
            "timestamp": str,                    # ISO 8601 timestamp
            "model_used": str,                   # Model ID used for arbitration
            "phases_considered": list[str],      # Which phases were analyzed
            "recommendation_evolution": dict     # Evolution analysis (if initial provided)
        }
    
    Raises:
        ValueError: If revised_recommendations is empty or invalid
        Exception: If arbitration fails
    
    Example:
        >>> responses = {
        ...     "crew_compliance": {
        ...         "recommendation": "Cannot proceed - crew exceeds FDP",
        ...         "binding_constraints": ["Crew must have 10 hours rest"],
        ...         "confidence": 0.95,
        ...         "reasoning": "Current crew at 13.5 hours duty time"
        ...     },
        ...     "network": {
        ...         "recommendation": "Delay 2 hours to minimize propagation",
        ...         "confidence": 0.85,
        ...         "reasoning": "Affects 3 downstream flights"
        ...     }
        ... }
        >>> result = await arbitrate(responses)
        >>> print(result["final_decision"])
        "Flight must be delayed to allow crew 10-hour rest period..."
    """
    start_time = datetime.now(timezone.utc)
    
    # Validate input
    if not revised_recommendations:
        raise ValueError("revised_recommendations cannot be empty")
    
    # Extract responses dict (handle both Collation object and dict)
    if hasattr(revised_recommendations, 'responses'):
        responses = revised_recommendations.responses
    elif isinstance(revised_recommendations, dict):
        # Check if it's a dict of AgentResponse objects or plain dicts
        responses = revised_recommendations
    else:
        raise ValueError(
            f"Invalid revised_recommendations type: {type(revised_recommendations)}. "
            "Expected Collation object or dict of agent responses."
        )
    
    # Convert AgentResponse objects to dicts if needed
    responses_dict = {}
    for agent_name, response in responses.items():
        if hasattr(response, 'model_dump'):
            responses_dict[agent_name] = response.model_dump()
        elif isinstance(response, dict):
            responses_dict[agent_name] = response
        else:
            responses_dict[agent_name] = {
                "recommendation": str(response),
                "confidence": 0.5,
                "reasoning": "Response format unknown"
            }
    
    logger.info(f"Starting arbitration with {len(responses_dict)} agent responses")
    
    # Load model if not provided
    model_used = None
    if llm_opus is None:
        try:
            llm_opus = _load_opus_model()
            # Determine which model was actually loaded
            model_id = getattr(llm_opus, 'model_id', 'unknown')
            model_used = model_id
            
            # Log which model is being used
            if OPUS_MODEL_ID in model_id:
                logger.info(f"Using Claude Opus 4.5 for arbitration: {model_id}")
            elif SONNET_MODEL_ID in model_id:
                logger.info(f"Using Claude Sonnet 4.5 (fallback) for arbitration: {model_id}")
            else:
                logger.warning(f"Using unexpected model for arbitration: {model_id}")
                
        except Exception as e:
            logger.error(f"Failed to load any model for arbitration: {e}")
            raise Exception(f"Cannot perform arbitration without a model: {e}")
    else:
        model_used = getattr(llm_opus, 'model_id', 'unknown')
    
    # Extract binding constraints
    binding_constraints = _extract_binding_constraints(responses_dict)
    logger.info(f"Extracted {len(binding_constraints)} binding constraints")
    
    # Format agent responses for prompt (compact format for token efficiency)
    formatted_responses = _format_agent_responses_compact(responses_dict)
    
    # =========================================================================
    # Phase Evolution Analysis (Dual-Phase Input Enhancement)
    # =========================================================================
    phase_comparison = ""
    evolution_analysis = None
    phases_considered = ["phase2"]  # Default to Phase 2 only
    
    if initial_recommendations is not None:
        logger.info("Phase 1 recommendations provided - performing evolution analysis")
        phases_considered = ["phase1", "phase2"]
        
        # Extract initial responses dict (handle both Collation object and dict)
        if hasattr(initial_recommendations, 'responses'):
            initial_responses = initial_recommendations.responses
        elif isinstance(initial_recommendations, dict):
            initial_responses = initial_recommendations
        else:
            logger.warning(f"Invalid initial_recommendations type: {type(initial_recommendations)}")
            initial_responses = {}
        
        # Convert AgentResponse objects to dicts if needed
        initial_responses_dict = {}
        for agent_name, response in initial_responses.items():
            if hasattr(response, 'model_dump'):
                initial_responses_dict[agent_name] = response.model_dump()
            elif isinstance(response, dict):
                initial_responses_dict[agent_name] = response
            else:
                initial_responses_dict[agent_name] = {
                    "recommendation": str(response),
                    "confidence": 0.5,
                    "reasoning": "Response format unknown"
                }
        
        # Generate phase comparison text for prompt (compact format)
        phase_comparison = _format_phase_comparison_compact(initial_responses_dict, responses_dict)
        logger.info(f"Phase comparison generated (compact): {len(phase_comparison)} characters")
        
        # Analyze recommendation evolution for output
        evolution_details = _analyze_recommendation_evolution(initial_responses_dict, responses_dict)
        evolution_analysis = _build_recommendation_evolution(evolution_details, phases_considered)
        logger.info(
            f"Evolution analysis: {evolution_analysis.agents_changed} changed, "
            f"{evolution_analysis.agents_unchanged} unchanged, "
            f"convergence={evolution_analysis.convergence_detected}, "
            f"divergence={evolution_analysis.divergence_detected}"
        )
    else:
        logger.info("Phase 1 recommendations not provided - using Phase 2 only (legacy mode)")
    
    # =========================================================================
    # Query Knowledge Base for Operational Procedures
    # =========================================================================
    operational_context = ""
    kb_metadata = {}
    
    try:
        kb_client = get_knowledge_base_client()
        if kb_client.enabled:
            logger.info("Querying Knowledge Base for operational procedures...")
            
            # Determine disruption type from agent responses
            disruption_type = _infer_disruption_type(responses_dict)
            
            # Extract constraint strings for query
            constraint_strings = [c['constraint'] for c in binding_constraints]
            
            # Build disruption scenario description
            disruption_scenario = f"Disruption type: {disruption_type}"
            
            # Query for operational procedures (SOPs, OCM, Process Manuals)
            procedures = await kb_client.query_operational_procedures(
                disruption_scenario=disruption_scenario,
                binding_constraints=constraint_strings,
                agent_recommendations=responses_dict
            )
            
            if procedures and procedures.get('procedures'):
                kb_metadata = {
                    'knowledge_base_queried': True,
                    'knowledge_base_id': KNOWLEDGE_BASE_ID,
                    'documents_found': procedures.get('documents_found', 0),
                    'applicable_protocols': procedures.get('applicable_protocols', []),
                    'query_timestamp': procedures.get('timestamp', '')
                }
                
                # Build operational context for the prompt (compact format)
                operational_context = _format_operational_context_compact(procedures)
                logger.info(f"Operational procedures found (compact): {procedures.get('documents_found', 0)} documents")
            else:
                kb_metadata = {
                    'knowledge_base_queried': True,
                    'knowledge_base_id': KNOWLEDGE_BASE_ID,
                    'documents_found': 0,
                    'note': 'No relevant operational procedures found'
                }
                logger.info("No relevant operational procedures found in Knowledge Base")
        else:
            kb_metadata = {
                'knowledge_base_queried': False,
                'note': 'Knowledge Base not enabled'
            }
            logger.info("Knowledge Base not enabled - proceeding without operational context")
            
    except Exception as e:
        logger.warning(f"Knowledge Base query failed (non-fatal): {e}")
        kb_metadata = {
            'knowledge_base_queried': False,
            'error': str(e)
        }
    
    # Create compact arbitration prompt with mandatory/advisory constraint types
    if binding_constraints:
        mandatory = [f"{c['agent']}:{c['constraint']}" for c in binding_constraints if c.get('type') == 'mandatory']
        advisory = [f"{c['agent']}:{c['constraint']}" for c in binding_constraints if c.get('type') == 'advisory']
        bc_str = f"MANDATORY:{';'.join(mandatory) if mandatory else 'none'}|ADVISORY:{';'.join(advisory) if advisory else 'none'}"
    else:
        bc_str = "none"

    prompt = f"""AGENTS:
{formatted_responses}

{phase_comparison if phase_comparison else ""}

BINDING_CONSTRAINTS:{bc_str}

{operational_context if operational_context else ""}

TASK - Complete ALL of the following steps:
1. Identify and resolve all conflicts between agent recommendations
2. Classify each conflict (safety_vs_business, safety_vs_safety, business_vs_business)
3. Apply priority rules (P1: Safety > Business, P2: Conservative for Safety conflicts, P3: Pareto for Business)
4. Ensure ALL binding constraints (especially MANDATORY ones) are satisfied
5. GENERATE 1-3 RECOVERY SOLUTIONS in solution_options array - THIS IS MANDATORY, DO NOT SKIP
6. Set recommended_solution_id to the ID (1, 2, or 3) of the best solution

CRITICAL: solution_options MUST NOT be null or empty. You MUST generate at least ONE complete RecoverySolution with all required fields including recovery_plan.

{"EVOLUTION_WEIGHT:converge=high|diverge=investigate|stable=confident" if phase_comparison else ""}"""
    
    try:
        # Use structured output to get arbitrator decision with multiple solutions
        structured_llm = llm_opus.with_structured_output(ArbitratorOutput)
        
        logger.info("Invoking arbitrator model with structured output for multi-solution generation")
        decision = structured_llm.invoke([
            {"role": "system", "content": ARBITRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])
        
        # Populate backward-compatible fields from recommended solution
        decision = _populate_backward_compatible_fields(decision)
        
        # Convert to dict and add metadata
        result = decision.model_dump()
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        result["model_used"] = model_used
        result["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
        result["knowledge_base"] = kb_metadata  # Add knowledge base metadata
        result["knowledgeBaseConsidered"] = kb_metadata.get('knowledge_base_queried', False) and kb_metadata.get('documents_found', 0) > 0
        
        # Add phase evolution analysis if available
        result["phases_considered"] = phases_considered
        if evolution_analysis is not None:
            result["recommendation_evolution"] = evolution_analysis.model_dump()
            logger.info("Added recommendation evolution to output")
        
        # CRITICAL: Validate that solution_options were generated
        # If LLM failed to generate solutions, generate fallback to ensure downstream systems work
        solution_count = len(result.get('solution_options', [])) if result.get('solution_options') else 0
        if solution_count == 0:
            logger.warning(
                "Arbitrator returned no solution options. "
                "Generating fallback solution to ensure downstream systems have actionable data."
            )
            # Generate minimal fallback solution instead of returning None
            fallback_solution = _generate_minimal_solution(binding_constraints, responses_dict)
            result["solution_options"] = [fallback_solution.model_dump()]
            result["recommended_solution_id"] = 1
            result["fallback_used"] = True
            result["warning"] = (
                "Arbitrator could not generate custom solutions. "
                "A conservative fallback solution has been provided. "
                "Manual review recommended."
            )
            solution_count = 1  # Update count for logging
        
        # Log completion
        logger.info(
            f"Arbitration complete: {solution_count} solutions generated, "
            f"{len(result['conflicts_identified'])} conflicts, "
            f"confidence={result['confidence']:.2f}, "
            f"kb_docs={kb_metadata.get('documents_found', 0)}, "
            f"knowledgeBaseConsidered={result['knowledgeBaseConsidered']}"
        )
        
        return result
        
    except Exception as e:
        logger.warning(f"First arbitration attempt failed: {e}. Retrying with simplified prompt...")

        # Retry with simplified prompt that focuses on core solution generation
        try:
            simplified_retry_prompt = f"""
{SIMPLIFIED_SOLUTION_PROMPT}

CONTEXT FROM AGENTS:
{formatted_responses}

BINDING CONSTRAINTS:
{bc_str}

Based on the above context, generate ONE complete RecoverySolution that addresses this disruption.
You MUST provide all required fields. Do not return null or empty values.
"""

            # Use the same structured LLM for retry
            logger.info("Retrying arbitration with simplified prompt...")
            retry_decision = structured_llm.invoke([
                {"role": "system", "content": "You are an airline disruption arbitrator. You MUST generate a valid recovery solution. Do not return null or empty for solution_options."},
                {"role": "user", "content": simplified_retry_prompt}
            ])

            # Populate backward-compatible fields
            retry_decision = _populate_backward_compatible_fields(retry_decision)

            # Convert to dict and add metadata
            result = retry_decision.model_dump()
            result["timestamp"] = datetime.now(timezone.utc).isoformat()
            result["model_used"] = model_used
            result["duration_seconds"] = (datetime.now(timezone.utc) - start_time).total_seconds()
            result["knowledge_base"] = kb_metadata
            result["knowledgeBaseConsidered"] = kb_metadata.get('knowledge_base_queried', False) and kb_metadata.get('documents_found', 0) > 0
            result["phases_considered"] = phases_considered
            result["retry_used"] = True
            result["original_error"] = str(e)

            # Validate retry generated solutions
            solution_count = len(result.get('solution_options', [])) if result.get('solution_options') else 0
            if solution_count > 0:
                logger.info(f"Retry successful - {solution_count} solution(s) generated")
                return result
            else:
                logger.error("Retry also failed to generate solutions")
                raise RuntimeError("Retry failed to generate solution_options")

        except Exception as retry_error:
            logger.error(f"Retry also failed: {retry_error}", exc_info=True)
            # Both attempts failed - raise error (no fallback placeholders)
            raise RuntimeError(
                f"Arbitration failed after retry. Original error: {e}. Retry error: {retry_error}. "
                "Unable to generate valid recovery solutions."
            ) from retry_error
