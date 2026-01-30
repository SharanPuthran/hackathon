#!/usr/bin/env python3
import boto3
import csv
import argparse
import os
import sys
from decimal import Decimal
from datetime import datetime
from pathlib import Path
import logging

"""
DynamoDB CSV Import Tool

This script imports CSV data into DynamoDB tables based on table definitions.
It supports:
- Automatic CSV discovery and table matching
- Schema validation
- Dry-run mode for testing
- Batch imports with progress tracking
- Error handling and logging
"""

# Import table definitions from create_dynamodb_tables.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from create_dynamodb_tables import TABLE_DEFINITIONS, convert_to_dynamodb_type

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def discover_csv_files(directories):
    """
    Discover all CSV files in the specified directories.

    Args:
        directories: List of directory paths to scan

    Returns:
        Dictionary mapping CSV basename (without extension) to full path
    """
    csv_files = {}

    for directory in directories:
        if not os.path.exists(directory):
            logger.warning(f"Directory not found: {directory}")
            continue

        for file_path in Path(directory).rglob('*.csv'):
            basename = file_path.stem  # filename without extension
            if basename not in csv_files:
                csv_files[basename] = str(file_path)

    return csv_files


def match_csvs_to_tables(csv_files, table_definitions):
    """
    Match discovered CSV files to table definitions.

    Args:
        csv_files: Dictionary of CSV files (basename -> path)
        table_definitions: TABLE_DEFINITIONS dictionary

    Returns:
        List of tuples (table_key, table_config, csv_path)
    """
    matches = []
    matched_basenames = set()

    for table_key, config in table_definitions.items():
        csv_basename = Path(config['file']).stem

        if csv_basename in csv_files:
            matches.append((table_key, config, csv_files[csv_basename]))
            matched_basenames.add(csv_basename)

    # Report unmatched CSVs
    unmatched = set(csv_files.keys()) - matched_basenames
    if unmatched:
        logger.info(f"Skipped {len(unmatched)} CSV files (no table definition): {', '.join(sorted(unmatched))}")

    return matches


def validate_csv_schema(csv_path, primary_key, sort_key=None):
    """
    Validate that CSV contains required key columns.

    Args:
        csv_path: Path to CSV file
        primary_key: Primary key column name
        sort_key: Sort key column name (optional)

    Returns:
        Tuple (is_valid, columns, error_message)
    """
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames

            if not columns:
                return False, [], "CSV file is empty or has no headers"

            # Check for primary key
            if primary_key not in columns:
                return False, columns, f"Missing primary key column: {primary_key}"

            # Check for sort key if defined
            if sort_key and sort_key not in columns:
                return False, columns, f"Missing sort key column: {sort_key}"

            return True, columns, None

    except Exception as e:
        return False, [], f"Error reading CSV: {str(e)}"


def count_csv_rows(csv_path):
    """Count number of data rows in CSV file."""
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            return sum(1 for _ in csv.DictReader(f))
    except:
        return 0


def table_has_data(table_name):
    """Check if a DynamoDB table has existing data."""
    try:
        table = dynamodb.Table(table_name)
        response = table.scan(Limit=1, Select='COUNT')
        return response['Count'] > 0
    except:
        return False


def import_csv_to_table(csv_path, table_name, primary_key, sort_key=None, dry_run=False):
    """
    Import CSV data into DynamoDB table.

    Args:
        csv_path: Path to CSV file
        table_name: DynamoDB table name
        primary_key: Primary key column
        sort_key: Sort key column (optional)
        dry_run: If True, validate only (don't import)

    Returns:
        Dictionary with import statistics
    """
    stats = {
        'total_rows': 0,
        'uploaded': 0,
        'failed': 0,
        'errors': []
    }

    try:
        # Read CSV data
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            items = list(reader)

        stats['total_rows'] = len(items)

        if not items:
            logger.warning(f"  No data in {csv_path}")
            return stats

        if dry_run:
            logger.info(f"  [DRY RUN] Would import {len(items)} items")
            stats['uploaded'] = len(items)
            return stats

        # Get table reference
        table = dynamodb.Table(table_name)

        # Import in batches
        batch_size = 25  # DynamoDB batch write limit

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]

            with table.batch_writer() as writer:
                for item in batch:
                    try:
                        # Convert item values to DynamoDB types
                        dynamodb_item = {}
                        for key, value in item.items():
                            converted_value = convert_to_dynamodb_type(value)
                            if converted_value is not None:
                                dynamodb_item[key] = converted_value

                        # Ensure primary key exists
                        if primary_key not in dynamodb_item:
                            error_msg = f"Missing primary key '{primary_key}' in item"
                            stats['errors'].append(error_msg)
                            stats['failed'] += 1
                            continue

                        # Ensure sort key exists if defined
                        if sort_key and sort_key not in dynamodb_item:
                            error_msg = f"Missing sort key '{sort_key}' in item"
                            stats['errors'].append(error_msg)
                            stats['failed'] += 1
                            continue

                        writer.put_item(Item=dynamodb_item)
                        stats['uploaded'] += 1

                    except Exception as e:
                        error_msg = f"Error uploading item: {str(e)}"
                        stats['errors'].append(error_msg)
                        stats['failed'] += 1

        return stats

    except FileNotFoundError:
        logger.error(f"  File not found: {csv_path}")
        return stats
    except Exception as e:
        logger.error(f"  Error importing data: {str(e)}")
        return stats


def main():
    """Main entry point for the import tool."""
    parser = argparse.ArgumentParser(
        description='Import CSV data into DynamoDB tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Import all tables from default directories
  python3 import_csv_to_dynamodb.py

  # Dry run (validation only)
  python3 import_csv_to_dynamodb.py --dry-run

  # Import specific tables
  python3 import_csv_to_dynamodb.py --tables Passengers,Flights,Bookings

  # Skip tables with existing data
  python3 import_csv_to_dynamodb.py --skip-existing
        '''
    )

    parser.add_argument(
        '--tables',
        help='Comma-separated list of table names to import (default: all)',
        default=None
    )

    parser.add_argument(
        '--directory',
        help='Specific directory to scan for CSV files (default: output/ and database/output/)',
        default=None
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate schemas only, do not import data'
    )

    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip tables that already have data'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Set log level
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Print header
    print("=" * 80)
    print("DynamoDB CSV Import Tool")
    print("=" * 80)
    print()

    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity['Account']}")
        print(f"User: {identity['Arn'].split('/')[-1]}")
    except Exception as e:
        print(f"Error: AWS credentials not configured: {e}")
        print("Please run: aws configure")
        return 1

    # Get AWS region
    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    print(f"Region: {region}")
    print()

    if args.dry_run:
        print("MODE: DRY RUN (validation only, no data import)")
        print()

    # Discover CSV files
    if args.directory:
        directories = [args.directory]
    else:
        directories = ['output', 'database/output']

    print("Discovering CSV files...")
    csv_files = discover_csv_files(directories)
    print(f"✓ Found {len(csv_files)} CSV files")
    print()

    # Match CSVs to tables
    print("Matching CSVs to DynamoDB tables...")
    matches = match_csvs_to_tables(csv_files, TABLE_DEFINITIONS)
    print(f"✓ Matched {len(matches)} CSV files to {len(matches)} tables")
    print()

    # Filter by requested tables if specified
    if args.tables:
        requested_tables = set(args.tables.split(','))
        matches = [(k, c, p) for k, c, p in matches if c['table_name'] in requested_tables]
        print(f"Filtered to {len(matches)} requested tables")
        print()

    # Validate schemas
    print("Validating schemas...")
    validation_results = []
    for table_key, config, csv_path in matches:
        is_valid, columns, error = validate_csv_schema(
            csv_path,
            config['primary_key'],
            config['sort_key']
        )

        row_count = count_csv_rows(csv_path)

        if is_valid:
            print(f"✓ {config['table_name']}: {len(columns)} columns, {row_count} rows, PK={config['primary_key']}")
        else:
            print(f"✗ {config['table_name']}: {error}")

        validation_results.append((table_key, config, csv_path, is_valid, row_count))

    print()

    # Stop if there are validation errors
    invalid_count = sum(1 for _, _, _, is_valid, _ in validation_results if not is_valid)
    if invalid_count > 0:
        print(f"Error: {invalid_count} tables failed schema validation")
        return 1

    # Import data
    print("Importing data...")
    print()

    total_tables = len(validation_results)
    total_items_uploaded = 0
    total_errors = 0
    start_time = datetime.now()

    for idx, (table_key, config, csv_path, is_valid, row_count) in enumerate(validation_results, 1):
        table_name = config['table_name']

        # Check if table should be skipped
        if args.skip_existing and table_has_data(table_name):
            print(f"[{idx}/{total_tables}] {table_name}")
            print(f"  ⚠ Skipped (table already has data)")
            print()
            continue

        print(f"[{idx}/{total_tables}] {table_name} ({row_count} rows)")

        # Import data
        stats = import_csv_to_table(
            csv_path,
            table_name,
            config['primary_key'],
            config['sort_key'],
            dry_run=args.dry_run
        )

        # Report results
        if stats['uploaded'] > 0:
            print(f"  ✓ Uploaded {stats['uploaded']:,} items")
            total_items_uploaded += stats['uploaded']

        if stats['failed'] > 0:
            print(f"  ⚠ Failed: {stats['failed']} items")
            total_errors += stats['failed']

            # Show first few errors
            for error in stats['errors'][:3]:
                print(f"    - {error}")
            if len(stats['errors']) > 3:
                print(f"    ... and {len(stats['errors']) - 3} more errors")

        print()

    duration = datetime.now() - start_time

    # Print summary
    print("=" * 80)
    print("Import Summary")
    print("=" * 80)
    print(f"Total Tables: {total_tables}")
    print(f"Total Items Uploaded: {total_items_uploaded:,}")
    print(f"Total Errors: {total_errors}")
    print(f"Duration: {duration}")
    print()

    if total_errors == 0:
        print("✓ Import completed successfully!")
    else:
        print(f"⚠ Import completed with {total_errors} errors")

    print()
    print("View tables in AWS Console:")
    print(f"  https://console.aws.amazon.com/dynamodbv2/home?region={region}#tables")
    print()
    print("=" * 80)

    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
