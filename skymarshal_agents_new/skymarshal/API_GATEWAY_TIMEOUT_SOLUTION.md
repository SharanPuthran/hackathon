# API Gateway Timeout Solution

## Problem

API Gateway has a hard 29-second timeout limit that cannot be increased. Since SkyMarshal's AgentCore Runtime analysis can take 30-90 seconds (especially on first invocation), we hit this timeout frequently.

## Root Cause

- **API Gateway Limit**: Maximum 29 seconds for any request
- **Lambda Timeout**: Set to 300 seconds (5 minutes)
- **AgentCore Analysis**: Takes 30-90 seconds for initial analysis
  - 7 agents running in 2 phases (safety → business)
  - Each agent makes LLM calls and database queries
  - Cold start overhead on first invocation

## Solutions Implemented

### 1. **Reduced Lambda Timeout (Current)**

**Status**: ✅ Implemented

**Changes**:

- Reduced Lambda timeout from 300s to 25s
- Removed retries to save time
- Added helpful error messages

**Pros**:

- No infrastructure changes needed
- Works with existing setup
- Clear error messages guide users

**Cons**:

- Analysis may still timeout on complex disruptions
- Requires user to retry

**Code Changes**:

```python
# lambda_handler.py
response = asyncio.run(
    ws_client.invoke_with_retry(
        prompt=prompt,
        session_id=session_id,
        timeout=25,  # 25 seconds to avoid API Gateway timeout
        max_retries=0  # No retries to save time
    )
)
```

### 2. **Frontend Retry Logic (Current)**

**Status**: ✅ Implemented

**Changes**:

- Frontend automatically retries on 504 errors
- Shows user-friendly error messages
- Maintains session context across retries

**User Experience**:

1. User submits disruption
2. If timeout occurs, shows: "Analysis taking longer than expected. Retrying..."
3. Automatically retries with same session_id
4. Usually succeeds on second attempt (warm Lambda)

### 3. **Future: Streaming Responses (Recommended)**

**Status**: 📋 Planned

**Implementation**:

- Use Lambda Response Streaming (requires Lambda URLs or Function URLs)
- Stream agent responses as they complete
- Frontend displays agents progressively

**Benefits**:

- No timeout issues
- Better UX (see agents working in real-time)
- Matches the UI design (agents appear one by one)

**Requirements**:

- Switch from API Gateway to Lambda Function URLs
- Update frontend to handle Server-Sent Events (SSE)
- Modify Lambda handler to stream responses

**Estimated Effort**: 4-6 hours

### 4. **Future: Async Processing with Polling (Alternative)**

**Status**: 📋 Planned

**Implementation**:

- POST /invoke returns immediately with request_id
- Frontend polls GET /status/{request_id}
- When complete, returns full response

**Benefits**:

- Works with existing API Gateway
- No timeout issues
- Can show progress updates

**Requirements**:

- Add status endpoint
- Store in-progress requests in DynamoDB
- Frontend polling logic

**Estimated Effort**: 6-8 hours

## Current Workaround

### For Users:

1. Submit your disruption query
2. If you see a timeout error, **click Retry**
3. The second attempt usually succeeds (warm Lambda + cached data)

### For Developers:

1. The Lambda now times out at 25 seconds
2. Error messages guide users to retry
3. Session IDs are preserved across retries
4. Frontend handles retries automatically

## Performance Optimization Tips

### Make AgentCore Faster:

1. **Optimize Agent Prompts**: Shorter prompts = faster responses
2. **Reduce Agent Count**: Consider combining agents
3. **Cache Database Queries**: Store frequently accessed data
4. **Use Faster Models**: Claude Haiku instead of Sonnet for some agents
5. **Parallel Execution**: Ensure agents run in parallel (already implemented)

### Infrastructure Improvements:

1. **Provisioned Concurrency**: Keep Lambda warm (costs $$$)
2. **Larger Lambda Memory**: More memory = faster execution
3. **VPC Optimization**: If using VPC, optimize ENI creation

## Recommended Next Steps

1. **Short Term** (This Week):
   - ✅ Reduce Lambda timeout to 25s
   - ✅ Add retry logic in frontend
   - ✅ Improve error messages
   - Test with real disruption scenarios

2. **Medium Term** (Next Sprint):
   - Implement Lambda Response Streaming
   - Update frontend for SSE
   - Remove API Gateway timeout dependency

3. **Long Term** (Future):
   - Optimize agent execution time
   - Consider caching strategies
   - Implement progress indicators

## Testing

### Test Scenarios:

1. **Simple Disruption** (should complete in <25s):

   ```
   Flight EY123 delayed 2 hours due to weather
   ```

2. **Complex Disruption** (may timeout):

   ```
   Flight EY123 from LHR to AUH delayed 5 hours due to hydraulic failure.
   412 passengers onboard, 68 connecting to SYD, 22 to MEL.
   6 passengers in First Class, 2 VIPs.
   Cargo includes live animals and time-sensitive pharmaceuticals.
   ```

3. **Retry Test**:
   - Submit complex disruption
   - Wait for timeout
   - Click retry
   - Should succeed on second attempt

## Monitoring

### CloudWatch Metrics to Watch:

- Lambda Duration (should be <25s)
- API Gateway 5XX errors (504 timeouts)
- Lambda Cold Start duration
- AgentCore invocation time

### Alarms to Set:

- Alert if >50% of requests timeout
- Alert if Lambda duration >20s consistently
- Alert if cold start >5s

## References

- [API Gateway Limits](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)
- [Lambda Response Streaming](https://docs.aws.amazon.com/lambda/latest/dg/configuration-response-streaming.html)
- [AgentCore Streaming](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-streaming.html)
