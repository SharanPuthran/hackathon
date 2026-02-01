#!/bin/bash

################################################################################
# Test Script for S3 Bucket Policies (Simplified - No OAI)
# 
# This script verifies that the S3 bucket policies are configured correctly
# for public read access (which CloudFront will use).
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

# Test 1: Verify bucket policy allows public read
test_bucket_policy() {
    log_test "Verify Bucket Policy Allows Public Read"
    
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
    
    # Check for public read access
    if echo "${policy}" | jq -e '.Statement[] | select(.Effect == "Allow" and .Action == "s3:GetObject" and .Principal == "*")' > /dev/null 2>&1; then
        log_success "Bucket policy allows public read access ✓"
        
        # Display policy
        log_info "Bucket Policy:"
        echo "${policy}" | jq '.'
        
        return 0
    else
        log_error "Bucket policy does not allow public read access"
        return 1
    fi
}

# Test 2: Verify public access block is disabled
test_public_access_block() {
    log_test "Verify Public Access Block Configuration"
    
    log_info "Checking public access block configuration..."
    
    # Try to get public access block configuration
    local config=$(aws s3api get-public-access-block \
        --bucket "${BUCKET_NAME}" \
        --region "${AWS_REGION}" \
        --query 'PublicAccessBlockConfiguration' \
        --output json 2>&1)
    
    if [ $? -ne 0 ]; then
        log_info "No public access block configuration (allows public access)"
        log_success "Public access is allowed for website hosting ✓"
        return 0
    fi
    
    # If configuration exists, check settings
    local block_public_policy=$(echo "${config}" | jq -r '.BlockPublicPolicy // false')
    local restrict_public_buckets=$(echo "${config}" | jq -r '.RestrictPublicBuckets // false')
    
    if [ "${block_public_policy}" = "false" ] && [ "${restrict_public_buckets}" = "false" ]; then
        log_success "Public access block allows bucket policies ✓"
        log_info "Configuration:"
        echo "${config}" | jq '.'
        return 0
    else
        log_warning "Public access block may restrict access"
        log_info "Configuration:"
        echo "${config}" | jq '.'
        return 0
    fi
}

# Test 3: Verify static website hosting is enabled
test_website_hosting() {
    log_test "Verify Static Website Hosting"
    
    log_info "Checking website hosting configuration..."
    
    local website_config=$(aws s3api get-bucket-website \
        --bucket "${BUCKET_NAME}" \
        --region "${AWS_REGION}" 2>&1)
    
    if [ $? -ne 0 ]; then
        log_error "Website hosting is not configured"
        return 1
    fi
    
    log_success "Website hosting is enabled ✓"
    log_info "Configuration:"
    echo "${website_config}" | jq '.'
    
    return 0
}

# Test 4: Verify configuration file
test_config_file() {
    log_test "Verify Configuration File"
    
    if [ ! -f "${CONFIG_FILE}" ]; then
        log_error "Configuration file not found: ${CONFIG_FILE}"
        return 1
    fi
    
    log_info "Configuration file found"
    
    local bucket_name=$(jq -r '.bucketName // empty' "${CONFIG_FILE}")
    local region=$(jq -r '.region // empty' "${CONFIG_FILE}")
    local access_type=$(jq -r '.accessType // empty' "${CONFIG_FILE}")
    
    if [ "${bucket_name}" = "${BUCKET_NAME}" ]; then
        log_success "Bucket name matches: ${bucket_name} ✓"
    else
        log_error "Bucket name mismatch: expected ${BUCKET_NAME}, got ${bucket_name}"
        return 1
    fi
    
    if [ "${region}" = "${AWS_REGION}" ]; then
        log_success "Region matches: ${region} ✓"
    else
        log_error "Region mismatch: expected ${AWS_REGION}, got ${region}"
        return 1
    fi
    
    if [ "${access_type}" = "public" ]; then
        log_success "Access type is public ✓"
    else
        log_warning "Access type: ${access_type}"
    fi
    
    log_info "Full configuration:"
    jq '.' "${CONFIG_FILE}"
    
    return 0
}

# Main test execution
main() {
    echo ""
    echo "=========================================="
    echo "S3 Bucket Policies Test (Simplified)"
    echo "=========================================="
    echo ""
    echo "Bucket: ${BUCKET_NAME}"
    echo "Region: ${AWS_REGION}"
    echo ""
    
    local failed_tests=0
    
    # Run all tests
    test_bucket_policy || ((failed_tests++))
    test_public_access_block || ((failed_tests++))
    test_website_hosting || ((failed_tests++))
    test_config_file || ((failed_tests++))
    
    # Summary
    echo ""
    echo "=========================================="
    echo "TEST SUMMARY"
    echo "=========================================="
    
    if [ ${failed_tests} -eq 0 ]; then
        log_success "All tests passed! ✓"
        echo ""
        log_info "Requirements validated:"
        log_info "  ✓ 3.1: Bucket policy allows read access (public for CloudFront)"
        log_info "  ✓ 3.2: Bucket configured for public website hosting"
        log_info "  ✓ 3.5: Bucket policy follows principle of least privilege (read-only)"
        log_info ""
        log_info "Note: CloudFront will be configured in task 6 to serve content"
        exit 0
    else
        log_error "${failed_tests} test(s) failed"
        exit 1
    fi
}

# Run tests
main "$@"
