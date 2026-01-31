#!/usr/bin/env python3
"""
Upload Missing Tables to DynamoDB - Fixed Version

This script properly handles data type conversion and error logging.
"""

import os
import sys
import csv
import boto3
import pandas as pd
from decimal import Decimal
from botocore.exceptions import ClientError

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
client = boto3.client('dynamodb', region_name=AWS_REGION)

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')

# Table configurations with CORRECT data types
NEW_TABLES = {
    'passengers': {
        'file': os.path.join(OUTPUT_DIR, 'passengers_enriched_final.csv'),
        'key_schema': [{'AttributeName': 'passenger_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'passenger_id', 'AttributeType': 'S'}]
    },
    'financial_parameters': {
        'file': os.path.join(OUTPUT_DIR, 'financial_parameters.csv'),
        'key_schema': [{'AttributeName': 'parameter_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'parameter_id', 'AttributeType': 'S'}]  # STRING
    },
    'financial_transactions': {
        'file': os.path.join(OUTPUT_DIR, 'financial_transactions.csv'),
        'key_schema': [{'AttributeName': 'transaction_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'transaction_id', 'AttributeType': 'S'}]  # STRING
    },
    'disruption_costs': {
        'file': os.path.join(OUTPUT_DIR, 'disruption_costs.csv'),
        'key_schema': [{'AttributeName': 'cost_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'cost_id', 'AttributeType': 'S'}]  # STRING
    },
    'disrupted_passengers_scenario': {
        'file': os.path.join(OUTPUT_DIR, 'disrupted_passengers_scenario.csv'),
        'key_schema': [{'AttributeName': 'passenger_id', 'KeyType': 'HASH'}],
        'attribute_definitions': [{'AttributeName': 'passenger_id', 'AttributeType': 'S'}]
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


def convert_value(value):
    """Convert Python values to DynamoDB compatible types"""
    if pd.isna(value) or value == '' or value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return Decimal(str(value))
    return str(value)


def delete_table_if_exists(table_name):
    """Delete a table if it exists"""
    try:
        client.delete_table(TableName=table_name)
        print(f"   Deleting existing table '{table_name}'...", end=" ")
        waiter = client.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
        print("✅")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        else:
            print(f"   ❌ Error: {e}")
            return False


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
        print(f"   ❌ Error: {e}")
        return False


def upload_csv_to_table(table_name, csv_file, key_field):
    """Upload CSV data to DynamoDB table using pandas"""
    table = dynamodb.Table(table_name)
    
    if not os.path.exists(csv_file):
        print(f"   ❌ CSV file not found: {csv_file}")
        return 0, 0
    
    # Read CSV with pandas
    print(f"   Reading CSV file...", end=" ")
    df = pd.read_csv(csv_file)
    print(f"✅ ({len(df)} rows)")
    
    # Check if key field exists
    if key_field not in df.columns:
        print(f"   ❌ Key field '{key_field}' not found in CSV columns: {list(df.columns)[:10]}")
        return 0, len(df)
    
    print(f"   Uploading to '{table_name}'...")
    
    # Batch write
    success_count = 0
    error_count = 0
    batch_size = 25
    
    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i:i+batch_size]
        
        try:
            with table.batch_writer() as batch:
                for idx, row in batch_df.iterrows():
                    try:
                        # Convert row to dict and clean values
                        item = {}
                        for col in df.columns:
                            value = row[col]
                            converted = convert_value(value)
                            if converted is not None:
                                item[col] = converted
                        
                        # Ensure key field exists
                        if key_field not in item:
                            error_count += 1
                            continue
                        
                        batch.put_item(Item=item)
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        if error_count <= 3:  # Only print first 3 errors
                            print(f"      ⚠️  Row {idx} error: {e}")
            
            # Progress indicator
            if (i // batch_size + 1) % 20 == 0:
                print(f"      Progress: {success_count}/{len(df)} items uploaded")
                
        except Exception as e:
            print(f"      ❌ Batch error: {e}")
            error_count += len(batch_df)
    
    print(f"   ✅ Upload complete: {success_count} items, {error_count} errors")
    return success_count, error_count


def recreate_and_upload_tables():
    """Delete, recreate, and upload data for all tables"""
    print("\n" + "=" * 80)
    print("RECREATING AND UPLOADING MISSING TABLES")
    print("=" * 80)
    
    results = {}
    
    for table_name, config in NEW_TABLES.items():
        print(f"\n{table_name}:")
        
        # Delete if exists
        delete_table_if_exists(table_name)
        
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


def verify_tables():
    """Verify all tables have data"""
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    for table_name in NEW_TABLES.keys():
        try:
            table = dynamodb.Table(table_name)
            response = table.scan(Select='COUNT', Limit=10)
            count = response.get('Count', 0)
            
            # Get more accurate count
            desc_response = client.describe_table(TableName=table_name)
            item_count = desc_response['Table'].get('ItemCount', count)
            
            status = "✅" if item_count > 0 else "⚠️"
            print(f"   {status} {table_name:35} {item_count:>8} items")
            
        except Exception as e:
            print(f"   ❌ {table_name:35} Error: {e}")


def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("UPLOAD MISSING TABLES TO DYNAMODB - FIXED VERSION")
    print("=" * 80)
    
    # Recreate and upload
    results = recreate_and_upload_tables()
    
    # Verify
    verify_tables()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_success = 0
    total_errors = 0
    
    for table_name, result in results.items():
        success = result['success']
        errors = result['errors']
        total_success += success
        total_errors += errors if errors > 0 else 0
        
        status = "✅" if success > 0 else "❌"
        print(f"{status} {table_name:35} {success:>8} items uploaded, {errors:>6} errors")
    
    print(f"\n📊 Total Statistics:")
    print(f"   Items uploaded: {total_success:,}")
    print(f"   Errors: {total_errors:,}")
    
    if total_success > 0:
        success_rate = (total_success / (total_success + total_errors) * 100) if (total_success + total_errors) > 0 else 0
        print(f"   Success rate: {success_rate:.1f}%")
    
    if total_errors == 0 and total_success > 0:
        print("\n✅ ALL TABLES UPLOADED SUCCESSFULLY!")
    elif total_success > 0:
        print("\n⚠️  UPLOAD COMPLETED WITH SOME ERRORS")
    else:
        print("\n❌ UPLOAD FAILED")
        sys.exit(1)


if __name__ == '__main__':
    main()
