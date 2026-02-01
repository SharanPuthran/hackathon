# Error Handling and Recovery Guide

## Quick Reference

This guide explains the error handling and recovery features in the deployment script.

## Features Overview

### 1. Automatic Error Detection

The script automatically detects and handles:

- AWS authentication failures
- S3 bucket errors (already exists, not found, access denied)
- CloudFront distribution errors (quota exceeded, creation failed)
- File upload failures
- Network timeouts
- Rate limiting

### 2. Rollback Capability

If deployment fails after creating resources, you'll be prompted:

```
Do you want to rollback and delete these resources? (y/N):
```

**What gets rolled back:**

- CloudFront distributions (disabled, not deleted)
- S3 bucket contents (emptied, bucket kept for safety)

### 3. Retry Logic

Transient failures are automatically retried with exponential backoff:

- Attempt 1: Immediate
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- Attempt 4: Wait 8 seconds

## Common Error Scenarios

### Authentication Errors

**Error:**

```
InvalidAccessKeyId: The AWS Access Key Id you provided does not exist
```

**Recovery:**

1. Run `aws sso login` if using AWS SSO
2. Run `aws configure` to update credentials
3. Check environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### Bucket Already Exists

**Error:**

```
BucketAlreadyExists: The requested bucket name is not available
```

**Recovery:**

1. If you own the bucket, the script will continue
2. If not, change `BUCKET_NAME` in the script
3. Check ownership: `aws s3api head-bucket --bucket BUCKET_NAME`

### Access Denied

**Error:**

```
AccessDenied: Access Denied
```

**Recovery:**

1. Verify IAM permissions (s3:_, cloudfront:_, sts:GetCallerIdentity)
2. Check IAM policies attached to your user/role
3. Contact AWS administrator for permission grants

### Upload Failure

**Error:**

```
Failed to sync files to S3
```

**Recovery:**

1. Check bucket exists: `aws s3 ls s3://BUCKET_NAME`
2. Verify s3:PutObject permission
3. Check internet connection
4. Try manual upload: `aws s3 cp file.html s3://BUCKET_NAME/`

### CloudFront Quota Exceeded

**Error:**

```
TooManyDistributions: You have reached the maximum number of distributions
```

**Recovery:**

1. Delete unused distributions: `aws cloudfront list-distributions`
2. Request quota increase from AWS Support
3. Use existing distribution if available

### Rate Limiting

**Error:**

```
ThrottlingException: Rate exceeded
```

**Recovery:**

- Wait a few minutes (automatic retry will handle this)
- The script uses exponential backoff
- No manual action needed

## Rollback Process

### When Rollback Happens

Rollback is offered when:

1. Deployment fails with non-zero exit code
2. Resources were created during the deployment
3. User confirms rollback action

### What Gets Rolled Back

**CloudFront Distribution:**

- Distribution is disabled (not deleted)
- Takes 15-20 minutes to fully disable
- Can be re-enabled or deleted manually later

**S3 Bucket:**

- All files are deleted from the bucket
- Bucket itself is kept (for safety)
- Can be deleted manually: `aws s3 rb s3://BUCKET_NAME --force`

### Manual Rollback

If you need to manually rollback:

```bash
# Disable CloudFront distribution
aws cloudfront get-distribution-config --id DISTRIBUTION_ID > config.json
# Edit config.json: set "Enabled": false
aws cloudfront update-distribution --id DISTRIBUTION_ID --distribution-config file://config.json --if-match ETAG

# Empty S3 bucket
aws s3 rm s3://BUCKET_NAME/ --recursive

# Delete S3 bucket (optional)
aws s3 rb s3://BUCKET_NAME --force
```

## Non-Critical Failures

Some failures don't stop deployment:

### Cache Invalidation Failure

```
[WARNING] Cache invalidation failed, but deployment can continue
```

**Impact:** Cache will expire naturally (based on TTL)

**Manual Fix:**

```bash
aws cloudfront create-invalidation --distribution-id DIST_ID --paths '/*'
```

### Metadata Setting Failure

```
[WARNING] Failed to set metadata for some files
```

**Impact:** Files uploaded but may not have optimal caching

**Manual Fix:**

```bash
aws s3api copy-object \
  --bucket BUCKET_NAME \
  --copy-source BUCKET_NAME/file.js \
  --key file.js \
  --metadata-directive REPLACE \
  --cache-control 'public, max-age=31536000'
```

## Debugging Tips

### Enable Verbose Logging

The script already logs all major steps. For more details:

```bash
bash -x deploy.sh 2>&1 | tee deployment.log
```

### Check Deployment State

During deployment, state is tracked in:

```
/tmp/skymarshal-deployment-state-$$.json
```

### View AWS CloudTrail

For detailed AWS API call logs:

```bash
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=CreateBucket
```

### Check Configuration

Deployment configuration is saved in:

```
./deploy-config.json
```

Contains:

- Bucket name
- Distribution ID
- Distribution domain
- Last invalidation details

## Best Practices

### Before Deployment

1. ✅ Verify AWS credentials: `aws sts get-caller-identity`
2. ✅ Check IAM permissions
3. ✅ Set environment variables in `.env` file
4. ✅ Run build: `cd frontend && npm run build`

### During Deployment

1. ✅ Monitor the output for warnings
2. ✅ Don't interrupt the process (Ctrl+C triggers cleanup)
3. ✅ Note the distribution ID for future reference

### After Failure

1. ✅ Read the error message carefully
2. ✅ Follow the recovery suggestions
3. ✅ Consider rollback if resources were created
4. ✅ Fix the issue before retrying

### After Success

1. ✅ Save the distribution URL
2. ✅ Wait 15-20 minutes for CloudFront deployment
3. ✅ Test the application
4. ✅ Keep `deploy-config.json` for future deployments

## Getting Help

### Error Message Not Clear?

1. Check this guide for common scenarios
2. Review the full error output
3. Check AWS service status: https://status.aws.amazon.com/
4. Review AWS CloudTrail logs

### Deployment Keeps Failing?

1. Verify all prerequisites are met
2. Check AWS service quotas
3. Try deploying to a different region
4. Contact AWS Support if needed

### Need to Start Over?

1. Run rollback if prompted
2. Manually delete resources if needed
3. Delete `deploy-config.json`
4. Run deployment again

## Advanced Recovery

### Recover from Partial Deployment

If deployment was interrupted:

```bash
# Check what exists
aws s3 ls s3://BUCKET_NAME/
aws cloudfront list-distributions

# Continue from where it left off
# The script is idempotent - it will skip existing resources
./deploy.sh
```

### Force Clean Deployment

```bash
# Remove configuration
rm -f deploy-config.json

# Empty bucket
aws s3 rm s3://BUCKET_NAME/ --recursive

# Run deployment
./deploy.sh
```

### Recover Distribution ID

If you lost the distribution ID:

```bash
# List all distributions
aws cloudfront list-distributions --query 'DistributionList.Items[*].[Id,DomainName,Origins.Items[0].DomainName]' --output table

# Find the one with your S3 bucket as origin
# Update deploy-config.json with the ID
```

## Summary

The deployment script includes comprehensive error handling:

- ✅ Automatic error detection and recovery
- ✅ Clear error messages with recovery steps
- ✅ Rollback capability for failed deployments
- ✅ Retry logic for transient failures
- ✅ Graceful handling of non-critical failures
- ✅ Resource tracking and cleanup

Most errors can be resolved by following the recovery suggestions in the error messages.
