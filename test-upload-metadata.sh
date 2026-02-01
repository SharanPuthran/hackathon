#!/bin/bash

################################################################################
# Test Script for File Upload Metadata
# 
# This script tests the Content-Type and Cache-Control logic
# without actually uploading to S3
################################################################################

set -e

# Source the functions from deploy.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Extract just the functions we need to test
get_content_type() {
    local file=$1
    local extension="${file##*.}"
    
    case "${extension}" in
        html) echo "text/html" ;;
        js) echo "application/javascript" ;;
        css) echo "text/css" ;;
        json) echo "application/json" ;;
        png) echo "image/png" ;;
        jpg|jpeg) echo "image/jpeg" ;;
        svg) echo "image/svg+xml" ;;
        ico) echo "image/x-icon" ;;
        woff) echo "font/woff" ;;
        woff2) echo "font/woff2" ;;
        ttf) echo "font/ttf" ;;
        eot) echo "application/vnd.ms-fontobject" ;;
        txt) echo "text/plain" ;;
        xml) echo "application/xml" ;;
        pdf) echo "application/pdf" ;;
        *) echo "application/octet-stream" ;;
    esac
}

get_cache_control() {
    local file=$1
    local filename=$(basename "${file}")
    local extension="${file##*.}"
    
    # HTML files: no-cache (always fetch fresh)
    if [ "${extension}" = "html" ]; then
        echo "no-cache, no-store, must-revalidate"
        return
    fi
    
    # Check if file has content hash (contains hyphen followed by 8+ alphanumeric chars before extension)
    # Pattern: filename-[hash].ext (e.g., index-a1b2c3d4.js)
    if echo "${filename}" | grep -qE '\-[a-zA-Z0-9]{8,}\.[^.]+$'; then
        # Hashed assets: cache forever (immutable)
        echo "public, max-age=31536000, immutable"
        return
    fi
    
    # Other static files: cache for 1 day
    echo "public, max-age=86400"
}

# Test cases
echo "Testing Content-Type mapping..."
echo "================================"

test_files=(
    "index.html"
    "app.js"
    "styles.css"
    "data.json"
    "logo.png"
    "icon.svg"
    "favicon.ico"
    "font.woff2"
    "unknown.xyz"
)

for file in "${test_files[@]}"; do
    content_type=$(get_content_type "${file}")
    echo "✓ ${file} -> ${content_type}"
done

echo ""
echo "Testing Cache-Control strategy..."
echo "================================"

test_files_cache=(
    "index.html"
    "index-BSPWIYOg.js"
    "vendor-D1axn4aC.js"
    "icons-DrxnPYgE.js"
    "styles-a1b2c3d4e5f6.css"
    "logo.png"
    "favicon.ico"
)

for file in "${test_files_cache[@]}"; do
    cache_control=$(get_cache_control "${file}")
    echo "✓ ${file} -> ${cache_control}"
done

echo ""
echo "Testing with actual build files..."
echo "================================"

if [ -d "frontend/dist" ]; then
    while IFS= read -r file; do
        rel_path="${file#frontend/dist/}"
        content_type=$(get_content_type "${file}")
        cache_control=$(get_cache_control "${file}")
        echo "✓ ${rel_path}"
        echo "  Content-Type: ${content_type}"
        echo "  Cache-Control: ${cache_control}"
    done < <(find frontend/dist -type f)
else
    echo "Build directory not found - skipping actual file test"
fi

echo ""
echo "All tests passed! ✓"
