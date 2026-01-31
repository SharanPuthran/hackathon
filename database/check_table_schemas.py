#!/usr/bin/env python3
"""Check DynamoDB table schemas"""

import boto3
import os

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
client = boto3.client('dynamodb', region_name=AWS_REGION)

tables = ['financial_transactions', 'disruption_costs']

for table_name in tables:
    try:
        response = client.describe_table(TableName=table_name)
        key_schema = response['Table']['KeySchema']
        attr_defs = response['Table']['AttributeDefinitions']
        item_count = response['Table'].get('ItemCount', 0)
        
        print(f'\n{table_name}:')
        print(f'  Item Count: {item_count}')
        print(f'  Key Schema: {key_schema}')
        print(f'  Attribute Definitions: {attr_defs}')
    except Exception as e:
        print(f'\n{table_name}: Error - {e}')
