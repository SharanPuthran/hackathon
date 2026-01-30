# AWS CLI Quick Start

## ✓ Installation Complete

AWS CLI installer has been executed. Follow these steps:

## Step 1: Restart Your Terminal ⚠️

**IMPORTANT**: You must restart your terminal for AWS CLI to work.

**Option A**: Close and reopen your terminal/PowerShell
**Option B**: Restart your IDE (VS Code, etc.)

## Step 2: Verify Installation

After restarting, run:

```powershell
aws --version
```

Expected output:
```
aws-cli/2.x.x Python/3.x.x Windows/10 exe/AMD64
```

## Step 3: Run Setup Script

```powershell
.\setup_aws.ps1
```

This script will:
- ✓ Verify AWS CLI installation
- ✓ Check if credentials are configured
- ✓ Guide you through configuration
- ✓ Test your AWS connection

## Step 4: Configure AWS (if needed)

```powershell
aws configure
```

You'll need:
1. **AWS Access Key ID** - Get from AWS Console → IAM → Users → Security Credentials
2. **AWS Secret Access Key** - Provided when creating access keys
3. **Default region** - e.g., `us-east-1`, `eu-west-1`, `ap-southeast-1`
4. **Output format** - Recommended: `json`

## Step 5: Test Connection

```powershell
aws sts get-caller-identity
```

## AWS Console Access

**Web Console**: https://console.aws.amazon.com/

Sign in with:
- Account ID or alias
- IAM username
- Password

## Quick Commands

```powershell
# Identity
aws sts get-caller-identity

# S3
aws s3 ls                                    # List buckets
aws s3 mb s3://my-bucket                     # Create bucket
aws s3 cp file.txt s3://my-bucket/           # Upload file
aws s3 sync ./output s3://my-bucket/data/    # Sync folder

# EC2
aws ec2 describe-instances                   # List instances
aws ec2 describe-regions                     # List regions

# Help
aws help
aws s3 help
```

## Files Created

- `AWS_CLI_SETUP_GUIDE.md` - Comprehensive setup guide
- `setup_aws.ps1` - Automated setup script
- `AWS_QUICK_START.md` - This quick reference

## Need Help?

1. Read `AWS_CLI_SETUP_GUIDE.md` for detailed instructions
2. Run `.\setup_aws.ps1` for guided setup
3. Visit: https://docs.aws.amazon.com/cli/

---

**Next Step**: Restart your terminal and run `aws --version` ✓
