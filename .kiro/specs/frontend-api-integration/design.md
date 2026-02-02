# Design Document: Frontend API Integration

## Overview

This design specifies the integration between the SkyMarshal React frontend and the deployed AgentCore REST API. The integration replaces mock data orchestration with real-time API communication, enabling users to interact with the live multi-agent disruption analysis system.

The design follows a layered architecture with clear separation between API communication, state management, and UI presentation. It leverages AWS Signature V4 authentication for secure API access and maintains the existing two-phase orchestration UI flow (safety → business).

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   App.tsx    │  │ Orchestration│  │   Agent      │     │
│  │              │─▶│    View      │─▶│  Components  │     │
│  └──────────────┘  └──────┬───────┘  └──────────────┘     │
│                            │                                 │
│                    ┌───────▼────────┐                       │
│                    │  API Service   │                       │
│                    │  - Auth        │                       │
│                    │  - HTTP Client │                       │
│                    └───────┬────────┘                       │
└────────────────────────────┼──────────────────────────────┘
                             │ HTTPS + AWS Sig V4
                    ┌────────▼────────┐
                    │  API Gateway    │
                    │  (AWS)          │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Lambda         │
                    │  (Invoke)       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  AgentCore      │
                    │  Runtime        │
                    └─────────────────┘
```

### Component Layers

1. **Presentation Layer**: React components (App.tsx, OrchestrationView.tsx, AgentMessage.tsx)
2. **Service Layer**: API client with authentication and request/response handling
3. **State Management Layer**: React hooks managing session state, loading states, and error states
4. **Infrastructure Layer**: AWS API Gateway, Lambda, AgentCore Runtime

## Components and Interfaces

### 1. API Service Module

**Location**: `frontend/services/api.ts`

**Purpose**: Centralized API communication with authentication and error handling

**Interface**:

```typescript
interface APIConfig {
  endpoint: string;
  region: string;
  credentials?: AWSCredentials;
}

interface InvokeRequest {
  prompt: string;
  session_id?: string;
}

interface InvokeResponse {
  status: "success" | "error";
  request_id: string;
  session_id: string;
  execution_time_ms: number;
  timestamp: string;
  assessment: Assessment;
  error?: string;
}

interface Assessment {
  safety_phase: PhaseResult;
  business_phase: PhaseResult;
  final_decision: string;
  recommendations: Recommendation[];
}

interface PhaseResult {
  agents: Record<string, AgentResult>;
  phase_status: string;
  constraints: string[];
}

interface AgentResult {
  agent_name: string;
  status: string;
  safety_analysis?: string;
  business_impact?: string;
  confidence: number;
  reasoning: string;
}

interface Recommendation {
  id: string;
  title: string;
  description: string;
  impact: "low" | "medium" | "high";
  cost: string;
  recommended: boolean;
}

class APIService {
  constructor(config: APIConfig);

  async invoke(request: InvokeRequest): Promise<InvokeResponse>;
  async healthCheck(): Promise<{ status: string }>;

  private async signRequest(request: Request): Promise<Request>;
  private handleError(error: any): APIError;
}
```

### 2. AWS Signature V4 Authentication

**Location**: `frontend/services/auth.ts`

**Purpose**: Sign HTTP requests with AWS Signature V4 for API Gateway authentication

**Interface**:

```typescript
interface AWSCredentials {
  accessKeyId: string;
  secretAccessKey: string;
  sessionToken?: string;
}

interface SignatureParams {
  method: string;
  url: string;
  headers: Record<string, string>;
  body: string;
  credentials: AWSCredentials;
  region: string;
  service: string;
}

class AWSSignatureV4 {
  static sign(params: SignatureParams): Record<string, string>;

  private static getSignatureKey(
    key: string,
    dateStamp: string,
    region: string,
    service: string,
  ): Uint8Array;

  private static createCanonicalRequest(
    method: string,
    uri: string,
    queryString: string,
    headers: Record<string, string>,
    payloadHash: string,
  ): string;

  private static createStringToSign(
    timestamp: string,
    credentialScope: string,
    canonicalRequestHash: string,
  ): string;
}
```

### 3. Environment Configuration

**Location**: `frontend/config/env.ts`

**Purpose**: Load and validate environment variables

**Interface**:

```typescript
interface EnvironmentConfig {
  apiEndpoint: string;
  awsRegion: string;
  isDevelopment: boolean;
}

function loadConfig(): EnvironmentConfig;
function validateConfig(config: Partial<EnvironmentConfig>): void;
```

**Environment Variables**:

- `VITE_API_ENDPOINT`: API Gateway endpoint URL
- `VITE_AWS_REGION`: AWS region (default: us-east-1)
- `VITE_ENABLE_MOCK`: Flag to enable mock mode for testing

### 4. Response Mapper

**Location**: `frontend/services/responseMapper.ts`

**Purpose**: Transform API responses into UI data structures

**Interface**:

```typescript
interface MessageData {
  id: string;
  agent: AgentType;
  safetyAnalysis?: string;
  businessImpact?: string;
  crossImpactAnalysis?: string;
  isCrossImpactRound?: boolean;
  isDecision?: boolean;
  solutionTitle?: string;
}

interface Solution {
  id: string;
  title: string;
  description: string;
  impact: "low" | "medium" | "high";
  cost: string;
  recommended: boolean;
}

class ResponseMapper {
  static mapToMessages(assessment: Assessment): MessageData[];
  static mapToSolutions(recommendations: Recommendation[]): Solution[];

  private static mapAgentResult(
    agentName: string,
    result: AgentResult,
  ): MessageData;
}
```

### 5. Session Manager

**Location**: `frontend/hooks/useSession.ts`

**Purpose**: Manage session state and persistence

**Interface**:

```typescript
interface SessionState {
  sessionId: string | null;
  isActive: boolean;
}

interface UseSessionReturn {
  sessionId: string | null;
  setSessionId: (id: string) => void;
  clearSession: () => void;
  isActive: boolean;
}

function useSession(): UseSessionReturn;
```

### 6. API Hook

**Location**: `frontend/hooks/useAPI.ts`

**Purpose**: React hook for API interactions with loading and error states

**Interface**:

```typescript
interface UseAPIReturn {
  invoke: (prompt: string) => Promise<InvokeResponse>;
  loading: boolean;
  error: string | null;
  clearError: () => void;
}

function useAPI(): UseAPIReturn;
```

### 7. Updated App Component

**Changes**:

- Initialize API service on mount
- Invoke API when user clicks "Proceed" button on landing page
- Pass API response to OrchestrationView
- Handle authentication errors at app level
- Add global error boundary
- Manage loading state during API call

**Updated Flow**:

```typescript
interface AppState {
  currentView: "landing" | "orchestration";
  userPrompt: string;
  apiResponse: InvokeResponse | null;
  loading: boolean;
  error: string | null;
}

// Flow:
// 1. User enters prompt on landing page
// 2. User clicks "Proceed"
// 3. App.tsx calls API with prompt
// 4. While loading, show loading indicator on landing page
// 5. On success, transition to OrchestrationView with response
// 6. On error, show error on landing page with retry
```

### 8. Updated OrchestrationView Component

**Changes**:

- Remove mock data constants (comment out)
- Remove mock orchestration sequence
- Receive API response as prop instead of calling API
- Parse response and display agent messages
- Add error handling UI for display issues
- Preserve existing UI structure and animations

**New Props**:

```typescript
interface OrchestrationViewProps {
  prompt: string;
  apiResponse: InvokeResponse;
  onError?: (error: string) => void;
  onComplete?: () => void;
}
```

- Handle authentication errors at app level
- Add global error boundary

## Data Models

### API Request/Response Flow

```typescript
// Request Flow (initiated from App.tsx)
User Input (string) on Landing Page
  → User clicks "Proceed"
  → App.tsx: InvokeRequest { prompt, session_id? }
  → API Service: AWS Signed HTTP Request
  → API Gateway
  → Lambda
  → AgentCore Runtime

// Response Flow
AgentCore Runtime
  → Lambda
  → API Gateway
  → API Service: InvokeResponse { status, assessment, ... }
  → App.tsx: Store response
  → Transition to OrchestrationView
  → ResponseMapper: MessageData[] + Solution[]
  → React State
  → UI Components
```

### State Management

```typescript
// App-level State
interface AppState {
  currentView: "landing" | "orchestration";
  userPrompt: string;
  apiConfig: APIConfig;
  authError: string | null;
}

// OrchestrationView State
interface OrchestrationState {
  stage:
    | "summoning"
    | "initial_round"
    | "waiting_for_user"
    | "cross_impact"
    | "decision_phase";
  messages: MessageData[];
  activeAgent: AgentType | null;
  thinkingAgent: AgentType | null;
  arbitratorAnalysis: string;
  solutions: Solution[];
  selectedSolutionId: string | null;
  loading: boolean;
  error: string | null;
}

// Session State (persisted)
interface SessionState {
  sessionId: string | null;
  lastActivity: number;
}
```

### Error Types

```typescript
enum APIErrorType {
  NETWORK_ERROR = "NETWORK_ERROR",
  AUTH_ERROR = "AUTH_ERROR",
  TIMEOUT_ERROR = "TIMEOUT_ERROR",
  RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR",
  VALIDATION_ERROR = "VALIDATION_ERROR",
  SERVER_ERROR = "SERVER_ERROR",
  UNKNOWN_ERROR = "UNKNOWN_ERROR",
}

interface APIError {
  type: APIErrorType;
  message: string;
  statusCode?: number;
  retryable: boolean;
  details?: any;
}
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Environment Configuration Loading

_For any_ set of environment variables containing API endpoint and region, loading the configuration should produce a config object with those exact values.

**Validates: Requirements 1.1, 1.3**

### Property 2: HTTPS URL Validation

_For any_ URL string, the validation function should accept it if and only if it starts with "https://" and is a valid URL format.

**Validates: Requirements 1.4**

### Property 3: AWS Signature Presence

_For any_ API request, the signed request should contain an Authorization header with the AWS4-HMAC-SHA256 signature format.

**Validates: Requirements 2.1, 2.3**

### Property 4: Request Structure Completeness

_For any_ prompt string and optional session_id, the API request body should contain the prompt field, and should contain the session_id field if and only if a session_id was provided.

**Validates: Requirements 3.1, 3.2, 3.3**

### Property 5: Loading State Consistency

_For any_ API call lifecycle, the loading state should be true from request start until response or error, and false otherwise.

**Validates: Requirements 3.4**

### Property 6: Error Display Completeness

_For any_ API error, the UI should display an error message and provide a retry mechanism.

**Validates: Requirements 3.5**

### Property 7: Assessment Extraction

_For any_ valid API response containing an assessment object, parsing the response should successfully extract the assessment with all required fields (safety_phase, business_phase, recommendations).

**Validates: Requirements 4.1**

### Property 8: Phase Data Mapping

_For any_ agent result in safety_phase or business_phase, the mapped MessageData should contain the agent's analysis in the corresponding field (safetyAnalysis for safety_phase, businessImpact for business_phase).

**Validates: Requirements 4.2, 4.3, 5.2, 5.3**

### Property 9: Session Persistence Round-Trip

_For any_ successful API response containing a session_id, storing that session_id and then making a subsequent request should include that same session_id in the request body.

**Validates: Requirements 4.4, 6.1, 6.2**

### Property 10: Invalid Response Handling

_For any_ malformed API response (missing required fields, wrong types), the error handler should catch the parsing error and display a user-friendly message.

**Validates: Requirements 4.5**

### Property 11: Agent Message Creation

_For any_ assessment with N agents in the safety_phase and M agents in the business_phase, the message mapper should create exactly N + M AgentMessage data objects.

**Validates: Requirements 5.1**

### Property 12: Stage Transition Correctness

_For any_ orchestration flow, the stage should transition from summoning → initial_round → waiting_for_user → cross_impact → decision_phase, and should only advance when the corresponding API response is received.

**Validates: Requirements 5.4, 8.1, 8.3, 11.5**

### Property 13: Session Cleanup

_For any_ session state, calling clearSession should result in sessionId being null and subsequent requests not including a session_id field.

**Validates: Requirements 6.3**

### Property 14: Unknown Error Fallback

_For any_ API error without a specific error type match, the displayed error message should be the error message from the API response.

**Validates: Requirements 7.5**

### Property 15: Error Recovery State

_For any_ failed API request, the application state should allow the user to retry the request with the same prompt.

**Validates: Requirements 8.4**

### Property 16: Recommendation Parsing

_For any_ list of recommendations in the API response, parsing should produce Solution objects with all required fields (id, title, description, impact, cost, recommended).

**Validates: Requirements 10.1, 10.2**

### Property 17: Solution Selection Storage

_For any_ solution selection, the selectedSolutionId state should be updated to match the selected solution's id.

**Validates: Requirements 10.4**

### Property 18: Recommendation Display Completeness

_For any_ list of N recommendations, the ArbitratorPanel should display exactly N solution cards.

**Validates: Requirements 10.5**

### Property 19: Cross-Impact Button Visibility

_For any_ orchestration state, the "Run Cross-Impact Analysis" button should be visible if and only if the stage is waiting_for_user.

**Validates: Requirements 11.1**

### Property 20: Cross-Impact Request Session Continuity

_For any_ cross-impact analysis trigger, the API request should include the session_id from the initial analysis.

**Validates: Requirements 11.2**

### Property 21: Cross-Impact Message Addition

_For any_ cross-impact API response with N agents, the message stream should grow by N messages.

**Validates: Requirements 11.4**

### Property 22: Response Format Compatibility

_For any_ API response (chunked or complete), the response handler should successfully parse it into the same MessageData structure.

**Validates: Requirements 12.2, 12.4**

### Property 23: Incremental Chunk Processing

_For any_ sequence of response chunks, each chunk should be processed and added to the UI as it arrives, without waiting for the complete response.

**Validates: Requirements 12.3**

## Error Handling

### Error Categories

1. **Network Errors**: Connection failures, DNS resolution failures
   - Display: "Unable to connect to API"
   - Action: Provide retry button
   - Logging: Log full error details to console

2. **Authentication Errors (401)**: Invalid or expired AWS credentials
   - Display: "Authentication failed - please check AWS credentials"
   - Action: Provide instructions for credential configuration
   - Logging: Log credential source (env vars, AWS SDK)

3. **Timeout Errors (504)**: Request exceeds 5-minute timeout
   - Display: "Request timed out - the analysis is taking longer than expected"
   - Action: Provide retry button with note about long-running analysis
   - Logging: Log request duration and endpoint

4. **Rate Limit Errors (429)**: Exceeded API Gateway rate limits
   - Display: "Too many requests - please wait and try again"
   - Action: Disable submit button for 5 seconds
   - Logging: Log rate limit headers

5. **Validation Errors (400)**: Invalid request format
   - Display: "Invalid request - please check your input"
   - Action: Highlight invalid fields if possible
   - Logging: Log validation error details

6. **Server Errors (500, 502, 503)**: Backend service failures
   - Display: "Service temporarily unavailable - please try again"
   - Action: Provide retry button
   - Logging: Log full error response

7. **Unknown Errors**: Unexpected error conditions
   - Display: Error message from API response or generic message
   - Action: Provide retry button
   - Logging: Log full error object

### Error Recovery Strategies

1. **Automatic Retry**: For transient network errors, retry up to 3 times with exponential backoff
2. **Session Recovery**: On session expiry, clear session and allow user to start new conversation
3. **Partial Response Handling**: If streaming fails mid-response, display partial results with warning
4. **Graceful Degradation**: If API is unavailable, show option to enable mock mode (if VITE_ENABLE_MOCK is true)

### Error Logging

All errors should be logged with:

- Timestamp
- Error type
- Error message
- Request details (endpoint, method, body)
- Response details (status code, headers, body)
- User action context (which button was clicked, current stage)

## Testing Strategy

### Unit Testing

Unit tests will verify specific examples and edge cases:

1. **Configuration Loading**:
   - Test with valid environment variables
   - Test with missing API endpoint
   - Test with invalid URL format
   - Test with missing region (should use default)

2. **AWS Signature Generation**:
   - Test signature format matches AWS specification
   - Test with different HTTP methods
   - Test with query parameters
   - Test with empty body

3. **Response Parsing**:
   - Test with complete valid response
   - Test with missing optional fields
   - Test with invalid JSON
   - Test with unexpected field types

4. **Error Handling**:
   - Test each HTTP error code (401, 429, 504, 500, etc.)
   - Test network timeout
   - Test malformed response
   - Test missing credentials

5. **State Transitions**:
   - Test stage progression through normal flow
   - Test stage on error
   - Test stage on retry

6. **Session Management**:
   - Test session creation on first call
   - Test session reuse on second call
   - Test session clear on new conversation
   - Test session expiry handling

### Property-Based Testing

Property tests will verify universal properties across all inputs using a property-based testing library (fast-check for TypeScript):

**Configuration**: Each property test should run minimum 100 iterations.

**Test Tags**: Each test must reference its design property:

```typescript
// Feature: frontend-api-integration, Property 1: Environment Configuration Loading
```

**Property Test Examples**:

1. **Property 1: Environment Configuration Loading**
   - Generate random valid API endpoints and regions
   - Verify config object contains exact values

2. **Property 2: HTTPS URL Validation**
   - Generate random URLs (http, https, ftp, invalid)
   - Verify only https URLs pass validation

3. **Property 4: Request Structure Completeness**
   - Generate random prompts and optional session IDs
   - Verify request body structure matches expectations

4. **Property 8: Phase Data Mapping**
   - Generate random agent results
   - Verify mapping preserves all data correctly

5. **Property 11: Agent Message Creation**
   - Generate random assessments with varying agent counts
   - Verify message count equals total agent count

6. **Property 22: Response Format Compatibility**
   - Generate both chunked and complete responses
   - Verify both parse to same structure

### Integration Testing

Integration tests will verify end-to-end flows:

1. **Complete Orchestration Flow**:
   - Submit prompt → Receive initial analysis → Trigger cross-impact → Receive recommendations
   - Verify all stages transition correctly
   - Verify all messages display correctly

2. **Multi-Turn Conversation**:
   - Submit first prompt → Submit second prompt with session
   - Verify session continuity
   - Verify context preservation

3. **Error Recovery**:
   - Trigger error → Retry → Success
   - Verify state resets correctly
   - Verify retry uses same prompt

4. **Authentication Flow**:
   - Test with valid credentials
   - Test with invalid credentials
   - Test with expired credentials

### Manual Testing Checklist

- [ ] Submit disruption scenario and verify agent responses appear
- [ ] Verify safety agents appear before business agents
- [ ] Trigger cross-impact analysis and verify additional responses
- [ ] Verify recommendations display in ArbitratorPanel
- [ ] Test with missing AWS credentials
- [ ] Test with invalid API endpoint
- [ ] Test network disconnection during request
- [ ] Test very long prompts (>1000 characters)
- [ ] Test rapid successive submissions
- [ ] Verify auto-scroll behavior
- [ ] Verify loading animations
- [ ] Verify error messages are user-friendly
- [ ] Test on different browsers (Chrome, Firefox, Safari)
- [ ] Test on mobile viewport
- [ ] Verify session persists across page refresh (if implemented)

### Performance Testing

- API call latency should be displayed to user
- UI should remain responsive during long-running API calls
- Memory usage should not grow unbounded with many messages
- Signature generation should complete in <100ms

### Security Testing

- Verify AWS credentials are never logged or exposed in UI
- Verify API endpoint is validated before use
- Verify request signing prevents tampering
- Verify HTTPS is enforced
- Verify no sensitive data in browser console (production mode)
