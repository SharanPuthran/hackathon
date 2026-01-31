#!/usr/bin/env python3
"""
Add Missing Critical Tables to DynamoDB and Clean Up Unused CSV Files

This script:
1. Adds 7 missing tables to DynamoDB
2. Uploads data from corresponding CSV files
3. Deletes unused CSV files (those without DynamoDB tables)
"""

import os
import sys
import csv
import boto3
import time
from decimal import Decimal
from botocore.exceptions import ClientError

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
client = boto3.client('dynamodb', region_name=AWS_REGION)

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')

# New tables to create
NEW_TABLES = {
    'passengers': {
        'file': os.path.join(OUTPUT_DIR, 'passengers_enriched_final.csv'),
        'key_schema': [{'AttributeName': 'passenger_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'passenger_id', 'AttributeType': 'S'}]  # STRING not number
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
        'attribute_definitions': [{'AttributeName': 'passenger_id', 'AttributeType': 'S'}]  # STRING not number
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

# CSV files to DELETE (no corresponding DynamoDB table needed)
CSV_FILES_TO_DELETE = [
    'airport_slots.csv',
    'crew_documents.csv',
    'crew_payroll.csv',
    'crew_training_records.csv',
    'operational_kpis.csv',
    'revenue_management.csv',
    'fuel_management.csv',
    # Duplicate/alternative files
    'bookings_enriched.csv',  # We use bookings.csv
    'crew_members.csv',  # We use crew_members_enriched.csv
    'crew_roster.csv',  # We use crew_roster_enriched.csv
    'flights_enriched_scenarios.csv',  # We use flights_enriched_mel.csv
    'maintenance_roster.csv',  # We use maintenance_staff.csv
]


def convert_value(value):
    """Convert Python values to DynamoDB compatible types"""
    if value is None or value == '' or (isinstance(value, str) and value.strip() == ''):
        return None
    if isinstance(value, float):
        if value != value:  # NaN check
            return None
        return Decimal(str(value))
    if isinstance(value, int):
        return value
    # Keep strings as strings - don't try to convert
    return str(value)


def create_table(table_name, config):
    """Create a DynamoDB table"""
    try:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=config['key_schema'],
            AttributeDefinitions=config['attribute_definitions'],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"   Creating table '{table_name}'...", end=" ")
        table.wait_until_exists()
        print("✅")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"   Table '{table_name}' already exists ✅")
            return True
        else:
            print(f"   ❌ Error: {e}")
            return False


def upload_csv_to_table(table_name, csv_file, key_field):
    """Upload CSV data to DynamoDB table"""
    table = dynamodb.Table(table_name)
    
    if not os.path.exists(csv_file):
        print(f"   ❌ CSV file not found: {csv_file}")
        return 0, 0
    
    # Read CSV
    items = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            items.append(row)
    
    print(f"   Uploading {len(items)} items to '{table_name}'...", end=" ")
    
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
    
    print(f"✅ ({success_count} items, {error_count} errors)")
    return success_count, error_count


def add_new_tables():
    """Create and populate new tables"""
    print("\n" + "=" * 80)
    print("STEP 1: ADDING MISSING TABLES TO DYNAMODB")
    print("=" * 80)
    
    results = {}
    
    for table_name, config in NEW_TABLES.items():
        print(f"\n{table_name}:")
        
        # Create table
        if not create_table(table_name, config):
            results[table_name] = {'success': 0, 'errors': -1}
            continue
        
        # Get key field name
        key_field = config['key_schema'][0]['AttributeName']
        
        # Upload data
        try:
            success, errors = upload_csv_to_table(table_name, config['file'], key_field)
            results[table_name] = {'success': success, 'errors': errors}
        except Exception as e:
            print(f"   ❌ Upload error: {e}")
            results[table_name] = {'success': 0, 'errors': -1}
    
    return results


def delete_unused_csv_files():
    """Delete CSV files that don't have corresponding DynamoDB tables"""
    print("\n" + "=" * 80)
    print("STEP 2: CLEANING UP UNUSED CSV FILES")
    print("=" * 80)
    
    deleted = []
    not_found = []
    
    for filename in CSV_FILES_TO_DELETE:
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                deleted.append(filename)
                print(f"   ✅ Deleted: {filename}")
            except Exception as e:
                print(f"   ❌ Error deleting {filename}: {e}")
        else:
            not_found.append(filename)
            print(f"   ⚠️  Not found: {filename}")
    
    return deleted, not_found


def verify_all_tables():
    """Verify all tables in DynamoDB"""
    print("\n" + "=" * 80)
    print("STEP 3: VERIFICATION")
    print("=" * 80)
    
    try:
        response = client.list_tables()
        tables = sorted(response.get('TableNames', []))
        
        print(f"\n📊 Total tables in DynamoDB: {len(tables)}")
        print("\nTable Status:")
        
        total_items = 0
        for table_name in tables:
            try:
                table = dynamodb.Table(table_name)
                # Use scan with limit to get actual count
                scan_response = table.scan(Select='COUNT', Limit=1000)
                count = scan_response.get('Count', 0)
                
                # For large tables, get approximate count from describe_table
                if count == 1000:
                    desc_response = client.describe_table(TableName=table_name)
                    count = desc_response['Table'].get('ItemCount', count)
                
                total_items += count
                print(f"   ✅ {table_name:35} {count:>8} items")
            except Exception as e:
                print(f"   ❌ {table_name:35} Error: {e}")
        
        print(f"\n📊 Total items across all tables: {total_items:,}")
        
    except Exception as e:
        print(f"❌ Error listing tables: {e}")


def update_upload_scripts():
    """Update cleanup_and_upload_dynamodb.py to include new tables"""
    print("\n" + "=" * 80)
    print("STEP 4: UPDATING UPLOAD SCRIPTS")
    print("=" * 80)
    
    upload_script = os.path.join(SCRIPT_DIR, 'cleanup_and_upload_dynamodb.py')
    
    if not os.path.exists(upload_script):
        print(f"   ⚠️  Upload script not found: {upload_script}")
        return
    
    # Read current script
    with open(upload_script, 'r') as f:
        content = f.read()
    
    # Check if passengers table is already in the script
    if "'passengers':" in content:
        print("   ✅ Upload script already includes new tables")
        return
    
    # Add new tables configuration
    new_tables_config = """
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
    },"""
    
    # Find the location to insert (before the closing brace of TABLES_TO_CREATE)
    insert_marker = "    'safety_constraints': {"
    if insert_marker in content:
        # Find the end of safety_constraints entry
        pos = content.find(insert_marker)
        # Find the closing brace for safety_constraints
        end_pos = content.find("},", pos) + 2
        
        # Insert new tables after safety_constraints
        new_content = content[:end_pos] + new_tables_config + content[end_pos:]
        
        # Write back
        with open(upload_script, 'w') as f:
            f.write(new_content)
        
        print(f"   ✅ Updated {upload_script}")
        print("   Added 7 new table configurations")
    else:
        print(f"   ⚠️  Could not find insertion point in {upload_script}")


def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("ADD MISSING TABLES AND CLEANUP UNUSED CSV FILES")
    print("=" * 80)
    
    # Step 1: Add new tables
    results = add_new_tables()
    
    # Step 2: Delete unused CSV files
    deleted, not_found = delete_unused_csv_files()
    
    # Step 3: Verify all tables
    verify_all_tables()
    
    # Step 4: Update upload scripts for future use
    update_upload_scripts()
    
    # Final Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)
    
    print(f"\n✅ New tables added: {len(results)}")
    for table_name, result in results.items():
        print(f"   • {table_name}: {result['success']} items uploaded, {result['errors']} errors")
    
    print(f"\n🗑️  CSV files deleted: {len(deleted)}")
    for filename in deleted:
        print(f"   • {filename}")
    
    if not_found:
        print(f"\n⚠️  CSV files not found (already deleted?): {len(not_found)}")
    
    total_items = sum(r['success'] for r in results.values())
    total_errors = sum(r['errors'] for r in results.values() if r['errors'] > 0)
    
    print(f"\n📊 Upload Statistics:")
    print(f"   Total items uploaded: {total_items:,}")
    print(f"   Total errors: {total_errors}")
    print(f"   Success rate: {(total_items / (total_items + total_errors) * 100):.1f}%")
    
    print("\n✅ COMPLETE!")
    print("\nNext steps:")
    print("1. Verify data in AWS Console")
    print("2. Test agent queries against new tables")
    print("3. Update validation scripts to include new tables")


if __name__ == '__main__':
    main()
