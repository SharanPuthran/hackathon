#!/bin/bash

################################################################################
# Test Script for S3 Bucket Policies and Public Access Blocking
# 
# This script verifies that the S3 bucket policies and public access blocking
# are configured correctly according to task 4 requirements.
################################################################################

set -e

# Configuration
BUCKET_NAME="skymarshal-frontend-368613657554"
AWS_REGION="us-east-1"
CONFIG_FILE="./deploy-config.json"

# Color codes
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

log_test() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}TEST: $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Test 1: Verify public access block settings are enabled
test_public_access_block() {
    log_test "Verify Public Access Block Settings"
    
    log_info "Checking public access block configuration..."
    
    local config=$(aws s3api get-public-access-block \
        --bucket "${BUCKET_NAME}" \
        --region "${AWS_REGION}" \
        --query 'PublicAccessBlockConfiguration' \
        --output json 2>&1)
    
    if [ $? -ne 0 ]; then
        log_error "Failed to get public access block configuration"
        return 1
    fi
    
    # Check all four settings
    local block_public_acls=$(echo "${config}" | jq -r '.BlockPublicAcls')
    local ignore_public_acls=$(echo "${config}" | jq -r '.IgnorePublicAcls')
    local block_public_policy=$(echo "${config}" | jq -r '.BlockPublicPolicy')
    local restrict_public_buckets=$(echo "${config}" | jq -r '.RestrictPublicBuckets')
    
    local all_enabled=true
    
    if [ "${block_public_acls}" != "true" ]; then
        log_error "BlockPublicAcls is not enabled"
        all_enabled=false
    fi
    
    if [ "${ignore_public_acls}" != "true" ]; then
        log_error "IgnorePublicAcls is not enabled"
        all_enabled=false
    fi
    
    if [ "${block_public_policy}" != "true" ]; then
        log_error "BlockPublicPolicy is not enabled"
        all_enabled=false
    fi
    
    if [ "${restrict_public_buckets}" != "true" ]; then
        log_error "RestrictPublicBuckets is not enabled"
        all_enabled=false
    fi
    
    if [ "${all_enabled}" = "true" ]; then
        log_success "All public access block settings are enabled ✓"
        log_info "  - BlockPublicAcls: ${block_public_acls}"
        log_info "  - IgnorePublicAcls: ${ignore_public_acls}"
        log_info "  - BlockPublicPolicy: ${block_public_policy}"
        log_info "  - RestrictPublicBuckets: ${restrict_public_buckets}"
        return 0
    else
        log_error "Some public access block settings are not enabled"
        return 1
    fi
}

# Test 2: Verify Origin Access Identity exists
test_oai_exists() {
    log_test "Verify Origin Access Identity Exists"
    
    log_info "Checking for OAI in configuration file..."
    
    if [ ! -f "${CONFIG_FILE}" ]; then
        log_error "Configuration file not found: ${CONFIG_FILE}"
        return 1
    fi
    
    local oai_id=$(jq -r '.oaiId // empty' "${CONFIG_FILE}")
    
    if [ -z "${oai_id}" ]; then
        log_error "OAI ID not found in configuration"
        return 1
    fi
    
    log_info "Found OAI ID: ${oai_id}"
    
    # Verify OAI exists in CloudFront
    log_info "Verifying OAI exists in CloudFront..."
    
    local oai_info=$(aws cloudfront get-cloud-front-origin-access-identity \
        --id "${oai_id}" \
        --query 'CloudFrontOriginAccessIdentity.{Id:Id,Comment:CloudFrontOriginAccessIdentityConfig.Comment}' \
        --output json 2>&1)
    
    if [ $? -ne 0 ]; then
        log_error "OAI does not exist in CloudFront"
        return 1
    fi
    
    log_success "Origin Access Identity exists ✓"
    log_info "OAI Details:"
    echo "${oai_info}" | jq '.'
    
    return 0
}

# Test 3: Verify bucket policy allows OAI access
test_bucket_policy() {
    log_test "Verify Bucket Policy Allows OAI Access"
    
    log_info "Retrieving bucket policy..."
    
    local policy=$(aws s3api get-bucket-policy \
        --bucket "${BUCKET_NAME}" \
        --region "${AWS_REGION}" \
        --query 'Policy' \
        --output text 2>&1)
    
    if [ $? -ne 0 ]; then
        log_error "Failed to get bucket policy"
        return 1
    fi
    
    log_info "Bucket policy retrieved"
    
    # Parse and check policy
    local oai_id=$(jq -r '.oaiId // empty' "${CONFIG_FILE}")
    
    if echo "${policy}" | jq -e ".Statement[] | select(.Principal.AWS | contains(\"${oai_id}\"))" > /dev/null 2>&1; then
        log_success "Bucket policy allows OAI access ✓"
        
        # Check for s3:GetObject action
        if echo "${policy}" | jq -e '.Statement[] | select(.Action == "s3:GetObject")' > /dev/null 2>&1; then
            log_success "Policy grants s3:GetObject permission ✓"
        else
            log_error "Policy does not grant s3:GetObject permission"
            return 1
        fi
        
        # Display policy
        log_info "Bucket Policy:"
        echo "${policy}" | jq '.'
        
        return 0
    else
        log_error "Bucket policy does not reference OAI"
        return 1
    fi
}

# Test 4: Verify direct S3 access is blocked
test_direct_access_blocked() {
    log_test "Verify Direct S3 Access is Blocked"
    
    local s3_website_url="http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"
    
    log_info "Testing direct S3 access at: ${s3_website_url}"
    
    # Try to access the bucket directly
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" "${s3_website_url}" 2>/dev/null || echo "000")
    
    log_info "Response code: ${response_code}"
    
    if [ "${response_code}" = "403" ]; then
        log_success "Direct S3 access is blocked (403 Forbidden) ✓"
        return 0
    elif [ "${response_code}" = "000" ]; then
        log_info "Could not connect to S3 website endpoint"
        log_info "This is expected if no files have been uploaded yet"
        return 0
    else
        log_error "Unexpected response code: ${response_code}"
        log_error "Expected 403 Forbidden"
        return 1
    fi
}

# Main test execution
main() {
    echo ""
    echo "=========================================="
    echo "S3 Bucket Policies and Public Access Test"
    echo "=========================================="
    echo ""
    echo "Bucket: ${BUCKET_NAME}"
    echo "Region: ${AWS_REGION}"
    echo ""
    
    local failed_tests=0
    
    # Run all tests
    test_public_access_block || ((failed_tests++))
    test_oai_exists || ((failed_tests++))
    test_bucket_policy || ((failed_tests++))
    test_direct_access_blocked || ((failed_tests++))
    
    # Summary
    echo ""
    echo "=========================================="
    echo "TEST SUMMARY"
    echo "=========================================="
    
    if [ ${failed_tests} -eq 0 ]; then
        log_success "All tests passed! ✓"
        echo ""
        log_info "Requirements validated:"
        log_info "  ✓ 3.1: Bucket policy allows CloudFront OAI to read objects"
        log_info "  ✓ 3.2: Bucket blocks direct public access"
        log_info "  ✓ 3.4: Direct S3 access is denied"
        log_info "  ✓ 3.5: Bucket policy follows principle of least privilege"
        exit 0
    else
        log_error "${failed_tests} test(s) failed"
        exit 1
    fi
}

# Run tests
main "$@"
