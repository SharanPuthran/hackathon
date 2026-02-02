# Design Document

## Overview

This design specifies a REST API layer for exposing the SkyMarshal AgentCore Runtime system. The solution uses AWS API Gateway with Lambda proxy integration to provide HTTP endpoints that wrap AgentCore Runtime WebSocket invocations. This approach enables external applications to invoke the deployed agent using standard HTTP POST requests while maintaining AWS SSO authentication and session management.

The design prioritizes simplicity, security, and cost-effectiveness by leveraging serverless AWS services and the AgentCore Runtime SDK's built-in WebSocket client capabilities.

## Architecture

### High-Level Architecture

```
┌─────────────────┐
│  Client App     │
│  (HTTP POST)    │
└────────┬────────┘
         │
         │ HTTPS
         ▼
┌─────────────────────────────────────┐
│   AWS API Gateway (REST API)        │
│   - /api/v1/invoke (POST)           │
│   - /api/v1/health (GET)            │
│   - AWS IAM Authorizer              │
└────────┬────────────────────────────┘
         │
         │ Lambda Proxy
         ▼
┌─────────────────────────────────────┐
│   Lambda Function                   │
│   - Parse HTTP request              │
│   - Create WebSocket connection     │
│   - Invoke AgentCore Runtime        │
│   - Stream/buffer response          │
│   - Return HTTP response            │
└────────┬────────────────────────────┘
         │
         │ WebSocket (wss://)
         ▼
┌─────────────────────────────────────┐
│   AgentCore Runtime                 │
│   - SkyMarshal Orchestrator         │
│   - 7 Specialized Agents            │
│   - DynamoDB Integration            │
└─────────────────────────────────────┘
```

### Component Interaction Flow

1. **Client Request**: External application sends HTTP POST to API Gateway with disruption prompt
2. **Authentication**: API Gateway validates AWS credentials using IAM Authorizer
3. **Lambda Invocation**: API Gateway forwards request to Lambda proxy function
4. **WebSocket Setup**: Lambda creates WebSocket connection to AgentCore Runtime using SDK
5. **Agent Execution**: AgentCore Runtime processes request through SkyMarshal orchestrator
6. **Response Handling**: Lambda collects streaming responses and formats for HTTP
7. **Client Response**: API Gateway returns formatted response to client

## Components and Interfaces

### 1. API Gateway Configuration

**Resource Structure**:

```
/api/v1/
  ├── /invoke (POST) - Main agent invocation endpoint
  ├── /health (GET) - Health check endpoint
  └── /sessions/{sessionId} (GET) - Session history retrieval
```

**API Gateway Settings**:

- Type: REST API (not HTTP API) for full IAM integration
- Authorization: AWS_IAM authorizer on all endpoints except /health
- CORS: Enabled for specified origins
- Throttling: 100 requests per second per account
- Timeout: 29 seconds (API Gateway maximum)
- Binary media types: application/json

**IAM Authorizer Configuration**:

```python
{
    "Type": "AWS_IAM",
    "AuthorizationType": "AWS_IAM",
    "IdentitySource": "method.request.header.Authorization"
}
```

### 2. Lambda Proxy Function

**Runtime**: Python 3.11
**Memory**: 512 MB
**Timeout**: 5 minutes (300 seconds)
**Concurrency**: Reserved concurrency of 10

**Environment Variables**:

```python
{
    "AGENTCORE_RUNTIME_ARN": "arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/skymarshal",
    "AWS_REGION": "us-east-1",
    "SESSION_TABLE_NAME": "skymarshal-sessions",
    "LOG_LEVEL": "INFO",
    "RESPONSE_MODE": "buffered"  # or "streaming"
}
```

**IAM Role Permissions**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeRuntime",
        "bedrock-agentcore:GetRuntime"
      ],
      "Resource": "arn:aws:bedrock-agentcore:*:*:runtime/skymarshal"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/skymarshal-sessions"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

**Function Interface**:

```python
def lambda_handler(event: dict, context: Any) -> dict:
    """
    Lambda handler for AgentCore Runtime invocation.

    Args:
        event: API Gateway proxy event containing:
            - body: JSON with 'prompt' and optional 'session_id'
            - headers: Authorization and other headers
            - requestContext: Request metadata
        context: Lambda context object

    Returns:
        API Gateway proxy response with:
            - statusCode: HTTP status code
            - headers: Response headers including CORS
            - body: JSON response or error message
    """
```

### 3. WebSocket Client Module

**Purpose**: Manages WebSocket connections to AgentCore Runtime

**Class Definition**:

```python
class AgentCoreWebSocketClient:
    """
    WebSocket client for AgentCore Runtime invocation.
    Uses bedrock_agentcore.runtime.AgentCoreRuntimeClient for connection setup.
    """

    def __init__(self, runtime_arn: str, region: str):
        """
        Initialize WebSocket client.

        Args:
            runtime_arn: Full ARN of AgentCore Runtime
            region: AWS region
        """
        self.runtime_arn = runtime_arn
        self.region = region
        self.client = AgentCoreRuntimeClient(region=region)

    async def invoke(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        timeout: int = 300
    ) -> AsyncGenerator[dict, None]:
        """
        Invoke AgentCore Runtime and stream responses.

        Args:
            prompt: Disruption description
            session_id: Optional session ID for context
            timeout: Maximum execution time in seconds

        Yields:
            Response chunks as dictionaries

        Raises:
            TimeoutError: If invocation exceeds timeout
            ConnectionError: If WebSocket connection fails
        """

    async def invoke_buffered(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        timeout: int = 300
    ) -> dict:
        """
        Invoke AgentCore Runtime and return complete response.

        Args:
            prompt: Disruption description
            session_id: Optional session ID for context
            timeout: Maximum execution time in seconds

        Returns:
            Complete response as dictionary

        Raises:
            TimeoutError: If invocation exceeds timeout
            ConnectionError: If WebSocket connection fails
        """
```

**WebSocket Message Protocol**:

```python
# Request message format
{
    "action": "invoke",
    "payload": {
        "prompt": "Flight AA123 delayed 3 hours due to weather",
        "session_id": "uuid-v4-string"
    }
}

# Response message format (streaming)
{
    "type": "chunk",
    "data": {
        "agent": "crew_compliance",
        "status": "analyzing",
        "partial_result": {...}
    }
}

# Final response message
{
    "type": "complete",
    "data": {
        "status": "success",
        "assessment": {...},
        "recommendations": [...],
        "execution_time_ms": 4523
    }
}

# Error message format
{
    "type": "error",
    "error": {
        "code": "TIMEOUT",
        "message": "Agent execution exceeded timeout",
        "details": {...}
    }
}
```

### 4. Session Manager

**Purpose**: Manages conversation sessions and history in DynamoDB

**DynamoDB Table Schema**:

```python
Table: skymarshal-sessions
Partition Key: session_id (String)
Sort Key: timestamp (Number)

Attributes:
- session_id: UUID v4 string
- timestamp: Unix timestamp in milliseconds
- request_id: UUID v4 string
- prompt: String (disruption description)
- response: Map (agent assessment)
- status: String (success|error|timeout)
- execution_time_ms: Number
- error_message: String (optional)
- ttl: Number (expiration timestamp)

GSI: user-sessions-index
- Partition Key: user_id (String)
- Sort Key: timestamp (Number)
```

**Class Definition**:

```python
class SessionManager:
    """
    Manages agent invocation sessions and history.
    """

    def __init__(self, table_name: str, region: str):
        """
        Initialize session manager.

        Args:
            table_name: DynamoDB table name
            region: AWS region
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.table = self.dynamodb.Table(table_name)

    def create_session(self) -> str:
        """
        Create a new session.

        Returns:
            Session ID (UUID v4)
        """

    def save_interaction(
        self,
        session_id: str,
        request_id: str,
        prompt: str,
        response: dict,
        execution_time_ms: int,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> None:
        """
        Save an interaction to session history.

        Args:
            session_id: Session identifier
            request_id: Request identifier
            prompt: User prompt
            response: Agent response
            execution_time_ms: Execution duration
            status: Interaction status
            error_message: Optional error message
        """

    def get_session_history(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[dict]:
        """
        Retrieve session history.

        Args:
            session_id: Session identifier
            limit: Maximum number of interactions to return

        Returns:
            List of interactions ordered by timestamp
        """

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions (TTL > 30 days).

        Returns:
            Number of sessions deleted
        """
```

### 5. Request Validator

**Purpose**: Validates and sanitizes incoming requests

**Class Definition**:

```python
class RequestValidator:
    """
    Validates API requests before processing.
    """

    MAX_PROMPT_LENGTH = 10000
    MIN_PROMPT_LENGTH = 10

    @staticmethod
    def validate_invoke_request(body: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate invocation request.

        Args:
            body: Request body dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """

    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """
        Sanitize prompt to prevent injection attacks.

        Args:
            prompt: Raw prompt string

        Returns:
            Sanitized prompt
        """

    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """
        Validate session ID format (UUID v4).

        Args:
            session_id: Session identifier

        Returns:
            True if valid UUID v4
        """
```

### 6. Response Formatter

**Purpose**: Formats agent responses for HTTP delivery

**Class Definition**:

```python
class ResponseFormatter:
    """
    Formats agent responses for API Gateway.
    """

    @staticmethod
    def format_success_response(
        data: dict,
        request_id: str,
        execution_time_ms: int
    ) -> dict:
        """
        Format successful response.

        Args:
            data: Agent assessment data
            request_id: Request identifier
            execution_time_ms: Execution duration

        Returns:
            Formatted API Gateway response
        """

    @staticmethod
    def format_error_response(
        error_code: str,
        error_message: str,
        request_id: str,
        status_code: int = 500
    ) -> dict:
        """
        Format error response.

        Args:
            error_code: Error code identifier
            error_message: Human-readable error message
            request_id: Request identifier
            status_code: HTTP status code

        Returns:
            Formatted API Gateway error response
        """

    @staticmethod
    def format_streaming_chunk(chunk: dict) -> str:
        """
        Format streaming response chunk as SSE.

        Args:
            chunk: Response chunk dictionary

        Returns:
            SSE-formatted string
        """
```

## Data Models

### Request Models

**InvokeRequest**:

```python
from pydantic import BaseModel, Field, validator

class InvokeRequest(BaseModel):
    """Request model for agent invocation."""

    prompt: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Disruption description in natural language"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for multi-turn conversations"
    )
    streaming: bool = Field(
        False,
        description="Enable streaming responses (SSE)"
    )

    @validator('session_id')
    def validate_session_id(cls, v):
        if v is not None:
            try:
                uuid.UUID(v, version=4)
            except ValueError:
                raise ValueError('session_id must be a valid UUID v4')
        return v

    @validator('prompt')
    def sanitize_prompt(cls, v):
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>{}]', '', v)
        return sanitized.strip()
```

### Response Models

**InvokeResponse**:

```python
class AgentAssessment(BaseModel):
    """Individual agent assessment."""

    agent_name: str
    status: str  # "approved" | "rejected" | "conditional"
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    constraints: List[str] = []
    recommendations: List[str] = []

class InvokeResponse(BaseModel):
    """Response model for successful invocation."""

    status: str = "success"
    request_id: str
    session_id: Optional[str]
    execution_time_ms: int

    assessment: dict = Field(
        ...,
        description="Complete disruption assessment"
    )

    safety_phase: dict = Field(
        ...,
        description="Safety agents results (crew, maintenance, regulatory)"
    )

    business_phase: dict = Field(
        ...,
        description="Business agents results (network, guest, cargo, finance)"
    )

    final_decision: str = Field(
        ...,
        description="Overall decision: approved | rejected | conditional"
    )

    recommendations: List[str] = Field(
        default_factory=list,
        description="Prioritized recovery recommendations"
    )

    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (timestamps, versions, etc.)"
    )
```

**ErrorResponse**:

```python
class ErrorResponse(BaseModel):
    """Response model for errors."""

    status: str = "error"
    request_id: str
    error_code: str
    error_message: str
    details: Optional[dict] = None
    timestamp: str
```

### Session Models

**SessionInteraction**:

```python
class SessionInteraction(BaseModel):
    """Single interaction within a session."""

    session_id: str
    request_id: str
    timestamp: int  # Unix timestamp in milliseconds
    prompt: str
    response: dict
    status: str
    execution_time_ms: int
    error_message: Optional[str] = None
```

**SessionHistory**:

```python
class SessionHistory(BaseModel):
    """Complete session history."""

    session_id: str
    created_at: int
    last_interaction_at: int
    interaction_count: int
    interactions: List[SessionInteraction]
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Request Validation Completeness

_For any_ HTTP request to the /invoke endpoint, the system should validate all required fields (prompt) and reject requests with missing or invalid data before invoking AgentCore Runtime.
**Validates: Requirements 1.3, 7.1, 7.2, 7.3, 7.4**

### Property 2: Authentication Enforcement

_For any_ request without valid AWS credentials, the API Gateway should return 401 Unauthorized before reaching the Lambda function.
**Validates: Requirements 5.1, 5.2, 5.3**

### Property 3: Session ID Consistency

_For any_ request with a session ID, all interactions within that session should maintain the same session identifier throughout the conversation.
**Validates: Requirements 4.2**

### Property 4: Response Format Consistency

_For any_ successful AgentCore Runtime invocation, the response should include status, request_id, execution_time_ms, and assessment fields in the specified format.
**Validates: Requirements 8.1, 8.2, 8.4**

### Property 5: Error Response Completeness

_For any_ error condition (timeout, validation failure, runtime error), the system should return a JSON response with error_code, error_message, and request_id fields.
**Validates: Requirements 6.1, 6.2, 6.4, 6.5**

### Property 6: Timeout Enforcement

_For any_ AgentCore Runtime invocation exceeding 5 minutes, the Lambda function should terminate the WebSocket connection and return a 504 Gateway Timeout response.
**Validates: Requirements 2.5, 6.3**

### Property 7: Session Persistence

_For any_ completed invocation, the interaction should be saved to DynamoDB with all required fields (session_id, timestamp, prompt, response, status).
**Validates: Requirements 4.5**

### Property 8: Prompt Sanitization

_For any_ prompt containing special characters (<, >, {, }), the validator should remove or escape them before processing.
**Validates: Requirements 7.5**

### Property 9: WebSocket Connection Cleanup

_For any_ Lambda invocation (successful or failed), the WebSocket connection to AgentCore Runtime should be properly closed before the function returns.
**Validates: Requirements 2.3, 2.4**

### Property 10: Rate Limit Enforcement

_For any_ client exceeding 100 requests per minute, the API Gateway should return 429 Too Many Requests with a Retry-After header.
**Validates: Requirements 13.1, 13.2**

### Property 11: Health Check Independence

_For any_ health check request to /health, the endpoint should return status without requiring authentication or invoking AgentCore Runtime.
**Validates: Requirements 14.1, 14.2, 14.4**

### Property 12: Streaming Chunk Format

_For any_ streaming response chunk, the formatter should convert it to valid Server-Sent Events format with "data: " prefix and double newline terminator.
**Validates: Requirements 3.2, 3.3**

### Property 13: Session Expiration

_For any_ session inactive for more than 30 minutes, the system should mark it as expired and exclude it from active session queries.
**Validates: Requirements 4.3**

### Property 14: Request ID Uniqueness

_For any_ two concurrent requests, the system should generate unique request IDs (UUID v4) to enable independent tracking.
**Validates: Requirements 6.5, 10.1**

### Property 15: CORS Header Inclusion

_For any_ successful response, the API Gateway should include Access-Control-Allow-Origin and other CORS headers for cross-origin requests.
**Validates: Requirements 1.5**

## Error Handling

### Error Categories

**1. Client Errors (4xx)**:

- 400 Bad Request: Invalid JSON, missing required fields, prompt too long
- 401 Unauthorized: Missing or invalid AWS credentials
- 403 Forbidden: Valid credentials but insufficient permissions
- 404 Not Found: Invalid endpoint or session not found
- 429 Too Many Requests: Rate limit exceeded

**2. Server Errors (5xx)**:

- 500 Internal Server Error: Unexpected Lambda error
- 502 Bad Gateway: AgentCore Runtime connection failure
- 503 Service Unavailable: AgentCore Runtime unavailable or overloaded
- 504 Gateway Timeout: Request exceeded timeout limit

### Error Handling Strategy

**Lambda Function Error Handling**:

```python
try:
    # Validate request
    is_valid, error_msg = RequestValidator.validate_invoke_request(body)
    if not is_valid:
        return ResponseFormatter.format_error_response(
            error_code="INVALID_REQUEST",
            error_message=error_msg,
            request_id=request_id,
            status_code=400
        )

    # Invoke AgentCore Runtime
    response = await ws_client.invoke_buffered(
        prompt=prompt,
        session_id=session_id,
        timeout=300
    )

    # Save to session history
    session_manager.save_interaction(...)

    # Return success response
    return ResponseFormatter.format_success_response(...)

except TimeoutError:
    return ResponseFormatter.format_error_response(
        error_code="TIMEOUT",
        error_message="Agent execution exceeded 5 minute timeout",
        request_id=request_id,
        status_code=504
    )

except ConnectionError as e:
    return ResponseFormatter.format_error_response(
        error_code="CONNECTION_FAILED",
        error_message=f"Failed to connect to AgentCore Runtime: {str(e)}",
        request_id=request_id,
        status_code=502
    )

except Exception as e:
    logger.exception("Unexpected error during invocation")
    return ResponseFormatter.format_error_response(
        error_code="INTERNAL_ERROR",
        error_message="An unexpected error occurred",
        request_id=request_id,
        status_code=500
    )

finally:
    # Ensure WebSocket cleanup
    if ws_client:
        await ws_client.close()
```

**Retry Strategy**:

- AgentCore Runtime connection failures: Retry up to 2 times with exponential backoff (1s, 2s)
- DynamoDB throttling: Automatic retry with AWS SDK default exponential backoff
- No retries for: Validation errors, authentication failures, timeouts

**Error Logging**:

```python
# CloudWatch Logs structure
{
    "timestamp": "2024-01-15T10:30:45.123Z",
    "level": "ERROR",
    "request_id": "uuid-v4",
    "session_id": "uuid-v4",
    "error_code": "TIMEOUT",
    "error_message": "Agent execution exceeded timeout",
    "stack_trace": "...",
    "context": {
        "prompt_length": 245,
        "execution_time_ms": 300000,
        "retry_count": 0
    }
}
```

## Testing Strategy

### Unit Testing

**Test Coverage Areas**:

1. Request validation logic
2. Prompt sanitization
3. Session ID validation
4. Response formatting
5. Error response generation
6. WebSocket message parsing

**Example Unit Tests**:

```python
def test_validate_invoke_request_missing_prompt():
    """Test that requests without prompt are rejected."""
    body = {"session_id": "valid-uuid"}
    is_valid, error = RequestValidator.validate_invoke_request(body)
    assert not is_valid
    assert "prompt" in error.lower()

def test_sanitize_prompt_removes_special_chars():
    """Test that special characters are removed from prompts."""
    prompt = "Flight <script>alert('xss')</script> delayed"
    sanitized = RequestValidator.sanitize_prompt(prompt)
    assert "<" not in sanitized
    assert ">" not in sanitized
    assert "Flight" in sanitized

def test_format_success_response_includes_required_fields():
    """Test that success responses include all required fields."""
    response = ResponseFormatter.format_success_response(
        data={"assessment": {}},
        request_id="test-id",
        execution_time_ms=1000
    )
    assert response["statusCode"] == 200
    assert "request_id" in json.loads(response["body"])
    assert "execution_time_ms" in json.loads(response["body"])
```

### Property-Based Testing

**Property Test Configuration**:

- Library: Hypothesis (Python)
- Iterations per test: 100 minimum
- Seed: Fixed for reproducibility in CI/CD

**Property Test Examples**:

```python
from hypothesis import given, strategies as st

@given(
    prompt=st.text(min_size=10, max_size=10000),
    session_id=st.one_of(st.none(), st.uuids(version=4).map(str))
)
def test_property_valid_requests_never_return_400(prompt, session_id):
    """
    Property 1: Request Validation Completeness
    For any valid request, the validator should not return 400 errors.

    Feature: agentcore-rest-api, Property 1: Request Validation Completeness
    """
    body = {"prompt": prompt}
    if session_id:
        body["session_id"] = session_id

    is_valid, error = RequestValidator.validate_invoke_request(body)
    assert is_valid or len(prompt) < 10 or len(prompt) > 10000

@given(
    data=st.dictionaries(
        keys=st.text(),
        values=st.one_of(st.text(), st.integers(), st.floats(), st.booleans())
    ),
    request_id=st.uuids(version=4).map(str),
    execution_time=st.integers(min_value=0, max_value=300000)
)
def test_property_success_responses_always_valid_json(data, request_id, execution_time):
    """
    Property 4: Response Format Consistency
    For any successful response, the output should be valid JSON with required fields.

    Feature: agentcore-rest-api, Property 4: Response Format Consistency
    """
    response = ResponseFormatter.format_success_response(
        data=data,
        request_id=request_id,
        execution_time_ms=execution_time
    )

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "status" in body
    assert "request_id" in body
    assert "execution_time_ms" in body
    assert body["request_id"] == request_id

@given(
    prompt=st.text(min_size=1, max_size=20000)
)
def test_property_prompt_sanitization_removes_dangerous_chars(prompt):
    """
    Property 8: Prompt Sanitization
    For any prompt, sanitization should remove special characters.

    Feature: agentcore-rest-api, Property 8: Prompt Sanitization
    """
    sanitized = RequestValidator.sanitize_prompt(prompt)
    assert "<" not in sanitized
    assert ">" not in sanitized
    assert "{" not in sanitized
    assert "}" not in sanitized
```

### Integration Testing

**Test Scenarios**:

1. End-to-end invocation with mock AgentCore Runtime
2. Session creation and history retrieval
3. Timeout handling with slow mock responses
4. Rate limiting with concurrent requests
5. Authentication with valid/invalid credentials
6. WebSocket connection failure recovery

**Integration Test Example**:

```python
@pytest.mark.integration
async def test_end_to_end_invocation():
    """Test complete invocation flow from HTTP request to response."""
    # Setup
    event = {
        "body": json.dumps({
            "prompt": "Flight AA123 delayed 3 hours due to weather"
        }),
        "headers": {
            "Authorization": "AWS4-HMAC-SHA256 ..."
        },
        "requestContext": {
            "requestId": "test-request-id"
        }
    }

    # Execute
    response = await lambda_handler(event, mock_context)

    # Verify
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["status"] == "success"
    assert "assessment" in body
    assert "execution_time_ms" in body
```

### Load Testing

**Load Test Configuration**:

- Tool: Locust or Artillery
- Target: 100 concurrent users
- Duration: 10 minutes
- Ramp-up: 10 users per second
- Success criteria: 95th percentile latency < 10 seconds

**Load Test Scenario**:

```python
from locust import HttpUser, task, between

class AgentCoreAPIUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def invoke_agent(self):
        self.client.post(
            "/api/v1/invoke",
            json={
                "prompt": "Flight delayed 2 hours due to maintenance"
            },
            headers={
                "Authorization": f"Bearer {self.auth_token}"
            }
        )
```

### Testing Best Practices

1. **Unit tests**: Focus on individual functions and edge cases
2. **Property tests**: Verify universal properties across random inputs (100+ iterations)
3. **Integration tests**: Test component interactions with mocks
4. **Load tests**: Validate performance under concurrent load
5. **Security tests**: Test authentication, authorization, and injection prevention
6. **Chaos tests**: Simulate AgentCore Runtime failures and network issues

**Test Execution Order**:

1. Unit tests (fast, run on every commit)
2. Property tests (medium, run on every commit)
3. Integration tests (slower, run on PR)
4. Load tests (slow, run before deployment)
5. Security tests (run weekly and before major releases)
