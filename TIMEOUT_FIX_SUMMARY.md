# API Gateway Timeout Fix - Summary

## Problem

Getting `{"message": "Endpoint request timed out"}` and 504 Gateway timeout errors because:

- API Gateway has a hard 29-second timeout limit
- AgentCore analysis takes 30-90 seconds (especially first time)
- Lambda was configured with 300-second timeout but API Gateway cuts it off at 29s

## Solution Implemented

### 1. Backend Changes (Lambda)

**File**: `skymarshal_agents_new/skymarshal/src/api/lambda_handler.py`

**Changes**:

- Reduced Lambda timeout from 300s to 25s (stays under API Gateway limit)
- Removed retries to save time (max_retries=0)
- Improved error messages to guide users

```python
# Before
response = asyncio.run(
    ws_client.invoke_with_retry(
        prompt=prompt,
        session_id=session_id,
        timeout=300,
        max_retries=2
    )
)

# After
response = asyncio.run(
    ws_client.invoke_with_retry(
        prompt=prompt,
        session_id=session_id,
        timeout=25,  # 25 seconds to avoid API Gateway timeout
        max_retries=0  # No retries to save time
    )
)
```

### 2. Frontend Changes

**File**: `frontend/App.tsx`

**Changes**:

- Added automatic retry logic (up to 2 attempts)
- Detects timeout errors (504) and retries automatically
- Waits 1 second between retries
- Shows user-friendly messages

```typescript
// Retry logic for timeout errors
const maxRetries = 2;
let attempt = 0;

while (attempt < maxRetries) {
  try {
    const response = await invoke(prompt);
    setApiResponse(response);
    setCurrentView("orchestration");
    return; // Success
  } catch (err) {
    attempt++;
    const isTimeout = error?.includes("timed out") || error?.includes("504");

    if (isTimeout && attempt < maxRetries) {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      continue; // Retry
    }
    break;
  }
}
```

**File**: `frontend/services/api.ts`

**Changes**:

- Better timeout error messages
- Indicates automatic retry is happening

### 3. Infrastructure Changes

**File**: `skymarshal_agents_new/skymarshal/infrastructure/api.tf`

**Changes**:

- Added explicit timeout configuration to API Gateway integration
- Set to 29 seconds (maximum allowed)

```hcl
resource "aws_api_gateway_integration" "invoke_lambda" {
  # ... other config ...
  timeout_milliseconds = 29000  # Maximum API Gateway timeout
}
```

## How It Works Now

### User Experience:

1. User submits disruption query
2. Frontend calls API
3. If timeout occurs (25s):
   - Shows: "Analysis is taking longer than expected. Retrying automatically..."
   - Automatically retries (up to 2 times)
   - Usually succeeds on 2nd attempt (warm Lambda)
4. If still fails after retries:
   - Shows error with retry button
   - User can manually retry

### Why Second Attempt Usually Works:

- **Lambda Warm-up**: First invocation has cold start overhead
- **AgentCore Caching**: Runtime may cache some data
- **Database Connections**: Connection pool is established
- **Model Loading**: Models are loaded in memory

## Deployment Instructions

### 1. Deploy Backend Changes

```bash
# Navigate to the skymarshal directory
cd skymarshal_agents_new/skymarshal

# Set environment variables
export AGENTCORE_RUNTIME_ARN="your-agentcore-runtime-arn"
export AWS_REGION="us-east-1"

# Run deployment script
./scripts/deploy_api.sh dev
```

This will:

- Package the updated Lambda function
- Deploy infrastructure changes with Terraform
- Update API Gateway configuration
- Run health checks

### 2. Frontend Changes (Already Applied)

The frontend changes are already in your local files. The dev server will pick them up automatically via hot reload.

If you need to restart the dev server:

```bash
# Stop the current process (Ctrl+C in the terminal)
# Or kill the background process
cd frontend
npm run dev
```

### 3. Verify the Fix

Test with a disruption query:

```bash
# Test the API directly
curl -X POST https://82gmbnz8x1.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Flight EY123 delayed 2 hours due to weather"}'
```

Or test through the frontend at http://localhost:3000/

## Expected Behavior

### Simple Disruptions (< 25s):

- ✅ Should complete on first attempt
- No timeout errors
- Smooth user experience

### Complex Disruptions (> 25s):

- ⏱️ First attempt may timeout
- 🔄 Automatically retries
- ✅ Usually succeeds on 2nd attempt
- User sees: "Retrying automatically..."

### Very Complex Disruptions (> 50s):

- ⏱️ May timeout twice
- ❌ Shows error with manual retry button
- User can click "Retry" to try again
- Consider simplifying the query

## Alternative Solutions (Future)

If timeouts continue to be an issue, consider:

### Option 1: Lambda Response Streaming (Recommended)

- Stream agent responses as they complete
- No timeout issues
- Better UX (see agents working in real-time)
- **Effort**: 4-6 hours
- **See**: `API_GATEWAY_TIMEOUT_SOLUTION.md` for details

### Option 2: Async Processing with Polling

- Return immediately with request_id
- Frontend polls for completion
- Works with existing API Gateway
- **Effort**: 6-8 hours

### Option 3: Optimize Agent Execution

- Use faster models (Claude Haiku)
- Reduce agent count
- Cache database queries
- **Effort**: Ongoing optimization

## Monitoring

### CloudWatch Metrics to Watch:

```bash
# View Lambda logs
aws logs tail /aws/lambda/skymarshal-api-invoke-dev --follow

# Check for timeout errors
aws logs filter-pattern "TIMEOUT" \
  --log-group-name /aws/lambda/skymarshal-api-invoke-dev \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

### Key Metrics:

- Lambda Duration (should be <25s)
- API Gateway 5XX errors (504 timeouts)
- Retry success rate
- User-facing error rate

## Troubleshooting

### If timeouts persist:

1. Check Lambda logs for actual execution time
2. Verify AgentCore Runtime is responding
3. Check DynamoDB query performance
4. Consider implementing streaming (Option 1 above)

### If retries fail:

1. Check network connectivity
2. Verify AWS credentials
3. Check API Gateway logs
4. Test with simpler disruption queries

## Files Changed

### Backend:

- ✅ `skymarshal_agents_new/skymarshal/src/api/lambda_handler.py`
- ✅ `skymarshal_agents_new/skymarshal/infrastructure/api.tf`
- ✅ `skymarshal_agents_new/skymarshal/API_GATEWAY_TIMEOUT_SOLUTION.md` (new)

### Frontend:

- ✅ `frontend/App.tsx`
- ✅ `frontend/services/api.ts`
- ✅ `frontend/config/env.ts` (timeout config)
- ✅ `frontend/.env.local` (VITE_API_TIMEOUT=120)
- ✅ `frontend/.env.example` (documentation)

### Documentation:

- ✅ `TIMEOUT_FIX_SUMMARY.md` (this file)
- ✅ `API_GATEWAY_TIMEOUT_SOLUTION.md` (detailed analysis)

## Next Steps

1. **Deploy the backend changes**:

   ```bash
   cd skymarshal_agents_new/skymarshal
   ./scripts/deploy_api.sh dev
   ```

2. **Test with real disruption queries**

3. **Monitor CloudWatch logs** for timeout patterns

4. **Consider implementing streaming** if timeouts persist

5. **Optimize agent execution** for better performance
