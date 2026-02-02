# Requirements Document

## Introduction

This specification defines the requirements for migrating SkyMarshal's database query mechanism from MCP tools to LangGraph's native DynamoDB integration. Agents will query operational data (flights, crew, cargo) using LangGraph tools instead of MCP tools, while the orchestrator workflow remains unchanged. Additionally, the arbitrator agent will be connected to AWS Bedrock Knowledge Base for informed decision-making.

## Glossary

- **LangGraph_Tool**: A LangGraph-native tool that wraps DynamoDB queries for agent use
- **MCP_Tool**: Model Context Protocol tool (legacy approach being replaced)
- **Orchestrator**: The main coordination system that manages the three-phase workflow (safety → business → arbitration)
- **Operational_Data**: Real-time airline data (flights, crew, cargo, passengers) stored in DynamoDB tables
- **Knowledge_Base**: AWS Bedrock Knowledge Base service for retrieval-augmented generation (RAG)
- **Arbitrator**: The final decision-making agent that resolves conflicts and provides binding recommendations
- **Agent**: A specialized AI component that analyzes one aspect of disruption (crew compliance, maintenance, regulatory, network, guest experience, cargo, finance)
- **DynamoDBClient**: The existing boto3-based client for querying operational data
- **GSI**: Global Secondary Index used for efficient DynamoDB queries

## Requirements

### Requirement 1: LangGraph Checkpoint Infrastructure

**User Story:** As a system administrator, I want to set up DynamoDB-backed checkpoint persistence, so that agent state is durable and survives failures.

#### Acceptance Criteria

1. WHEN the system initializes THEN the System SHALL create a DynamoDB table for checkpoints with partition key (PK), sort key (SK), and TTL attributes
2. WHEN the system initializes THEN the System SHALL create an S3 bucket for storing large checkpoint payloads (≥350KB)
3. WHEN a checkpoint is less than 350KB THEN the System SHALL store it directly in DynamoDB
4. WHEN a checkpoint is 350KB or larger THEN the System SHALL store the payload in S3 and store a reference in DynamoDB
5. THE System SHALL configure DynamoDBSaver with appropriate table name, S3 bucket, and AWS credentials

### Requirement 2: Thread Management

**User Story:** As an orchestrator, I want to manage conversation threads, so that multi-round workflows maintain continuity and context.

#### Acceptance Criteria

1. WHEN a new disruption analysis starts THEN the System SHALL create a unique thread identifier
2. WHEN an agent executes within a thread THEN the System SHALL associate all checkpoints with that thread ID
3. WHEN retrieving thread history THEN the System SHALL return all checkpoints ordered by timestamp
4. WHEN a thread completes THEN the System SHALL mark it as complete in the checkpoint metadata
5. THE System SHALL support querying threads by status (active, completed, failed)

### Requirement 3: Agent Checkpoint Persistence

**User Story:** As an agent, I want to save checkpoints at key decision points, so that execution can resume after failures.

#### Acceptance Criteria

1. WHEN an agent begins analysis THEN the System SHALL save a checkpoint with initial state
2. WHEN an agent completes a major decision THEN the System SHALL save a checkpoint with the decision and rationale
3. WHEN an agent encounters an error THEN the System SHALL save a checkpoint with error details
4. WHEN an agent completes successfully THEN the System SHALL save a final checkpoint with results
5. THE System SHALL include timestamp, agent name, phase, and confidence score in each checkpoint

### Requirement 4: Orchestrator State Management

**User Story:** As an orchestrator, I want to persist workflow state across all three phases, so that the entire disruption analysis can be resumed from any point.

#### Acceptance Criteria

1. WHEN Phase 1 (safety) completes THEN the Orchestrator SHALL save a checkpoint with all safety agent results
2. WHEN Phase 2 (business) completes THEN the Orchestrator SHALL save a checkpoint with all business agent results
3. WHEN Phase 3 (arbitration) begins THEN the Orchestrator SHALL load checkpoints from Phases 1 and 2
4. WHEN the workflow fails at any phase THEN the Orchestrator SHALL support resuming from the last successful checkpoint
5. THE Orchestrator SHALL maintain thread continuity across all three phases

### Requirement 5: Failure Recovery

**User Story:** As a system operator, I want to recover from agent failures, so that disruption analysis can complete without starting over.

#### Acceptance Criteria

1. WHEN an agent crashes mid-execution THEN the System SHALL retrieve the last checkpoint for that thread
2. WHEN resuming from a checkpoint THEN the System SHALL restore agent state and continue from that point
3. WHEN multiple agents fail in parallel THEN the System SHALL recover each agent independently
4. WHEN a phase fails completely THEN the System SHALL support restarting that phase with previous phase results
5. THE System SHALL log all recovery attempts with timestamps and success status

### Requirement 6: Human-in-the-Loop Integration

**User Story:** As an airline operations manager, I want to approve critical arbitrator decisions, so that AI recommendations are validated before execution.

#### Acceptance Criteria

1. WHEN the arbitrator reaches a decision point THEN the System SHALL pause execution and save a checkpoint
2. WHEN paused for approval THEN the System SHALL expose the decision and rationale through an API
3. WHEN a human approves a decision THEN the System SHALL resume execution from the paused checkpoint
4. WHEN a human rejects a decision THEN the System SHALL mark the thread as rejected and halt execution
5. THE System SHALL record approval/rejection metadata in the checkpoint (approver ID, timestamp, comments)

### Requirement 7: Arbitrator Knowledge Base Connection

**User Story:** As an arbitrator agent, I want to query AWS Bedrock Knowledge Base, so that I can access regulatory guidance and precedent for decision-making.

#### Acceptance Criteria

1. WHEN the arbitrator needs regulatory guidance THEN the System SHALL query Bedrock Knowledge Base with relevant context
2. WHEN Knowledge Base returns results THEN the System SHALL include source citations in the arbitrator's rationale
3. WHEN Knowledge Base queries fail THEN the System SHALL fall back to LLM-only reasoning and log the failure
4. THE Arbitrator SHALL use retrieval-augmented generation (RAG) to ground decisions in documented precedent
5. THE System SHALL configure Knowledge Base connection with appropriate IAM permissions and endpoint

### Requirement 8: Operational Data Access Preservation

**User Story:** As an agent, I want to continue querying operational data efficiently, so that real-time flight, crew, and cargo information remains accessible.

#### Acceptance Criteria

1. WHEN an agent queries flight data THEN the System SHALL use the existing DynamoDBClient with GSI queries
2. WHEN an agent queries crew roster THEN the System SHALL use the existing crew compliance tools unchanged
3. WHEN an agent queries cargo shipments THEN the System SHALL use the existing cargo tools unchanged
4. THE System SHALL maintain separate DynamoDB tables for operational data (Flights, CrewRoster, CargoShipments, etc.)
5. THE System SHALL NOT migrate operational data queries to the checkpoint persistence pattern

### Requirement 9: Development and Production Modes

**User Story:** As a developer, I want to use in-memory checkpoints during development, so that I can test without DynamoDB infrastructure.

#### Acceptance Criteria

1. WHEN running in development mode THEN the System SHALL use MemorySaver for checkpoint persistence
2. WHEN running in production mode THEN the System SHALL use DynamoDBSaver for checkpoint persistence
3. WHEN switching between modes THEN the System SHALL detect the environment from configuration or environment variables
4. THE System SHALL provide identical checkpoint APIs regardless of persistence backend
5. THE System SHALL log which checkpoint backend is active at startup

### Requirement 10: Audit Trail and Time-Travel Debugging

**User Story:** As a compliance officer, I want to inspect complete audit trails of disruption analysis, so that I can verify regulatory compliance and investigate decisions.

#### Acceptance Criteria

1. WHEN querying a thread's history THEN the System SHALL return all checkpoints with timestamps and agent names
2. WHEN inspecting a checkpoint THEN the System SHALL provide full state including inputs, outputs, and reasoning
3. WHEN replaying a workflow THEN the System SHALL support loading any historical checkpoint and continuing from that point
4. THE System SHALL retain checkpoints according to configurable TTL (default 90 days for compliance)
5. THE System SHALL support exporting checkpoint history in JSON format for external audit tools

### Requirement 11: Backward Compatibility

**User Story:** As a system maintainer, I want existing agents to work during migration, so that the system remains operational throughout the transition.

#### Acceptance Criteria

1. WHEN agents use existing tool interfaces THEN the System SHALL continue to support them without modification
2. WHEN the checkpoint system is disabled THEN the System SHALL fall back to in-memory execution
3. WHEN migrating incrementally THEN the System SHALL support mixed mode (some agents with checkpoints, some without)
4. THE System SHALL maintain existing API contracts for agent invocation
5. THE System SHALL provide migration utilities to convert existing workflows to checkpoint-based execution

### Requirement 12: Performance and Scalability

**User Story:** As a system architect, I want checkpoint persistence to scale efficiently, so that high-volume disruption analysis remains performant.

#### Acceptance Criteria

1. WHEN saving checkpoints THEN the System SHALL complete writes within 100ms for checkpoints under 350KB
2. WHEN loading checkpoints THEN the System SHALL complete reads within 50ms from DynamoDB
3. WHEN handling large checkpoints THEN the System SHALL stream S3 payloads to avoid memory exhaustion
4. THE System SHALL support concurrent checkpoint operations across multiple threads
5. THE System SHALL implement exponential backoff for DynamoDB throttling errors
