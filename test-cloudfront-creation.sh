#!/bin/bash

################################################################################
# CloudFront Distribution Creation Test Script
#
# This script tests the CloudFront distribution creation functionality
# without actually creating resources (dry-run mode where possible)
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/deploy.sh" 2>/dev/null || true

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CloudFront Distribution Creation Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Test 1: Verify AWS CLI is available
echo -e "${BLUE}Test 1: Verify AWS CLI availability${NC}"
if command -v aws &> /dev/null; then
    echo -e "${GREEN}✓ AWS CLI is installed${NC}"
    aws --version
else
    echo -e "${RED}✗ AWS CLI is not installed${NC}"
    exit 1
fi
echo ""

# Test 2: Verify AWS credentials
echo -e "${BLUE}Test 2: Verify AWS credentials${NC}"
if aws sts get-caller-identity --region us-east-1 &> /dev/null; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --region us-east-1)
    echo -e "${GREEN}✓ AWS credentials are valid${NC}"
    echo "  Account ID: ${ACCOUNT_ID}"
else
    echo -e "${RED}✗ AWS credentials are not configured${NC}"
    echo "  Please run 'aws sso login' or configure credentials"
    exit 1
fi
echo ""

# Test 3: Check if S3 bucket exists
echo -e "${BLUE}Test 3: Check S3 bucket existence${NC}"
BUCKET_NAME="skymarshal-frontend-368613657554"
if aws s3api head-bucket --bucket "${BUCKET_NAME}" --region us-east-1 2>/dev/null; then
    echo -e "${GREEN}✓ S3 bucket exists: ${BUCKET_NAME}${NC}"
else
    echo -e "${YELLOW}⚠ S3 bucket does not exist: ${BUCKET_NAME}${NC}"
    echo "  This is expected if you haven't run the deployment yet"
fi
echo ""

# Test 4: Check for existing CloudFront distribution
echo -e "${BLUE}Test 4: Check for existing CloudFront distribution${NC}"
CONFIG_FILE="${SCRIPT_DIR}/deploy-config.json"
if [ -f "${CONFIG_FILE}" ]; then
    DISTRIBUTION_ID=$(jq -r '.distributionId // empty' "${CONFIG_FILE}" 2>/dev/null)
    if [ -n "${DISTRIBUTION_ID}" ]; then
        echo "  Found distribution ID in config: ${DISTRIBUTION_ID}"
        
        # Check if distribution exists
        if aws cloudfront get-distribution --id "${DISTRIBUTION_ID}" --region us-east-1 > /dev/null 2>&1; then
            echo -e "${GREEN}✓ CloudFront distribution exists${NC}"
            
            # Get distribution details
            DIST_DETAILS=$(aws cloudfront get-distribution --id "${DISTRIBUTION_ID}" --region us-east-1 2>&1)
            DOMAIN_NAME=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DomainName')
            STATUS=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.Status')
            ENABLED=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.Enabled')
            
            echo "  Domain: ${DOMAIN_NAME}"
            echo "  Status: ${STATUS}"
            echo "  Enabled: ${ENABLED}"
            
            # Check configuration
            COMPRESSION=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.DefaultCacheBehavior.Compress')
            VIEWER_PROTOCOL=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.DefaultCacheBehavior.ViewerProtocolPolicy')
            
            echo "  Compression: ${COMPRESSION}"
            echo "  Viewer Protocol: ${VIEWER_PROTOCOL}"
            
            # Check custom error response
            ERROR_CODE=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ErrorCode // "not set"')
            RESPONSE_PAGE=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ResponsePagePath // "not set"')
            RESPONSE_CODE=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ResponseCode // "not set"')
            
            echo "  Custom Error Response:"
            echo "    Error Code: ${ERROR_CODE}"
            echo "    Response Page: ${RESPONSE_PAGE}"
            echo "    Response Code: ${RESPONSE_CODE}"
            
            # Check OAI
            OAI=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.Origins.Items[0].S3OriginConfig.OriginAccessIdentity // "not set"')
            echo "  OAI: ${OAI}"
            
            # Verify configuration matches requirements
            echo ""
            echo -e "${BLUE}Configuration Verification:${NC}"
            
            if [ "${COMPRESSION}" = "true" ]; then
                echo -e "${GREEN}✓ Compression is enabled${NC}"
            else
                echo -e "${RED}✗ Compression is not enabled${NC}"
            fi
            
            if [ "${VIEWER_PROTOCOL}" = "redirect-to-https" ]; then
                echo -e "${GREEN}✓ HTTPS redirect is configured${NC}"
            else
                echo -e "${RED}✗ HTTPS redirect is not configured${NC}"
            fi
            
            if [ "${ERROR_CODE}" = "404" ] && [ "${RESPONSE_PAGE}" = "/index.html" ] && [ "${RESPONSE_CODE}" = "200" ]; then
                echo -e "${GREEN}✓ SPA routing (404 → index.html) is configured${NC}"
            else
                echo -e "${RED}✗ SPA routing is not configured correctly${NC}"
            fi
            
            if [ "${OAI}" != "not set" ] && [ -n "${OAI}" ]; then
                echo -e "${GREEN}✓ Origin Access Identity is configured${NC}"
            else
                echo -e "${RED}✗ Origin Access Identity is not configured${NC}"
            fi
        else
            echo -e "${YELLOW}⚠ Distribution ID in config but distribution not found${NC}"
            echo "  The distribution may have been deleted"
        fi
    else
        echo -e "${YELLOW}⚠ No distribution ID found in config${NC}"
    fi
else
    echo -e "${YELLOW}⚠ No config file found${NC}"
    echo "  This is expected if you haven't run the deployment yet"
fi
echo ""

# Test 5: Check for existing OAI
echo -e "${BLUE}Test 5: Check for existing Origin Access Identity${NC}"
if [ -f "${CONFIG_FILE}" ]; then
    OAI_ID=$(jq -r '.oaiId // empty' "${CONFIG_FILE}" 2>/dev/null)
    if [ -n "${OAI_ID}" ]; then
        echo "  Found OAI ID in config: ${OAI_ID}"
        
        if aws cloudfront get-cloud-front-origin-access-identity --id "${OAI_ID}" --region us-east-1 > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Origin Access Identity exists${NC}"
            
            OAI_DETAILS=$(aws cloudfront get-cloud-front-origin-access-identity --id "${OAI_ID}" --region us-east-1 2>&1)
            S3_CANONICAL_USER_ID=$(echo "${OAI_DETAILS}" | jq -r '.CloudFrontOriginAccessIdentity.S3CanonicalUserId')
            
            echo "  S3 Canonical User ID: ${S3_CANONICAL_USER_ID}"
        else
            echo -e "${YELLOW}⚠ OAI ID in config but OAI not found${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No OAI ID found in config${NC}"
    fi
else
    echo -e "${YELLOW}⚠ No config file found${NC}"
fi
echo ""

# Test 6: Verify S3 bucket policy (if bucket exists)
echo -e "${BLUE}Test 6: Verify S3 bucket policy${NC}"
if aws s3api head-bucket --bucket "${BUCKET_NAME}" --region us-east-1 2>/dev/null; then
    if aws s3api get-bucket-policy --bucket "${BUCKET_NAME}" --region us-east-1 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Bucket policy exists${NC}"
        
        POLICY=$(aws s3api get-bucket-policy --bucket "${BUCKET_NAME}" --region us-east-1 --query Policy --output text 2>&1)
        
        # Check if policy allows OAI access
        if echo "${POLICY}" | grep -q "CanonicalUser"; then
            echo -e "${GREEN}✓ Policy allows OAI access (CanonicalUser principal)${NC}"
        elif echo "${POLICY}" | grep -q "PublicReadGetObject"; then
            echo -e "${YELLOW}⚠ Policy allows public access (not OAI-based)${NC}"
            echo "  This will be updated when CloudFront is created"
        else
            echo -e "${YELLOW}⚠ Policy exists but type is unclear${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No bucket policy found${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Bucket does not exist, skipping policy check${NC}"
fi
echo ""

# Test 7: Summary and recommendations
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ -n "${DISTRIBUTION_ID}" ] && aws cloudfront get-distribution --id "${DISTRIBUTION_ID}" --region us-east-1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ CloudFront distribution is already created${NC}"
    echo ""
    echo "Distribution URL: https://$(aws cloudfront get-distribution --id "${DISTRIBUTION_ID}" --region us-east-1 --query 'Distribution.DomainName' --output text)"
    echo ""
    echo "To update the distribution, you can:"
    echo "  1. Run the deployment script again (it will use the existing distribution)"
    echo "  2. Manually update via AWS Console"
    echo "  3. Delete the distribution and run deployment to create a new one"
else
    echo -e "${YELLOW}⚠ CloudFront distribution not found${NC}"
    echo ""
    echo "To create the CloudFront distribution:"
    echo "  1. Ensure S3 bucket is created and files are uploaded"
    echo "  2. Run: ./deploy.sh"
    echo ""
    echo "The deployment script will:"
    echo "  - Create Origin Access Identity (OAI)"
    echo "  - Update S3 bucket policy to allow OAI access"
    echo "  - Enable public access block on S3"
    echo "  - Create CloudFront distribution with:"
    echo "    • S3 origin with OAI"
    echo "    • HTTPS redirect"
    echo "    • Compression enabled"
    echo "    • Custom error response for SPA routing (404 → index.html)"
    echo "  - Store distribution ID in deploy-config.json"
fi
echo ""

echo -e "${GREEN}All tests completed!${NC}"
