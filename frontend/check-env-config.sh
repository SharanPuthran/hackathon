#!/bin/bash

echo "🔍 Checking Environment Configuration"
echo "======================================"
echo ""

# Function to extract value from env file
get_env_value() {
    local file=$1
    local key=$2
    grep "^${key}=" "$file" 2>/dev/null | cut -d'=' -f2
}

# Check .env
echo "📄 .env (base configuration):"
if [ -f ".env" ]; then
    mock_solution=$(get_env_value ".env" "VITE_MOCK_SOLUTION")
    enable_mock=$(get_env_value ".env" "VITE_ENABLE_MOCK")
    echo "  VITE_MOCK_SOLUTION: ${mock_solution:-not set}"
    echo "  VITE_ENABLE_MOCK: ${enable_mock:-not set}"
else
    echo "  ❌ File not found"
fi
echo ""

# Check .env.local
echo "📄 .env.local (local overrides - HIGHEST PRIORITY):"
if [ -f ".env.local" ]; then
    mock_solution=$(get_env_value ".env.local" "VITE_MOCK_SOLUTION")
    enable_mock=$(get_env_value ".env.local" "VITE_ENABLE_MOCK")
    echo "  VITE_MOCK_SOLUTION: ${mock_solution:-not set}"
    echo "  VITE_ENABLE_MOCK: ${enable_mock:-not set}"
    echo ""
    echo "  ⚠️  .env.local overrides .env!"
else
    echo "  ℹ️  File not found (will use .env)"
fi
echo ""

# Determine effective configuration
echo "✅ EFFECTIVE CONFIGURATION (what Vite will use):"
if [ -f ".env.local" ]; then
    mock_solution=$(get_env_value ".env.local" "VITE_MOCK_SOLUTION")
    enable_mock=$(get_env_value ".env.local" "VITE_ENABLE_MOCK")
    source_file=".env.local"
else
    mock_solution=$(get_env_value ".env" "VITE_MOCK_SOLUTION")
    enable_mock=$(get_env_value ".env" "VITE_ENABLE_MOCK")
    source_file=".env"
fi

echo "  Source: $source_file"
echo "  VITE_MOCK_SOLUTION: ${mock_solution:-solution_1 (default)}"
echo "  VITE_ENABLE_MOCK: ${enable_mock:-false (default)}"
echo ""

# Validation
echo "🔍 VALIDATION:"
if [ "$enable_mock" = "true" ]; then
    echo "  ✅ Mock mode is ENABLED"
else
    echo "  ⚠️  Mock mode is DISABLED (will use real API)"
fi

if [ -n "$mock_solution" ]; then
    solution_file="data/responses/${mock_solution}.json"
    if [ -f "$solution_file" ]; then
        size=$(du -h "$solution_file" | cut -f1)
        echo "  ✅ Solution file exists: $mock_solution ($size)"
    else
        echo "  ❌ Solution file NOT FOUND: $solution_file"
    fi
else
    echo "  ⚠️  No solution specified (will use solution_1)"
fi
echo ""

# Instructions
echo "======================================"
echo "📋 NEXT STEPS:"
echo ""
if [ "$enable_mock" = "true" ] && [ -n "$mock_solution" ]; then
    echo "✅ Configuration looks good!"
    echo ""
    echo "To apply changes:"
    echo "  1. Stop dev server (Ctrl+C)"
    echo "  2. Run: npm run dev"
    echo "  3. Open app and submit a query"
    echo ""
    echo "Expected: App will load $mock_solution"
else
    echo "⚠️  Configuration needs attention:"
    echo ""
    if [ "$enable_mock" != "true" ]; then
        echo "  • Enable mock mode in $source_file:"
        echo "    VITE_ENABLE_MOCK=true"
    fi
    if [ -z "$mock_solution" ]; then
        echo "  • Set solution in $source_file:"
        echo "    VITE_MOCK_SOLUTION=solution_6"
    fi
    echo ""
    echo "Then restart: npm run dev"
fi
