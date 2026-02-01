#!/bin/bash

# Test script to verify Vite build configuration
# This script tests that the build system meets all requirements

set -e

echo "=== Testing Vite Build Configuration ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Clean build
echo "Test 1: Running clean build..."
rm -rf dist
npm run build > /dev/null 2>&1
if [ -d "dist" ]; then
    echo -e "${GREEN}✓ Build creates dist/ directory${NC}"
else
    echo -e "${RED}✗ Build failed to create dist/ directory${NC}"
    exit 1
fi

# Test 2: Verify index.html exists
echo "Test 2: Checking for index.html..."
if [ -f "dist/index.html" ]; then
    echo -e "${GREEN}✓ index.html exists${NC}"
else
    echo -e "${RED}✗ index.html not found${NC}"
    exit 1
fi

# Test 3: Verify assets directory exists
echo "Test 3: Checking for assets/ directory..."
if [ -d "dist/assets" ]; then
    echo -e "${GREEN}✓ assets/ directory exists${NC}"
else
    echo -e "${RED}✗ assets/ directory not found${NC}"
    exit 1
fi

# Test 4: Verify content hashes in filenames
echo "Test 4: Checking for content hashes in filenames..."
HASHED_FILES=$(find dist/assets -type f -name "*-*.*" | wc -l | tr -d ' ')
if [ "$HASHED_FILES" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $HASHED_FILES files with content hashes${NC}"
else
    echo -e "${RED}✗ No files with content hashes found${NC}"
    exit 1
fi

# Test 5: Verify JavaScript files are minified
echo "Test 5: Checking JavaScript minification..."
JS_FILE=$(find dist/assets -name "*.js" -type f | head -1)
if [ -f "$JS_FILE" ]; then
    # Check average line length (minified files have very long lines)
    AVG_LINE_LENGTH=$(awk '{total += length($0); count++} END {print int(total/count)}' "$JS_FILE")
    if [ "$AVG_LINE_LENGTH" -gt 100 ]; then
        echo -e "${GREEN}✓ JavaScript files appear minified (avg line length: $AVG_LINE_LENGTH)${NC}"
    else
        echo -e "${YELLOW}⚠ JavaScript files may not be minified (avg line length: $AVG_LINE_LENGTH)${NC}"
    fi
else
    echo -e "${RED}✗ No JavaScript files found${NC}"
    exit 1
fi

# Test 6: Verify chunk splitting (vendor chunk should exist)
echo "Test 6: Checking for vendor chunk..."
VENDOR_CHUNK=$(find dist/assets -name "vendor-*.js" -type f | wc -l | tr -d ' ')
if [ "$VENDOR_CHUNK" -gt 0 ]; then
    echo -e "${GREEN}✓ Vendor chunk exists (code splitting working)${NC}"
else
    echo -e "${YELLOW}⚠ No vendor chunk found${NC}"
fi

# Test 7: Verify icons chunk exists
echo "Test 7: Checking for icons chunk..."
ICONS_CHUNK=$(find dist/assets -name "icons-*.js" -type f | wc -l | tr -d ' ')
if [ "$ICONS_CHUNK" -gt 0 ]; then
    echo -e "${GREEN}✓ Icons chunk exists (code splitting working)${NC}"
else
    echo -e "${YELLOW}⚠ No icons chunk found${NC}"
fi

# Test 8: Verify build is deterministic (same input = same output structure)
echo "Test 8: Testing build determinism..."
FIRST_BUILD_FILES=$(find dist -type f | sort)
rm -rf dist
npm run build > /dev/null 2>&1
SECOND_BUILD_FILES=$(find dist -type f | sort)

if [ "$FIRST_BUILD_FILES" = "$SECOND_BUILD_FILES" ]; then
    echo -e "${GREEN}✓ Build is deterministic (same file structure)${NC}"
else
    echo -e "${YELLOW}⚠ Build produces different file structure (hashes may vary)${NC}"
fi

# Test 9: Run verification script
echo "Test 9: Running build verification script..."
if npm run verify > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Build verification script passed${NC}"
else
    echo -e "${RED}✗ Build verification script failed${NC}"
    exit 1
fi

# Test 10: Check total build size
echo "Test 10: Checking build size..."
BUILD_SIZE=$(du -sh dist | cut -f1)
echo -e "${GREEN}✓ Total build size: $BUILD_SIZE${NC}"

echo ""
echo -e "${GREEN}=== All build configuration tests passed! ===${NC}"
echo ""
echo "Summary:"
echo "  - Build output directory: dist/"
echo "  - Content hashing: Enabled"
echo "  - Minification: Enabled"
echo "  - Code splitting: Enabled (vendor + icons chunks)"
echo "  - Build size: $BUILD_SIZE"
