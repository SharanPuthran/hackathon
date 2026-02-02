# Deploy Async Polling Solution - Complete Guide

## Why This Solves Your Problem

**Your Issue**: AgentCore takes 2-5 minutes to respond, but API Gateway times out at 29 seconds.

**This Solution**:

- Initial request returns in < 1 second ✅
- AgentCore processes in background for as long as needed (up to 15 minutes) ✅
- Frontend polls for results every 2 seconds ✅
- **NO TIMEOUT ISSUES** ✅

## Architecture

```
User submits prompt
    ↓
POST /invoke (returns in < 1s)
    ↓
Lambda stores in DynamoDB: status="processing"
    ↓
Lambda invokes itself async
    ↓
Background Lambda calls AgentCore (2-5 minutes, no problem!)
    ↓
Updates DynamoDB: status="complete", assessment={...}
    ↓
Frontend polls GET /status/{request_id} every 2s
    ↓
Gets result when complete
```

## Step-by-Step Deployment

### Step 1: Create DynamoDB Table for Requests

```bash
cd skymarshal_agents_new/skymarshal

# Create the requests table
aws dynamodb create-table \
  --table-name skymarshal-requests-dev \
  --attribute-definitions \
    AttributeName=request_id,AttributeType=S \
  --key-schema \
    AttributeName=request_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --time-to-live-specification \
    Enabled=true,AttributeName=ttl \
  --region us-east-1
```

### Step 2: Update Terraform Configuration

Add the requests table and status endpoint to `infrastructure/api.tf`:

```hcl
# Add after the sessions table

# DynamoDB Table for Async Requests
resource "aws_dynamodb_table" "requests" {
  name           = "skymarshal-requests-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "request_id"

  attribute {
    name = "request_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "skymarshal-requests"
    Environment = var.environment
  }
}

# Update Lambda IAM policy to include requests table
resource "aws_iam_role_policy" "lambda_policy" {
  name = "skymarshal-api-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeRuntime",
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:GetRuntime"
        ]
        Resource = "${var.agentcore_runtime_arn}*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:DescribeTable"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn,
          aws_dynamodb_table.requests.arn  # Add this
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"  # Add this for async invocation
        ]
        Resource = aws_lambda_function.invoke_handler.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Update Lambda function to use async handler
resource "aws_lambda_function" "invoke_handler" {
  filename      = "../build/lambda_package.zip"
  function_name = "skymarshal-api-invoke-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "src.api.lambda_handler_async.lambda_handler"  # Changed
  runtime       = "python3.11"
  timeout       = 900  # 15 minutes for background processing
  memory_size   = 1024

  environment {
    variables = {
      AGENTCORE_RUNTIME_ARN = var.agentcore_runtime_arn
      SKYMARSHAL_AWS_REGION = var.aws_region
      SESSION_TABLE_NAME    = aws_dynamodb_table.sessions.name
      REQUESTS_TABLE_NAME   = aws_dynamodb_table.requests.name  # Add this
      LOG_LEVEL             = "INFO"
    }
  }

  reserved_concurrent_executions = 10

  tags = {
    Name        = "skymarshal-api-invoke"
    Environment = var.environment
  }
}

# Add status endpoint
resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "status"
}

resource "aws_api_gateway_resource" "status_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.status.id
  path_part   = "{request_id}"
}

resource "aws_api_gateway_method" "status_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "status_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.status_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "status_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.status_id.id
  http_method             = aws_api_gateway_method.status_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.invoke_handler.invoke_arn
}

resource "aws_api_gateway_integration" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}
```

### Step 3: Deploy Backend

```bash
cd skymarshal_agents_new/skymarshal

# Set environment variables
export AGENTCORE_RUNTIME_ARN="your-agentcore-runtime-arn"
export AWS_REGION="us-east-1"

# Package Lambda
rm -rf build
mkdir -p build/lambda
mkdir -p build/lambda/src
cp -r src/api build/lambda/src/
cp -r src/api build/lambda/api
cp src/__init__.py build/lambda/src/

# Install dependencies
uv pip install --target build/lambda boto3 pydantic websockets

# Create zip
cd build/lambda
zip -q -r ../lambda_package.zip .
cd ../..

# Deploy with Terraform
cd infrastructure
terraform init
terraform plan -var="agentcore_runtime_arn=$AGENTCORE_RUNTIME_ARN" -out=tfplan
terraform apply tfplan
cd ..
```

### Step 4: Update Frontend

Create `frontend/services/apiAsync.ts`:

```typescript
import { APIService, InvokeRequest, InvokeResponse, APIError } from "./api";

export class AsyncAPIService extends APIService {
  /**
   * Invoke with async polling
   */
  async invokeWithPolling(
    request: InvokeRequest,
    onProgress?: (status: string, elapsedSeconds: number) => void,
  ): Promise<InvokeResponse> {
    // Start async processing
    const requestId = await this.startAsync(request);

    const startTime = Date.now();
    let pollCount = 0;

    // Poll for completion
    while (true) {
      await new Promise((r) => setTimeout(r, 2000)); // Wait 2 seconds
      pollCount++;

      const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);

      try {
        const status = await this.checkStatus(requestId);

        if (onProgress) {
          onProgress(status.status, elapsedSeconds);
        }

        if (status.status === "complete") {
          return {
            status: "success",
            request_id: requestId,
            session_id: status.session_id,
            execution_time_ms: status.execution_time_ms,
            timestamp: new Date().toISOString(),
            assessment: status.assessment,
          };
        } else if (status.status === "error") {
          throw {
            type: "SERVER_ERROR",
            message: status.error || "Processing failed",
            retryable: false,
          } as APIError;
        }

        // Continue polling if status is 'processing'
        // Safety check: stop after 10 minutes
        if (elapsedSeconds > 600) {
          throw {
            type: "TIMEOUT_ERROR",
            message: "Processing exceeded 10 minutes",
            retryable: true,
          } as APIError;
        }
      } catch (error) {
        // If it's an API error, throw it
        if ((error as APIError).type) {
          throw error;
        }
        // Otherwise, continue polling (might be temporary network issue)
        console.warn(`Poll attempt ${pollCount} failed:`, error);
      }
    }
  }

  /**
   * Start async processing
   */
  private async startAsync(request: InvokeRequest): Promise<string> {
    const url = `${this.config.endpoint}/invoke`;
    const body = JSON.stringify(request);

    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });

    if (!response.ok) {
      throw await this.handleHttpError(response);
    }

    const data = await response.json();
    return data.request_id;
  }

  /**
   * Check status of async request
   */
  private async checkStatus(requestId: string): Promise<any> {
    const url = `${this.config.endpoint}/status/${requestId}`;

    const response = await fetch(url);

    if (!response.ok) {
      throw await this.handleHttpError(response);
    }

    return await response.json();
  }
}
```

Update `frontend/hooks/useAPI.ts`:

```typescript
import { useState, useCallback } from "react";
import { AsyncAPIService } from "../services/apiAsync";
import { InvokeResponse, APIError } from "../services/api";
import { getConfig } from "../config/env";
import { useSession } from "./useSession";

export interface UseAPIReturn {
  invoke: (
    prompt: string,
    onProgress?: (status: string, elapsed: number) => void,
  ) => Promise<InvokeResponse>;
  loading: boolean;
  error: string | null;
  progress: string | null;
  clearError: () => void;
}

export function useAPI(): UseAPIReturn {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const { sessionId, setSessionId } = useSession(false);

  const invoke = useCallback(
    async (
      prompt: string,
      onProgress?: (status: string, elapsed: number) => void,
    ): Promise<InvokeResponse> => {
      setLoading(true);
      setError(null);
      setProgress("Starting...");

      try {
        const config = getConfig();
        const apiService = new AsyncAPIService({
          endpoint: config.apiEndpoint,
          region: config.awsRegion,
          timeout: config.apiTimeout,
        });

        const response = await apiService.invokeWithPolling(
          {
            prompt,
            session_id: sessionId || undefined,
          },
          (status, elapsed) => {
            setProgress(`${status} (${elapsed}s)`);
            if (onProgress) {
              onProgress(status, elapsed);
            }
          },
        );

        if (response.session_id) {
          setSessionId(response.session_id);
        }

        setLoading(false);
        setProgress(null);
        return response;
      } catch (err) {
        setLoading(false);
        setProgress(null);

        if ((err as APIError).type) {
          const apiError = err as APIError;
          setError(apiError.message);
          throw apiError;
        }

        const errorMessage =
          err instanceof Error ? err.message : "An unexpected error occurred";
        setError(errorMessage);
        throw err;
      }
    },
    [sessionId, setSessionId],
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    invoke,
    loading,
    error,
    progress,
    clearError,
  };
}
```

Update `frontend/App.tsx`:

```typescript
const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<"landing" | "orchestration">("landing");
  const [userPrompt, setUserPrompt] = useState<string>("");
  const [apiResponse, setApiResponse] = useState<InvokeResponse | null>(null);
  const { invoke, loading, error, progress, clearError } = useAPI();

  const handleProcess = async (prompt: string) => {
    setUserPrompt(prompt);
    clearError();

    try {
      const response = await invoke(prompt);
      setApiResponse(response);
      setCurrentView("orchestration");
    } catch (err) {
      console.error("Failed to invoke API:", err);
    }
  };

  return (
    <div className="relative w-full h-screen">
      <Background />
      <div className="relative z-10 w-full h-full flex flex-col">
        {currentView === "landing" && (
          <LandingPage
            onProcess={handleProcess}
            loading={loading}
            error={error}
            progress={progress}  // Show progress
            onRetry={() => handleProcess(userPrompt)}
          />
        )}
        {currentView === "orchestration" && apiResponse && (
          <OrchestrationView prompt={userPrompt} apiResponse={apiResponse} />
        )}
      </div>
    </div>
  );
};
```

### Step 5: Test

```bash
# Test async invoke
curl -X POST https://your-api.com/api/v1/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Flight EY123 delayed 2 hours"}'

# Response: {"status":"accepted","request_id":"abc-123","poll_url":"/api/v1/status/abc-123"}

# Poll status
curl https://your-api.com/api/v1/status/abc-123

# Response (processing): {"request_id":"abc-123","status":"processing"}
# Response (complete): {"request_id":"abc-123","status":"complete","assessment":{...}}
```

## Success Criteria

✅ POST /invoke returns in < 1 second
✅ No 504 timeout errors
✅ AgentCore can process for 2-5 minutes without issues
✅ Frontend shows progress while polling
✅ Results appear when complete

## Troubleshooting

**Issue**: Still getting 504 errors
**Fix**: Make sure you're using the new `lambda_handler_async.py` handler

**Issue**: Status always shows "processing"
**Fix**: Check Lambda logs to see if background processing is working

**Issue**: Frontend not polling
**Fix**: Check browser console for errors in polling logic

## Next Steps

1. Deploy backend (Steps 1-3)
2. Update frontend (Step 4)
3. Test end-to-end
4. Add progress indicators in UI
5. Add retry logic for failed requests
