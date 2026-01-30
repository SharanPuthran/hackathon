# Setup DynamoDB Without AWS CLI

## Good News!

You don't actually need AWS CLI to upload your data to DynamoDB. Since you already have **boto3** installed, you can configure AWS credentials directly and use Python scripts!

## Quick Setup (3 Steps)

### Step 1: Get AWS Credentials

You need two things from AWS:
1. **AWS Access Key ID**
2. **AWS Secret Access Key**

#### How to Get Them:

**Option A: Create New IAM User (Recommended)**

1. Go to AWS Console: https://console.aws.amazon.com/
2. Sign in with your AWS account
3. Go to **IAM** service (search for "IAM" in the top search bar)
4. Click **Users** in the left menu
5. Click **Add User** (or **Create User**)
6. Enter username: `airline-data-user`
7. Select **Access key - Programmatic access**
8. Click **Next: Permissions**
9. Click **Attach existing policies directly**
10. Search and select these policies:
    - `AmazonDynamoDBFullAccess`
    - `AmazonS3FullAccess` (optional, for S3 uploads)
11. Click **Next** through remaining screens
12. Click **Create User**
13. **IMPORTANT**: Download the CSV file or copy the credentials
    - Access Key ID: `AKIAIOSFODNN7EXAMPLE`
    - Secret Access Key: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`

**Option B: Use Existing IAM User**

1. Go to AWS Console → IAM → Users
2. Click on your username
3. Go to **Security Credentials** tab
4. Click **Create Access Key**
5. Select **Command Line Interface (CLI)**
6. Click **Next** → **Create Access Key**
7. Download or copy the credentials

### Step 2: Configure Credentials

Run this Python script:

```powershell
py configure_aws_credentials.py
```

It will ask for:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Output format (just press Enter for `json`)

The script will:
- Save credentials to `~/.aws/credentials`
- Save config to `~/.aws/config`
- Test the connection
- Show your AWS account info

### Step 3: Create DynamoDB Tables

```powershell
py create_dynamodb_tables.py
```

This will:
- Create 16 DynamoDB tables
- Upload ~15,000 items from your CSV files
- Show progress and summary

**That's it!** No AWS CLI needed!

## Alternative: Manual Configuration

If you prefer to configure manually:

### Create credentials file:

1. Create folder: `C:\Users\YOUR_USERNAME\.aws\`
2. Create file: `credentials` (no extension)
3. Add content:

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY_ID
aws_secret_access_key = YOUR_SECRET_ACCESS_KEY
```

### Create config file:

1. In same folder: `C:\Users\YOUR_USERNAME\.aws\`
2. Create file: `config` (no extension)
3. Add content:

```ini
[default]
region = us-east-1
output = json
```

## Verify Configuration

Test your credentials with Python:

```python
import boto3

# Test connection
sts = boto3.client('sts')
identity = sts.get_caller_identity()

print(f"Account: {identity['Account']}")
print(f"User: {identity['Arn']}")
print("✓ Credentials working!")
```

Or run:

```powershell
py -c "import boto3; sts = boto3.client('sts'); print(sts.get_caller_identity())"
```

## AWS Regions

Choose a region close to you:

| Region Code | Location |
|-------------|----------|
| us-east-1 | US East (N. Virginia) |
| us-west-2 | US West (Oregon) |
| eu-west-1 | Europe (Ireland) |
| eu-central-1 | Europe (Frankfurt) |
| ap-south-1 | Asia Pacific (Mumbai) |
| ap-southeast-1 | Asia Pacific (Singapore) |
| ap-northeast-1 | Asia Pacific (Tokyo) |

## What Gets Created

When you run `py create_dynamodb_tables.py`:

### 16 DynamoDB Tables:

1. **Passengers** - 11,406 records
2. **Flights** - 256 records
3. **Weather** - 456 records (19 airports)
4. **AircraftAvailability** - 168 records
5. **DisruptedPassengers** - 346 records
6. **AircraftSwapOptions** - 4 records
7. **InboundFlightImpact** - 3 scenarios
8. **MaintenanceWorkOrders** - ~100 records
9. **Bookings** - ~1,000 records
10. **Baggage** - ~1,000 records
11. **CrewMembers** - ~100 records
12. **CrewRoster** - ~200 records
13. **CargoShipments** - ~100 records
14. **CargoFlightAssignments** - ~100 records
15. **MaintenanceStaff** - ~50 records
16. **MaintenanceRoster** - ~100 records

**Total: ~15,000 items**

## Cost

- **Initial upload**: ~$0.02 (one-time)
- **Monthly storage**: ~$0.01
- **Monthly queries**: ~$0.003

**Total: ~$0.05/month** (likely free tier!)

## View Your Data

After upload, view tables at:
https://console.aws.amazon.com/dynamodbv2/home#tables

## Query Examples

### Python:

```python
import boto3

dynamodb = boto3.resource('dynamodb')

# Get a passenger
table = dynamodb.Table('Passengers')
response = table.get_item(Key={'passenger_id': '22A00001111Z'})
print(response['Item'])

# Query weather
table = dynamodb.Table('Weather')
response = table.query(
    KeyConditionExpression='airport_code = :code',
    ExpressionAttributeValues={':code': 'AUH'}
)
for record in response['Items']:
    print(f"{record['forecast_time_zulu']}: {record['condition']}")

# Scan for VIP passengers
table = dynamodb.Table('Passengers')
response = table.scan(
    FilterExpression='passenger_category = :cat',
    ExpressionAttributeValues={':cat': 'VIP'}
)
print(f"VIP passengers: {len(response['Items'])}")
```

## Troubleshooting

### "Unable to locate credentials"
- Run `py configure_aws_credentials.py` again
- Check files exist: `~/.aws/credentials` and `~/.aws/config`

### "Access Denied"
- Check IAM user has DynamoDB permissions
- Attach `AmazonDynamoDBFullAccess` policy

### "Invalid region"
- Use valid region code (e.g., `us-east-1`)
- See region list above

### "boto3 not found"
- Run: `py -m pip install boto3`

## Why This Works Without AWS CLI

- **boto3** is the Python AWS SDK
- It reads credentials from `~/.aws/credentials` directly
- AWS CLI also uses the same credential files
- So you can use boto3 without installing AWS CLI!

## Benefits of This Approach

✓ No AWS CLI installation needed
✓ Simpler setup
✓ Works immediately
✓ Same credential files as AWS CLI
✓ Can add AWS CLI later if needed

## Next Steps

1. ✓ boto3 already installed
2. Run `py configure_aws_credentials.py`
3. Enter your AWS credentials
4. Run `py create_dynamodb_tables.py`
5. View data in AWS Console

## Support

- **boto3 Docs**: https://boto3.amazonaws.com/v1/documentation/api/latest/
- **DynamoDB Docs**: https://docs.aws.amazon.com/dynamodb/
- **IAM User Guide**: https://docs.aws.amazon.com/IAM/latest/UserGuide/

---

**Ready to start?** Run: `py configure_aws_credentials.py`
