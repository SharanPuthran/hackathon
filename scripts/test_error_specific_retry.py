#!/usr/bin/env python3
"""
Test error-specific retry strategies for GSI creation.

This script validates that all error-specific retry strategies are correctly
implemented as specified in Task 1.15.
"""

import asyncio
from unittest.mock import Mock, patch, MagicMock
from gsi_retry_utils import (
    RetryConfig,
    ErrorSpecificRetryHandler,
    extract_error_type,
    get_error_specific_delay,
    is_validation_attribute_conflict,
    should_retry_error,
    get_error_description
)


def test_extract_error_type():
    """Test error type extraction from error messages."""
    print("Testing error type extraction...")
    
    test_cases = [
        ("ResourceInUseException: Table is being updated", "ResourceInUseException"),
        ("LimitExceededException: Too many requests", "LimitExceededException"),
        ("ValidationException: Attribute already defined", "ValidationException"),
        ("ThrottlingException: Rate exceeded", "ThrottlingException"),
        ("InternalServerError: Internal error", "InternalServerError"),
        ("Some other error", None)
    ]
    
    for error_msg, expected_type in test_cases:
        result = extract_error_type(error_msg)
        status = "✓" if result == expected_type else "✗"
        print(f"  {status} '{error_msg[:50]}...' -> {result} (expected: {expected_type})")
        if result != expected_type:
            return False
    
    print("  ✓ All error type extraction tests passed\n")
    return True


def test_error_specific_delays():
    """Test error-specific delay calculations."""
    print("Testing error-specific delays...")
    
    config = RetryConfig()
    
    test_cases = [
        ("ResourceInUseException", 0, 5, "5s delay for table availability"),
        ("LimitExceededException", 0, 300, "5 minutes for limit reset"),
        ("ValidationException", 0, 0, "Immediate retry after merge"),
        ("ThrottlingException", 0, 30, "Exponential backoff (30s)"),
        ("ThrottlingException", 1, 60, "Exponential backoff (60s)"),
        ("InternalServerError", 0, 30, "Exponential backoff (30s)"),
        ("InternalServerError", 2, 120, "Exponential backoff (120s)"),
    ]
    
    for error_type, attempt, expected_delay, description in test_cases:
        result = get_error_specific_delay(error_type, attempt, config)
        status = "✓" if result == expected_delay else "✗"
        print(f"  {status} {error_type} (attempt {attempt}): {result}s (expected: {expected_delay}s) - {description}")
        if result != expected_delay:
            return False
    
    print("  ✓ All error-specific delay tests passed\n")
    return True


def test_validation_attribute_conflict():
    """Test detection of ValidationException attribute conflicts."""
    print("Testing ValidationException attribute conflict detection...")
    
    test_cases = [
        ("ValidationException: Attribute already defined", True),
        ("ValidationException: AttributeDefinition conflict", True),
        ("ValidationException: duplicate attribute name", True),
        ("ValidationException: Invalid key schema", False),
        ("ThrottlingException: Rate exceeded", False),
    ]
    
    for error_msg, expected_result in test_cases:
        result = is_validation_attribute_conflict(error_msg)
        status = "✓" if result == expected_result else "✗"
        print(f"  {status} '{error_msg}' -> {result} (expected: {expected_result})")
        if result != expected_result:
            return False
    
    print("  ✓ All ValidationException detection tests passed\n")
    return True


def test_should_retry_error():
    """Test retry decision logic."""
    print("Testing retry decision logic...")
    
    test_cases = [
        ("ResourceInUseException", 0, 5, True, "Should retry on first attempt"),
        ("ResourceInUseException", 4, 5, False, "Should not retry after max attempts"),
        ("LimitExceededException", 2, 5, True, "Should retry LimitExceededException"),
        ("ValidationException", 1, 5, True, "Should retry ValidationException"),
        ("ThrottlingException", 3, 5, True, "Should retry ThrottlingException"),
        ("InternalServerError", 0, 5, True, "Should retry InternalServerError"),
        ("UnknownError", 2, 5, True, "Should retry unknown errors"),
    ]
    
    for error_type, attempt, max_attempts, expected_result, description in test_cases:
        result = should_retry_error(error_type, attempt, max_attempts)
        status = "✓" if result == expected_result else "✗"
        print(f"  {status} {error_type} (attempt {attempt}/{max_attempts}): {result} (expected: {expected_result}) - {description}")
        if result != expected_result:
            return False
    
    print("  ✓ All retry decision tests passed\n")
    return True


def test_error_descriptions():
    """Test error description generation."""
    print("Testing error descriptions...")
    
    error_types = [
        "ResourceInUseException",
        "LimitExceededException",
        "ValidationException",
        "ThrottlingException",
        "InternalServerError"
    ]
    
    for error_type in error_types:
        description = get_error_description(error_type)
        status = "✓" if description and len(description) > 0 else "✗"
        print(f"  {status} {error_type}: {description}")
        if not description:
            return False
    
    print("  ✓ All error description tests passed\n")
    return True


def test_error_handler():
    """Test ErrorSpecificRetryHandler class."""
    print("Testing ErrorSpecificRetryHandler...")
    
    config = RetryConfig(max_attempts=3)
    handler = ErrorSpecificRetryHandler(config)
    
    # Test handling ResourceInUseException
    error = Exception("ResourceInUseException: Table is being updated")
    should_retry, delay, description = handler.handle_error(error, 0)
    
    if not should_retry:
        print("  ✗ Should retry ResourceInUseException")
        return False
    if delay != 5:
        print(f"  ✗ Wrong delay for ResourceInUseException: {delay}s (expected: 5s)")
        return False
    print(f"  ✓ ResourceInUseException: should_retry={should_retry}, delay={delay}s")
    
    # Test handling LimitExceededException
    error = Exception("LimitExceededException: Too many requests")
    should_retry, delay, description = handler.handle_error(error, 1)
    
    if not should_retry:
        print("  ✗ Should retry LimitExceededException")
        return False
    if delay != 300:
        print(f"  ✗ Wrong delay for LimitExceededException: {delay}s (expected: 300s)")
        return False
    print(f"  ✓ LimitExceededException: should_retry={should_retry}, delay={delay}s")
    
    # Test max attempts reached
    error = Exception("ThrottlingException: Rate exceeded")
    should_retry, delay, description = handler.handle_error(error, 2)
    
    if should_retry:
        print("  ✗ Should not retry after max attempts")
        return False
    print(f"  ✓ Max attempts: should_retry={should_retry}")
    
    # Test retry history
    history = handler.get_retry_history()
    if len(history) != 3:
        print(f"  ✗ Wrong retry history length: {len(history)} (expected: 3)")
        return False
    print(f"  ✓ Retry history: {len(history)} entries")
    
    print("  ✓ All ErrorSpecificRetryHandler tests passed\n")
    return True


def test_retry_strategy_summary():
    """Print summary of retry strategies."""
    print("=" * 70)
    print("RETRY STRATEGY SUMMARY")
    print("=" * 70)
    
    strategies = [
        ("ResourceInUseException", "Wait for table availability, retry with 5s delay"),
        ("LimitExceededException", "Wait 5 minutes (300s) for limit reset"),
        ("ValidationException", "Merge attribute definitions, retry immediately (0s)"),
        ("ThrottlingException", "Exponential backoff (30s, 60s, 120s, 240s, 480s)"),
        ("InternalServerError", "Exponential backoff (30s, 60s, 120s, 240s, 480s)")
    ]
    
    for error_type, strategy in strategies:
        print(f"\n{error_type}:")
        print(f"  Strategy: {strategy}")
        print(f"  Description: {get_error_description(error_type)}")
    
    print("\n" + "=" * 70)
    print()


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("TESTING ERROR-SPECIFIC RETRY STRATEGIES (Task 1.15)")
    print("=" * 70 + "\n")
    
    tests = [
        ("Error Type Extraction", test_extract_error_type),
        ("Error-Specific Delays", test_error_specific_delays),
        ("ValidationException Detection", test_validation_attribute_conflict),
        ("Retry Decision Logic", test_should_retry_error),
        ("Error Descriptions", test_error_descriptions),
        ("ErrorSpecificRetryHandler", test_error_handler)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}\n")
    
    # Print retry strategy summary
    test_retry_strategy_summary()
    
    # Print results
    print("=" * 70)
    print("TEST RESULTS")
    print("=" * 70)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    
    if failed == 0:
        print("\n✓ ALL TESTS PASSED - Error-specific retry strategies are correctly implemented")
        return 0
    else:
        print(f"\n✗ {failed} TEST(S) FAILED - Please review implementation")
        return 1


if __name__ == "__main__":
    exit(main())
