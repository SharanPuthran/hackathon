# Checkpoint Deployment Guide

## Overview

This guide explains how to deploy SkyMarshal with checkpoint persistence enabled. Checkpoint persistence provides durable state management, failure recovery, and complete audit trails for regulatory compliance.

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured with credentials
- UV package manager installed
- SkyMarshal agent system installed

## Deployment Modes

### Development Mode (Default)

In-memory checkpoints for local development and testing:

```bash
# No AWS resources required
CHECKPOINT_MODE=development
```

**Use Cases:**

- Local development and testing
- Fast iteration without AWS costs
- CI/CD pipeline testing
- Proof-of-concept demonstrations

**Limitations:**

- No persistence across restarts
- No failure recovery
- No audit trail

### Production Mode

Durable checkpoints with DynamoDB + S3:

```bash
CHECKPOINT_MODE=production
CHECKPOINT_TABLE_NAME=SkyMarshalCheckpoints
CHECKPOINT_S3_BUCKET=skymarshal-checkpoints-<account-id>
CHECKPOINT_TTL_DAYS=90
```

**Use Cases:**

- Production deployments
- Regulatory compliance (EASA, GCAA, FAA)
- Failure recovery requirements
- Audit trail requirements
- Human-in-the-loop workflows

**Benefits:**

- ✅ Durable persistence across restarts
- ✅ Automatic failure recovery
- ✅ Complete audit trail (90 days default)
- ✅ Time-travel debugging
- ✅ Size-based routing (DynamoDB <350KB, S3 ≥350KB)

## Step-by-Step Deployment

### Step 1: Create Infrastructure

#### 1.1 Create DynamoDB Table

```bash
cd skymarshal_agents_new/skymarshal
uv run python scripts/create_checkpoint_table.py
```

**Table Configuration:**

- **Name**: `SkyMarshalCheckpoints`
- **Partition Key**: `PK` (String) - Format: `THREAD#{thread_id}`
- **Sort Key**: `SK` (String) - Format: `CHECKPOINT#{checkpoint_id}#{timestamp}`
- **GSI**: `thread-status-index` (thread_id, status)
- **TTL**: Enabled on `ttl` attribute (90 days default)
- **Billing**: On-demand (pay per request)

**Verify Table Creation:**

```bash
aws dynamodb describe-table --table-name SkyMarshalCheckpoints
```

#### 1.2 Create S3 Bucket

```bash
uv run python scripts/create_checkpoint_s3_bucket.py
```

**Bucket Configuration:**

- **Name**: `skymarshal-checkpoints-<account-id>`
- **Versioning**: Enabled
- **Encryption**: AES256 (SSE-S3)
- **Lifecycle**: 90 day expiration for `checkpoints/` prefix
- **Region**: us-east-1 (or your preferred region)

**Verify Bucket Creation:**

```bash
aws s3 ls s3://skymarshal-checkpoints-<account-id>
```

### Step 2: Configure IAM Permissions

The AgentCore execution role needs permissions for DynamoDB and S3:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CheckpointDynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/SkyMarshalCheckpoints",
        "arn:aws:dynamodb:*:*:table/SkyMarshalCheckpoints/index/*"
      ]
    },
    {
      "Sid": "CheckpointS3Access",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::skymarshal-checkpoints-*/*"
    },
    {
      "Sid": "CheckpointS3BucketAccess",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::skymarshal-checkpoints-*"
    }
  ]
}
```

**Apply Permissions:**

```bash
# Get the execution role ARN from .bedrock_agentcore.yaml
ROLE_ARN=$(grep "execution_role:" .bedrock_agentcore.yaml | awk '{print $2}')

# Create policy
aws iam create-policy \
  --policy-name SkyMarshalCheckpointPolicy \
  --policy-document file://checkpoint-policy.json

# Attach policy to role
aws iam attach-role-policy \
  --role-name $(echo $ROLE_ARN | cut -d'/' -f2) \
  --policy-arn arn:aws:iam::<account-id>:policy/SkyMarshalCheckpointPolicy
```

### Step 3: Configure Environment Variables

Update your `.env` file:

```bash
# Checkpoint Configuration
CHECKPOINT_MODE=production
CHECKPOINT_TABLE_NAME=SkyMarshalCheckpoints
CHECKPOINT_S3_BUCKET=skymarshal-checkpoints-<account-id>
CHECKPOINT_TTL_DAYS=90

# Optional: Knowledge Base for arbitrator
KNOWLEDGE_BASE_ID=<your-kb-id>
```

### Step 4: Test Locally

Before deploying, test checkpoint functionality locally:

```bash
# Test checkpoint integration
uv run python src/checkpoint/migration.py

# Expected output:
# ✅ CheckpointSaver initialized: backend=DynamoDB
# ✅ ThreadManager initialized
# ✅ Thread created: <uuid>
# ✅ Checkpoint saved
# ✅ Checkpoint loaded: test_checkpoint
# ✅ All checkpoint integration tests passed
```

### Step 5: Deploy to AgentCore

```bash
# Deploy with checkpoint support
uv run agentcore deploy

# Expected output:
# ✅ Agent deployed successfully
# ✅ Agent ID: skymarshal_Agent-<id>
# ✅ Agent ARN: arn:aws:bedrock-agentcore:us-east-1:<account>:runtime/skymarshal_Agent-<id>
```

### Step 6: Verify Deployment

Test the deployed agent with checkpoint persistence:

```bash
# Invoke agent
uv run agentcore invoke "Flight EY123 on Jan 20th had a mechanical failure"

# Check DynamoDB for checkpoints
aws dynamodb scan --table-name SkyMarshalCheckpoints --limit 5

# Check S3 for large checkpoints
aws s3 ls s3://skymarshal-checkpoints-<account-id>/checkpoints/ --recursive
```

## Monitoring and Observability

### CloudWatch Logs

Checkpoint operations are logged to CloudWatch:

```bash
# View logs
aws logs tail /aws/bedrock-agentcore/skymarshal_Agent --follow

# Search for checkpoint logs
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/skymarshal_Agent \
  --filter-pattern "Checkpoint"
```

**Key Log Messages:**

- `✅ Checkpoint infrastructure initialized: mode=production`
- `💾 Checkpoint saved: <checkpoint-id>`
- `Checkpoint size <bytes> bytes exceeds threshold, routing to S3`
- `Checkpoint loaded from S3: <s3-key>`

### DynamoDB Metrics

Monitor checkpoint table performance:

```bash
# Get table metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=SkyMarshalCheckpoints \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

### S3 Metrics

Monitor S3 bucket usage:

```bash
# Get bucket size
aws s3 ls s3://skymarshal-checkpoints-<account-id>/checkpoints/ \
  --recursive --summarize --human-readable

# Get object count
aws s3api list-objects-v2 \
  --bucket skymarshal-checkpoints-<account-id> \
  --prefix checkpoints/ \
  --query 'length(Contents)'
```

## Cost Optimization

### DynamoDB Costs

- **On-Demand Pricing**: $1.25 per million write requests, $0.25 per million read requests
- **Typical Usage**: ~10 checkpoints per workflow = ~$0.0000125 per workflow
- **Monthly Estimate**: 10,000 workflows/month = ~$0.13/month

### S3 Costs

- **Storage**: $0.023 per GB/month (Standard)
- **Requests**: $0.005 per 1,000 PUT requests, $0.0004 per 1,000 GET requests
- **Typical Usage**: Large checkpoints (≥350KB) are rare
- **Monthly Estimate**: 100 large checkpoints/month = ~$0.01/month

### TTL Configuration

Checkpoints automatically expire after 90 days (configurable):

```bash
# Update TTL in .env
CHECKPOINT_TTL_DAYS=30  # Reduce to 30 days for cost savings
```

## Troubleshooting

### Issue: Checkpoints Not Saving

**Symptoms:**

- No checkpoints in DynamoDB
- Logs show "Falling back to in-memory storage"

**Solutions:**

1. **Check IAM Permissions:**

   ```bash
   aws iam get-role-policy --role-name <role-name> --policy-name SkyMarshalCheckpointPolicy
   ```

2. **Verify Table Exists:**

   ```bash
   aws dynamodb describe-table --table-name SkyMarshalCheckpoints
   ```

3. **Check Environment Variables:**
   ```bash
   echo $CHECKPOINT_MODE
   echo $CHECKPOINT_TABLE_NAME
   ```

### Issue: Large Checkpoints Failing

**Symptoms:**

- Logs show "Failed to save large checkpoint to S3"
- Checkpoints >350KB not persisting

**Solutions:**

1. **Verify S3 Bucket Exists:**

   ```bash
   aws s3 ls s3://skymarshal-checkpoints-<account-id>
   ```

2. **Check S3 Permissions:**

   ```bash
   aws s3api get-bucket-policy --bucket skymarshal-checkpoints-<account-id>
   ```

3. **Test S3 Upload:**
   ```bash
   echo "test" | aws s3 cp - s3://skymarshal-checkpoints-<account-id>/test.txt
   ```

### Issue: Checkpoint Load Failures

**Symptoms:**

- Logs show "Failed to load checkpoint"
- Recovery operations failing

**Solutions:**

1. **Check Checkpoint Exists:**

   ```bash
   aws dynamodb query \
     --table-name SkyMarshalCheckpoints \
     --key-condition-expression "PK = :pk" \
     --expression-attribute-values '{":pk":{"S":"THREAD#<thread-id>"}}'
   ```

2. **Verify S3 Object Exists:**

   ```bash
   aws s3 ls s3://skymarshal-checkpoints-<account-id>/checkpoints/<thread-id>/
   ```

3. **Check TTL Expiration:**
   - Checkpoints expire after 90 days by default
   - Verify checkpoint timestamp is within TTL window

## Rollback

To disable checkpoint persistence:

```bash
# Update .env
CHECKPOINT_MODE=development

# Redeploy
uv run agentcore deploy
```

**Note:** Existing checkpoints in DynamoDB/S3 will remain but won't be used.

## Cleanup

To remove checkpoint infrastructure:

```bash
# Delete DynamoDB table
aws dynamodb delete-table --table-name SkyMarshalCheckpoints

# Delete S3 bucket (must be empty first)
aws s3 rm s3://skymarshal-checkpoints-<account-id> --recursive
aws s3 rb s3://skymarshal-checkpoints-<account-id>

# Detach IAM policy
aws iam detach-role-policy \
  --role-name <role-name> \
  --policy-arn arn:aws:iam::<account-id>:policy/SkyMarshalCheckpointPolicy

# Delete IAM policy
aws iam delete-policy \
  --policy-arn arn:aws:iam::<account-id>:policy/SkyMarshalCheckpointPolicy
```

## Best Practices

1. **Start with Development Mode**: Test locally before enabling production mode
2. **Monitor Costs**: Set up CloudWatch billing alarms for DynamoDB and S3
3. **Configure TTL**: Adjust `CHECKPOINT_TTL_DAYS` based on compliance requirements
4. **Enable Versioning**: Keep S3 versioning enabled for audit trail
5. **Regular Backups**: Enable DynamoDB point-in-time recovery for critical deployments
6. **Test Recovery**: Periodically test failure recovery procedures
7. **Document Thread IDs**: Keep records of important thread IDs for audit purposes

## Support

For issues or questions:

1. Check CloudWatch logs for error messages
2. Verify IAM permissions are correctly configured
3. Test checkpoint integration locally first
4. Review the migration guide: `python src/checkpoint/migration.py`
5. Consult the main README for general troubleshooting

## References

- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [S3 Lifecycle Policies](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)
