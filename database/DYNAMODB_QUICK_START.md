# DynamoDB Quick Start

## 🚀 Fast Track Setup

### Step 1: Check Prerequisites

```powershell
.\setup_dynamodb.ps1
```

This will check:
- ✓ Python installed
- ✓ AWS CLI installed
- ✓ AWS credentials configured
- ✓ boto3 library installed

### Step 2: Create Tables and Upload Data

```powershell
py create_dynamodb_tables.py
```

This will:
- Create 16 DynamoDB tables
- Upload ~15,000 items from CSV files
- Show progress and summary

**That's it!** Your data is now in DynamoDB.

## 📊 What Gets Created

| Table | Records | Key |
|-------|---------|-----|
| Passengers | 11,406 | passenger_id |
| Flights | 256 | flight_id |
| Weather | 456 | airport_code + forecast_time_zulu |
| AircraftAvailability | 168 | aircraft_registration + availability_start |
| DisruptedPassengers | 346 | passenger_id |
| + 11 more tables | ~2,000 | various |

**Total: 16 tables, ~15,000 items**

## 🔍 Quick Queries

### AWS CLI:

```powershell
# List all tables
aws dynamodb list-tables

# Get a passenger
aws dynamodb get-item --table-name Passengers --key '{\"passenger_id\":{\"S\":\"22A00001111Z\"}}'

# Scan for VIP passengers
aws dynamodb scan --table-name Passengers --filter-expression "passenger_category = :cat" --expression-attribute-values '{\":cat\":{\"S\":\"VIP\"}}'

# Get weather for AUH
aws dynamodb query --table-name Weather --key-condition-expression "airport_code = :code" --expression-attribute-values '{\":code\":{\"S\":\"AUH\"}}'
```

### Python:

```python
import boto3

dynamodb = boto3.resource('dynamodb')

# Get passenger
table = dynamodb.Table('Passengers')
response = table.get_item(Key={'passenger_id': '22A00001111Z'})
print(response['Item'])

# Query weather
table = dynamodb.Table('Weather')
response = table.query(
    KeyConditionExpression='airport_code = :code',
    ExpressionAttributeValues={':code': 'AUH'}
)
print(response['Items'])
```

## 🌐 View in AWS Console

https://console.aws.amazon.com/dynamodbv2/home#tables

## 💰 Cost

**Estimated: $0.05/month** (likely free tier!)

- Initial upload: ~$0.02 (one-time)
- Storage: ~$0.01/month
- Queries: ~$0.003/month

## 📚 Files Created

- `create_dynamodb_tables.py` - Main script (Python)
- `create_dynamodb_tables.ps1` - Alternative (PowerShell)
- `setup_dynamodb.ps1` - Prerequisites checker
- `DYNAMODB_SETUP_GUIDE.md` - Comprehensive guide
- `DYNAMODB_QUICK_START.md` - This file

## ⚠️ Prerequisites

1. **Python** - Already installed ✓
2. **AWS CLI** - Run `.\setup_aws.ps1` if needed
3. **AWS Credentials** - Run `aws configure`
4. **boto3** - Run `py -m pip install boto3`

## 🔧 Troubleshooting

**"boto3 not found"**
```powershell
py -m pip install boto3
```

**"Unable to locate credentials"**
```powershell
aws configure
```

**"Table already exists"**
- Normal if running multiple times
- Script will skip existing tables

## 📖 Full Documentation

Read `DYNAMODB_SETUP_GUIDE.md` for:
- Detailed table schemas
- Advanced queries
- Integration examples
- Best practices
- Cost optimization

---

**Ready?** Run: `.\setup_dynamodb.ps1` then `py create_dynamodb_tables.py`
