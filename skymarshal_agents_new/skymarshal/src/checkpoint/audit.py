"""Audit trail and time-travel debugging utilities"""

import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


async def export_thread_history(
    checkpoint_saver,
    thread_id: str,
    phase_filter: Optional[str] = None,
    agent_filter: Optional[str] = None,
    output_format: str = "json"
) -> str:
    """
    Export complete thread history for audit purposes.
    
    Retrieves all checkpoints for a thread and exports them in the specified format.
    Useful for regulatory compliance, debugging, and analysis.
    
    Args:
        checkpoint_saver: CheckpointSaver instance
        thread_id: Thread identifier to export
        phase_filter: Optional filter by phase (phase1, phase2, phase3)
        agent_filter: Optional filter by agent name
        output_format: Export format ("json", "markdown", "csv")
        
    Returns:
        str: Formatted export data
        
    Example:
        >>> from checkpoint import CheckpointSaver
        >>> from checkpoint.audit import export_thread_history
        >>> 
        >>> saver = CheckpointSaver(mode="production")
        >>> export = await export_thread_history(
        ...     saver, 
        ...     thread_id="abc-123",
        ...     output_format="json"
        ... )
        >>> print(export)
    """
    try:
        logger.info(f"Exporting thread history: thread_id={thread_id}")
        
        # Get complete history
        history = await checkpoint_saver.get_thread_history(
            thread_id=thread_id,
            phase_filter=phase_filter,
            agent_filter=agent_filter
        )
        
        if not history:
            logger.warning(f"No history found for thread: {thread_id}")
            return json.dumps({"error": "No history found", "thread_id": thread_id})
        
        # Prepare export data
        export_data = {
            "thread_id": thread_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "checkpoint_count": len(history),
            "filters": {
                "phase": phase_filter,
                "agent": agent_filter
            },
            "checkpoints": history
        }
        
        # Format based on output_format
        if output_format == "json":
            result = json.dumps(export_data, indent=2)
        elif output_format == "markdown":
            result = _format_as_markdown(export_data)
        elif output_format == "csv":
            result = _format_as_csv(export_data)
        else:
            logger.error(f"Unsupported output format: {output_format}")
            result = json.dumps(export_data, indent=2)
        
        logger.info(f"Thread history exported: {len(history)} checkpoints")
        return result
        
    except Exception as e:
        logger.error(f"Failed to export thread history: {e}")
        logger.exception("Full traceback:")
        return json.dumps({"error": str(e), "thread_id": thread_id})


def _format_as_markdown(export_data: Dict[str, Any]) -> str:
    """Format export data as Markdown"""
    md = f"# Thread History: {export_data['thread_id']}\n\n"
    md += f"**Export Time**: {export_data['export_timestamp']}\n"
    md += f"**Checkpoint Count**: {export_data['checkpoint_count']}\n\n"
    
    if export_data['filters']['phase'] or export_data['filters']['agent']:
        md += "## Filters\n\n"
        if export_data['filters']['phase']:
            md += f"- Phase: {export_data['filters']['phase']}\n"
        if export_data['filters']['agent']:
            md += f"- Agent: {export_data['filters']['agent']}\n"
        md += "\n"
    
    md += "## Checkpoints\n\n"
    
    for checkpoint in export_data['checkpoints']:
        md += f"### {checkpoint.get('checkpoint_id', 'Unknown')}\n\n"
        md += f"- **Timestamp**: {checkpoint.get('timestamp', 'N/A')}\n"
        
        metadata = checkpoint.get('metadata', {})
        if metadata:
            md += f"- **Phase**: {metadata.get('phase', 'N/A')}\n"
            md += f"- **Agent**: {metadata.get('agent', 'N/A')}\n"
            md += f"- **Status**: {metadata.get('status', 'N/A')}\n"
            if 'confidence' in metadata:
                md += f"- **Confidence**: {metadata.get('confidence', 0.0):.2f}\n"
        
        md += "\n"
    
    return md


def _format_as_csv(export_data: Dict[str, Any]) -> str:
    """Format export data as CSV"""
    csv = "checkpoint_id,timestamp,phase,agent,status,confidence\n"
    
    for checkpoint in export_data['checkpoints']:
        checkpoint_id = checkpoint.get('checkpoint_id', '')
        timestamp = checkpoint.get('timestamp', '')
        metadata = checkpoint.get('metadata', {})
        phase = metadata.get('phase', '')
        agent = metadata.get('agent', '')
        status = metadata.get('status', '')
        confidence = metadata.get('confidence', '')
        
        csv += f"{checkpoint_id},{timestamp},{phase},{agent},{status},{confidence}\n"
    
    return csv


async def replay_from_checkpoint(
    checkpoint_saver,
    thread_id: str,
    checkpoint_id: str,
    continue_execution: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Load a historical checkpoint for time-travel debugging.
    
    Retrieves a specific checkpoint and optionally continues execution from that point.
    Useful for debugging issues, analyzing past decisions, and testing recovery.
    
    Args:
        checkpoint_saver: CheckpointSaver instance
        thread_id: Thread identifier
        checkpoint_id: Specific checkpoint to load
        continue_execution: If True, continue execution from this checkpoint
        
    Returns:
        dict: Checkpoint data with state and metadata, or None if not found
        
    Example:
        >>> from checkpoint import CheckpointSaver
        >>> from checkpoint.audit import replay_from_checkpoint
        >>> 
        >>> saver = CheckpointSaver(mode="production")
        >>> checkpoint = await replay_from_checkpoint(
        ...     saver,
        ...     thread_id="abc-123",
        ...     checkpoint_id="phase1_complete"
        ... )
        >>> print(checkpoint['state'])
    """
    try:
        logger.info(f"Replaying from checkpoint: thread_id={thread_id}, checkpoint_id={checkpoint_id}")
        
        # Load the checkpoint
        checkpoint = await checkpoint_saver.load_checkpoint(
            thread_id=thread_id,
            checkpoint_id=checkpoint_id
        )
        
        if not checkpoint:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return None
        
        logger.info(f"Checkpoint loaded: {checkpoint_id}")
        logger.debug(f"Checkpoint metadata: {checkpoint.get('metadata', {})}")
        
        if continue_execution:
            logger.warning("Continue execution not yet implemented - returning checkpoint data only")
            # TODO: Implement execution continuation
            # This would require:
            # 1. Determine which phase to resume from
            # 2. Restore state to orchestrator
            # 3. Continue execution from that point
        
        return checkpoint
        
    except Exception as e:
        logger.error(f"Failed to replay from checkpoint: {e}")
        logger.exception("Full traceback:")
        return None


async def get_checkpoint_summary(
    checkpoint_saver,
    thread_id: str
) -> Dict[str, Any]:
    """
    Get a summary of all checkpoints for a thread.
    
    Provides high-level overview without loading full checkpoint data.
    Useful for quick analysis and debugging.
    
    Args:
        checkpoint_saver: CheckpointSaver instance
        thread_id: Thread identifier
        
    Returns:
        dict: Summary with checkpoint counts, phases, and status
        
    Example:
        >>> summary = await get_checkpoint_summary(saver, "abc-123")
        >>> print(f"Total checkpoints: {summary['total_count']}")
        >>> print(f"Phases: {summary['phases']}")
    """
    try:
        logger.info(f"Getting checkpoint summary: thread_id={thread_id}")
        
        # List all checkpoints
        checkpoints = await checkpoint_saver.list_checkpoints(thread_id=thread_id)
        
        if not checkpoints:
            return {
                "thread_id": thread_id,
                "total_count": 0,
                "phases": [],
                "agents": [],
                "status_counts": {}
            }
        
        # Analyze checkpoints
        phases = set()
        agents = set()
        status_counts = {}
        
        for checkpoint in checkpoints:
            metadata = checkpoint.get('metadata', {})
            
            phase = metadata.get('phase')
            if phase:
                phases.add(phase)
            
            agent = metadata.get('agent')
            if agent:
                agents.add(agent)
            
            status = metadata.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        summary = {
            "thread_id": thread_id,
            "total_count": len(checkpoints),
            "phases": sorted(list(phases)),
            "agents": sorted(list(agents)),
            "status_counts": status_counts,
            "first_checkpoint": checkpoints[0].get('timestamp') if checkpoints else None,
            "last_checkpoint": checkpoints[-1].get('timestamp') if checkpoints else None
        }
        
        logger.info(f"Checkpoint summary: {summary['total_count']} checkpoints, {len(phases)} phases")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get checkpoint summary: {e}")
        logger.exception("Full traceback:")
        return {
            "thread_id": thread_id,
            "error": str(e)
        }


if __name__ == "__main__":
    # Example usage
    import asyncio
    from checkpoint import CheckpointSaver
    
    async def main():
        # Initialize checkpoint saver
        saver = CheckpointSaver(mode="development")
        
        # Create test thread and checkpoint
        from checkpoint import ThreadManager
        thread_manager = ThreadManager(checkpoint_saver=saver)
        thread_id = thread_manager.create_thread(
            user_prompt="Test audit trail",
            metadata={"test": True}
        )
        
        # Save test checkpoint
        await saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="test_checkpoint",
            state={"test": "data"},
            metadata={"phase": "phase1", "agent": "test_agent", "status": "completed"}
        )
        
        # Export history
        print("=" * 60)
        print("EXPORT THREAD HISTORY (JSON)")
        print("=" * 60)
        export_json = await export_thread_history(saver, thread_id, output_format="json")
        print(export_json)
        
        print("\n" + "=" * 60)
        print("EXPORT THREAD HISTORY (MARKDOWN)")
        print("=" * 60)
        export_md = await export_thread_history(saver, thread_id, output_format="markdown")
        print(export_md)
        
        print("\n" + "=" * 60)
        print("CHECKPOINT SUMMARY")
        print("=" * 60)
        summary = await get_checkpoint_summary(saver, thread_id)
        print(json.dumps(summary, indent=2))
        
        print("\n" + "=" * 60)
        print("REPLAY FROM CHECKPOINT")
        print("=" * 60)
        checkpoint = await replay_from_checkpoint(saver, thread_id, "test_checkpoint")
        print(json.dumps(checkpoint, indent=2))
    
    asyncio.run(main())
