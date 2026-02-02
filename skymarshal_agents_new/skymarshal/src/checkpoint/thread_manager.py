"""ThreadManager for managing thread lifecycle and metadata"""

import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class ThreadManager:
    """
    Manages thread lifecycle and metadata for multi-round workflows.
    
    Tracks thread status (active, completed, failed) and provides
    query capabilities for thread management and monitoring.
    """

    def __init__(self, checkpoint_saver=None):
        """
        Initialize ThreadManager.
        
        Args:
            checkpoint_saver: Optional CheckpointSaver for persistence
        """
        self.checkpoint_saver = checkpoint_saver
        self.threads = {}  # In-memory cache for thread metadata
        logger.info("ThreadManager initialized")

    def create_thread(self, user_prompt: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create new thread and return unique thread_id.
        
        Args:
            user_prompt: Initial user prompt that started the workflow
            metadata: Optional additional metadata
        
        Returns:
            Unique thread identifier (UUID)
        """
        thread_id = str(uuid.uuid4())
        
        thread_data = {
            "thread_id": thread_id,
            "user_prompt": user_prompt,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.threads[thread_id] = thread_data
        logger.info(f"Thread created: {thread_id}")
        
        return thread_id

    def get_thread_status(self, thread_id: str) -> Optional[str]:
        """
        Get current status of a thread.
        
        Args:
            thread_id: Unique thread identifier
        
        Returns:
            Thread status: "active", "completed", "failed", or None if not found
        """
        thread = self.threads.get(thread_id)
        if thread:
            return thread.get("status")
        
        logger.warning(f"Thread not found: {thread_id}")
        return None

    def get_thread_metadata(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete metadata for a thread.
        
        Args:
            thread_id: Unique thread identifier
        
        Returns:
            Thread metadata dictionary or None if not found
        """
        thread = self.threads.get(thread_id)
        if thread:
            return thread.copy()
        
        logger.warning(f"Thread not found: {thread_id}")
        return None

    def mark_thread_complete(self, thread_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark thread as successfully completed.
        
        Args:
            thread_id: Unique thread identifier
            result: Optional final result data
        """
        thread = self.threads.get(thread_id)
        if not thread:
            logger.warning(f"Cannot mark thread complete - not found: {thread_id}")
            return
        
        thread["status"] = "completed"
        thread["updated_at"] = datetime.utcnow().isoformat()
        thread["completed_at"] = datetime.utcnow().isoformat()
        
        if result:
            thread["result"] = result
        
        logger.info(f"Thread marked complete: {thread_id}")

    def mark_thread_failed(self, thread_id: str, error: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark thread as failed with error information.
        
        Args:
            thread_id: Unique thread identifier
            error: Error message
            error_details: Optional detailed error information
        """
        thread = self.threads.get(thread_id)
        if not thread:
            logger.warning(f"Cannot mark thread failed - not found: {thread_id}")
            return
        
        thread["status"] = "failed"
        thread["updated_at"] = datetime.utcnow().isoformat()
        thread["failed_at"] = datetime.utcnow().isoformat()
        thread["error"] = error
        
        if error_details:
            thread["error_details"] = error_details
        
        logger.error(f"Thread marked failed: {thread_id} - {error}")

    def mark_thread_rejected(self, thread_id: str, reason: str, approver_id: Optional[str] = None) -> None:
        """
        Mark thread as rejected by human approver.
        
        Args:
            thread_id: Unique thread identifier
            reason: Rejection reason
            approver_id: Optional ID of person who rejected
        """
        thread = self.threads.get(thread_id)
        if not thread:
            logger.warning(f"Cannot mark thread rejected - not found: {thread_id}")
            return
        
        thread["status"] = "rejected"
        thread["updated_at"] = datetime.utcnow().isoformat()
        thread["rejected_at"] = datetime.utcnow().isoformat()
        thread["rejection_reason"] = reason
        
        if approver_id:
            thread["rejected_by"] = approver_id
        
        logger.info(f"Thread marked rejected: {thread_id} by {approver_id or 'unknown'}")

    async def query_threads(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query threads with optional filtering.
        
        Args:
            status: Optional filter by status (active, completed, failed, rejected)
            limit: Maximum number of threads to return
            offset: Number of threads to skip (for pagination)
        
        Returns:
            List of thread metadata dictionaries
        """
        threads = list(self.threads.values())
        
        # Apply status filter
        if status:
            threads = [t for t in threads if t.get("status") == status]
        
        # Sort by created_at descending (newest first)
        threads.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        # Apply pagination
        threads = threads[offset:offset + limit]
        
        logger.debug(f"Query returned {len(threads)} threads (status={status}, limit={limit}, offset={offset})")
        return threads

    def get_active_threads(self) -> List[Dict[str, Any]]:
        """
        Get all active threads.
        
        Returns:
            List of active thread metadata dictionaries
        """
        active = [t for t in self.threads.values() if t.get("status") == "active"]
        logger.debug(f"Found {len(active)} active threads")
        return active

    def get_thread_count(self, status: Optional[str] = None) -> int:
        """
        Get count of threads, optionally filtered by status.
        
        Args:
            status: Optional filter by status
        
        Returns:
            Number of threads matching criteria
        """
        if status:
            count = sum(1 for t in self.threads.values() if t.get("status") == status)
        else:
            count = len(self.threads)
        
        return count

    def cleanup_old_threads(self, days: int = 90) -> int:
        """
        Remove thread metadata older than specified days.
        
        Note: This only removes in-memory metadata. Checkpoints in DynamoDB
        are managed by TTL configuration.
        
        Args:
            days: Age threshold in days
        
        Returns:
            Number of threads removed
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()
        
        threads_to_remove = [
            tid for tid, thread in self.threads.items()
            if thread.get("created_at", "") < cutoff_iso
        ]
        
        for tid in threads_to_remove:
            del self.threads[tid]
        
        logger.info(f"Cleaned up {len(threads_to_remove)} threads older than {days} days")
        return len(threads_to_remove)
