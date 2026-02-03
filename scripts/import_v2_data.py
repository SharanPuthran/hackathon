#!/usr/bin/env python3
"""
Import V2 CSV Data to DynamoDB Script

Imports all 23 V2 CSV files from database/output/v2/ into their corresponding DynamoDB tables.
This script uses batch writes for efficiency and handles data type conversions.

Usage:
    python scripts/import_v2_data.py [--dry-run] [--table TABLE_NAME] [--verify]

Arguments:
    --dry-run       Print what would be imported without actually importing
    --table NAME    Import only the specified table (e.g., flights_v2)
    --verify        Verify data counts after import
"""

import boto3
import csv
import sys
import argparse
import os
from decimal import Decimal
from typing import Dict, List, Any, Optional
from botocore.exceptions import ClientError

# Add parent directory to path for imports
sys.path.insert(0, '/Users/sharanputhran/Learning/Hackathon/skymarshal_agents_new/skymarshal/src')

from database.table_config import CSV_TO_TABLE_MAPPING, V2_TABLE_SCHEMAS

# AWS Configuration
AWS_REGION = "us-east-1"
CSV_BASE_PATH = "/Users/sharanputhran/Learning/Hackathon/database/output/v2"
BATCH_SIZE = 25  # DynamoDB batch write limit


def convert_value(value: Any, column_name: str) -> Any:
    """
    Convert CSV string value to appropriate DynamoDB type.

    Args:
        value: The string value from CSV
        column_name: The column name (used for type inference)

    Returns:
        Converted value appropriate for DynamoDB
    """
    # Handle None and empty values first
    if value is None:
        return None

    # Convert to string for further processing
    value_str = str(value).strip()

    if value_str == '' or value_str.lower() == 'null':
        return None

    # Columns that should always be strings (GSI keys, IDs, etc.)
    string_columns = (
        '_id', '_number', 'pnr', 'code', 'name', 'type', 'status',
        'regulation', 'category', 'connection_type', 'role', 'base',
        'aircraft_registration', 'airport_code', 'equipment_type',
        'partner_airline_code', 'origin', 'destination'
    )

    # Check if column should always be string
    is_string_column = any(column_name.lower().endswith(suffix) or
                          column_name.lower() == suffix.strip('_')
                          for suffix in string_columns)

    # For sequence_number specifically, keep as string for GSI compatibility
    if column_name.lower() == 'sequence_number':
        return value_str

    if is_string_column:
        return value_str

    # Boolean conversions - only for explicit true/false/yes/no (not 1/0)
    if value_str.lower() in ('true', 'yes'):
        return True
    if value_str.lower() in ('false', 'no'):
        return False

    # Numeric conversions (for known numeric columns)
    numeric_suffixes = (
        '_count', '_minutes', '_hours', '_kg', '_usd', '_cbm',
        '_min', '_max', '_c', '_kts', '_m', '_ft', '_percent', 'capacity',
        'weight', 'volume', 'pieces', 'quantity', 'value',
        'cost', 'fee', 'penalty', 'followers'
    )

    # Check if it's a numeric column
    is_numeric_column = any(column_name.lower().endswith(suffix) for suffix in numeric_suffixes)

    if is_numeric_column:
        try:
            # Try integer first
            if '.' not in value_str:
                return int(value_str)
            # Then decimal
            return Decimal(value_str)
        except (ValueError, TypeError, Exception):
            # Return as string if conversion fails
            return value_str

    # Try to detect numbers automatically
    try:
        if '.' in value_str:
            return Decimal(value_str)
        elif value_str.isdigit() or (value_str.startswith('-') and value_str[1:].isdigit()):
            return int(value_str)
    except (ValueError, TypeError, Exception):
        pass

    # Return as string
    return value_str


def read_csv_file(csv_path: str) -> List[Dict[str, Any]]:
    """
    Read CSV file and convert to list of dictionaries.

    Args:
        csv_path: Path to the CSV file

    Returns:
        List of dictionaries representing each row
    """
    items = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            item = {}
            for column_name, value in row.items():
                # Skip None column names (caused by trailing commas or extra fields)
                if column_name is None:
                    continue
                # Skip empty column names
                if not column_name or not column_name.strip():
                    continue
                converted_value = convert_value(value, column_name)
                # Skip None values (DynamoDB doesn't allow None/NULL)
                if converted_value is not None:
                    item[column_name] = converted_value
            items.append(item)

    return items


def batch_write_items(dynamodb_resource, table_name: str, items: List[Dict[str, Any]]) -> int:
    """
    Write items to DynamoDB table in batches.

    Args:
        dynamodb_resource: Boto3 DynamoDB resource
        table_name: Name of the DynamoDB table
        items: List of items to write

    Returns:
        Number of items successfully written
    """
    table = dynamodb_resource.Table(table_name)
    written = 0

    # Process in batches
    for i in range(0, len(items), BATCH_SIZE):
        batch = items[i:i + BATCH_SIZE]

        with table.batch_writer() as writer:
            for item in batch:
                try:
                    writer.put_item(Item=item)
                    written += 1
                except ClientError as e:
                    print(f"  [ERROR] Failed to write item: {e}")

    return written


def import_csv_to_table(
    dynamodb_resource,
    csv_filename: str,
    table_name: str,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Import a single CSV file to its corresponding DynamoDB table.

    Args:
        dynamodb_resource: Boto3 DynamoDB resource
        csv_filename: Name of the CSV file
        table_name: Name of the DynamoDB table
        dry_run: If True, only print what would be imported

    Returns:
        Dictionary with import statistics
    """
    csv_path = os.path.join(CSV_BASE_PATH, csv_filename)
    result = {
        "csv_file": csv_filename,
        "table_name": table_name,
        "csv_rows": 0,
        "items_written": 0,
        "success": False,
        "error": None
    }

    # Check if CSV file exists
    if not os.path.exists(csv_path):
        result["error"] = f"CSV file not found: {csv_path}"
        print(f"[ERROR] {result['error']}")
        return result

    # Read CSV file
    try:
        items = read_csv_file(csv_path)
        result["csv_rows"] = len(items)
    except Exception as e:
        result["error"] = f"Failed to read CSV: {e}"
        print(f"[ERROR] {result['error']}")
        return result

    if dry_run:
        print(f"\n[DRY-RUN] Would import: {csv_filename} -> {table_name}")
        print(f"  CSV rows: {len(items)}")
        if items:
            print(f"  Sample columns: {list(items[0].keys())[:5]}...")
        result["success"] = True
        return result

    # Check if table exists
    try:
        dynamodb_resource.Table(table_name).table_status
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            result["error"] = f"Table {table_name} does not exist. Run create_v2_tables.py first."
            print(f"[ERROR] {result['error']}")
            return result
        raise

    # Write to DynamoDB
    print(f"\n[IMPORT] {csv_filename} -> {table_name}")
    print(f"  CSV rows: {len(items)}")

    try:
        written = batch_write_items(dynamodb_resource, table_name, items)
        result["items_written"] = written
        result["success"] = True
        print(f"  [SUCCESS] Imported {written}/{len(items)} items")
    except Exception as e:
        result["error"] = f"Failed to write to DynamoDB: {e}"
        print(f"  [ERROR] {result['error']}")

    return result


def import_all_v2_data(dry_run: bool = False, specific_table: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Import all V2 CSV files to their corresponding DynamoDB tables.

    Args:
        dry_run: If True, only print what would be imported
        specific_table: If provided, only import this specific table

    Returns:
        List of import result dictionaries
    """
    dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION)
    results = []

    print("=" * 70)
    print("SkyMarshal V2 Data Import")
    print("=" * 70)
    print(f"Region: {AWS_REGION}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print(f"CSV Source: {CSV_BASE_PATH}")
    print(f"Tables to import: {len(CSV_TO_TABLE_MAPPING)}")
    print("=" * 70)

    for csv_filename, table_name in CSV_TO_TABLE_MAPPING.items():
        # Skip if specific table requested and this isn't it
        if specific_table and table_name != specific_table:
            continue

        result = import_csv_to_table(dynamodb_resource, csv_filename, table_name, dry_run)
        results.append(result)

    # Print summary
    print("\n" + "=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)

    total_csv_rows = sum(r["csv_rows"] for r in results)
    total_written = sum(r["items_written"] for r in results)
    successful = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])

    print(f"Total CSV files: {len(results)}")
    print(f"Total CSV rows: {total_csv_rows}")
    print(f"Total items written: {total_written}")
    print(f"Successful imports: {successful}")
    print(f"Failed imports: {failed}")

    if failed > 0:
        print("\nFailed imports:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['csv_file']}: {r['error']}")

    return results


def verify_data() -> None:
    """Verify data counts in all V2 tables."""
    dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)

    print("\n" + "=" * 70)
    print("V2 DATA VERIFICATION")
    print("=" * 70)
    print(f"{'CSV File':<35} {'Table':<35} {'CSV Rows':>10} {'DB Items':>10} {'Match':>7}")
    print("-" * 70)

    for csv_filename, table_name in CSV_TO_TABLE_MAPPING.items():
        csv_path = os.path.join(CSV_BASE_PATH, csv_filename)

        # Count CSV rows
        csv_rows = 0
        if os.path.exists(csv_path):
            with open(csv_path, 'r') as f:
                csv_rows = sum(1 for _ in f) - 1  # Subtract header

        # Count DynamoDB items
        db_items = 0
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            db_items = response['Table'].get('ItemCount', 0)
        except ClientError:
            db_items = -1  # Table doesn't exist

        match = "YES" if csv_rows == db_items else "NO"
        if db_items == -1:
            match = "MISSING"

        print(f"{csv_filename:<35} {table_name:<35} {csv_rows:>10} {db_items:>10} {match:>7}")


def main():
    parser = argparse.ArgumentParser(description="Import V2 CSV data to DynamoDB")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be imported without importing")
    parser.add_argument("--table", type=str, help="Import only the specified table (e.g., flights_v2)")
    parser.add_argument("--verify", action="store_true", help="Verify data counts after import")

    args = parser.parse_args()

    if args.verify:
        verify_data()
        return

    results = import_all_v2_data(dry_run=args.dry_run, specific_table=args.table)

    # Exit with error code if any imports failed
    if any(not r["success"] for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
