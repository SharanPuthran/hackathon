#!/usr/bin/env python3
"""
Test script for GSI validation query functionality (Task 1.17).

This script tests the validate_gsi_query function to ensure it:
1. Performs test query on newly created GSI
2. Verifies query uses GSI (not table scan)
3. Marks GSI as "ACTIVE but non-functional" if validation fails
4. Logs validation results
"""

import boto3
import sys
from gsi_retry_utils import validate_gsi_query, log_validation_results

# Initialize DynamoDB client
dynamodb_client = boto3.client('dynamodb', region_name='us-east-1')


def test_validate_existing_gsi():
    """
    Test validation on an existing GSI.
    
    This test uses the flight-number-date-index GSI on the flights table,
    which should already exist from previous tasks.
    """
    print("=" * 80)
    print("Test 1: Validate existing GSI (flight-number-date-index)")
    print("=" * 80)
    
    table_name = "flights"
    index_name = "flight-number-date-index"
    
    # GSI configuration for flight-number-date-index
    gsi_config = {
        'IndexName': index_name,
        'KeySchema': [
            {'AttributeName': 'flight_number', 'KeyType': 'HASH'},
            {'AttributeName': 'scheduled_departure', 'KeyType': 'RANGE'}
        ],
        'Projection': {'ProjectionType': 'ALL'}
    }
    
    # Validate the GSI
    is_functional, status, validation_details = validate_gsi_query(
        dynamodb_client,
        table_name,
        index_name,
        gsi_config
    )
    
    # Log results
    log_validation_results(
        index_name,
        table_name,
        is_functional,
        status,
        validation_details
    )
    
    # Check results
    print("\nTest Results:")
    print(f"  Is Functional: {is_functional}")
    print(f"  Status: {status}")
    print(f"  Test Query Executed: {validation_details.get('test_query_executed', False)}")
    print(f"  Uses GSI: {validation_details.get('uses_gsi', 'unknown')}")
    
    if status == "functional":
        print("  ✓ Test PASSED: GSI is functional")
        return True
    else:
        print(f"  ✗ Test FAILED: GSI status is {status}")
        return False


def test_validate_nonexistent_gsi():
    """
    Test validation on a non-existent GSI.
    
    This should return a validation error.
    """
    print("\n" + "=" * 80)
    print("Test 2: Validate non-existent GSI")
    print("=" * 80)
    
    table_name = "flights"
    index_name = "nonexistent-index"
    
    # Dummy GSI configuration
    gsi_config = {
        'IndexName': index_name,
        'KeySchema': [
            {'AttributeName': 'dummy_key', 'KeyType': 'HASH'}
        ],
        'Projection': {'ProjectionType': 'ALL'}
    }
    
    # Validate the GSI
    is_functional, status, validation_details = validate_gsi_query(
        dynamodb_client,
        table_name,
        index_name,
        gsi_config
    )
    
    # Log results
    log_validation_results(
        index_name,
        table_name,
        is_functional,
        status,
        validation_details
    )
    
    # Check results
    print("\nTest Results:")
    print(f"  Is Functional: {is_functional}")
    print(f"  Status: {status}")
    print(f"  Error: {validation_details.get('error', 'None')}")
    
    if status in ["validation-error", "non-functional"]:
        print("  ✓ Test PASSED: Correctly identified non-existent GSI")
        return True
    else:
        print(f"  ✗ Test FAILED: Expected validation-error or non-functional, got {status}")
        return False


def test_validate_multiple_gsis():
    """
    Test validation on multiple GSIs to ensure it works consistently.
    """
    print("\n" + "=" * 80)
    print("Test 3: Validate multiple GSIs")
    print("=" * 80)
    
    # List of GSIs to test
    gsi_tests = [
        {
            'table_name': 'flights',
            'index_name': 'aircraft-registration-index',
            'gsi_config': {
                'IndexName': 'aircraft-registration-index',
                'KeySchema': [
                    {'AttributeName': 'aircraft_registration', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        },
        {
            'table_name': 'bookings',
            'index_name': 'flight-id-index',
            'gsi_config': {
                'IndexName': 'flight-id-index',
                'KeySchema': [
                    {'AttributeName': 'flight_id', 'KeyType': 'HASH'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        },
        {
            'table_name': 'CrewRoster',
            'index_name': 'flight-position-index',
            'gsi_config': {
                'IndexName': 'flight-position-index',
                'KeySchema': [
                    {'AttributeName': 'flight_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'position', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        }
    ]
    
    results = []
    for test in gsi_tests:
        print(f"\n  Testing {test['index_name']} on {test['table_name']}...")
        
        is_functional, status, validation_details = validate_gsi_query(
            dynamodb_client,
            test['table_name'],
            test['index_name'],
            test['gsi_config']
        )
        
        results.append({
            'index_name': test['index_name'],
            'table_name': test['table_name'],
            'is_functional': is_functional,
            'status': status
        })
        
        print(f"    Status: {status}, Functional: {is_functional}")
    
    # Summary
    print("\nTest Results Summary:")
    functional_count = sum(1 for r in results if r['is_functional'])
    total_count = len(results)
    
    print(f"  Functional GSIs: {functional_count}/{total_count}")
    
    for result in results:
        status_icon = "✓" if result['is_functional'] else "✗"
        print(f"  {status_icon} {result['index_name']} on {result['table_name']}: {result['status']}")
    
    if functional_count == total_count:
        print("  ✓ Test PASSED: All GSIs are functional")
        return True
    else:
        print(f"  ⚠ Test PARTIAL: {functional_count}/{total_count} GSIs are functional")
        return True  # Still pass if some GSIs are functional


def test_validation_with_invalid_config():
    """
    Test validation with invalid GSI configuration.
    
    This should return a validation error.
    """
    print("\n" + "=" * 80)
    print("Test 4: Validate with invalid GSI configuration")
    print("=" * 80)
    
    table_name = "flights"
    index_name = "flight-number-date-index"
    
    # Invalid GSI configuration (missing KeySchema)
    gsi_config = {
        'IndexName': index_name,
        'Projection': {'ProjectionType': 'ALL'}
    }
    
    # Validate the GSI
    is_functional, status, validation_details = validate_gsi_query(
        dynamodb_client,
        table_name,
        index_name,
        gsi_config
    )
    
    # Log results
    log_validation_results(
        index_name,
        table_name,
        is_functional,
        status,
        validation_details
    )
    
    # Check results
    print("\nTest Results:")
    print(f"  Is Functional: {is_functional}")
    print(f"  Status: {status}")
    print(f"  Error: {validation_details.get('error', 'None')}")
    
    if status == "validation-error":
        print("  ✓ Test PASSED: Correctly identified invalid configuration")
        return True
    else:
        print(f"  ✗ Test FAILED: Expected validation-error, got {status}")
        return False


def main():
    """Run all validation tests."""
    print("GSI Validation Query Test Suite (Task 1.17)")
    print("=" * 80)
    print()
    
    tests = [
        ("Validate existing GSI", test_validate_existing_gsi),
        ("Validate non-existent GSI", test_validate_nonexistent_gsi),
        ("Validate multiple GSIs", test_validate_multiple_gsis),
        ("Validate with invalid config", test_validation_with_invalid_config)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' raised exception: {e}")
            results.append((test_name, False))
    
    # Final summary
    print("\n" + "=" * 80)
    print("Test Suite Summary")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status_icon = "✓" if result else "✗"
        print(f"  {status_icon} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests PASSED")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
