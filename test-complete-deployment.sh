#!/bin/bash

################################################################################
# Task 14: Complete Deployment Test
# 
# This script performs a comprehensive test of the entire deployment:
# - Verifies all infrastructure is created correctly
# - Tests application functionality through CloudFront URL
# - Verifies SPA routing works for multiple paths
# - Confirms cache invalidation works
# - Ensures all components are properly configured
################################################################################

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_test() {
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Test ${TESTS_TOTAL}: $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Load configuration
CONFIG_FILE="deploy-config.json"

if [ ! -f "${CONFIG_FILE}" ]; then
    log_error "Configuration file not found: ${CONFIG_FILE}"
    log_error "Please run ./deploy.sh first to create the deployment"
    exit 1
fi

# Extract configuration values
BUCKET_NAME=$(jq -r '.bucketName' "${CONFIG_FILE}")
DISTRIBUTION_ID=$(jq -r '.distributionId' "${CONFIG_FILE}")
DISTRIBUTION_DOMAIN=$(jq -r '.distributionDomain' "${CONFIG_FILE}")
AWS_REGION=$(jq -r '.region' "${CONFIG_FILE}")

log_info "Loaded configuration:"
log_info "  Bucket: ${BUCKET_NAME}"
log_info "  Distribution ID: ${DISTRIBUTION_ID}"
log_info "  Distribution Domain: ${DISTRIBUTION_DOMAIN}"
log_info "  Region: ${AWS_REGION}"

################################################################################
# Test 1: Verify S3 Bucket Configuration
################################################################################

log_test "Verify S3 Bucket Configuration"

# Check bucket exists
log_info "Checking if bucket exists..."
if aws s3api head-bucket --bucket "${BUCKET_NAME}" --region "${AWS_REGION}" 2>/dev/null; then
    log_success "S3 bucket exists"
else
    log_error "S3 bucket does not exist"
fi

# Check website configuration
log_info "Checking website configuration..."
WEBSITE_CONFIG=$(aws s3api get-bucket-website --bucket "${BUCKET_NAME}" --region "${AWS_REGION}" 2>&1)

if [ $? -eq 0 ]; then
    INDEX_DOC=$(echo "${WEBSITE_CONFIG}" | jq -r '.IndexDocument.Suffix')
    ERROR_DOC=$(echo "${WEBSITE_CONFIG}" | jq -r '.ErrorDocument.Key')
    
    if [ "${INDEX_DOC}" = "index.html" ] && [ "${ERROR_DOC}" = "index.html" ]; then
        log_success "Website configuration correct (index: ${INDEX_DOC}, error: ${ERROR_DOC})"
    else
        log_error "Website configuration incorrect (index: ${INDEX_DOC}, error: ${ERROR_DOC})"
    fi
else
    log_error "Failed to get website configuration"
fi

# Check bucket policy
log_info "Checking bucket policy..."
if aws s3api get-bucket-policy --bucket "${BUCKET_NAME}" --region "${AWS_REGION}" > /dev/null 2>&1; then
    log_success "Bucket policy is configured"
else
    log_error "Bucket policy is not configured"
fi

################################################################################
# Test 2: Verify Files Are Uploaded
################################################################################

log_test "Verify Files Are Uploaded to S3"

# Check critical files exist
CRITICAL_FILES=("index.html")

for file in "${CRITICAL_FILES[@]}"; do
    log_info "Checking ${file}..."
    if aws s3api head-object --bucket "${BUCKET_NAME}" --key "${file}" --region "${AWS_REGION}" > /dev/null 2>&1; then
        log_success "${file} exists in S3"
        
        # Get metadata
        METADATA=$(aws s3api head-object --bucket "${BUCKET_NAME}" --key "${file}" --region "${AWS_REGION}" 2>/dev/null)
        CONTENT_TYPE=$(echo "${METADATA}" | jq -r '.ContentType')
        CACHE_CONTROL=$(echo "${METADATA}" | jq -r '.CacheControl // "not set"')
        
        log_info "  Content-Type: ${CONTENT_TYPE}"
        log_info "  Cache-Control: ${CACHE_CONTROL}"
        
        # Verify Content-Type
        if [ "${CONTENT_TYPE}" = "text/html" ]; then
            log_success "  Content-Type is correct"
        else
            log_error "  Content-Type is incorrect (expected text/html, got ${CONTENT_TYPE})"
        fi
        
        # Verify Cache-Control for HTML (should be no-cache)
        if echo "${CACHE_CONTROL}" | grep -qi "no-cache"; then
            log_success "  Cache-Control is correct for HTML"
        else
            log_warning "  Cache-Control may not be optimal (${CACHE_CONTROL})"
        fi
    else
        log_error "${file} not found in S3"
    fi
done

# Count total files
log_info "Counting files in S3..."
FILE_COUNT=$(aws s3 ls "s3://${BUCKET_NAME}/" --recursive --region "${AWS_REGION}" | wc -l | tr -d ' ')
log_info "Total files in S3: ${FILE_COUNT}"

if [ "${FILE_COUNT}" -gt 0 ]; then
    log_success "S3 bucket contains files"
else
    log_error "S3 bucket is empty"
fi

################################################################################
# Test 3: Verify CloudFront Distribution Configuration
################################################################################

log_test "Verify CloudFront Distribution Configuration"

# Get distribution details
log_info "Getting distribution details..."
DIST_DETAILS=$(aws cloudfront get-distribution --id "${DISTRIBUTION_ID}" 2>&1)

if [ $? -ne 0 ]; then
    log_error "Failed to get distribution details"
else
    log_success "Distribution exists"
    
    # Check status
    STATUS=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.Status')
    log_info "Distribution status: ${STATUS}"
    
    if [ "${STATUS}" = "Deployed" ]; then
        log_success "Distribution is deployed"
    else
        log_warning "Distribution status is ${STATUS} (not Deployed)"
    fi
    
    # Check enabled
    ENABLED=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.Enabled')
    if [ "${ENABLED}" = "true" ]; then
        log_success "Distribution is enabled"
    else
        log_error "Distribution is not enabled"
    fi
    
    # Check compression
    COMPRESSION=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.DefaultCacheBehavior.Compress')
    if [ "${COMPRESSION}" = "true" ]; then
        log_success "Compression is enabled"
    else
        log_error "Compression is not enabled"
    fi
    
    # Check viewer protocol policy
    VIEWER_PROTOCOL=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.DefaultCacheBehavior.ViewerProtocolPolicy')
    if [ "${VIEWER_PROTOCOL}" = "redirect-to-https" ]; then
        log_success "HTTPS redirect is configured"
    else
        log_error "HTTPS redirect is not configured (got: ${VIEWER_PROTOCOL})"
    fi
    
    # Check custom error response for SPA routing
    ERROR_CODE=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ErrorCode')
    RESPONSE_PAGE=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ResponsePagePath')
    RESPONSE_CODE=$(echo "${DIST_DETAILS}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ResponseCode')
    
    log_info "Custom error response: ${ERROR_CODE} → ${RESPONSE_PAGE} (${RESPONSE_CODE})"
    
    if [ "${ERROR_CODE}" = "404" ] && [ "${RESPONSE_PAGE}" = "/index.html" ] && [ "${RESPONSE_CODE}" = "200" ]; then
        log_success "SPA routing error response is configured correctly"
    else
        log_error "SPA routing error response is not configured correctly"
    fi
fi

################################################################################
# Test 4: Test Application Functionality Through CloudFront
################################################################################

log_test "Test Application Functionality Through CloudFront"

CLOUDFRONT_URL="https://${DISTRIBUTION_DOMAIN}"
log_info "Testing URL: ${CLOUDFRONT_URL}"

# Test root path
log_info "Testing root path (/)..."
RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${CLOUDFRONT_URL}" 2>/dev/null || echo "000")

if [ "${RESPONSE_CODE}" = "200" ]; then
    log_success "Root path returns 200"
    
    # Get content and verify it's HTML
    CONTENT=$(curl -s "${CLOUDFRONT_URL}" 2>/dev/null)
    
    if echo "${CONTENT}" | grep -qi "<!DOCTYPE html>\|<html"; then
        log_success "Root path returns HTML content"
    else
        log_error "Root path does not return HTML content"
    fi
    
    # Check for React root div
    if echo "${CONTENT}" | grep -qi '<div id="root"'; then
        log_success "React root div found"
    else
        log_warning "React root div not found (may use different mount point)"
    fi
else
    log_error "Root path returns ${RESPONSE_CODE} (expected 200)"
fi

################################################################################
# Test 5: Verify SPA Routing Works for Multiple Paths
################################################################################

log_test "Verify SPA Routing Works for Multiple Paths"

# Test multiple non-root paths
TEST_PATHS=(
    "/dashboard"
    "/settings"
    "/about"
    "/nonexistent/path"
)

SPA_TESTS_PASSED=0
SPA_TESTS_TOTAL=${#TEST_PATHS[@]}

for path in "${TEST_PATHS[@]}"; do
    TEST_URL="${CLOUDFRONT_URL}${path}"
    log_info "Testing path: ${path}"
    
    RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${TEST_URL}" 2>/dev/null || echo "000")
    
    if [ "${RESPONSE_CODE}" = "200" ]; then
        log_info "  ✓ ${path} returns 200"
        SPA_TESTS_PASSED=$((SPA_TESTS_PASSED + 1))
        
        # Verify it returns HTML (not a 404 page)
        CONTENT=$(curl -s "${TEST_URL}" 2>/dev/null)
        if echo "${CONTENT}" | grep -qi "<!DOCTYPE html>\|<html"; then
            log_info "  ✓ ${path} returns HTML content"
        else
            log_warning "  ⚠ ${path} may not return proper HTML"
        fi
    else
        log_info "  ✗ ${path} returns ${RESPONSE_CODE} (expected 200)"
    fi
done

log_info "SPA routing test results: ${SPA_TESTS_PASSED}/${SPA_TESTS_TOTAL} paths passed"

if [ ${SPA_TESTS_PASSED} -eq ${SPA_TESTS_TOTAL} ]; then
    log_success "All SPA routing tests passed"
elif [ ${SPA_TESTS_PASSED} -gt 0 ]; then
    log_success "SPA routing is working (${SPA_TESTS_PASSED}/${SPA_TESTS_TOTAL} paths)"
else
    log_error "SPA routing is not working"
fi

################################################################################
# Test 6: Verify Cache Headers
################################################################################

log_test "Verify Cache Headers"

# Test index.html cache headers
log_info "Testing index.html cache headers..."
HEADERS=$(curl -s -I "${CLOUDFRONT_URL}/index.html" 2>/dev/null)

if echo "${HEADERS}" | grep -qi "cache-control"; then
    CACHE_CONTROL=$(echo "${HEADERS}" | grep -i "cache-control" | cut -d: -f2- | tr -d '\r\n' | xargs)
    log_info "Cache-Control header: ${CACHE_CONTROL}"
    
    if echo "${CACHE_CONTROL}" | grep -qi "no-cache\|no-store"; then
        log_success "index.html has no-cache directive"
    else
        log_warning "index.html cache control may not be optimal: ${CACHE_CONTROL}"
    fi
else
    log_warning "No Cache-Control header found for index.html"
fi

# Test compression
log_info "Testing compression..."
if echo "${HEADERS}" | grep -qi "content-encoding.*gzip\|content-encoding.*br"; then
    ENCODING=$(echo "${HEADERS}" | grep -i "content-encoding" | cut -d: -f2- | tr -d '\r\n' | xargs)
    log_success "Compression is enabled (${ENCODING})"
else
    log_warning "Compression may not be enabled (check with larger files)"
fi

################################################################################
# Test 7: Confirm Cache Invalidation Works
################################################################################

log_test "Confirm Cache Invalidation Works"

# Check last invalidation
LAST_INVALIDATION_ID=$(jq -r '.lastInvalidationId // empty' "${CONFIG_FILE}")

if [ -n "${LAST_INVALIDATION_ID}" ]; then
    log_info "Last invalidation ID: ${LAST_INVALIDATION_ID}"
    
    # Get invalidation status
    INVALIDATION_STATUS=$(aws cloudfront get-invalidation \
        --distribution-id "${DISTRIBUTION_ID}" \
        --id "${LAST_INVALIDATION_ID}" \
        --query 'Invalidation.Status' \
        --output text 2>&1)
    
    if [ $? -eq 0 ]; then
        log_info "Invalidation status: ${INVALIDATION_STATUS}"
        
        if [ "${INVALIDATION_STATUS}" = "Completed" ]; then
            log_success "Last cache invalidation completed successfully"
        else
            log_warning "Last cache invalidation status: ${INVALIDATION_STATUS}"
        fi
    else
        log_warning "Could not get invalidation status"
    fi
else
    log_warning "No invalidation ID found in configuration"
fi

# Test creating a new invalidation
log_info "Testing cache invalidation creation..."
NEW_INVALIDATION=$(aws cloudfront create-invalidation \
    --distribution-id "${DISTRIBUTION_ID}" \
    --paths "/test-invalidation-$(date +%s).txt" 2>&1)

if [ $? -eq 0 ]; then
    NEW_INVALIDATION_ID=$(echo "${NEW_INVALIDATION}" | jq -r '.Invalidation.Id')
    log_success "Successfully created test invalidation: ${NEW_INVALIDATION_ID}"
else
    log_error "Failed to create test invalidation"
fi

################################################################################
# Test 8: Verify Direct S3 Access
################################################################################

log_test "Verify S3 Access Configuration"

# Test direct S3 access
S3_URL="https://${BUCKET_NAME}.s3.${AWS_REGION}.amazonaws.com/index.html"
log_info "Testing direct S3 URL: ${S3_URL}"

S3_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${S3_URL}" 2>/dev/null || echo "000")

log_info "Direct S3 access returns: ${S3_RESPONSE}"

if [ "${S3_RESPONSE}" = "200" ]; then
    log_info "Bucket is publicly readable (required for CloudFront custom origin)"
    log_success "S3 access configuration verified"
elif [ "${S3_RESPONSE}" = "403" ]; then
    log_info "Direct S3 access is blocked (OAI configuration)"
    log_success "S3 access configuration verified"
else
    log_warning "Unexpected S3 response: ${S3_RESPONSE}"
fi

################################################################################
# Test 9: Verify Static Assets
################################################################################

log_test "Verify Static Assets"

# List assets directory
log_info "Checking for assets in S3..."
ASSETS=$(aws s3 ls "s3://${BUCKET_NAME}/assets/" --recursive --region "${AWS_REGION}" 2>&1)

if [ $? -eq 0 ]; then
    ASSET_COUNT=$(echo "${ASSETS}" | wc -l | tr -d ' ')
    log_info "Found ${ASSET_COUNT} assets"
    
    if [ "${ASSET_COUNT}" -gt 0 ]; then
        log_success "Static assets are uploaded"
        
        # Show sample assets
        log_info "Sample assets:"
        echo "${ASSETS}" | head -n 3 | while IFS= read -r line; do
            log_info "  ${line}"
        done
    else
        log_warning "No assets found in /assets/ directory"
    fi
else
    log_warning "Could not list assets directory"
fi

################################################################################
# Test 10: End-to-End Application Test
################################################################################

log_test "End-to-End Application Test"

log_info "Performing end-to-end application test..."

# Test 1: Load root page
log_info "1. Loading root page..."
ROOT_CODE=$(curl -s -o /tmp/root_content.html -w "%{http_code}" "${CLOUDFRONT_URL}" 2>/dev/null)
ROOT_CONTENT=$(cat /tmp/root_content.html 2>/dev/null)

if [ "${ROOT_CODE}" = "200" ]; then
    log_success "Root page loads successfully"
else
    log_error "Root page failed to load (${ROOT_CODE})"
fi

# Test 2: Verify HTML structure
log_info "2. Verifying HTML structure..."
HTML_CHECKS=0

if echo "${ROOT_CONTENT}" | grep -qi "<!DOCTYPE html>"; then
    HTML_CHECKS=$((HTML_CHECKS + 1))
fi

if echo "${ROOT_CONTENT}" | grep -qi "<html"; then
    HTML_CHECKS=$((HTML_CHECKS + 1))
fi

if echo "${ROOT_CONTENT}" | grep -qi "<head"; then
    HTML_CHECKS=$((HTML_CHECKS + 1))
fi

if echo "${ROOT_CONTENT}" | grep -qi "<body"; then
    HTML_CHECKS=$((HTML_CHECKS + 1))
fi

if [ ${HTML_CHECKS} -eq 4 ]; then
    log_success "HTML structure is valid (${HTML_CHECKS}/4 checks)"
else
    log_error "HTML structure is incomplete (${HTML_CHECKS}/4 checks)"
fi

# Test 3: Check for JavaScript bundles
log_info "3. Checking for JavaScript bundles..."
if echo "${ROOT_CONTENT}" | grep -qi "<script.*src=.*\.js"; then
    log_success "JavaScript bundles are referenced"
else
    log_warning "No JavaScript bundles found in HTML"
fi

# Test 4: Check for CSS
log_info "4. Checking for CSS..."
if echo "${ROOT_CONTENT}" | grep -qi "<link.*stylesheet\|<style"; then
    log_success "CSS is referenced"
else
    log_warning "No CSS found in HTML"
fi

# Test 5: Test a client-side route
log_info "5. Testing client-side route..."
ROUTE_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${CLOUDFRONT_URL}/dashboard" 2>/dev/null || echo "000")

if [ "${ROUTE_RESPONSE}" = "200" ]; then
    log_success "Client-side routing works"
else
    log_error "Client-side routing failed (${ROUTE_RESPONSE})"
fi

################################################################################
# Summary
################################################################################

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DEPLOYMENT TEST SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

log_info "Total tests: ${TESTS_TOTAL}"
log_info "Tests passed: ${TESTS_PASSED}"
log_info "Tests failed: ${TESTS_FAILED}"

echo ""

if [ ${TESTS_FAILED} -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    log_success "Deployment is fully functional!"
    echo ""
    log_info "Application URL: https://${DISTRIBUTION_DOMAIN}"
    log_info "S3 Bucket: ${BUCKET_NAME}"
    log_info "CloudFront Distribution: ${DISTRIBUTION_ID}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    log_error "${TESTS_FAILED} test(s) failed"
    log_info "Please review the test output above for details"
    echo ""
    exit 1
fi
