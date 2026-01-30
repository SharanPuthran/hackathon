#!/usr/bin/env python3
"""
Test script for Crew Compliance agent database tools
Tests DynamoDB queries directly without LangChain decorators
"""

import boto3
import json
from decimal import Decimal

# Custom JSON encoder for DynamoDB Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

# DynamoDB Configuration
AWS_REGION = "us-east-1"
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

# Initialize tables
crew_roster_table = dynamodb.Table('CrewRoster')
crew_members_table = dynamodb.Table('CrewMembers')

print("=" * 60)
print("Testing Crew Compliance Agent Database Tools")
print("=" * 60)

# Test 1: Query flight crew roster for flight 1
print("\n📋 Test 1: Query Crew Roster for Flight 1")
print("-" * 60)
try:
    response = crew_roster_table.query(
        IndexName='flight-position-index',
        KeyConditionExpression='flight_id = :fid',
        ExpressionAttributeValues={':fid': '1'}
    )

    crew_roster = response['Items']
    print(f"✅ Success! Found {len(crew_roster)} crew members")
    print(f"\nCrew Roster:")
    for i, crew in enumerate(crew_roster, 1):
        print(f"  {i}. Crew ID: {crew.get('crew_id')}, Position: {crew.get('position_id')}, "
              f"Status: {crew.get('roster_status', 'N/A')}")

except Exception as e:
    print(f"❌ Exception: {str(e)}")

# Test 2: Query crew member details
print("\n\n👤 Test 2: Query Crew Member Details (Crew ID 5)")
print("-" * 60)
try:
    response = crew_members_table.get_item(
        Key={'crew_id': '5'}
    )

    crew_member = response.get('Item')

    if not crew_member:
        print(f"❌ Crew member 5 not found")
    else:
        print(f"✅ Success!")
        print(f"\nCrew Member Details:")
        print(f"  - Crew ID: {crew_member.get('crew_id')}")
        print(f"  - Name: {crew_member.get('first_name', 'N/A')} {crew_member.get('last_name', 'N/A')}")
        print(f"  - Position: {crew_member.get('position_id', 'N/A')}")
        print(f"  - Base: {crew_member.get('base_airport_id', 'N/A')}")

except Exception as e:
    print(f"❌ Exception: {str(e)}")

# Test 3: Test another flight
print("\n\n📋 Test 3: Query Crew Roster for Flight 5")
print("-" * 60)
try:
    response = crew_roster_table.query(
        IndexName='flight-position-index',
        KeyConditionExpression='flight_id = :fid',
        ExpressionAttributeValues={':fid': '5'}
    )

    crew_roster = response['Items']
    print(f"✅ Success! Found {len(crew_roster)} crew members for flight 5")

except Exception as e:
    print(f"❌ Exception: {str(e)}")

# Test 4: Check GSI exists
print("\n\n🔍 Test 4: Verify GSI Configuration")
print("-" * 60)
try:
    table_desc = dynamodb.meta.client.describe_table(TableName='CrewRoster')
    gsis = table_desc['Table'].get('GlobalSecondaryIndexes', [])

    print(f"Found {len(gsis)} GSI(s) on CrewRoster table:")
    for gsi in gsis:
        status = gsi.get('IndexStatus', 'UNKNOWN')
        print(f"  - {gsi['IndexName']}: {status}")
        print(f"    Keys: PK={gsi['KeySchema'][0]['AttributeName']}", end="")
        if len(gsi['KeySchema']) > 1:
            print(f", SK={gsi['KeySchema'][1]['AttributeName']}")
        else:
            print()

except Exception as e:
    print(f"❌ Exception: {str(e)}")

print("\n" + "=" * 60)
print("✅ Database Tool Tests Complete!")
print("=" * 60)
print("\n💡 Next Steps:")
print("   1. If all tests passed: Agent can query DynamoDB successfully")
print("   2. Start the agent: python src/main.py")
print("   3. Test via HTTP: curl -X POST http://localhost:8080/invoke ...")

