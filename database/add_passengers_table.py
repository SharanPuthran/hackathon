#!/usr/bin/env python3
"""
Add Passengers Table Configuration and Upload

This script adds the passengers table to the upload configuration and uploads the data.
"""

import os
import sys
import csv
import boto3
from botocore.exceptions import ClientError

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')
PASSENGERS_CSV = os.path.join(OUTPUT_DIR, 'passengers_enriched_final.csv')

# Table configuration
PASSENGERS_TABLE_CONFIG = {
    'TableName': 'passengers',
    'KeySchema': [
        {'AttributeName': 'passenger_id', 'KeyType': 'HASH'}
    ],
    'AttributeDefinitions': [
        {'AttributeName': 'passenger_id', 'AttributeType': 'N'}
    ],
    'BillingMode': 'PAY_PER_REQUEST'
}


def create_passengers_table():
    """Create the passengers table in DynamoDB"""
    print("\n" + "=" * 60)
    print("Creating passengers table...")
    print("=" * 60)
    
    try:
        response = dynamodb.create_table(**PASSENGERS_TABLE_CONFIG)
        print(f"✅ Table 'passengers' created successfully")
        print(f"   Status: {response['TableDescription']['TableStatus']}")
        
        # Wait for table to be active
        waiter = dynamodb.get_waiter('table_exists')
        print("   Waiting for table to become active...")
        waiter.wait(TableName='passengers')
        print("   Table is now ACTIVE")
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table 'passengers' already exists")
            return True
        else:
            print(f"❌ Error creating table: {e}")
            return False


def upload_passengers_data():
    """Upload passengers data from CSV to DynamoDB"""
    print("\n" + "=" * 60)
    print("Uploading passengers data...")
    print("=" * 60)
    
    if not os.path.exists(PASSENGERS_CSV):
        print(f"❌ CSV file not found: {PASSENGERS_CSV}")
        return False
    
    try:
        # Read CSV file
        with open(PASSENGERS_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            items = []
            
            for row in reader:
                # Convert passenger_id to number
                item = {
                    'passenger_id': {'N': str(row['passenger_id'])},
                    'first_name': {'S': row.get('first_name', '')},
                    'last_name': {'S': row.get('last_name', '')},
                    'email': {'S': row.get('email', '')},
                    'phone': {'S': row.get('phone', '')},
                    'nationality': {'S': row.get('nationality', '')},
                    'passport_number': {'S': row.get('passport_number', '')},
                }
                
                # Add optional fields if present
                if row.get('date_of_birth'):
                    item['date_of_birth'] = {'S': row['date_of_birth']}
                if row.get('passport_expiry'):
                    item['passport_expiry'] = {'S': row['passport_expiry']}
                if row.get('frequent_flyer_number'):
                    item['frequent_flyer_number'] = {'S': row['frequent_flyer_number']}
                if row.get('frequent_flyer_tier_id'):
                    item['frequent_flyer_tier_id'] = {'N': str(row['frequent_flyer_tier_id'])}
                if row.get('is_vip'):
                    item['is_vip'] = {'BOOL': row['is_vip'].lower() in ['true', '1', 'yes']}
                if row.get('has_medical_condition'):
                    item['has_medical_condition'] = {'BOOL': row['has_medical_condition'].lower() in ['true', '1', 'yes']}
                if row.get('medical_notes'):
                    item['medical_notes'] = {'S': row['medical_notes']}
                if row.get('meal_preference'):
                    item['meal_preference'] = {'S': row['meal_preference']}
                if row.get('pnr'):
                    item['pnr'] = {'S': row['pnr']}
                if row.get('traveler_id'):
                    item['traveler_id'] = {'S': row['traveler_id']}
                if row.get('preferred_language'):
                    item['preferred_language'] = {'S': row['preferred_language']}
                if row.get('customer_value_score'):
                    item['customer_value_score'] = {'N': str(row['customer_value_score'])}
                
                items.append(item)
        
        print(f"📊 Read {len(items)} passengers from CSV")
        
        # Upload in batches of 25 (DynamoDB limit)
        batch_size = 25
        total_uploaded = 0
        errors = 0
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            try:
                request_items = {
                    'passengers': [
                        {'PutRequest': {'Item': item}} for item in batch
                    ]
                }
                
                response = dynamodb.batch_write_item(RequestItems=request_items)
                total_uploaded += len(batch)
                
                # Handle unprocessed items
                if response.get('UnprocessedItems'):
                    print(f"⚠️  Batch {i//batch_size + 1}: {len(response['UnprocessedItems'])} unprocessed items")
                    errors += len(response['UnprocessedItems'])
                
                # Progress indicator
                if (i // batch_size + 1) % 10 == 0:
                    print(f"   Progress: {total_uploaded}/{len(items)} items uploaded")
                    
            except ClientError as e:
                print(f"❌ Error uploading batch {i//batch_size + 1}: {e}")
                errors += len(batch)
        
        print(f"\n✅ Upload complete!")
        print(f"   Total items: {len(items)}")
        print(f"   Uploaded: {total_uploaded}")
        print(f"   Errors: {errors}")
        print(f"   Success rate: {(total_uploaded / len(items) * 100):.1f}%")
        
        return errors == 0
        
    except Exception as e:
        print(f"❌ Error reading CSV or uploading data: {e}")
        return False


def verify_upload():
    """Verify the passengers table has data"""
    print("\n" + "=" * 60)
    print("Verifying passengers table...")
    print("=" * 60)
    
    try:
        response = dynamodb.describe_table(TableName='passengers')
        item_count = response['Table'].get('ItemCount', 0)
        
        print(f"✅ Table 'passengers' verified")
        print(f"   Status: {response['Table']['TableStatus']}")
        print(f"   Item count: {item_count}")
        
        # Sample query
        scan_response = dynamodb.scan(
            TableName='passengers',
            Limit=5
        )
        
        print(f"   Sample items: {len(scan_response.get('Items', []))}")
        
        return True
        
    except ClientError as e:
        print(f"❌ Error verifying table: {e}")
        return False


def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("PASSENGERS TABLE SETUP")
    print("=" * 80)
    
    # Step 1: Create table
    if not create_passengers_table():
        print("\n❌ Failed to create passengers table")
        sys.exit(1)
    
    # Step 2: Upload data
    if not upload_passengers_data():
        print("\n❌ Failed to upload passengers data")
        sys.exit(1)
    
    # Step 3: Verify
    if not verify_upload():
        print("\n❌ Failed to verify passengers table")
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✅ PASSENGERS TABLE SETUP COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Verify data in AWS Console")
    print("2. Test queries against passengers table")
    print("3. Update agents to use passengers data")


if __name__ == '__main__':
    main()
