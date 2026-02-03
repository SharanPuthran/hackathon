# Requirements Document

## Introduction

This document specifies the requirements for optimizing the performance of the SkyMarshal multi-agent system. The system currently uses AWS Bedrock AgentCore to orchestrate 7 specialized agents across 3 phases (initial recommendations, revision, arbitration) for airline disruption management. The optimization focuses on reducing execution time through async execution improvements, prompt optimization for agent-to-agent communication, DynamoDB batch queries, and model configuration updates.

## Glossary

- **Orchestrator**: The main coordination system that manages agent execution across phases
- **Agent**: A specialized AI component that analyzes specific aspects of disruptions (crew_compliance, maintenance, regulatory, network, guest_experience, cargo, finance)
- **Arbitrator**: The final decision-making component that resolves conflicts and produces final recommendations
- **Phase_1**: Initial agent execution phase where all 7 agents analyze the disruption
- **Phase_2**: Revision phase where agents refine their assessments based on Phase 1 results
- **Phase_3**: Arbitration phase where the Arbitrator produces final recommendations
- **CRIS**: AWS Cross-Region Inference Service for global model availability
- **Haiku**: Claude 3.5 Haiku model (fast, cost-effective)
- **Sonnet**: Claude 3.5 Sonnet model (balanced performance)
- **DynamoDB_Client**: The database client that provides access to operational data
- **Batch_Query**: DynamoDB BatchGetItem operation that retrieves multiple items in a single request
- **A2A_Communication**: Agent-to-agent communication optimized for machine readability

## Requirements

### Requirement 1: Async Agent Execution

**User Story:** As a system operator, I want agents to execute asynchronously with proper synchronization, so that the system completes disruption analysis in minimal time while maintaining correctness.

#### Acceptance Criteria

1. WHEN Phase_1 begins, THE Orchestrator SHALL invoke all 7 agents asynchronously using asyncio.gather()
2. WHEN Phase_2 begins, THE Orchestrator SHALL invoke all 7 agents asynchronously using asyncio.gather()
3. WHEN all Phase_1 agents complete, THE Orchestrator SHALL wait for all results before transitioning to Phase_2
4. WHEN all Phase_2 agents complete, THE Orchestrator SHALL wait for all results before transitioning to Phase_3
5. WHEN any agent execution exceeds timeout threshold, THE Orchestrator SHALL handle the timeout gracefully and continue with available results
6. WHEN an agent raises an exception, THE Orchestrator SHALL capture the error and continue execution with remaining agents

### Requirement 2: Prompt Optimization for A2A Communication

**User Story:** As a system architect, I want all prompts optimized for agent-to-agent communication, so that token usage is minimized and execution speed is maximized.

#### Acceptance Criteria

1. WHEN the Orchestrator constructs prompts for agents, THE Orchestrator SHALL use concise, structured XML format without human-oriented explanations
2. WHEN agents construct responses, THE Agent SHALL return structured data in XML format optimized for machine parsing
3. WHEN the Arbitrator constructs prompts, THE Arbitrator SHALL use concise XML format focused on decision-making requirements
4. THE Orchestrator SHALL follow Anthropic Claude prompt engineering best practices for XML tag usage
5. THE Agent SHALL follow Anthropic Claude prompt engineering best practices for structured output
6. THE Arbitrator SHALL follow Anthropic Claude prompt engineering best practices for decision synthesis
7. WHEN prompts reference data, THE System SHALL use compact representations without redundant explanations

### Requirement 3: DynamoDB Batch Query Implementation

**User Story:** As a performance engineer, I want DynamoDB queries to use batch operations, so that database access latency is minimized when multiple items are needed.

#### Acceptance Criteria

1. WHEN an agent needs multiple items from the same table, THE DynamoDB_Client SHALL use BatchGetItem instead of multiple get_item calls
2. WHEN a batch query is requested, THE DynamoDB_Client SHALL support up to 100 items per batch request
3. WHEN a batch query exceeds 100 items, THE DynamoDB_Client SHALL split the request into multiple batches automatically
4. WHEN a batch query fails, THE DynamoDB_Client SHALL implement exponential backoff retry logic
5. WHEN unprocessed keys are returned, THE DynamoDB_Client SHALL retry those keys in subsequent requests
6. THE DynamoDB_Client SHALL provide batch query methods for all operational tables (flights, passengers, crew, cargo)
7. WHEN agents request data, THE Agent SHALL use batch query methods when multiple items are needed

### Requirement 4: Model Configuration Updates

**User Story:** As a system administrator, I want all models updated to use AWS Global CRIS variants, so that the system benefits from improved availability and performance.

#### Acceptance Criteria

1. WHEN loading agent models, THE System SHALL use AWS Global CRIS Haiku model ID
2. WHEN loading the orchestrator model, THE System SHALL use AWS Global CRIS Haiku model ID
3. WHEN loading the arbitrator model, THE System SHALL use AWS Global CRIS Sonnet model ID
4. THE System SHALL retrieve correct CRIS model IDs using AWS CLI bedrock list-foundation-models command
5. WHEN model loading fails, THE System SHALL provide clear error messages indicating the model ID and region
6. THE System SHALL validate model availability before deployment

### Requirement 5: Performance Monitoring and Optimization

**User Story:** As a performance engineer, I want to identify and fix performance bottlenecks, so that the system achieves optimal throughput and minimal latency.

#### Acceptance Criteria

1. WHEN analyzing the codebase, THE System SHALL identify synchronous operations that can be made asynchronous
2. WHEN analyzing data access patterns, THE System SHALL identify opportunities for caching or batching
3. WHEN analyzing agent execution, THE System SHALL identify redundant computations or data transfers
4. THE System SHALL measure execution time for each phase (Phase_1, Phase_2, Phase_3)
5. THE System SHALL measure execution time for each agent within phases
6. WHEN optimizations are applied, THE System SHALL maintain functional correctness and accuracy

### Requirement 6: Error Handling and Resilience

**User Story:** As a system operator, I want robust error handling for async operations and batch queries, so that partial failures do not cause complete system failure.

#### Acceptance Criteria

1. WHEN an agent times out, THE Orchestrator SHALL log the timeout and continue with available agent results
2. WHEN a batch query partially fails, THE DynamoDB_Client SHALL return successful items and report failed items
3. WHEN model invocation fails, THE System SHALL retry with exponential backoff up to 3 attempts
4. WHEN all retries are exhausted, THE System SHALL return a degraded response with available data
5. THE System SHALL log all errors with sufficient context for debugging
6. WHEN critical safety agents fail (crew_compliance, maintenance, regulatory), THE System SHALL halt execution and require manual intervention

### Requirement 7: Backward Compatibility and Testing

**User Story:** As a developer, I want comprehensive tests for optimizations, so that I can verify correctness and prevent regressions.

#### Acceptance Criteria

1. WHEN batch queries are implemented, THE System SHALL maintain backward compatibility with existing single-item query interfaces
2. WHEN prompts are optimized, THE System SHALL produce functionally equivalent outputs to previous versions
3. WHEN models are changed, THE System SHALL validate output quality against baseline assessments
4. THE System SHALL include unit tests for batch query operations
5. THE System SHALL include integration tests for async agent execution
6. THE System SHALL include property tests for prompt optimization correctness
