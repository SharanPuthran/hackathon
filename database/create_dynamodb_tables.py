import boto3
import csv
import json
import decimal
from decimal import Decimal
from datetime import datetime

"""
Create DynamoDB tables and upload CSV data
This script will:
1. Create DynamoDB tables for each CSV file
2. Define appropriate primary keys
3. Upload all data from CSV files
"""

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')

# Table definitions with primary keys
TABLE_DEFINITIONS = {
    'passengers_enriched_final': {
        'file': 'output/passengers_enriched_final.csv',
        'table_name': 'Passengers',
        'primary_key': 'passenger_id',
        'sort_key': None,
        'description': 'Passenger records with enriched data'
    },
    'flights_enriched_mel': {
        'file': 'output/flights_enriched_mel.csv',
        'table_name': 'Flights',
        'primary_key': 'flight_id',
        'sort_key': None,
        'description': 'Flight records with MEL data'
    },
    'aircraft_availability_enriched_mel': {
        'file': 'output/aircraft_availability_enriched_mel.csv',
        'table_name': 'AircraftAvailability',
        'primary_key': 'aircraftRegistration',
        'sort_key': 'valid_from_zulu',
        'description': 'Aircraft availability with MEL status'
    },
    'aircraft_maintenance_workorders': {
        'file': 'output/aircraft_maintenance_workorders.csv',
        'table_name': 'MaintenanceWorkOrders',
        'primary_key': 'workorder_id',
        'sort_key': None,
        'description': 'Aircraft maintenance work orders'
    },
    'weather': {
        'file': 'output/weather.csv',
        'table_name': 'Weather',
        'primary_key': 'airport_code',
        'sort_key': 'forecast_time_zulu',
        'description': 'Weather forecasts for airports'
    },
    'disrupted_passengers_scenario': {
        'file': 'output/disrupted_passengers_scenario.csv',
        'table_name': 'DisruptedPassengers',
        'primary_key': 'passenger_id',
        'sort_key': None,
        'description': 'Disruption scenario passenger data'
    },
    'aircraft_swap_options': {
        'file': 'output/aircraft_swap_options.csv',
        'table_name': 'AircraftSwapOptions',
        'primary_key': 'aircraft_registration',
        'sort_key': None,
        'description': 'Aircraft swap options for disruptions'
    },
    'inbound_flight_impact': {
        'file': 'output/inbound_flight_impact.csv',
        'table_name': 'InboundFlightImpact',
        'primary_key': 'scenario',
        'sort_key': None,
        'description': 'Inbound flight impact analysis'
    },
    'bookings': {
        'file': 'output/bookings.csv',
        'table_name': 'Bookings',
        'primary_key': 'booking_id',
        'sort_key': None,
        'description': 'Flight bookings'
    },
    'baggage': {
        'file': 'output/baggage.csv',
        'table_name': 'Baggage',
        'primary_key': 'baggage_tag',
        'sort_key': None,
        'description': 'Baggage tracking'
    },
    'crew_members': {
        'file': 'output/crew_members.csv',
        'table_name': 'CrewMembers',
        'primary_key': 'crew_id',
        'sort_key': None,
        'description': 'Crew member information'
    },
    'crew_roster': {
        'file': 'output/crew_roster.csv',
        'table_name': 'CrewRoster',
        'primary_key': 'roster_id',
        'sort_key': None,
        'description': 'Crew roster assignments'
    },
    'cargo_shipments': {
        'file': 'output/cargo_shipments.csv',
        'table_name': 'CargoShipments',
        'primary_key': 'shipment_id',
        'sort_key': None,
        'description': 'Cargo shipment tracking'
    },
    'cargo_flight_assignments': {
        'file': 'output/cargo_flight_assignments.csv',
        'table_name': 'CargoFlightAssignments',
        'primary_key': 'assignment_id',
        'sort_key': None,
        'description': 'Cargo to flight assignments'
    },
    'maintenance_staff': {
        'file': 'output/maintenance_staff.csv',
        'table_name': 'MaintenanceStaff',
        'primary_key': 'staff_id',
        'sort_key': None,
        'description': 'Maintenance staff information'
    },
    'maintenance_roster': {
        'file': 'output/maintenance_roster.csv',
        'table_name': 'MaintenanceRoster',
        'primary_key': 'roster_id',
        'sort_key': None,
        'description': 'Maintenance staff roster'
    },
    'return_flight_impact': {
        'file': 'output/return_flight_impact.csv',
        'table_name': 'ReturnFlightImpact',
        'primary_key': 'scenario',
        'sort_key': None,
        'description': 'Return flight delay impact analysis'
    }
}

def convert_to_dynamodb_type(value):
    """Convert Python types to DynamoDB compatible types"""
    if value == '' or value is None:
        return None
    
    # Try to convert to number
    try:
        if '.' in str(value):
            return Decimal(str(value))
        else:
            return int(value)
    except (ValueError, decimal.InvalidOperation):
        pass
    
    # Return as string
    return str(value)

def create_table(table_name, primary_key, sort_key=None):
    """Create a DynamoDB table"""
    try:
        # Check if table already exists
        existing_tables = dynamodb_client.list_tables()['TableNames']
        if table_name in existing_tables:
            print(f"  ⚠ Table '{table_name}' already exists, skipping creation")
            return True
        
        # Define key schema
        key_schema = [
            {'AttributeName': primary_key, 'KeyType': 'HASH'}
        ]
        
        attribute_definitions = [
            {'AttributeName': primary_key, 'AttributeType': 'S'}
        ]
        
        if sort_key:
            key_schema.append({'AttributeName': sort_key, 'KeyType': 'RANGE'})
            attribute_definitions.append({'AttributeName': sort_key, 'AttributeType': 'S'})
        
        # Create table
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode='PAY_PER_REQUEST'  # On-demand pricing
        )
        
        # Wait for table to be created
        print(f"  Creating table '{table_name}'...", end='', flush=True)
        table.wait_until_exists()
        print(" ✓ Created")
        return True
        
    except Exception as e:
        print(f"  ✗ Error creating table '{table_name}': {e}")
        return False

def upload_csv_to_dynamodb(csv_file, table_name, primary_key, sort_key=None):
    """Upload CSV data to DynamoDB table"""
    try:
        table = dynamodb.Table(table_name)
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            items = list(reader)
        
        if not items:
            print(f"  ⚠ No data in {csv_file}")
            return 0
        
        # Upload in batches
        batch_size = 25  # DynamoDB batch write limit
        uploaded_count = 0
        failed_count = 0
        
        print(f"  Uploading {len(items)} items...", end='', flush=True)
        
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
                            print(f"\n  ✗ Missing primary key '{primary_key}' in item")
                            failed_count += 1
                            continue
                        
                        writer.put_item(Item=dynamodb_item)
                        uploaded_count += 1
                        
                    except Exception as e:
                        print(f"\n  ✗ Error uploading item: {e}")
                        failed_count += 1
        
        print(f" ✓ Uploaded {uploaded_count} items")
        if failed_count > 0:
            print(f"  ⚠ Failed: {failed_count} items")
        
        return uploaded_count
        
    except FileNotFoundError:
        print(f"  ✗ File not found: {csv_file}")
        return 0
    except Exception as e:
        print(f"  ✗ Error uploading data: {e}")
        return 0

def main():
    print("=" * 80)
    print("DynamoDB Table Creation and Data Upload")
    print("=" * 80)
    print()
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"✓ AWS Account: {identity['Account']}")
        print(f"✓ User: {identity['Arn']}")
        print()
    except Exception as e:
        print(f"✗ AWS credentials not configured: {e}")
        print("  Please run: aws configure")
        return
    
    # Get AWS region
    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    print(f"✓ Region: {region}")
    print()
    
    total_tables = len(TABLE_DEFINITIONS)
    created_tables = 0
    uploaded_items = 0
    
    print(f"Processing {total_tables} tables...")
    print()
    
    for key, config in TABLE_DEFINITIONS.items():
        print(f"[{created_tables + 1}/{total_tables}] {config['table_name']}")
        print(f"  Description: {config['description']}")
        print(f"  Primary Key: {config['primary_key']}", end='')
        if config['sort_key']:
            print(f", Sort Key: {config['sort_key']}")
        else:
            print()
        
        # Create table
        if create_table(config['table_name'], config['primary_key'], config['sort_key']):
            created_tables += 1
            
            # Upload data
            count = upload_csv_to_dynamodb(
                config['file'],
                config['table_name'],
                config['primary_key'],
                config['sort_key']
            )
            uploaded_items += count
        
        print()
    
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Tables Created/Verified: {created_tables}/{total_tables}")
    print(f"Total Items Uploaded: {uploaded_items:,}")
    print()
    print("View tables in AWS Console:")
    print(f"  https://console.aws.amazon.com/dynamodbv2/home?region={region}#tables")
    print()
    print("Query example (AWS CLI):")
    print("  aws dynamodb scan --table-name Passengers --limit 10")
    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
