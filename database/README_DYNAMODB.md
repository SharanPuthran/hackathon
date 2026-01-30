# Upload Your Airline Data to AWS DynamoDB

## 🎉 Good News - AWS CLI Not Required!

You can upload all your CSV files to DynamoDB using Python boto3 directly. No need to troubleshoot AWS CLI installation!

## ✅ What You Already Have

- ✓ Python 3.12 installed
- ✓ boto3 (AWS SDK for Python) installed
- ✓ 16 CSV files with ~15,000 records ready
- ✓ All scripts created and ready to run

## 🚀 Quick Start (2 Commands)

### Step 1: Configure AWS Credentials

```powershell
py configure_aws_credentials.py
```

This will ask for:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)

### Step 2: Create Tables and Upload Data

```powershell
py create_dynamodb_tables.py
```

This will:
- Create 16 DynamoDB tables
- Upload ~15,000 items automatically
- Show progress and summary

**Done!** Your data is now in AWS DynamoDB.

## 🔑 Getting AWS Credentials

### Option 1: Create New IAM User (Recommended)

1. **Go to AWS Console**: https://console.aws.amazon.com/
2. **Navigate to IAM**: Search for "IAM" in the top search bar
3. **Create User**:
   - Click **Users** → **Create User**
   - Username: `airline-data-user`
   - Enable: **Programmatic access** (or **Access key**)
4. **Set Permissions**:
   - Click **Attach policies directly**
   - Search and select: `AmazonDynamoDBFullAccess`
   - (Optional) Also add: `AmazonS3FullAccess`
5. **Create and Download**:
   - Click through to create user
   - **Download CSV** with credentials
   - Or copy Access Key ID and Secret Access Key

### Option 2: Use Existing IAM User

1. Go to: AWS Console → IAM → Users
2. Click your username
3. Go to **Security Credentials** tab
4. Click **Create Access Key**
5. Select **Command Line Interface (CLI)**
6. Download or copy the credentials

### Option 3: Use AWS CloudShell (No Local Setup)

If you want to avoid local setup entirely:

1. Go to: https://console.aws.amazon.com/
2. Click **CloudShell** icon (terminal icon in top bar)
3. Upload your CSV files
4. Run the Python scripts directly in CloudShell

## 📊 What Gets Created

| Table Name | Records | Description |
|------------|---------|-------------|
| Passengers | 11,406 | Passenger records with enriched data |
| Flights | 256 | Flight records with MEL data |
| Weather | 456 | Weather forecasts (19 airports, 3 days) |
| AircraftAvailability | 168 | Aircraft availability with MEL status |
| DisruptedPassengers | 346 | Disruption scenario passengers |
| AircraftSwapOptions | 4 | Aircraft swap alternatives |
| InboundFlightImpact | 3 | Inbound flight impact scenarios |
| MaintenanceWorkOrders | ~100 | Maintenance work orders |
| Bookings | ~1,000 | Flight bookings |
| Baggage | ~1,000 | Baggage tracking |
| CrewMembers | ~100 | Crew information |
| CrewRoster | ~200 | Crew assignments |
| CargoShipments | ~100 | Cargo tracking |
| CargoFlightAssignments | ~100 | Cargo assignments |
| MaintenanceStaff | ~50 | Maintenance staff |
| MaintenanceRoster | ~100 | Maintenance roster |

**Total: 16 tables, ~15,000 items**

## 💰 Cost Estimate

- **Initial Upload**: ~$0.02 (one-time)
- **Monthly Storage**: ~$0.01 (50 MB)
- **Monthly Queries**: ~$0.003 (10,000 reads)

**Total: ~$0.05/month** (likely free tier!)

### AWS Free Tier Includes:
- 25 GB storage
- 25 write capacity units
- 25 read capacity units

Your usage will stay within free tier! 🎉

## 🔍 Query Your Data

### Python Examples:

```python
import boto3

dynamodb = boto3.resource('dynamodb')

# Get a specific passenger
passengers = dynamodb.Table('Passengers')
response = passengers.get_item(Key={'passenger_id': '22A00001111Z'})
print(response['Item'])

# Query weather for an airport
weather = dynamodb.Table('Weather')
response = weather.query(
    KeyConditionExpression='airport_code = :code',
    ExpressionAttributeValues={':code': 'AUH'}
)
print(f"Weather records: {len(response['Items'])}")

# Find VIP passengers
passengers = dynamodb.Table('Passengers')
response = passengers.scan(
    FilterExpression='passenger_category = :cat',
    ExpressionAttributeValues={':cat': 'VIP'}
)
print(f"VIP passengers: {len(response['Items'])}")

# Get disrupted passengers needing hotel
disrupted = dynamodb.Table('DisruptedPassengers')
response = disrupted.scan(
    FilterExpression='requires_hotel = :hotel',
    ExpressionAttributeValues={':hotel': 'Y'}
)
print(f"Passengers needing hotel: {len(response['Items'])}")

# Get aircraft swap options
swaps = dynamodb.Table('AircraftSwapOptions')
response = swaps.scan()
for option in response['Items']:
    print(f"{option['aircraft_registration']}: {option['swap_feasibility']}")
```

## 🌐 View in AWS Console

After upload, view your tables at:
https://console.aws.amazon.com/dynamodbv2/home#tables

You can:
- Browse all items
- Run queries
- View metrics
- Export data
- Set up alarms

## 📁 Files Created

| File | Purpose |
|------|---------|
| `configure_aws_credentials.py` | Configure AWS credentials |
| `create_dynamodb_tables.py` | Create tables and upload data |
| `quick_setup.ps1` | Automated setup script |
| `SETUP_WITHOUT_AWS_CLI.md` | Detailed guide |
| `README_DYNAMODB.md` | This file |

## 🔧 Troubleshooting

### "Unable to locate credentials"
```powershell
py configure_aws_credentials.py
```

### "Access Denied"
- Check IAM user has `AmazonDynamoDBFullAccess` policy
- Verify credentials are correct

### "boto3 not found"
```powershell
py -m pip install boto3
```

### "Table already exists"
- Normal if running multiple times
- Script will skip existing tables
- To recreate: Delete table in AWS Console first

## 🎯 Use Cases

1. **Disruption Management**
   - Query disrupted passengers
   - Check aircraft swap options
   - Monitor weather impacts

2. **Passenger Services**
   - Look up passenger details
   - Check VIP/influencer status
   - View connection information

3. **Operations**
   - Track aircraft availability
   - Monitor maintenance schedules
   - Analyze flight data

4. **Analytics**
   - Customer value analysis
   - Disruption impact reports
   - Weather pattern analysis

## 📚 Documentation

- **Detailed Setup**: `SETUP_WITHOUT_AWS_CLI.md`
- **DynamoDB Guide**: `DYNAMODB_SETUP_GUIDE.md`
- **Quick Reference**: `DYNAMODB_QUICK_START.md`

## 🆘 Support Resources

- **boto3 Docs**: https://boto3.amazonaws.com/v1/documentation/api/latest/
- **DynamoDB Docs**: https://docs.aws.amazon.com/dynamodb/
- **IAM User Guide**: https://docs.aws.amazon.com/IAM/latest/UserGuide/
- **AWS Free Tier**: https://aws.amazon.com/free/

## ✅ Quick Checklist

- [ ] Get AWS credentials (Access Key ID + Secret Key)
- [ ] Run `py configure_aws_credentials.py`
- [ ] Run `py create_dynamodb_tables.py`
- [ ] Verify tables in AWS Console
- [ ] Test queries with Python

## 🚀 Alternative: One-Command Setup

```powershell
.\quick_setup.ps1
```

This interactive script will:
1. Check prerequisites
2. Guide you through credential configuration
3. Offer to create tables and upload data
4. All in one go!

---

**Ready to start?** Run: `py configure_aws_credentials.py`

**Need help?** Read: `SETUP_WITHOUT_AWS_CLI.md`
