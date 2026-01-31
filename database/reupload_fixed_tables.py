#!/usr/bin/env python3
"""
Re-upload financial_transactions and disruption_costs with proper key conversion
"""

import os
import sys
import pandas as pd
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')

# Table configurations
TABLES_TO_FIX = {
    'financial_transactions': {
        'file': os.path.join(OUTPUT_DIR, 'financial_transactions.csv'),
        'key_field': 'transaction_id'
    },
    'disruption_costs': {
        'file': os.path.join(OUTPUT_DIR, 'disruption_costs.csv'),
        'key_field': 'cost_id'
    }
}


def convert_value(value, is_key_field=False):
    """
    Convert Python values to DynamoDB compatible types
    
    CRITICAL: Key fields must be strings, not Decimals!
    """
    # Handle null/empty values
    if pd.isna(value) or value == '' or value is None:
        return None
    
    # Key fields must be strings
    if is_key_field:
        return str(value)
    
    # Convert numbers to Decimal for DynamoDB
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return Decimal(str(value))
    
    # Everything else as string
    return str(value)


def clear_table(table_name):
    """Delete all items from a table"""
    table = dynamodb.Table(table_name)
    
    print(f"   Clearing existing data from '{table_name}'...", end=" ")
    
    try:
        # Scan to get all items
        response = table.scan()
        items = response.get('Items', [])
        
        # Get key schema
        key_schema = table.key_schema
        key_name = key_schema[0]['AttributeName']
        
        # Delete in batches
        deleted = 0
        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={key_name: item[key_name]})
                deleted += 1
        
        print(f"✅ ({deleted} items deleted)")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def upload_csv_to_table(table_name, csv_file, key_field):
    """Upload CSV data to DynamoDB table with proper key conversion"""
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
        print(f"   ❌ Key field '{key_field}' not found in CSV")
        return 0, len(df)
    
    print(f"   Uploading to '{table_name}'...")
    
    # Batch write
    success_count = 0
    error_count = 0
    error_details = []
    batch_size = 25
    
    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i:i+batch_size]
        
        try:
            with table.batch_writer() as batch:
                for idx, row in batch_df.iterrows():
                    try:
                        # Convert row to dict with proper type conversion
                        item = {}
                        for col in df.columns:
                            value = row[col]
                            # Mark if this is the key field
                            is_key = (col == key_field)
                            converted = convert_value(value, is_key_field=is_key)
                            
                            if converted is not None:
                                item[col] = converted
                        
                        # Ensure key field exists and is a string
                        if key_field not in item:
                            error_count += 1
                            error_details.append(f"Row {idx}: Missing key field")
                            continue
                        
                        if not isinstance(item[key_field], str):
                            error_count += 1
                            error_details.append(f"Row {idx}: Key is not string: {type(item[key_field])}")
                            continue
                        
                        batch.put_item(Item=item)
                        success_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        if len(error_details) < 5:  # Only store first 5 errors
                            error_details.append(f"Row {idx}: {str(e)[:100]}")
            
            # Progress indicator
            if (i // batch_size + 1) % 50 == 0:
                print(f"      Progress: {success_count}/{len(df)} items uploaded")
                
        except Exception as e:
            print(f"      ❌ Batch error: {e}")
            error_count += len(batch_df)
            if len(error_details) < 5:
                error_details.append(f"Batch {i//batch_size}: {str(e)[:100]}")
    
    # Print error details if any
    if error_details:
        print(f"      Error details:")
        for detail in error_details:
            print(f"        - {detail}")
    
    print(f"   ✅ Upload complete: {success_count} items, {error_count} errors")
    return success_count, error_count


def verify_table(table_name):
    """Verify table has data"""
    try:
        table = dynamodb.Table(table_name)
        
        # Scan a few items to verify
        response = table.scan(Limit=5)
        items = response.get('Items', [])
        count = response.get('Count', 0)
        
        # Get table description for item count
        client = boto3.client('dynamodb', region_name=AWS_REGION)
        desc_response = client.describe_table(TableName=table_name)
        item_count = desc_response['Table'].get('ItemCount', count)
        
        print(f"   Items in table: {item_count}")
        
        if items:
            print(f"   Sample item keys:")
            for item in items[:3]:
                # Get the key field
                key_schema = table.key_schema
                key_name = key_schema[0]['AttributeName']
                key_value = item.get(key_name, 'N/A')
                key_type = type(key_value).__name__
                print(f"     - {key_name}={key_value} (type: {key_type})")
        
        return item_count
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return 0


def main():
    """Main execution"""
    print("\n" + "="*80)
    print("RE-UPLOAD FIXED TABLES TO DYNAMODB")
    print("="*80)
    print("\nThis script will:")
    print("  1. Clear existing data from tables")
    print("  2. Re-upload with proper key field conversion (int -> string)")
    print("  3. Verify upload success")
    
    results = {}
    
    for table_name, config in TABLES_TO_FIX.items():
        print(f"\n{'='*80}")
        print(f"Processing: {table_name}")
        print(f"{'='*80}")
        
        # Clear existing data
        if not clear_table(table_name):
            print(f"   ⚠️  Warning: Could not clear table, continuing anyway...")
        
        # Upload data
        try:
            success, errors = upload_csv_to_table(
                table_name, 
                config['file'], 
                config['key_field']
            )
            results[table_name] = {'success': success, 'errors': errors}
        except Exception as e:
            print(f"   ❌ Upload error: {e}")
            results[table_name] = {'success': 0, 'errors': -1}
            continue
        
        # Verify
        print(f"\n   Verification:")
        item_count = verify_table(table_name)
        results[table_name]['verified_count'] = item_count
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_success = 0
    total_errors = 0
    all_verified = True
    
    for table_name, result in results.items():
        success = result['success']
        errors = result['errors']
        verified = result.get('verified_count', 0)
        
        total_success += success
        total_errors += errors if errors > 0 else 0
        
        if verified != success:
            all_verified = False
        
        status = "✅" if success > 0 and errors == 0 else "⚠️" if success > 0 else "❌"
        print(f"{status} {table_name:35}")
        print(f"     Uploaded: {success:>8} items")
        print(f"     Errors:   {errors:>8}")
        print(f"     Verified: {verified:>8} items in table")
    
    print(f"\n📊 Total Statistics:")
    print(f"   Items uploaded: {total_success:,}")
    print(f"   Errors: {total_errors:,}")
    
    if total_success > 0:
        success_rate = (total_success / (total_success + total_errors) * 100) if (total_success + total_errors) > 0 else 0
        print(f"   Success rate: {success_rate:.1f}%")
    
    if total_errors == 0 and total_success > 0 and all_verified:
        print("\n✅ ALL TABLES UPLOADED SUCCESSFULLY WITH 0 ERRORS!")
        return 0
    elif total_success > 0:
        print("\n⚠️  UPLOAD COMPLETED WITH SOME ERRORS")
        return 1
    else:
        print("\n❌ UPLOAD FAILED")
        return 2


if __name__ == '__main__':
    sys.exit(main())
