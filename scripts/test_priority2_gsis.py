#!/usr/bin/env python3
"""
Test Priority 2 DynamoDB GSIs

This script validates that Priority 2 GSIs are created, ACTIVE, and perform as expected.
It tests the specific use cases for each GSI:
- Regulatory Agent: Curfew compliance checks
- Cargo Agent: Cold chain identification
- Maintenance Agent: Conflict detection
"""

import boto3
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')

# Priority 2 GSI Test Definitions
PRIORITY2_GSI_TESTS = {
    'flights': {
        'gsi_name': 'airport-curfew-index',
        'description': 'Curfew compliance checks (Regulatory Agent)',
        'test_query': {
            'IndexName': 'airport-curfew-index',
            'KeyConditionExpression': 'destination_airport_id = :airport',
            'ExpressionAttributeValues': {
                ':airport': 'AUH'  # Abu Dhabi airport
            },
            'Limit': 10
        },
        'expected_impact': '20-50x performance improvement',
        'query_volume': '100+ queries/day'
    },
    'CargoShipments': {
        'gsi_name': 'cargo-temperature-index',
        'description': 'Cold chain identification (Cargo Agent)',
        'test_query': {
            'IndexName': 'cargo-temperature-index',
            'KeyConditionExpression': 'commodity_type_id = :commodity',
            'ExpressionAttributeValues': {
                ':commodity': 1  # Perishables
            },
            'Limit': 10
        },
        'expected_impact': '20-50x performance improvement',
        'query_volume': '150+ queries/day'
    },
    'MaintenanceWorkOrders': {
        'gsi_name': 'aircraft-maintenance-date-index',
        'description': 'Maintenance conflict detection (Maintenance Agent)',
        'test_query': {
            'IndexName': 'aircraft-maintenance-date-index',
            'KeyConditionExpression': 'aircraft_registration = :reg',
            'ExpressionAttributeValues': {
                ':reg': 'A6-EYA'  # Sample aircraft
            },
            'Limit': 10
        },
        'expected_impact': '20-50x performance improvement',
        'query_volume': '80+ queries/day'
    }
}


def check_table_exists(table_name: str) -> bool:
    """Check if a DynamoDB table exists."""
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except dynamodb_client.exceptions.ResourceNotFoundException:
        return False
    except Exception as e:
        print(f"  ⚠ Error checking table {table_name}: {str(e)}")
        return False


def check_gsi_exists(table_name: str, gsi_name: str) -> Tuple[bool, str]:
    """
    Check if a GSI exists and return its status.

    Returns:
        Tuple of (exists: bool, status: str)
    """
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        gsis = response['Table'].get('GlobalSecondaryIndexes', [])

        for gsi in gsis:
            if gsi['IndexName'] == gsi_name:
                return (True, gsi['IndexStatus'])

        return (False, 'NOT_FOUND')

    except Exception as e:
        print(f"  ⚠ Error checking GSI: {str(e)}")
        return (False, 'ERROR')


def test_gsi_query(table_name: str, test_config: Dict) -> Tuple[bool, str, float]:
    """
    Test a GSI query and measure performance.

    Returns:
        Tuple of (success: bool, message: str, latency_ms: float)
    """
    gsi_name = test_config['gsi_name']
    test_query = test_config['test_query']

    try:
        table = dynamodb.Table(table_name)

        # Measure query latency
        start_time = datetime.now()

        response = table.query(**test_query)

        end_time = datetime.now()
        latency_ms = (end_time - start_time).total_seconds() * 1000

        item_count = len(response.get('Items', []))

        return (True, f"Query successful: {item_count} items returned", latency_ms)

    except Exception as e:
        return (False, f"Query failed: {str(e)}", 0.0)


def run_priority2_gsi_tests() -> Dict:
    """
    Run all Priority 2 GSI tests.

    Returns:
        Dictionary with test results
    """
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_tests': len(PRIORITY2_GSI_TESTS),
        'passed': 0,
        'failed': 0,
        'tests': {}
    }

    print("=" * 80)
    print("Priority 2 GSI Validation Tests")
    print("=" * 80)
    print()

    for table_name, test_config in PRIORITY2_GSI_TESTS.items():
        gsi_name = test_config['gsi_name']
        description = test_config['description']

        print(f"Testing {table_name}.{gsi_name}")
        print(f"  Use case: {description}")

        test_result = {
            'table': table_name,
            'gsi': gsi_name,
            'description': description,
            'expected_impact': test_config['expected_impact'],
            'query_volume': test_config['query_volume'],
            'checks': {}
        }

        # Check 1: Table exists
        print(f"  [1/3] Checking table exists...", end=' ')
        if check_table_exists(table_name):
            print("✓")
            test_result['checks']['table_exists'] = True
        else:
            print("✗ Table not found")
            test_result['checks']['table_exists'] = False
            test_result['status'] = 'FAILED'
            results['tests'][f"{table_name}.{gsi_name}"] = test_result
            results['failed'] += 1
            print()
            continue

        # Check 2: GSI exists and is ACTIVE
        print(f"  [2/3] Checking GSI status...", end=' ')
        exists, status = check_gsi_exists(table_name, gsi_name)

        if not exists:
            print(f"✗ GSI not found")
            test_result['checks']['gsi_exists'] = False
            test_result['checks']['gsi_status'] = 'NOT_FOUND'
            test_result['status'] = 'FAILED'
            results['tests'][f"{table_name}.{gsi_name}"] = test_result
            results['failed'] += 1
            print()
            continue

        test_result['checks']['gsi_exists'] = True
        test_result['checks']['gsi_status'] = status

        if status != 'ACTIVE':
            print(f"✗ GSI status: {status} (expected ACTIVE)")
            test_result['status'] = 'FAILED'
            results['tests'][f"{table_name}.{gsi_name}"] = test_result
            results['failed'] += 1
            print()
            continue

        print(f"✓ ACTIVE")

        # Check 3: Query performance
        print(f"  [3/3] Testing query performance...", end=' ')
        success, message, latency_ms = test_gsi_query(table_name, test_config)

        test_result['checks']['query_success'] = success
        test_result['checks']['query_message'] = message
        test_result['checks']['latency_ms'] = latency_ms

        if not success:
            print(f"✗ {message}")
            test_result['status'] = 'FAILED'
            results['tests'][f"{table_name}.{gsi_name}"] = test_result
            results['failed'] += 1
            print()
            continue

        # Check latency target (<100ms)
        if latency_ms > 100:
            print(f"⚠ {message} (latency: {latency_ms:.2f}ms, target: <100ms)")
            test_result['status'] = 'WARNING'
        else:
            print(f"✓ {message} (latency: {latency_ms:.2f}ms)")
            test_result['status'] = 'PASSED'

        results['tests'][f"{table_name}.{gsi_name}"] = test_result
        results['passed'] += 1
        print()

    return results


def print_summary(results: Dict) -> None:
    """Print test summary."""
    print("=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print()

    if results['failed'] == 0:
        print("✓ All Priority 2 GSIs validated successfully!")
        print()
        print("Performance Summary:")
        for test_name, test_result in results['tests'].items():
            if test_result['status'] == 'PASSED':
                latency = test_result['checks']['latency_ms']
                print(f"  • {test_name}: {latency:.2f}ms")
        print()
        print("Expected Benefits:")
        print("  • Regulatory Agent: Faster curfew compliance checks")
        print("  • Cargo Agent: Faster cold chain identification")
        print("  • Maintenance Agent: Faster conflict detection")
    else:
        print(f"⚠ {results['failed']} test(s) failed")
        print()
        print("Failed tests:")
        for test_name, test_result in results['tests'].items():
            if test_result['status'] == 'FAILED':
                print(f"  • {test_name}")
                if 'query_message' in test_result['checks']:
                    print(f"    Reason: {test_result['checks']['query_message']}")

    print()
    print("=" * 80)


def save_results(results: Dict, filename: str = 'priority2_gsi_test_results.json') -> None:
    """Save test results to JSON file."""
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {filename}")


def main():
    """Main entry point."""
    print()
    print("Priority 2 GSI Validation Test Suite")
    print("Testing: Curfew compliance, Cold chain, Maintenance conflicts")
    print()

    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity['Account']}")
        print(f"User: {identity['Arn'].split('/')[-1]}")
    except Exception as e:
        print(f"Error: AWS credentials not configured: {e}")
        print("Please run: aws configure")
        return 1

    # Get AWS region
    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    print(f"Region: {region}")
    print()

    # Run tests
    results = run_priority2_gsi_tests()

    # Print summary
    print_summary(results)

    # Save results
    save_results(results)

    # Return exit code
    return 0 if results['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
