# Implementation Plan: AgentCore REST API

## Overview

This implementation plan creates a REST API layer for the SkyMarshal AgentCore Runtime system using AWS API Gateway, Lambda, and the AgentCore SDK. The implementation follows a serverless architecture with Python 3.11, focusing on security, reliability, and maintainability.

## Tasks

- [ ] 1. Set up project structure and dependencies
  - Create `api/` directory under `skymarshal_agents_new/skymarshal/`
  - Initialize Python package structure with `__init__.py` files
  - Add required dependencies to `pyproject.toml`: boto3, websockets, pydantic
  - Create `.env.example` with required environment variables
  - _Requirements: 12.2, 12.3_

- [x] 2. Implement request validation module
  - [x] 2.1 Create `api/validation.py` with RequestValidator class
    - Implement `validate_invoke_request()` method
    - Implement `sanitize_prompt()` method to remove special characters
    - Implement `validate_session_id()` method for UUID v4 validation
    - Add constants for MAX_PROMPT_LENGTH (10000) and MIN_PROMPT_LENGTH (10)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  - [ ]\* 2.2 Write property test for request validation
    - **Property 1: Request Validation Completeness**
    - **Validates: Requirements 1.3, 7.1, 7.2, 7.3, 7.4**
    - Generate random valid requests and verify they pass validation
    - Generate random invalid requests and verify they are rejected
  - [ ]\* 2.3 Write property test for prompt sanitization
    - **Property 8: Prompt Sanitization**
    - **Validates: Requirements 7.5**
    - Generate random prompts with special characters
    - Verify sanitized output never contains <, >, {, }

- [x] 3. Implement data models with Pydantic
  - [x] 3.1 Create `api/models.py` with request/response models
    - Implement InvokeRequest model with validators
    - Implement InvokeResponse model with nested structures
    - Implement ErrorResponse model
    - Implement SessionInteraction and SessionHistory models
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [ ]\* 3.2 Write unit tests for model validation
    - Test InvokeRequest validation with valid/invalid data
    - Test session_id UUID v4 validation
    - Test prompt length constraints
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 4. Implement WebSocket client for AgentCore Runtime
  - [x] 4.1 Create `api/websocket_client.py` with AgentCoreWebSocketClient class
    - Initialize with runtime ARN and region
    - Implement `invoke()` method for streaming responses
    - Implement `invoke_buffered()` method for complete responses
    - Implement connection cleanup in `close()` method
    - Add timeout handling and retry logic
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  - [ ]\* 4.2 Write property test for WebSocket connection cleanup
    - **Property 9: WebSocket Connection Cleanup**
    - **Validates: Requirements 2.3, 2.4**
    - Generate random invocation scenarios (success, failure, timeout)
    - Verify WebSocket is always closed after invocation
  - [ ]\* 4.3 Write unit tests for timeout handling
    - Test timeout enforcement at 5 minutes
    - Test retry logic with exponential backoff
    - Test connection error handling
    - _Requirements: 2.4, 2.5, 6.3_

- [x] 5. Checkpoint - Ensure core modules are working
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement session management with DynamoDB
  - [x] 6.1 Create `api/session_manager.py` with SessionManager class
    - Implement `create_session()` to generate UUID v4 session IDs
    - Implement `save_interaction()` to persist invocations
    - Implement `get_session_history()` to retrieve past interactions
    - Implement `cleanup_expired_sessions()` for TTL management
    - Add DynamoDB table initialization check
    - _Requirements: 4.1, 4.2, 4.4, 4.5_
  - [ ]\* 6.2 Write property test for session persistence
    - **Property 7: Session Persistence**
    - **Validates: Requirements 4.5**
    - Generate random interactions and save to DynamoDB
    - Verify all required fields are persisted correctly
  - [ ]\* 6.3 Write property test for session ID consistency
    - **Property 3: Session ID Consistency**
    - **Validates: Requirements 4.2**
    - Generate random session with multiple interactions
    - Verify session_id remains consistent across all interactions

- [x] 7. Implement response formatting module
  - [x] 7.1 Create `api/response_formatter.py` with ResponseFormatter class
    - Implement `format_success_response()` for successful invocations
    - Implement `format_error_response()` for error conditions
    - Implement `format_streaming_chunk()` for SSE format
    - Add CORS headers to all responses
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
  - [ ]\* 7.2 Write property test for response format consistency
    - **Property 4: Response Format Consistency**
    - **Validates: Requirements 8.1, 8.2, 8.4**
    - Generate random successful responses
    - Verify all required fields are present (status, request_id, execution_time_ms, assessment)
  - [ ]\* 7.3 Write property test for error response completeness
    - **Property 5: Error Response Completeness**
    - **Validates: Requirements 6.1, 6.2, 6.4, 6.5**
    - Generate random error conditions
    - Verify error responses include error_code, error_message, request_id

- [x] 8. Implement main Lambda handler
  - [x] 8.1 Create `api/lambda_handler.py` with main handler function
    - Parse API Gateway proxy event
    - Extract and validate request body
    - Generate unique request_id (UUID v4)
    - Invoke WebSocket client with timeout
    - Save interaction to session manager
    - Format and return response
    - Add comprehensive error handling with try/except blocks
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.5, 6.1, 6.2, 6.3, 6.4_
  - [ ]\* 8.2 Write property test for request ID uniqueness
    - **Property 14: Request ID Uniqueness**
    - **Validates: Requirements 6.5, 10.1**
    - Generate multiple concurrent requests
    - Verify all request IDs are unique UUID v4 values
  - [ ]\* 8.3 Write integration test for end-to-end invocation
    - Mock AgentCore Runtime WebSocket connection
    - Send complete HTTP request through Lambda handler
    - Verify response format and status code
    - Verify session is saved to DynamoDB
    - _Requirements: 1.1, 2.1, 2.2, 4.5, 8.1_

- [x] 9. Implement health check endpoint
  - [x] 9.1 Create `api/health.py` with health check handler
    - Implement basic health check returning 200 OK
    - Add AgentCore Runtime connectivity check
    - Add DynamoDB connectivity check
    - Include version information in response
    - No authentication required
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5_
  - [ ]\* 9.2 Write property test for health check independence
    - **Property 11: Health Check Independence**
    - **Validates: Requirements 14.1, 14.2, 14.4**
    - Verify health endpoint returns status without authentication
    - Verify health endpoint does not invoke AgentCore Runtime

- [x] 10. Checkpoint - Ensure Lambda functions are complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Create Infrastructure as Code with AWS CDK or Terraform
  - [x] 11.1 Create `infrastructure/api_stack.py` (CDK) or `infrastructure/api.tf` (Terraform)
    - Define API Gateway REST API resource
    - Define Lambda function with Python 3.11 runtime
    - Define IAM role with required permissions (AgentCore, DynamoDB, CloudWatch)
    - Define DynamoDB table for sessions with TTL
    - Configure API Gateway endpoints (/invoke, /health, /sessions/{id})
    - Configure IAM authorizer for API Gateway
    - Set Lambda timeout to 300 seconds and memory to 512 MB
    - _Requirements: 1.1, 5.1, 5.2, 5.3, 9.1, 9.2, 9.3, 9.4_
  - [x] 11.2 Add rate limiting configuration to API Gateway
    - Configure throttle settings: 100 requests per second
    - Configure burst limit: 200 requests
    - Add usage plan for different tiers
    - _Requirements: 13.1, 13.2, 13.3_
  - [x] 11.3 Configure CORS for API Gateway
    - Add CORS configuration for allowed origins
    - Include required headers in responses
    - _Requirements: 1.5_

- [x] 12. Create deployment scripts
  - [x] 12.1 Create `scripts/deploy_api.sh` deployment script
    - Package Lambda function with dependencies
    - Deploy infrastructure using CDK/Terraform
    - Output API Gateway endpoint URL
    - Validate deployment with health check
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  - [x] 12.2 Create `scripts/test_api.sh` testing script
    - Run unit tests with pytest
    - Run property tests with hypothesis
    - Run integration tests against deployed API
    - Generate coverage report
    - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 13. Create API documentation
  - [x] 13.1 Generate OpenAPI 3.0 specification
    - Document all endpoints with request/response schemas
    - Include authentication requirements
    - Add example requests and responses
    - Document error codes and messages
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_
  - [x] 13.2 Create README.md for API usage
    - Document authentication setup with AWS SSO
    - Provide example curl commands
    - Document rate limits and quotas
    - Include troubleshooting guide
    - _Requirements: 15.3, 15.4, 15.5_

- [x] 14. Implement logging and monitoring
  - [x] 14.1 Add structured logging to all modules
    - Use Python logging with JSON formatter
    - Include request_id, session_id in all log entries
    - Log request/response payloads (sanitized)
    - Log execution times and error details
    - _Requirements: 10.1, 10.2, 10.3_
  - [x] 14.2 Add CloudWatch metrics
    - Emit custom metrics for request count, latency, errors
    - Add metrics for AgentCore Runtime invocation success/failure
    - Add metrics for DynamoDB operations
    - _Requirements: 10.4_
  - [x] 14.3 Configure AWS X-Ray tracing
    - Enable X-Ray for Lambda function
    - Add subsegments for WebSocket calls and DynamoDB operations
    - _Requirements: 10.5_

- [x] 15. Create local development environment
  - [x] 15.1 Create `scripts/run_local.sh` for local testing
    - Set up local environment variables
    - Mock AgentCore Runtime WebSocket for development
    - Run Lambda function locally using AWS SAM or similar
    - _Requirements: 12.1, 12.2, 12.3_
  - [x] 15.2 Create mock AgentCore Runtime for testing
    - Implement simple WebSocket server that mimics AgentCore responses
    - Return sample SkyMarshal assessment data
    - Support session management
    - _Requirements: 12.1, 12.4_

- [x] 16. Final checkpoint - End-to-end validation
  - Deploy API to AWS development environment
  - Run integration tests against deployed API
  - Verify authentication with AWS SSO
  - Test rate limiting with concurrent requests
  - Verify session management and history retrieval
  - Check CloudWatch logs and metrics
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (100+ iterations)
- Unit tests validate specific examples and edge cases
- Integration tests validate component interactions
- The implementation uses Python 3.11 with async/await for WebSocket handling
- All AWS resources are defined as Infrastructure as Code for reproducibility
- Local development environment enables testing without AWS deployment
