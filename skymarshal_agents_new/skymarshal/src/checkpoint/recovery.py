"""Recovery functions for checkpoint-based failure recovery"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def recover_from_failure(
    thread_id: str,
    checkpoint_saver,
    error: Optional[Exception] = None
) -> Dict[str, Any]:
    """
    Recover from workflow failure by loading last successful checkpoint.
    
    Args:
        thread_id: Thread identifier for the failed workflow
        checkpoint_saver: CheckpointSaver instance
        error: Optional exception that caused the failure
    
    Returns:
        dict: Recovery result with status and recovered state
    """
    logger.info(f"🔄 Attempting recovery for thread: {thread_id}")
    
    try:
        # Get all checkpoints for the thread
        checkpoints = await checkpoint_saver.list_checkpoints(thread_id)
        
        if not checkpoints:
            logger.error(f"   ❌ No checkpoints found for thread {thread_id}")
            return {
                "status": "recovery_failed",
                "reason": "No checkpoints available",
                "thread_id": thread_id,
                "error": str(error) if error else None
            }
        
        # Find last successful checkpoint (completed status)
        successful_checkpoints = [
            cp for cp in checkpoints
            if cp.get("metadata", {}).get("status") == "completed"
        ]
        
        if not successful_checkpoints:
            logger.warning(f"   ⚠️  No successful checkpoints found, using latest checkpoint")
            last_checkpoint = checkpoints[-1]
        else:
            last_checkpoint = successful_checkpoints[-1]
        
        checkpoint_id = last_checkpoint.get("checkpoint_id")
        phase = last_checkpoint.get("metadata", {}).get("phase", "unknown")
        
        logger.info(f"   📍 Found recovery point: {checkpoint_id} (phase: {phase})")
        
        # Load full checkpoint data
        checkpoint_data = await checkpoint_saver.load_checkpoint(thread_id, checkpoint_id)
        
        if not checkpoint_data:
            logger.error(f"   ❌ Failed to load checkpoint data")
            return {
                "status": "recovery_failed",
                "reason": "Could not load checkpoint data",
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id
            }
        
        logger.info(f"   ✅ Recovery successful from checkpoint: {checkpoint_id}")
        
        return {
            "status": "recovered",
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "phase": phase,
            "state": checkpoint_data.get("state", {}),
            "metadata": checkpoint_data.get("metadata", {}),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"   ❌ Recovery failed: {e}")
        logger.exception("Recovery error details:")
        return {
            "status": "recovery_failed",
            "reason": str(e),
            "thread_id": thread_id,
            "error": str(error) if error else None
        }


async def resume_from_checkpoint(
    thread_id: str,
    checkpoint_id: str,
    checkpoint_saver
) -> Optional[Dict[str, Any]]:
    """
    Resume workflow execution from a specific checkpoint.
    
    Args:
        thread_id: Thread identifier
        checkpoint_id: Specific checkpoint to resume from
        checkpoint_saver: CheckpointSaver instance
    
    Returns:
        Checkpoint state or None if not found
    """
    logger.info(f"🔄 Resuming from checkpoint: {checkpoint_id}")
    
    try:
        checkpoint_data = await checkpoint_saver.load_checkpoint(thread_id, checkpoint_id)
        
        if not checkpoint_data:
            logger.error(f"   ❌ Checkpoint not found: {checkpoint_id}")
            return None
        
        logger.info(f"   ✅ Checkpoint loaded successfully")
        return checkpoint_data.get("state", {})
        
    except Exception as e:
        logger.error(f"   ❌ Failed to resume from checkpoint: {e}")
        return None


async def recover_agent(
    thread_id: str,
    agent_name: str,
    checkpoint_saver
) -> Optional[Dict[str, Any]]:
    """
    Recover individual agent state from last successful checkpoint.
    
    Args:
        thread_id: Thread identifier
        agent_name: Name of the agent to recover
        checkpoint_saver: CheckpointSaver instance
    
    Returns:
        Agent state or None if not found
    """
    logger.info(f"🔄 Recovering agent: {agent_name}")
    
    try:
        # Get thread history filtered by agent
        history = await checkpoint_saver.get_thread_history(
            thread_id=thread_id,
            agent_filter=agent_name
        )
        
        if not history:
            logger.warning(f"   ⚠️  No checkpoints found for agent {agent_name}")
            return None
        
        # Find last completed checkpoint for this agent
        completed_checkpoints = [
            cp for cp in history
            if cp.get("metadata", {}).get("status") == "completed"
        ]
        
        if not completed_checkpoints:
            logger.warning(f"   ⚠️  No completed checkpoints for agent {agent_name}")
            return None
        
        last_checkpoint = completed_checkpoints[-1]
        checkpoint_id = last_checkpoint.get("checkpoint_id")
        
        logger.info(f"   ✅ Agent recovered from checkpoint: {checkpoint_id}")
        
        return last_checkpoint.get("state", {})
        
    except Exception as e:
        logger.error(f"   ❌ Agent recovery failed: {e}")
        return None


async def restart_phase(
    thread_id: str,
    phase: str,
    checkpoint_saver
) -> Optional[Dict[str, Any]]:
    """
    Restart a specific phase using results from previous phases.
    
    Args:
        thread_id: Thread identifier
        phase: Phase to restart (phase1, phase2, phase3)
        checkpoint_saver: CheckpointSaver instance
    
    Returns:
        Previous phase results or None if not found
    """
    logger.info(f"🔄 Restarting phase: {phase}")
    
    try:
        # Determine which previous phase to load
        if phase == "phase2":
            # Load phase1 results
            history = await checkpoint_saver.get_thread_history(
                thread_id=thread_id,
                phase_filter="phase1"
            )
            previous_phase = "phase1"
        elif phase == "phase3":
            # Load phase2 results
            history = await checkpoint_saver.get_thread_history(
                thread_id=thread_id,
                phase_filter="phase2"
            )
            previous_phase = "phase2"
        else:
            # Phase1 has no previous phase
            logger.info(f"   ℹ️  Phase 1 has no previous phase to load")
            return {}
        
        if not history:
            logger.error(f"   ❌ No checkpoints found for {previous_phase}")
            return None
        
        # Get the completion checkpoint for the previous phase
        completion_checkpoints = [
            cp for cp in history
            if cp.get("checkpoint_id", "").endswith("_complete")
        ]
        
        if not completion_checkpoints:
            logger.error(f"   ❌ No completion checkpoint found for {previous_phase}")
            return None
        
        last_completion = completion_checkpoints[-1]
        checkpoint_id = last_completion.get("checkpoint_id")
        
        logger.info(f"   ✅ Loaded {previous_phase} results from: {checkpoint_id}")
        
        return last_completion.get("state", {})
        
    except Exception as e:
        logger.error(f"   ❌ Phase restart failed: {e}")
        return None
