#!/usr/bin/env python3
"""
Create DynamoDB table for checkpoint persistence
"""

import os
import boto3
import sys

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
TABLE_NAME = os.getenv('CHECKPOINT_TABLE_NAME', 'SkyMarshalCheckpoints')

def create_checkpoint_table():
    """Create DynamoDB table for checkpoint persistence"""
    
    dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
    
    print(f"Creating checkpoint table: {TABLE_NAME}")
    print(f"Region: {AWS_REGION}")
    
    try:
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName=TABLE_NAME)
            print(f"✅ Table {TABLE_NAME} already exists")
            print(f"   Status: {response['Table']['TableStatus']}")
            print(f"   Item count: {response['Table']['ItemCount']}")
            return 0
        except dynamodb.exceptions.ResourceNotFoundException:
            pass
        
        # Create table
        response = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    'AttributeName': 'PK',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'SK',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'PK',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'SK',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'thread_id',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'status',
                    'AttributeType': 'S'  # String
                }
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'thread-status-index',
                    'KeySchema': [
                        {
                            'AttributeName': 'thread_id',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'status',
                            'KeyType': 'RANGE'
                        }
                    ],
                    'Projection': {
                        'ProjectionType': 'ALL'
                    },
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            BillingMode='PROVISIONED',
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            },
            Tags=[
                {
                    'Key': 'Application',
                    'Value': 'SkyMarshal'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'CheckpointPersistence'
                }
            ]
        )
        
        print(f"✅ Table creation initiated: {TABLE_NAME}")
        print(f"   Status: {response['TableDescription']['TableStatus']}")
        
        # Wait for table to be active
        print("\n⏳ Waiting for table to become active...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(
            TableName=TABLE_NAME,
            WaiterConfig={
                'Delay': 5,
                'MaxAttempts': 60
            }
        )
        
        # Enable TTL
        print("\n⏳ Enabling TTL on 'ttl' attribute...")
        dynamodb.update_time_to_live(
            TableName=TABLE_NAME,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': 'ttl'
            }
        )
        
        print(f"\n✅ Table {TABLE_NAME} created successfully!")
        print("\nTable details:")
        print(f"  - Partition Key: PK (String)")
        print(f"  - Sort Key: SK (String)")
        print(f"  - GSI: thread-status-index (thread_id, status)")
        print(f"  - TTL: Enabled on 'ttl' attribute")
        print(f"  - Billing: Provisioned (5 RCU, 5 WCU)")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error creating table: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(create_checkpoint_table())
