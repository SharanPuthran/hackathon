# Async Polling Solution for Timeout Issues

## Problem

- API Gateway has 29-second timeout
- AgentCore analysis takes 30-90 seconds
- Lambda streaming requires complex setup (Lambda Web Adapter + Docker)

## Solution: Async Processing with Polling

### How It Works

```
1. User submits prompt
   ↓
2. POST /invoke returns immediately with request_id
   Response: {"request_id": "abc123", "status": "processing"}
   ↓
3. Lambda processes in background (async)
   ↓
4. Frontend polls GET /status/abc123 every 2 seconds
   ↓
5. When complete, returns full response
   Response: {"request_id": "abc123", "status": "complete", "assessment": {...}}
```

### Benefits

- ✅ No timeout issues (returns immediately)
- ✅ Works with existing infrastructure
- ✅ Simple to implement
- ✅ Production-ready pattern
- ✅ No complex Docker/Web Adapter setup

### Implementation

#### Backend Changes

**1. Update Lambda to support async mode**

```python
# lambda_handler.py
import asyncio
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('skymarshal-requests')

def lambda_handler(event, context):
    path = event.get('path', '')

    if path == '/invoke':
        return handle_invoke_async(event)
    elif path.startswith('/status/'):
        request_id = path.split('/')[-1]
        return handle_status_check(request_id)

def handle_invoke_async(event):
    """Start async processing and return immediately"""
    body = json.loads(event['body'])
    request_id = str(uuid.uuid4())

    # Store request in DynamoDB
    table.put_item(Item={
        'request_id': request_id,
        'status': 'processing',
        'prompt': body['prompt'],
        'session_id': body.get('session_id'),
        'created_at': int(time.time()),
        'ttl': int(time.time()) + 3600  # 1 hour TTL
    })

    # Invoke Lambda asynchronously
    lambda_client = boto3.client('lambda')
    lambda_client.invoke(
        FunctionName=context.function_name,
        InvocationType='Event',  # Async invocation
        Payload=json.dumps({
            'action': 'process',
            'request_id': request_id,
            'prompt': body['prompt'],
            'session_id': body.get('session_id')
        })
    )

    # Return immediately
    return {
        'statusCode': 202,  # Accepted
        'headers': {'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({
            'request_id': request_id,
            'status': 'processing',
            'message': 'Request accepted. Poll /status/{request_id} for results.'
        })
    }

def handle_status_check(request_id):
    """Check status of async request"""
    try:
        response = table.get_item(Key={'request_id': request_id})
        item = response.get('Item')

        if not item:
            return {
                'statusCode': 404,
                'headers': {'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'Request not found'})
            }

        return {
            'statusCode': 200,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps(item, default=str)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }
```

**2. Add status endpoint to API Gateway**

```hcl
# api.tf
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
```

#### Frontend Changes

**1. Update API service**

```typescript
// api.ts
async invokeAsync(request: InvokeRequest): Promise<string> {
    const url = `${this.config.endpoint}/invoke`;
    const response = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(request),
    });

    const data = await response.json();
    return data.request_id;
}

async checkStatus(requestId: string): Promise<InvokeResponse> {
    const url = `${this.config.endpoint}/status/${requestId}`;
    const response = await fetch(url);
    return await response.json();
}

async invokeWithPolling(
    request: InvokeRequest,
    onProgress?: (status: string) => void
): Promise<InvokeResponse> {
    // Start async processing
    const requestId = await this.invokeAsync(request);

    // Poll for completion
    while (true) {
        await new Promise(r => setTimeout(r, 2000)); // Wait 2 seconds

        const status = await this.checkStatus(requestId);

        if (onProgress) {
            onProgress(status.status);
        }

        if (status.status === 'complete') {
            return status;
        } else if (status.status === 'error') {
            throw new Error(status.error);
        }

        // Continue polling if status is 'processing'
    }
}
```

**2. Update App.tsx**

```typescript
const handleProcess = async (prompt: string) => {
  setUserPrompt(prompt);
  clearError();

  try {
    const response = await invokeWithPolling({ prompt }, (status) => {
      // Update UI with status
      console.log("Status:", status);
    });

    setApiResponse(response);
    setCurrentView("orchestration");
  } catch (err) {
    console.error("Failed:", err);
  }
};
```

### Deployment Steps

1. Update Lambda handler
2. Update Terraform to add /status endpoint
3. Deploy: `terraform apply`
4. Update frontend code
5. Test

### Testing

```bash
# Test async invoke
curl -X POST https://your-api.com/api/v1/invoke \
  -d '{"prompt":"test"}' \
  -H "Content-Type: application/json"

# Response: {"request_id": "abc123", "status": "processing"}

# Poll status
curl https://your-api.com/api/v1/status/abc123

# Response: {"request_id": "abc123", "status": "complete", "assessment": {...}}
```

## Comparison with Streaming

| Feature                | Async Polling | Streaming               |
| ---------------------- | ------------- | ----------------------- |
| Setup Complexity       | Low           | High                    |
| Infrastructure Changes | Minimal       | Major                   |
| Works with Python      | ✅ Yes        | ❌ Requires Web Adapter |
| Implementation Time    | 30 min        | 4-6 hours               |
| Production Ready       | ✅ Yes        | ⚠️ Complex              |
| No Timeouts            | ✅ Yes        | ✅ Yes                  |

## Recommendation

**Use Async Polling** for immediate solution. Consider streaming later if needed.
