#!/usr/bin/env python3
"""
Create New DynamoDB GSIs for Multi-Round Orchestration

This script creates the new Global Secondary Indexes required for the
SkyMarshal multi-round orchestration rearchitecture.

New GSIs:
- Flights: flight-number-date-index (for flight lookup by number and date)
- Flights: aircraft-registration-index (for aircraft-based queries)
- Bookings: flight-id-index (for passenger queries by flight)
- MaintenanceWorkOrders: aircraft-registration-index (for maintenance by aircraft)
"""

import boto3
import argparse
import asyncio
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Initialize DynamoDB client
dynamodb_client = boto3.client('dynamodb')

# New GSI Definitions for Multi-Round Orchestration
NEW_GSI_DEFINITIONS = {
    'flights': [
        {
            'IndexName': 'flight-number-date-index',
            'KeySchema': [
                {'AttributeName': 'flight_number', 'KeyType': 'HASH'},
                {'AttributeName': 'scheduled_departure', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'flight_number', 'AttributeType': 'S'},
                {'AttributeName': 'scheduled_departure', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query flights by flight number and date (e.g., EY123 on 2026-01-20)'
        },
        {
            'IndexName': 'aircraft-registration-index',
            'KeySchema': [
                {'AttributeName': 'aircraft_registration', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'aircraft_registration', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all flights for a specific aircraft'
        }
    ],
    'bookings': [
        {
            'IndexName': 'flight-id-index',
            'KeySchema': [
                {'AttributeName': 'flight_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'flight_id', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all passenger bookings for a specific flight'
        }
    ],
    'MaintenanceWorkOrders': [
        {
            'IndexName': 'aircraft-registration-index',
            'KeySchema': [
                {'AttributeName': 'aircraftRegistration', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'aircraftRegistration', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query all maintenance work orders for a specific aircraft'
        }
    ],
    'CrewRoster': [
        {
            'IndexName': 'flight-position-index',
            'KeySchema': [
                {'AttributeName': 'flight_id', 'KeyType': 'HASH'},
                {'AttributeName': 'position', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'flight_id', 'AttributeType': 'S'},
                {'AttributeName': 'position', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query crew roster by flight and position'
        }
    ],
    'CargoFlightAssignments': [
        {
            'IndexName': 'flight-loading-index',
            'KeySchema': [
                {'AttributeName': 'flight_id', 'KeyType': 'HASH'},
                {'AttributeName': 'loading_priority', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'flight_id', 'AttributeType': 'S'},
                {'AttributeName': 'loading_priority', 'AttributeType': 'N'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query cargo assignments by flight and loading priority'
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
            'Description': 'Query cargo assignments by shipment ID'
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
            'Description': 'Query baggage by booking ID'
        }
    ]
}


def table_exists(table_name: str) -> bool:
    """Check if a DynamoDB table exists."""
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except dynamodb_client.exceptions.ResourceNotFoundException:
        return False
    except Exception as e:
        print(f"  ⚠ Error checking table {table_name}: {str(e)}")
        return False


def get_existing_gsis(table_name: str) -> Dict[str, str]:
    """Get list of existing GSI names and their statuses for a table."""
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        gsis = response['Table'].get('GlobalSecondaryIndexes', [])
        return {gsi['IndexName']: gsi['IndexStatus'] for gsi in gsis}
    except Exception as e:
        print(f"  ⚠ Error getting GSIs for {table_name}: {str(e)}")
        return {}


def get_attribute_definitions(table_name: str) -> List[Dict]:
    """Get existing attribute definitions from table."""
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        return response['Table'].get('AttributeDefinitions', [])
    except:
        return []


async def create_gsi_async(table_name: str, gsi_config: Dict, wait: bool = True, validate: bool = False) -> Tuple[bool, str]:
    """
    Create a Global Secondary Index on a DynamoDB table (async).

    Args:
        table_name: Name of the table
        gsi_config: GSI configuration dictionary
        wait: Whether to wait for GSI to become ACTIVE
        validate: Whether to validate GSI performance

    Returns:
        Tuple of (success: bool, message: str)
    """
    index_name = gsi_config['IndexName']
    description = gsi_config.get('Description', '')

    print(f"  Creating {index_name}...")
    if description:
        print(f"    Use case: {description}")

    try:
        # Check if already exists
        existing_gsis = get_existing_gsis(table_name)
        if index_name in existing_gsis:
            status = existing_gsis[index_name]
            if status == 'ACTIVE':
                print(f"    ✓ Already exists and is ACTIVE")
                if validate:
                    validate_gsi_performance(table_name, index_name)
                return (True, f"Already exists and is ACTIVE")
            else:
                print(f"    ⏳ Already exists with status: {status}")
                return (True, f"Already exists with status: {status}")

        # Get existing attribute definitions
        existing_attrs = get_attribute_definitions(table_name)
        existing_attr_names = {attr['AttributeName'] for attr in existing_attrs}

        # Merge new attribute definitions with existing ones
        new_attrs = gsi_config['AttributeDefinitions']
        for attr in new_attrs:
            if attr['AttributeName'] not in existing_attr_names:
                existing_attrs.append(attr)

        # Create GSI (billing mode is inherited from table)
        dynamodb_client.update_table(
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

        # Wait for GSI to become active
        if wait:
            if await wait_for_gsi_active(table_name, index_name):
                if validate:
                    validate_gsi_performance(table_name, index_name)
                return (True, "Created and ACTIVE")
            else:
                return (False, "Failed to become ACTIVE")
        else:
            print(f"    ℹ GSI created, not waiting for backfill")
            return (True, "Created, not waiting")

    except dynamodb_client.exceptions.ResourceInUseException:
        msg = f"Table {table_name} is being updated, please try again later"
        print(f"  ⚠ {msg}")
        return (False, msg)
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower():
            print(f"  ℹ GSI {index_name} already exists")
            return (True, "Already exists")
        else:
            print(f"  ✗ Error creating GSI: {error_msg}")
            return (False, error_msg)


async def process_table_gsis(table_name: str, gsis: List[Dict], wait: bool = True, validate: bool = False) -> Tuple[int, int]:
    """
    Process all GSIs for a single table concurrently.

    Args:
        table_name: Name of the table
        gsis: List of GSI configurations
        wait: Whether to wait for GSIs to become ACTIVE
        validate: Whether to validate GSI performance

    Returns:
        Tuple of (created_count, failed_count)
    """
    print(f"{table_name}")

    # Check if table exists
    if not table_exists(table_name):
        print(f"  ✗ Table does not exist")
        return (0, len(gsis))

    # Create all GSIs for this table concurrently
    tasks = [create_gsi_async(table_name, gsi_config, wait, validate) for gsi_config in gsis]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    created_count = 0
    failed_count = 0

    for result in results:
        if isinstance(result, Exception):
            print(f"  ✗ Exception: {result}")
            failed_count += 1
        else:
            success, message = result
            if success:
                created_count += 1
            else:
                failed_count += 1

    print()
    return (created_count, failed_count)


async def wait_for_gsi_active(table_name: str, index_name: str, timeout: int = 600) -> bool:
    """
    Wait for a GSI to become ACTIVE (async).

    Args:
        table_name: Name of the table
        index_name: Name of the GSI
        timeout: Maximum wait time in seconds (default: 10 minutes)

    Returns:
        True if GSI is ACTIVE, False if timeout or error
    """
    start_time = asyncio.get_event_loop().time()
    print(f"  Waiting for {index_name} to become ACTIVE...", end='', flush=True)

    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            gsis = response['Table'].get('GlobalSecondaryIndexes', [])

            for gsi in gsis:
                if gsi['IndexName'] == index_name:
                    status = gsi['IndexStatus']

                    if status == 'ACTIVE':
                        elapsed = int(asyncio.get_event_loop().time() - start_time)
                        print(f" ✓ ACTIVE ({elapsed}s)")
                        return True
                    elif status == 'CREATING':
                        print(".", end='', flush=True)
                    else:
                        print(f" ✗ Unexpected status: {status}")
                        return False

            await asyncio.sleep(10)  # Check every 10 seconds

        except Exception as e:
            print(f" ✗ Error: {str(e)}")
            return False

    print(" ✗ Timeout")
    return False


def delete_gsi(table_name: str, index_name: str) -> bool:
    """
    Delete a Global Secondary Index (rollback capability).

    Args:
        table_name: Name of the table
        index_name: Name of the GSI to delete

    Returns:
        True if successful, False otherwise
    """
    try:
        dynamodb_client.update_table(
            TableName=table_name,
            GlobalSecondaryIndexUpdates=[{
                'Delete': {
                    'IndexName': index_name
                }
            }]
        )
        print(f"  ✓ GSI {index_name} deletion initiated")
        return True

    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"  ⚠ Table {table_name} is being updated, please try again later")
        return False
    except Exception as e:
        print(f"  ✗ Error deleting GSI: {str(e)}")
        return False


def check_gsi_status(table_name: str) -> None:
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


def validate_gsi_performance(table_name: str, index_name: str) -> bool:
    """
    Validate GSI performance with a sample query.

    Args:
        table_name: Name of the table
        index_name: Name of the GSI

    Returns:
        True if query successful, False otherwise
    """
    try:
        # Perform a simple query to validate the GSI works
        response = dynamodb_client.query(
            TableName=table_name,
            IndexName=index_name,
            Limit=1,
            Select='COUNT'
        )
        print(f"  ✓ GSI {index_name} query validation successful")
        return True
    except Exception as e:
        print(f"  ⚠ GSI {index_name} query validation failed: {str(e)}")
        return False


def main():
    """Main entry point for GSI creation tool."""
    parser = argparse.ArgumentParser(
        description='Create new DynamoDB GSIs for multi-round orchestration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create all new GSIs
  python3 scripts/create_gsis.py

  # Create GSIs for specific table
  python3 scripts/create_gsis.py --table flights

  # Check GSI status
  python3 scripts/create_gsis.py --check-status

  # Rollback (delete) GSIs
  python3 scripts/create_gsis.py --rollback

  # Skip waiting for GSI activation
  python3 scripts/create_gsis.py --no-wait
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

    parser.add_argument(
        '--rollback',
        action='store_true',
        help='Delete the new GSIs (rollback)'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate GSI performance with sample queries'
    )

    args = parser.parse_args()

    # Print header
    print("=" * 80)
    print("DynamoDB GSI Creation Tool - Multi-Round Orchestration (Async)")
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

        for table_name in NEW_GSI_DEFINITIONS.keys():
            if args.table and table_name != args.table:
                continue

            print(f"{table_name}:")
            check_gsi_status(table_name)
            print()

        return 0

    # Rollback mode
    if args.rollback:
        print("⚠ ROLLBACK MODE: Deleting new GSIs...")
        print()

        tables_to_process = NEW_GSI_DEFINITIONS
        if args.table:
            if args.table not in NEW_GSI_DEFINITIONS:
                print(f"Error: Table '{args.table}' not found in GSI definitions")
                return 1
            tables_to_process = {args.table: NEW_GSI_DEFINITIONS[args.table]}

        deleted_count = 0
        failed_count = 0

        for table_name, gsis in tables_to_process.items():
            print(f"{table_name}:")

            if not table_exists(table_name):
                print(f"  ✗ Table does not exist")
                continue

            existing_gsis = get_existing_gsis(table_name)

            for gsi_config in gsis:
                index_name = gsi_config['IndexName']

                if index_name not in existing_gsis:
                    print(f"  ℹ GSI {index_name} does not exist, skipping")
                    continue

                print(f"  Deleting {index_name}...")
                if delete_gsi(table_name, index_name):
                    deleted_count += 1
                else:
                    failed_count += 1

            print()

        print(f"Deleted: {deleted_count}, Failed: {failed_count}")
        return 0 if failed_count == 0 else 1

    # Filter tables if requested
    tables_to_process = NEW_GSI_DEFINITIONS
    if args.table:
        if args.table not in NEW_GSI_DEFINITIONS:
            print(f"Error: Table '{args.table}' not found in GSI definitions")
            print(f"Available tables: {', '.join(NEW_GSI_DEFINITIONS.keys())}")
            return 1
        tables_to_process = {args.table: NEW_GSI_DEFINITIONS[args.table]}

    # Count total GSIs
    total_gsis = sum(len(gsis) for gsis in tables_to_process.values())

    print(f"Creating {total_gsis} new GSIs for {len(tables_to_process)} tables (async)...")
    print()

    start_time = datetime.now()

    # Run async GSI creation
    created_count, failed_count = asyncio.run(create_all_gsis_async(
        tables_to_process,
        wait=not args.no_wait,
        validate=args.validate
    ))

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
        print()
        print("Next steps:")
        print("  1. Validate GSI performance: python3 scripts/create_gsis.py --validate")
        print("  2. Check GSI status: python3 scripts/create_gsis.py --check-status")
        print("  3. Update agent code to use new GSIs")
    else:
        print(f"⚠ GSI creation completed with {failed_count} failures")

    print()
    print("View tables in AWS Console:")
    print(f"  https://console.aws.amazon.com/dynamodbv2/home?region={region}#tables")
    print()
    print("=" * 80)

    return 0 if failed_count == 0 else 1


async def create_all_gsis_async(tables_to_process: Dict[str, List[Dict]], wait: bool = True, validate: bool = False) -> Tuple[int, int]:
    """
    Create all GSIs across all tables concurrently.

    Args:
        tables_to_process: Dictionary of table names to GSI configurations
        wait: Whether to wait for GSIs to become ACTIVE
        validate: Whether to validate GSI performance

    Returns:
        Tuple of (total_created_count, total_failed_count)
    """
    # Process all tables concurrently
    tasks = [
        process_table_gsis(table_name, gsis, wait, validate)
        for table_name, gsis in tables_to_process.items()
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    total_created = 0
    total_failed = 0

    for result in results:
        if isinstance(result, Exception):
            print(f"✗ Exception processing table: {result}")
            total_failed += 1
        else:
            created, failed = result
            total_created += created
            total_failed += failed

    return (total_created, total_failed)


if __name__ == "__main__":
    sys.exit(main())
