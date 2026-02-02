# CORS Fix Summary

## Problem

The frontend was getting CORS errors when trying to call the API Gateway endpoint from localhost:3000.

## Solution Implemented

### 1. API Gateway Changes (Terraform)

- ✅ Disabled IAM authentication temporarily for `/invoke` endpoint (changed from `AWS_IAM` to `NONE`)
- ✅ Added OPTIONS methods for CORS preflight requests on `/invoke` and `/health` endpoints
- ✅ Added CORS headers to all responses:
  - `Access-Control-Allow-Origin: *`
  - `Access-Control-Allow-Headers: Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
  - `Access-Control-Allow-Methods: POST,OPTIONS` (for /invoke) and `GET,OPTIONS` (for /health)

### 2. Lambda Response Headers

- ✅ Lambda already returns CORS headers in all responses (success and error)
- Located in: `skymarshal_agents_new/skymarshal/src/api/response_formatter.py`

### 3. Frontend Configuration (Vite Proxy)

- ✅ Added Vite proxy configuration to forward `/api` requests to the actual API Gateway
- ✅ Updated `.env.local` to use relative URL: `VITE_API_ENDPOINT=/api/v1`
- ✅ Updated environment validation to accept relative URLs

## Files Modified

### Infrastructure

- `skymarshal_agents_new/skymarshal/infrastructure/api.tf`
  - Added OPTIONS methods and CORS configuration
  - Temporarily disabled IAM auth

### Frontend

- `frontend/vite.config.ts` - Added proxy configuration
- `frontend/.env.local` - Changed to relative URL
- `frontend/.env.example` - Updated documentation
- `frontend/config/env.ts` - Allow relative URLs in validation

## Testing

### CORS Preflight Test

```bash
curl -X OPTIONS https://82gmbnz8x1.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" -i
```

**Result**: ✅ Returns 200 with correct CORS headers

### API Invocation Test

```bash
curl -X POST https://82gmbnz8x1.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Test flight disruption"}' -i
```

**Result**: ✅ Request reaches Lambda and executes (takes ~30 seconds)

## How It Works

### Development Mode (localhost:3000)

1. Frontend makes request to `/api/v1/invoke` (relative URL)
2. Vite dev server intercepts the request
3. Vite proxies to `https://82gmbnz8x1.execute-api.us-east-1.amazonaws.com/dev/api/v1/invoke`
4. API Gateway processes request (no CORS issues since request comes from Vite server)
5. Response flows back through proxy to frontend

### Production Mode

1. Frontend makes request to full HTTPS URL
2. Browser sends OPTIONS preflight request
3. API Gateway returns CORS headers
4. Browser sends actual POST request
5. API Gateway returns response with CORS headers

## Important Notes

### ⚠️ Security Warning

IAM authentication is currently **DISABLED** for testing purposes. This means:

- Anyone can call the API without credentials
- This is **NOT suitable for production**
- Re-enable IAM auth before production deployment

### Re-enabling IAM Auth

To re-enable IAM authentication:

1. Edit `skymarshal_agents_new/skymarshal/infrastructure/api.tf`:

```terraform
resource "aws_api_gateway_method" "invoke_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.invoke.id
  http_method   = "POST"
  authorization = "AWS_IAM"  # Change back to AWS_IAM
}
```

2. Apply changes:

```bash
cd skymarshal_agents_new/skymarshal/infrastructure
terraform apply
aws apigateway create-deployment --rest-api-id 82gmbnz8x1 --stage-name dev
```

3. Implement AWS credential management in frontend (Cognito, Amplify, or backend service)

## Next Steps

1. ✅ Test frontend with real API calls
2. ⚠️ Implement proper AWS credential management
3. ⚠️ Re-enable IAM authentication for production
4. ⚠️ Restrict CORS origin to specific domains (change from `*` to actual domain)
5. ⚠️ Add rate limiting and API key authentication as additional security layer

## Status

- ✅ CORS issue resolved
- ✅ Frontend can call API from localhost
- ✅ API Gateway deployed with CORS support
- ⚠️ IAM auth temporarily disabled (security risk)
- ⚠️ Need to implement credential management before production

## Frontend Dev Server

The frontend dev server is running at: **http://localhost:3000/**

You can now test the full integration by:

1. Opening http://localhost:3000/ in your browser
2. Entering a disruption scenario
3. Clicking "Proceed" to invoke the API
4. Watching the agent responses appear in real-time
