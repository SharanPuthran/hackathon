# Configuration Management

## Overview

The SkyMarshal frontend deployment uses a configuration file (`deploy-config.json`) to store deployment settings and ensure idempotent operations. This document describes the configuration management system and how it supports reproducible deployments.

## Configuration File

**Location**: `deploy-config.json` (project root)

**Purpose**: Store deployment state and resource identifiers to enable idempotent deployments

**Format**: JSON

### Configuration Schema

```json
{
  "bucketName": "string", // S3 bucket name
  "region": "string", // AWS region (e.g., "us-east-1")
  "accessType": "string", // Access type ("public" or "oai")
  "distributionId": "string", // CloudFront distribution ID
  "distributionDomain": "string", // CloudFront domain name
  "distributionStatus": "string", // Distribution status ("InProgress" or "Deployed")
  "oaiId": "string", // Origin Access Identity ID (optional)
  "oaiCanonicalUserId": "string", // OAI canonical user ID (optional)
  "lastInvalidationId": "string", // Last cache invalidation ID
  "lastInvalidationTime": "string" // Last invalidation timestamp (ISO 8601)
}
```

### Example Configuration

```json
{
  "bucketName": "skymarshal-frontend-368613657554",
  "region": "us-east-1",
  "accessType": "public",
  "distributionId": "E1UPCWP154P397",
  "distributionDomain": "dimegvpe26p0m.cloudfront.net",
  "distributionStatus": "Deployed",
  "lastInvalidationId": "I4EKQVMIFAL9MZSD8IQ1MR7FO5",
  "lastInvalidationTime": "2026-02-01T08:11:24.621000+00:00"
}
```

## Configuration Management Functions

The deployment script provides two core functions for configuration management:

### save_to_config()

Saves a key-value pair to the configuration file.

**Usage**:

```bash
save_to_config "key" "value"
```

**Example**:

```bash
save_to_config "bucketName" "skymarshal-frontend-368613657554"
save_to_config "distributionId" "E1UPCWP154P397"
```

**Behavior**:

- Creates configuration file if it doesn't exist
- Updates existing keys or adds new keys
- Preserves other keys in the configuration
- Uses `jq` for safe JSON manipulation

### load_from_config()

Loads a value from the configuration file.

**Usage**:

```bash
value=$(load_from_config "key")
```

**Example**:

```bash
BUCKET_NAME=$(load_from_config "bucketName")
DISTRIBUTION_ID=$(load_from_config "distributionId")
```

**Behavior**:

- Returns the value if key exists
- Returns empty string if key doesn't exist
- Returns empty string if configuration file doesn't exist
- Safe to use in conditionals

## Idempotency

The configuration management system enables idempotent deployments by:

1. **Resource Existence Checks**: Before creating resources, the script checks if they already exist using configuration values
2. **Reusing Existing Resources**: If resources exist, they are reused instead of creating duplicates
3. **Stable Configuration**: Running deployment multiple times produces the same configuration
4. **No Duplicate Resources**: The same S3 bucket and CloudFront distribution are used across deployments

### Idempotency Checks

#### S3 Bucket

```bash
# Check if bucket already exists
if bucket_exists "${BUCKET_NAME}"; then
    log_info "Bucket ${BUCKET_NAME} already exists"
    # Skip creation, verify configuration
else
    # Create new bucket
fi
```

#### CloudFront Distribution

```bash
# Check if distribution already exists in config
local existing_distribution_id=$(load_from_config "distributionId")

if [ -n "${existing_distribution_id}" ]; then
    # Verify distribution still exists
    if aws cloudfront get-distribution --id "${existing_distribution_id}" > /dev/null 2>&1; then
        log_success "Using existing CloudFront distribution: ${existing_distribution_id}"
        DISTRIBUTION_ID="${existing_distribution_id}"
        return 0
    fi
fi

# Create new distribution if needed
```

#### Bucket Policy

```bash
# Check if policy is already configured
local existing_policy=$(aws s3api get-bucket-policy --bucket "${BUCKET_NAME}" 2>/dev/null)

if [ $? -eq 0 ]; then
    # Check if the policy contains the expected statement
    if echo "${existing_policy}" | grep -q "PublicReadGetObject"; then
        log_success "Bucket policy is already configured correctly"
        return 0
    fi
fi

# Apply policy if needed
```

#### Website Configuration

```bash
# Check if website hosting is already configured
local existing_website=$(aws s3api get-bucket-website --bucket "${BUCKET_NAME}" 2>/dev/null)

if [ $? -eq 0 ]; then
    # Check if configuration is correct
    local index_doc=$(echo "${existing_website}" | jq -r '.IndexDocument.Suffix // empty')
    local error_doc=$(echo "${existing_website}" | jq -r '.ErrorDocument.Key // empty')

    if [ "${index_doc}" = "index.html" ] && [ "${error_doc}" = "index.html" ]; then
        log_success "Static website hosting already configured correctly"
        return 0
    fi
fi

# Apply configuration if needed
```

## Testing Idempotency

### Quick Test

Run the idempotency verification test:

```bash
./test-idempotency.sh
```

This test verifies:

- Configuration file exists and is complete
- All required fields are present
- Resources exist and are accessible
- Idempotency functions are implemented
- Configuration values remain stable

### Full Test

Run the full idempotency test (actually runs deployment twice):

```bash
./test-full-idempotency.sh
```

This test verifies:

- Second deployment completes without errors
- No duplicate resources are created
- Configuration remains stable
- All operations are idempotent
- Deployment logs show idempotent behavior

## Version Control

The configuration file should be included in version control to:

1. **Track Deployment State**: Know which resources are deployed
2. **Team Collaboration**: Share deployment configuration across team
3. **Disaster Recovery**: Recreate deployment from configuration
4. **Audit Trail**: Track changes to deployment configuration

### .gitignore Considerations

The `deploy-config.json` file **should be committed** to version control because:

- It contains resource identifiers, not secrets
- It enables reproducible deployments
- It documents the current deployment state

However, ensure that:

- `.env` files are **NOT** committed (contain secrets)
- AWS credentials are **NOT** in the configuration
- API keys are **NOT** in the configuration

## Configuration Updates

### Manual Updates

You can manually edit `deploy-config.json` if needed:

```bash
# Edit configuration
vim deploy-config.json

# Verify JSON is valid
jq empty deploy-config.json

# Run deployment to apply changes
./deploy.sh
```

### Programmatic Updates

Use the configuration functions in scripts:

```bash
# Load current value
CURRENT_BUCKET=$(load_from_config "bucketName")

# Update value
save_to_config "bucketName" "new-bucket-name"

# Verify update
NEW_BUCKET=$(load_from_config "bucketName")
echo "Updated bucket: ${CURRENT_BUCKET} → ${NEW_BUCKET}"
```

## Troubleshooting

### Configuration File Missing

If `deploy-config.json` is missing:

1. Run deployment to create it: `./deploy.sh`
2. Configuration will be created automatically
3. All resource identifiers will be saved

### Configuration Corrupted

If configuration is corrupted (invalid JSON):

1. Backup the file: `cp deploy-config.json deploy-config.json.backup`
2. Fix JSON syntax: `vim deploy-config.json`
3. Validate: `jq empty deploy-config.json`
4. Or delete and recreate: `rm deploy-config.json && ./deploy.sh`

### Configuration Out of Sync

If configuration doesn't match actual resources:

1. Check actual resources:

   ```bash
   aws s3 ls | grep skymarshal-frontend
   aws cloudfront list-distributions
   ```

2. Update configuration manually:

   ```bash
   save_to_config "bucketName" "actual-bucket-name"
   save_to_config "distributionId" "actual-distribution-id"
   ```

3. Run deployment to verify: `./deploy.sh`

### Multiple Deployments

If you have multiple deployments (dev, staging, prod):

1. Use separate configuration files:

   ```bash
   deploy-config-dev.json
   deploy-config-staging.json
   deploy-config-prod.json
   ```

2. Modify deployment script to use environment-specific config:

   ```bash
   CONFIG_FILE="${SCRIPT_DIR}/deploy-config-${ENVIRONMENT}.json"
   ```

3. Run with environment parameter:
   ```bash
   ./deploy.sh dev
   ./deploy.sh staging
   ./deploy.sh prod
   ```

## Best Practices

1. **Commit Configuration**: Always commit `deploy-config.json` to version control
2. **Verify After Changes**: Run `./test-idempotency.sh` after manual configuration changes
3. **Backup Before Major Changes**: Copy configuration before major infrastructure changes
4. **Document Custom Fields**: If adding custom fields, document them in this file
5. **Use Consistent Naming**: Follow the existing naming convention for new fields
6. **Validate JSON**: Always validate JSON after manual edits using `jq empty`
7. **Test Idempotency**: Run `./test-full-idempotency.sh` before merging deployment changes

## Requirements Satisfied

This configuration management system satisfies the following requirements:

- **Requirement 10.1**: Infrastructure defined as code (configuration file)
- **Requirement 10.2**: S3 bucket settings in configuration
- **Requirement 10.3**: CloudFront distribution settings in configuration
- **Requirement 10.4**: Updates applied idempotently (checks before creating)
- **Requirement 10.5**: Configuration stored in version control

## Related Documentation

- [Error Handling Guide](ERROR_HANDLING_GUIDE.md)
- [Deployment README](README.md)
- [Task Completion Summaries](TASK_*_COMPLETION_SUMMARY.md)
