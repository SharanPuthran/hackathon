#!/bin/bash

################################################################################
# Test Script for Error Handling and Recovery
# 
# This script tests the error handling capabilities of the deployment script
################################################################################

set -e

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

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo "=================================="
echo "Error Handling Test Suite"
echo "=================================="
echo ""

# Test 1: Verify error handling functions exist
log_test "Test 1: Checking error handling functions exist in deploy.sh"

required_functions=(
    "initialize_deployment_state"
    "record_resource"
    "cleanup_on_exit"
    "perform_rollback"
    "rollback_cloudfront_distribution"
    "rollback_s3_bucket"
    "handle_aws_error"
    "retry_with_backoff"
)

test1_passed=true
for func in "${required_functions[@]}"; do
    if grep -q "^${func}()" deploy.sh || grep -q "^${func} ()" deploy.sh; then
        log_pass "  ✓ Function '${func}' found"
    else
        log_fail "  ✗ Function '${func}' not found"
        test1_passed=false
    fi
done

if [ "$test1_passed" = true ]; then
    log_pass "Test 1: All error handling functions exist"
else
    log_fail "Test 1: Some error handling functions are missing"
fi

echo ""

# Test 2: Verify trap is set for cleanup
log_test "Test 2: Checking cleanup trap is configured"

if grep -q "trap cleanup_on_exit EXIT INT TERM" deploy.sh; then
    log_pass "Test 2: Cleanup trap is configured"
else
    log_fail "Test 2: Cleanup trap is not configured"
fi

echo ""

# Test 3: Verify error messages include context
log_test "Test 3: Checking error messages include recovery suggestions"

test3_passed=true
error_contexts=(
    "Authentication Error Detected"
    "Bucket Already Exists Error"
    "Access Denied Error"
    "CloudFront Quota Exceeded"
    "Invalid Configuration Error"
    "AWS Service Timeout/Unavailable"
    "Rate Limit Exceeded"
)

for context in "${error_contexts[@]}"; do
    if grep -q "${context}" deploy.sh; then
        log_pass "  ✓ Error context '${context}' found"
    else
        log_fail "  ✗ Error context '${context}' not found"
        test3_passed=false
    fi
done

if [ "$test3_passed" = true ]; then
    log_pass "Test 3: All error contexts with recovery suggestions exist"
else
    log_fail "Test 3: Some error contexts are missing"
fi

echo ""

# Test 4: Verify AWS CLI commands have error handling
log_test "Test 4: Checking AWS CLI commands have error handling"

# Count AWS CLI commands
total_aws_commands=$(grep -c "aws " deploy.sh || echo "0")
log_info "  Total AWS CLI commands found: ${total_aws_commands}"

# Check for error capture patterns
error_capture_count=$(grep -c "2>&1)" deploy.sh || echo "0")
log_info "  Commands with error capture: ${error_capture_count}"

if [ ${error_capture_count} -gt 10 ]; then
    log_pass "Test 4: AWS CLI commands have error handling"
else
    log_fail "Test 4: Insufficient error handling for AWS CLI commands"
fi

echo ""

# Test 5: Verify rollback capability exists
log_test "Test 5: Checking rollback capability"

test5_passed=true

# Check for resource tracking
if grep -q "CREATED_RESOURCES" deploy.sh; then
    log_pass "  ✓ Resource tracking array exists"
else
    log_fail "  ✗ Resource tracking array not found"
    test5_passed=false
fi

# Check for rollback prompt
if grep -q "Do you want to rollback" deploy.sh; then
    log_pass "  ✓ Rollback prompt exists"
else
    log_fail "  ✗ Rollback prompt not found"
    test5_passed=false
fi

# Check for rollback functions
if grep -q "perform_rollback" deploy.sh; then
    log_pass "  ✓ Rollback function exists"
else
    log_fail "  ✗ Rollback function not found"
    test5_passed=false
fi

if [ "$test5_passed" = true ]; then
    log_pass "Test 5: Rollback capability is implemented"
else
    log_fail "Test 5: Rollback capability is incomplete"
fi

echo ""

# Test 6: Verify retry logic exists
log_test "Test 6: Checking retry logic with exponential backoff"

if grep -q "retry_with_backoff" deploy.sh; then
    log_pass "  ✓ Retry function exists"
    
    # Check for exponential backoff
    if grep -q "delay=\$((delay \* 2))" deploy.sh; then
        log_pass "  ✓ Exponential backoff implemented"
    else
        log_fail "  ✗ Exponential backoff not found"
    fi
    
    log_pass "Test 6: Retry logic with exponential backoff exists"
else
    log_fail "Test 6: Retry function not found"
fi

echo ""

# Test 7: Verify deployment state tracking
log_test "Test 7: Checking deployment state tracking"

test7_passed=true

if grep -q "DEPLOYMENT_STATE_FILE" deploy.sh; then
    log_pass "  ✓ Deployment state file variable exists"
else
    log_fail "  ✗ Deployment state file variable not found"
    test7_passed=false
fi

if grep -q "initialize_deployment_state" deploy.sh; then
    log_pass "  ✓ State initialization function exists"
else
    log_fail "  ✗ State initialization function not found"
    test7_passed=false
fi

if grep -q "record_resource" deploy.sh; then
    log_pass "  ✓ Resource recording function exists"
else
    log_fail "  ✗ Resource recording function not found"
    test7_passed=false
fi

if [ "$test7_passed" = true ]; then
    log_pass "Test 7: Deployment state tracking is implemented"
else
    log_fail "Test 7: Deployment state tracking is incomplete"
fi

echo ""

# Test 8: Verify specific error handlers
log_test "Test 8: Checking specific error handlers for common failures"

test8_passed=true

error_types=(
    "InvalidAccessKeyId"
    "BucketAlreadyExists"
    "NoSuchBucket"
    "AccessDenied"
    "TooManyDistributions"
    "ThrottlingException"
)

for error_type in "${error_types[@]}"; do
    if grep -q "${error_type}" deploy.sh; then
        log_pass "  ✓ Handler for '${error_type}' found"
    else
        log_fail "  ✗ Handler for '${error_type}' not found"
        test8_passed=false
    fi
done

if [ "$test8_passed" = true ]; then
    log_pass "Test 8: All specific error handlers exist"
else
    log_fail "Test 8: Some specific error handlers are missing"
fi

echo ""

# Test 9: Verify error messages include recovery suggestions
log_test "Test 9: Checking error messages include recovery suggestions"

recovery_suggestion_count=$(grep -c "Recovery suggestions:" deploy.sh || echo "0")
log_info "  Recovery suggestion blocks found: ${recovery_suggestion_count}"

if [ ${recovery_suggestion_count} -ge 5 ]; then
    log_pass "Test 9: Error messages include recovery suggestions"
else
    log_fail "Test 9: Insufficient recovery suggestions in error messages"
fi

echo ""

# Test 10: Verify initialization is called in main
log_test "Test 10: Checking deployment state initialization in main function"

if grep -A 5 "^main()" deploy.sh | grep -q "initialize_deployment_state"; then
    log_pass "Test 10: Deployment state is initialized in main function"
else
    log_fail "Test 10: Deployment state initialization not found in main function"
fi

echo ""

# Summary
echo "=================================="
echo "Test Summary"
echo "=================================="

# Count passed tests
passed_tests=0
total_tests=10

# Re-run checks for summary
[ "$test1_passed" = true ] && passed_tests=$((passed_tests + 1))
grep -q "trap cleanup_on_exit EXIT INT TERM" deploy.sh && passed_tests=$((passed_tests + 1))
[ "$test3_passed" = true ] && passed_tests=$((passed_tests + 1))
[ ${error_capture_count} -gt 10 ] && passed_tests=$((passed_tests + 1))
[ "$test5_passed" = true ] && passed_tests=$((passed_tests + 1))
grep -q "retry_with_backoff" deploy.sh && passed_tests=$((passed_tests + 1))
[ "$test7_passed" = true ] && passed_tests=$((passed_tests + 1))
[ "$test8_passed" = true ] && passed_tests=$((passed_tests + 1))
[ ${recovery_suggestion_count} -ge 5 ] && passed_tests=$((passed_tests + 1))
grep -A 5 "^main()" deploy.sh | grep -q "initialize_deployment_state" && passed_tests=$((passed_tests + 1))

echo ""
log_info "Tests Passed: ${passed_tests}/${total_tests}"

if [ ${passed_tests} -eq ${total_tests} ]; then
    log_pass "All tests passed! ✓"
    exit 0
else
    log_fail "Some tests failed"
    exit 1
fi
