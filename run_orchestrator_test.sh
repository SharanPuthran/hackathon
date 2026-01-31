#!/bin/bash

# SkyMarshal Orchestrator Test Runner
# This script runs a complete test of the orchestrator system

set -e  # Exit on error

echo "════════════════════════════════════════════════════════════════════════════════"
echo "                    SKYMARSHAL ORCHESTRATOR TEST SUITE"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

print_success "Python 3 found: $(python3 --version)"

# Check AWS credentials
print_status "Checking AWS credentials..."
if aws sts get-caller-identity &> /dev/null; then
    print_success "AWS credentials configured"
    aws sts get-caller-identity --query 'Account' --output text | xargs -I {} echo "  Account: {}"
else
    print_error "AWS credentials not configured"
    echo "  Run: aws configure"
    exit 1
fi

echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "STEP 1: Checking DynamoDB Data"
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""

python3 check_dynamodb_data.py

if [ $? -ne 0 ]; then
    print_error "DynamoDB data check failed"
    echo ""
    print_warning "To populate DynamoDB:"
    echo "  cd database"
    echo "  python generators/create_disruption_scenario_v2.py"
    echo "  python import_csv_to_dynamodb.py"
    exit 1
fi

echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "STEP 2: Testing Orchestrator Locally"
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""

python3 test_local_orchestrator.py

if [ $? -ne 0 ]; then
    print_error "Local orchestrator test failed"
    exit 1
fi

echo ""
echo "────────────────────────────────────────────────────────────────────────────────"
echo "STEP 3: Testing Individual Agents"
echo "────────────────────────────────────────────────────────────────────────────────"
echo ""

# Ask user if they want to test individual agents
read -p "Do you want to test individual agents? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 test_orchestrator_flow.py --mode individual
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo "                           TEST SUITE COMPLETE"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

print_success "All tests passed!"
echo ""
echo "Next steps:"
echo "  1. Deploy to AgentCore:"
echo "     cd skymarshal_agents"
echo "     agentcore deploy"
echo ""
echo "  2. Test deployed orchestrator:"
echo "     agentcore invoke 'Analyze flight disruption'"
echo ""
echo "  3. Monitor logs:"
echo "     agentcore logs --tail 50"
echo ""
echo "  4. Test with custom disruption:"
echo "     Edit sample_disruption.json and run:"
echo "     python test_orchestrator_flow.py --mode orchestrator"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
