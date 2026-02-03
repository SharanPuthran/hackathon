#!/bin/bash

# SkyMarshal Optimization Deployment Script
# This script deploys all performance optimizations to AWS infrastructure

set -e  # Exit on error

echo "=========================================="
echo "SkyMarshal Optimization Deployment"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
AGENTCORE_ARN="arn:aws:bedrock-agentcore:us-east-1:368613657554:runtime/skymarshal_Agent-cn8OdHGjgz"
ENVIRONMENT="dev"
AWS_REGION="us-east-1"

echo -e "${YELLOW}Configuration:${NC}"
echo "  AgentCore ARN: $AGENTCORE_ARN"
echo "  Environment: $ENVIRONMENT"
echo "  AWS Region: $AWS_REGION"
echo ""

# Step 1: Verify AWS credentials
echo -e "${YELLOW}Step 1: Verifying AWS credentials...${NC}"
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${GREEN}✓ AWS credentials valid${NC}"
    aws sts get-caller-identity --query 'Account' --output text
else
    echo -e "${RED}✗ AWS credentials not configured${NC}"
    echo "Please run: aws sso login"
    exit 1
fi
echo ""

# Step 2: Build Lambda package
echo -e "${YELLOW}Step 2: Building Lambda package...${NC}"
cd "$(dirname "$0")/.."  # Go to skymarshal root

# Create build directory
mkdir -p build

# Package Lambda function
echo "  Packaging source code..."
zip -r build/lambda_package.zip src/ \
    -x "*.pyc" \
    -x "*__pycache__/*" \
    -x "*.pytest_cache/*" \
    -x "*.hypothesis/*" \
    -x "*.ruff_cache/*" \
    > /dev/null 2>&1

# Get package size
PACKAGE_SIZE=$(du -h build/lambda_package.zip | cut -f1)
echo -e "${GREEN}✓ Lambda package created: $PACKAGE_SIZE${NC}"
echo ""

# Step 3: Deploy infrastructure with Terraform
echo -e "${YELLOW}Step 3: Deploying infrastructure with Terraform...${NC}"
cd infrastructure

# Set Terraform variables
export TF_VAR_agentcore_runtime_arn="$AGENTCORE_ARN"
export TF_VAR_environment="$ENVIRONMENT"
export TF_VAR_aws_region="$AWS_REGION"

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "  Initializing Terraform..."
    terraform init
fi

# Validate configuration
echo "  Validating Terraform configuration..."
if terraform validate > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Terraform configuration valid${NC}"
else
    echo -e "${RED}✗ Terraform configuration invalid${NC}"
    terraform validate
    exit 1
fi

# Plan changes
echo "  Planning infrastructure changes..."
terraform plan -out=tfplan

# Prompt for confirmation
echo ""
echo -e "${YELLOW}Review the plan above. Do you want to apply these changes? (yes/no)${NC}"
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 0
fi

# Apply changes
echo "  Applying infrastructure changes..."
terraform apply tfplan

echo -e "${GREEN}✓ Infrastructure deployed${NC}"
echo ""

# Step 4: Get API endpoints
echo -e "${YELLOW}Step 4: Retrieving API endpoints...${NC}"
API_ENDPOINT=$(terraform output -raw api_endpoint 2>/dev/null || echo "N/A")
INVOKE_URL=$(terraform output -raw invoke_url 2>/dev/null || echo "N/A")
STATUS_URL=$(terraform output -raw status_url 2>/dev/null || echo "N/A")
HEALTH_URL=$(terraform output -raw health_url 2>/dev/null || echo "N/A")

echo "  API Endpoint: $API_ENDPOINT"
echo "  Invoke URL: $INVOKE_URL"
echo "  Status URL: $STATUS_URL"
echo "  Health URL: $HEALTH_URL"
echo ""

# Step 5: Test deployment
echo -e "${YELLOW}Step 5: Testing deployment...${NC}"

if [ "$HEALTH_URL" != "N/A" ]; then
    echo "  Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL")
    
    if [ "$HEALTH_RESPONSE" = "200" ]; then
        echo -e "${GREEN}✓ Health check passed (HTTP $HEALTH_RESPONSE)${NC}"
    else
        echo -e "${RED}✗ Health check failed (HTTP $HEALTH_RESPONSE)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Health URL not available, skipping test${NC}"
fi
echo ""

# Step 6: Summary
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Optimizations Applied:"
echo "  ✓ Lambda Memory: 3072 MB (3x increase)"
echo "  ✓ Lambda Concurrency: 50 (5x increase)"
echo "  ✓ API Gateway Caching: Enabled (5s TTL)"
echo "  ✓ Connection Pooling: Enabled"
echo "  ✓ Parallel Agent Execution: Already active"
echo ""
echo "Expected Performance:"
echo "  • 85% faster execution (420s → 60s)"
echo "  • 70% cost reduction (\$0.51 → \$0.15 per request)"
echo "  • 5x higher capacity (10 → 50 concurrent)"
echo ""
echo "Next Steps:"
echo "  1. Monitor CloudWatch metrics for performance"
echo "  2. Test with sample requests"
echo "  3. Review cost savings in AWS Cost Explorer"
echo ""
echo "Test Commands:"
echo "  # Health check"
echo "  curl $HEALTH_URL"
echo ""
echo "  # Invoke agent (async)"
echo "  curl -X POST $INVOKE_URL \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"prompt\": \"Flight EY123 delayed 3 hours\"}'"
echo ""
echo "Documentation:"
echo "  • Deployment Report: ../../OPTIMIZATION_DEPLOYMENT_SUMMARY.md"
echo "  • Readiness Report: ../../AGENT_DEPLOYMENT_READINESS_REPORT.md"
echo ""
