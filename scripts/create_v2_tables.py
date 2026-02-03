#!/usr/bin/env python3
"""
Create V2 DynamoDB Tables Script

Creates all 23 V2 DynamoDB tables with proper schemas and GSIs.
This script does NOT modify existing tables - it only creates new _v2 tables.

Usage:
    python scripts/create_v2_tables.py [--dry-run] [--table TABLE_NAME]

Arguments:
    --dry-run       Print what would be created without actually creating
    --table NAME    Create only the specified table (e.g., flights_v2)
"""

import boto3
import sys
import argparse
import time
from typing import Dict, List, Optional
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.insert(0, '/Users/sharanputhran/Learning/Hackathon/skymarshal_agents_new/skymarshal/src')

from database.table_config import V2_TABLE_SCHEMAS, V2_TABLES, TableSchema

# AWS Configuration
AWS_REGION = "us-east-1"
BILLING_MODE = "PAY_PER_REQUEST"


def create_table_definition(table_name: str, schema: TableSchema) -> Dict:
    """
    Create DynamoDB table definition from TableSchema.

    Args:
        table_name: The DynamoDB table name
        schema: TableSchema object with key and GSI definitions

    Returns:
        Dictionary with CreateTable parameters
    """
    # Key schema
    key_schema = [
        {
            "AttributeName": schema.partition_key,
            "KeyType": "HASH"
        }
    ]

    # Attribute definitions
    attribute_definitions = [
        {
            "AttributeName": schema.partition_key,
            "AttributeType": schema.partition_key_type
        }
    ]

    # Add sort key if present
    if schema.sort_key:
        key_schema.append({
            "AttributeName": schema.sort_key,
            "KeyType": "RANGE"
        })
        attribute_definitions.append({
            "AttributeName": schema.sort_key,
            "AttributeType": schema.sort_key_type or "S"
        })

    # Base table definition
    table_def = {
        "TableName": table_name,
        "KeySchema": key_schema,
        "AttributeDefinitions": attribute_definitions,
        "BillingMode": BILLING_MODE
    }

    # Add GSIs if present
    if schema.gsis:
        gsi_definitions = []
        for gsi in schema.gsis:
            gsi_key_schema = [
                {
                    "AttributeName": gsi["pk"],
                    "KeyType": "HASH"
                }
            ]

            # Add GSI partition key to attribute definitions if not already present
            pk_attr = {"AttributeName": gsi["pk"], "AttributeType": "S"}
            if pk_attr not in attribute_definitions and not any(
                ad["AttributeName"] == gsi["pk"] for ad in attribute_definitions
            ):
                attribute_definitions.append(pk_attr)

            # Add sort key if present
            if "sk" in gsi:
                gsi_key_schema.append({
                    "AttributeName": gsi["sk"],
                    "KeyType": "RANGE"
                })
                # Add GSI sort key to attribute definitions if not already present
                sk_attr = {"AttributeName": gsi["sk"], "AttributeType": "S"}
                if sk_attr not in attribute_definitions and not any(
                    ad["AttributeName"] == gsi["sk"] for ad in attribute_definitions
                ):
                    attribute_definitions.append(sk_attr)

            gsi_definitions.append({
                "IndexName": gsi["name"],
                "KeySchema": gsi_key_schema,
                "Projection": {"ProjectionType": "ALL"}
            })

        table_def["GlobalSecondaryIndexes"] = gsi_definitions

    return table_def


def table_exists(dynamodb_client, table_name: str) -> bool:
    """Check if a table already exists."""
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        raise


def wait_for_table_active(dynamodb_client, table_name: str, max_wait: int = 300) -> bool:
    """Wait for table to become active."""
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            if status == 'ACTIVE':
                return True
            print(f"  Table {table_name} status: {status}, waiting...")
            time.sleep(5)
        except ClientError as e:
            print(f"  Error checking table status: {e}")
            time.sleep(5)
    return False


def create_v2_table(dynamodb_client, table_name: str, schema: TableSchema, dry_run: bool = False) -> bool:
    """
    Create a single V2 table.

    Args:
        dynamodb_client: Boto3 DynamoDB client
        table_name: Name of the table to create
        schema: TableSchema object
        dry_run: If True, only print what would be created

    Returns:
        True if successful, False otherwise
    """
    # Check if table already exists
    if table_exists(dynamodb_client, table_name):
        print(f"[SKIP] Table {table_name} already exists")
        return True

    # Create table definition
    table_def = create_table_definition(table_name, schema)

    if dry_run:
        print(f"\n[DRY-RUN] Would create table: {table_name}")
        print(f"  Partition Key: {schema.partition_key} ({schema.partition_key_type})")
        if schema.sort_key:
            print(f"  Sort Key: {schema.sort_key} ({schema.sort_key_type})")
        if schema.gsis:
            print(f"  GSIs ({len(schema.gsis)}):")
            for gsi in schema.gsis:
                sk_info = f", SK: {gsi['sk']}" if 'sk' in gsi else ""
                print(f"    - {gsi['name']} (PK: {gsi['pk']}{sk_info})")
        return True

    # Create the table
    try:
        print(f"\n[CREATE] Creating table: {table_name}")
        dynamodb_client.create_table(**table_def)

        # Wait for table to become active
        print(f"  Waiting for table to become active...")
        if wait_for_table_active(dynamodb_client, table_name):
            print(f"  [SUCCESS] Table {table_name} created and active")
            return True
        else:
            print(f"  [WARNING] Table {table_name} created but not yet active")
            return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ResourceInUseException':
            print(f"  [SKIP] Table {table_name} already exists")
            return True
        else:
            print(f"  [ERROR] Failed to create table {table_name}: {e}")
            return False


def create_all_v2_tables(dry_run: bool = False, specific_table: Optional[str] = None) -> Dict[str, bool]:
    """
    Create all V2 tables.

    Args:
        dry_run: If True, only print what would be created
        specific_table: If provided, only create this specific table

    Returns:
        Dictionary mapping table names to success status
    """
    dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
    results = {}

    print("=" * 70)
    print("SkyMarshal V2 DynamoDB Table Creation")
    print("=" * 70)
    print(f"Region: {AWS_REGION}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"Tables to create: {len(V2_TABLE_SCHEMAS)}")
    print("=" * 70)

    for table_name, schema in V2_TABLE_SCHEMAS.items():
        # Skip if specific table requested and this isn't it
        if specific_table and table_name != specific_table:
            continue

        success = create_v2_table(dynamodb_client, table_name, schema, dry_run)
        results[table_name] = success

        # Small delay between table creations to avoid throttling
        if not dry_run and success:
            time.sleep(1)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = sum(1 for v in results.values() if v)
    failed = sum(1 for v in results.values() if not v)

    print(f"Total tables: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\nFailed tables:")
        for table_name, success in results.items():
            if not success:
                print(f"  - {table_name}")

    return results


def verify_tables() -> None:
    """Verify all V2 tables exist and print their status."""
    dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)

    print("\n" + "=" * 70)
    print("V2 TABLE VERIFICATION")
    print("=" * 70)

    for table_name in V2_TABLE_SCHEMAS.keys():
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            item_count = response['Table'].get('ItemCount', 0)
            gsi_count = len(response['Table'].get('GlobalSecondaryIndexes', []))
            print(f"[{status:8}] {table_name:40} Items: {item_count:5}, GSIs: {gsi_count}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"[MISSING ] {table_name:40}")
            else:
                print(f"[ERROR   ] {table_name:40} - {e}")


def main():
    parser = argparse.ArgumentParser(description="Create V2 DynamoDB tables")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without creating")
    parser.add_argument("--table", type=str, help="Create only the specified table")
    parser.add_argument("--verify", action="store_true", help="Verify existing tables")

    args = parser.parse_args()

    if args.verify:
        verify_tables()
        return

    results = create_all_v2_tables(dry_run=args.dry_run, specific_table=args.table)

    # Exit with error code if any tables failed
    if any(not v for v in results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
