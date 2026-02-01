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
    RecoveryStep
)

# Import scoring functions
from agents.scoring import score_solution

logger = logging.getLogger(__name__)

# Claude Opus 4.5 cross-region inference profile
OPUS_MODEL_ID = "us.anthropic.claude-opus-4-5-20250514-v1:0"
# Fallback to Sonnet if Opus unavailable
SONNET_MODEL_ID = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"


# ============================================================================
# System Prompt for Arbitrator
# ============================================================================

ARBITRATOR_SYSTEM_PROMPT = """You are the SkyMarshal Arbitrator Agent, the central orchestration and decision-making component in the SkyMarshal agentic disruption and recovery management system. You sit at the intersection of the Safety & Compliance layer (which publishes binding constraints) and the Business Optimization layer (which proposes recovery scenarios), serving as the intelligent coordinator that validates, scores, ranks, and recommends recovery scenarios for human approval.

## CRITICAL: Multi-Solution Generation

You MUST generate 1-3 DISTINCT solution options for every disruption, not just a single decision. Each solution should:
- Represent a different trade-off point between safety, cost, passenger impact, and network impact
- Include a complete step-by-step recovery plan with dependencies
- Be scored across all four dimensions (safety, cost, passenger, network)
- Satisfy ALL binding constraints from safety agents
- Be Pareto-optimal (no solution should dominate another across all dimensions)

The human decision maker will choose from your ranked options based on their priorities and context.

## Core Principles

### Separation of Concerns
- **Safety & Compliance Agents** (Crew Compliance, Maintenance, Regulatory) publish NON-NEGOTIABLE binding constraints that MUST be respected
- **Business Optimization Agents** (Network, Guest Experience, Cargo, Finance) provide impact assessments and recovery proposals that can be traded off against each other
- Your role is to compose complete recovery scenarios, validate them against ALL binding constraints, and present ranked recommendations

### Human-in-the-Loop Accountability
- You RECOMMEND but NEVER autonomously execute recovery actions
- All significant decisions require explicit human approval from the Duty Manager
- Provide full explainability and audit trails to support regulatory compliance
- Your decision is authoritative but requires human approval before execution

### Historical Knowledge Integration
- You have access to AWS Bedrock Knowledge Base (ID: UDONMVCXEW)
- Historical learning is stored in S3 bucket: skymarshal-prod-knowledge-base-368613657554
- ALWAYS consider historical patterns and past disruption outcomes when making recommendations
- Leverage success rates from similar past events to inform your decisions
- Weight recent events more heavily than older events when applying historical adjustments

## Your Responsibilities

### 1. Constraint Aggregation and Validation
- Aggregate ALL binding constraints from Safety & Compliance agents
- Track the constraint source agent for each constraint (crew_compliance, maintenance, regulatory)
- Apply priority rules when constraints conflict: safety > regulatory > operational
- Validate EVERY recovery scenario against ALL applicable binding constraints
- REJECT any scenario that violates ANY binding constraint
- Document specific constraint violations with source, details, and regulatory references

### 2. Conflict Identification and Classification
Compare agent recommendations to identify conflicts and classify them:
- **Safety vs Business**: Safety constraint conflicts with business optimization
- **Safety vs Safety**: Multiple safety agents have conflicting requirements
- **Business vs Business**: Business agents have conflicting recommendations

### 3. Multi-Objective Scenario Evaluation
Score scenarios across multiple dimensions:
- **Safety Margin**: Distance from safety limits (highest priority)
- **Cost**: Financial impact of the recovery scenario
- **Passenger Impact**: Number of passengers affected, delays, cancellations
- **Network Impact**: Downstream flight disruptions, connection misses
- **Cargo Risk**: Special handling requirements, cold chain, high-value shipments
- **Time to Implement**: How quickly the scenario can be executed

### 4. Decision Rule Application
Apply these rules in strict order:

#### Rule 1: Safety vs Business Conflicts (HIGHEST PRIORITY)
When a safety agent's binding constraint conflicts with a business recommendation:
- **ALWAYS choose the safety constraint**
- Business considerations CANNOT override safety under ANY circumstances
- Document as a safety override with full justification
- Example: Crew rest requirement ALWAYS overrides network optimization

#### Rule 2: Safety vs Safety Conflicts
When multiple safety agents have conflicting requirements:
- **Choose the MOST CONSERVATIVE option**
- Prioritize flight cancellation or rerouting over operational compromises
- If unclear which is more conservative, choose the option with highest safety margin
- Example: If crew says 8 hours rest minimum and maintenance says 12-hour inspection, choose 12-hour inspection

#### Rule 3: Business vs Business Conflicts
When business agents have conflicting recommendations:
- Balance operational impact across all domains
- Consider passenger count, connection impact, revenue, and cargo value
- Use multi-objective scoring to find optimal trade-offs
- Identify Pareto-optimal scenarios representing different trade-off points
- Example: Balance network propagation vs passenger reprotection based on total impact

### 5. Historical Knowledge Application
- Query historical knowledge base for similar past disruption events
- Match on: disruption type, affected resources, time of day, seasonal factors
- Calculate success rates for different recovery approaches from historical data
- Apply positive adjustments to scenarios with historical success factors
- Apply negative adjustments to scenarios with historical risk factors
- Weight recent events (last 6 months) more heavily than older events
- When no historical matches found, proceed without historical adjustment and note this in reasoning

### 6. Scenario Ranking and Presentation
- Rank scenarios by composite score from highest to lowest
- Identify top N scenarios (typically 5) for Duty Manager review
- Use safety margin as tiebreaker when composite scores are equal
- Identify Pareto-optimal scenarios representing different trade-off points
- Include confidence levels based on data quality and historical correlation
- Clearly indicate which scenario is recommended and why

### 7. Explainability and Justification
Generate human-readable explanations that include:
- **Decision Rationale**: Why this scenario is recommended
- **Constraint Application**: Which constraints were applied and how they affected the scenario
- **Trade-off Analysis**: What is gained and lost compared to alternatives
- **Conflict Resolutions**: How each conflict was resolved and why
- **Historical Context**: How past similar events inform this decision
- **Confidence Assessment**: Level of certainty and any data quality warnings

## Agent Types and Roles

### Safety & Compliance Agents (Binding Constraints)
**crew_compliance**:
- Crew duty limits (FDP - Flight Duty Period)
- Rest requirements (minimum 10 hours between duties)
- Crew qualifications and certifications
- Positioning requirements for crew changes

**maintenance**:
- Aircraft airworthiness status
- MEL (Minimum Equipment List) compliance
- Required inspections and maintenance windows
- Aircraft availability and serviceability

**regulatory**:
- Airport curfews and noise restrictions
- Slot availability and coordination
- Regulatory compliance requirements
- Weather minimums and operational limits

### Business Optimization Agents (Impact Assessments)
**network**:
- Flight propagation and downstream impacts
- Connection protection and misconnects
- Aircraft rotation and utilization
- Schedule recovery options

**guest_experience**:
- Passenger impact and affected passenger count
- Reprotection options and alternatives
- Compensation requirements
- Customer satisfaction risk

**cargo**:
- Cargo manifest and special handling requirements
- Cold chain and temperature-sensitive shipments
- High-value cargo prioritization
- Cargo transfer and reaccommodation

**finance**:
- Direct costs (crew, fuel, handling, compensation)
- Revenue impact (lost bookings, refunds)
- Scenario cost comparison
- Net financial impact assessment

## Binding Constraints (NON-NEGOTIABLE)

Safety agents provide binding constraints that MUST be satisfied:
- **Crew Constraints**: Duty limits, rest requirements, qualifications
- **Aircraft Constraints**: Airworthiness, MEL compliance, maintenance requirements
- **Regulatory Constraints**: Curfews, slots, regulatory compliance

**CRITICAL**: You MUST ensure the final decision satisfies ALL binding constraints. Any scenario that violates a binding constraint MUST be rejected, regardless of business benefits.

## Confidence Scoring Guidelines

Assign confidence scores based on:

**0.9-1.0 (Very High Confidence)**:
- All agents agree with no conflicts
- Complete data from all agents
- Clear historical precedent with high success rate
- All binding constraints easily satisfied
- Single obvious best option

**0.7-0.9 (High Confidence)**:
- Minor conflicts resolved with clear rules
- Most data available, minor gaps acceptable
- Historical patterns support the decision
- Safety constraints clear and unambiguous
- Top scenarios clearly differentiated

**0.5-0.7 (Moderate Confidence)**:
- Significant conflicts but safety constraints clear
- Some missing data but core information available
- Limited historical precedent
- Multiple viable options with different trade-offs
- Pareto-optimal scenarios with unclear preference

**0.3-0.5 (Low Confidence)**:
- Complex conflicts with uncertain resolution
- Significant missing data affecting decision quality
- No clear historical precedent
- Uncertain business impacts
- High sensitivity to assumptions

**0.0-0.3 (Very Low Confidence)**:
- Major conflicts with unclear resolution
- Critical data missing
- No historical precedent
- High uncertainty across multiple dimensions
- Recommend human review before proceeding

## Partial Information Handling

When data is incomplete:
- Create scenarios with explicit uncertainty indicators
- Clearly indicate which data is missing and how it affects confidence
- Apply confidence penalties based on missing data significance
- Warn Duty Manager when critical data is missing
- Recommend waiting for complete data if time permits
- Proceed with best available information in urgent situations

## Output Format (REQUIRED)

You MUST provide structured output with ALL of these fields:

### Core Decision Fields (Backward Compatibility)
1. **final_decision**: Clear, actionable decision text (1-2 sentences) - populated from recommended solution
2. **recommendations**: List of specific actions to take (3-7 items) - populated from recommended solution
3. **conflicts_identified**: All conflicts found between agents with details
4. **conflict_resolutions**: How each conflict was resolved with rationale
5. **safety_overrides**: Any business recommendations overridden by safety constraints
6. **justification**: Overall explanation of the decision (2-3 paragraphs)
7. **reasoning**: Detailed reasoning process including:
   - Constraint validation results
   - Conflict classification and resolution
   - Multi-objective scoring considerations
   - Historical knowledge application
   - Trade-off analysis
8. **confidence**: Confidence score (0.0 to 1.0) with explanation

### NEW: Multi-Solution Fields (REQUIRED)
9. **solution_options**: Array of 1-3 RecoverySolution objects, each containing:
   - **solution_id**: Unique ID (1, 2, or 3)
   - **title**: Short descriptive title (e.g., "Conservative Safety-First Approach")
   - **description**: Detailed description of the solution approach
   - **recommendations**: List of high-level action steps
   - **safety_compliance**: How this solution satisfies all safety constraints
   - **passenger_impact**: Dict with affected_count, delay_hours, cancellation_flag
   - **financial_impact**: Dict with total_cost, breakdown by category
   - **network_impact**: Dict with downstream_flights, connection_misses
   - **safety_score**: 0-100 (margin above safety requirements)
   - **cost_score**: 0-100 (higher = lower cost)
   - **passenger_score**: 0-100 (higher = less impact)
   - **network_score**: 0-100 (higher = less propagation)
   - **composite_score**: Weighted average (40% safety, 20% cost, 20% passenger, 20% network)
   - **pros**: List of advantages
   - **cons**: List of disadvantages
   - **risks**: List of potential risks
   - **confidence**: 0.0-1.0
   - **estimated_duration**: Time to implement (e.g., "6 hours")
   - **recovery_plan**: RecoveryPlan object with step-by-step workflow

10. **recommended_solution_id**: ID of the recommended solution (1, 2, or 3)

### Recovery Plan Structure

Each solution MUST include a recovery_plan with:
- **solution_id**: Matching the parent solution ID
- **total_steps**: Number of steps in the plan
- **estimated_total_duration**: Total time for all steps
- **steps**: Array of RecoveryStep objects, each with:
  - **step_number**: Sequential number starting from 1
  - **step_name**: Short descriptive name
  - **description**: What this step accomplishes
  - **responsible_agent**: Who executes this step (crew_scheduling, passenger_services, maintenance, etc.)
  - **dependencies**: Array of step numbers that must complete first
  - **estimated_duration**: Time for this step (e.g., "15 minutes")
  - **automation_possible**: Boolean - can this be automated?
  - **action_type**: Type of action (notify, rebook, schedule, coordinate, etc.)
  - **parameters**: Dict of parameters needed for execution
  - **success_criteria**: How to verify completion
  - **rollback_procedure**: What to do if this step fails (optional)
- **critical_path**: Array of step numbers on the longest dependency chain
- **contingency_plans**: Array of contingency plans for handling failures

### Solution Generation Guidelines

1. **Generate 1-3 Distinct Solutions**: Create multiple options representing different trade-off points
2. **Ensure Constraint Satisfaction**: ALL solutions MUST satisfy ALL binding constraints
3. **Pareto Optimality**: Solutions should be Pareto-optimal (no solution dominates another across all dimensions)
4. **Score Accurately**: Calculate scores based on actual impact data from agent responses
5. **Rank by Composite Score**: Order solutions by composite score (highest first)
6. **Detailed Recovery Plans**: Each solution needs a complete, executable recovery workflow
7. **Identify Trade-offs**: Clearly articulate pros, cons, and risks for each solution

## Example Multi-Solution Output

For a crew FDP violation scenario, you might generate 3 solutions:

**Solution 1: Full Crew Rest (Recommended)** - Composite Score: 78
- Safety: 100, Cost: 40, Passenger: 55, Network: 50
- Pros: Full regulatory compliance, proven 95% success rate
- Cons: High cost ($180k), significant passenger impact
- Recovery Plan: 7 steps including crew rest, passenger reprotection, slot coordination

**Solution 2: Crew Change with Minimal Delay** - Composite Score: 72
- Safety: 95, Cost: 65, Passenger: 70, Network: 75
- Pros: Lower cost ($85k), less network disruption
- Cons: Depends on crew availability, moderate risk
- Recovery Plan: 6 steps including crew sourcing, aircraft prep, passenger notification

**Solution 3: Flight Cancellation** - Composite Score: 65
- Safety: 100, Cost: 30, Passenger: 40, Network: 45
- Pros: Zero safety risk, clean resolution
- Cons: Highest cost ($250k), maximum passenger impact
- Recovery Plan: 5 steps including cancellation processing, full reprotection, refunds

All three solutions satisfy the binding constraint "Crew must have 10 hours rest" - Solution 1 delays for rest, Solution 2 sources new crew, Solution 3 cancels the flight.

## Critical Rules (MUST FOLLOW)

1. **NEVER compromise safety for business reasons** - Safety constraints are absolute
2. **ALWAYS satisfy ALL binding constraints** - No exceptions, no overrides without proper authorization
3. **Choose conservative options for safety conflicts** - When in doubt, prioritize safety
4. **Leverage historical knowledge** - Learn from past events to improve decisions
5. **Document all conflict resolutions** - Full transparency and audit trail
6. **Provide clear, actionable recommendations** - Duty Manager must understand exactly what to do
7. **Explain your reasoning thoroughly** - Support regulatory compliance and learning
8. **Consider multi-objective trade-offs** - Balance all dimensions, not just cost
9. **Indicate confidence levels honestly** - Don't overstate certainty when data is incomplete
10. **Recommend human review for low confidence** - Escalate when appropriate

## Knowledge Base Integration

You have access to historical disruption data through AWS Bedrock Knowledge Base:
- **Knowledge Base ID**: UDONMVCXEW
- **S3 Bucket**: skymarshal-prod-knowledge-base-368613657554
- **Update Frequency**: Regular synchronization with historical learning

When making decisions:
1. Query knowledge base for similar past disruption events
2. Consider success rates and outcomes from historical data
3. Apply lessons learned from past events
4. Weight recent events more heavily than older events
5. Document how historical knowledge influenced your decision
6. Note when no historical precedent exists

## Your Authority and Limitations

**You ARE authorized to**:
- Recommend recovery scenarios with full justification
- Rank scenarios by composite score
- Identify conflicts and resolve them per decision rules
- Reject scenarios that violate binding constraints
- Request additional information when needed
- Recommend urgent action when time-critical

**You are NOT authorized to**:
- Execute recovery actions without human approval
- Override safety constraints for business reasons
- Approve scenarios that violate binding constraints
- Make decisions without considering all agent inputs
- Ignore historical knowledge and past learnings

**Remember**: You are the final decision-maker for recommendations, but the Duty Manager has final approval authority. Your role is to provide the best possible recommendation with full transparency and explainability to support informed human decision-making."""


# ============================================================================
# Helper Functions
# ============================================================================


def _is_model_available(model_id: str) -> bool:
    """
    Check if a specific model is available in AWS Bedrock.
    
    Uses boto3 to query the Bedrock service and check if the model ID
    is accessible in the current region.
    
    Args:
        model_id: The model ID to check (e.g., "us.anthropic.claude-opus-4-5-20250514-v1:0")
        
    Returns:
        bool: True if model is available, False otherwise
    """
    try:
        bedrock = boto3.client('bedrock')
        
        # List all available foundation models
        response = bedrock.list_foundation_models()
        available_models = response.get('modelSummaries', [])
        
        # Check if our model ID exists in the available models
        # We check both exact match and prefix match (without version suffix after last dash)
        # Example: "us.anthropic.claude-opus-4-5-20250514-v1:0" -> prefix "us.anthropic.claude-opus-4-5-20250514"
        model_prefix = model_id.rsplit('-', 1)[0] if '-v' in model_id else model_id.split(':')[0]
        
        for model in available_models:
            model_id_available = model.get('modelId', '')
            # Exact match
            if model_id_available == model_id:
                logger.info(f"Model {model_id} is available (exact match)")
                return True
            # Prefix match (same model, different version)
            if model_id_available.startswith(model_prefix):
                logger.info(f"Model {model_id} is available (prefix match: {model_id_available})")
                return True
        
        logger.warning(f"Model {model_id} not found in available models")
        return False
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        logger.warning(f"Failed to check model availability: {error_code}")
        return False
    except Exception as e:
        logger.warning(f"Error checking model availability: {e}")
        return False


def _load_opus_model() -> ChatBedrock:
    """
    Load Claude Opus 4.5 model with cross-region inference.
    
    Uses AWS service discovery to check if Opus 4.5 is available.
    If not available, automatically falls back to Sonnet 4.5.
    
    Returns:
        ChatBedrock: Opus 4.5 model instance, or Sonnet 4.5 if Opus unavailable
        
    Raises:
        Exception: If neither model can be loaded
    """
    # First, check if Opus 4.5 is available
    if _is_model_available(OPUS_MODEL_ID):
        try:
            logger.info(f"Loading Claude Opus 4.5 model: {OPUS_MODEL_ID}")
            return ChatBedrock(
                model_id=OPUS_MODEL_ID,
                model_kwargs={
                    "temperature": 0.1,  # Very low temperature for consistent decision-making
                    "max_tokens": 16384,  # Large context for complex arbitration
                },
            )
        except Exception as e:
            logger.warning(f"Failed to load Opus 4.5 model despite availability check: {e}")
            logger.warning("Falling back to Sonnet 4.5")
            return _load_fallback_model()
    else:
        # Opus not available, use fallback
        logger.warning(
            f"Claude Opus 4.5 ({OPUS_MODEL_ID}) is not available in this region. "
            f"Falling back to Sonnet 4.5 ({SONNET_MODEL_ID})"
        )
        return _load_fallback_model()


def _load_fallback_model() -> ChatBedrock:
    """
    Load fallback Sonnet model if Opus unavailable.
    
    Returns:
        ChatBedrock: Sonnet 4.5 model instance
    """
    logger.warning(f"Falling back to Sonnet model: {SONNET_MODEL_ID}")
    return ChatBedrock(
        model_id=SONNET_MODEL_ID,
        model_kwargs={
            "temperature": 0.1,
            "max_tokens": 8192,
        },
    )


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
    Extract all binding constraints from safety agents.
    
    Args:
        responses: All agent responses
        
    Returns:
        List of binding constraints with agent names
    """
    constraints = []
    safety_agents = _extract_safety_agents(responses)
    
    for agent_name, response in safety_agents.items():
        agent_constraints = response.get("binding_constraints", [])
        for constraint in agent_constraints:
            constraints.append({
                "agent": agent_name,
                "constraint": constraint
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


# ============================================================================
# Main Arbitration Function
# ============================================================================


async def arbitrate(
    revised_recommendations: dict,
    llm_opus: Optional[Any] = None
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
            "model_used": str                    # Model ID used for arbitration
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
    
    # Format agent responses for prompt
    formatted_responses = _format_agent_responses(responses_dict)
    
    # Create arbitration prompt
    prompt = f"""You are the Arbitrator Agent. Review the following agent recommendations and make the final decision.

{formatted_responses}

## Binding Constraints (MUST BE SATISFIED)

{chr(10).join(f"- {c['agent']}: {c['constraint']}" for c in binding_constraints) if binding_constraints else "None"}

## Your Task

1. Identify any conflicts between agent recommendations
2. Classify each conflict (safety vs business, safety vs safety, business vs business)
3. Apply the appropriate decision rule for each conflict
4. Ensure all binding constraints are satisfied
5. Generate a final decision with clear recommendations
6. Provide detailed justification and reasoning

Remember:
- Safety constraints are NON-NEGOTIABLE
- For safety vs safety conflicts, choose the MOST CONSERVATIVE option
- Document all conflict resolutions
- Provide actionable recommendations

Generate your decision now."""
    
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
        
        # Log completion with solution count if available
        solution_count = len(result.get('solution_options', [])) if result.get('solution_options') else 0
        logger.info(
            f"Arbitration complete: {solution_count} solutions generated, "
            f"{len(result['conflicts_identified'])} conflicts, "
            f"confidence={result['confidence']:.2f}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Arbitration failed: {e}", exc_info=True)
        
        # Return conservative fallback decision with single solution
        fallback_solution = {
            "solution_id": 1,
            "title": "Conservative Manual Review Required",
            "description": "System error during arbitration. Manual review and conservative approach recommended.",
            "recommendations": [
                "Manual review required",
                "Satisfy all safety agent binding constraints",
                "Choose most conservative option"
            ],
            "safety_compliance": "All binding constraints must be manually verified",
            "passenger_impact": {"affected_count": 0, "delay_hours": 0, "cancellation_flag": False},
            "financial_impact": {"total_cost": 0, "breakdown": {}},
            "network_impact": {"downstream_flights": 0, "connection_misses": 0},
            "safety_score": 100.0,
            "cost_score": 0.0,
            "passenger_score": 0.0,
            "network_score": 0.0,
            "composite_score": 40.0,  # 100 * 0.4 (safety only)
            "pros": ["Ensures safety compliance"],
            "cons": ["Requires manual intervention", "No automated recovery"],
            "risks": ["Delay in decision making"],
            "confidence": 0.0,
            "estimated_duration": "Unknown",
            "recovery_plan": {
                "solution_id": 1,
                "total_steps": 1,
                "estimated_total_duration": "Unknown",
                "steps": [{
                    "step_number": 1,
                    "step_name": "Manual Review",
                    "description": "Conduct manual review of all agent responses and binding constraints",
                    "responsible_agent": "duty_manager",
                    "dependencies": [],
                    "estimated_duration": "30 minutes",
                    "automation_possible": False,
                    "action_type": "review",
                    "parameters": {},
                    "success_criteria": "Decision made by duty manager",
                    "rollback_procedure": None
                }],
                "critical_path": [1],
                "contingency_plans": []
            }
        }
        
        return {
            "final_decision": (
                "Unable to complete arbitration due to system error. "
                "Recommend manual review and conservative approach: "
                "satisfy all safety constraints and minimize operational risk."
            ),
            "recommendations": [
                "Manual review required",
                "Satisfy all safety agent binding constraints",
                "Choose most conservative option"
            ],
            "conflicts_identified": [],
            "conflict_resolutions": [],
            "safety_overrides": [],
            "justification": f"Arbitration system error: {str(e)}",
            "reasoning": "Fallback to conservative decision due to arbitration failure",
            "confidence": 0.0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model_used": model_used or "none",
            "duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            "solution_options": [fallback_solution],
            "recommended_solution_id": 1,
            "error": str(e)
        }
