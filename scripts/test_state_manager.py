#!/usr/bin/env python3
"""
Test script for GSI state manager functionality.

This script demonstrates:
1. State file creation and initialization
2. Status updates during GSI creation
3. Resume capability
4. State file cleanup
"""

import asyncio
import sys
from pathlib import Path
from gsi_state_manager import GSIStateManager


def test_state_initialization():
    """Test state manager initialization."""
    print("=" * 80)
    print("Test 1: State Manager Initialization")
    print("=" * 80)
    
    # Create state manager
    state_manager = GSIStateManager(
        script_name="test_gsi_creation.py",
        state_dir="."
    )
    
    # Define test GSI definitions
    gsi_definitions = {
        'bookings': [
            {'IndexName': 'passenger-flight-index'},
            {'IndexName': 'flight-status-index'}
        ],
        'Baggage': [
            {'IndexName': 'location-status-index'}
        ],
        'CrewRoster': [
            {'IndexName': 'crew-duty-date-index'}
        ]
    }
    
    # Initialize GSIs
    state_manager.initialize_gsis(gsi_definitions)
    
    print("\nInitialized state with 4 GSIs")
    state_manager.print_status()
    
    return state_manager


def test_status_updates(state_manager):
    """Test status updates."""
    print("=" * 80)
    print("Test 2: Status Updates")
    print("=" * 80)
    
    # Simulate GSI creation progress
    print("\nSimulating GSI creation progress...")
    
    # Start first GSI
    print("\n1. Starting bookings.passenger-flight-index...")
    state_manager.update_gsi_status('bookings', 'passenger-flight-index', 'in_progress')
    
    # Complete first GSI
    print("2. Completed bookings.passenger-flight-index")
    state_manager.update_gsi_status('bookings', 'passenger-flight-index', 'active', retry_count=1)
    
    # Start second GSI
    print("3. Starting bookings.flight-status-index...")
    state_manager.update_gsi_status('bookings', 'flight-status-index', 'in_progress')
    
    # Fail second GSI after retries
    print("4. Failed bookings.flight-status-index after 3 retries")
    state_manager.update_gsi_status(
        'bookings', 
        'flight-status-index', 
        'failed', 
        retry_count=3,
        error='LimitExceededException: Too many GSIs'
    )
    
    # Start third GSI
    print("5. Starting Baggage.location-status-index...")
    state_manager.update_gsi_status('Baggage', 'location-status-index', 'in_progress')
    
    # Complete third GSI
    print("6. Completed Baggage.location-status-index")
    state_manager.update_gsi_status('Baggage', 'location-status-index', 'active', retry_count=2)
    
    state_manager.print_status()
    
    return state_manager


def test_resume_capability(state_manager):
    """Test resume capability."""
    print("=" * 80)
    print("Test 3: Resume Capability")
    print("=" * 80)
    
    # Get pending GSIs
    pending = state_manager.get_pending_gsis()
    print(f"\nPending GSIs: {len(pending)}")
    for table_name, index_name in pending:
        print(f"  - {table_name}.{index_name}")
    
    # Get failed GSIs
    failed = state_manager.get_failed_gsis()
    print(f"\nFailed GSIs: {len(failed)}")
    for table_name, index_name, error in failed:
        print(f"  - {table_name}.{index_name}")
        print(f"    Error: {error}")
    
    # Get resume point
    resume_point = state_manager.get_resume_point()
    if resume_point:
        table_name, index_name = resume_point
        print(f"\nResume point: {table_name}.{index_name}")
    else:
        print("\nNo resume point (all GSIs processed)")
    
    return state_manager


def test_state_persistence():
    """Test state persistence across instances."""
    print("=" * 80)
    print("Test 4: State Persistence")
    print("=" * 80)
    
    # Create new state manager instance (should load existing state)
    print("\nCreating new state manager instance...")
    new_state_manager = GSIStateManager(
        script_name="test_gsi_creation.py",
        state_dir="."
    )
    
    print("\nLoaded state from file:")
    new_state_manager.print_status()
    
    # Verify state matches
    summary = new_state_manager.get_summary()
    print(f"\nVerification:")
    print(f"  Total GSIs: {summary['total']}")
    print(f"  Active: {summary['active']}")
    print(f"  Failed: {summary['failed']}")
    print(f"  Pending: {summary['pending']}")
    
    return new_state_manager


def test_completion_and_cleanup(state_manager):
    """Test completion detection and cleanup."""
    print("=" * 80)
    print("Test 5: Completion and Cleanup")
    print("=" * 80)
    
    # Complete remaining GSI
    print("\nCompleting remaining GSI...")
    state_manager.update_gsi_status('CrewRoster', 'crew-duty-date-index', 'active', retry_count=1)
    
    state_manager.print_status()
    
    # Check if complete
    is_complete = state_manager.is_complete()
    print(f"\nAll GSIs complete: {is_complete}")
    
    if is_complete:
        print("\nCleaning up state file...")
        state_manager.cleanup()
        
        # Verify state file is archived
        state_file = Path(".gsi_creation_state.json")
        if not state_file.exists():
            print("✓ State file archived successfully")
        else:
            print("✗ State file still exists")
    
    return state_manager


def test_skip_logic(state_manager):
    """Test skip logic for already active GSIs."""
    print("=" * 80)
    print("Test 6: Skip Logic")
    print("=" * 80)
    
    # Test skip logic
    test_cases = [
        ('bookings', 'passenger-flight-index', True),  # Active - should skip
        ('bookings', 'flight-status-index', False),    # Failed - should not skip
        ('CrewRoster', 'crew-duty-date-index', True),  # Active - should skip
    ]
    
    print("\nTesting skip logic:")
    for table_name, index_name, expected_skip in test_cases:
        should_skip = state_manager.should_skip_gsi(table_name, index_name)
        status = state_manager.get_gsi_status(table_name, index_name)
        result = "✓" if should_skip == expected_skip else "✗"
        print(f"  {result} {table_name}.{index_name} (status: {status}, skip: {should_skip})")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("GSI State Manager Test Suite")
    print("=" * 80 + "\n")
    
    try:
        # Test 1: Initialization
        state_manager = test_state_initialization()
        input("\nPress Enter to continue to Test 2...")
        
        # Test 2: Status updates
        state_manager = test_status_updates(state_manager)
        input("\nPress Enter to continue to Test 3...")
        
        # Test 3: Resume capability
        state_manager = test_resume_capability(state_manager)
        input("\nPress Enter to continue to Test 4...")
        
        # Test 4: State persistence
        state_manager = test_state_persistence()
        input("\nPress Enter to continue to Test 5...")
        
        # Test 5: Completion and cleanup
        state_manager = test_completion_and_cleanup(state_manager)
        input("\nPress Enter to continue to Test 6...")
        
        # Test 6: Skip logic
        test_skip_logic(state_manager)
        
        print("\n" + "=" * 80)
        print("All tests completed!")
        print("=" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
