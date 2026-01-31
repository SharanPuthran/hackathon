#!/usr/bin/env python3
"""
State file management for GSI creation with resume capability.

This module provides functionality to track GSI creation progress and support
resuming from the last successful GSI in case of interruption.

State file format (.gsi_creation_state.json):
{
    "version": "1.0",
    "created_at": "2025-01-20T10:30:00Z",
    "updated_at": "2025-01-20T10:35:00Z",
    "script_name": "create_priority1_gsis.py",
    "gsis": {
        "bookings.passenger-flight-index": {
            "table_name": "bookings",
            "index_name": "passenger-flight-index",
            "status": "active",
            "creation_time": "2025-01-20T10:31:00Z",
            "retry_count": 2,
            "last_error": null
        },
        "bookings.flight-status-index": {
            "table_name": "bookings",
            "index_name": "flight-status-index",
            "status": "failed",
            "creation_time": "2025-01-20T10:33:00Z",
            "retry_count": 5,
            "last_error": "LimitExceededException: Too many GSIs"
        }
    },
    "summary": {
        "total": 6,
        "pending": 2,
        "in_progress": 0,
        "active": 3,
        "failed": 1
    }
}

Status values:
- pending: GSI creation not yet attempted
- in_progress: GSI creation currently in progress
- active: GSI successfully created and is ACTIVE
- failed: GSI creation failed after all retries
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from pathlib import Path


class GSIState:
    """Represents the state of a single GSI."""
    
    def __init__(
        self,
        table_name: str,
        index_name: str,
        status: str = "pending",
        creation_time: Optional[str] = None,
        retry_count: int = 0,
        last_error: Optional[str] = None
    ):
        """
        Initialize GSI state.
        
        Args:
            table_name: Name of the table
            index_name: Name of the GSI
            status: Current status (pending, in_progress, active, failed)
            creation_time: ISO timestamp when GSI creation started
            retry_count: Number of retry attempts
            last_error: Last error message (if any)
        """
        self.table_name = table_name
        self.index_name = index_name
        self.status = status
        self.creation_time = creation_time
        self.retry_count = retry_count
        self.last_error = last_error
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'table_name': self.table_name,
            'index_name': self.index_name,
            'status': self.status,
            'creation_time': self.creation_time,
            'retry_count': self.retry_count,
            'last_error': self.last_error
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GSIState':
        """Create GSIState from dictionary."""
        return cls(
            table_name=data['table_name'],
            index_name=data['index_name'],
            status=data.get('status', 'pending'),
            creation_time=data.get('creation_time'),
            retry_count=data.get('retry_count', 0),
            last_error=data.get('last_error')
        )
    
    def get_key(self) -> str:
        """Get unique key for this GSI (table.index)."""
        return f"{self.table_name}.{self.index_name}"


class GSIStateManager:
    """
    Manages GSI creation state with resume capability.
    
    This class provides functionality to:
    - Track GSI creation progress
    - Save state to file after each GSI
    - Resume from last successful GSI
    - Clean up state file on completion
    """
    
    STATE_FILE_NAME = ".gsi_creation_state.json"
    STATE_VERSION = "1.0"
    
    def __init__(self, script_name: str, state_dir: str = "."):
        """
        Initialize state manager.
        
        Args:
            script_name: Name of the script creating GSIs
            state_dir: Directory to store state file (default: current directory)
        """
        self.script_name = script_name
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / self.STATE_FILE_NAME
        
        self.gsis: Dict[str, GSIState] = {}
        self.created_at: Optional[str] = None
        self.updated_at: Optional[str] = None
        
        # Load existing state if available
        if self.state_file.exists():
            self.load()
    
    def initialize_gsis(self, gsi_definitions: Dict[str, List[dict]]) -> None:
        """
        Initialize GSI states from definitions.
        
        Args:
            gsi_definitions: Dictionary mapping table names to lists of GSI configs
        """
        for table_name, gsi_configs in gsi_definitions.items():
            for gsi_config in gsi_configs:
                index_name = gsi_config['IndexName']
                key = f"{table_name}.{index_name}"
                
                # Only initialize if not already in state
                if key not in self.gsis:
                    self.gsis[key] = GSIState(table_name, index_name)
        
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        
        self.updated_at = datetime.now().isoformat()
        self.save()
    
    def update_gsi_status(
        self,
        table_name: str,
        index_name: str,
        status: str,
        retry_count: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Update the status of a GSI.
        
        Args:
            table_name: Name of the table
            index_name: Name of the GSI
            status: New status (pending, in_progress, active, failed)
            retry_count: Number of retry attempts (optional)
            error: Error message if failed (optional)
        """
        key = f"{table_name}.{index_name}"
        
        if key not in self.gsis:
            self.gsis[key] = GSIState(table_name, index_name)
        
        gsi_state = self.gsis[key]
        gsi_state.status = status
        
        if status == "in_progress" and not gsi_state.creation_time:
            gsi_state.creation_time = datetime.now().isoformat()
        
        if retry_count is not None:
            gsi_state.retry_count = retry_count
        
        if error:
            gsi_state.last_error = error
        
        self.updated_at = datetime.now().isoformat()
        self.save()
    
    def get_gsi_status(self, table_name: str, index_name: str) -> Optional[str]:
        """
        Get the status of a GSI.
        
        Args:
            table_name: Name of the table
            index_name: Name of the GSI
        
        Returns:
            Status string or None if not found
        """
        key = f"{table_name}.{index_name}"
        gsi_state = self.gsis.get(key)
        return gsi_state.status if gsi_state else None
    
    def get_pending_gsis(self) -> List[Tuple[str, str]]:
        """
        Get list of GSIs that are pending (not yet attempted).
        
        Returns:
            List of (table_name, index_name) tuples
        """
        return [
            (gsi.table_name, gsi.index_name)
            for gsi in self.gsis.values()
            if gsi.status == "pending"
        ]
    
    def get_failed_gsis(self) -> List[Tuple[str, str, str]]:
        """
        Get list of GSIs that failed.
        
        Returns:
            List of (table_name, index_name, error) tuples
        """
        return [
            (gsi.table_name, gsi.index_name, gsi.last_error or "Unknown error")
            for gsi in self.gsis.values()
            if gsi.status == "failed"
        ]
    
    def get_summary(self) -> dict:
        """
        Get summary of GSI creation progress.
        
        Returns:
            Dictionary with counts by status
        """
        summary = {
            'total': len(self.gsis),
            'pending': 0,
            'in_progress': 0,
            'active': 0,
            'failed': 0
        }
        
        for gsi in self.gsis.values():
            if gsi.status in summary:
                summary[gsi.status] += 1
        
        return summary
    
    def is_complete(self) -> bool:
        """
        Check if all GSIs are complete (active or failed).
        
        Returns:
            True if all GSIs are complete, False otherwise
        """
        summary = self.get_summary()
        return summary['pending'] == 0 and summary['in_progress'] == 0
    
    def save(self) -> None:
        """Save state to file."""
        state_data = {
            'version': self.STATE_VERSION,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'script_name': self.script_name,
            'gsis': {
                key: gsi.to_dict()
                for key, gsi in self.gsis.items()
            },
            'summary': self.get_summary()
        }
        
        # Ensure directory exists
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Write to temporary file first, then rename (atomic operation)
        temp_file = self.state_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            json.dump(state_data, f, indent=2)
        
        # Atomic rename
        temp_file.replace(self.state_file)
    
    def load(self) -> None:
        """Load state from file."""
        if not self.state_file.exists():
            return
        
        try:
            with open(self.state_file, 'r') as f:
                state_data = json.load(f)
            
            self.created_at = state_data.get('created_at')
            self.updated_at = state_data.get('updated_at')
            
            # Load GSI states
            gsis_data = state_data.get('gsis', {})
            self.gsis = {
                key: GSIState.from_dict(gsi_data)
                for key, gsi_data in gsis_data.items()
            }
            
            print(f"Loaded state from {self.state_file}")
            print(f"  Created: {self.created_at}")
            print(f"  Updated: {self.updated_at}")
            
            summary = self.get_summary()
            print(f"  Summary: {summary['active']} active, {summary['failed']} failed, "
                  f"{summary['pending']} pending, {summary['in_progress']} in progress")
        
        except Exception as e:
            print(f"Warning: Failed to load state file: {e}")
            print("Starting with fresh state")
    
    def cleanup(self) -> None:
        """
        Clean up state file on successful completion.
        
        This should be called when all GSIs are successfully created.
        """
        if self.state_file.exists():
            try:
                # Archive the state file instead of deleting
                archive_name = f".gsi_creation_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                archive_path = self.state_dir / archive_name
                
                self.state_file.rename(archive_path)
                print(f"State file archived to {archive_path}")
            except Exception as e:
                print(f"Warning: Failed to archive state file: {e}")
    
    def print_status(self) -> None:
        """Print current status of all GSIs."""
        print("\n" + "=" * 80)
        print("GSI Creation Status")
        print("=" * 80)
        
        summary = self.get_summary()
        print(f"\nSummary:")
        print(f"  Total: {summary['total']}")
        print(f"  Active: {summary['active']}")
        print(f"  Failed: {summary['failed']}")
        print(f"  Pending: {summary['pending']}")
        print(f"  In Progress: {summary['in_progress']}")
        
        if summary['active'] > 0:
            print(f"\nActive GSIs:")
            for gsi in self.gsis.values():
                if gsi.status == "active":
                    print(f"  ✓ {gsi.table_name}.{gsi.index_name}")
        
        if summary['failed'] > 0:
            print(f"\nFailed GSIs:")
            for gsi in self.gsis.values():
                if gsi.status == "failed":
                    print(f"  ✗ {gsi.table_name}.{gsi.index_name}")
                    if gsi.last_error:
                        print(f"    Error: {gsi.last_error}")
                    print(f"    Retry count: {gsi.retry_count}")
        
        if summary['pending'] > 0:
            print(f"\nPending GSIs:")
            for gsi in self.gsis.values():
                if gsi.status == "pending":
                    print(f"  ⏳ {gsi.table_name}.{gsi.index_name}")
        
        print("=" * 80 + "\n")
    
    def should_skip_gsi(self, table_name: str, index_name: str) -> bool:
        """
        Check if a GSI should be skipped (already active).
        
        Args:
            table_name: Name of the table
            index_name: Name of the GSI
        
        Returns:
            True if GSI should be skipped, False otherwise
        """
        status = self.get_gsi_status(table_name, index_name)
        return status == "active"
    
    def get_resume_point(self) -> Optional[Tuple[str, str]]:
        """
        Get the resume point (first pending GSI).
        
        Returns:
            Tuple of (table_name, index_name) or None if no pending GSIs
        """
        pending = self.get_pending_gsis()
        return pending[0] if pending else None
