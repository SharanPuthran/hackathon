"""Human-in-the-loop approval system for checkpoint-based workflows"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def pause_for_approval(
    checkpoint_saver,
    thread_manager,
    thread_id: str,
    decision: Dict[str, Any],
    checkpoint_id: str = "approval_pending"
) -> Dict[str, Any]:
    """
    Pause workflow execution and save checkpoint for human approval.
    
    Saves the current decision state and marks the thread as pending approval.
    The workflow can be resumed after approval or rejected.
    
    Args:
        checkpoint_saver: CheckpointSaver instance
        thread_manager: ThreadManager instance
        thread_id: Thread identifier
        decision: Decision data requiring approval
        checkpoint_id: Checkpoint identifier (default: "approval_pending")
        
    Returns:
        dict: Approval request with thread_id and checkpoint_id
        
    Example:
        >>> from checkpoint import CheckpointSaver, ThreadManager
        >>> from checkpoint.approval import pause_for_approval
        >>> 
        >>> saver = CheckpointSaver(mode="production")
        >>> manager = ThreadManager(checkpoint_saver=saver)
        >>> 
        >>> decision = {
        ...     "final_decision": "Cancel flight",
        ...     "confidence": 0.85,
        ...     "reasoning": "Safety concerns"
        ... }
        >>> 
        >>> approval_request = await pause_for_approval(
        ...     saver, manager, thread_id, decision
        ... )
        >>> print(f"Approval required: {approval_request['approval_url']}")
    """
    try:
        logger.info(f"Pausing for approval: thread_id={thread_id}")
        
        # Save checkpoint with approval pending status
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            state={
                "decision": decision,
                "status": "approval_pending",
                "paused_at": datetime.utcnow().isoformat()
            },
            metadata={
                "phase": "approval",
                "status": "approval_pending",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Checkpoint saved for approval: {checkpoint_id}")
        
        # Return approval request
        approval_request = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "decision": decision,
            "status": "approval_pending",
            "approval_url": f"/api/approvals/{thread_id}",
            "message": "Decision requires human approval. Use approve_decision() or reject_decision() to continue."
        }
        
        return approval_request
        
    except Exception as e:
        logger.error(f"Failed to pause for approval: {e}")
        logger.exception("Full traceback:")
        return {
            "error": str(e),
            "thread_id": thread_id
        }


async def get_pending_approval(
    checkpoint_saver,
    thread_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve pending approval decision for a thread.
    
    Loads the checkpoint with approval_pending status and returns the decision
    that requires human review.
    
    Args:
        checkpoint_saver: CheckpointSaver instance
        thread_id: Thread identifier
        
    Returns:
        dict: Pending decision data, or None if no approval pending
        
    Example:
        >>> pending = await get_pending_approval(saver, thread_id)
        >>> if pending:
        ...     print(f"Decision: {pending['decision']['final_decision']}")
        ...     print(f"Confidence: {pending['decision']['confidence']}")
    """
    try:
        logger.info(f"Getting pending approval: thread_id={thread_id}")
        
        # Load approval checkpoint
        checkpoint = await checkpoint_saver.load_checkpoint(
            thread_id=thread_id,
            checkpoint_id="approval_pending"
        )
        
        if not checkpoint:
            logger.info(f"No pending approval found for thread: {thread_id}")
            return None
        
        state = checkpoint.get('state', {})
        
        if state.get('status') != 'approval_pending':
            logger.info(f"Approval already processed for thread: {thread_id}")
            return None
        
        logger.info(f"Pending approval found: thread_id={thread_id}")
        return {
            "thread_id": thread_id,
            "decision": state.get('decision', {}),
            "paused_at": state.get('paused_at'),
            "status": "approval_pending"
        }
        
    except Exception as e:
        logger.error(f"Failed to get pending approval: {e}")
        logger.exception("Full traceback:")
        return None


async def approve_decision(
    checkpoint_saver,
    thread_manager,
    thread_id: str,
    approver_id: str,
    comments: Optional[str] = None
) -> Dict[str, Any]:
    """
    Approve a pending decision and resume workflow execution.
    
    Records approval metadata and marks the thread as ready to continue.
    The workflow can then be resumed from the approval checkpoint.
    
    Args:
        checkpoint_saver: CheckpointSaver instance
        thread_manager: ThreadManager instance
        thread_id: Thread identifier
        approver_id: Identifier of the person approving
        comments: Optional approval comments
        
    Returns:
        dict: Approval confirmation with resume instructions
        
    Example:
        >>> result = await approve_decision(
        ...     saver, manager, thread_id,
        ...     approver_id="ops_manager_123",
        ...     comments="Approved - safety checks complete"
        ... )
        >>> print(result['message'])
    """
    try:
        logger.info(f"Approving decision: thread_id={thread_id}, approver={approver_id}")
        
        # Load pending approval
        pending = await get_pending_approval(checkpoint_saver, thread_id)
        
        if not pending:
            logger.error(f"No pending approval found for thread: {thread_id}")
            return {
                "error": "No pending approval found",
                "thread_id": thread_id
            }
        
        # Save approval checkpoint
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="approval_approved",
            state={
                "decision": pending['decision'],
                "status": "approved",
                "approved_at": datetime.utcnow().isoformat(),
                "approver_id": approver_id,
                "comments": comments
            },
            metadata={
                "phase": "approval",
                "status": "approved",
                "timestamp": datetime.utcnow().isoformat(),
                "approver_id": approver_id
            }
        )
        
        logger.info(f"Decision approved: thread_id={thread_id}")
        
        return {
            "thread_id": thread_id,
            "status": "approved",
            "approver_id": approver_id,
            "approved_at": datetime.utcnow().isoformat(),
            "message": "Decision approved. Workflow can now resume execution.",
            "resume_instructions": "Use resume_from_checkpoint() to continue workflow execution."
        }
        
    except Exception as e:
        logger.error(f"Failed to approve decision: {e}")
        logger.exception("Full traceback:")
        return {
            "error": str(e),
            "thread_id": thread_id
        }


async def reject_decision(
    checkpoint_saver,
    thread_manager,
    thread_id: str,
    approver_id: str,
    reason: str,
    comments: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reject a pending decision and halt workflow execution.
    
    Records rejection metadata and marks the thread as rejected.
    The workflow will not continue and requires manual intervention.
    
    Args:
        checkpoint_saver: CheckpointSaver instance
        thread_manager: ThreadManager instance
        thread_id: Thread identifier
        approver_id: Identifier of the person rejecting
        reason: Reason for rejection
        comments: Optional additional comments
        
    Returns:
        dict: Rejection confirmation
        
    Example:
        >>> result = await reject_decision(
        ...     saver, manager, thread_id,
        ...     approver_id="ops_manager_123",
        ...     reason="Insufficient safety data",
        ...     comments="Need more crew availability information"
        ... )
        >>> print(result['message'])
    """
    try:
        logger.info(f"Rejecting decision: thread_id={thread_id}, approver={approver_id}")
        
        # Load pending approval
        pending = await get_pending_approval(checkpoint_saver, thread_id)
        
        if not pending:
            logger.error(f"No pending approval found for thread: {thread_id}")
            return {
                "error": "No pending approval found",
                "thread_id": thread_id
            }
        
        # Save rejection checkpoint
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="approval_rejected",
            state={
                "decision": pending['decision'],
                "status": "rejected",
                "rejected_at": datetime.utcnow().isoformat(),
                "approver_id": approver_id,
                "reason": reason,
                "comments": comments
            },
            metadata={
                "phase": "approval",
                "status": "rejected",
                "timestamp": datetime.utcnow().isoformat(),
                "approver_id": approver_id
            }
        )
        
        # Mark thread as rejected
        thread_manager.mark_thread_rejected(
            thread_id=thread_id,
            reason=reason,
            rejected_by=approver_id
        )
        
        logger.info(f"Decision rejected: thread_id={thread_id}")
        
        return {
            "thread_id": thread_id,
            "status": "rejected",
            "approver_id": approver_id,
            "rejected_at": datetime.utcnow().isoformat(),
            "reason": reason,
            "message": "Decision rejected. Workflow execution halted. Manual intervention required."
        }
        
    except Exception as e:
        logger.error(f"Failed to reject decision: {e}")
        logger.exception("Full traceback:")
        return {
            "error": str(e),
            "thread_id": thread_id
        }


if __name__ == "__main__":
    # Example usage
    import asyncio
    from checkpoint import CheckpointSaver, ThreadManager
    
    async def main():
        # Initialize checkpoint infrastructure
        saver = CheckpointSaver(mode="development")
        manager = ThreadManager(checkpoint_saver=saver)
        
        # Create test thread
        thread_id = manager.create_thread(
            user_prompt="Test approval workflow",
            metadata={"test": True}
        )
        
        print("=" * 60)
        print("HUMAN-IN-THE-LOOP APPROVAL WORKFLOW")
        print("=" * 60)
        
        # Simulate a decision requiring approval
        decision = {
            "final_decision": "Cancel flight EY123",
            "confidence": 0.85,
            "reasoning": "Safety concerns due to maintenance issues",
            "recommendations": [
                "Cancel flight immediately",
                "Rebook passengers on next available flight",
                "Notify crew and ground staff"
            ]
        }
        
        # Pause for approval
        print("\n1. Pausing for approval...")
        approval_request = await pause_for_approval(
            saver, manager, thread_id, decision
        )
        print(f"   Status: {approval_request['status']}")
        print(f"   Approval URL: {approval_request['approval_url']}")
        print(f"   Message: {approval_request['message']}")
        
        # Get pending approval
        print("\n2. Getting pending approval...")
        pending = await get_pending_approval(saver, thread_id)
        if pending:
            print(f"   Decision: {pending['decision']['final_decision']}")
            print(f"   Confidence: {pending['decision']['confidence']}")
            print(f"   Paused at: {pending['paused_at']}")
        
        # Approve decision
        print("\n3. Approving decision...")
        approval_result = await approve_decision(
            saver, manager, thread_id,
            approver_id="ops_manager_123",
            comments="Approved - safety checks complete"
        )
        print(f"   Status: {approval_result['status']}")
        print(f"   Approver: {approval_result['approver_id']}")
        print(f"   Message: {approval_result['message']}")
        
        # Test rejection flow with new thread
        print("\n" + "=" * 60)
        print("TESTING REJECTION FLOW")
        print("=" * 60)
        
        thread_id2 = manager.create_thread(
            user_prompt="Test rejection workflow",
            metadata={"test": True}
        )
        
        await pause_for_approval(saver, manager, thread_id2, decision)
        
        print("\n4. Rejecting decision...")
        rejection_result = await reject_decision(
            saver, manager, thread_id2,
            approver_id="ops_manager_456",
            reason="Insufficient safety data",
            comments="Need more crew availability information"
        )
        print(f"   Status: {rejection_result['status']}")
        print(f"   Approver: {rejection_result['approver_id']}")
        print(f"   Reason: {rejection_result['reason']}")
        print(f"   Message: {rejection_result['message']}")
        
        print("\n" + "=" * 60)
    
    asyncio.run(main())
