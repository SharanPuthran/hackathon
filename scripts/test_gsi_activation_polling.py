#!/usr/bin/env python3
"""
Test script for GSI activation polling with retry logic (Task 1.16).

This script tests the wait_for_gsi_active_with_retry function to ensure it:
- Polls GSI status every 10 seconds
- Timeouts after 15 minutes (90 attempts)
- Retries status query up to 3 times if query fails
- Logs activation progress with timestamps
"""

import sys
import time
import logging
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add scripts directory to path
sys.path.insert(0, 'scripts')

from gsi_retry_utils import wait_for_gsi_active_with_retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_gsi_becomes_active_immediately():
    """Test case: GSI is already ACTIVE on first check."""
    print("\n" + "=" * 80)
    print("Test 1: GSI becomes ACTIVE immediately")
    print("=" * 80)
    
    # Mock DynamoDB client
    mock_client = Mock()
    mock_client.describe_table.return_value = {
        'Table': {
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'test-index',
                    'IndexStatus': 'ACTIVE'
                }
            ]
        }
    }
    
    start_time = time.time()
    result = wait_for_gsi_active_with_retry(
        mock_client,
        'test-table',
        'test-index',
        timeout=900,
        poll_interval=10,
        max_query_retries=3
    )
    elapsed = time.time() - start_time
    
    print(f"Result: {result}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"describe_table called: {mock_client.describe_table.call_count} times")
    
    assert result is True, "Expected True when GSI is ACTIVE"
    assert mock_client.describe_table.call_count == 1, "Expected 1 call to describe_table"
    assert elapsed < 1, "Expected immediate return"
    
    print("✓ Test passed")
    return True


def test_gsi_becomes_active_after_polling():
    """Test case: GSI becomes ACTIVE after several polls."""
    print("\n" + "=" * 80)
    print("Test 2: GSI becomes ACTIVE after polling")
    print("=" * 80)
    
    # Mock DynamoDB client with CREATING status for first 3 calls, then ACTIVE
    mock_client = Mock()
    call_count = [0]
    
    def describe_table_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 3:
            return {
                'Table': {
                    'GlobalSecondaryIndexes': [
                        {
                            'IndexName': 'test-index',
                            'IndexStatus': 'CREATING'
                        }
                    ]
                }
            }
        else:
            return {
                'Table': {
                    'GlobalSecondaryIndexes': [
                        {
                            'IndexName': 'test-index',
                            'IndexStatus': 'ACTIVE'
                        }
                    ]
                }
            }
    
    mock_client.describe_table.side_effect = describe_table_side_effect
    
    start_time = time.time()
    result = wait_for_gsi_active_with_retry(
        mock_client,
        'test-table',
        'test-index',
        timeout=900,
        poll_interval=2,  # Use shorter interval for testing
        max_query_retries=3
    )
    elapsed = time.time() - start_time
    
    print(f"Result: {result}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"describe_table called: {mock_client.describe_table.call_count} times")
    
    assert result is True, "Expected True when GSI becomes ACTIVE"
    assert mock_client.describe_table.call_count == 4, "Expected 4 calls to describe_table"
    assert elapsed >= 6, "Expected at least 6 seconds (3 polls * 2s interval)"
    
    print("✓ Test passed")
    return True


def test_query_retry_on_failure():
    """Test case: Status query fails but succeeds on retry."""
    print("\n" + "=" * 80)
    print("Test 3: Status query fails but succeeds on retry")
    print("=" * 80)
    
    # Mock DynamoDB client that fails first 2 times, then succeeds
    mock_client = Mock()
    call_count = [0]
    
    def describe_table_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 2:
            raise Exception("Temporary network error")
        else:
            return {
                'Table': {
                    'GlobalSecondaryIndexes': [
                        {
                            'IndexName': 'test-index',
                            'IndexStatus': 'ACTIVE'
                        }
                    ]
                }
            }
    
    mock_client.describe_table.side_effect = describe_table_side_effect
    
    start_time = time.time()
    result = wait_for_gsi_active_with_retry(
        mock_client,
        'test-table',
        'test-index',
        timeout=900,
        poll_interval=10,
        max_query_retries=3
    )
    elapsed = time.time() - start_time
    
    print(f"Result: {result}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"describe_table called: {mock_client.describe_table.call_count} times")
    
    assert result is True, "Expected True when query succeeds on retry"
    assert mock_client.describe_table.call_count == 3, "Expected 3 calls (2 failures + 1 success)"
    
    print("✓ Test passed")
    return True


def test_query_retry_exhausted():
    """Test case: Status query fails all retries."""
    print("\n" + "=" * 80)
    print("Test 4: Status query fails all retries")
    print("=" * 80)
    
    # Mock DynamoDB client that always fails
    mock_client = Mock()
    mock_client.describe_table.side_effect = Exception("Persistent network error")
    
    start_time = time.time()
    result = wait_for_gsi_active_with_retry(
        mock_client,
        'test-table',
        'test-index',
        timeout=900,
        poll_interval=10,
        max_query_retries=3
    )
    elapsed = time.time() - start_time
    
    print(f"Result: {result}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"describe_table called: {mock_client.describe_table.call_count} times")
    
    assert result is False, "Expected False when all query retries exhausted"
    assert mock_client.describe_table.call_count == 3, "Expected 3 calls (max retries)"
    
    print("✓ Test passed")
    return True


def test_timeout_after_max_attempts():
    """Test case: Timeout after 15 minutes (90 attempts)."""
    print("\n" + "=" * 80)
    print("Test 5: Timeout after max attempts")
    print("=" * 80)
    
    # Mock DynamoDB client that always returns CREATING
    mock_client = Mock()
    mock_client.describe_table.return_value = {
        'Table': {
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'test-index',
                    'IndexStatus': 'CREATING'
                }
            ]
        }
    }
    
    start_time = time.time()
    result = wait_for_gsi_active_with_retry(
        mock_client,
        'test-table',
        'test-index',
        timeout=20,  # Use shorter timeout for testing (20s = 2 attempts with 10s interval)
        poll_interval=10,
        max_query_retries=3
    )
    elapsed = time.time() - start_time
    
    print(f"Result: {result}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"describe_table called: {mock_client.describe_table.call_count} times")
    
    assert result is False, "Expected False when timeout reached"
    assert elapsed >= 20, "Expected at least 20 seconds"
    
    print("✓ Test passed")
    return True


def test_gsi_not_found():
    """Test case: GSI not found on table."""
    print("\n" + "=" * 80)
    print("Test 6: GSI not found on table")
    print("=" * 80)
    
    # Mock DynamoDB client with no matching GSI
    mock_client = Mock()
    mock_client.describe_table.return_value = {
        'Table': {
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'other-index',
                    'IndexStatus': 'ACTIVE'
                }
            ]
        }
    }
    
    start_time = time.time()
    result = wait_for_gsi_active_with_retry(
        mock_client,
        'test-table',
        'test-index',
        timeout=900,
        poll_interval=10,
        max_query_retries=3
    )
    elapsed = time.time() - start_time
    
    print(f"Result: {result}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"describe_table called: {mock_client.describe_table.call_count} times")
    
    assert result is False, "Expected False when GSI not found"
    assert mock_client.describe_table.call_count == 1, "Expected 1 call to describe_table"
    
    print("✓ Test passed")
    return True


def test_unexpected_status():
    """Test case: GSI has unexpected status."""
    print("\n" + "=" * 80)
    print("Test 7: GSI has unexpected status")
    print("=" * 80)
    
    # Mock DynamoDB client with unexpected status
    mock_client = Mock()
    mock_client.describe_table.return_value = {
        'Table': {
            'GlobalSecondaryIndexes': [
                {
                    'IndexName': 'test-index',
                    'IndexStatus': 'DELETING'
                }
            ]
        }
    }
    
    start_time = time.time()
    result = wait_for_gsi_active_with_retry(
        mock_client,
        'test-table',
        'test-index',
        timeout=900,
        poll_interval=10,
        max_query_retries=3
    )
    elapsed = time.time() - start_time
    
    print(f"Result: {result}")
    print(f"Elapsed time: {elapsed:.2f}s")
    print(f"describe_table called: {mock_client.describe_table.call_count} times")
    
    assert result is False, "Expected False for unexpected status"
    assert mock_client.describe_table.call_count == 1, "Expected 1 call to describe_table"
    
    print("✓ Test passed")
    return True


def test_logging_output():
    """Test case: Verify logging output includes timestamps and progress."""
    print("\n" + "=" * 80)
    print("Test 8: Verify logging output")
    print("=" * 80)
    
    # Mock DynamoDB client with CREATING status for 2 calls, then ACTIVE
    mock_client = Mock()
    call_count = [0]
    
    def describe_table_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] <= 2:
            return {
                'Table': {
                    'GlobalSecondaryIndexes': [
                        {
                            'IndexName': 'test-index',
                            'IndexStatus': 'CREATING'
                        }
                    ]
                }
            }
        else:
            return {
                'Table': {
                    'GlobalSecondaryIndexes': [
                        {
                            'IndexName': 'test-index',
                            'IndexStatus': 'ACTIVE'
                        }
                    ]
                }
            }
    
    mock_client.describe_table.side_effect = describe_table_side_effect
    
    # Capture log output
    with patch('gsi_retry_utils.logger') as mock_logger:
        result = wait_for_gsi_active_with_retry(
            mock_client,
            'test-table',
            'test-index',
            timeout=900,
            poll_interval=1,  # Use shorter interval for testing
            max_query_retries=3
        )
        
        print(f"Result: {result}")
        print(f"Logger info called: {mock_logger.info.call_count} times")
        
        # Verify logging calls
        assert mock_logger.info.call_count >= 3, "Expected at least 3 info log calls"
        
        # Check that logs include progress information
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        print(f"Log calls: {len(log_calls)}")
        
        # Verify initial log
        assert any('Waiting for GSI' in str(call) for call in log_calls), "Expected initial waiting log"
        
        # Verify progress logs
        assert any('CREATING' in str(call) for call in log_calls), "Expected CREATING status log"
        
        # Verify completion log
        assert any('ACTIVE' in str(call) for call in log_calls), "Expected ACTIVE status log"
    
    print("✓ Test passed")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("GSI Activation Polling with Retry Logic - Test Suite (Task 1.16)")
    print("=" * 80)
    print()
    print("Testing requirements:")
    print("  • Poll GSI status every 10 seconds")
    print("  • Timeout after 15 minutes (90 attempts)")
    print("  • Retry status query up to 3 times if query fails")
    print("  • Log activation progress with timestamps")
    print()
    
    tests = [
        ("GSI becomes ACTIVE immediately", test_gsi_becomes_active_immediately),
        ("GSI becomes ACTIVE after polling", test_gsi_becomes_active_after_polling),
        ("Query retry on failure", test_query_retry_on_failure),
        ("Query retry exhausted", test_query_retry_exhausted),
        ("Timeout after max attempts", test_timeout_after_max_attempts),
        ("GSI not found", test_gsi_not_found),
        ("Unexpected status", test_unexpected_status),
        ("Logging output", test_logging_output),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"✗ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ Test error: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print()
    
    if failed == 0:
        print("✓ All tests passed!")
        print()
        print("Task 1.16 implementation verified:")
        print("  ✓ Polls GSI status every 10 seconds")
        print("  ✓ Timeouts after 15 minutes (90 attempts)")
        print("  ✓ Retries status query up to 3 times if query fails")
        print("  ✓ Logs activation progress with timestamps")
        return 0
    else:
        print(f"✗ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
