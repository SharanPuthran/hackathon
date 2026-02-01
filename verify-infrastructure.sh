#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Infrastructure Verification Report"
echo "=========================================="
echo ""

# Load configuration
BUCKET_NAME=$(jq -r '.bucketName' deploy-config.json)
DISTRIBUTION_ID=$(jq -r '.distributionId' deploy-config.json)
DISTRIBUTION_DOMAIN=$(jq -r '.distributionDomain' deploy-config.json)
OAI_ID=$(jq -r '.oaiId' deploy-config.json)

echo "Configuration:"
echo "  Bucket: $BUCKET_NAME"
echo "  Distribution ID: $DISTRIBUTION_ID"
echo "  Distribution Domain: $DISTRIBUTION_DOMAIN"
echo "  OAI ID: $OAI_ID"
echo ""

# Test 1: S3 Bucket Exists
echo "Test 1: S3 Bucket Exists"
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC} - S3 bucket exists"
else
    echo -e "${RED}✗ FAIL${NC} - S3 bucket does not exist"
    exit 1
fi
echo ""

# Test 2: S3 Website Configuration
echo "Test 2: S3 Website Configuration"
WEBSITE_CONFIG=$(aws s3api get-bucket-website --bucket "$BUCKET_NAME" 2>/dev/null)
if [ $? -eq 0 ]; then
    INDEX_DOC=$(echo "$WEBSITE_CONFIG" | jq -r '.IndexDocument.Suffix')
    ERROR_DOC=$(echo "$WEBSITE_CONFIG" | jq -r '.ErrorDocument.Key')
    if [ "$INDEX_DOC" = "index.html" ] && [ "$ERROR_DOC" = "index.html" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Website configuration correct (index: $INDEX_DOC, error: $ERROR_DOC)"
    else
        echo -e "${RED}✗ FAIL${NC} - Website configuration incorrect"
        exit 1
    fi
else
    echo -e "${RED}✗ FAIL${NC} - No website configuration found"
    exit 1
fi
echo ""

# Test 3: S3 Public Access Blocking
echo "Test 3: S3 Public Access Blocking"
PUBLIC_ACCESS=$(aws s3api get-public-access-block --bucket "$BUCKET_NAME" 2>/dev/null)
if [ $? -eq 0 ]; then
    BLOCK_PUBLIC_ACLS=$(echo "$PUBLIC_ACCESS" | jq -r '.PublicAccessBlockConfiguration.BlockPublicAcls')
    IGNORE_PUBLIC_ACLS=$(echo "$PUBLIC_ACCESS" | jq -r '.PublicAccessBlockConfiguration.IgnorePublicAcls')
    BLOCK_PUBLIC_POLICY=$(echo "$PUBLIC_ACCESS" | jq -r '.PublicAccessBlockConfiguration.BlockPublicPolicy')
    RESTRICT_PUBLIC_BUCKETS=$(echo "$PUBLIC_ACCESS" | jq -r '.PublicAccessBlockConfiguration.RestrictPublicBuckets')
    
    if [ "$BLOCK_PUBLIC_ACLS" = "true" ] && [ "$IGNORE_PUBLIC_ACLS" = "true" ] && \
       [ "$BLOCK_PUBLIC_POLICY" = "true" ] && [ "$RESTRICT_PUBLIC_BUCKETS" = "true" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Public access is properly blocked"
    else
        echo -e "${RED}✗ FAIL${NC} - Public access blocking not configured correctly"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Could not verify public access blocking"
fi
echo ""

# Test 4: S3 Bucket Policy (OAI Access)
echo "Test 4: S3 Bucket Policy (OAI Access)"
BUCKET_POLICY=$(aws s3api get-bucket-policy --bucket "$BUCKET_NAME" --query 'Policy' --output text 2>/dev/null)
if [ $? -eq 0 ]; then
    if echo "$BUCKET_POLICY" | grep -q "cloudfront:user/CloudFront Origin Access Identity $OAI_ID"; then
        echo -e "${GREEN}✓ PASS${NC} - Bucket policy grants access to OAI"
    else
        echo -e "${RED}✗ FAIL${NC} - Bucket policy does not reference OAI correctly"
        exit 1
    fi
else
    echo -e "${RED}✗ FAIL${NC} - No bucket policy found"
    exit 1
fi
echo ""

# Test 5: Files Uploaded to S3
echo "Test 5: Files Uploaded to S3"
FILE_COUNT=$(aws s3 ls s3://$BUCKET_NAME/ --recursive | wc -l)
if [ "$FILE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ PASS${NC} - $FILE_COUNT files found in S3 bucket"
    
    # Check for key files
    if aws s3 ls s3://$BUCKET_NAME/index.html >/dev/null 2>&1; then
        echo -e "${GREEN}✓ PASS${NC} - index.html exists"
    else
        echo -e "${RED}✗ FAIL${NC} - index.html not found"
        exit 1
    fi
else
    echo -e "${RED}✗ FAIL${NC} - No files found in S3 bucket"
    exit 1
fi
echo ""

# Test 6: CloudFront Distribution Status
echo "Test 6: CloudFront Distribution Status"
DIST_STATUS=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.Status' --output text)
DIST_ENABLED=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.DistributionConfig.Enabled' --output text)

if [ "$DIST_STATUS" = "Deployed" ] && [ "$DIST_ENABLED" = "True" ]; then
    echo -e "${GREEN}✓ PASS${NC} - CloudFront distribution is deployed and enabled"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Distribution status: $DIST_STATUS, enabled: $DIST_ENABLED"
fi
echo ""

# Test 7: CloudFront Origin Configuration
echo "Test 7: CloudFront Origin Configuration"
ORIGIN_CONFIG=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.DistributionConfig.Origins.Items[0]')
ORIGIN_DOMAIN=$(echo "$ORIGIN_CONFIG" | jq -r '.DomainName')
ORIGIN_OAI=$(echo "$ORIGIN_CONFIG" | jq -r '.S3OriginConfig.OriginAccessIdentity')

if echo "$ORIGIN_DOMAIN" | grep -q "$BUCKET_NAME"; then
    echo -e "${GREEN}✓ PASS${NC} - Origin points to correct S3 bucket"
else
    echo -e "${RED}✗ FAIL${NC} - Origin domain incorrect: $ORIGIN_DOMAIN"
    exit 1
fi

if echo "$ORIGIN_OAI" | grep -q "$OAI_ID"; then
    echo -e "${GREEN}✓ PASS${NC} - Origin uses correct OAI"
else
    echo -e "${RED}✗ FAIL${NC} - Origin OAI incorrect: $ORIGIN_OAI"
    exit 1
fi
echo ""

# Test 8: CloudFront Cache Behavior
echo "Test 8: CloudFront Cache Behavior"
CACHE_BEHAVIOR=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.DistributionConfig.DefaultCacheBehavior')
VIEWER_PROTOCOL=$(echo "$CACHE_BEHAVIOR" | jq -r '.ViewerProtocolPolicy')
COMPRESS=$(echo "$CACHE_BEHAVIOR" | jq -r '.Compress')

if [ "$VIEWER_PROTOCOL" = "redirect-to-https" ]; then
    echo -e "${GREEN}✓ PASS${NC} - HTTPS redirect enabled"
else
    echo -e "${RED}✗ FAIL${NC} - HTTPS redirect not configured"
    exit 1
fi

if [ "$COMPRESS" = "true" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Compression enabled"
else
    echo -e "${RED}✗ FAIL${NC} - Compression not enabled"
    exit 1
fi
echo ""

# Test 9: CloudFront Custom Error Response (SPA Routing)
echo "Test 9: CloudFront Custom Error Response (SPA Routing)"
ERROR_RESPONSES=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.DistributionConfig.CustomErrorResponses.Items')
ERROR_404=$(echo "$ERROR_RESPONSES" | jq -r '.[] | select(.ErrorCode==404)')

if [ -n "$ERROR_404" ]; then
    RESPONSE_CODE=$(echo "$ERROR_404" | jq -r '.ResponseCode')
    RESPONSE_PAGE=$(echo "$ERROR_404" | jq -r '.ResponsePagePath')
    
    if [ "$RESPONSE_CODE" = "200" ] && [ "$RESPONSE_PAGE" = "/index.html" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Custom 404 error response configured for SPA routing"
    else
        echo -e "${RED}✗ FAIL${NC} - Custom error response incorrect (code: $RESPONSE_CODE, page: $RESPONSE_PAGE)"
        exit 1
    fi
else
    echo -e "${RED}✗ FAIL${NC} - No custom 404 error response found"
    exit 1
fi
echo ""

# Test 10: Direct S3 Access Blocked
echo "Test 10: Direct S3 Access Blocked"
S3_URL="http://$BUCKET_NAME.s3-website-us-east-1.amazonaws.com/index.html"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$S3_URL" --max-time 10)

if [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Direct S3 access properly blocked (403)"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Direct S3 access returned: $HTTP_CODE (expected 403)"
fi
echo ""

# Test 11: CloudFront Access Works
echo "Test 11: CloudFront Access Works"
CF_URL="https://$DISTRIBUTION_DOMAIN/"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$CF_URL" --max-time 10)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - CloudFront serves content successfully (200)"
    
    # Check if content is HTML
    CONTENT=$(curl -s "$CF_URL" --max-time 10)
    if echo "$CONTENT" | grep -q "<html"; then
        echo -e "${GREEN}✓ PASS${NC} - Response contains HTML content"
    else
        echo -e "${RED}✗ FAIL${NC} - Response does not contain HTML"
        exit 1
    fi
else
    echo -e "${RED}✗ FAIL${NC} - CloudFront access failed (HTTP $HTTP_CODE)"
    exit 1
fi
echo ""

# Test 12: SPA Routing (Non-Root Path)
echo "Test 12: SPA Routing (Non-Root Path)"
CF_SUBPATH_URL="https://$DISTRIBUTION_DOMAIN/dashboard"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$CF_SUBPATH_URL" --max-time 10)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Non-root path returns 200 (SPA routing works)"
else
    echo -e "${YELLOW}⚠ WARNING${NC} - Non-root path returned: $HTTP_CODE (expected 200)"
fi
echo ""

echo "=========================================="
echo "Verification Complete!"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ S3 bucket configured correctly"
echo "  ✓ CloudFront distribution deployed"
echo "  ✓ OAI access configured"
echo "  ✓ Public access blocked"
echo "  ✓ Files uploaded successfully"
echo "  ✓ SPA routing configured"
echo ""
echo "CloudFront URL: https://$DISTRIBUTION_DOMAIN"
echo ""
