#!/bin/bash
# Deployment script for AgentCore REST API with Async Polling

set -e

echo "🚀 Deploying AgentCore REST API with Async Polling..."

# Configuration
ENVIRONMENT=${1:-dev}
AWS_REGION=${AWS_REGION:-us-east-1}
AGENTCORE_RUNTIME_ARN="arn:aws:bedrock-agentcore:us-east-1:368613657554:runtime/skymarshal_Agent-cn8OdHGjgz"

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
cp src/__init__.py build/lambda/src/ 2>/dev/null || true

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
echo "🏗️  Step 2: Deploying infrastructure with Terraform (Async Polling)..."
cd infrastructure

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
STATUS_URL=$(terraform output -raw status_url)
HEALTH_URL=$(terraform output -raw health_url)
SESSIONS_TABLE=$(terraform output -raw dynamodb_sessions_table)
REQUESTS_TABLE=$(terraform output -raw dynamodb_requests_table)

cd ..

echo ""
echo "✅ Deployment complete!"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "API Endpoints:"
echo "═══════════════════════════════════════════════════════════"
echo "Base:        $API_ENDPOINT"
echo "Invoke:      $INVOKE_URL"
echo "Status:      $STATUS_URL/{request_id}"
echo "Health:      $HEALTH_URL"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "DynamoDB Tables:"
echo "  Sessions:  $SESSIONS_TABLE"
echo "  Requests:  $REQUESTS_TABLE"
echo ""
echo "⚡ Async polling enabled! No more timeouts!"
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
echo "1. Update frontend .env with new endpoint:"
echo "   VITE_API_ENDPOINT=$API_ENDPOINT"
echo ""
echo "2. Test async invoke:"
echo "   curl -X POST $INVOKE_URL \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"prompt\":\"Flight EY123 delayed 2 hours\"}'"
echo ""
echo "3. Check status (use request_id from above):"
echo "   curl $STATUS_URL/{request_id}"
echo ""
echo "4. View Lambda logs:"
echo "   aws logs tail /aws/lambda/skymarshal-api-invoke-$ENVIRONMENT --follow"
echo ""
echo "🎉 Async polling API is ready! No more 29-second timeout!"
echo ""
