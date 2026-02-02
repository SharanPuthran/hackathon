# Streaming API Deployment Plan

## Current Issue

Getting `{"message":"Missing Authentication Token"}` with 401 error because:

1. Frontend is still pointing to old API Gateway endpoint
2. Streaming infrastructure not yet deployed
3. Lambda Function URL not created

## Complete Solution

### Phase 1: Deploy Streaming Infrastructure

**Goal**: Deploy Lambda with Function URL (no API Gateway)

**Steps**:

1. Package Lambda function with streaming handler
2. Deploy Terraform with `api_streaming.tf`
3. Get Lambda Function URL
4. Test streaming endpoint

**Files to Deploy**:

- `skymarshal_agents_new/skymarshal/src/api/lambda_handler_streaming.py` (already created)
- `skymarshal_agents_new/skymarshal/infrastructure/api_streaming.tf` (already created)
- `skymarshal_agents_new/skymarshal/scripts/deploy_api_streaming.sh` (already created)

**Commands**:

```bash
cd skymarshal_agents_new/skymarshal
export AGENTCORE_RUNTIME_ARN="<your-arn>"
./scripts/deploy_api_streaming.sh dev
```

**Expected Output**:

- Lambda Function URL (e.g., `https://abc123.lambda-url.us-east-1.on.aws/`)
- No API Gateway involved
- No 29-second timeout limit

### Phase 2: Update Frontend Configuration

**Goal**: Point frontend to new Lambda Function URL

**Steps**:

1. Update `frontend/.env.local` with new endpoint
2. Remove `/api/v1` path (Lambda Function URL is direct)
3. Update Vite proxy configuration (or remove it)
4. Restart dev server

**Files to Update**:

- `frontend/.env.local`
- `frontend/vite.config.ts` (remove proxy or update)

**New Configuration**:

```env
# Use Lambda Function URL directly (no proxy needed)
VITE_API_ENDPOINT=https://abc123.lambda-url.us-east-1.on.aws/
VITE_AWS_REGION=us-east-1
VITE_API_TIMEOUT=300000  # 5 minutes, no limit now!
```

### Phase 3: Fix Frontend Streaming Code

**Goal**: Ensure frontend correctly handles SSE streaming

**Issues to Fix**:

1. API service `invokeStreaming` method needs correct URL handling
2. Remove `/invoke` path from streaming calls (Lambda Function URL is the handler)
3. Ensure SSE parsing works correctly
4. Handle CORS properly

**Files to Fix**:

- `frontend/services/api.ts` - Fix streaming URL
- `frontend/hooks/useAPI.ts` - Already updated
- `frontend/App.tsx` - Already updated

**Key Changes Needed**:

```typescript
// In api.ts invokeStreaming method
const url = `${this.config.endpoint}`; // Direct URL, no /invoke path
```

### Phase 4: Test End-to-End

**Goal**: Verify streaming works without timeouts

**Test Cases**:

1. Simple disruption (should stream quickly)
2. Complex disruption (should stream over 30+ seconds without timeout)
3. Error handling
4. Session continuity

**Test Command**:

```bash
# Test streaming directly
curl -N -X POST https://abc123.lambda-url.us-east-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Flight EY123 delayed 2 hours due to weather"}'
```

## Detailed Implementation Steps

### Step 1: Check Prerequisites

```bash
# Verify AgentCore Runtime ARN
echo $AGENTCORE_RUNTIME_ARN

# Verify AWS credentials
aws sts get-caller-identity

# Verify UV is installed
uv --version
```

### Step 2: Package Lambda

```bash
cd skymarshal_agents_new/skymarshal

# Clean previous builds
rm -rf build

# Create build directory
mkdir -p build/lambda

# Copy source files
mkdir -p build/lambda/src
cp -r src/api build/lambda/src/
cp -r src/api build/lambda/api
cp src/__init__.py build/lambda/src/

# Install dependencies
uv pip install --target build/lambda boto3 pydantic websockets awslambdaric

# Create zip
cd build/lambda
zip -q -r ../lambda_package.zip .
cd ../..
```

### Step 3: Deploy with Terraform

```bash
cd infrastructure

# Initialize Terraform
terraform init

# Plan with streaming config
terraform plan \
  -var="aws_region=us-east-1" \
  -var="agentcore_runtime_arn=$AGENTCORE_RUNTIME_ARN" \
  -var="environment=dev" \
  -target=module.api_streaming \
  -out=tfplan

# Apply
terraform apply tfplan

# Get outputs
LAMBDA_URL=$(terraform output -raw invoke_url)
echo "Lambda Function URL: $LAMBDA_URL"
```

### Step 4: Update Frontend

```bash
cd ../../frontend

# Update .env.local
cat > .env.local << EOF
# SkyMarshal API Configuration - Streaming
VITE_API_ENDPOINT=$LAMBDA_URL
VITE_AWS_REGION=us-east-1
VITE_API_TIMEOUT=300
VITE_ENABLE_MOCK=false
EOF

# Restart dev server
npm run dev
```

### Step 5: Fix API Service

Update `frontend/services/api.ts`:

```typescript
async invokeStreaming(
    request: InvokeRequest,
    onChunk: (chunk: any) => void,
    onComplete: (response: InvokeResponse) => void,
    onError: (error: APIError) => void
): Promise<void> {
    // Use endpoint directly - Lambda Function URL is the handler
    const url = this.config.endpoint;
    const body = JSON.stringify(request);

    try {
        const headers: Record<string, string> = {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        };

        const response = await fetch(url, {
            method: 'POST',
            headers,
            body,
        });

        if (!response.ok) {
            throw await this.handleHttpError(response);
        }

        // Handle streaming response
        const reader = response.body?.getReader();
        if (!reader) {
            throw new Error('Response body is not readable');
        }

        const decoder = new TextDecoder();
        let buffer = '';
        let metadata: any = null;
        const chunks: any[] = [];

        while (true) {
            const { done, value } = await reader.read();

            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.substring(6));

                    if (data.type === 'metadata') {
                        metadata = data;
                    } else if (data.type === 'chunk') {
                        chunks.push(data.data);
                        onChunk(data.data);
                    } else if (data.type === 'complete') {
                        const completeResponse: InvokeResponse = {
                            status: 'success',
                            request_id: metadata?.request_id || '',
                            session_id: metadata?.session_id || '',
                            execution_time_ms: data.execution_time_ms,
                            timestamp: new Date().toISOString(),
                            assessment: this.aggregateChunks(chunks),
                        };
                        onComplete(completeResponse);
                    } else if (data.type === 'error') {
                        onError({
                            type: APIErrorType.SERVER_ERROR,
                            message: data.error_message,
                            retryable: false,
                        });
                    }
                }
            }
        }
    } catch (error) {
        onError(this.handleError(error));
    }
}
```

## Troubleshooting

### Issue: 401 Missing Authentication Token

**Cause**: Still hitting old API Gateway endpoint
**Fix**: Update VITE_API_ENDPOINT to Lambda Function URL

### Issue: CORS errors

**Cause**: Lambda Function URL CORS not configured
**Fix**: Already configured in `api_streaming.tf`

### Issue: Streaming not working

**Cause**: Response not in SSE format
**Fix**: Verify Lambda handler uses `response_stream.write()`

### Issue: Chunks not appearing

**Cause**: Frontend SSE parsing incorrect
**Fix**: Check `data: ` prefix and `\n\n` delimiters

## Success Criteria

✅ Lambda Function URL deployed
✅ Frontend connects to Lambda Function URL
✅ No 401 errors
✅ No timeout errors (even for 60+ second requests)
✅ Agent responses stream progressively
✅ UI updates as chunks arrive
✅ Session management works
✅ Error handling works

## Rollback Plan

If streaming doesn't work:

1. Keep old API Gateway endpoint in `.env.local`
2. Use buffered mode with retries
3. Debug streaming separately

## Next Steps After Success

1. Add authentication to Lambda Function URL
2. Implement progress indicators in UI
3. Add streaming status messages
4. Optimize chunk aggregation
5. Add metrics and monitoring
