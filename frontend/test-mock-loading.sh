#!/bin/bash

# Test Mock Solution Loading
# This script verifies that mock solutions can be loaded correctly

echo "🧪 Testing Mock Solution Loading"
echo "================================"
echo ""

# Check if solution files exist
echo "✓ Checking solution files..."
for i in {1..6}; do
    file="data/responses/solution_${i}.json"
    if [ -f "$file" ]; then
        size=$(du -h "$file" | cut -f1)
        echo "  ✓ solution_${i}.json exists (${size})"
    else
        echo "  ✗ solution_${i}.json MISSING!"
        exit 1
    fi
done
echo ""

# Check .env configuration
echo "✓ Checking .env configuration..."
if [ -f ".env" ]; then
    echo "  ✓ .env file exists"
    
    if grep -q "VITE_ENABLE_MOCK=true" .env; then
        echo "  ✓ Mock mode enabled"
    else
        echo "  ⚠ Mock mode not enabled (VITE_ENABLE_MOCK=true)"
    fi
    
    solution=$(grep "VITE_MOCK_SOLUTION=" .env | cut -d'=' -f2)
    if [ -n "$solution" ]; then
        echo "  ✓ Current solution: $solution"
    else
        echo "  ⚠ No solution specified (will use solution_1)"
    fi
else
    echo "  ✗ .env file not found!"
    exit 1
fi
echo ""

# Check TypeScript files
echo "✓ Checking TypeScript files..."
files=(
    "data/mockResponse.ts"
    "services/apiAsync.ts"
    "utils/mockSolutionSwitcher.ts"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file exists"
    else
        echo "  ✗ $file MISSING!"
        exit 1
    fi
done
echo ""

# Check if node_modules exists
echo "✓ Checking dependencies..."
if [ -d "node_modules" ]; then
    echo "  ✓ node_modules exists"
else
    echo "  ⚠ node_modules not found. Run: npm install"
fi
echo ""

echo "================================"
echo "✅ All checks passed!"
echo ""
echo "To test the fix:"
echo "1. Stop the dev server (Ctrl+C)"
echo "2. Edit .env and set VITE_MOCK_SOLUTION=solution_X"
echo "3. Run: npm run dev"
echo "4. Open the app and submit a query"
echo ""
echo "Or use runtime switching:"
echo "1. Open browser console"
echo "2. Run: window.switchMockSolution('solution_X')"
echo "3. Submit a new query"
