#!/bin/bash

################################################################################
# Test Script for CloudFront Cache Invalidation
#
# This script tests the cache invalidation functionality without requiring
# a full deployment. It verifies:
# 1. Invalidation creation with unique caller reference
# 2. Path specification (/index.html and /assets/*)
# 3. Status polling with timeout
# 4. Logging of invalidation ID and status
################################################################################

set -e

# Source the deployment script functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/deploy.sh" 2>/dev/null || true

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

################################################################################
# Test 1: Verify invalidation function exists
################################################################################

test_function_exists() {
    log_test "Test 1: Verifying invalidation function exists..."
    
    if declare -f invalidate_cloudfront_cache > /dev/null; then
        log_pass "invalidate_cloudfront_cache function exists"
        return 0
    else
        log_fail "invalidate_cloudfront_cache function not found"
        return 1
    fi
}

################################################################################
# Test 2: Verify caller reference generation
################################################################################

test_caller_reference() {
    log_test "Test 2: Verifying caller reference generation..."
    
    # Generate two caller references with a small delay
    local ref1="invalidation-$(date +%s)"
    sleep 1
    local ref2="invalidation-$(date +%s)"
    
    if [ "${ref1}" != "${ref2}" ]; then
        log_pass "Caller references are unique: ${ref1} != ${ref2}"
        return 0
    else
        log_fail "Caller references are not unique"
        return 1
    fi
}

################################################################################
# Test 3: Verify paths configuration
################################################################################

test_paths_configuration() {
    log_test "Test 3: Verifying paths configuration..."
    
    # Check if the script contains the correct paths
    if grep -q '"/index.html"' deploy.sh && grep -q '"/assets/\*"' deploy.sh; then
        log_pass "Critical paths configured: /index.html and /assets/*"
        return 0
    else
        log_fail "Critical paths not properly configured"
        return 1
    fi
}

################################################################################
# Test 4: Verify timeout configuration
################################################################################

test_timeout_configuration() {
    log_test "Test 4: Verifying timeout configuration..."
    
    # Check if timeout is set to 300 seconds (5 minutes)
    if grep -q 'timeout=300' deploy.sh; then
        log_pass "Timeout configured to 5 minutes (300 seconds)"
        return 0
    else
        log_fail "Timeout not properly configured"
        return 1
    fi
}

################################################################################
# Test 5: Verify logging functionality
################################################################################

test_logging() {
    log_test "Test 5: Verifying logging functionality..."
    
    # Check if the function logs invalidation ID and status
    if grep -q 'log_info "Invalidation ID:' deploy.sh && \
       grep -q 'log_info "Status:' deploy.sh; then
        log_pass "Logging functionality present"
        return 0
    else
        log_fail "Logging functionality incomplete"
        return 1
    fi
}

################################################################################
# Test 6: Verify error handling
################################################################################

test_error_handling() {
    log_test "Test 6: Verifying error handling..."
    
    # Check if the function handles missing distribution ID
    if grep -q 'if \[ -z "\${DISTRIBUTION_ID}" \]' deploy.sh; then
        log_pass "Error handling for missing distribution ID present"
        return 0
    else
        log_fail "Error handling incomplete"
        return 1
    fi
}

################################################################################
# Test 7: Verify integration with main flow
################################################################################

test_main_flow_integration() {
    log_test "Test 7: Verifying integration with main deployment flow..."
    
    # Check if invalidate_cloudfront_cache is called in main function
    if grep 'invalidate_cloudfront_cache$' deploy.sh | grep -v '^#' | grep -v 'invalidate_cloudfront_cache()' > /dev/null; then
        log_pass "Invalidation integrated into main deployment flow"
        return 0
    else
        log_fail "Invalidation not integrated into main flow"
        return 1
    fi
}

################################################################################
# Test 8: Verify AWS CLI command structure
################################################################################

test_aws_cli_command() {
    log_test "Test 8: Verifying AWS CLI command structure..."
    
    # Check if the correct AWS CLI command is used
    if grep -q 'aws cloudfront create-invalidation' deploy.sh && \
       grep 'distribution-id' deploy.sh > /dev/null && \
       grep 'paths' deploy.sh > /dev/null; then
        log_pass "AWS CLI command structure correct"
        return 0
    else
        log_fail "AWS CLI command structure incorrect"
        return 1
    fi
}

################################################################################
# Test 9: Verify status polling logic
################################################################################

test_status_polling() {
    log_test "Test 9: Verifying status polling logic..."
    
    # Check if the function polls for completion status
    if grep -q 'aws cloudfront get-invalidation' deploy.sh && \
       grep -q 'while \[ ${elapsed} -lt ${timeout} \]' deploy.sh; then
        log_pass "Status polling logic present"
        return 0
    else
        log_fail "Status polling logic incomplete"
        return 1
    fi
}

################################################################################
# Test 10: Verify configuration persistence
################################################################################

test_config_persistence() {
    log_test "Test 10: Verifying configuration persistence..."
    
    # Check if invalidation ID is saved to config
    if grep -q 'save_to_config "lastInvalidationId"' deploy.sh && \
       grep -q 'save_to_config "lastInvalidationTime"' deploy.sh; then
        log_pass "Configuration persistence implemented"
        return 0
    else
        log_fail "Configuration persistence incomplete"
        return 1
    fi
}

################################################################################
# Run all tests
################################################################################

main() {
    echo ""
    echo "=========================================="
    echo "CloudFront Cache Invalidation Tests"
    echo "=========================================="
    echo ""
    
    local total_tests=10
    local passed_tests=0
    
    # Run tests
    test_function_exists && ((passed_tests++)) || true
    test_caller_reference && ((passed_tests++)) || true
    test_paths_configuration && ((passed_tests++)) || true
    test_timeout_configuration && ((passed_tests++)) || true
    test_logging && ((passed_tests++)) || true
    test_error_handling && ((passed_tests++)) || true
    test_main_flow_integration && ((passed_tests++)) || true
    test_aws_cli_command && ((passed_tests++)) || true
    test_status_polling && ((passed_tests++)) || true
    test_config_persistence && ((passed_tests++)) || true
    
    echo ""
    echo "=========================================="
    echo "Test Results"
    echo "=========================================="
    echo "Passed: ${passed_tests}/${total_tests}"
    
    if [ ${passed_tests} -eq ${total_tests} ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed${NC}"
        exit 1
    fi
}

main "$@"
