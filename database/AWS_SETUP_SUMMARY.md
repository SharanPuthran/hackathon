# AWS CLI Setup Summary

## ✓ What's Been Done

1. **AWS CLI Installer Downloaded and Executed**
   - Latest AWS CLI v2 has been installed on your system
   - Installation location: `C:\Program Files\Amazon\AWSCLIV2\`

2. **Setup Scripts Created**
   - `setup_aws.ps1` - Automated configuration helper
   - `upload_to_s3.ps1` - Upload your data to S3
   - `AWS_CLI_SETUP_GUIDE.md` - Comprehensive guide
   - `AWS_QUICK_START.md` - Quick reference

## ⚠️ Important: Next Steps Required

### Step 1: Restart Your Terminal (REQUIRED)

The AWS CLI has been installed but won't work until you restart your terminal.

**Choose one:**
- Close and reopen your PowerShell/Command Prompt
- Restart your IDE (VS Code, etc.)
- Open a new terminal window

### Step 2: Verify Installation

After restarting, run:

```powershell
aws --version
```

Expected output:
```
aws-cli/2.x.x Python/3.x.x Windows/10 exe/AMD64
```

### Step 3: Run Setup Script

```powershell
.\setup_aws.ps1
```

This will:
- ✓ Verify AWS CLI is working
- ✓ Check if credentials are configured
- ✓ Guide you through configuration
- ✓ Test your AWS connection

### Step 4: Configure AWS Credentials

If not already configured, run:

```powershell
aws configure
```

You'll need:

1. **AWS Access Key ID**
   - Get from: AWS Console → IAM → Users → Security Credentials → Create Access Key
   - Example: `AKIAIOSFODNN7EXAMPLE`

2. **AWS Secret Access Key**
   - Provided when you create the access key
   - Example: `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`
   - ⚠️ Keep this secret!

3. **Default Region**
   - Choose closest to you or where your resources are
   - Examples: `us-east-1`, `eu-west-1`, `ap-southeast-1`, `ap-south-1`

4. **Output Format**
   - Recommended: `json`
   - Options: `json`, `yaml`, `text`, `table`

### Step 5: Test Connection

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

## 🚀 Quick Commands After Setup

### Check Your Identity
```powershell
aws sts get-caller-identity
```

### List S3 Buckets
```powershell
aws s3 ls
```

### Upload Your Airline Data
```powershell
.\upload_to_s3.ps1
```

This will:
- Create an S3 bucket (or use existing)
- Upload all your CSV files
- Provide S3 URLs for access

### List EC2 Instances
```powershell
aws ec2 describe-instances --region us-east-1
```

### Get Help
```powershell
aws help
aws s3 help
aws ec2 help
```

## 📁 Your Data Files Ready for Upload

- `output/passengers_enriched_final.csv` (11,406 passengers)
- `output/flights_enriched_mel.csv` (256 flights)
- `output/aircraft_availability_enriched_mel.csv` (168 records)
- `output/weather.csv` (456 weather records, 19 airports)
- `output/disrupted_passengers_scenario.csv` (346 passengers)
- `output/aircraft_swap_options.csv` (4 aircraft options)
- `output/inbound_flight_impact.csv` (3 scenarios)

## 🌐 AWS Console Access

**Web Console**: https://console.aws.amazon.com/

Sign in with:
- Account ID or alias
- IAM username
- Password

**Popular Services:**
- S3: https://s3.console.aws.amazon.com/
- EC2: https://console.aws.amazon.com/ec2/
- RDS: https://console.aws.amazon.com/rds/
- Lambda: https://console.aws.amazon.com/lambda/
- IAM: https://console.aws.amazon.com/iam/

## 🔐 Getting AWS Credentials

### Option 1: Create IAM User (Recommended for Development)

1. Log in to AWS Console
2. Go to **IAM** → **Users** → **Add User**
3. Set username (e.g., `airline-data-user`)
4. Enable **Programmatic access**
5. Attach policies:
   - `AmazonS3FullAccess` (for S3 operations)
   - `AmazonEC2ReadOnlyAccess` (for EC2 viewing)
   - Or create custom policy with specific permissions
6. Click **Create User**
7. **Download credentials CSV** (contains Access Key ID and Secret)
8. Use these credentials in `aws configure`

### Option 2: Use AWS SSO (For Organizations)

If your organization uses AWS SSO:

```powershell
aws configure sso
```

Follow the prompts to authenticate via browser.

### Option 3: AWS CloudShell (No Installation Needed)

1. Go to: https://console.aws.amazon.com/
2. Sign in to your AWS account
3. Click **CloudShell** icon (terminal icon in top navigation)
4. AWS CLI is pre-installed and pre-configured!

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `AWS_CLI_SETUP_GUIDE.md` | Comprehensive setup guide with all details |
| `AWS_QUICK_START.md` | Quick reference for getting started |
| `AWS_SETUP_SUMMARY.md` | This file - overview and next steps |
| `setup_aws.ps1` | Automated setup and verification script |
| `upload_to_s3.ps1` | Upload your data files to S3 |

## 🔧 Troubleshooting

### "aws: command not found"
- **Solution**: Restart your terminal
- If still not working, manually add to PATH:
  - Path: `C:\Program Files\Amazon\AWSCLIV2\`

### "Unable to locate credentials"
- **Solution**: Run `aws configure` to set up credentials

### "Access Denied"
- **Solution**: Check IAM permissions for your user
- Ensure you have necessary policies attached

### "Invalid region"
- **Solution**: Use valid AWS region codes
- List: https://docs.aws.amazon.com/general/latest/gr/rande.html

## 🎯 Common Use Cases for Your Airline Data

### 1. Store Data in S3
```powershell
# Upload all data
.\upload_to_s3.ps1

# Or manually
aws s3 cp output/weather.csv s3://my-bucket/data/
aws s3 sync ./output s3://my-bucket/data/
```

### 2. Set Up RDS Database
```powershell
# Create PostgreSQL database
aws rds create-db-instance `
  --db-instance-identifier airline-db `
  --db-instance-class db.t3.micro `
  --engine postgres `
  --master-username admin `
  --master-user-password YourPassword123 `
  --allocated-storage 20
```

### 3. Create Lambda Function for Disruption Handling
```powershell
# Package and deploy Lambda
aws lambda create-function `
  --function-name disruption-handler `
  --runtime python3.12 `
  --role arn:aws:iam::ACCOUNT:role/lambda-role `
  --handler lambda_function.lambda_handler `
  --zip-file fileb://function.zip
```

### 4. Use AWS SDK in Python
```python
import boto3

# Upload to S3
s3 = boto3.client('s3')
s3.upload_file('output/weather.csv', 'my-bucket', 'data/weather.csv')

# Query DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('passengers')
response = table.get_item(Key={'passenger_id': '12345'})
```

## 📞 Support Resources

- **AWS CLI Docs**: https://docs.aws.amazon.com/cli/
- **AWS CLI Reference**: https://awscli.amazonaws.com/v2/documentation/api/latest/
- **AWS Free Tier**: https://aws.amazon.com/free/
- **AWS Support**: https://console.aws.amazon.com/support/

## ✅ Checklist

- [ ] Restart terminal
- [ ] Run `aws --version` to verify installation
- [ ] Run `.\setup_aws.ps1` for guided setup
- [ ] Run `aws configure` to set credentials
- [ ] Run `aws sts get-caller-identity` to test connection
- [ ] Run `.\upload_to_s3.ps1` to upload your data
- [ ] Access AWS Console: https://console.aws.amazon.com/

---

**Current Status**: AWS CLI installed, waiting for terminal restart

**Next Action**: Restart your terminal and run `aws --version` ✓
