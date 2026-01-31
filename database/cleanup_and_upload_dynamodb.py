"""
Complete DynamoDB cleanup and fresh upload script.
1. Delete ALL existing tables
2. Create fresh tables with correct schema
3. Upload verified data
4. Clean up unused CSV files
"""
import boto3
import pandas as pd
import csv
import time
import os
from decimal import Decimal
from botocore.exceptions import ClientError

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
client = boto3.client('dynamodb', region_name='us-east-1')

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')

# Tables to create and upload - MATCHING EXISTING DynamoDB table names
TABLES_TO_CREATE = {
    'flights': {
        'file': os.path.join(OUTPUT_DIR, 'flights_enriched_mel.csv'),
        'key_schema': [{'AttributeName': 'flight_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'flight_id', 'AttributeType': 'N'}]
    },
    'bookings': {
        'file': os.path.join(OUTPUT_DIR, 'bookings.csv'),
        'key_schema': [{'AttributeName': 'booking_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'booking_id', 'AttributeType': 'N'}]
    },
    'CrewMembers': {
        'file': os.path.join(OUTPUT_DIR, 'crew_members_enriched.csv'),
        'key_schema': [{'AttributeName': 'crew_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'crew_id', 'AttributeType': 'N'}]
    },
    'CrewRoster': {
        'file': os.path.join(OUTPUT_DIR, 'crew_roster_enriched.csv'),
        'key_schema': [{'AttributeName': 'roster_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'roster_id', 'AttributeType': 'N'}]
    },
    'AircraftAvailability': {
        'file': os.path.join(OUTPUT_DIR, 'aircraft_availability_enriched_mel.csv'),
        'key_schema': [{'AttributeName': 'aircraftRegistration', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'aircraftRegistration', 'AttributeType': 'S'}]
    },
    'disruption_events': {
        'file': os.path.join(OUTPUT_DIR, 'disruption_events.csv'),
        'key_schema': [{'AttributeName': 'disruption_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'disruption_id', 'AttributeType': 'S'}]
    },
    'recovery_scenarios': {
        'file': os.path.join(OUTPUT_DIR, 'recovery_scenarios.csv'),
        'key_schema': [{'AttributeName': 'scenario_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'scenario_id', 'AttributeType': 'S'}]
    },
    'recovery_actions': {
        'file': os.path.join(OUTPUT_DIR, 'recovery_actions.csv'),
        'key_schema': [{'AttributeName': 'action_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'action_id', 'AttributeType': 'S'}]
    },
    'Weather': {
        'file': os.path.join(OUTPUT_DIR, 'weather.csv'),
        'key_schema': [{'AttributeName': 'weather_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'weather_id', 'AttributeType': 'N'}]
    },
    'Baggage': {
        'file': os.path.join(OUTPUT_DIR, 'baggage.csv'),
        'key_schema': [{'AttributeName': 'baggage_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'baggage_id', 'AttributeType': 'N'}]
    },
    'CargoShipments': {
        'file': os.path.join(OUTPUT_DIR, 'cargo_shipments.csv'),
        'key_schema': [{'AttributeName': 'shipment_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'shipment_id', 'AttributeType': 'N'}]
    },
    'CargoFlightAssignments': {
        'file': os.path.join(OUTPUT_DIR, 'cargo_flight_assignments.csv'),
        'key_schema': [{'AttributeName': 'assignment_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'assignment_id', 'AttributeType': 'N'}]
    },
    'MaintenanceStaff': {
        'file': os.path.join(OUTPUT_DIR, 'maintenance_staff.csv'),
        'key_schema': [{'AttributeName': 'roster_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'roster_id', 'AttributeType': 'N'}]
    },
    'MaintenanceWorkOrders': {
                'file': os.path.join(OUTPUT_DIR, 'aircraft_maintenance_workorders.csv'),

        'key_schema': [{'AttributeName': 'workorder_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'workorder_id', 'AttributeType': 'S'}]
    },
    'business_impact_assessment': {
                        'file': os.path.join(OUTPUT_DIR, 'business_impact_assessment.csv'),

        'key_schema': [{'AttributeName': 'assessment_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'assessment_id', 'AttributeType': 'S'}]
    },
    'safety_constraints': {
                                'file': os.path.join(OUTPUT_DIR, 'safety_constraints.csv'),

        'key_schema': [{'AttributeName': 'constraint_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'constraint_id', 'AttributeType': 'S'}]
    },
    'passengers': {
        'file': os.path.join(OUTPUT_DIR, 'passengers_enriched_final.csv'),
        'key_schema': [{'AttributeName': 'passenger_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'passenger_id', 'AttributeType': 'N'}]
    },
    'financial_parameters': {
        'file': os.path.join(OUTPUT_DIR, 'financial_parameters.csv'),
        'key_schema': [{'AttributeName': 'parameter_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'parameter_id', 'AttributeType': 'N'}]
    },
    'financial_transactions': {
        'file': os.path.join(OUTPUT_DIR, 'financial_transactions.csv'),
        'key_schema': [{'AttributeName': 'transaction_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'transaction_id', 'AttributeType': 'N'}]
    },
    'disruption_costs': {
        'file': os.path.join(OUTPUT_DIR, 'disruption_costs.csv'),
        'key_schema': [{'AttributeName': 'cost_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'cost_id', 'AttributeType': 'N'}]
    },
    'disrupted_passengers_scenario': {
        'file': os.path.join(OUTPUT_DIR, 'disrupted_passengers_scenario.csv'),
        'key_schema': [{'AttributeName': 'passenger_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'passenger_id', 'AttributeType': 'N'}]
    },
    'aircraft_swap_options': {
        'file': os.path.join(OUTPUT_DIR, 'aircraft_swap_options.csv'),
        'key_schema': [{'AttributeName': 'aircraft_registration', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'aircraft_registration', 'AttributeType': 'S'}]
    },
    'inbound_flight_impact': {
        'file': os.path.join(OUTPUT_DIR, 'inbound_flight_impact.csv'),
        'key_schema': [{'AttributeName': 'scenario', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'scenario', 'AttributeType': 'S'}]
    },
}

# CSV files to KEEP (used by tables above + essential)
FILES_TO_KEEP = {
    'output/flights_enriched_mel.csv',
    'output/passengers_enriched_final.csv',
    'output/bookings.csv',
    'output/crew_members_enriched.csv',
    'output/crew_roster_enriched.csv',
    'output/aircraft_availability_enriched_mel.csv',
    'output/disruption_events.csv',
    'output/recovery_scenarios.csv',
    'output/recovery_actions.csv',
    'output/weather.csv',
    'output/baggage.csv',
    'output/cargo_shipments.csv',
    # Additional files synced with past disruption data
    'output/financial_parameters.csv',
    'output/financial_transactions.csv',
    'output/disruption_costs.csv',
    'output/operational_kpis.csv',
    'output/revenue_management.csv',
    'output/fuel_management.csv',
    'output/safety_constraints.csv',
}

def delete_all_tables():
    """Delete all existing DynamoDB tables"""
    print("\n" + "=" * 60)
    print("STEP 1: DELETING ALL EXISTING DYNAMODB TABLES")
    print("=" * 60)
    
    try:
        response = client.list_tables()
        tables = response.get('TableNames', [])
        
        if not tables:
            print("No tables found to delete.")
            return
        
        print(f"Found {len(tables)} tables to delete:")
        for table in tables:
            print(f"  - {table}")
        
        for table_name in tables:
            try:
                print(f"\nDeleting {table_name}...", end=" ")
                client.delete_table(TableName=table_name)
                print("✓ Delete initiated")
            except ClientError as e:
                print(f"✗ Error: {e.response['Error']['Message']}")
        
        # Wait for all tables to be deleted
        print("\nWaiting for tables to be deleted...")
        for table_name in tables:
            try:
                waiter = client.get_waiter('table_not_exists')
                waiter.wait(TableName=table_name, WaiterConfig={'Delay': 5, 'MaxAttempts': 30})
                print(f"  ✓ {table_name} deleted")
            except Exception as e:
                print(f"  ✗ {table_name}: {e}")
        
        print("\nAll tables deleted successfully!")
        
    except ClientError as e:
        print(f"Error listing tables: {e.response['Error']['Message']}")

def delete_table_if_exists(table_name):
    """Delete a table if it exists and wait for deletion"""
    try:
        client.delete_table(TableName=table_name)
        waiter = client.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name, WaiterConfig={'Delay': 3, 'MaxAttempts': 20})
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise

def create_table(table_name, config):
    """Create a single DynamoDB table (delete first if exists)"""
    # First try to delete if exists
    delete_table_if_exists(table_name)
    time.sleep(2)
    
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=config['key_schema'],
            AttributeDefinitions=config['attribute_definitions'],
            BillingMode='PAY_PER_REQUEST'
        )
        return table
    except ClientError as e:
        raise

def convert_value(value):
    """Convert Python values to DynamoDB compatible types"""
    if pd.isna(value) or value == '' or value is None:
        return None
    if isinstance(value, float):
        if value != value:  # NaN check
            return None
        return Decimal(str(value))
    if isinstance(value, int):
        return value
    return str(value)

def upload_csv_to_table(table_name, csv_file, key_field):
    """Upload CSV data to DynamoDB table"""
    table = dynamodb.Table(table_name)
    
    # Read CSV
    if 'passengers' in csv_file:
        # Use csv reader for large files
        items = []
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                items.append(row)
    else:
        df = pd.read_csv(csv_file)
        items = df.to_dict('records')
    
    print(f"  Uploading {len(items)} items...", end=" ")
    
    # Batch write
    success_count = 0
    error_count = 0
    
    with table.batch_writer() as batch:
        for item in items:
            try:
                # Convert all values
                clean_item = {}
                for k, v in item.items():
                    converted = convert_value(v)
                    if converted is not None:
                        clean_item[k] = converted
                
                # Ensure key field exists
                if key_field not in clean_item:
                    error_count += 1
                    continue
                
                batch.put_item(Item=clean_item)
                success_count += 1
            except Exception as e:
                error_count += 1
    
    print(f"✓ {success_count} uploaded, {error_count} errors")
    return success_count, error_count

def create_and_upload_tables():
    """Create all tables and upload data"""
    print("\n" + "=" * 60)
    print("STEP 1: CREATING TABLES AND UPLOADING DATA")
    print("=" * 60)
    
    results = {}
    
    for table_name, config in TABLES_TO_CREATE.items():
        csv_file = config['file']
        
        if not os.path.exists(csv_file):
            print(f"\n{table_name}: ✗ File not found: {csv_file}")
            continue
        
        print(f"\n{table_name}:")
        
        # Create table
        print(f"  Creating table...", end=" ")
        try:
            table = create_table(table_name, config)
            table.wait_until_exists()
            print("✓")
        except Exception as e:
            print(f"✗ Error: {e}")
            continue
        
        # Get key field name
        key_field = config['key_schema'][0]['AttributeName']
        
        # Upload data
        try:
            success, errors = upload_csv_to_table(table_name, csv_file, key_field)
            results[table_name] = {'success': success, 'errors': errors}
        except Exception as e:
            print(f"  ✗ Upload error: {e}")
            results[table_name] = {'success': 0, 'errors': -1}
    
    return results

def cleanup_unused_csv_files():
    """Delete unused CSV files from output folder"""
    print("\n" + "=" * 60)
    print("STEP 2: CLEANING UP UNUSED CSV FILES")
    print("=" * 60)
    
    output_dir = 'output'
    deleted = []
    kept = []
    
    for filename in os.listdir(output_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(output_dir, filename)
            if filepath in FILES_TO_KEEP:
                kept.append(filename)
            else:
                try:
                    os.remove(filepath)
                    deleted.append(filename)
                except Exception as e:
                    print(f"  Error deleting {filename}: {e}")
    
    print(f"\nKept {len(kept)} files:")
    for f in sorted(kept):
        print(f"  ✓ {f}")
    
    print(f"\nDeleted {len(deleted)} unused files:")
    for f in sorted(deleted):
        print(f"  ✗ {f}")
    
    return deleted, kept

def verify_tables():
    """Verify all tables were created and have data"""
    print("\n" + "=" * 60)
    print("STEP 3: VERIFICATION")
    print("=" * 60)
    
    response = client.list_tables()
    tables = response.get('TableNames', [])
    
    print(f"\nTables in DynamoDB: {len(tables)}")
    for table_name in sorted(tables):
        try:
            table = dynamodb.Table(table_name)
            count = table.scan(Select='COUNT')['Count']
            print(f"  ✓ {table_name}: {count} items")
        except Exception as e:
            print(f"  ✗ {table_name}: Error - {e}")

def delete_old_tables(tables_to_keep):
    """Delete tables that are NOT in the keep list"""
    print("\n" + "=" * 60)
    print("STEP 4: DELETING OLD/UNUSED DYNAMODB TABLES")
    print("=" * 60)
    
    try:
        response = client.list_tables()
        all_tables = response.get('TableNames', [])
        
        # Find tables to delete (not in our new tables list)
        tables_to_delete = [t for t in all_tables if t not in tables_to_keep]
        
        if not tables_to_delete:
            print("No old tables to delete.")
            return
        
        print(f"Found {len(tables_to_delete)} old tables to delete:")
        for table in tables_to_delete:
            print(f"  - {table}")
        
        for table_name in tables_to_delete:
            try:
                print(f"\nDeleting {table_name}...", end=" ")
                client.delete_table(TableName=table_name)
                print("✓ Delete initiated")
            except ClientError as e:
                print(f"✗ Error: {e.response['Error']['Message']}")
        
        # Wait for tables to be deleted
        print("\nWaiting for old tables to be deleted...")
        for table_name in tables_to_delete:
            try:
                waiter = client.get_waiter('table_not_exists')
                waiter.wait(TableName=table_name, WaiterConfig={'Delay': 5, 'MaxAttempts': 30})
                print(f"  ✓ {table_name} deleted")
            except Exception as e:
                print(f"  ✗ {table_name}: {e}")
        
        print(f"\nDeleted {len(tables_to_delete)} old tables!")
        
    except ClientError as e:
        print(f"Error: {e.response['Error']['Message']}")

def main():
    print("=" * 60)
    print("DYNAMODB FRESH UPLOAD AND CLEANUP")
    print("=" * 60)
    
    # Step 1: Create tables and upload data (drop and recreate if exists)
    results = create_and_upload_tables()
    
    # Step 2: Cleanup unused CSV files
    deleted, kept = cleanup_unused_csv_files()
    
    # Step 3: Verify new tables
    verify_tables()
    
    # Step 4: Delete old/unused DynamoDB tables (at the end)
    new_table_names = list(TABLES_TO_CREATE.keys())
    delete_old_tables(new_table_names)
    
    # Final Summary
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Tables created/updated: {len(results)}")
    total_items = sum(r['success'] for r in results.values())
    print(f"Total items uploaded: {total_items}")
    print(f"CSV files kept: {len(kept)}")
    print(f"CSV files deleted: {len(deleted)}")
    print("\n✅ COMPLETE!")

if __name__ == '__main__':
    main()
