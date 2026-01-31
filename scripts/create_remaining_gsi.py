#!/usr/bin/env python3
"""
Create remaining GSI for CargoFlightAssignments table

This script waits for the flight-loading-index to become ACTIVE,
then creates the shipment-index GSI.
"""

import boto3
import asyncio
import sys
from datetime import datetime

dynamodb_client = boto3.client('dynamodb')

async def wait_for_gsi_active(table_name: str, index_name: str, timeout: int = 600):
    """Wait for a GSI to become ACTIVE."""
    start_time = asyncio.get_event_loop().time()
    print(f"Waiting for {index_name} on {table_name} to become ACTIVE...", flush=True)

    while asyncio.get_event_loop().time() - start_time < timeout:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            gsis = response['Table'].get('GlobalSecondaryIndexes', [])

            for gsi in gsis:
                if gsi['IndexName'] == index_name:
                    status = gsi['IndexStatus']

                    if status == 'ACTIVE':
                        elapsed = int(asyncio.get_event_loop().time() - start_time)
                        print(f"✓ {index_name} is ACTIVE ({elapsed}s)")
                        return True
                    elif status == 'CREATING':
                        print(".", end='', flush=True)
                    else:
                        print(f"\n✗ Unexpected status: {status}")
                        return False

            await asyncio.sleep(10)

        except Exception as e:
            print(f"\n✗ Error: {str(e)}")
            return False

    print("\n✗ Timeout")
    return False

def create_shipment_index():
    """Create the shipment-index GSI."""
    try:
        print("\nCreating shipment-index GSI...")
        
        # Get existing attribute definitions
        response = dynamodb_client.describe_table(TableName='CargoFlightAssignments')
        existing_attrs = response['Table'].get('AttributeDefinitions', [])
        
        # Add shipment_id attribute if not exists
        attr_names = {attr['AttributeName'] for attr in existing_attrs}
        if 'shipment_id' not in attr_names:
            existing_attrs.append({
                'AttributeName': 'shipment_id',
                'AttributeType': 'S'
            })
        
        # Create GSI
        dynamodb_client.update_table(
            TableName='CargoFlightAssignments',
            AttributeDefinitions=existing_attrs,
            GlobalSecondaryIndexUpdates=[{
                'Create': {
                    'IndexName': 'shipment-index',
                    'KeySchema': [
                        {'AttributeName': 'shipment_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            }]
        )
        
        print("✓ shipment-index GSI created successfully!")
        return True
        
    except Exception as e:
        error_msg = str(e)
        if 'already exists' in error_msg.lower():
            print("ℹ shipment-index already exists")
            return True
        else:
            print(f"✗ Error creating GSI: {error_msg}")
            return False

async def main():
    """Main entry point."""
    print("=" * 80)
    print("Create Remaining GSI for CargoFlightAssignments")
    print("=" * 80)
    print()
    
    # Wait for flight-loading-index to become ACTIVE
    if await wait_for_gsi_active('CargoFlightAssignments', 'flight-loading-index'):
        # Create shipment-index
        if create_shipment_index():
            print("\n✓ All GSIs for CargoFlightAssignments created successfully!")
            return 0
        else:
            return 1
    else:
        print("\n✗ Failed to wait for flight-loading-index")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
