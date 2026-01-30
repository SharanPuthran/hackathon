# DynamoDB Setup Guide

## Overview

This guide will help you create DynamoDB tables and upload all your airline data CSV files to AWS DynamoDB.

## What is DynamoDB?

Amazon DynamoDB is a fully managed NoSQL database service that provides fast and predictable performance with seamless scalability. Perfect for your airline disruption management system.

## Prerequisites

1. ✓ AWS CLI installed and configured
2. ✓ AWS credentials set up (`aws configure`)
3. ✓ Python 3.x with boto3 library

## Tables to be Created

| Table Name | Primary Key | Sort Key | Records | Description |
|------------|-------------|----------|---------|-------------|
| Passengers | passenger_id | - | 11,406 | Passenger records with enriched data |
| Flights | flight_id | - | 256 | Flight records with MEL data |
| AircraftAvailability | aircraft_registration | availability_start | 168 | Aircraft availability with MEL status |
| MaintenanceWorkOrders | workorder_id | - | ~100 | Aircraft maintenance work orders |
| Weather | airport_code | forecast_time_zulu | 456 | Weather forecasts for 19 airports |
| DisruptedPassengers | passenger_id | - | 346 | Disruption scenario passenger data |
| AircraftSwapOptions | aircraft_registration | - | 4 | Aircraft swap options |
| InboundFlightImpact | scenario | - | 3 | Inbound flight impact analysis |
| Bookings | booking_id | - | ~1000 | Flight bookings |
| Baggage | baggage_tag | - | ~1000 | Baggage tracking |
| CrewMembers | crew_id | - | ~100 | Crew member information |
| CrewRoster | roster_id | - | ~200 | Crew roster assignments |
| CargoShipments | shipment_id | - | ~100 | Cargo shipment tracking |
| CargoFlightAssignments | assignment_id | - | ~100 | Cargo to flight assignments |
| MaintenanceStaff | staff_id | - | ~50 | Maintenance staff information |
| MaintenanceRoster | roster_id | - | ~100 | Maintenance staff roster |

**Total: 16 tables, ~15,000+ items**

## Installation Steps

### Step 1: Install boto3 (Python AWS SDK)

```powershell
pip install boto3
```

Or if using Python 3:

```powershell
pip3 install boto3
```

Or using py:

```powershell
py -m pip install boto3
```

### Step 2: Verify AWS Configuration

```powershell
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAI...",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-username"
}
```

### Step 3: Choose Your Method

#### Method A: Python Script (Recommended - Creates Tables + Uploads Data)

```powershell
py create_dynamodb_tables.py
```

This will:
- ✓ Create all 16 DynamoDB tables
- ✓ Upload all CSV data automatically
- ✓ Handle data type conversions
- ✓ Use batch writes for efficiency
- ✓ Show progress and summary

#### Method B: PowerShell Script (Creates Tables Only)

```powershell
.\create_dynamodb_tables.ps1
```

Then upload data using Python script:
```powershell
py create_dynamodb_tables.py
```

#### Method C: AWS Console (Manual)

1. Go to: https://console.aws.amazon.com/dynamodbv2/
2. Click "Create table"
3. Enter table name and keys
4. Choose "On-demand" billing mode
5. Click "Create table"
6. Repeat for each table

## Step 4: Verify Tables Created

### Using AWS CLI:

```powershell
# List all tables
aws dynamodb list-tables

# Describe a specific table
aws dynamodb describe-table --table-name Passengers

# Count items in a table
aws dynamodb scan --table-name Passengers --select COUNT

# Get sample items
aws dynamodb scan --table-name Passengers --limit 5
```

### Using AWS Console:

1. Go to: https://console.aws.amazon.com/dynamodbv2/
2. Click on "Tables" in the left menu
3. You should see all 16 tables listed
4. Click on any table to view items

## Step 5: Query Your Data

### Example Queries (AWS CLI):

```powershell
# Get a specific passenger
aws dynamodb get-item `
  --table-name Passengers `
  --key '{\"passenger_id\": {\"S\": \"22A00001111Z\"}}'

# Scan for VIP passengers
aws dynamodb scan `
  --table-name Passengers `
  --filter-expression \"passenger_category = :cat\" `
  --expression-attribute-values '{\":cat\":{\"S\":\"VIP\"}}'

# Get weather for a specific airport
aws dynamodb query `
  --table-name Weather `
  --key-condition-expression \"airport_code = :code\" `
  --expression-attribute-values '{\":code\":{\"S\":\"AUH\"}}'

# Get flights with MEL
aws dynamodb scan `
  --table-name Flights `
  --filter-expression \"mel_status = :status\" `
  --expression-attribute-values '{\":status\":{\"S\":\"ACTIVE\"}}'
```

### Example Queries (Python with boto3):

```python
import boto3

dynamodb = boto3.resource('dynamodb')

# Get a passenger
passengers_table = dynamodb.Table('Passengers')
response = passengers_table.get_item(
    Key={'passenger_id': '22A00001111Z'}
)
passenger = response.get('Item')
print(passenger)

# Query weather for an airport
weather_table = dynamodb.Table('Weather')
response = weather_table.query(
    KeyConditionExpression='airport_code = :code',
    ExpressionAttributeValues={':code': 'AUH'}
)
weather_records = response['Items']
print(f"Found {len(weather_records)} weather records")

# Scan for disrupted passengers
disrupted_table = dynamodb.Table('DisruptedPassengers')
response = disrupted_table.scan(
    FilterExpression='has_connection = :conn',
    ExpressionAttributeValues={':conn': 'Y'}
)
passengers_with_connections = response['Items']
print(f"Passengers with connections: {len(passengers_with_connections)}")

# Get aircraft swap options
swap_table = dynamodb.Table('AircraftSwapOptions')
response = swap_table.scan()
swap_options = response['Items']
for option in swap_options:
    print(f"{option['aircraft_registration']}: {option['swap_feasibility']}")
```

## Cost Estimation

### DynamoDB Pricing (On-Demand Mode):

- **Write requests**: $1.25 per million write request units
- **Read requests**: $0.25 per million read request units
- **Storage**: $0.25 per GB-month

### Estimated Costs for Your Data:

**Initial Upload (~15,000 items):**
- Write cost: ~$0.02 (one-time)

**Monthly Storage (~50 MB):**
- Storage cost: ~$0.01/month

**Monthly Queries (assuming 10,000 reads):**
- Read cost: ~$0.003/month

**Total Estimated Cost: ~$0.05/month** (very minimal!)

### Free Tier:

AWS Free Tier includes:
- 25 GB of storage
- 25 write capacity units
- 25 read capacity units

Your usage will likely stay within the free tier!

## Table Schema Details

### Passengers Table
```
Primary Key: passenger_id (String)
Attributes:
  - first_name, last_name
  - passenger_category (Regular/VIP/VVIP)
  - is_influencer (Y/N)
  - customer_value_score (Decimal)
  - flight_number
  - aircraft_type, aircraft_registration
  - departure_airport, arrival_airport
  - profession, preferred_language
  - meal_preference, beverage_preference
  - pnr, traveler_id
  - and more...
```

### Flights Table
```
Primary Key: flight_id (String)
Attributes:
  - flight_number
  - aircraft_type, aircraft_registration
  - origin_airport, destination_airport
  - departure_time, arrival_time
  - mel_status, mel_category, mel_item
  - upline/downline flight information
  - and more...
```

### Weather Table
```
Primary Key: airport_code (String)
Sort Key: forecast_time_zulu (String)
Attributes:
  - condition (Clear, Cloudy, Rain, etc.)
  - temperature_c, visibility_km
  - wind_speed_kts, wind_direction
  - precipitation_mm_per_hour
  - operational_impact
  - runway_condition
  - and more...
```

### AircraftAvailability Table
```
Primary Key: aircraft_registration (String)
Sort Key: availability_start (String)
Attributes:
  - availability_status (AVAILABLE/AOG/MAINT)
  - mel_status, mel_category
  - mel_dispatch_impact
  - availability_end
  - and more...
```

## Advanced Operations

### Create Global Secondary Index (GSI)

If you need to query by attributes other than the primary key:

```powershell
aws dynamodb update-table `
  --table-name Passengers `
  --attribute-definitions AttributeName=flight_number,AttributeType=S `
  --global-secondary-index-updates `
    '[{\"Create\":{\"IndexName\":\"FlightNumberIndex\",\"KeySchema\":[{\"AttributeName\":\"flight_number\",\"KeyType\":\"HASH\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}}]'
```

### Enable Point-in-Time Recovery

```powershell
aws dynamodb update-continuous-backups `
  --table-name Passengers `
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

### Export Table to S3

```powershell
aws dynamodb export-table-to-point-in-time `
  --table-arn arn:aws:dynamodb:REGION:ACCOUNT:table/Passengers `
  --s3-bucket my-backup-bucket `
  --export-format DYNAMODB_JSON
```

## Integration with Your Application

### Python Example (Flask API):

```python
from flask import Flask, jsonify
import boto3

app = Flask(__name__)
dynamodb = boto3.resource('dynamodb')

@app.route('/passengers/<passenger_id>')
def get_passenger(passenger_id):
    table = dynamodb.Table('Passengers')
    response = table.get_item(Key={'passenger_id': passenger_id})
    return jsonify(response.get('Item', {}))

@app.route('/weather/<airport_code>')
def get_weather(airport_code):
    table = dynamodb.Table('Weather')
    response = table.query(
        KeyConditionExpression='airport_code = :code',
        ExpressionAttributeValues={':code': airport_code},
        Limit=10
    )
    return jsonify(response['Items'])

@app.route('/disruption/passengers')
def get_disrupted_passengers():
    table = dynamodb.Table('DisruptedPassengers')
    response = table.scan(
        FilterExpression='requires_hotel = :hotel',
        ExpressionAttributeValues={':hotel': 'Y'}
    )
    return jsonify(response['Items'])

if __name__ == '__main__':
    app.run(debug=True)
```

### Node.js Example:

```javascript
const AWS = require('aws-sdk');
const dynamodb = new AWS.DynamoDB.DocumentClient();

// Get passenger
async function getPassenger(passengerId) {
  const params = {
    TableName: 'Passengers',
    Key: { passenger_id: passengerId }
  };
  const result = await dynamodb.get(params).promise();
  return result.Item;
}

// Query weather
async function getWeather(airportCode) {
  const params = {
    TableName: 'Weather',
    KeyConditionExpression: 'airport_code = :code',
    ExpressionAttributeValues: { ':code': airportCode }
  };
  const result = await dynamodb.query(params).promise();
  return result.Items;
}
```

## Troubleshooting

### Error: "boto3 not found"
```powershell
py -m pip install boto3
```

### Error: "Unable to locate credentials"
```powershell
aws configure
```

### Error: "Table already exists"
- This is normal if you run the script multiple times
- The script will skip existing tables
- To recreate, delete the table first:
```powershell
aws dynamodb delete-table --table-name TableName
```

### Error: "ResourceNotFoundException"
- Table doesn't exist yet
- Run the creation script first

### Error: "ProvisionedThroughputExceededException"
- You're making too many requests
- Add delays between requests
- Or switch to on-demand billing mode

## Best Practices

1. **Use On-Demand Billing** for unpredictable workloads
2. **Enable Point-in-Time Recovery** for important tables
3. **Use GSIs** for additional query patterns
4. **Implement pagination** for large result sets
5. **Use batch operations** for multiple items
6. **Monitor costs** in AWS Cost Explorer
7. **Set up CloudWatch alarms** for unusual activity
8. **Use IAM roles** instead of access keys when possible

## Monitoring and Maintenance

### View Metrics in CloudWatch:

1. Go to: https://console.aws.amazon.com/cloudwatch/
2. Click "Metrics" → "DynamoDB"
3. View:
   - Read/Write capacity units
   - Throttled requests
   - System errors
   - User errors

### Set Up Alarms:

```powershell
aws cloudwatch put-metric-alarm `
  --alarm-name HighReadCapacity `
  --alarm-description "Alert when read capacity is high" `
  --metric-name ConsumedReadCapacityUnits `
  --namespace AWS/DynamoDB `
  --statistic Sum `
  --period 300 `
  --threshold 1000 `
  --comparison-operator GreaterThanThreshold
```

## Next Steps

1. ✓ Create tables using Python script
2. ✓ Verify data uploaded successfully
3. ✓ Test queries using AWS CLI or Console
4. ✓ Build API endpoints to access data
5. ✓ Integrate with your disruption management application
6. ✓ Set up monitoring and alarms
7. ✓ Implement backup strategy

## Support Resources

- **DynamoDB Documentation**: https://docs.aws.amazon.com/dynamodb/
- **Boto3 Documentation**: https://boto3.amazonaws.com/v1/documentation/api/latest/
- **DynamoDB Best Practices**: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html
- **Pricing Calculator**: https://calculator.aws/

---

**Ready to start?** Run: `py create_dynamodb_tables.py`
