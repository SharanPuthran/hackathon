# Implementation Plan: SkyMarshal Performance Optimization

## Overview

This plan implements performance optimizations for the SkyMarshal multi-agent system through four key areas: async execution verification, prompt optimization for A2A communication, DynamoDB batch queries, and model configuration updates. The implementation follows an incremental approach with validation at each step.

## Tasks

- [x] 1. Verify and enhance async execution patterns
  - Review existing asyncio.gather() usage in Phase 1 and Phase 2
  - Add configurable timeouts per agent type (safety: 60s, business: 45s)
  - Enhance error handling for partial failures
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [ ]\* 1.1 Write property test for phase synchronization
  - **Property 1: Phase Synchronization**
  - **Validates: Requirements 1.3, 1.4**

- [ ]\* 1.2 Write property test for agent failure resilience
  - **Property 2: Agent Failure Resilience**
  - **Validates: Requirements 1.5, 1.6, 6.1, 6.5**

- [ ] 2. Implement DynamoDB batch query support
  - [x] 2.1 Add batch_get_items() method to DynamoDBClient
    - Implement automatic splitting for requests > 100 items
    - Add exponential backoff retry logic
    - Handle unprocessed keys
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  - [x] 2.2 Add batch query methods for common patterns
    - batch_get_crew_members(crew_ids)
    - batch_get_flights(flight_ids)
    - batch_get_passengers(passenger_ids)
    - batch_get_cargo_shipments(shipment_ids)
    - _Requirements: 3.6_
  - [ ]\* 2.3 Write property test for batch size handling
    - **Property 5: Batch Size Handling**
    - **Validates: Requirements 3.3**
  - [ ]\* 2.4 Write property test for batch retry logic
    - **Property 6: Batch Query Retry Logic**
    - **Validates: Requirements 3.4, 3.5**
  - [ ]\* 2.5 Write property test for partial batch failures
    - **Property 7: Partial Batch Failure Handling**
    - **Validates: Requirements 6.2**
  - [ ]\* 2.6 Write unit tests for batch query operations
    - Test 100-item batch
    - Test 101-item batch (splitting)
    - Test 250-item batch (multiple splits)
    - Test partial failures
    - Test throttling scenarios
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3. Checkpoint - Verify batch queries work correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Update agent tools to use batch queries
  - [x] 4.1 Update crew compliance agent tools
    - Modify query_crew_roster_and_members to use batch_get_crew_members
    - _Requirements: 3.7_
  - [x] 4.2 Update network agent tools
    - Modify connecting flight queries to use batch_get_flights
    - _Requirements: 3.7_
  - [x] 4.3 Update guest experience agent tools
    - Modify passenger queries to use batch_get_passengers
    - _Requirements: 3.7_
  - [x] 4.4 Update cargo agent tools
    - Modify shipment queries to use batch_get_cargo_shipments
    - _Requirements: 3.7_
  - [ ]\* 4.5 Write property test for batch query usage
    - **Property 4: Batch Query Usage**
    - **Validates: Requirements 3.1, 3.7**
  - [ ]\* 4.6 Write property test for backward compatibility
    - **Property 11: Backward Compatibility**
    - **Validates: Requirements 7.1**

- [ ] 5. Optimize prompts for A2A communication
  - [x] 5.1 Create OptimizedPrompt model with to_xml() method
    - Implement XML generation for Phase 1 prompts
    - Implement XML generation for Phase 2 prompts with context
    - _Requirements: 2.1, 2.2_
  - [x] 5.2 Update augment_prompt_phase1() to use XML format
    - Replace verbose text with <disruption> and <task> tags
    - _Requirements: 2.1_
  - [x] 5.3 Update augment_prompt_phase2() to use XML format
    - Use structured <context> with nested <agent> tags
    - Include recommendation, confidence, constraints
    - _Requirements: 2.1, 2.7_
  - [x] 5.4 Optimize agent SYSTEM_PROMPT templates
    - Update crew_compliance agent prompt
    - Update maintenance agent prompt
    - Update regulatory agent prompt
    - Update network agent prompt
    - Update guest_experience agent prompt
    - Update cargo agent prompt
    - Update finance agent prompt
    - Target: 40% token reduction per agent
    - _Requirements: 2.2, 2.7_
  - [x] 5.5 Optimize arbitrator SYSTEM_PROMPT
    - Use structured XML format
    - Remove verbose explanations
    - _Requirements: 2.3_
  - [ ]\* 5.6 Write property test for prompt structure compliance
    - **Property 3: Prompt Structure Compliance**
    - **Validates: Requirements 2.1, 2.2, 2.7**
  - [ ]\* 5.7 Write unit tests for prompt optimization
    - Test Phase 1 XML generation
    - Test Phase 2 XML generation with context
    - Test arbitrator XML generation
    - Verify 30% token reduction
    - Verify no verbose human-oriented text
    - _Requirements: 2.1, 2.2, 2.3, 2.7_

- [ ] 6. Checkpoint - Verify prompt optimization works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Update model configuration for agent types
  - [x] 7.1 Add AGENT_MODEL_CONFIG to src/model/load.py
    - Define safety agent config (Sonnet 4.5)
    - Define business agent config (Haiku 4.5)
    - Define arbitrator config (Sonnet 4.5)
    - _Requirements: 4.1, 4.2, 4.3_
  - [x] 7.2 Add load_model_for_agent() function
    - Accept agent_type parameter (safety|business|arbitrator)
    - Return ChatBedrock with appropriate model
    - _Requirements: 4.1, 4.2, 4.3_
  - [x] 7.3 Update orchestrator to use agent-specific models
    - Modify phase1_initial_recommendations to load models per agent type
    - Modify phase2_revision_round to load models per agent type
    - Safety agents: crew_compliance, maintenance, regulatory use Sonnet
    - Business agents: network, guest_experience, cargo, finance use Haiku
    - _Requirements: 4.1, 4.2_
  - [x] 7.4 Update arbitrator to use Sonnet model
    - Modify phase3_arbitration to use load_arbitrator_model()
    - _Requirements: 4.3_
  - [ ]\* 7.5 Write unit tests for model configuration
    - Test safety agents use Sonnet model ID
    - Test business agents use Haiku model ID
    - Test arbitrator uses Sonnet model ID
    - Test model loading error messages
    - _Requirements: 4.1, 4.2, 4.3, 4.5_
  - [ ]\* 7.6 Write property test for model retry logic
    - **Property 8: Model Retry with Backoff**
    - **Validates: Requirements 6.3**

- [ ] 8. Enhance error handling and resilience
  - [x] 8.1 Add configurable timeouts per agent type
    - Safety agents: 60s timeout
    - Business agents: 45s timeout
    - Arbitrator: 90s timeout
    - Update run_agent_safely() to accept timeout parameter
    - _Requirements: 1.5, 1.6_
  - [x] 8.2 Implement safety agent failure halt logic
    - Check if failed agent is in SAFETY_AGENTS list
    - If safety agent fails after retries, halt execution
    - Return error requiring manual intervention
    - _Requirements: 6.6_
  - [ ]\* 8.3 Write property test for safety agent failure halt
    - **Property 9: Safety Agent Failure Halt**
    - **Validates: Requirements 6.6**
  - [ ]\* 8.4 Write unit tests for error handling
    - Test safety agent failure halts execution
    - Test business agent failure continues
    - Test model retry exhaustion returns degraded response
    - Test batch query throttling handling
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 9. Add performance monitoring and metrics
  - [ ] 9.1 Ensure execution time measurement at all levels
    - Verify duration_seconds recorded for each agent
    - Verify duration_seconds recorded for each phase
    - Verify total_duration_seconds recorded for orchestration
    - _Requirements: 5.4, 5.5_
  - [ ]\* 9.2 Write property test for execution time measurement
    - **Property 10: Execution Time Measurement**
    - **Validates: Requirements 5.4, 5.5**
  - [ ]\* 9.3 Write unit tests for timing metrics
    - Test agent duration is recorded
    - Test phase duration is recorded
    - Test total duration is recorded
    - Test all durations are non-negative
    - _Requirements: 5.4, 5.5_

- [ ] 10. Checkpoint - Verify all optimizations work together
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Integration testing and validation
  - [ ] 11.1 Create baseline performance test suite
    - Run 100 test cases with current system
    - Record median, p95, p99 latencies
    - Record token usage per request
    - Record cost per request
    - Save baseline outputs for comparison
    - _Requirements: 5.6, 7.2, 7.3_
  - [ ] 11.2 Run performance tests with optimized system
    - Run same 100 test cases with optimizations
    - Record median, p95, p99 latencies
    - Record token usage per request
    - Record cost per request
    - _Requirements: 5.6_
  - [ ] 11.3 Validate output quality preservation
    - Compare optimized outputs to baseline
    - Verify recommendations match
    - Verify confidence scores within ±0.1
    - Verify binding constraints match
    - _Requirements: 5.6, 7.2, 7.3_
  - [ ]\* 11.4 Write property test for output quality preservation
    - **Property 12: Output Quality Preservation**
    - **Validates: Requirements 5.6, 7.2, 7.3**
  - [ ]\* 11.5 Write integration tests
    - Test end-to-end optimized execution is faster
    - Test optimized output is equivalent to baseline
    - Test cost reduction from Haiku usage
    - Test backward compatibility with old queries
    - _Requirements: 5.6, 7.1, 7.2, 7.3_

- [ ] 12. Documentation and deployment
  - [ ] 12.1 Update README with optimization details
    - Document new batch query methods
    - Document agent-specific model configuration
    - Document performance improvements
    - Document backward compatibility guarantees
    - _Requirements: 7.1_
  - [ ] 12.2 Update deployment configuration
    - Verify .bedrock_agentcore.yaml is up to date
    - Verify pyproject.toml dependencies are correct
    - Add any new environment variables to .env.example
    - _Requirements: 4.6_
  - [ ] 12.3 Create performance optimization guide
    - Document prompt optimization best practices
    - Document when to use batch queries
    - Document model selection guidelines
    - Document monitoring and metrics
    - _Requirements: 2.4, 2.5, 2.6, 3.1, 4.1_

- [ ] 13. Final checkpoint - Deploy and verify
  - Deploy optimized system to development environment
  - Run smoke tests to verify functionality
  - Monitor performance metrics
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end optimization effectiveness

## Expected Performance Improvements

**Baseline** (before optimization):

- Total execution time: ~120s
- Token usage: ~15,000 tokens per request
- Cost: ~$0.15 per request

**Target** (after optimization):

- Total execution time: ~95s (21% improvement)
- Token usage: ~10,500 tokens per request (30% reduction)
- Cost: ~$0.08 per request (47% reduction)

**Key Optimizations**:

1. Business agents use Haiku (2-3x faster, 70% cheaper)
2. Batch queries reduce database latency by 60-80%
3. Optimized prompts reduce token usage by 30%
4. Async execution already optimal (verified)
