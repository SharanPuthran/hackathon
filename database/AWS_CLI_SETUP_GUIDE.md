# AWS CLI Setup Guide

## Installation Status
✓ AWS CLI installer has been downloaded and executed.

## Next Steps

### 1. Restart Your Terminal
The AWS CLI has been installed, but you need to restart your PowerShell/Command Prompt or IDE terminal for the PATH changes to take effect.

**Option A: Restart your terminal**
- Close this terminal window
- Open a new PowerShell or Command Prompt window
- Run: `aws --version`

**Option B: Restart your IDE**
- Close and reopen your IDE (VS Code, etc.)
- Open a new terminal
- Run: `aws --version`

### 2. Verify Installation
After restarting your terminal, verify AWS CLI is installed:

```powershell
aws --version
```

Expected output:
```
aws-cli/2.x.x Python/3.x.x Windows/10 exe/AMD64
```

### 3. Configure AWS CLI

Once AWS CLI is verified, configure it with your AWS credentials:

```powershell
aws configure
```

You'll be prompted for:

1. **AWS Access Key ID**: Your AWS access key
   - Get this from AWS Console → IAM → Users → Security Credentials
   - Or from your AWS administrator

2. **AWS Secret Access Key**: Your AWS secret key
   - Provided when you create access keys
   - Keep this secure!

3. **Default region name**: Your preferred AWS region
   - Examples: `us-east-1`, `eu-west-1`, `ap-southeast-1`
   - Choose the region closest to you or where your resources are

4. **Default output format**: Output format preference
   - Options: `json` (recommended), `yaml`, `text`, `table`
   - Recommended: `json`

### Example Configuration Session

```powershell
PS> aws configure
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
Default region name [None]: us-east-1
Default output format [None]: json
```

### 4. Test Your Configuration

After configuration, test your AWS connection:

```powershell
# Test basic connectivity
aws sts get-caller-identity

# List S3 buckets (if you have any)
aws s3 ls

# List EC2 instances (if you have any)
aws ec2 describe-instances --region us-east-1
```

### 5. AWS Console Access

To access the AWS Console in your browser:

1. **Go to**: https://console.aws.amazon.com/
2. **Sign in with**:
   - Account ID or alias
   - IAM username
   - Password

**Or use SSO (if configured)**:
- Go to your organization's SSO portal
- Example: https://your-company.awsapps.com/start

### 6. Multiple AWS Profiles (Optional)

If you work with multiple AWS accounts, you can configure multiple profiles:

```powershell
# Configure a named profile
aws configure --profile work
aws configure --profile personal

# Use a specific profile
aws s3 ls --profile work
aws ec2 describe-instances --profile personal

# Set default profile for session
$env:AWS_PROFILE="work"
```

### 7. Configuration Files Location

Your AWS credentials are stored at:
- **Windows**: `C:\Users\YOUR_USERNAME\.aws\`
  - `credentials` - Contains access keys
  - `config` - Contains region and output settings

### 8. Security Best Practices

1. **Never commit credentials to Git**
   - Add `.aws/` to your `.gitignore`
   - Use environment variables or AWS SSO for CI/CD

2. **Use IAM roles when possible**
   - For EC2 instances, Lambda functions, etc.
   - Avoid hardcoding credentials

3. **Rotate access keys regularly**
   - AWS recommends rotating every 90 days
   - Delete unused keys

4. **Use MFA (Multi-Factor Authentication)**
   - Enable MFA for your IAM user
   - Adds extra security layer

5. **Follow least privilege principle**
   - Only grant necessary permissions
   - Use IAM policies to restrict access

### 9. Common AWS CLI Commands

```powershell
# S3 Operations
aws s3 ls                                    # List buckets
aws s3 ls s3://bucket-name/                  # List objects in bucket
aws s3 cp file.txt s3://bucket-name/         # Upload file
aws s3 cp s3://bucket-name/file.txt ./       # Download file
aws s3 sync ./folder s3://bucket-name/       # Sync folder

# EC2 Operations
aws ec2 describe-instances                   # List instances
aws ec2 start-instances --instance-ids i-xxx # Start instance
aws ec2 stop-instances --instance-ids i-xxx  # Stop instance

# IAM Operations
aws iam list-users                           # List IAM users
aws iam get-user                             # Get current user info

# CloudFormation
aws cloudformation list-stacks               # List stacks
aws cloudformation describe-stacks           # Describe stacks

# Lambda
aws lambda list-functions                    # List Lambda functions
aws lambda invoke --function-name my-func    # Invoke function

# RDS
aws rds describe-db-instances                # List RDS instances

# DynamoDB
aws dynamodb list-tables                     # List DynamoDB tables
```

### 10. Troubleshooting

**Issue: "aws: command not found"**
- Solution: Restart terminal or add AWS CLI to PATH manually
- Path: `C:\Program Files\Amazon\AWSCLIV2\`

**Issue: "Unable to locate credentials"**
- Solution: Run `aws configure` to set up credentials

**Issue: "Access Denied"**
- Solution: Check your IAM permissions
- Verify you're using the correct profile

**Issue: "Invalid region"**
- Solution: Use valid AWS region codes
- List: https://docs.aws.amazon.com/general/latest/gr/rande.html

### 11. Getting AWS Credentials

If you don't have AWS credentials yet:

**Option A: Create IAM User (for personal/development)**
1. Log in to AWS Console
2. Go to IAM → Users → Add User
3. Set username and enable "Programmatic access"
4. Attach policies (e.g., AdministratorAccess for testing)
5. Download credentials CSV (contains Access Key ID and Secret)

**Option B: Use AWS SSO (for organizations)**
1. Contact your AWS administrator
2. Get SSO portal URL
3. Use `aws configure sso` command

**Option C: Use AWS CloudShell (browser-based)**
1. Log in to AWS Console
2. Click CloudShell icon (top right)
3. Pre-configured AWS CLI in browser

### 12. Alternative: AWS CloudShell

If you want to use AWS CLI immediately without local installation:

1. Go to: https://console.aws.amazon.com/
2. Sign in to your AWS account
3. Click the CloudShell icon (terminal icon in top navigation bar)
4. AWS CLI is pre-installed and pre-configured!

### 13. Next Steps After Setup

Once AWS CLI is configured, you can:

1. **Upload your database files to S3**
   ```powershell
   aws s3 mb s3://my-airline-data-bucket
   aws s3 sync ./output s3://my-airline-data-bucket/data/
   ```

2. **Set up RDS database**
   ```powershell
   aws rds create-db-instance --db-instance-identifier airline-db \
     --db-instance-class db.t3.micro \
     --engine postgres \
     --master-username admin \
     --master-user-password YourPassword123
   ```

3. **Deploy Lambda functions**
   ```powershell
   aws lambda create-function --function-name disruption-handler \
     --runtime python3.12 \
     --role arn:aws:iam::account:role/lambda-role \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://function.zip
   ```

4. **Use AWS SDK in Python**
   ```python
   import boto3
   
   # S3 client
   s3 = boto3.client('s3')
   s3.upload_file('output/weather.csv', 'my-bucket', 'weather.csv')
   
   # DynamoDB client
   dynamodb = boto3.resource('dynamodb')
   table = dynamodb.Table('passengers')
   ```

## Quick Reference Card

```powershell
# Installation Check
aws --version

# Configuration
aws configure
aws configure --profile myprofile

# Identity Check
aws sts get-caller-identity

# S3 Quick Commands
aws s3 ls
aws s3 cp file.txt s3://bucket/
aws s3 sync ./folder s3://bucket/

# EC2 Quick Commands
aws ec2 describe-instances
aws ec2 describe-regions

# Help
aws help
aws s3 help
aws ec2 describe-instances help
```

## Support Resources

- **AWS CLI Documentation**: https://docs.aws.amazon.com/cli/
- **AWS CLI Command Reference**: https://awscli.amazonaws.com/v2/documentation/api/latest/index.html
- **AWS Free Tier**: https://aws.amazon.com/free/
- **AWS Support**: https://console.aws.amazon.com/support/

---

**Note**: After restarting your terminal, come back and run `aws --version` to verify the installation, then proceed with `aws configure` to set up your credentials.
