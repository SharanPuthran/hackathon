#!/usr/bin/env python3
"""
Compare CSV files in output folder with DynamoDB tables

This script identifies:
1. CSV files that have corresponding DynamoDB tables
2. CSV files that are missing DynamoDB tables
3. DynamoDB tables that don't have CSV files
"""

import os
import boto3
import json
from pathlib import Path

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')


def get_csv_files():
    """Get all CSV files in output directory"""
    csv_files = []
    for file in os.listdir(OUTPUT_DIR):
        if file.endswith('.csv'):
            csv_files.append(file)
    return sorted(csv_files)


def get_dynamodb_tables():
    """Get all DynamoDB tables"""
    try:
        response = dynamodb.list_tables()
        return sorted(response.get('TableNames', []))
    except Exception as e:
        print(f"Error listing DynamoDB tables: {e}")
        return []


def get_table_item_count(table_name):
    """Get item count for a table"""
    try:
        response = dynamodb.describe_table(TableName=table_name)
        return response['Table'].get('ItemCount', 0)
    except Exception as e:
        return f"Error: {e}"


def get_csv_row_count(csv_file):
    """Get row count for a CSV file (excluding header)"""
    try:
        csv_path = os.path.join(OUTPUT_DIR, csv_file)
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Count lines minus header
            return sum(1 for _ in f) - 1
    except Exception as e:
        return f"Error: {e}"


def normalize_name(name):
    """Normalize table/file names for comparison"""
    # Remove .csv extension
    name = name.replace('.csv', '')
    # Remove common suffixes
    name = name.replace('_enriched', '')
    name = name.replace('_final', '')
    name = name.replace('_mel', '')
    name = name.replace('_scenario', '')
    # Convert to lowercase for comparison
    return name.lower()


def create_mapping():
    """Create mapping between CSV files and potential table names"""
    csv_to_table_mapping = {
        # Exact matches
        'flights_enriched_mel.csv': 'flights',
        'bookings.csv': 'bookings',
        'bookings_enriched.csv': 'bookings',
        'passengers_enriched_final.csv': 'passengers',
        'crew_members_enriched.csv': 'CrewMembers',
        'crew_members.csv': 'CrewMembers',
        'crew_roster_enriched.csv': 'CrewRoster',
        'crew_roster.csv': 'CrewRoster',
        'aircraft_availability_enriched_mel.csv': 'AircraftAvailability',
        'aircraft_maintenance_workorders.csv': 'MaintenanceWorkOrders',
        'maintenance_staff.csv': 'MaintenanceStaff',
        'maintenance_roster.csv': 'MaintenanceStaff',
        'cargo_flight_assignments.csv': 'CargoFlightAssignments',
        'cargo_shipments.csv': 'CargoShipments',
        'baggage.csv': 'Baggage',
        'weather.csv': 'Weather',
        'disruption_events.csv': 'disruption_events',
        'recovery_scenarios.csv': 'recovery_scenarios',
        'recovery_actions.csv': 'recovery_actions',
        'business_impact_assessment.csv': 'business_impact_assessment',
        'safety_constraints.csv': 'safety_constraints',
        
        # Additional files that might need tables
        'disrupted_passengers_scenario.csv': 'disrupted_passengers_scenario',
        'aircraft_swap_options.csv': 'aircraft_swap_options',
        'inbound_flight_impact.csv': 'inbound_flight_impact',
        'airport_slots.csv': 'airport_slots',
        'crew_documents.csv': 'crew_documents',
        'crew_payroll.csv': 'crew_payroll',
        'crew_training_records.csv': 'crew_training_records',
        'disruption_costs.csv': 'disruption_costs',
        'financial_parameters.csv': 'financial_parameters',
        'financial_transactions.csv': 'financial_transactions',
        'fuel_management.csv': 'fuel_management',
        'operational_kpis.csv': 'operational_kpis',
        'revenue_management.csv': 'revenue_management',
        'flights_enriched_scenarios.csv': 'flights',  # Duplicate/alternative
    }
    
    return csv_to_table_mapping


def main():
    """Main comparison logic"""
    print("\n" + "=" * 80)
    print("CSV FILES vs DYNAMODB TABLES COMPARISON")
    print("=" * 80)
    
    # Get data
    csv_files = get_csv_files()
    dynamodb_tables = get_dynamodb_tables()
    mapping = create_mapping()
    
    print(f"\n📊 Summary:")
    print(f"   CSV files found: {len(csv_files)}")
    print(f"   DynamoDB tables found: {len(dynamodb_tables)}")
    
    # Analysis 1: CSV files with tables
    print("\n" + "=" * 80)
    print("✅ CSV FILES WITH CORRESPONDING DYNAMODB TABLES")
    print("=" * 80)
    
    matched_csvs = []
    for csv_file in csv_files:
        expected_table = mapping.get(csv_file)
        if expected_table and expected_table in dynamodb_tables:
            csv_rows = get_csv_row_count(csv_file)
            table_items = get_table_item_count(expected_table)
            matched_csvs.append(csv_file)
            
            status = "✅" if csv_rows == table_items else "⚠️"
            print(f"{status} {csv_file:45} → {expected_table:30} (CSV: {csv_rows:6}, DB: {table_items:6})")
    
    # Analysis 2: CSV files WITHOUT tables
    print("\n" + "=" * 80)
    print("❌ CSV FILES MISSING DYNAMODB TABLES")
    print("=" * 80)
    
    missing_tables = []
    for csv_file in csv_files:
        expected_table = mapping.get(csv_file)
        if expected_table and expected_table not in dynamodb_tables:
            csv_rows = get_csv_row_count(csv_file)
            missing_tables.append((csv_file, expected_table, csv_rows))
            print(f"❌ {csv_file:45} → {expected_table:30} (CSV rows: {csv_rows:6})")
        elif not expected_table:
            csv_rows = get_csv_row_count(csv_file)
            print(f"⚠️  {csv_file:45} → No mapping defined      (CSV rows: {csv_rows:6})")
    
    # Analysis 3: DynamoDB tables without CSV files
    print("\n" + "=" * 80)
    print("⚠️  DYNAMODB TABLES WITHOUT CSV FILES")
    print("=" * 80)
    
    csv_table_names = set(mapping.values())
    orphaned_tables = []
    for table in dynamodb_tables:
        if table not in csv_table_names:
            table_items = get_table_item_count(table)
            orphaned_tables.append((table, table_items))
            print(f"⚠️  {table:30} (Items: {table_items:6})")
    
    # Analysis 4: Critical missing tables
    print("\n" + "=" * 80)
    print("🔴 CRITICAL MISSING TABLES (Referenced in constants.py)")
    print("=" * 80)
    
    critical_tables = [
        'passengers',  # Used by arbitrator
        'disrupted_passengers_scenario',  # Used for disruption scenarios
        'aircraft_swap_options',  # Used for recovery planning
        'inbound_flight_impact',  # Used for network analysis
    ]
    
    critical_missing = []
    for table in critical_tables:
        if table not in dynamodb_tables:
            # Find corresponding CSV
            csv_file = None
            for csv, tbl in mapping.items():
                if tbl == table:
                    csv_file = csv
                    break
            
            if csv_file:
                csv_rows = get_csv_row_count(csv_file)
                critical_missing.append((table, csv_file, csv_rows))
                print(f"🔴 {table:30} ← {csv_file:45} (CSV rows: {csv_rows:6})")
            else:
                print(f"🔴 {table:30} ← No CSV file found")
    
    # Summary Report
    print("\n" + "=" * 80)
    print("📋 SUMMARY REPORT")
    print("=" * 80)
    
    print(f"\n✅ Matched (CSV + Table): {len(matched_csvs)}")
    print(f"❌ Missing Tables: {len(missing_tables)}")
    print(f"⚠️  Orphaned Tables: {len(orphaned_tables)}")
    print(f"🔴 Critical Missing: {len(critical_missing)}")
    
    # Recommendations
    print("\n" + "=" * 80)
    print("💡 RECOMMENDATIONS")
    print("=" * 80)
    
    if critical_missing:
        print("\n🔴 HIGH PRIORITY - Add these critical tables:")
        for table, csv_file, rows in critical_missing:
            print(f"   • {table} (from {csv_file}, {rows} rows)")
    
    if missing_tables:
        print("\n⚠️  MEDIUM PRIORITY - Consider adding these tables:")
        for csv_file, table, rows in missing_tables:
            if table not in critical_tables:
                print(f"   • {table} (from {csv_file}, {rows} rows)")
    
    # Generate action items
    print("\n" + "=" * 80)
    print("📝 ACTION ITEMS")
    print("=" * 80)
    
    if critical_missing:
        print("\n1. Add critical tables to upload scripts:")
        print("   File: database/cleanup_and_upload_dynamodb.py")
        print("   File: database/async_import_dynamodb.py")
        print("\n   Tables to add:")
        for table, csv_file, rows in critical_missing:
            print(f"   • {table}")
        
        print("\n2. Run upload script to create and populate tables")
        print("\n3. Verify data integrity and foreign key relationships")
        print("\n4. Update validation scripts to include new tables")
    
    # Export results to JSON
    results = {
        'summary': {
            'csv_files': len(csv_files),
            'dynamodb_tables': len(dynamodb_tables),
            'matched': len(matched_csvs),
            'missing_tables': len(missing_tables),
            'orphaned_tables': len(orphaned_tables),
            'critical_missing': len(critical_missing)
        },
        'matched_csvs': matched_csvs,
        'missing_tables': [{'csv': csv, 'table': tbl, 'rows': rows} for csv, tbl, rows in missing_tables],
        'orphaned_tables': [{'table': tbl, 'items': items} for tbl, items in orphaned_tables],
        'critical_missing': [{'table': tbl, 'csv': csv, 'rows': rows} for tbl, csv, rows in critical_missing]
    }
    
    output_file = os.path.join(SCRIPT_DIR, 'csv_dynamodb_comparison.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {output_file}")
    
    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
