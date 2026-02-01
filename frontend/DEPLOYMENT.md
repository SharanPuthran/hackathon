# SkyMarshal Frontend Deployment Guide

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Environment Setup](#environment-setup)
4. [Deployment Process](#deployment-process)
5. [Deployment Commands](#deployment-commands)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Topics](#advanced-topics)

---

## Overview

This guide explains how to deploy the SkyMarshal React frontend application to AWS infrastructure using:

- **Amazon S3**: Static website hosting for build artifacts
- **Amazon CloudFront**: Global CDN for low-latency content delivery
- **AWS CLI**: Infrastructure automation and deployment

The deployment is fully automated through the `deploy.sh` script, which handles:

- Building the React application with Vite
- Creating and configuring S3 bucket
- Uploading files with proper metadata and cache headers
- Creating CloudFront distribution with SPA routing support
- Cache invalidation and deployment verification

**Deployment Architecture:**

```
Developer → Build (Vite) → S3 Bucket (Private) → CloudFront CDN → Global Users
```

---

## Prerequisites

### Required Software

1. **Node.js 18+** and **npm 9+**

   ```bash
   # Check versions
   node --version  # Should be v18.0.0 or higher
   npm --version   # Should be 9.0.0 or higher

   # Install Node.js (if needed)
   # macOS: brew install node
   # Linux: sudo apt-get install nodejs npm
   # Windows: Download from https://nodejs.org/
   ```

2. **AWS CLI v2**

   ```bash
   # Check version
   aws --version  # Should be aws-cli/2.x.x or higher

   # Install AWS CLI
   # macOS: brew install awscli
   # Linux: curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && unzip awscliv2.zip && sudo ./aws/install
   # Windows: Download MSI installer from https://aws.amazon.com/cli/
   ```

3. **jq** (JSON processor)

   ```bash
   # Check if installed
   jq --version
   ```

   # Install jq

   # macOS: brew install jq

   # Linux: sudo apt-get install jq

   # Windows: Download from https://stedolan.github.io/jq/download/

   ```

   ```

### AWS Account Requirements

1. **AWS Account** with appropriate permissions:
   - `s3:*` - Full S3 access for bucket creation and management
   - `cloudfront:*` - CloudFront distribution management
   - `sts:GetCallerIdentity` - Identity verification

2. **AWS SSO or IAM Credentials** configured locally

3. **Sufficient AWS Service Quotas**:
   - S3 buckets: At least 1 available bucket
   - CloudFront distributions: At least 1 available distribution
   - Check quotas: `aws service-quotas list-service-quotas --service-code cloudfront`

### Project Dependencies

1. **Frontend dependencies installed**:

   ```bash
   cd frontend
   npm install
   ```

2. **Environment variables configured** (see [Environment Setup](#environment-setup))

---

## Environment Setup

### Step 1: Configure AWS Credentials

Choose one of the following authentication methods:

#### Option A: AWS SSO (Recommended)

```bash
# Configure AWS SSO
aws configure sso

# Follow the prompts:
# - SSO start URL: Your organization's SSO URL
# - SSO region: Your SSO region (e.g., us-east-1)
# - Account: Select your AWS account
# - Role: Select appropriate role with deployment permissions
# - CLI default region: us-east-1 (or your preferred region)
# - CLI output format: json

# Login to AWS SSO
aws sso login

# Verify credentials
aws sts get-caller-identity
```

#### Option B: IAM User Credentials

```bash
# Configure AWS credentials
aws configure

# Enter when prompted:
# - AWS Access Key ID: Your access key
# - AWS Secret Access Key: Your secret key
# - Default region name: us-east-1
# - Default output format: json

# Verify credentials
aws sts get-caller-identity
```

#### Option C: Environment Variables

```bash
# Set AWS credentials in your shell
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"

# Verify credentials
aws sts get-caller-identity
```

### Step 2: Configure Environment Variables

1. **Navigate to frontend directory**:

   ```bash
   cd frontend
   ```

2. **Create `.env` file from template**:

   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` file** with your actual values:

   ```bash
   # Required: Gemini API Key for AI features
   VITE_GEMINI_API_KEY=your_actual_gemini_api_key_here
   ```

4. **Verify `.env` file is in `.gitignore`**:
   ```bash
   # Check that .env is ignored
   git check-ignore .env
   # Should output: .env
   ```

**Important Security Notes:**

- Never commit `.env` files to version control
- API keys in `VITE_*` variables are embedded in the client bundle
- Only use API keys safe for client-side exposure
- Consider using API key restrictions in Google Cloud Console

### Step 3: Verify Prerequisites

Run the verification script to check all prerequisites:

```bash
# From project root
cd frontend
./validate-env.js  # Validates environment variables
```

Or manually verify:

```bash
# Check Node.js
node --version

# Check npm
npm --version

# Check AWS CLI
aws --version

# Check jq
jq --version

# Check AWS credentials
aws sts get-caller-identity

# Check environment variables
grep VITE_GEMINI_API_KEY .env
```

---

## Deployment Process

### Overview

The deployment process consists of 9 automated steps:

1. **AWS Credential Verification** - Validates AWS access
2. **Environment Variable Validation** - Checks required variables
3. **S3 Bucket Creation** - Creates storage bucket
4. **S3 Policy Configuration** - Sets up access policies
5. **File Upload** - Uploads build artifacts with metadata
6. **CloudFront Distribution** - Creates CDN distribution
7. **Configuration Verification** - Validates setup
8. **Cache Invalidation** - Clears CloudFront cache
9. **Deployment Verification** - Tests deployment health

### Step-by-Step Deployment

#### Step 1: Build the Application

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (if not already done)
npm install

# Build for production
npm run build

# Verify build output
ls -la dist/
```

**Expected output:**

- `dist/index.html` - Main HTML file
- `dist/assets/` - JavaScript, CSS, and other assets
- Files should have content hashes (e.g., `index-a1b2c3d4.js`)

#### Step 2: Run Deployment Script

```bash
# From project root
./deploy.sh

# Or specify environment (dev/prod)
./deploy.sh dev
./deploy.sh prod
```

**What happens during deployment:**

1. **Credential Check** (30 seconds)
   - Verifies AWS CLI is installed
   - Validates AWS credentials
   - Displays account ID and region

2. **Environment Validation** (10 seconds)
   - Checks for required `VITE_*` variables
   - Validates `.env` file exists

3. **S3 Bucket Setup** (1-2 minutes)
   - Creates bucket `skymarshal-frontend-368613657554`
   - Configures static website hosting
   - Sets index and error documents to `index.html`

4. **Policy Configuration** (30 seconds)
   - Removes public access blocks
   - Applies public read bucket policy
   - Enables CloudFront access

5. **File Upload** (2-5 minutes)
   - Syncs all files from `dist/` to S3
   - Sets Content-Type headers per file type
   - Applies Cache-Control strategies:
     - HTML: `no-cache, no-store, must-revalidate`
     - Hashed assets: `public, max-age=31536000, immutable`
     - Other files: `public, max-age=86400`

6. **CloudFront Creation** (15-20 minutes)
   - Creates distribution with S3 origin
   - Configures compression and HTTPS redirect
   - Sets up custom error response (404 → index.html)
   - Deploys to global edge locations

7. **Cache Invalidation** (3-5 minutes)
   - Invalidates `/index.html` and `/assets/*`
   - Ensures users get latest version

8. **Verification** (2-3 minutes)
   - Tests CloudFront URL returns 200
   - Verifies HTML content structure
   - Tests SPA routing on multiple paths
   - Confirms S3 access configuration

**Total deployment time:** 25-40 minutes (first deployment)
**Subsequent deployments:** 5-10 minutes (infrastructure already exists)

#### Step 3: Access Your Application

After successful deployment, the script outputs:

```
Deployment Summary:
  S3 Bucket: skymarshal-frontend-368613657554
  CloudFront Distribution ID: E1234567890ABC
  CloudFront URL: https://d1234567890abc.cloudfront.net

Note: CloudFront distribution is being deployed to edge locations.
This process takes 15-20 minutes. Once deployed, access your app at:
  https://d1234567890abc.cloudfront.net
```

**Access your application:**

```bash
# Open in browser
open https://d1234567890abc.cloudfront.net

# Or use curl to test
curl -I https://d1234567890abc.cloudfront.net
```

---

## Deployment Commands

### Basic Deployment

```bash
# Deploy to default environment (dev)
./deploy.sh

# Deploy to specific environment
./deploy.sh dev
./deploy.sh prod
```

### Build Only (No Deployment)

```bash
cd frontend
npm run build
```

### Upload Only (Skip Build)

```bash
# Manually upload after building
cd frontend
aws s3 sync dist/ s3://skymarshal-frontend-368613657554/ \
  --region us-east-1 \
  --delete
```

### Cache Invalidation Only

```bash
# Invalidate CloudFront cache manually
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/*"

# Invalidate specific paths
aws cloudfront create-invalidation \
  --distribution-id E1234567890ABC \
  --paths "/index.html" "/assets/*"
```

### Check Deployment Status

```bash
# Check CloudFront distribution status
aws cloudfront get-distribution \
  --id E1234567890ABC \
  --query 'Distribution.Status' \
  --output text

# Check S3 bucket contents
aws s3 ls s3://skymarshal-frontend-368613657554/ --recursive

# Check invalidation status
aws cloudfront get-invalidation \
  --distribution-id E1234567890ABC \
  --id I1234567890ABC
```

### Configuration Management

```bash
# View current deployment configuration
cat deploy-config.json

# Configuration includes:
# - bucketName: S3 bucket name
# - region: AWS region
# - distributionId: CloudFront distribution ID
# - distributionDomain: CloudFront domain name
```

---

## Verification

### Automated Verification

The deployment script automatically runs verification checks:

1. ✓ CloudFront distribution reaches "Deployed" status
2. ✓ CloudFront URL returns HTTP 200
3. ✓ Response contains valid HTML structure
4. ✓ SPA routing works for non-root paths
5. ✓ S3 access configuration is correct

### Manual Verification

#### Test Main Page

```bash
# Test CloudFront URL
curl -I https://d1234567890abc.cloudfront.net

# Expected: HTTP/2 200
# Expected headers:
# - content-type: text/html
# - x-cache: Hit from cloudfront (after first request)
```

#### Test SPA Routing

```bash
# Test non-root paths
curl -I https://d1234567890abc.cloudfront.net/dashboard
curl -I https://d1234567890abc.cloudfront.net/settings

# Expected: HTTP/2 200 (not 404)
# Should return index.html for client-side routing
```

#### Test Cache Headers

```bash
# Check index.html cache headers
curl -I https://d1234567890abc.cloudfront.net/index.html

# Expected: cache-control: no-cache, no-store, must-revalidate

# Check hashed asset cache headers
curl -I https://d1234567890abc.cloudfront.net/assets/index-a1b2c3d4.js

# Expected: cache-control: public, max-age=31536000, immutable
```

#### Test Compression

```bash
# Check if compression is enabled
curl -H "Accept-Encoding: gzip" -I https://d1234567890abc.cloudfront.net

# Expected: content-encoding: gzip or br
```

#### Verify S3 Direct Access

```bash
# Test direct S3 access
curl -I https://skymarshal-frontend-368613657554.s3.us-east-1.amazonaws.com/index.html

# Expected: HTTP/1.1 200 (public bucket policy allows direct access)
# Note: CloudFront is the primary access method
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue 1: AWS Authentication Failure

**Symptoms:**

```
[ERROR] AWS Error in AWS Credential Verification:
InvalidAccessKeyId: The AWS Access Key Id you provided does not exist
```

**Solutions:**

1. **Check AWS SSO login status:**

   ```bash
   aws sso login
   ```

2. **Verify credentials:**

   ```bash
   aws sts get-caller-identity
   ```

3. **Reconfigure AWS CLI:**

   ```bash
   aws configure
   # Or for SSO:
   aws configure sso
   ```

4. **Check environment variables:**

   ```bash
   echo $AWS_ACCESS_KEY_ID
   echo $AWS_SECRET_ACCESS_KEY
   ```

5. **Verify IAM permissions:**
   - Ensure your user/role has required permissions
   - Required: `s3:*`, `cloudfront:*`, `sts:GetCallerIdentity`

#### Issue 2: Missing Environment Variables

**Symptoms:**

```
[ERROR] Missing required environment variables:
  - VITE_GEMINI_API_KEY
```

**Solutions:**

1. **Create `.env` file:**

   ```bash
   cd frontend
   cp .env.example .env
   ```

2. **Add required variables:**

   ```bash
   echo "VITE_GEMINI_API_KEY=your_key_here" >> .env
   ```

3. **Verify file exists:**

   ```bash
   cat .env | grep VITE_GEMINI_API_KEY
   ```

4. **Check file location:**
   - `.env` must be in `frontend/` directory
   - Not in project root

#### Issue 3: Build Directory Not Found

**Symptoms:**

```
[ERROR] Build directory not found: /path/to/frontend/dist
```

**Solutions:**

1. **Build the application:**

   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. **Verify build output:**

   ```bash
   ls -la dist/
   ```

3. **Check for build errors:**

   ```bash
   npm run build 2>&1 | tee build.log
   ```

4. **Clear and rebuild:**
   ```bash
   rm -rf dist/ node_modules/
   npm install
   npm run build
   ```

#### Issue 4: S3 Bucket Already Exists

**Symptoms:**

```
[ERROR] Bucket Already Exists Error
The bucket name 'skymarshal-frontend-368613657554' is already in use
```

**Solutions:**

1. **Check if you own the bucket:**

   ```bash
   aws s3api head-bucket --bucket skymarshal-frontend-368613657554
   ```

2. **If you own it, deployment will continue automatically**

3. **If not, update bucket name in `deploy.sh`:**

   ```bash
   # Edit deploy.sh
   BUCKET_NAME="skymarshal-frontend-YOUR-ACCOUNT-ID"
   ```

4. **Use your AWS account ID:**
   ```bash
   ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
   echo "skymarshal-frontend-${ACCOUNT_ID}"
   ```

#### Issue 5: CloudFront Distribution Creation Failed

**Symptoms:**

```
[ERROR] AWS Error in CloudFront Distribution Creation:
TooManyDistributions: You have reached the maximum number of distributions
```

**Solutions:**

1. **Check existing distributions:**

   ```bash
   aws cloudfront list-distributions --query 'DistributionList.Items[*].[Id,DomainName,Status]' --output table
   ```

2. **Delete unused distributions:**

   ```bash
   # First disable the distribution
   aws cloudfront get-distribution-config --id E1234567890ABC > dist-config.json
   # Edit dist-config.json and set "Enabled": false
   aws cloudfront update-distribution --id E1234567890ABC --distribution-config file://dist-config.json --if-match ETAG

   # Wait for distribution to be disabled, then delete
   aws cloudfront delete-distribution --id E1234567890ABC --if-match ETAG
   ```

3. **Request quota increase:**
   - Go to AWS Service Quotas console
   - Request increase for CloudFront distributions

4. **Use existing distribution:**
   - Update `deploy-config.json` with existing distribution ID
   - Script will reuse existing distribution

#### Issue 6: Upload Fails with Access Denied

**Symptoms:**

```
[ERROR] Access Denied Error
Failed to upload files to S3
```

**Solutions:**

1. **Verify S3 permissions:**

   ```bash
   aws s3 ls s3://skymarshal-frontend-368613657554/
   ```

2. **Check IAM policy:**
   - Ensure `s3:PutObject` permission
   - Ensure `s3:PutObjectAcl` permission

3. **Verify bucket policy:**

   ```bash
   aws s3api get-bucket-policy --bucket skymarshal-frontend-368613657554
   ```

4. **Check public access block:**
   ```bash
   aws s3api get-public-access-block --bucket skymarshal-frontend-368613657554
   ```

#### Issue 7: Cache Invalidation Timeout

**Symptoms:**

```
[WARNING] Invalidation timeout reached (5 minutes)
Invalidation is still in progress but deployment will continue
```

**Solutions:**

1. **This is not critical** - deployment can continue
2. **Check invalidation status:**

   ```bash
   aws cloudfront get-invalidation \
     --distribution-id E1234567890ABC \
     --id I1234567890ABC
   ```

3. **Wait for completion:**
   - Invalidations typically complete in 5-15 minutes
   - Cache will expire naturally based on TTL

4. **Create manual invalidation if needed:**
   ```bash
   aws cloudfront create-invalidation \
     --distribution-id E1234567890ABC \
     --paths "/*"
   ```

#### Issue 8: SPA Routing Returns 404

**Symptoms:**

- Direct navigation to `/dashboard` returns 404
- Refresh on non-root path shows error

**Solutions:**

1. **Verify custom error response:**

   ```bash
   aws cloudfront get-distribution-config \
     --id E1234567890ABC \
     --query 'DistributionConfig.CustomErrorResponses'
   ```

2. **Expected configuration:**

   ```json
   {
     "ErrorCode": 404,
     "ResponsePagePath": "/index.html",
     "ResponseCode": "200"
   }
   ```

3. **Update distribution if needed:**
   - Get current config with ETag
   - Modify CustomErrorResponses
   - Update distribution

4. **Wait for deployment:**
   - Changes take 15-20 minutes to propagate

#### Issue 9: Stale Content After Deployment

**Symptoms:**

- Users see old version after deployment
- Changes not visible immediately

**Solutions:**

1. **Create cache invalidation:**

   ```bash
   aws cloudfront create-invalidation \
     --distribution-id E1234567890ABC \
     --paths "/*"
   ```

2. **Hard refresh in browser:**
   - Chrome/Firefox: Ctrl+Shift+R (Cmd+Shift+R on Mac)
   - Safari: Cmd+Option+R

3. **Clear browser cache:**
   - Or use incognito/private mode

4. **Check cache headers:**

   ```bash
   curl -I https://d1234567890abc.cloudfront.net/index.html
   ```

5. **Verify invalidation completed:**
   ```bash
   aws cloudfront list-invalidations --distribution-id E1234567890ABC
   ```

#### Issue 10: Deployment Script Fails Mid-Process

**Symptoms:**

```
[ERROR] Deployment failed with exit code 1
The following resources were created during this deployment:
  - cloudfront_distribution: E1234567890ABC
  - s3_bucket: skymarshal-frontend-368613657554
```

**Solutions:**

1. **Review error message** for specific failure point

2. **Rollback if prompted:**
   - Script offers automatic rollback
   - Choose 'y' to delete created resources
   - Choose 'n' to keep resources and retry

3. **Manual cleanup if needed:**

   ```bash
   # Empty and delete S3 bucket
   aws s3 rm s3://skymarshal-frontend-368613657554/ --recursive
   aws s3 rb s3://skymarshal-frontend-368613657554

   # Disable and delete CloudFront distribution
   # (requires multiple steps - see Issue 5)
   ```

4. **Retry deployment:**

   ```bash
   ./deploy.sh
   ```

5. **Check deployment state:**
   ```bash
   cat deploy-config.json
   ```

### Debugging Tips

#### Enable Verbose Logging

```bash
# Add debug output to deployment script
set -x  # Add to top of deploy.sh
./deploy.sh 2>&1 | tee deployment.log
```

#### Check AWS CloudTrail

```bash
# View recent API calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateDistribution \
  --max-results 10
```

#### Test AWS Connectivity

```bash
# Test S3 access
aws s3 ls

# Test CloudFront access
aws cloudfront list-distributions

# Test STS (credentials)
aws sts get-caller-identity
```

#### Validate Build Output

```bash
cd frontend/dist

# Check file structure
tree .

# Check file sizes
du -sh *

# Verify index.html
cat index.html | grep -i "root"

# Check for source maps (should not be in production)
find . -name "*.map"
```

---

## Advanced Topics

### Multiple Environments

Deploy to different environments (dev, staging, prod):

```bash
# Update deploy.sh to support environment-specific buckets
BUCKET_NAME="skymarshal-frontend-${ENVIRONMENT}-368613657554"

# Deploy to different environments
./deploy.sh dev
./deploy.sh staging
./deploy.sh prod
```

### Custom Domain Names

Add custom domain to CloudFront distribution:

1. **Create SSL certificate in ACM** (us-east-1 region):

   ```bash
   aws acm request-certificate \
     --domain-name skymarshal.example.com \
     --validation-method DNS \
     --region us-east-1
   ```

2. **Validate certificate** via DNS records

3. **Update CloudFront distribution:**

   ```bash
   # Add alternate domain names (CNAMEs)
   # Add SSL certificate ARN
   # Update via AWS Console or CLI
   ```

4. **Update DNS records:**
   ```
   skymarshal.example.com CNAME d1234567890abc.cloudfront.net
   ```

### CI/CD Integration

Integrate deployment into CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Deploy Frontend
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: "18"

      - name: Install dependencies
        run: cd frontend && npm ci

      - name: Build
        run: cd frontend && npm run build
        env:
          VITE_GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Deploy to AWS
        run: ./deploy.sh prod
```

### Monitoring and Logging

#### CloudFront Access Logs

Enable logging for CloudFront distribution:

```bash
# Create logging bucket
aws s3 mb s3://skymarshal-cloudfront-logs-368613657554

# Update distribution to enable logging
# Via AWS Console: Distribution Settings > Logging
```

#### CloudWatch Metrics

Monitor CloudFront metrics:

```bash
# View CloudFront metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/CloudFront \
  --metric-name Requests \
  --dimensions Name=DistributionId,Value=E1234567890ABC \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 3600 \
  --statistics Sum
```

### Cost Optimization

#### Estimate Costs

- **S3 Storage**: ~$0.023/GB/month
- **S3 Requests**: ~$0.0004/1000 GET requests
- **CloudFront Data Transfer**: ~$0.085/GB (first 10 TB)
- **CloudFront Requests**: ~$0.0075/10,000 HTTPS requests

#### Reduce Costs

1. **Use appropriate cache TTLs** - Reduce origin requests
2. **Enable compression** - Reduce data transfer
3. **Use CloudFront price class** - Limit edge locations if needed
4. **Clean up old distributions** - Delete unused resources

### Security Best Practices

1. **Use HTTPS only** - CloudFront redirects HTTP to HTTPS
2. **Rotate API keys regularly** - Update VITE_GEMINI_API_KEY
3. **Restrict API keys** - Use Google Cloud Console restrictions
4. **Enable CloudFront WAF** - Protect against common attacks
5. **Use signed URLs** - For private content (if needed)
6. **Monitor access logs** - Detect unusual patterns
7. **Keep dependencies updated** - Run `npm audit` regularly

### Performance Optimization

1. **Optimize build output:**

   ```bash
   # Analyze bundle size
   cd frontend
   npm run build -- --mode production

   # Use bundle analyzer
   npm install --save-dev rollup-plugin-visualizer
   ```

2. **Configure compression:**
   - CloudFront automatically compresses text-based content
   - Verify: `curl -H "Accept-Encoding: gzip" -I <url>`

3. **Use appropriate cache strategies:**
   - HTML: No cache (always fresh)
   - Hashed assets: Cache forever (immutable)
   - Other assets: Cache for 1 day

4. **Monitor performance:**
   - Use CloudFront reports in AWS Console
   - Monitor cache hit ratio
   - Track origin response times

---

## Additional Resources

### Documentation

- [AWS S3 Static Website Hosting](https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html)
- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [AWS CLI Reference](https://docs.aws.amazon.com/cli/)
- [Vite Build Documentation](https://vitejs.dev/guide/build.html)

### Support

For deployment issues:

1. Review this troubleshooting guide
2. Check AWS Service Health Dashboard
3. Review CloudTrail logs for API errors
4. Contact AWS Support (if you have a support plan)

### Configuration Files

- `deploy.sh` - Main deployment script
- `deploy-config.json` - Deployment state and configuration
- `frontend/.env` - Environment variables (not in git)
- `frontend/.env.example` - Environment variable template
- `frontend/vite.config.ts` - Vite build configuration

---

## Quick Reference

### Essential Commands

```bash
# Full deployment
./deploy.sh

# Build only
cd frontend && npm run build

# Upload only
aws s3 sync frontend/dist/ s3://skymarshal-frontend-368613657554/ --delete

# Invalidate cache
aws cloudfront create-invalidation --distribution-id E1234567890ABC --paths "/*"

# Check status
aws cloudfront get-distribution --id E1234567890ABC --query 'Distribution.Status'

# View logs
tail -f /tmp/deployment.log
```

### Important URLs

- **S3 Bucket**: `https://skymarshal-frontend-368613657554.s3.us-east-1.amazonaws.com`
- **S3 Website**: `http://skymarshal-frontend-368613657554.s3-website-us-east-1.amazonaws.com`
- **CloudFront**: `https://d1234567890abc.cloudfront.net` (from deploy-config.json)
- **AWS Console**: `https://console.aws.amazon.com/`

### Configuration Values

```json
{
  "bucketName": "skymarshal-frontend-368613657554",
  "region": "us-east-1",
  "distributionId": "E1234567890ABC",
  "distributionDomain": "d1234567890abc.cloudfront.net"
}
```

---

**Last Updated**: January 2024  
**Version**: 1.0.0  
**Maintained By**: SkyMarshal Development Team
