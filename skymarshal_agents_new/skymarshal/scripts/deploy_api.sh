#!/bin/bash
# Deployment script for AgentCore REST API

set -e

echo "🚀 Deploying AgentCore REST API..."

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AGENTCORE_RUNTIME_ARN=${AGENTCORE_RUNTIME_ARN}

if [ -z "$AGENTCORE_RUNTIME_ARN" ]; then
    echo "❌ Error: AGENTCORE_RUNTIME_ARN environment variable is required"
    exit 1
fi

echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "AgentCore Runtime ARN: $AGENTCORE_RUNTIME_ARN"
echo ""

# Step 1: Package Lambda function
echo "📦 Step 1: Packaging Lambda function..."
cd "$(dirname "$0")/.."

# Create temporary directory for packaging
rm -rf build
mkdir -p build/lambda

# Copy source files
mkdir -p build/lambda/src
cp -r src/api build/lambda/src/
cp -r src/api build/lambda/api
cp src/__init__.py build/lambda/src/

# Install dependencies
echo "Installing dependencies..."
uv pip install --target build/lambda boto3 pydantic websockets

# Create zip package
cd build/lambda
zip -q -r ../lambda_package.zip .
cd ../..

echo "✓ Lambda package created: build/lambda_package.zip"
echo ""

# Step 2: Deploy infrastructure with Terraform
echo "🏗️  Step 2: Deploying infrastructure with Terraform..."
cd infrastructure

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
    -var="aws_region=$AWS_REGION" \
    -var="agentcore_runtime_arn=$AGENTCORE_RUNTIME_ARN" \
    -var="environment=$ENVIRONMENT" \
    -out=tfplan

# Apply deployment
terraform apply tfplan

# Get outputs
API_ENDPOINT=$(terraform output -raw api_endpoint)
INVOKE_URL=$(terraform output -raw invoke_url)
HEALTH_URL=$(terraform output -raw health_url)

cd ..

echo ""
echo "✅ Deployment complete!"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "API Endpoints:"
echo "═══════════════════════════════════════════════════════════"
echo "Base URL:    $API_ENDPOINT"
echo "Invoke:      $INVOKE_URL"
echo "Health:      $HEALTH_URL"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Step 3: Validate deployment
echo "🔍 Step 3: Validating deployment..."
echo "Testing health endpoint..."

HEALTH_RESPONSE=$(curl -s "$HEALTH_URL")
HEALTH_STATUS=$(echo "$HEALTH_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "error")

if [ "$HEALTH_STATUS" = "healthy" ] || [ "$HEALTH_STATUS" = "degraded" ]; then
    echo "✓ Health check passed: $HEALTH_STATUS"
else
    echo "⚠️  Health check returned: $HEALTH_STATUS"
fi

echo ""
echo "📝 Next steps:"
echo "1. Configure AWS credentials with appropriate permissions"
echo "2. Test the API with: curl -X POST $INVOKE_URL -d '{\"prompt\":\"Flight delayed\"}'"
echo "3. View logs: aws logs tail /aws/lambda/skymarshal-api-invoke-$ENVIRONMENT --follow"
echo ""
