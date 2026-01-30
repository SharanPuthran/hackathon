#!/usr/bin/env python3
"""
Test AWS Bedrock connection and model access
"""

import os
import sys
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
import json

def test_aws_credentials():
    """Test if AWS credentials are configured"""
    print("=" * 70)
    print("AWS BEDROCK CONNECTION TEST")
    print("=" * 70)
    print()
    
    # Check environment variables
    print("1. Checking AWS credentials...")
    aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
    aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    aws_region = os.getenv('AWS_REGION', 'us-east-1')
    
    if not aws_access_key:
        print("   ✗ AWS_ACCESS_KEY_ID not found in environment")
        print("   → Set it in .env file or export AWS_ACCESS_KEY_ID=your-key")
        return False
    else:
        print(f"   ✓ AWS_ACCESS_KEY_ID found: {aws_access_key[:8]}...")
    
    if not aws_secret_key:
        print("   ✗ AWS_SECRET_ACCESS_KEY not found in environment")
        print("   → Set it in .env file or export AWS_SECRET_ACCESS_KEY=your-secret")
        return False
    else:
        print(f"   ✓ AWS_SECRET_ACCESS_KEY found: {aws_secret_key[:8]}...")
    
    print(f"   ✓ AWS_REGION: {aws_region}")
    print()
    
    return True

def test_bedrock_connection():
    """Test connection to AWS Bedrock"""
    print("2. Testing AWS Bedrock connection...")
    
    try:
        config = Config(
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )
        
        # Create Bedrock client
        bedrock = boto3.client('bedrock', config=config)
        
        # List foundation models
        response = bedrock.list_foundation_models()
        
        print(f"   ✓ Successfully connected to AWS Bedrock")
        print(f"   ✓ Found {len(response.get('modelSummaries', []))} foundation models")
        print()
        
        return True, bedrock
        
    except NoCredentialsError:
        print("   ✗ No AWS credentials found")
        print("   → Configure credentials in .env file or AWS CLI")
        return False, None
    except PartialCredentialsError:
        print("   ✗ Incomplete AWS credentials")
        print("   → Both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY required")
        return False, None
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        print(f"   ✗ AWS Error: {error_code}")
        print(f"   → {error_msg}")
        return False, None
    except Exception as e:
        print(f"   ✗ Connection failed: {str(e)}")
        return False, None

def test_bedrock_runtime():
    """Test Bedrock Runtime for model invocation"""
    print("3. Testing AWS Bedrock Runtime...")
    
    try:
        config = Config(
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            read_timeout=60,
            connect_timeout=60
        )
        
        bedrock_runtime = boto3.client('bedrock-runtime', config=config)
        
        print(f"   ✓ Successfully connected to Bedrock Runtime")
        print()
        
        return True, bedrock_runtime
        
    except Exception as e:
        print(f"   ✗ Runtime connection failed: {str(e)}")
        return False, None

def check_model_access(bedrock):
    """Check access to specific models used in SkyMarshal"""
    print("4. Checking model access...")
    
    # Models used in SkyMarshal
    required_models = {
        "Claude 3.7 Sonnet": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "Gemini 3.0 Pro": "google.gemini-3-0-pro-v1:0",
        "GPT-5 Turbo": "openai.gpt-5-turbo-20250214-v1:0",
        "Gemini 3.0 Flash": "google.gemini-3-0-flash-v1:0",
        "Amazon Nova Pro": "us.amazon.nova-pro-v1:0"
    }
    
    try:
        response = bedrock.list_foundation_models()
        available_models = {m['modelId']: m for m in response.get('modelSummaries', [])}
        
        accessible_count = 0
        
        for model_name, model_id in required_models.items():
            # Check if model ID pattern exists
            matching = [m for m in available_models.keys() if model_id.split(':')[0] in m]
            
            if matching:
                print(f"   ✓ {model_name}")
                print(f"     Model ID: {model_id}")
                accessible_count += 1
            else:
                print(f"   ✗ {model_name} - Not accessible")
                print(f"     Model ID: {model_id}")
                print(f"     → May need to request access in AWS Console")
        
        print()
        print(f"   Summary: {accessible_count}/{len(required_models)} models accessible")
        print()
        
        if accessible_count == 0:
            print("   ⚠️  No models accessible - you may need to:")
            print("      1. Request model access in AWS Bedrock Console")
            print("      2. Wait for approval (can take a few minutes)")
            print("      3. Ensure your AWS account has Bedrock permissions")
        
        return accessible_count > 0
        
    except Exception as e:
        print(f"   ✗ Failed to check models: {str(e)}")
        return False

def test_simple_invocation(bedrock_runtime):
    """Test a simple model invocation"""
    print("5. Testing model invocation (optional)...")
    
    # Try with a simple Claude model (most commonly available)
    test_model = "anthropic.claude-3-sonnet-20240229-v1:0"  # Older stable version
    
    try:
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Say 'Hello from AWS Bedrock!' in exactly 5 words."
                }
            ]
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=test_model,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        output = response_body['content'][0]['text']
        
        print(f"   ✓ Model invocation successful!")
        print(f"   ✓ Test model: {test_model}")
        print(f"   ✓ Response: {output}")
        print()
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDeniedException':
            print(f"   ⚠️  Model access denied (expected if not yet approved)")
            print(f"   → Request access to models in AWS Bedrock Console")
        else:
            print(f"   ✗ Invocation failed: {error_code}")
        print()
        return False
    except Exception as e:
        print(f"   ⚠️  Invocation test skipped: {str(e)}")
        print()
        return False

def main():
    """Run all connection tests"""
    
    # Load .env if exists
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("Note: python-dotenv not installed, using environment variables only")
        print()
    
    # Test 1: Credentials
    if not test_aws_credentials():
        print()
        print("=" * 70)
        print("RESULT: ✗ AWS credentials not configured")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Copy .env.example to .env")
        print("2. Add your AWS credentials to .env")
        print("3. Run this test again")
        return False
    
    # Test 2: Bedrock connection
    success, bedrock = test_bedrock_connection()
    if not success:
        print()
        print("=" * 70)
        print("RESULT: ✗ Cannot connect to AWS Bedrock")
        print("=" * 70)
        return False
    
    # Test 3: Bedrock Runtime
    success, bedrock_runtime = test_bedrock_runtime()
    if not success:
        print()
        print("=" * 70)
        print("RESULT: ✗ Cannot connect to Bedrock Runtime")
        print("=" * 70)
        return False
    
    # Test 4: Model access
    has_models = check_model_access(bedrock)
    
    # Test 5: Simple invocation (optional)
    if bedrock_runtime:
        test_simple_invocation(bedrock_runtime)
    
    # Final result
    print("=" * 70)
    if has_models:
        print("RESULT: ✓ AWS Bedrock connection working!")
        print("=" * 70)
        print()
        print("✓ Credentials configured")
        print("✓ Bedrock connection successful")
        print("✓ Models accessible")
        print()
        print("You can now run the SkyMarshal system!")
    else:
        print("RESULT: ⚠️  Connection works but models need access")
        print("=" * 70)
        print()
        print("✓ Credentials configured")
        print("✓ Bedrock connection successful")
        print("✗ Models not yet accessible")
        print()
        print("Next steps:")
        print("1. Go to AWS Console → Bedrock → Model access")
        print("2. Request access to required models")
        print("3. Wait for approval (usually instant)")
        print("4. Run this test again")
    
    return has_models

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
