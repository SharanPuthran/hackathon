# DynamoDB Import Script

## Overview

`async_import_dynamodb.py` is an async script that cleans up existing DynamoDB tables and imports CSV data from the `database/output` directory.

## Features

- **Async Operations**: All table operations run concurrently for maximum performance
- **Clean Slate**: Deletes all existing tables before creating new ones
- **Batch Uploads**: Uploads data in concurrent batches (25 items per batch)
- **Verification**: Validates all tables and counts items after import
- **Error Handling**: Gracefully handles missing files and conversion errors

## Requirements

```bash
pip install aioboto3 pandas boto3
```

## Usage

```bash
cd database
python3 async_import_dynamodb.py
```

## What It Does

1. **Cleanup**: Deletes all existing DynamoDB tables concurrently
2. **Create & Upload**: Creates 16 tables and uploads CSV data in parallel
3. **Verify**: Scans all tables to confirm data was imported

## Tables Created

- `flights` - Flight schedules and status
- `bookings` - Passenger bookings
- `CrewMembers` - Crew member details
- `CrewRoster` - Crew assignments
- `AircraftAvailability` - Aircraft status and MEL items
- `disruption_events` - Disruption event records
- `recovery_scenarios` - Recovery scenario options
- `recovery_actions` - Recovery action details
- `Weather` - Weather data
- `Baggage` - Baggage tracking
- `CargoShipments` - Cargo shipment details
- `CargoFlightAssignments` - Cargo-to-flight assignments
- `MaintenanceStaff` - Maintenance personnel roster
- `MaintenanceWorkOrders` - Maintenance work orders
- `business_impact_assessment` - Business impact data
- `safety_constraints` - Safety constraint records

## Performance

The async implementation processes all 16 tables concurrently:

- Typical runtime: 30-60 seconds
- Handles 20,000+ items across all tables
- Concurrent batch writes for optimal throughput

## Configuration

Table definitions are in the `TABLE_CONFIGS` dictionary. Each table specifies:

- CSV file name
- Key schema (partition key)
- Attribute definitions
- Key field name

## Error Handling

- Missing CSV files are skipped with a warning
- Invalid items (missing key field) are counted as errors
- Table creation failures are reported but don't stop other tables
- Final summary shows success/error counts
