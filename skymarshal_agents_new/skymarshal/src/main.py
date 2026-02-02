"""SkyMarshal Multi-Agent Orchestrator"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Tuple

from bedrock_agentcore import BedrockAgentCoreApp

from agents import (
    analyze_cargo,
    analyze_crew_compliance,
    analyze_finance,
    analyze_guest_experience,
    analyze_maintenance,
    analyze_network,
    analyze_regulatory,
)
from agents.arbitrator import arbitrate
from agents.schemas import AgentResponse, Collation
from checkpoint import CheckpointSaver, ThreadManager
from mcp_client.client import get_streamable_http_mcp_client
from model.load import load_model

# Configure comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Initialize AgentCore app
app = BedrockAgentCoreApp()

# Initialize checkpoint infrastructure
checkpoint_mode = os.getenv("CHECKPOINT_MODE", "development")
checkpoint_saver = CheckpointSaver(mode=checkpoint_mode)
thread_manager = ThreadManager(checkpoint_saver=checkpoint_saver)

logger.info(f"✅ Checkpoint infrastructure initialized: mode={checkpoint_mode}")
logger.info(f"   Backend: {checkpoint_saver.backend.__class__.__name__}")

# Agent registry for routing
AGENT_REGISTRY: Dict[str, Callable] = {
    "crew_compliance": analyze_crew_compliance,
    "maintenance": analyze_maintenance,
    "regulatory": analyze_regulatory,
    "network": analyze_network,
    "guest_experience": analyze_guest_experience,
    "cargo": analyze_cargo,
    "finance": analyze_finance,
}

# Safety and business agent groups
SAFETY_AGENTS: List[Tuple[str, Callable]] = [
    ("crew_compliance", analyze_crew_compliance),
    ("maintenance", analyze_maintenance),
    ("regulatory", analyze_regulatory),
]

BUSINESS_AGENTS: List[Tuple[str, Callable]] = [
    ("network", analyze_network),
    ("guest_experience", analyze_guest_experience),
    ("cargo", analyze_cargo),
    ("finance", analyze_finance),
]


def augment_prompt_phase1(user_prompt: str) -> str:
    """
    Augment user prompt with Phase 1 instructions.
    
    Adds instruction for initial recommendation while preserving
    the original user prompt content unchanged.
    
    Args:
        user_prompt: Original natural language prompt from user
        
    Returns:
        str: Augmented prompt with phase-specific instructions
        
    Example:
        >>> original = "Flight EY123 on Jan 20th had a mechanical failure"
        >>> augmented = augment_prompt_phase1(original)
        >>> print(augmented)
        Flight EY123 on Jan 20th had a mechanical failure
        
        Please analyze this disruption and provide your initial recommendation from your domain perspective.
    """
    instruction = "Please analyze this disruption and provide your initial recommendation from your domain perspective."
    return f"{user_prompt}\n\n{instruction}"


def augment_prompt_phase2(user_prompt: str, initial_collation: dict) -> str:
    """
    Augment user prompt with Phase 2 instructions and initial recommendations.
    
    Adds instruction for revision round along with other agents' initial
    recommendations, while preserving the original user prompt content.
    
    Args:
        user_prompt: Original natural language prompt from user
        initial_collation: Collated initial recommendations from all agents
        
    Returns:
        str: Augmented prompt with phase-specific instructions and collation
        
    Example:
        >>> original = "Flight EY123 on Jan 20th had a mechanical failure"
        >>> collation = {
        ...     "responses": {
        ...         "crew_compliance": {
        ...             "recommendation": "Crew is available",
        ...             "confidence": 0.95
        ...         }
        ...     }
        ... }
        >>> augmented = augment_prompt_phase2(original, collation)
        >>> # Returns original prompt + other agents' recommendations + instruction
    """
    instruction = "Review other agents' recommendations and revise if needed."
    
    # Format initial recommendations for context
    recommendations_text = "\n\nOther agents have provided the following recommendations:\n"
    for agent_name, response in initial_collation.get("responses", {}).items():
        recommendations_text += f"\n{agent_name.upper()}:\n"
        recommendations_text += f"  Recommendation: {response.get('recommendation', 'N/A')}\n"
        recommendations_text += f"  Confidence: {response.get('confidence', 'N/A')}\n"
        if response.get('binding_constraints'):
            recommendations_text += f"  Binding Constraints: {response.get('binding_constraints')}\n"
    
    return f"{user_prompt}{recommendations_text}\n\n{instruction}"


async def run_agent_safely(
    agent_name: str,
    agent_fn: Callable[[dict, Any, list], Awaitable[dict]],
    payload: dict,
    llm: Any,
    mcp_tools: list,
    timeout: int = 60,
    thread_id: str = None,
    checkpoint_saver: CheckpointSaver = None,
) -> dict:
    """
    Run agent with timeout, error handling, and optional checkpoint persistence.

    Args:
        agent_name: Name of the agent
        agent_fn: Agent function to call
        payload: Request payload with natural language prompt
        llm: Model instance
        mcp_tools: MCP tools
        timeout: Timeout in seconds (default 60)
        thread_id: Optional thread identifier for checkpoint persistence
        checkpoint_saver: Optional checkpoint saver for state persistence

    Returns:
        dict: Agent result with status
    """
    start_time = datetime.now()
    
    # Save checkpoint at agent start
    if thread_id and checkpoint_saver:
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id=f"{agent_name}_start",
            state={
                "agent": agent_name,
                "payload": payload,
                "status": "started"
            },
            metadata={
                "agent": agent_name,
                "phase": payload.get("phase", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "status": "started"
            }
        )
        logger.debug(f"   💾 Checkpoint saved: {agent_name}_start")
    
    try:
        logger.info(f"🚀 Starting {agent_name} agent...")
        logger.debug(f"   Payload keys: {list(payload.keys())}")
        logger.debug(f"   MCP tools count: {len(mcp_tools)}")

        result = await asyncio.wait_for(
            agent_fn(payload, llm, mcp_tools), timeout=timeout
        )

        duration = (datetime.now() - start_time).total_seconds()
        # Only set status to success if not already set by agent
        if "status" not in result:
            result["status"] = "success"
        result["duration_seconds"] = duration
        # Always ensure agent name is in result
        result["agent"] = agent_name

        # Save checkpoint at agent completion
        if thread_id and checkpoint_saver:
            await checkpoint_saver.save_checkpoint(
                thread_id=thread_id,
                checkpoint_id=f"{agent_name}_complete",
                state=result,
                metadata={
                    "agent": agent_name,
                    "phase": payload.get("phase", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed",
                    "confidence": result.get("confidence", 0.0),
                    "duration_seconds": duration
                }
            )
            logger.debug(f"   💾 Checkpoint saved: {agent_name}_complete")

        logger.info(f"✅ {agent_name} completed successfully in {duration:.2f}s")
        logger.debug(f"   Result keys: {list(result.keys())}")
        return result

    except asyncio.TimeoutError:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"⏱ {agent_name} timeout after {timeout}s (actual: {duration:.2f}s)"
        )
        
        error_result = {
            "agent": agent_name,
            "status": "timeout",
            "error": f"Agent execution exceeded {timeout} second timeout",
            "duration_seconds": duration,
        }
        
        # Save checkpoint on timeout
        if thread_id and checkpoint_saver:
            await checkpoint_saver.save_checkpoint(
                thread_id=thread_id,
                checkpoint_id=f"{agent_name}_timeout",
                state=error_result,
                metadata={
                    "agent": agent_name,
                    "phase": payload.get("phase", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                    "status": "timeout",
                    "duration_seconds": duration
                }
            )
            logger.debug(f"   💾 Checkpoint saved: {agent_name}_timeout")
        
        return error_result
        
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ {agent_name} error after {duration:.2f}s: {e}")
        logger.exception(f"Full traceback for {agent_name}:")
        
        error_result = {
            "agent": agent_name,
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": duration,
        }
        
        # Save checkpoint on error
        if thread_id and checkpoint_saver:
            await checkpoint_saver.save_checkpoint(
                thread_id=thread_id,
                checkpoint_id=f"{agent_name}_error",
                state=error_result,
                metadata={
                    "agent": agent_name,
                    "phase": payload.get("phase", "unknown"),
                    "timestamp": datetime.now().isoformat(),
                    "status": "error",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": duration
                }
            )
            logger.debug(f"   💾 Checkpoint saved: {agent_name}_error")
        
        return error_result


async def phase1_initial_recommendations(
    user_prompt: str,
    llm: Any,
    mcp_tools: list,
    thread_id: str = None,
    checkpoint_saver: CheckpointSaver = None
) -> Collation:
    """
    Phase 1: Initial Recommendations with checkpoint persistence.
    
    Invoke all 7 agents in parallel with the user prompt plus instructions.
    Agents are responsible for extracting flight info and performing lookups.
    
    Saves checkpoints before and after phase execution for failure recovery.
    
    Args:
        user_prompt: Natural language prompt from user
        llm: Model instance
        mcp_tools: MCP tools
        thread_id: Optional thread identifier for checkpoint persistence
        checkpoint_saver: Optional checkpoint saver for state persistence
        
    Returns:
        Collation: Collated initial recommendations with metadata
    """
    logger.info("🔒 Phase 1: Initial Recommendations (parallel execution)")
    
    # Save checkpoint before phase execution
    if thread_id and checkpoint_saver:
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="phase1_start",
            state={"user_prompt": user_prompt},
            metadata={
                "phase": "phase1",
                "status": "started",
                "timestamp": datetime.now().isoformat()
            }
        )
        logger.debug(f"   ✅ Phase 1 start checkpoint saved")
    
    # Augment prompt with phase 1 instructions
    augmented_prompt = augment_prompt_phase1(user_prompt)
    logger.debug(f"   Augmented prompt: {augmented_prompt[:150]}...")
    
    # Create payload with augmented prompt
    payload = {
        "user_prompt": augmented_prompt,
        "phase": "initial"
    }
    
    # Get all agents (safety + business)
    all_agents = SAFETY_AGENTS + BUSINESS_AGENTS
    logger.debug(f"   Agents: {[name for name, _ in all_agents]}")
    
    # Run all agents in parallel with checkpoint support
    phase_start = datetime.now()
    agent_tasks = [
        run_agent_safely(name, fn, payload, llm, mcp_tools, timeout=60, thread_id=thread_id, checkpoint_saver=checkpoint_saver)
        for name, fn in all_agents
    ]
    agent_results = await asyncio.gather(*agent_tasks)
    phase_duration = (datetime.now() - phase_start).total_seconds()
    
    logger.info(f"   Phase 1 completed in {phase_duration:.2f}s")
    
    # Collate responses using Pydantic model
    responses = {}
    for result in agent_results:
        agent_name = result.get("agent", "unknown")
        try:
            # Determine status - use result status if present, otherwise default to success
            status = result.get("status", "success")
            
            # Convert raw result to AgentResponse model
            agent_response = AgentResponse(
                agent_name=agent_name,
                recommendation=result.get("recommendation", "No recommendation provided"),
                confidence=result.get("confidence", 0.0),
                binding_constraints=result.get("binding_constraints", []),
                reasoning=result.get("reasoning", "No reasoning provided"),
                data_sources=result.get("data_sources", []),
                extracted_flight_info=result.get("extracted_flight_info"),
                timestamp=result.get("timestamp", datetime.now().isoformat()),
                status=status,
                duration_seconds=result.get("duration_seconds"),
                error=result.get("error"),
            )
            responses[agent_name] = agent_response
        except Exception as e:
            logger.error(f"   ⚠️  Failed to parse response from {agent_name}: {e}")
            # Create error response
            responses[agent_name] = AgentResponse(
                agent_name=agent_name,
                recommendation="Failed to parse agent response",
                confidence=0.0,
                reasoning=f"Error parsing response: {str(e)}",
                data_sources=[],
                timestamp=datetime.now().isoformat(),
                status="error",
                error=str(e),
            )
    
    # Create collation using Pydantic model
    collation = Collation(
        phase="initial",
        responses=responses,
        timestamp=datetime.now().isoformat(),
        duration_seconds=phase_duration
    )
    
    # Save checkpoint after phase completion
    if thread_id and checkpoint_saver:
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="phase1_complete",
            state=collation.model_dump(),
            metadata={
                "phase": "phase1",
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": phase_duration
            }
        )
        logger.debug(f"   ✅ Phase 1 completion checkpoint saved")
    
    # Log collation summary
    counts = collation.get_agent_count()
    logger.info(f"   Collation: {counts['success']} success, {counts['timeout']} timeout, {counts['error']} error")
    
    return collation


async def phase2_revision_round(
    user_prompt: str,
    initial_collation: Collation,
    llm: Any,
    mcp_tools: list,
    thread_id: str = None,
    checkpoint_saver: CheckpointSaver = None
) -> Collation:
    """
    Phase 2: Revision Round with checkpoint persistence.
    
    Invoke all 7 agents with user prompt, initial recommendations, and revision instructions.
    Agents review others' recommendations and revise their own.
    
    Loads Phase 1 checkpoint and saves Phase 2 checkpoints for failure recovery.
    
    Args:
        user_prompt: Original natural language prompt from user
        initial_collation: Collated initial recommendations from phase 1
        llm: Model instance
        mcp_tools: MCP tools
        thread_id: Optional thread identifier for checkpoint persistence
        checkpoint_saver: Optional checkpoint saver for state persistence
        
    Returns:
        Collation: Collated revised recommendations with metadata
    """
    logger.info("🔄 Phase 2: Revision Round (parallel execution)")
    
    # Save checkpoint before phase execution
    if thread_id and checkpoint_saver:
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="phase2_start",
            state={
                "user_prompt": user_prompt,
                "phase1_results": initial_collation.model_dump()
            },
            metadata={
                "phase": "phase2",
                "status": "started",
                "timestamp": datetime.now().isoformat()
            }
        )
        logger.debug(f"   ✅ Phase 2 start checkpoint saved")
    
    # Convert Collation to dict for augment_prompt_phase2
    initial_collation_dict = {
        "phase": initial_collation.phase,
        "responses": {
            name: response.model_dump() for name, response in initial_collation.responses.items()
        },
        "timestamp": initial_collation.timestamp,
        "duration_seconds": initial_collation.duration_seconds
    }
    
    # Augment prompt with phase 2 instructions and initial collation
    augmented_prompt = augment_prompt_phase2(user_prompt, initial_collation_dict)
    logger.debug(f"   Augmented prompt length: {len(augmented_prompt)} chars")
    
    # Create payload with augmented prompt and other recommendations
    payload = {
        "user_prompt": augmented_prompt,
        "phase": "revision",
        "other_recommendations": {
            name: response.model_dump() for name, response in initial_collation.responses.items()
        }
    }
    
    # Get all agents (safety + business)
    all_agents = SAFETY_AGENTS + BUSINESS_AGENTS
    logger.debug(f"   Agents: {[name for name, _ in all_agents]}")
    
    # Run all agents in parallel with checkpoint support
    phase_start = datetime.now()
    agent_tasks = [
        run_agent_safely(name, fn, payload, llm, mcp_tools, timeout=60, thread_id=thread_id, checkpoint_saver=checkpoint_saver)
        for name, fn in all_agents
    ]
    agent_results = await asyncio.gather(*agent_tasks)
    phase_duration = (datetime.now() - phase_start).total_seconds()
    
    logger.info(f"   Phase 2 completed in {phase_duration:.2f}s")
    
    # Collate responses using Pydantic model
    responses = {}
    for result in agent_results:
        agent_name = result.get("agent", "unknown")
        try:
            # Determine status - use result status if present, otherwise default to success
            status = result.get("status", "success")
            
            # Convert raw result to AgentResponse model
            agent_response = AgentResponse(
                agent_name=agent_name,
                recommendation=result.get("recommendation", "No recommendation provided"),
                confidence=result.get("confidence", 0.0),
                binding_constraints=result.get("binding_constraints", []),
                reasoning=result.get("reasoning", "No reasoning provided"),
                data_sources=result.get("data_sources", []),
                extracted_flight_info=result.get("extracted_flight_info"),
                timestamp=result.get("timestamp", datetime.now().isoformat()),
                status=status,
                duration_seconds=result.get("duration_seconds"),
                error=result.get("error"),
            )
            responses[agent_name] = agent_response
        except Exception as e:
            logger.error(f"   ⚠️  Failed to parse response from {agent_name}: {e}")
            # Create error response
            responses[agent_name] = AgentResponse(
                agent_name=agent_name,
                recommendation="Failed to parse agent response",
                confidence=0.0,
                reasoning=f"Error parsing response: {str(e)}",
                data_sources=[],
                timestamp=datetime.now().isoformat(),
                status="error",
                error=str(e),
            )
    
    # Create collation using Pydantic model
    collation = Collation(
        phase="revision",
        responses=responses,
        timestamp=datetime.now().isoformat(),
        duration_seconds=phase_duration
    )
    
    # Save checkpoint after phase completion
    if thread_id and checkpoint_saver:
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="phase2_complete",
            state=collation.model_dump(),
            metadata={
                "phase": "phase2",
                "status": "completed",
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": phase_duration
            }
        )
        logger.debug(f"   ✅ Phase 2 completion checkpoint saved")
    
    # Log collation summary
    counts = collation.get_agent_count()
    logger.info(f"   Collation: {counts['success']} success, {counts['timeout']} timeout, {counts['error']} error")
    
    return collation


async def phase3_arbitration(
    revised_collation: Collation,
    llm: Any,
    thread_id: str = None,
    checkpoint_saver: CheckpointSaver = None,
    initial_collation: Optional[Collation] = None
) -> dict:
    """
    Phase 3: Arbitration with checkpoint persistence.
    
    Invoke arbitrator with all revised recommendations.
    Arbitrator resolves conflicts and makes final decision.
    
    Loads Phase 1 and Phase 2 checkpoints and saves final decision checkpoint.
    
    Args:
        revised_collation: Collated revised recommendations from phase 2 (Collation model)
        llm: Model instance (Opus 4.5 for arbitrator)
        thread_id: Optional thread identifier for checkpoint persistence
        checkpoint_saver: Optional checkpoint saver for state persistence
        initial_collation: Optional collated initial recommendations from phase 1 (Collation model).
            When provided, enables phase evolution analysis showing how recommendations
            changed between Phase 1 and Phase 2.
        
    Returns:
        dict: Final arbitrated decision
        {
            "phase": "arbitration",
            "final_decision": str,
            "recommendations": list[str],
            "conflicts_identified": list[dict],
            "conflict_resolutions": list[dict],
            "safety_overrides": list[dict],
            "justification": str,
            "reasoning": str,
            "confidence": float,
            "timestamp": str,
            "duration_seconds": float,
            "phases_considered": list[str],
            "recommendation_evolution": dict  # Only if initial_collation provided
        }
    """
    logger.info("⚖️  Phase 3: Arbitration")
    
    # Save checkpoint before phase execution
    if thread_id and checkpoint_saver:
        checkpoint_state = {"phase2_results": revised_collation.model_dump()}
        if initial_collation is not None:
            checkpoint_state["phase1_results"] = initial_collation.model_dump()
        
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="phase3_start",
            state=checkpoint_state,
            metadata={
                "phase": "phase3",
                "status": "started",
                "timestamp": datetime.now().isoformat(),
                "phases_available": ["phase1", "phase2"] if initial_collation else ["phase2"]
            }
        )
        logger.debug(f"   ✅ Phase 3 start checkpoint saved")
    
    phase_start = datetime.now()
    
    try:
        # Call arbitrator with revised collation and optional initial collation
        # Note: arbitrator will load Opus 4.5 model internally if llm is None
        if initial_collation is not None:
            logger.info("   Invoking arbitrator with both Phase 1 and Phase 2 recommendations")
        else:
            logger.info("   Invoking arbitrator with Phase 2 recommendations only (legacy mode)")
        result = await arbitrate(revised_collation, llm_opus=None, initial_recommendations=initial_collation)
        
        # Add phase metadata
        result["phase"] = "arbitration"
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        result["duration_seconds"] = phase_duration
        
        # Save final checkpoint
        if thread_id and checkpoint_saver:
            await checkpoint_saver.save_checkpoint(
                thread_id=thread_id,
                checkpoint_id="phase3_complete",
                state=result,
                metadata={
                    "phase": "phase3",
                    "status": "completed",
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": phase_duration,
                    "confidence": result.get("confidence", 0.0)
                }
            )
            logger.debug(f"   ✅ Phase 3 completion checkpoint saved")
        
        logger.info(f"   Phase 3 completed in {phase_duration:.2f}s")
        logger.info(f"   Conflicts identified: {len(result.get('conflicts_identified', []))}")
        logger.info(f"   Confidence: {result.get('confidence', 0.0):.2f}")
        
        return result
        
    except Exception as e:
        # Fallback to conservative decision on error
        logger.error(f"   ❌ Arbitration failed: {e}")
        logger.exception("   Full traceback:")
        
        phase_duration = (datetime.now() - phase_start).total_seconds()
        
        # Extract all recommendations for fallback
        recommendations = []
        for agent_name, response in revised_collation.responses.items():
            if response.status == "success":
                rec = response.recommendation
                recommendations.append(f"{agent_name}: {rec}")
        
        fallback_decision = {
            "phase": "arbitration",
            "final_decision": "Arbitration failed - manual review required. Apply most conservative safety recommendations.",
            "recommendations": recommendations,
            "conflicts_identified": [],
            "conflict_resolutions": [],
            "safety_overrides": [],
            "justification": f"Arbitration system error: {str(e)}. Defaulting to conservative approach.",
            "reasoning": "Fallback to conservative decision due to arbitration failure",
            "confidence": 0.0,
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": phase_duration,
            "error": str(e)
        }
        
        logger.info(f"   Phase 3 completed (fallback) in {phase_duration:.2f}s")
        
        return fallback_decision


async def handle_disruption(user_prompt: str, llm: Any, mcp_tools: list) -> dict:
    """
    Orchestrator: Three-phase multi-round orchestration with checkpoint persistence.
    
    Phase 1: Initial recommendations from all agents
    Phase 2: Revision round with cross-agent insights
    Phase 3: Arbitration and final decision
    
    Accepts natural language prompts. Agents will use their database tools
    to extract required information and perform analysis.
    
    Checkpoint persistence enables:
    - Failure recovery from last successful checkpoint
    - Complete audit trail for regulatory compliance
    - Time-travel debugging for issue investigation

    Args:
        user_prompt: Natural language description of the disruption
        llm: Model instance
        mcp_tools: MCP tools

    Returns:
        dict: Final decision with complete audit trail and thread_id
    """
    logger.info("=" * 60)
    logger.info("🎯 Starting SkyMarshal Orchestrator (Three-Phase)")
    logger.info("=" * 60)

    if not user_prompt or not user_prompt.strip():
        logger.error("❌ No prompt provided")
        return {
            "status": "VALIDATION_FAILED",
            "reason": "No prompt provided. Please provide a natural language description of the disruption.",
            "timestamp": datetime.now().isoformat(),
            "recommendations": [
                "Provide a prompt describing the disruption.",
                "Example: 'Flight EY123 from AUH to LHR is delayed 3 hours due to technical issues'",
                "Example: 'Analyze the impact of a 5-hour delay on flight 1 departing from JFK'",
            ],
        }

    logger.info(f"📝 Processing prompt: {user_prompt[:100]}...")
    logger.info("📋 Agents will extract required information from prompt and database")
    
    orchestration_start = datetime.now()
    
    # Create thread for this workflow
    thread_id = thread_manager.create_thread(
        user_prompt=user_prompt,
        metadata={"orchestration_start": orchestration_start.isoformat()}
    )
    logger.info(f"🧵 Thread created: {thread_id}")
    
    try:
        # Save initial checkpoint
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="start",
            state={"user_prompt": user_prompt},
            metadata={
                "phase": "start",
                "timestamp": datetime.now().isoformat()
            }
        )
        logger.debug(f"   ✅ Initial checkpoint saved")
        
        # Phase 1: Initial Recommendations
        initial_collation = await phase1_initial_recommendations(
            user_prompt, llm, mcp_tools, thread_id, checkpoint_saver
        )
        
        # Phase 2: Revision Round
        revised_collation = await phase2_revision_round(
            user_prompt, initial_collation, llm, mcp_tools, thread_id, checkpoint_saver
        )
        
        # Phase 3: Arbitration
        final_decision = await phase3_arbitration(
            revised_collation, llm, thread_id, checkpoint_saver, initial_collation
        )
        
        # Calculate total duration
        total_duration = (datetime.now() - orchestration_start).total_seconds()
        
        # Mark thread as complete
        thread_manager.mark_thread_complete(
            thread_id=thread_id,
            result=final_decision
        )
        logger.info(f"   ✅ Thread marked complete: {thread_id}")
        
        # Build complete response with audit trail
        response = {
            "status": "success",
            "thread_id": thread_id,
            "final_decision": final_decision,
            "knowledgeBaseConsidered": final_decision.get("knowledgeBaseConsidered", False),
            "audit_trail": {
                "user_prompt": user_prompt,
                "phase1_initial": initial_collation.model_dump(),
                "phase2_revision": revised_collation.model_dump(),
                "phase3_arbitration": final_decision
            },
            "timestamp": datetime.now().isoformat(),
            "phase1_duration_seconds": initial_collation.duration_seconds,
            "phase2_duration_seconds": revised_collation.duration_seconds,
            "phase3_duration_seconds": final_decision.get("duration_seconds", 0),
            "total_duration_seconds": total_duration
        }

        # Log knowledge base consideration status
        kb_considered = final_decision.get("knowledgeBaseConsidered", False)
        kb_docs = final_decision.get("knowledge_base", {}).get("documents_found", 0)
        logger.info(f"📚 Knowledge Base: considered={kb_considered}, documents_found={kb_docs}")

        logger.info("=" * 60)
        logger.info(
            f"✅ Orchestrator Complete (Total: {total_duration:.2f}s)"
        )
        logger.info("=" * 60)

        return response
        
    except Exception as e:
        # Mark thread as failed
        thread_manager.mark_thread_failed(
            thread_id=thread_id,
            error=str(e),
            error_details={"error_type": type(e).__name__}
        )
        logger.error(f"   ❌ Thread marked failed: {thread_id} - {e}")
        
        # Re-raise exception for upstream handling
        raise


@app.entrypoint
async def invoke(payload):
    """
    Single orchestrator entrypoint for all agents.
    
    Accepts natural language prompts and routes to appropriate agent(s).
    Agents use their database tools to extract required information.

    Payload format:
    {
        "agent": "crew_compliance" | "orchestrator" | <other_agent>,
        "user_prompt": "Natural language description of the disruption..."
    }

    Examples:
    - "Flight EY123 from AUH to LHR is delayed 3 hours due to technical issues"
    - "Analyze crew compliance for flight 1 with a 5-hour delay"
    - "What's the financial impact of canceling flight AA456?"

    Returns:
        dict: Agent response or aggregated orchestrator response
    """
    request_start = datetime.now()
    logger.info("=" * 80)
    logger.info("🎯 NEW REQUEST RECEIVED")
    logger.info("=" * 80)

    try:
        # Log payload details
        agent_name = payload.get("agent", "orchestrator")
        
        # Support both 'user_prompt' (new) and 'prompt' (legacy) for backward compatibility
        user_prompt = payload.get("user_prompt") or payload.get("prompt", "")
        
        logger.info(f"📨 Target Agent: {agent_name}")
        logger.info(f"📝 Prompt: {user_prompt[:200]}...")
        logger.debug(f"   Payload keys: {list(payload.keys())}")

        if not user_prompt:
            logger.error("❌ No prompt provided")
            return {
                "error": "No prompt provided",
                "message": "Please provide a 'user_prompt' field with a natural language description of the disruption",
                "examples": [
                    "Flight EY123 from AUH to LHR is delayed 3 hours due to technical issues",
                    "Analyze the impact of a 5-hour delay on flight 1",
                ],
            }

        # Load shared resources
        logger.info("🔧 Loading shared resources...")

        logger.debug("   Loading model...")
        llm = load_model()
        logger.info("   ✅ Model loaded (Claude Sonnet 4.5)")

        logger.debug("   Loading MCP client...")
        mcp_client = get_streamable_http_mcp_client()
        logger.info("   ✅ MCP client loaded")

        logger.debug("   Getting MCP tools...")
        mcp_tools = await mcp_client.get_tools()
        logger.info(f"   ✅ MCP tools loaded ({len(mcp_tools)} tools)")

        # Normalize payload to use user_prompt
        normalized_payload = {"user_prompt": user_prompt}

        # Determine routing
        if agent_name == "orchestrator":
            # Run all agents (safety → business)
            logger.info("🎯 Routing to ORCHESTRATOR (all agents)")
            result = await handle_disruption(user_prompt, llm, mcp_tools)

        elif agent_name in AGENT_REGISTRY:
            # Route to specific agent
            logger.info(f"🎯 Routing to SPECIFIC AGENT: {agent_name}")
            agent_fn = AGENT_REGISTRY[agent_name]
            result = await run_agent_safely(
                agent_name, agent_fn, normalized_payload, llm, mcp_tools
            )

        else:
            # Unknown agent
            logger.error(f"❌ Unknown agent: {agent_name}")
            available = list(AGENT_REGISTRY.keys()) + ["orchestrator"]
            logger.debug(f"   Available agents: {available}")
            return {
                "error": f"Unknown agent: {agent_name}",
                "available_agents": available,
            }

        # Calculate total duration
        total_duration = (datetime.now() - request_start).total_seconds()
        result["request_duration_seconds"] = total_duration

        logger.info("=" * 80)
        logger.info(f"✅ REQUEST COMPLETED in {total_duration:.2f}s")
        logger.info("=" * 80)

        return result

    except Exception as e:
        total_duration = (datetime.now() - request_start).total_seconds()
        logger.error("=" * 80)
        logger.error(f"❌ ORCHESTRATOR INVOCATION FAILED after {total_duration:.2f}s")
        logger.error("=" * 80)
        logger.error(f"Error: {e}")
        logger.exception("Full traceback:")

        return {
            "error": "Orchestrator invocation failed",
            "error_message": str(e),
            "error_type": type(e).__name__,
            "request_duration_seconds": total_duration,
        }


if __name__ == "__main__":
    # Run local development server on port 8080
    app.run()
