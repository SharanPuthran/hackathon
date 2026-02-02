#!/bin/bash
# Testing script for AgentCore REST API

set -e

echo "🧪 Testing AgentCore REST API..."

# Run unit tests
echo "Running unit tests..."
uv run pytest test/test_api_validation.py test/test_api_models.py -v

# Generate coverage report
echo ""
echo "Generating coverage report..."
uv run pytest test/test_api_*.py --cov=src/api --cov-report=html --cov-report=term

echo ""
echo "✅ All tests passed!"
echo "📊 Coverage report generated in htmlcov/index.html"
