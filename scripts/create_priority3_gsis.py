#!/usr/bin/env python3
"""
Create Priority 3 DynamoDB GSIs for Multi-Round Orchestration

This script creates the Priority 3 (Future Enhancement) Global Secondary Indexes for
the SkyMarshal multi-round orchestration rearchitecture.

Priority 3 GSIs (Future Enhancement):
- CargoShipments: cargo-value-index (PK: shipment_value DESC)
- Flights: flight-revenue-index (PK: flight_id, SK: total_revenue)
- CrewMembers: crew-qualification-index (PK: aircraft_type_id, SK: qualification_expiry)
- NOTAMs: notam-validity-index (PK: airport_code, SK: notam_start)

These GSIs are nice-to-have for future optimization and advanced features.
"""

import boto3
import argparse
import asyncio
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from gsi_retry_utils import RetryConfig, log_retry_attempt, generate_failure_report

# Initialize DynamoDB client
dynamodb_client = boto3.client('dynamodb')

# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    backoff_delays=(30, 60, 120, 240, 480),
    continue_on_failure=True
)

# Priority 3 GSI Definitions (Future Enhancement)
PRIORITY3_GSI_DEFINITIONS = {
    'CargoShipments': [
        {
            'IndexName': 'cargo-value-index',
            'KeySchema': [
                {'AttributeName': 'shipment_value', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'shipment_value', 'AttributeType': 'N'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Identify high-value cargo for prioritization decisions (Cargo Agent)',
            'EstimatedImpact': '10-20x performance improvement, 50+ queries/day',
            'RequiredBy': 'Cargo Agent',
            'UseCase': 'High-value cargo prioritization during disruptions'
        }
    ],
    'flights': [
        {
            'IndexName': 'flight-revenue-index',
            'KeySchema': [
                {'AttributeName': 'flight_id', 'KeyType': 'HASH'},
                {'AttributeName': 'total_revenue', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'flight_id', 'AttributeType': 'S'},
                {'AttributeName': 'total_revenue', 'AttributeType': 'N'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Calculate revenue impact for cost-benefit analysis (Finance Agent)',
            'EstimatedImpact': '10-20x performance improvement, 40+ queries/day',
            'RequiredBy': 'Finance Agent',
            'UseCase': 'Revenue impact analysis for disruption decisions'
        }
    ],
    'CrewMembers': [
        {
            'IndexName': 'crew-qualification-index',
            'KeySchema': [
                {'AttributeName': 'aircraft_type_id', 'KeyType': 'HASH'},
                {'AttributeName': 'qualification_expiry', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'aircraft_type_id', 'AttributeType': 'N'},
                {'AttributeName': 'qualification_expiry', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Find qualified crew replacements by aircraft type (Crew Compliance Agent)',
            'EstimatedImpact': '10-20x performance improvement, 30+ queries/day',
            'RequiredBy': 'Crew Compliance Agent',
            'UseCase': 'Crew replacement identification during disruptions'
        }
    ],
    'NOTAMs': [
        {
            'IndexName': 'notam-validity-index',
            'KeySchema': [
                {'AttributeName': 'airport_code', 'KeyType': 'HASH'},
                {'AttributeName': 'notam_start', 'KeyType': 'RANGE'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'airport_code', 'AttributeType': 'S'},
                {'AttributeName': 'notam_start', 'AttributeType': 'S'}
            ],
            'Projection': {'ProjectionType': 'ALL'},
            'Description': 'Query active NOTAMs for airport operational restrictions (Regulatory Agent)',
            'EstimatedImpact': '10-20x performance improvement, 60+ queries/day',
            'RequiredBy': 'Regulatory Agent',
            'UseCase': 'NOTAM compliance checking for flight operations'
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


async def create_gsi_async(table_name: str, gsi_config: Dict, wait: bool = True, validate: bool = False, retry_config: Optional[RetryConfig] = None) -> Tuple[bool, str]:
    """
    Create a Global Secondary Index on a DynamoDB table (async) with retry logic.

    Args:
        table_name: Name of the table
        gsi_config: GSI configuration dictionary
        wait: Whether to wait for GSI to become ACTIVE
        validate: Whether to validate GSI performance
        retry_config: Retry configuration (uses default if None)

    Returns:
        Tuple of (success: bool, message: str)
    """
    if retry_config is None:
        retry_config = DEFAULT_RETRY_CONFIG
    
    index_name = gsi_config['IndexName']
    description = gsi_config.get('Description', '')

    print(f"  Creating {index_name}...")
    if description:
        print(f"    Use case: {description}")

    retry_history = []
    
    for attempt in range(retry_config.max_attempts):
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
                    error_msg = "Failed to become ACTIVE"
                    retry_history.append({
                        'attempt': attempt + 1,
                        'timestamp': datetime.now().isoformat(),
                        'error': error_msg,
                        'error_type': 'ActivationTimeout'
                    })
                    
                    if attempt < retry_config.max_attempts - 1:
                        delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
                        log_retry_attempt(index_name, table_name, attempt + 1, retry_config.max_attempts, error_msg, len(retry_history), delay)
                        await asyncio.sleep(delay)
                        continue
                    else:
                        return (False, error_msg)
            else:
                print(f"    ℹ GSI created, not waiting for backfill")
                return (True, "Created, not waiting")

        except dynamodb_client.exceptions.ResourceInUseException as e:
            error_msg = f"Table {table_name} is being updated"
            error_type = 'ResourceInUseException'
            
            retry_history.append({
                'attempt': attempt + 1,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'error_type': error_type
            })
            
            if attempt < retry_config.max_attempts - 1:
                # Wait for table availability, retry immediately
                delay = 0
                print(f"  ⚠ {error_msg}, retrying immediately...")
                log_retry_attempt(index_name, table_name, attempt + 1, retry_config.max_attempts, error_msg, len(retry_history), delay)
                await asyncio.sleep(5)  # Small delay to let table become available
                continue
            else:
                print(f"  ✗ {error_msg} after {retry_config.max_attempts} attempts")
                return (False, error_msg)
                
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            # Check for specific error types in message
            if 'LimitExceededException' in error_msg:
                error_type = 'LimitExceededException'
                delay = 300  # 5 minutes
            elif 'ValidationException' in error_msg and 'attribute' in error_msg.lower():
                error_type = 'ValidationException'
                delay = 0  # Retry immediately after merge
            elif 'ThrottlingException' in error_msg:
                error_type = 'ThrottlingException'
                delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
            elif 'InternalServerError' in error_msg:
                error_type = 'InternalServerError'
                delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
            elif 'already exists' in error_msg.lower():
                print(f"  ℹ GSI {index_name} already exists")
                return (True, "Already exists")
            else:
                delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
            
            retry_history.append({
                'attempt': attempt + 1,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'error_type': error_type
            })
            
            if attempt < retry_config.max_attempts - 1:
                log_retry_attempt(index_name, table_name, attempt + 1, retry_config.max_attempts, error_msg, len(retry_history), delay)
                print(f"  ⚠ Error: {error_msg}")
                print(f"  ⏳ Retrying in {delay}s (attempt {attempt + 2}/{retry_config.max_attempts})...")
                await asyncio.sleep(delay)
                continue
            else:
                print(f"  ✗ Error creating GSI after {retry_config.max_attempts} attempts: {error_msg}")
                
                # Generate failure report
                failure_report = generate_failure_report(index_name, table_name, retry_history)
                print(f"  ℹ Failure report generated for {index_name}")
                
                return (False, error_msg)
    
    # Should not reach here, but just in case
    return (False, f"Failed after {retry_config.max_attempts} attempts")

async def process_table_gsis(table_name: str, gsis: List[Dict], wait: bool = True, validate: bool = False, retry_config: Optional[RetryConfig] = None) -> Tuple[int, int]:
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
    if retry_config is None:
        retry_config = DEFAULT_RETRY_CONFIG
    
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

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  ✗ Exception: {result}")
            failed_count += 1
            
            # Log that we're continuing with remaining GSIs
            if retry_config.continue_on_failure and i < len(gsis) - 1:
                print(f"  ℹ Continuing with remaining GSIs...")
        else:
            success, message = result
            if success:
                created_count += 1
            else:
                failed_count += 1
                
                # Log that we're continuing with remaining GSIs
                if retry_config.continue_on_failure and i < len(gsis) - 1:
                    print(f"  ℹ Continuing with remaining GSIs...")

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
    """Main entry point for Priority 3 GSI creation tool."""
    parser = argparse.ArgumentParser(
        description='Create Priority 3 (Future Enhancement) DynamoDB GSIs for multi-round orchestration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Priority 3 GSIs are nice-to-have for future optimization and advanced features.

Examples:
  # Create all Priority 3 GSIs
  python3 scripts/create_priority3_gsis.py

  # Create GSIs for specific table
  python3 scripts/create_priority3_gsis.py --table CargoShipments

  # Check GSI status
  python3 scripts/create_priority3_gsis.py --check-status

  # Rollback (delete) GSIs
  python3 scripts/create_priority3_gsis.py --rollback

  # Skip waiting for GSI activation
  python3 scripts/create_priority3_gsis.py --no-wait

  # Validate GSI performance
  python3 scripts/create_priority3_gsis.py --validate
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
        help='Delete the Priority 3 GSIs (rollback)'
    )

    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate GSI performance with sample queries'
    )

    parser.add_argument(
        '--max-attempts',
        type=int,
        default=5,
        help='Maximum number of retry attempts (default: 5)'
    )

    args = parser.parse_args()

    # Print header
    print("=" * 80)
    print("DynamoDB Priority 3 GSI Creation Tool - Multi-Round Orchestration")
    print("=" * 80)
    print()
    print("Priority 3 GSIs: Future Enhancement")
    print("Expected Impact: 10-20x performance improvement")
    print("Query Volume: 30-60+ queries/day per GSI")
    print()
    print("⚠ NOTE: These GSIs are optional and intended for future optimization.")
    print("         Create them only when the corresponding features are needed.")
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
        print("Checking Priority 3 GSI status...")
        print()

        for table_name in PRIORITY3_GSI_DEFINITIONS.keys():
            if args.table and table_name != args.table:
                continue

            print(f"{table_name}:")
            check_gsi_status(table_name)
            print()

        return 0

    # Rollback mode
    if args.rollback:
        print("⚠ ROLLBACK MODE: Deleting Priority 3 GSIs...")
        print()

        tables_to_process = PRIORITY3_GSI_DEFINITIONS
        if args.table:
            if args.table not in PRIORITY3_GSI_DEFINITIONS:
                print(f"Error: Table '{args.table}' not found in Priority 3 GSI definitions")
                return 1
            tables_to_process = {args.table: PRIORITY3_GSI_DEFINITIONS[args.table]}

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
    tables_to_process = PRIORITY3_GSI_DEFINITIONS
    if args.table:
        if args.table not in PRIORITY3_GSI_DEFINITIONS:
            print(f"Error: Table '{args.table}' not found in Priority 3 GSI definitions")
            print(f"Available tables: {', '.join(PRIORITY3_GSI_DEFINITIONS.keys())}")
            return 1
        tables_to_process = {args.table: PRIORITY3_GSI_DEFINITIONS[args.table]}

    # Count total GSIs
    total_gsis = sum(len(gsis) for gsis in tables_to_process.values())

    print(f"Creating {total_gsis} Priority 3 GSIs for {len(tables_to_process)} tables (async)...")
    print(f"Retry configuration: max {args.max_attempts} attempts with exponential backoff")
    print()

    start_time = datetime.now()

    # Run async GSI creation
    created_count, failed_count = asyncio.run(create_all_gsis_async(
        tables_to_process,
        wait=not args.no_wait,
        validate=args.validate,
        retry_config=RetryConfig(
            max_attempts=args.max_attempts,
            backoff_delays=(30, 60, 120, 240, 480),
            continue_on_failure=True
        )
    ))

    duration = datetime.now() - start_time

    # Print summary
    print("=" * 80)
    print("Priority 3 GSI Creation Summary")
    print("=" * 80)
    print(f"Total Tables: {len(tables_to_process)}")
    print(f"Total GSIs: {total_gsis}")
    print(f"Created/Verified: {created_count}")
    print(f"Failed: {failed_count}")
    print(f"Duration: {duration}")
    print()

    if failed_count == 0:
        print("✓ All Priority 3 GSIs created successfully!")
        print()
        print("Expected Performance Improvements:")
        print("  • Cargo Agent: 10-20x faster high-value cargo prioritization")
        print("  • Finance Agent: 10-20x faster revenue impact analysis")
        print("  • Crew Compliance Agent: 10-20x faster crew replacement queries")
        print("  • Regulatory Agent: 10-20x faster NOTAM compliance checks")
        print()
        print("Next steps:")
        print("  1. Validate GSI performance: python3 scripts/create_priority3_gsis.py --validate")
        print("  2. Check GSI status: python3 scripts/create_priority3_gsis.py --check-status")
        print("  3. Update agent code to use new GSIs when implementing features")
        print("  4. Run validation script: python3 scripts/validate_dynamodb_data.py")
    else:
        print(f"⚠ GSI creation completed with {failed_count} failures")

    print()
    print("View tables in AWS Console:")
    print(f"  https://console.aws.amazon.com/dynamodbv2/home?region={region}#tables")
    print()
    print("=" * 80)

    return 0 if failed_count == 0 else 1


async def create_all_gsis_async(tables_to_process: Dict[str, List[Dict]], wait: bool = True, validate: bool = False, retry_config: Optional[RetryConfig] = None) -> Tuple[int, int]:
    """
    Create all GSIs across all tables concurrently.

    Args:
        tables_to_process: Dictionary of table names to GSI configurations
        wait: Whether to wait for GSIs to become ACTIVE
        validate: Whether to validate GSI performance

    Returns:
        Tuple of (total_created_count, total_failed_count)
    """
    if retry_config is None:
        retry_config = DEFAULT_RETRY_CONFIG
    
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
