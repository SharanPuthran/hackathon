#!/usr/bin/env python3
"""
Add DynamoDB Permissions to AgentCore Runtime Role

This script adds DynamoDB read permissions to the AgentCore runtime IAM role
so that agents can query DynamoDB tables.
"""

import boto3
import json
import sys

# Initialize IAM client
iam_client = boto3.client('iam')

# Role name (from validation report)
ROLE_NAME = 'AmazonBedrockAgentCoreSDKRuntime-us-east-1-51e75bb8e1'

# DynamoDB tables that agents need access to
DYNAMODB_TABLES = [
    'flights',
    'bookings',
    'passengers',
    'CrewRoster',
    'CrewMembers',
    'MaintenanceWorkOrders',
    'MaintenanceStaff',
    'maintenance_roster',
    'AircraftAvailability',
    'CargoFlightAssignments',
    'CargoShipments',
    'Baggage',
    'Weather'
]

def get_account_id():
    """Get AWS account ID."""
    sts = boto3.client('sts')
    return sts.get_caller_identity()['Account']

def get_region():
    """Get AWS region."""
    session = boto3.session.Session()
    return session.region_name or 'us-east-1'

def create_dynamodb_policy_document():
    """Create IAM policy document for DynamoDB access."""
    account_id = get_account_id()
    region = get_region()
    
    # Build table ARNs
    table_arns = [
        f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}"
        for table_name in DYNAMODB_TABLES
    ]
    
    # Add GSI ARNs (allow access to all GSIs on these tables)
    table_arns.extend([
        f"arn:aws:dynamodb:{region}:{account_id}:table/{table_name}/index/*"
        for table_name in DYNAMODB_TABLES
    ])
    
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "DynamoDBReadAccess",
                "Effect": "Allow",
                "Action": [
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchGetItem",
                    "dynamodb:DescribeTable"
                ],
                "Resource": table_arns
            }
        ]
    }
    
    return policy_document

def add_inline_policy():
    """Add inline policy to the IAM role."""
    try:
        policy_document = create_dynamodb_policy_document()
        policy_name = 'DynamoDBReadAccessPolicy'
        
        print(f"Adding DynamoDB permissions to role: {ROLE_NAME}")
        print(f"Policy name: {policy_name}")
        print()
        print("Tables with access:")
        for table in DYNAMODB_TABLES:
            print(f"  - {table}")
        print()
        
        # Put role policy
        iam_client.put_role_policy(
            RoleName=ROLE_NAME,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        
        print("✓ DynamoDB permissions added successfully!")
        print()
        print("Permissions granted:")
        print("  - dynamodb:GetItem")
        print("  - dynamodb:Query")
        print("  - dynamodb:Scan")
        print("  - dynamodb:BatchGetItem")
        print("  - dynamodb:DescribeTable")
        print()
        print("Next steps:")
        print("  1. Run validation script to verify permissions")
        print("  2. Test agent queries against DynamoDB")
        
        return True
        
    except iam_client.exceptions.NoSuchEntityException:
        print(f"✗ Error: Role {ROLE_NAME} does not exist")
        return False
    except Exception as e:
        print(f"✗ Error adding policy: {str(e)}")
        return False

def check_existing_policies():
    """Check existing inline policies on the role."""
    try:
        response = iam_client.list_role_policies(RoleName=ROLE_NAME)
        policies = response.get('PolicyNames', [])
        
        if policies:
            print("Existing inline policies:")
            for policy in policies:
                print(f"  - {policy}")
            print()
        
        return policies
        
    except Exception as e:
        print(f"✗ Error checking policies: {str(e)}")
        return []

def main():
    """Main entry point."""
    print("=" * 80)
    print("Add DynamoDB Permissions to AgentCore Runtime Role")
    print("=" * 80)
    print()
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity['Account']}")
        print(f"User: {identity['Arn'].split('/')[-1]}")
        print(f"Region: {get_region()}")
        print()
    except Exception as e:
        print(f"Error: AWS credentials not configured: {e}")
        return 1
    
    # Check existing policies
    existing_policies = check_existing_policies()
    
    if 'DynamoDBReadAccessPolicy' in existing_policies:
        print("⚠ DynamoDBReadAccessPolicy already exists")
        print("Do you want to update it? (y/n): ", end='')
        response = input().strip().lower()
        if response != 'y':
            print("Aborted.")
            return 0
        print()
    
    # Add the policy
    if add_inline_policy():
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())
