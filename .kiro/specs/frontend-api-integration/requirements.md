# Requirements Document: Frontend API Integration

## Introduction

This specification defines the integration between the SkyMarshal React frontend and the deployed AgentCore REST API. The integration will replace the current mock data orchestration with real-time API calls to the backend, enabling users to interact with the live multi-agent system for airline disruption analysis.

## Glossary

- **Frontend**: The React 19 + TypeScript web application that provides the user interface
- **API**: The AWS API Gateway REST endpoint backed by Lambda and AgentCore Runtime
- **AgentCore_Runtime**: The AWS Bedrock AgentCore serverless platform hosting the SkyMarshal agent system
- **Session**: A conversation context identified by a UUID that enables multi-turn interactions
- **AWS_Signature_V4**: The authentication mechanism required by AWS API Gateway for IAM-authenticated endpoints
- **Orchestration_View**: The React component that displays agent responses and manages the multi-phase execution flow
- **Agent_Response**: The structured data returned by each agent containing safety analysis and business impact
- **Phase**: A stage of execution (safety phase or business phase) in the two-phase agent orchestration model

## Requirements

### Requirement 1: API Client Configuration

**User Story:** As a developer, I want to configure the API endpoint through environment variables, so that I can easily switch between development and production environments.

#### Acceptance Criteria

1. WHEN the application starts, THE Frontend SHALL load the API endpoint URL from environment variables
2. WHEN the API endpoint is not configured, THE Frontend SHALL display a clear error message to the user
3. THE Frontend SHALL support configuration of AWS region through environment variables
4. THE Frontend SHALL validate that the API endpoint URL is a valid HTTPS URL

### Requirement 2: AWS Authentication

**User Story:** As a user, I want the frontend to authenticate with AWS automatically, so that I can access the API without manual credential management.

#### Acceptance Criteria

1. WHEN making API requests, THE Frontend SHALL sign requests using AWS Signature V4
2. WHEN AWS credentials are not available, THE Frontend SHALL display an authentication error with instructions
3. THE Frontend SHALL use the execute-api service name for signature generation
4. WHEN credentials expire, THE Frontend SHALL handle the 401 error and prompt for re-authentication

### Requirement 3: Prompt Submission

**User Story:** As a user, I want to submit disruption scenarios through the UI, so that I can receive analysis from the agent system.

#### Acceptance Criteria

1. WHEN a user submits a prompt from the landing page, THE Frontend SHALL send a POST request to the /invoke endpoint
2. WHEN sending the request, THE Frontend SHALL include the prompt text in the request body
3. WHEN a session exists, THE Frontend SHALL include the session_id in the request body
4. WHEN the request is in progress, THE Frontend SHALL display a loading indicator
5. WHEN the request fails, THE Frontend SHALL display an error message with retry option

### Requirement 4: Response Parsing

**User Story:** As a developer, I want to parse API responses into the existing UI data structures, so that agent responses display correctly in the orchestration view.

#### Acceptance Criteria

1. WHEN the API returns a response, THE Frontend SHALL extract the assessment object
2. WHEN parsing agent responses, THE Frontend SHALL map safety_phase data to agent safety analysis fields
3. WHEN parsing agent responses, THE Frontend SHALL map business_phase data to agent business impact fields
4. WHEN the response contains a session_id, THE Frontend SHALL store it for subsequent requests
5. WHEN the response structure is invalid, THE Frontend SHALL log the error and display a user-friendly message

### Requirement 5: Agent Message Display

**User Story:** As a user, I want to see agent responses appear in real-time, so that I can follow the analysis as it progresses.

#### Acceptance Criteria

1. WHEN agent responses are received, THE Frontend SHALL create AgentMessage components for each agent
2. WHEN displaying messages, THE Frontend SHALL show safety analysis in the safety section
3. WHEN displaying messages, THE Frontend SHALL show business impact in the business section
4. WHEN all agents have responded, THE Frontend SHALL update the stage to waiting_for_user
5. WHEN messages are added, THE Frontend SHALL auto-scroll to show the latest message

### Requirement 6: Session Management

**User Story:** As a user, I want my conversation context to persist across multiple prompts, so that I can have multi-turn interactions with the system.

#### Acceptance Criteria

1. WHEN the first API call succeeds, THE Frontend SHALL store the returned session_id
2. WHEN making subsequent API calls, THE Frontend SHALL include the stored session_id
3. WHEN the user starts a new conversation, THE Frontend SHALL clear the stored session_id
4. WHEN a session expires (API returns error), THE Frontend SHALL clear the session_id and notify the user

### Requirement 7: Error Handling

**User Story:** As a user, I want clear error messages when something goes wrong, so that I understand what happened and how to proceed.

#### Acceptance Criteria

1. WHEN a network error occurs, THE Frontend SHALL display "Unable to connect to API" with retry option
2. WHEN authentication fails (401), THE Frontend SHALL display "Authentication failed - please check AWS credentials"
3. WHEN the request times out (504), THE Frontend SHALL display "Request timed out - the analysis is taking longer than expected"
4. WHEN rate limiting occurs (429), THE Frontend SHALL display "Too many requests - please wait and try again"
5. WHEN an unknown error occurs, THE Frontend SHALL display the error message from the API response

### Requirement 8: Loading States

**User Story:** As a user, I want to see visual feedback during API calls, so that I know the system is processing my request.

#### Acceptance Criteria

1. WHEN an API request starts, THE Frontend SHALL transition to the summoning stage
2. WHILE the API request is in progress, THE Frontend SHALL display the "Establishing Neural Link" animation
3. WHEN the API request completes, THE Frontend SHALL transition to the initial_round stage
4. WHEN the API request fails, THE Frontend SHALL return to a state allowing retry

### Requirement 9: Mock Data Management

**User Story:** As a developer, I want to preserve mock data as commented code, so that I can easily switch back for testing or development purposes.

#### Acceptance Criteria

1. THE Frontend SHALL comment out the MOCK_INITIAL_RESPONSES constant in OrchestrationView
2. THE Frontend SHALL comment out the MOCK_CROSS_IMPACT_RESPONSES constant in OrchestrationView
3. THE Frontend SHALL comment out the mock orchestration sequence in the useEffect hook
4. THE Frontend SHALL comment out the ARBITRATOR_SOLUTIONS mock data
5. THE Frontend SHALL add comments explaining how to re-enable mock mode for testing

### Requirement 10: Recommendations Display

**User Story:** As a user, I want to see the system's recommended solutions, so that I can make informed decisions about disruption recovery.

#### Acceptance Criteria

1. WHEN the API returns recommendations, THE Frontend SHALL parse them into Solution objects
2. WHEN displaying recommendations, THE Frontend SHALL show the title, description, impact, and cost
3. WHEN a recommendation is marked as recommended, THE Frontend SHALL highlight it visually
4. WHEN the user selects a solution, THE Frontend SHALL record the selection locally
5. THE Frontend SHALL display all recommendations in the ArbitratorPanel component

### Requirement 11: Cross-Impact Analysis

**User Story:** As a user, I want to trigger cross-impact analysis, so that I can see how different factors interact in the disruption scenario.

#### Acceptance Criteria

1. WHEN the initial analysis completes, THE Frontend SHALL display the "Run Cross-Impact Analysis" button
2. WHEN the user clicks the button, THE Frontend SHALL send a follow-up API request with the session_id
3. WHEN the cross-impact request is in progress, THE Frontend SHALL show thinking indicators for agents
4. WHEN cross-impact responses arrive, THE Frontend SHALL display them in the message stream
5. WHEN cross-impact analysis completes, THE Frontend SHALL transition to the decision_phase stage

### Requirement 12: Response Streaming Support

**User Story:** As a developer, I want to support streaming responses in the future, so that users can see agent responses as they are generated.

#### Acceptance Criteria

1. THE Frontend SHALL structure the API client to allow future streaming support
2. THE Frontend SHALL handle both complete responses and chunked responses
3. WHEN the API returns chunks, THE Frontend SHALL process them incrementally
4. THE Frontend SHALL maintain backward compatibility with non-streaming responses
