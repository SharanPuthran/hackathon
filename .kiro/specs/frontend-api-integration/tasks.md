# Implementation Plan: Frontend API Integration

## Overview

This implementation plan breaks down the frontend-API integration into discrete coding tasks. The approach follows a layered architecture: first building the foundational API service layer, then integrating it into the App component, and finally updating the OrchestrationView to use real data. Each task builds incrementally to ensure the application remains functional throughout development.

## Tasks

- [x] 1. Set up environment configuration and validation
  - Create `frontend/config/env.ts` with environment variable loading
  - Add validation for required variables (API endpoint, AWS region)
  - Create `.env.example` file with all required variables
  - Add TypeScript types for EnvironmentConfig
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]\* 1.1 Write property test for environment configuration loading
  - **Property 1: Environment Configuration Loading**
  - **Validates: Requirements 1.1, 1.3**

- [ ]\* 1.2 Write unit tests for URL validation
  - Test HTTPS validation
  - Test invalid URL formats
  - Test missing configuration error
  - _Requirements: 1.2, 1.4_

- [x] 2. Implement AWS Signature V4 authentication
  - Create `frontend/services/auth.ts` with AWSSignatureV4 class
  - Implement signature generation following AWS specification
  - Add helper functions for canonical request and string-to-sign
  - Add TypeScript interfaces for credentials and signature params
  - _Requirements: 2.1, 2.3_

- [ ]\* 2.1 Write property test for AWS signature presence
  - **Property 3: AWS Signature Presence**
  - **Validates: Requirements 2.1, 2.3**

- [ ]\* 2.2 Write unit tests for authentication error handling
  - Test missing credentials error
  - Test 401 error handling
  - Test credential expiry handling
  - _Requirements: 2.2, 2.4_

- [x] 3. Create API service module
  - Create `frontend/services/api.ts` with APIService class
  - Implement invoke() method with request signing
  - Implement healthCheck() method
  - Add error handling and error type classification
  - Add TypeScript interfaces for all request/response types
  - _Requirements: 3.1, 3.2, 3.3, 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ]\* 3.1 Write property test for request structure completeness
  - **Property 4: Request Structure Completeness**
  - **Validates: Requirements 3.1, 3.2, 3.3**

- [ ]\* 3.2 Write unit tests for error handling
  - Test network error (display and retry)
  - Test 401 authentication error
  - Test 504 timeout error
  - Test 429 rate limit error
  - Test unknown error fallback
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 4. Implement response mapper
  - Create `frontend/services/responseMapper.ts` with ResponseMapper class
  - Implement mapToMessages() to convert assessment to MessageData[]
  - Implement mapToSolutions() to convert recommendations to Solution[]
  - Add helper function to map individual agent results
  - Handle missing optional fields gracefully
  - _Requirements: 4.1, 4.2, 4.3, 10.1, 10.2_

- [ ]\* 4.1 Write property test for assessment extraction
  - **Property 7: Assessment Extraction**
  - **Validates: Requirements 4.1**

- [ ]\* 4.2 Write property test for phase data mapping
  - **Property 8: Phase Data Mapping**
  - **Validates: Requirements 4.2, 4.3, 5.2, 5.3**

- [ ]\* 4.3 Write property test for agent message creation
  - **Property 11: Agent Message Creation**
  - **Validates: Requirements 5.1**

- [ ]\* 4.4 Write property test for recommendation parsing
  - **Property 16: Recommendation Parsing**
  - **Validates: Requirements 10.1, 10.2**

- [ ]\* 4.5 Write unit tests for invalid response handling
  - Test malformed JSON
  - Test missing required fields
  - Test unexpected field types
  - _Requirements: 4.5_

- [x] 5. Create session management hook
  - Create `frontend/hooks/useSession.ts` with useSession hook
  - Implement session state management (sessionId, isActive)
  - Implement setSessionId, clearSession functions
  - Add session persistence to localStorage (optional)
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ]\* 5.1 Write property test for session persistence round-trip
  - **Property 9: Session Persistence Round-Trip**
  - **Validates: Requirements 4.4, 6.1, 6.2**

- [ ]\* 5.2 Write unit tests for session management
  - Test session creation on first call
  - Test session reuse on subsequent calls
  - Test session clear on new conversation
  - Test session expiry handling
  - _Requirements: 6.3, 6.4_

- [x] 6. Create API hook with loading and error states
  - Create `frontend/hooks/useAPI.ts` with useAPI hook
  - Implement invoke function that calls APIService
  - Manage loading, error, and success states
  - Integrate with useSession hook for session management
  - Add clearError function
  - _Requirements: 3.4, 3.5, 8.1, 8.2, 8.3, 8.4_

- [ ]\* 6.1 Write property test for loading state consistency
  - **Property 5: Loading State Consistency**
  - **Validates: Requirements 3.4**

- [ ]\* 6.2 Write unit tests for API hook states
  - Test loading state during API call
  - Test error state on failure
  - Test success state on completion
  - Test retry after error
  - _Requirements: 3.5, 8.4_

- [ ] 7. Checkpoint - Ensure all service layer tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Update App.tsx to integrate API service
  - Import APIService and useAPI hook
  - Add state for apiResponse, loading, and error
  - Modify handleProcess to call API instead of just transitioning
  - Show loading indicator on landing page during API call
  - Show error message on landing page if API fails
  - Pass apiResponse to OrchestrationView on success
  - Add retry mechanism for failed requests
  - _Requirements: 3.1, 3.4, 3.5, 8.1, 8.4_

- [ ]\* 8.1 Write integration test for App.tsx API flow
  - Test complete flow: submit → API call → transition to orchestration
  - Test error flow: submit → API error → show error → retry
  - _Requirements: 3.1, 3.4, 3.5_

- [x] 9. Update OrchestrationView to use API response
  - Add apiResponse prop to OrchestrationViewProps
  - Remove (comment out) MOCK_INITIAL_RESPONSES constant
  - Remove (comment out) MOCK_CROSS_IMPACT_RESPONSES constant
  - Remove (comment out) ARBITRATOR_SOLUTIONS constant
  - Remove (comment out) mock orchestration sequence in useEffect
  - Parse apiResponse using ResponseMapper on component mount
  - Update messages state with parsed agent messages
  - Update solutions state with parsed recommendations
  - Add comments explaining how to re-enable mock mode
  - _Requirements: 4.1, 4.2, 4.3, 5.1, 9.1, 9.2, 9.3, 9.4, 9.5, 10.1, 10.5_

- [ ]\* 9.1 Write property test for stage transition correctness
  - **Property 12: Stage Transition Correctness**
  - **Validates: Requirements 5.4, 8.1, 8.3, 11.5**

- [ ]\* 9.2 Write unit tests for OrchestrationView with real data
  - Test message display from API response
  - Test solutions display from API response
  - Test stage transitions
  - _Requirements: 5.1, 5.2, 5.3, 10.5_

- [ ] 10. Implement cross-impact analysis trigger
  - Add API call for cross-impact analysis when button is clicked
  - Include session_id in cross-impact request
  - Update messages with cross-impact responses
  - Transition to decision_phase after completion
  - Show thinking indicators during cross-impact processing
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ]\* 10.1 Write property test for cross-impact request session continuity
  - **Property 20: Cross-Impact Request Session Continuity**
  - **Validates: Requirements 11.2**

- [ ]\* 10.2 Write unit tests for cross-impact flow
  - Test button visibility in waiting_for_user stage
  - Test API call includes session_id
  - Test messages added after cross-impact response
  - Test stage transition to decision_phase
  - _Requirements: 11.1, 11.3, 11.4, 11.5_

- [x] 11. Add solution selection and display
  - Ensure solutions from API are displayed in ArbitratorPanel
  - Implement solution selection state management
  - Update selectedSolutionId when user selects a solution
  - Verify all solution fields are displayed (title, description, impact, cost)
  - _Requirements: 10.2, 10.3, 10.4, 10.5_

- [ ]\* 11.1 Write property test for solution selection storage
  - **Property 17: Solution Selection Storage**
  - **Validates: Requirements 10.4**

- [ ]\* 11.2 Write unit tests for solution display
  - Test all recommendations are displayed
  - Test solution selection updates state
  - _Requirements: 10.4, 10.5_

- [ ] 12. Add environment variable configuration files
  - Create `.env.example` with all required variables
  - Update `vite.config.ts` to load environment variables
  - Add documentation in README for environment setup
  - Add validation error messages for missing configuration
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 13. Checkpoint - Ensure all integration tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Add error boundary and global error handling
  - Create ErrorBoundary component for App.tsx
  - Add global error handler for uncaught errors
  - Add user-friendly error messages for all error types
  - Add retry buttons for recoverable errors
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ]\* 14.1 Write unit tests for error boundary
  - Test error boundary catches component errors
  - Test error boundary displays fallback UI
  - Test error boundary allows retry
  - _Requirements: 7.1, 7.5_

- [ ] 15. Add loading states and animations
  - Add loading spinner on landing page during API call
  - Preserve existing "Establishing Neural Link" animation in OrchestrationView
  - Add loading indicators for cross-impact analysis
  - Ensure smooth transitions between loading and content states
  - _Requirements: 8.1, 8.2, 11.3_

- [ ] 16. Implement streaming support preparation (future-proofing)
  - Structure API client to support streaming responses
  - Add response type detection (chunked vs complete)
  - Implement incremental chunk processing
  - Maintain backward compatibility with non-streaming responses
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [ ]\* 16.1 Write property test for response format compatibility
  - **Property 22: Response Format Compatibility**
  - **Validates: Requirements 12.2, 12.4**

- [ ] 17. Final checkpoint - End-to-end testing
  - Test complete flow: landing page → API call → orchestration → cross-impact → solutions
  - Test error scenarios: network error, auth error, timeout
  - Test session continuity across multiple prompts
  - Test with real API endpoint (if available)
  - Verify all UI elements display correctly
  - Verify auto-scroll behavior works
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation preserves existing UI/UX while replacing mock data with real API calls
- Mock data is commented out (not deleted) to allow easy switching back for testing
- AWS credentials should be configured through environment variables or AWS SDK default credential chain
