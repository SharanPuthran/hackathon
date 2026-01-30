#!/usr/bin/env python3
import boto3
import argparse
import time
import sys
from datetime import datetime

"""
DynamoDB GSI Creation Tool

This script creates Global Secondary Indexes (GSIs) on existing DynamoDB tables
to improve query performance. It implements high-priority GSIs based on common
query patterns.

GSIs created:
- Bookings: 2 GSIs (passenger-flight, flight-status)
- Baggage: 2 GSIs (booking, location-status)
- CrewRoster: 1 GSI (flight-position)
- CargoFlightAssignments: 2 GSIs (flight-loading, shipment)
- MaintenanceRoster: 1 GSI (workorder-shift)
"""

# Initialize DynamoDB client
dynamodb_client = boto3.client('dynamodb')

# GSI Definitions - High Priority Only
GSI_DEFINITIONS = {
    'Bookings': [
        {
            'IndexName': 'passenger-flight-index',
            'KeySchema': [
                {'AttributeName': 'passenger_id', 'KeyType': 'HASH'},
                {'AttributeName': 'flight_id', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'passenger_id', 'AttributeType': 'S'},
                {'AttributeName': 'flight_id', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all bookings for a specific passenger'
        },
        {
            'IndexName': 'flight-status-index',
            'KeySchema': [
                {'AttributeName': 'flight_id', 'KeyType': 'HASH'},
                {'AttributeName': 'booking_status', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'flight_id', 'AttributeType': 'S'},
                {'AttributeName': 'booking_status', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all bookings for a flight by status (e.g., Confirmed)'
        }
    ],
    'Baggage': [
        {
            'IndexName': 'booking-index',
            'KeySchema': [
                {'AttributeName': 'booking_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'booking_id', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all baggage for a specific booking'
        },
        {
            'IndexName': 'location-status-index',
            'KeySchema': [
                {'AttributeName': 'current_location', 'KeyType': 'HASH'},
                {'AttributeName': 'baggage_status', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'current_location', 'AttributeType': 'S'},
                {'AttributeName': 'baggage_status', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all baggage at a location by status (e.g., MISHANDLED at AUH)'
        }
    ],
    'CrewRoster': [
        {
            'IndexName': 'flight-position-index',
            'KeySchema': [
                {'AttributeName': 'flight_id', 'KeyType': 'HASH'},
                {'AttributeName': 'position_id', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'flight_id', 'AttributeType': 'S'},
                {'AttributeName': 'position_id', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all crew assigned to a specific flight'
        }
    ],
    'CargoFlightAssignments': [
        {
            'IndexName': 'flight-loading-index',
            'KeySchema': [
                {'AttributeName': 'flight_id', 'KeyType': 'HASH'},
                {'AttributeName': 'loading_status', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'flight_id', 'AttributeType': 'S'},
                {'AttributeName': 'loading_status', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all cargo on a flight by loading status'
        },
        {
            'IndexName': 'shipment-index',
            'KeySchema': [
                {'AttributeName': 'shipment_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'shipment_id', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Track a shipment across multiple flights'
        }
    ],
    'MaintenanceRoster': [
        {
            'IndexName': 'workorder-shift-index',
            'KeySchema': [
                {'AttributeName': 'workorder_id', 'KeyType': 'HASH'},
                {'AttributeName': 'shift_start_zulu', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'workorder_id', 'AttributeType': 'S'},
                {'AttributeName': 'shift_start_zulu', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all staff working on a specific work order'
        }
    ]
}


def table_exists(table_name):
    """Check if a DynamoDB table exists."""
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except dynamodb_client.exceptions.ResourceNotFoundException:
        return False
    except Exception as e:
        print(f"  ⚠ Error checking table {table_name}: {str(e)}")
        return False


def get_existing_gsis(table_name):
    """Get list of existing GSI names for a table."""
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        gsis = response['Table'].get('GlobalSecondaryIndexes', [])
        return {gsi['IndexName']: gsi['IndexStatus'] for gsi in gsis}
    except Exception as e:
        print(f"  ⚠ Error getting GSIs for {table_name}: {str(e)}")
        return {}


def get_attribute_definitions(table_name):
    """Get existing attribute definitions from table."""
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        return response['Table'].get('AttributeDefinitions', [])
    except:
        return []


def create_gsi(table_name, gsi_config):
    """
    Create a Global Secondary Index on a DynamoDB table.

    Args:
        table_name: Name of the table
        gsi_config: GSI configuration dictionary

    Returns:
        True if successful, False otherwise
    """
    try:
        # Get existing attribute definitions
        existing_attrs = get_attribute_definitions(table_name)
        existing_attr_names = {attr['AttributeName'] for attr in existing_attrs}

        # Merge new attribute definitions with existing ones
        new_attrs = gsi_config['AttributeDefinitions']
        for attr in new_attrs:
            if attr['AttributeName'] not in existing_attr_names:
                existing_attrs.append(attr)

        # Create GSI (billing mode is inherited from table)
        response = dynamodb_client.update_table(
            TableName=table_name,
            AttributeDefinitions=existing_attrs,
            GlobalSecondaryIndexUpdates=[{
                'Create': {
                    'IndexName': gsi_config['IndexName'],
                    'KeySchema': gsi_config['KeySchema'],
                    'Projection': gsi_config['Projection']
                }
            }]
        )

        return True

    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"  ⚠ Table {table_name} is being updated, please try again later")
        return False
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower():
            print(f"  ℹ GSI {gsi_config['IndexName']} already exists")
            return True
        else:
            print(f"  ✗ Error creating GSI: {error_msg}")
            return False


def wait_for_gsi_active(table_name, index_name, timeout=600):
    """
    Wait for a GSI to become ACTIVE.

    Args:
        table_name: Name of the table
        index_name: Name of the GSI
        timeout: Maximum wait time in seconds (default: 10 minutes)

    Returns:
        True if GSI is ACTIVE, False if timeout or error
    """
    start_time = time.time()
    print(f"  Waiting for {index_name} to become ACTIVE...", end='', flush=True)

    while time.time() - start_time < timeout:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            gsis = response['Table'].get('GlobalSecondaryIndexes', [])

            for gsi in gsis:
                if gsi['IndexName'] == index_name:
                    status = gsi['IndexStatus']

                    if status == 'ACTIVE':
                        elapsed = int(time.time() - start_time)
                        print(f" ✓ ACTIVE ({elapsed}s)")
                        return True
                    elif status == 'CREATING':
                        print(".", end='', flush=True)
                    else:
                        print(f" ✗ Unexpected status: {status}")
                        return False

            time.sleep(10)  # Check every 10 seconds

        except Exception as e:
            print(f" ✗ Error: {str(e)}")
            return False

    print(" ✗ Timeout")
    return False


def check_gsi_status(table_name):
    """Check and display status of all GSIs on a table."""
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        gsis = response['Table'].get('GlobalSecondaryIndexes', [])

        if not gsis:
            print(f"  No GSIs found on table {table_name}")
            return

        print(f"  GSIs on {table_name}:")
        for gsi in gsis:
            index_name = gsi['IndexName']
            status = gsi['IndexStatus']
            item_count = gsi.get('ItemCount', 'N/A')
            size_bytes = gsi.get('IndexSizeBytes', 0)
            size_mb = size_bytes / 1024 / 1024 if size_bytes > 0 else 0

            status_symbol = "✓" if status == "ACTIVE" else "⏳"
            print(f"    {status_symbol} {index_name}: {status} | {item_count} items | {size_mb:.2f} MB")

    except Exception as e:
        print(f"  ✗ Error checking GSIs: {str(e)}")


def main():
    """Main entry point for GSI creation tool."""
    parser = argparse.ArgumentParser(
        description='Create Global Secondary Indexes on DynamoDB tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create all high-priority GSIs
  python3 add_dynamodb_gsis.py

  # Create GSIs for specific table
  python3 add_dynamodb_gsis.py --table Bookings

  # Check GSI status
  python3 add_dynamodb_gsis.py --check-status
        '''
    )

    parser.add_argument(
        '--table',
        help='Create GSIs for specific table only',
        default=None
    )

    parser.add_argument(
        '--check-status',
        action='store_true',
        help='Check status of existing GSIs'
    )

    parser.add_argument(
        '--no-wait',
        action='store_true',
        help='Do not wait for GSI backfill to complete'
    )

    args = parser.parse_args()

    # Print header
    print("=" * 80)
    print("DynamoDB GSI Creation Tool")
    print("=" * 80)
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

    # Check status mode
    if args.check_status:
        print("Checking GSI status...")
        print()

        for table_name in GSI_DEFINITIONS.keys():
            if args.table and table_name != args.table:
                continue

            print(f"{table_name}:")
            check_gsi_status(table_name)
            print()

        return 0

    # Filter tables if requested
    tables_to_process = GSI_DEFINITIONS
    if args.table:
        if args.table not in GSI_DEFINITIONS:
            print(f"Error: Table '{args.table}' not found in GSI definitions")
            print(f"Available tables: {', '.join(GSI_DEFINITIONS.keys())}")
            return 1
        tables_to_process = {args.table: GSI_DEFINITIONS[args.table]}

    # Count total GSIs
    total_gsis = sum(len(gsis) for gsis in tables_to_process.values())

    print(f"Creating GSIs for {len(tables_to_process)} tables...")
    print()

    start_time = datetime.now()
    created_count = 0
    failed_count = 0

    for idx, (table_name, gsis) in enumerate(tables_to_process.items(), 1):
        print(f"[{idx}/{len(tables_to_process)}] {table_name}")

        # Check if table exists
        if not table_exists(table_name):
            print(f"  ✗ Table does not exist")
            failed_count += len(gsis)
            print()
            continue

        # Get existing GSIs
        existing_gsis = get_existing_gsis(table_name)

        # Create each GSI
        for gsi_config in gsis:
            index_name = gsi_config['IndexName']
            description = gsi_config.get('Description', '')

            print(f"  Creating {index_name}...")
            if description:
                print(f"    Use case: {description}")

            # Skip if already exists
            if index_name in existing_gsis:
                status = existing_gsis[index_name]
                if status == 'ACTIVE':
                    print(f"    ✓ Already exists and is ACTIVE")
                    created_count += 1
                else:
                    print(f"    ⏳ Already exists with status: {status}")
                continue

            # Create GSI
            if create_gsi(table_name, gsi_config):
                # Wait for GSI to become active
                if not args.no_wait:
                    if wait_for_gsi_active(table_name, index_name):
                        created_count += 1
                    else:
                        failed_count += 1
                else:
                    print(f"    ℹ GSI created, not waiting for backfill")
                    created_count += 1
            else:
                failed_count += 1

        print()

    duration = datetime.now() - start_time

    # Print summary
    print("=" * 80)
    print("GSI Creation Summary")
    print("=" * 80)
    print(f"Total Tables: {len(tables_to_process)}")
    print(f"Total GSIs: {total_gsis}")
    print(f"Created/Verified: {created_count}")
    print(f"Failed: {failed_count}")
    print(f"Duration: {duration}")
    print()

    if failed_count == 0:
        print("✓ All GSIs created successfully!")
    else:
        print(f"⚠ GSI creation completed with {failed_count} failures")

    print()
    print("View tables in AWS Console:")
    print(f"  https://console.aws.amazon.com/dynamodbv2/home?region={region}#tables")
    print()
    print("=" * 80)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
