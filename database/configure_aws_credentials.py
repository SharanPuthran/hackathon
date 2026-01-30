"""
Configure AWS Credentials without AWS CLI
This script helps you set up AWS credentials for boto3 directly
"""

import os
from pathlib import Path

print("=" * 80)
print("AWS Credentials Configuration (boto3)")
print("=" * 80)
print()
print("This script will configure AWS credentials for Python boto3 library.")
print("You don't need AWS CLI installed for this to work!")
print()

# Get AWS credentials from user
print("Please enter your AWS credentials:")
print("(You can get these from AWS Console → IAM → Users → Security Credentials)")
print()

aws_access_key_id = input("AWS Access Key ID: ").strip()
aws_secret_access_key = input("AWS Secret Access Key: ").strip()
default_region = input("Default region name (e.g., us-east-1, eu-west-1): ").strip() or "us-east-1"
output_format = input("Default output format (json/yaml/text) [json]: ").strip() or "json"

print()
print("Configuring credentials...")

# Create .aws directory
aws_dir = Path.home() / ".aws"
aws_dir.mkdir(exist_ok=True)

# Write credentials file
credentials_file = aws_dir / "credentials"
credentials_content = f"""[default]
aws_access_key_id = {aws_access_key_id}
aws_secret_access_key = {aws_secret_access_key}
"""

with open(credentials_file, 'w') as f:
    f.write(credentials_content)

print(f"✓ Credentials saved to: {credentials_file}")

# Write config file
config_file = aws_dir / "config"
config_content = f"""[default]
region = {default_region}
output = {output_format}
"""

with open(config_file, 'w') as f:
    f.write(config_content)

print(f"✓ Config saved to: {config_file}")
print()

# Test the credentials
print("Testing credentials...")
try:
    import boto3
    
    sts = boto3.client('sts')
    identity = sts.get_caller_identity()
    
    print()
    print("=" * 80)
    print("✓ SUCCESS! AWS credentials configured and working!")
    print("=" * 80)
    print()
    print(f"Account ID: {identity['Account']}")
    print(f"User ARN: {identity['Arn']}")
    print(f"User ID: {identity['UserId']}")
    print()
    print("You can now run: py create_dynamodb_tables.py")
    print()
    
except Exception as e:
    print()
    print("=" * 80)
    print("✗ Error testing credentials")
    print("=" * 80)
    print()
    print(f"Error: {e}")
    print()
    print("Please check:")
    print("  1. Your Access Key ID is correct")
    print("  2. Your Secret Access Key is correct")
    print("  3. Your IAM user has necessary permissions")
    print()
    print("You can run this script again to reconfigure.")
    print()
