#!/usr/bin/env python3
"""
Demo script showing state file and resume capability.

This script demonstrates:
1. Creating GSIs with state tracking
2. Resuming from interruption
3. Handling failures with state persistence
4. Cleaning up state file on completion
"""

import asyncio
import sys
from gsi_state_manager import GSIStateManager
from enhanced_gsi_creation import create_gsi_with_error_specific_retry
from gsi_retry_utils import RetryConfig


# Sample GSI definitions for demo
DEMO_GSI_DEFINITIONS = {
    'bookings': [
        {
            'IndexName': 'demo-index-1',
            'KeySchema': [
                {'AttributeName': 'demo_key_1', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'demo_key_1', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Demo GSI 1 for testing state management'
        },
        {
            'IndexName': 'demo-index-2',
            'KeySchema': [
                {'AttributeName': 'demo_key_2', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'demo_key_2', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Demo GSI 2 for testing state management'
        }
    ],
    'Baggage': [
        {
            'IndexName': 'demo-index-3',
            'KeySchema': [
                {'AttributeName': 'demo_key_3', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'demo_key_3', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Demo GSI 3 for testing state management'
        }
    ]
}


async def create_gsis_with_state(resume: bool = False):
    """
    Create GSIs with state tracking and resume capability.
    
    Args:
        resume: Whether to resume from previous state
    """
    print("=" * 80)
    print("GSI Creation with State Management")
    print("=" * 80)
    
    # Initialize state manager
    state_manager = GSIStateManager(
        script_name="demo_state_resume.py",
        state_dir="."
    )
    
    # Initialize GSI definitions
    if not resume:
        print("\nInitializing new GSI creation session...")
        state_manager.initialize_gsis(DEMO_GSI_DEFINITIONS)
    else:
        print("\nResuming from previous session...")
        if not state_manager.gsis:
            print("No previous state found. Starting fresh.")
            state_manager.initialize_gsis(DEMO_GSI_DEFINITIONS)
    
    # Print initial status
    state_manager.print_status()
    
    # Configure retry settings
    retry_config = RetryConfig(
        max_attempts=3,  # Reduced for demo
        backoff_delays=(5, 10, 20),
        continue_on_failure=True
    )
    
    # Process each GSI
    results = []
    
    for table_name, gsi_configs in DEMO_GSI_DEFINITIONS.items():
        for gsi_config in gsi_configs:
            index_name = gsi_config['IndexName']
            
            # Check if should skip (already active)
            if state_manager.should_skip_gsi(table_name, index_name):
                print(f"\n✓ Skipping {table_name}.{index_name} (already active)")
                continue
            
            # Check if should retry (previously failed)
            status = state_manager.get_gsi_status(table_name, index_name)
            if status == "failed":
                print(f"\n⚠ Retrying {table_name}.{index_name} (previously failed)")
            
            print(f"\n{'=' * 80}")
            print(f"Creating GSI: {table_name}.{index_name}")
            print(f"{'=' * 80}")
            
            try:
                # Create GSI with state tracking
                success, message, metadata = await create_gsi_with_error_specific_retry(
                    table_name=table_name,
                    gsi_config=gsi_config,
                    wait=False,  # Don't wait for demo (would take too long)
                    validate=False,
                    retry_config=retry_config,
                    state_manager=state_manager
                )
                
                results.append({
                    'table': table_name,
                    'index': index_name,
                    'success': success,
                    'message': message,
                    'attempts': metadata.get('attempts', 0)
                })
                
                if success:
                    print(f"\n✓ Success: {message}")
                else:
                    print(f"\n✗ Failed: {message}")
                
            except KeyboardInterrupt:
                print("\n\n⚠ Interrupted by user!")
                print("State has been saved. You can resume by running:")
                print("  python3 demo_state_resume.py --resume")
                state_manager.print_status()
                sys.exit(1)
            
            except Exception as e:
                print(f"\n✗ Unexpected error: {e}")
                state_manager.update_gsi_status(
                    table_name,
                    index_name,
                    "failed",
                    error=str(e)
                )
    
    # Print final status
    print("\n" + "=" * 80)
    print("GSI Creation Complete")
    print("=" * 80)
    
    state_manager.print_status()
    
    # Print results summary
    print("\nResults Summary:")
    print("-" * 80)
    for result in results:
        status_icon = "✓" if result['success'] else "✗"
        print(f"{status_icon} {result['table']}.{result['index']}: {result['message']} "
              f"(attempts: {result['attempts']})")
    
    # Check if all complete
    if state_manager.is_complete():
        print("\n✓ All GSIs processed!")
        
        # Ask user if they want to clean up state file
        response = input("\nClean up state file? (y/n): ")
        if response.lower() == 'y':
            state_manager.cleanup()
            print("State file archived.")
    else:
        print("\n⚠ Some GSIs are still pending or in progress.")
        print("Run with --resume to continue.")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Demo GSI creation with state management and resume capability"
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous state'
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("GSI State Management Demo")
    print("=" * 80)
    print("\nThis demo shows how state management works:")
    print("1. State is saved after each GSI operation")
    print("2. You can interrupt (Ctrl+C) and resume later")
    print("3. Failed GSIs can be retried")
    print("4. State file is cleaned up on completion")
    print("\nNOTE: This is a demo - GSIs won't actually be created")
    print("=" * 80 + "\n")
    
    try:
        asyncio.run(create_gsis_with_state(resume=args.resume))
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
