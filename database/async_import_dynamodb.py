"""
Async DynamoDB cleanup and import script.
Cleans up existing tables and imports CSV files concurrently.
"""
import asyncio
import csv
import os
from decimal import Decimal
from typing import Dict, List, Tuple, Any

import aioboto3
import pandas as pd
from botocore.exceptions import ClientError

# Configuration
REGION = 'us-east-1'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')

# Table definitions from cleanup_and_upload_dynamodb.py
TABLE_CONFIGS = {
    'flights': {
        'file': 'flights_enriched_mel.csv',
        'key_schema': [{'AttributeName': 'flight_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'flight_id', 'AttributeType': 'N'}],
        'key_field': 'flight_id'
    },
    'bookings': {
        'file': 'bookings.csv',
        'key_schema': [{'AttributeName': 'booking_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'booking_id', 'AttributeType': 'N'}],
        'key_field': 'booking_id'
    },
    'CrewMembers': {
        'file': 'crew_members_enriched.csv',
        'key_schema': [{'AttributeName': 'crew_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'crew_id', 'AttributeType': 'N'}],
        'key_field': 'crew_id'
    },
    'CrewRoster': {
        'file': 'crew_roster_enriched.csv',
        'key_schema': [{'AttributeName': 'roster_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'roster_id', 'AttributeType': 'N'}],
        'key_field': 'roster_id'
    },
    'AircraftAvailability': {
        'file': 'aircraft_availability_enriched_mel.csv',
        'key_schema': [
            {'AttributeName': 'aircraftRegistration', 'KeyType': 'HASH'},
            {'AttributeName': 'valid_from_zulu', 'KeyType': 'RANGE'}
        ],
        'attribute_definitions': [
            {'AttributeName': 'aircraftRegistration', 'AttributeType': 'S'},
            {'AttributeName': 'valid_from_zulu', 'AttributeType': 'S'}
        ],
        'key_field': 'aircraftRegistration'
    },
    'disruption_events': {
        'file': 'disruption_events.csv',
        'key_schema': [{'AttributeName': 'disruption_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'disruption_id', 'AttributeType': 'S'}],
        'key_field': 'disruption_id'
    },
    'recovery_scenarios': {
        'file': 'recovery_scenarios.csv',
        'key_schema': [{'AttributeName': 'scenario_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'scenario_id', 'AttributeType': 'S'}],
        'key_field': 'scenario_id'
    },
    'recovery_actions': {
        'file': 'recovery_actions.csv',
        'key_schema': [{'AttributeName': 'action_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'action_id', 'AttributeType': 'S'}],
        'key_field': 'action_id'
    },
    'Weather': {
        'file': 'weather.csv',
        'key_schema': [{'AttributeName': 'airport_code', 'KeyType': 'HASH'}, {'AttributeName': 'forecast_time_zulu', 'KeyType': 'RANGE'}],
        'attribute_definitions': [
            {'AttributeName': 'airport_code', 'AttributeType': 'S'},
            {'AttributeName': 'forecast_time_zulu', 'AttributeType': 'S'}
        ],
        'key_field': 'airport_code'
    },
    'Baggage': {
        'file': 'baggage.csv',
        'key_schema': [{'AttributeName': 'baggage_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'baggage_id', 'AttributeType': 'N'}],
        'key_field': 'baggage_id'
    },
    'CargoShipments': {
        'file': 'cargo_shipments.csv',
        'key_schema': [{'AttributeName': 'shipment_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'shipment_id', 'AttributeType': 'N'}],
        'key_field': 'shipment_id'
    },
    'CargoFlightAssignments': {
        'file': 'cargo_flight_assignments.csv',
        'key_schema': [{'AttributeName': 'assignment_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'assignment_id', 'AttributeType': 'N'}],
        'key_field': 'assignment_id'
    },
    'MaintenanceStaff': {
        'file': 'maintenance_staff.csv',
        'key_schema': [{'AttributeName': 'staff_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'staff_id', 'AttributeType': 'S'}],
        'key_field': 'staff_id'
    },
    'MaintenanceWorkOrders': {
        'file': 'aircraft_maintenance_workorders.csv',
        'key_schema': [{'AttributeName': 'workorder_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'workorder_id', 'AttributeType': 'S'}],
        'key_field': 'workorder_id'
    },
    'business_impact_assessment': {
        'file': 'business_impact_assessment.csv',
        'key_schema': [{'AttributeName': 'assessment_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'assessment_id', 'AttributeType': 'S'}],
        'key_field': 'assessment_id'
    },
    'safety_constraints': {
        'file': 'safety_constraints.csv',
        'key_schema': [{'AttributeName': 'constraint_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'constraint_id', 'AttributeType': 'S'}],
        'key_field': 'constraint_id'
    },
}


def convert_value(value: Any) -> Any:
    """Convert Python values to DynamoDB compatible types."""
    if pd.isna(value) or value == '' or value is None:
        return None
    if isinstance(value, float):
        if value != value:  # NaN check
            return None
        return Decimal(str(value))
    if isinstance(value, int):
        return value
    return str(value)


def load_csv_data(csv_path: str) -> List[Dict[str, Any]]:
    """Load CSV data into list of dictionaries."""
    if 'passengers' in csv_path:
        # Use csv reader for large files
        items = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(row)
        return items
    else:
        df = pd.read_csv(csv_path)
        return df.to_dict('records')


async def list_all_tables(session) -> List[str]:
    """List all DynamoDB tables."""
    async with session.client('dynamodb', region_name=REGION) as client:
        response = await client.list_tables()
        return response.get('TableNames', [])


async def delete_table(session, table_name: str) -> bool:
    """Delete a single table and wait for deletion."""
    async with session.client('dynamodb', region_name=REGION) as client:
        try:
            print(f"  Deleting {table_name}...", end=" ", flush=True)
            await client.delete_table(TableName=table_name)
            
            # Wait for deletion
            waiter = client.get_waiter('table_not_exists')
            await waiter.wait(
                TableName=table_name,
                WaiterConfig={'Delay': 3, 'MaxAttempts': 30}
            )
            print("✓")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print("(not found)")
                return False
            print(f"✗ {e.response['Error']['Message']}")
            return False


async def cleanup_tables(session) -> int:
    """Delete all existing DynamoDB tables concurrently."""
    print("\n" + "=" * 60)
    print("STEP 1: CLEANING UP EXISTING TABLES")
    print("=" * 60)
    
    tables = await list_all_tables(session)
    
    if not tables:
        print("No tables found to delete.")
        return 0
    
    print(f"Found {len(tables)} tables to delete:")
    
    # Delete all tables concurrently
    tasks = [delete_table(session, table_name) for table_name in tables]
    results = await asyncio.gather(*tasks)
    
    deleted_count = sum(1 for r in results if r)
    print(f"\n✓ Deleted {deleted_count} tables")
    return deleted_count


async def create_table(session, table_name: str, config: Dict) -> bool:
    """Create a single DynamoDB table."""
    async with session.client('dynamodb', region_name=REGION) as client:
        try:
            await client.create_table(
                TableName=table_name,
                KeySchema=config['key_schema'],
                AttributeDefinitions=config['attribute_definitions'],
                BillingMode='PAY_PER_REQUEST'
            )
            
            # Wait for table to be active
            waiter = client.get_waiter('table_exists')
            await waiter.wait(
                TableName=table_name,
                WaiterConfig={'Delay': 2, 'MaxAttempts': 30}
            )
            return True
        except ClientError as e:
            print(f"  ✗ Error creating {table_name}: {e.response['Error']['Message']}")
            return False


async def upload_batch(table, items: List[Dict], start_idx: int, batch_size: int = 25):
    """Upload a batch of items to DynamoDB."""
    batch = items[start_idx:start_idx + batch_size]
    
    async with table.batch_writer() as writer:
        for item in batch:
            await writer.put_item(Item=item)
    
    return len(batch)


async def upload_data_to_table(session, table_name: str, csv_path: str, key_field: str) -> Tuple[int, int]:
    """Upload CSV data to a DynamoDB table with concurrent batches."""
    # Load data
    raw_items = load_csv_data(csv_path)
    
    # Convert and clean items
    clean_items = []
    for item in raw_items:
        clean_item = {}
        for k, v in item.items():
            converted = convert_value(v)
            if converted is not None:
                clean_item[k] = converted
        
        # Ensure key field exists
        if key_field in clean_item:
            clean_items.append(clean_item)
    
    if not clean_items:
        return 0, len(raw_items)
    
    # Upload in concurrent batches
    async with session.resource('dynamodb', region_name=REGION) as dynamodb:
        table = await dynamodb.Table(table_name)
        
        batch_size = 25  # DynamoDB batch write limit
        tasks = []
        
        for i in range(0, len(clean_items), batch_size):
            task = upload_batch(table, clean_items, i, batch_size)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(r for r in results if isinstance(r, int))
        error_count = len(raw_items) - success_count
        
        return success_count, error_count


async def process_table(session, table_name: str, config: Dict) -> Dict[str, Any]:
    """Process a single table: create and upload data."""
    csv_path = os.path.join(OUTPUT_DIR, config['file'])
    
    result = {
        'table': table_name,
        'created': False,
        'uploaded': 0,
        'errors': 0,
        'error_msg': None
    }
    
    # Check if CSV exists
    if not os.path.exists(csv_path):
        result['error_msg'] = f"CSV not found: {config['file']}"
        print(f"✗ {table_name}: {result['error_msg']}")
        return result
    
    print(f"Processing {table_name}...", end=" ", flush=True)
    
    # Create table
    created = await create_table(session, table_name, config)
    result['created'] = created
    
    if not created:
        result['error_msg'] = "Failed to create table"
        print(f"✗ {table_name}: {result['error_msg']}")
        return result
    
    # Upload data
    try:
        success, errors = await upload_data_to_table(
            session, table_name, csv_path, config['key_field']
        )
        result['uploaded'] = success
        result['errors'] = errors
        print(f"✓ ({success} items)")
    except Exception as e:
        result['error_msg'] = str(e)
        print(f"✗ Upload error: {e}")
    
    return result


async def create_and_upload_tables(session) -> List[Dict[str, Any]]:
    """Create all tables and upload data concurrently."""
    print("\n" + "=" * 60)
    print("STEP 2: CREATING TABLES AND UPLOADING DATA")
    print("=" * 60)
    
    # Process all tables concurrently
    tasks = [
        process_table(session, table_name, config)
        for table_name, config in TABLE_CONFIGS.items()
    ]
    
    results = await asyncio.gather(*tasks)
    return results


async def verify_tables(session) -> Dict[str, int]:
    """Verify all tables and count items."""
    print("\n" + "=" * 60)
    print("STEP 3: VERIFICATION")
    print("=" * 60)
    
    tables = await list_all_tables(session)
    print(f"\nTables in DynamoDB: {len(tables)}")
    
    counts = {}
    async with session.resource('dynamodb', region_name=REGION) as dynamodb:
        for table_name in sorted(tables):
            try:
                table = await dynamodb.Table(table_name)
                response = await table.scan(Select='COUNT')
                count = response['Count']
                counts[table_name] = count
                print(f"  ✓ {table_name}: {count} items")
            except Exception as e:
                print(f"  ✗ {table_name}: Error - {e}")
                counts[table_name] = -1
    
    return counts


async def main():
    """Main execution function."""
    print("=" * 60)
    print("ASYNC DYNAMODB CLEANUP AND IMPORT")
    print("=" * 60)
    
    session = aioboto3.Session()
    
    # Step 1: Cleanup existing tables
    deleted_count = await cleanup_tables(session)
    
    # Wait a bit for cleanup to complete
    await asyncio.sleep(2)
    
    # Step 2: Create tables and upload data
    results = await create_and_upload_tables(session)
    
    # Step 3: Verify
    counts = await verify_tables(session)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Tables deleted: {deleted_count}")
    print(f"Tables created: {sum(1 for r in results if r['created'])}")
    
    total_uploaded = sum(r['uploaded'] for r in results)
    total_errors = sum(r['errors'] for r in results)
    print(f"Total items uploaded: {total_uploaded}")
    print(f"Total errors: {total_errors}")
    
    # Show any failures
    failures = [r for r in results if r['error_msg']]
    if failures:
        print(f"\nFailures ({len(failures)}):")
        for f in failures:
            print(f"  ✗ {f['table']}: {f['error_msg']}")
    
    print("\n✅ COMPLETE!")


if __name__ == '__main__':
    asyncio.run(main())
