#!/bin/bash

################################################################################
# Test Script for Deployment Verification Functions
#
# This script tests the deployment verification and health check functions
# without running a full deployment.
################################################################################

set -e

# Source color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

################################################################################
# Test Configuration
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/deploy-config.json"

# Check if config file exists
if [ ! -f "${CONFIG_FILE}" ]; then
    log_error "Configuration file not found: ${CONFIG_FILE}"
    log_error "Please run a deployment first to create the configuration"
    exit 1
fi

# Load configuration
DISTRIBUTION_ID=$(jq -r '.distributionId // empty' "${CONFIG_FILE}")
DISTRIBUTION_DOMAIN=$(jq -r '.distributionDomain // empty' "${CONFIG_FILE}")
BUCKET_NAME=$(jq -r '.bucketName // empty' "${CONFIG_FILE}")
AWS_REGION=$(jq -r '.region // "us-east-1"' "${CONFIG_FILE}")

if [ -z "${DISTRIBUTION_ID}" ] || [ -z "${DISTRIBUTION_DOMAIN}" ]; then
    log_error "Missing required configuration values"
    log_error "Distribution ID: ${DISTRIBUTION_ID}"
    log_error "Distribution Domain: ${DISTRIBUTION_DOMAIN}"
    exit 1
fi

log_info "Test Configuration:"
log_info "  Distribution ID: ${DISTRIBUTION_ID}"
log_info "  Distribution Domain: ${DISTRIBUTION_DOMAIN}"
log_info "  Bucket Name: ${BUCKET_NAME}"
log_info "  Region: ${AWS_REGION}"

################################################################################
# Test 1: Check Distribution Status
################################################################################

log_step "Test 1: Check CloudFront Distribution Status"

log_info "Checking distribution status..."
DIST_STATUS=$(aws cloudfront get-distribution \
    --id "${DISTRIBUTION_ID}" \
    --query 'Distribution.Status' \
    --output text 2>&1)

if [ $? -eq 0 ]; then
    log_success "Distribution status: ${DIST_STATUS}"
    
    if [ "${DIST_STATUS}" = "Deployed" ]; then
        log_success "✓ Distribution is deployed"
    else
        log_info "Distribution is still deploying (status: ${DIST_STATUS})"
        log_info "This is normal for new deployments"
    fi
else
    log_error "Failed to get distribution status"
    log_error "${DIST_STATUS}"
    exit 1
fi

################################################################################
# Test 2: Test CloudFront Access
################################################################################

log_step "Test 2: Test CloudFront Access"

CLOUDFRONT_URL="https://${DISTRIBUTION_DOMAIN}"
log_info "Testing URL: ${CLOUDFRONT_URL}"

RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${CLOUDFRONT_URL}" 2>/dev/null || echo "000")

log_info "Response code: ${RESPONSE_CODE}"

if [ "${RESPONSE_CODE}" = "200" ]; then
    log_success "✓ CloudFront access successful (HTTP 200)"
elif [ "${RESPONSE_CODE}" = "000" ]; then
    log_error "✗ Failed to connect to CloudFront"
    log_error "This may indicate the distribution is still deploying"
else
    log_error "✗ Unexpected response code: ${RESPONSE_CODE}"
fi

################################################################################
# Test 3: Verify Response Content
################################################################################

log_step "Test 3: Verify Response Content"

log_info "Fetching content from CloudFront..."
RESPONSE_CONTENT=$(curl -s "${CLOUDFRONT_URL}" 2>/dev/null)

if [ -z "${RESPONSE_CONTENT}" ]; then
    log_error "✗ Failed to fetch content"
else
    log_success "✓ Content fetched successfully"
    
    # Check for HTML structure
    if echo "${RESPONSE_CONTENT}" | grep -qi "<!DOCTYPE html>\|<html"; then
        log_success "✓ HTML document structure found"
    else
        log_error "✗ HTML document structure not found"
    fi
    
    if echo "${RESPONSE_CONTENT}" | grep -qi "<head"; then
        log_success "✓ HTML head tag found"
    else
        log_error "✗ HTML head tag not found"
    fi
    
    if echo "${RESPONSE_CONTENT}" | grep -qi "<body"; then
        log_success "✓ HTML body tag found"
    else
        log_error "✗ HTML body tag not found"
    fi
    
    if echo "${RESPONSE_CONTENT}" | grep -qi '<div id="root"'; then
        log_success "✓ React root div found"
    else
        log_info "⚠ React root div not found (may use different mount point)"
    fi
fi

################################################################################
# Test 4: Test SPA Routing
################################################################################

log_step "Test 4: Test SPA Routing"

TEST_PATHS=(
    "/dashboard"
    "/settings"
    "/about"
)

log_info "Testing non-root paths for SPA routing..."

for path in "${TEST_PATHS[@]}"; do
    TEST_URL="https://${DISTRIBUTION_DOMAIN}${path}"
    log_info "Testing: ${path}"
    
    RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${TEST_URL}" 2>/dev/null || echo "000")
    
    if [ "${RESPONSE_CODE}" = "200" ]; then
        log_success "  ✓ ${path} returns 200"
        
        # Verify it returns HTML
        CONTENT=$(curl -s "${TEST_URL}" 2>/dev/null)
        if echo "${CONTENT}" | grep -qi "<!DOCTYPE html>\|<html"; then
            log_success "  ✓ ${path} returns HTML content"
        else
            log_error "  ✗ ${path} does not return HTML"
        fi
    else
        log_error "  ✗ ${path} returns ${RESPONSE_CODE} (expected 200)"
    fi
done

################################################################################
# Test 5: Verify S3 Access Configuration
################################################################################

log_step "Test 5: Verify S3 Access Configuration"

S3_URL="https://${BUCKET_NAME}.s3.${AWS_REGION}.amazonaws.com/index.html"
log_info "Testing direct S3 URL: ${S3_URL}"

RESPONSE_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${S3_URL}" 2>/dev/null || echo "000")

log_info "S3 response code: ${RESPONSE_CODE}"

if [ "${RESPONSE_CODE}" = "200" ]; then
    log_info "✓ Direct S3 access returns 200 (public bucket policy)"
    log_info "This is expected for CloudFront custom origin configuration"
elif [ "${RESPONSE_CODE}" = "403" ]; then
    log_success "✓ Direct S3 access is blocked (HTTP 403)"
    log_info "This indicates OAI-only access is configured"
else
    log_info "⚠ Unexpected S3 response code: ${RESPONSE_CODE}"
fi

################################################################################
# Test 6: Verify CloudFront Configuration
################################################################################

log_step "Test 6: Verify CloudFront Configuration"

log_info "Checking CloudFront configuration..."

DIST_CONFIG=$(aws cloudfront get-distribution --id "${DISTRIBUTION_ID}" 2>&1)

if [ $? -eq 0 ]; then
    # Check compression
    COMPRESSION=$(echo "${DIST_CONFIG}" | jq -r '.Distribution.DistributionConfig.DefaultCacheBehavior.Compress')
    if [ "${COMPRESSION}" = "true" ]; then
        log_success "✓ Compression is enabled"
    else
        log_error "✗ Compression is not enabled"
    fi
    
    # Check viewer protocol policy
    VIEWER_PROTOCOL=$(echo "${DIST_CONFIG}" | jq -r '.Distribution.DistributionConfig.DefaultCacheBehavior.ViewerProtocolPolicy')
    if [ "${VIEWER_PROTOCOL}" = "redirect-to-https" ]; then
        log_success "✓ HTTPS redirect is configured"
    else
        log_error "✗ HTTPS redirect is not configured (current: ${VIEWER_PROTOCOL})"
    fi
    
    # Check custom error response
    ERROR_CODE=$(echo "${DIST_CONFIG}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ErrorCode')
    RESPONSE_PAGE=$(echo "${DIST_CONFIG}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ResponsePagePath')
    RESPONSE_CODE=$(echo "${DIST_CONFIG}" | jq -r '.Distribution.DistributionConfig.CustomErrorResponses.Items[0].ResponseCode')
    
    if [ "${ERROR_CODE}" = "404" ] && [ "${RESPONSE_PAGE}" = "/index.html" ] && [ "${RESPONSE_CODE}" = "200" ]; then
        log_success "✓ Custom error response configured for SPA routing"
    else
        log_error "✗ Custom error response not properly configured"
        log_error "  Error Code: ${ERROR_CODE} (expected: 404)"
        log_error "  Response Page: ${RESPONSE_PAGE} (expected: /index.html)"
        log_error "  Response Code: ${RESPONSE_CODE} (expected: 200)"
    fi
else
    log_error "Failed to get distribution configuration"
fi

################################################################################
# Summary
################################################################################

log_step "Test Summary"

log_success "All deployment verification tests completed"
log_info ""
log_info "If all tests passed, your deployment is working correctly!"
log_info "If some tests failed, review the errors above and check:"
log_info "  1. CloudFront distribution is fully deployed (can take 15-20 minutes)"
log_info "  2. Files were uploaded to S3 correctly"
log_info "  3. CloudFront cache has been invalidated"
log_info ""
log_info "CloudFront URL: https://${DISTRIBUTION_DOMAIN}"
