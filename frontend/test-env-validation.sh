#!/bin/bash

################################################################################
# Environment Variable Validation Test Script
# 
# This script tests the environment variable validation functionality
# to ensure it correctly detects missing, invalid, and valid configurations.
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Environment Variable Validation Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Backup existing .env files
echo -e "${BLUE}Backing up existing .env files...${NC}"
[ -f .env ] && mv .env .env.backup
[ -f .env.local ] && mv .env.local .env.local.backup

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Missing environment variables
echo -e "\n${BLUE}Test 1: Missing environment variables${NC}"
echo "Expected: Validation should fail"

rm -f .env .env.local

if node validate-env.js > /dev/null 2>&1; then
    echo -e "${RED}✗ FAILED: Validation passed when it should have failed${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
else
    echo -e "${GREEN}✓ PASSED: Validation correctly failed for missing variables${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi

# Test 2: Placeholder values
echo -e "\n${BLUE}Test 2: Placeholder values${NC}"
echo "Expected: Validation should fail"

cat > .env.local << EOF
VITE_GEMINI_API_KEY=your_api_key_here
EOF

if node validate-env.js > /dev/null 2>&1; then
    echo -e "${RED}✗ FAILED: Validation passed for placeholder value${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
else
    echo -e "${GREEN}✓ PASSED: Validation correctly failed for placeholder value${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi

# Test 3: Test placeholder value
echo -e "\n${BLUE}Test 3: Test placeholder value${NC}"
echo "Expected: Validation should fail"

cat > .env.local << EOF
VITE_GEMINI_API_KEY=test_key_for_validation
EOF

if node validate-env.js > /dev/null 2>&1; then
    echo -e "${RED}✗ FAILED: Validation passed for test placeholder${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
else
    echo -e "${GREEN}✓ PASSED: Validation correctly failed for test placeholder${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi

# Test 4: Valid API key
echo -e "\n${BLUE}Test 4: Valid API key${NC}"
echo "Expected: Validation should pass"

cat > .env.local << EOF
VITE_GEMINI_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuvwxyz
EOF

if node validate-env.js > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED: Validation correctly passed for valid API key${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED: Validation failed for valid API key${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 5: Valid API key in .env (not .env.local)
echo -e "\n${BLUE}Test 5: Valid API key in .env file${NC}"
echo "Expected: Validation should pass"

rm -f .env.local
cat > .env << EOF
VITE_GEMINI_API_KEY=AIzaSyABCDEF1234567890abcdefghijklmnopqrst
EOF

if node validate-env.js > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED: Validation correctly passed for .env file${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED: Validation failed for .env file${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 6: Priority - .env.local overrides .env
echo -e "\n${BLUE}Test 6: Priority - .env.local overrides .env${NC}"
echo "Expected: Validation should use .env.local value"

cat > .env << EOF
VITE_GEMINI_API_KEY=AIzaSyValidKeyInEnv
EOF

cat > .env.local << EOF
VITE_GEMINI_API_KEY=placeholder_value
EOF

if node validate-env.js > /dev/null 2>&1; then
    echo -e "${RED}✗ FAILED: Should have used placeholder from .env.local${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
else
    echo -e "${GREEN}✓ PASSED: Correctly prioritized .env.local over .env${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
fi

# Test 7: npm script integration
echo -e "\n${BLUE}Test 7: npm script integration${NC}"
echo "Expected: npm run validate:env should work"

cat > .env.local << EOF
VITE_GEMINI_API_KEY=AIzaSyD1234567890abcdefghijklmnopqrstuvwxyz
EOF

if npm run validate:env > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PASSED: npm run validate:env works correctly${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED: npm run validate:env failed${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 8: .env.example exists and is valid
echo -e "\n${BLUE}Test 8: .env.example file exists${NC}"
echo "Expected: .env.example should exist and contain required variables"

if [ -f .env.example ]; then
    if grep -q "VITE_GEMINI_API_KEY" .env.example; then
        echo -e "${GREEN}✓ PASSED: .env.example exists and contains required variables${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ FAILED: .env.example missing required variables${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "${RED}✗ FAILED: .env.example file not found${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Test 9: .gitignore excludes .env files
echo -e "\n${BLUE}Test 9: .gitignore excludes .env files${NC}"
echo "Expected: .gitignore should exclude .env and .env.local"

if grep -q "^\.env$" .gitignore && grep -q "^\.env\.local$" .gitignore; then
    echo -e "${GREEN}✓ PASSED: .gitignore correctly excludes .env files${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED: .gitignore missing .env exclusions${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

# Cleanup
echo -e "\n${BLUE}Cleaning up test files...${NC}"
rm -f .env .env.local

# Restore backups
[ -f .env.backup ] && mv .env.backup .env
[ -f .env.local.backup ] && mv .env.local.backup .env.local

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Tests passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests failed: ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ ${TESTS_FAILED} -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
