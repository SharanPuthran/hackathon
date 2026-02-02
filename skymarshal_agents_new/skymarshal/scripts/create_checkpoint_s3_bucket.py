#!/usr/bin/env python3
"""
Create S3 bucket for large checkpoint storage (≥350KB)
"""

import os
import boto3
import sys

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BUCKET_NAME = os.getenv('CHECKPOINT_S3_BUCKET', 'skymarshal-checkpoints')
AWS_ACCOUNT_ID = boto3.client('sts').get_caller_identity()['Account']

def create_checkpoint_bucket():
    """Create S3 bucket for large checkpoint storage"""
    
    s3 = boto3.client('s3', region_name=AWS_REGION)
    
    # Make bucket name unique with account ID
    unique_bucket_name = f"{BUCKET_NAME}-{AWS_ACCOUNT_ID}"
    
    print(f"Creating S3 bucket: {unique_bucket_name}")
    print(f"Region: {AWS_REGION}")
    
    try:
        # Check if bucket already exists
        try:
            s3.head_bucket(Bucket=unique_bucket_name)
            print(f"✅ Bucket {unique_bucket_name} already exists")
            
            # Get bucket location
            location = s3.get_bucket_location(Bucket=unique_bucket_name)
            print(f"   Location: {location.get('LocationConstraint', 'us-east-1')}")
            
            return 0
        except s3.exceptions.NoSuchBucket:
            pass
        except Exception as e:
            if '404' not in str(e):
                raise
        
        # Create bucket
        if AWS_REGION == 'us-east-1':
            # us-east-1 doesn't need LocationConstraint
            s3.create_bucket(Bucket=unique_bucket_name)
        else:
            s3.create_bucket(
                Bucket=unique_bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': AWS_REGION
                }
            )
        
        print(f"✅ Bucket created: {unique_bucket_name}")
        
        # Enable versioning
        print("\n⏳ Enabling versioning...")
        s3.put_bucket_versioning(
            Bucket=unique_bucket_name,
            VersioningConfiguration={
                'Status': 'Enabled'
            }
        )
        
        # Enable encryption
        print("⏳ Enabling encryption...")
        s3.put_bucket_encryption(
            Bucket=unique_bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }
                ]
            }
        )
        
        # Add lifecycle policy for cleanup
        print("⏳ Adding lifecycle policy (90 day expiration)...")
        s3.put_bucket_lifecycle_configuration(
            Bucket=unique_bucket_name,
            LifecycleConfiguration={
                'Rules': [
                    {
                        'ID': 'DeleteOldCheckpoints',
                        'Status': 'Enabled',
                        'Prefix': 'checkpoints/',
                        'Expiration': {
                            'Days': 90
                        }
                    }
                ]
            }
        )
        
        # Add tags
        print("⏳ Adding tags...")
        s3.put_bucket_tagging(
            Bucket=unique_bucket_name,
            Tagging={
                'TagSet': [
                    {
                        'Key': 'Application',
                        'Value': 'SkyMarshal'
                    },
                    {
                        'Key': 'Purpose',
                        'Value': 'CheckpointStorage'
                    }
                ]
            }
        )
        
        print(f"\n✅ S3 bucket {unique_bucket_name} configured successfully!")
        print("\nBucket configuration:")
        print(f"  - Versioning: Enabled")
        print(f"  - Encryption: AES256")
        print(f"  - Lifecycle: 90 day expiration for checkpoints/")
        print(f"  - Region: {AWS_REGION}")
        
        print(f"\n📝 Update your .env file with:")
        print(f"   CHECKPOINT_S3_BUCKET={unique_bucket_name}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error creating bucket: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(create_checkpoint_bucket())
