#!/usr/bin/env python3
"""
Demo script to show retry logic in action with simulated failures.
"""

import asyncio
import sys
sys.path.insert(0, 'scripts')

from gsi_retry_utils import RetryConfig, log_retry_attempt, generate_failure_report
from datetime import datetime

async def simulate_gsi_creation_with_retries(gsi_name: str, table_name: str, failure_pattern: list):
    """
    Simulate GSI creation with configurable failure pattern.
    
    Args:
        gsi_name: Name of the GSI
        table_name: Name of the table
        failure_pattern: List of error types for each attempt (None = success)
    """
    retry_config = RetryConfig(max_attempts=5)
    retry_history = []
    
    print(f"\n{'='*80}")
    print(f"Simulating GSI Creation: {gsi_name} on {table_name}")
    print(f"Failure Pattern: {failure_pattern}")
    print(f"{'='*80}\n")
    
    for attempt in range(retry_config.max_attempts):
        print(f"Attempt {attempt + 1}/{retry_config.max_attempts}...")
        
        # Simulate the attempt
        if attempt < len(failure_pattern) and failure_pattern[attempt] is not None:
            error_type = failure_pattern[attempt]
            error_msg = f"Simulated {error_type}"
            
            retry_history.append({
                'attempt': attempt + 1,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'error_type': error_type
            })
            
            if attempt < retry_config.max_attempts - 1:
                # Calculate delay based on error type
                if error_type == 'ResourceInUseException':
                    delay = 0
                elif error_type == 'LimitExceededException':
                    delay = 300
                elif error_type == 'ThrottlingException':
                    delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
                else:
                    delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
                
                log_retry_attempt(gsi_name, table_name, attempt + 1, retry_config.max_attempts, error_msg, len(retry_history), delay)
                print(f"  ⚠ Error: {error_msg}")
                print(f"  ⏳ Retrying in {delay}s (attempt {attempt + 2}/{retry_config.max_attempts})...")
                
                # Simulate delay (shortened for demo)
                await asyncio.sleep(min(delay / 10, 2))  # Max 2 seconds for demo
                continue
            else:
                print(f"  ✗ Failed after {retry_config.max_attempts} attempts")
                
                # Generate failure report
                failure_report = generate_failure_report(gsi_name, table_name, retry_history)
                print(f"\n  Failure Report:")
                print(f"    Total Attempts: {failure_report['total_attempts']}")
                print(f"    Failure Reasons: {failure_report['failure_reasons']}")
                print(f"    Recommended Actions:")
                for action in failure_report['recommended_actions'][:3]:
                    print(f"      - {action}")
                
                return False
        else:
            # Success!
            print(f"  ✓ GSI created successfully!")
            if retry_history:
                print(f"  ℹ Succeeded after {len(retry_history)} failed attempts")
            return True
    
    return False

async def main():
    """Run demo scenarios."""
    print("\n" + "="*80)
    print("GSI Retry Logic Demo")
    print("="*80)
    
    # Scenario 1: Success on first attempt
    print("\n\nScenario 1: Success on First Attempt")
    print("-" * 80)
    await simulate_gsi_creation_with_retries(
        "test-index-1",
        "test-table",
        [None]  # Success immediately
    )
    
    # Scenario 2: Fail once, then succeed
    print("\n\nScenario 2: Fail Once (ResourceInUseException), Then Succeed")
    print("-" * 80)
    await simulate_gsi_creation_with_retries(
        "test-index-2",
        "test-table",
        ['ResourceInUseException', None]  # Fail once, then succeed
    )
    
    # Scenario 3: Multiple failures with exponential backoff
    print("\n\nScenario 3: Multiple Failures with Exponential Backoff")
    print("-" * 80)
    await simulate_gsi_creation_with_retries(
        "test-index-3",
        "test-table",
        ['ThrottlingException', 'ThrottlingException', None]  # Fail twice, then succeed
    )
    
    # Scenario 4: All attempts exhausted
    print("\n\nScenario 4: All Attempts Exhausted")
    print("-" * 80)
    await simulate_gsi_creation_with_retries(
        "test-index-4",
        "test-table",
        ['ThrottlingException'] * 5  # Fail all 5 attempts
    )
    
    # Scenario 5: Mixed error types
    print("\n\nScenario 5: Mixed Error Types")
    print("-" * 80)
    await simulate_gsi_creation_with_retries(
        "test-index-5",
        "test-table",
        ['ResourceInUseException', 'ThrottlingException', 'LimitExceededException', None]
    )
    
    print("\n" + "="*80)
    print("Demo Complete!")
    print("="*80 + "\n")

if __name__ == '__main__':
    asyncio.run(main())
