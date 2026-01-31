#!/usr/bin/env python3
"""
Test script to verify retry logic implementation.
"""

import sys
sys.path.insert(0, 'scripts')

from gsi_retry_utils import (
    RetryConfig,
    get_retry_delay,
    extract_error_type,
    generate_failure_report,
    should_continue_on_failure
)

def test_retry_config():
    """Test RetryConfig initialization."""
    print("Testing RetryConfig...")
    
    config = RetryConfig()
    assert config.max_attempts == 5
    assert config.backoff_delays == (30, 60, 120, 240, 480)
    assert config.continue_on_failure == True
    
    print("  ✓ Default configuration correct")
    
    custom_config = RetryConfig(max_attempts=3, backoff_delays=(10, 20, 30))
    assert custom_config.max_attempts == 3
    assert custom_config.backoff_delays == (10, 20, 30)
    
    print("  ✓ Custom configuration correct")

def test_get_retry_delay():
    """Test retry delay calculation."""
    print("\nTesting get_retry_delay...")
    
    config = RetryConfig()
    
    # Test exponential backoff
    assert get_retry_delay(0, config) == 30
    assert get_retry_delay(1, config) == 60
    assert get_retry_delay(2, config) == 120
    assert get_retry_delay(3, config) == 240
    assert get_retry_delay(4, config) == 480
    assert get_retry_delay(5, config) == 480  # Use last delay for attempts beyond configured
    
    print("  ✓ Exponential backoff delays correct")
    
    # Test error-specific delays
    assert get_retry_delay(0, config, 'ResourceInUseException') == 0
    assert get_retry_delay(0, config, 'LimitExceededException') == 300
    assert get_retry_delay(0, config, 'ValidationException') == 0
    
    print("  ✓ Error-specific delays correct")

def test_extract_error_type():
    """Test error type extraction."""
    print("\nTesting extract_error_type...")
    
    assert extract_error_type("ResourceInUseException: Table is being updated") == "ResourceInUseException"
    assert extract_error_type("LimitExceededException: Too many requests") == "LimitExceededException"
    assert extract_error_type("ValidationException: Invalid attribute") == "ValidationException"
    assert extract_error_type("ThrottlingException: Rate exceeded") == "ThrottlingException"
    assert extract_error_type("InternalServerError: Server error") == "InternalServerError"
    assert extract_error_type("Unknown error") is None
    
    print("  ✓ Error type extraction correct")

def test_generate_failure_report():
    """Test failure report generation."""
    print("\nTesting generate_failure_report...")
    
    retry_history = [
        {
            'attempt': 1,
            'timestamp': '2026-01-31T12:00:00',
            'error': 'ResourceInUseException',
            'error_type': 'ResourceInUseException'
        },
        {
            'attempt': 2,
            'timestamp': '2026-01-31T12:01:00',
            'error': 'ThrottlingException',
            'error_type': 'ThrottlingException'
        }
    ]
    
    report = generate_failure_report('test-index', 'test-table', retry_history)
    
    assert report['gsi_name'] == 'test-index'
    assert report['table_name'] == 'test-table'
    assert report['total_attempts'] == 2
    assert len(report['failure_reasons']) == 2
    assert 'recommended_actions' in report
    
    print("  ✓ Failure report generation correct")

def test_should_continue_on_failure():
    """Test continue on failure logic."""
    print("\nTesting should_continue_on_failure...")
    
    config_continue = RetryConfig(continue_on_failure=True)
    config_stop = RetryConfig(continue_on_failure=False)
    
    assert should_continue_on_failure(config_continue) == True
    assert should_continue_on_failure(config_continue, 'ResourceInUseException') == True
    
    # Critical errors should stop even if continue_on_failure is False
    assert should_continue_on_failure(config_stop, 'InternalServerError') == False
    assert should_continue_on_failure(config_stop, 'ThrottlingException') == False
    
    print("  ✓ Continue on failure logic correct")

def main():
    """Run all tests."""
    print("=" * 80)
    print("Testing GSI Retry Logic Implementation")
    print("=" * 80)
    
    try:
        test_retry_config()
        test_get_retry_delay()
        test_extract_error_type()
        test_generate_failure_report()
        test_should_continue_on_failure()
        
        print("\n" + "=" * 80)
        print("✓ All tests passed!")
        print("=" * 80)
        return 0
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
