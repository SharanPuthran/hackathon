#!/usr/bin/env python3
import boto3
import time
from decimal import Decimal

"""
DynamoDB GSI Query Test Script

This script tests all created GSIs with real queries and demonstrates
performance improvements over table scans.

Tests:
- Bookings: Query by passenger_id and flight_id+status
- Baggage: Query by booking_id and location+status
- CrewRoster: Query by flight_id
- CargoFlightAssignments: Query by flight_id and shipment_id
- MaintenanceRoster: Query by workorder_id
"""

# Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')


def test_bookings_gsis():
    """Test Bookings table GSIs."""
    print("Testing Bookings GSIs...")
    table = dynamodb.Table('Bookings')

    try:
        # Test 1: passenger-flight-index
        # Query: Get all bookings for a specific passenger
        print("  1. Testing passenger-flight-index...")

        # Get a sample passenger_id from the table
        scan_response = table.scan(Limit=1)
        if scan_response['Items']:
            sample_passenger_id = str(scan_response['Items'][0]['passenger_id'])

            response = table.query(
                IndexName='passenger-flight-index',
                KeyConditionExpression='passenger_id = :pid',
                ExpressionAttributeValues={':pid': sample_passenger_id}
            )

            print(f"     ✓ Found {response['Count']} bookings for passenger {sample_passenger_id}")
            print(f"       RCU consumed: {response.get('ConsumedCapacity', {}).get('CapacityUnits', 'N/A')}")
        else:
            print("     ⚠ No data in Bookings table")

        # Test 2: flight-status-index
        # Query: Get all confirmed bookings for a flight
        print("  2. Testing flight-status-index...")

        # Get a sample flight_id
        if scan_response['Items']:
            sample_flight_id = str(scan_response['Items'][0]['flight_id'])

            response = table.query(
                IndexName='flight-status-index',
                KeyConditionExpression='flight_id = :fid AND booking_status = :status',
                ExpressionAttributeValues={
                    ':fid': sample_flight_id,
                    ':status': 'Confirmed'
                }
            )

            print(f"     ✓ Flight {sample_flight_id} has {response['Count']} confirmed bookings")
            print(f"       RCU consumed: {response.get('ConsumedCapacity', {}).get('CapacityUnits', 'N/A')}")
        else:
            print("     ⚠ No data in Bookings table")

        print()

    except Exception as e:
        print(f"     ✗ Error testing Bookings GSIs: {str(e)}")
        print()


def test_baggage_gsis():
    """Test Baggage table GSIs."""
    print("Testing Baggage GSIs...")
    table = dynamodb.Table('Baggage')

    try:
        # Test 1: booking-index
        print("  1. Testing booking-index...")

        # Get a sample booking_id
        scan_response = table.scan(Limit=1)
        if scan_response['Items']:
            sample_booking_id = str(scan_response['Items'][0]['booking_id'])

            response = table.query(
                IndexName='booking-index',
                KeyConditionExpression='booking_id = :bid',
                ExpressionAttributeValues={':bid': sample_booking_id}
            )

            print(f"     ✓ Booking {sample_booking_id} has {response['Count']} baggage items")
            print(f"       RCU consumed: {response.get('ConsumedCapacity', {}).get('CapacityUnits', 'N/A')}")
        else:
            print("     ⚠ No data in Baggage table")

        # Test 2: location-status-index
        print("  2. Testing location-status-index...")

        if scan_response['Items']:
            sample_location = str(scan_response['Items'][0].get('current_location', 'AUH'))

            response = table.query(
                IndexName='location-status-index',
                KeyConditionExpression='current_location = :loc',
                ExpressionAttributeValues={':loc': sample_location},
                Limit=10
            )

            print(f"     ✓ Location {sample_location} has {response['Count']} baggage items (showing 10)")
            print(f"       RCU consumed: {response.get('ConsumedCapacity', {}).get('CapacityUnits', 'N/A')}")
        else:
            print("     ⚠ No data in Baggage table")

        print()

    except Exception as e:
        print(f"     ✗ Error testing Baggage GSIs: {str(e)}")
        print()


def test_crew_roster_gsi():
    """Test CrewRoster table GSI."""
    print("Testing CrewRoster GSI...")
    table = dynamodb.Table('CrewRoster')

    try:
        # Test: flight-position-index
        print("  1. Testing flight-position-index...")

        # Get a sample flight_id
        scan_response = table.scan(Limit=1)
        if scan_response['Items']:
            sample_flight_id = str(scan_response['Items'][0]['flight_id'])

            response = table.query(
                IndexName='flight-position-index',
                KeyConditionExpression='flight_id = :fid',
                ExpressionAttributeValues={':fid': sample_flight_id}
            )

            print(f"     ✓ Flight {sample_flight_id} has {response['Count']} crew members assigned")
            print(f"       RCU consumed: {response.get('ConsumedCapacity', {}).get('CapacityUnits', 'N/A')}")
        else:
            print("     ⚠ No data in CrewRoster table")

        print()

    except Exception as e:
        print(f"     ✗ Error testing CrewRoster GSI: {str(e)}")
        print()


def test_cargo_gsis():
    """Test CargoFlightAssignments table GSIs."""
    print("Testing CargoFlightAssignments GSIs...")
    table = dynamodb.Table('CargoFlightAssignments')

    try:
        # Test 1: flight-loading-index
        print("  1. Testing flight-loading-index...")

        # Get a sample flight_id
        scan_response = table.scan(Limit=1)
        if scan_response['Items']:
            sample_flight_id = str(scan_response['Items'][0]['flight_id'])

            response = table.query(
                IndexName='flight-loading-index',
                KeyConditionExpression='flight_id = :fid',
                ExpressionAttributeValues={':fid': sample_flight_id}
            )

            print(f"     ✓ Flight {sample_flight_id} has {response['Count']} cargo assignments")
            print(f"       RCU consumed: {response.get('ConsumedCapacity', {}).get('CapacityUnits', 'N/A')}")
        else:
            print("     ⚠ No data in CargoFlightAssignments table")

        # Test 2: shipment-index
        print("  2. Testing shipment-index...")

        if scan_response['Items']:
            sample_shipment_id = str(scan_response['Items'][0]['shipment_id'])

            response = table.query(
                IndexName='shipment-index',
                KeyConditionExpression='shipment_id = :sid',
                ExpressionAttributeValues={':sid': sample_shipment_id}
            )

            print(f"     ✓ Shipment {sample_shipment_id} is on {response['Count']} flights")
            print(f"       RCU consumed: {response.get('ConsumedCapacity', {}).get('CapacityUnits', 'N/A')}")
        else:
            print("     ⚠ No data in CargoFlightAssignments table")

        print()

    except Exception as e:
        print(f"     ✗ Error testing CargoFlightAssignments GSIs: {str(e)}")
        print()


def test_maintenance_roster_gsi():
    """Test MaintenanceRoster table GSI."""
    print("Testing MaintenanceRoster GSI...")
    table = dynamodb.Table('MaintenanceRoster')

    try:
        # Test: workorder-shift-index
        print("  1. Testing workorder-shift-index...")

        # Get a sample workorder_id
        scan_response = table.scan(Limit=1)
        if scan_response['Items']:
            sample_workorder_id = str(scan_response['Items'][0]['workorder_id'])

            response = table.query(
                IndexName='workorder-shift-index',
                KeyConditionExpression='workorder_id = :wid',
                ExpressionAttributeValues={':wid': sample_workorder_id}
            )

            print(f"     ✓ Work order {sample_workorder_id} has {response['Count']} staff assigned")
            print(f"       RCU consumed: {response.get('ConsumedCapacity', {}).get('CapacityUnits', 'N/A')}")
        else:
            print("     ⚠ No data in MaintenanceRoster table")

        print()

    except Exception as e:
        print(f"     ✗ Error testing MaintenanceRoster GSI: {str(e)}")
        print()


def test_performance_comparison():
    """Compare scan vs GSI query performance."""
    print("Performance Comparison: Table Scan vs. GSI Query")
    print("-" * 80)

    table = dynamodb.Table('Bookings')

    try:
        # Get a sample passenger_id for testing
        scan_response = table.scan(Limit=1)
        if not scan_response['Items']:
            print("  ⚠ No data in Bookings table for performance test")
            return

        sample_passenger_id = str(scan_response['Items'][0]['passenger_id'])

        # Test 1: Table scan (inefficient)
        print("  WITHOUT GSI (Table Scan):")
        start_time = time.time()
        scan_response = table.scan(
            FilterExpression='passenger_id = :pid',
            ExpressionAttributeValues={':pid': sample_passenger_id}
        )
        scan_duration = (time.time() - start_time) * 1000  # Convert to ms

        print(f"    Items scanned: {scan_response.get('ScannedCount', 0)}")
        print(f"    Items returned: {scan_response['Count']}")
        print(f"    Duration: {scan_duration:.1f}ms")
        print()

        # Test 2: GSI query (efficient)
        print("  WITH GSI (Targeted Query):")
        start_time = time.time()
        query_response = table.query(
            IndexName='passenger-flight-index',
            KeyConditionExpression='passenger_id = :pid',
            ExpressionAttributeValues={':pid': sample_passenger_id}
        )
        query_duration = (time.time() - start_time) * 1000  # Convert to ms

        print(f"    Items read: {query_response['Count']}")
        print(f"    Duration: {query_duration:.1f}ms")
        print()

        # Calculate improvements
        if scan_response.get('ScannedCount', 0) > 0 and query_response['Count'] > 0:
            scan_efficiency = (scan_response['Count'] / scan_response['ScannedCount']) * 100
            speedup = scan_duration / query_duration if query_duration > 0 else 1

            print("  Performance Improvement:")
            print(f"    Scan efficiency: {scan_efficiency:.2f}% (returned {scan_response['Count']} out of {scan_response['ScannedCount']} scanned)")
            print(f"    Speedup: {speedup:.1f}x faster with GSI")
            print(f"    RCU savings: ~{100 - scan_efficiency:.1f}% fewer items read")
        print()

    except Exception as e:
        print(f"  ✗ Error in performance test: {str(e)}")
        print()


def main():
    """Main entry point."""
    print("=" * 80)
    print("DynamoDB GSI Query Tests")
    print("=" * 80)
    print()

    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity['Account']}")
    except Exception as e:
        print(f"Error: AWS credentials not configured: {e}")
        return 1

    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    print(f"Region: {region}")
    print()

    # Run all tests
    test_bookings_gsis()
    test_baggage_gsis()
    test_crew_roster_gsi()
    test_cargo_gsis()
    test_maintenance_roster_gsi()

    # Performance comparison
    test_performance_comparison()

    print("=" * 80)
    print("✓ All GSI query tests completed!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
