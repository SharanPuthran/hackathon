#!/bin/bash
# Deployment script for AgentCore REST API with Streaming Support

set -e

echo "🚀 Deploying AgentCore REST API with Streaming..."

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
uv pip install --target build/lambda boto3 pydantic websockets awslambdaric

# Create zip package
cd build/lambda
zip -q -r ../lambda_package.zip .
cd ../..

echo "✓ Lambda package created: build/lambda_package.zip"
echo ""

# Step 2: Deploy infrastructure with Terraform
echo "🏗️  Step 2: Deploying infrastructure with Terraform (Streaming)..."
cd infrastructure

# Initialize Terraform
terraform init

# Plan deployment using streaming configuration
terraform plan \
    -var="aws_region=$AWS_REGION" \
    -var="agentcore_runtime_arn=$AGENTCORE_RUNTIME_ARN" \
    -var="environment=$ENVIRONMENT" \
    -out=tfplan

# Apply deployment
terraform apply tfplan

# Get outputs
INVOKE_URL=$(terraform output -raw invoke_url)
HEALTH_URL=$(terraform output -raw health_url)
LAMBDA_FUNCTION_NAME=$(terraform output -raw lambda_function_name)

cd ..

echo ""
echo "✅ Deployment complete!"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "API Endpoints (Lambda Function URLs):"
echo "═══════════════════════════════════════════════════════════"
echo "Invoke:      $INVOKE_URL"
echo "Health:      $HEALTH_URL"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "⚡ Streaming enabled! No more timeouts!"
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
echo "1. Update frontend .env.local with new endpoint:"
echo "   VITE_API_ENDPOINT=$INVOKE_URL"
echo ""
echo "2. Test streaming with:"
echo "   curl -N -X POST $INVOKE_URL \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"prompt\":\"Flight EY123 delayed 2 hours\"}'"
echo ""
echo "3. View logs:"
echo "   aws logs tail /aws/lambda/$LAMBDA_FUNCTION_NAME --follow"
echo ""
echo "🎉 Streaming API is ready! No more 29-second timeout!"
echo ""
