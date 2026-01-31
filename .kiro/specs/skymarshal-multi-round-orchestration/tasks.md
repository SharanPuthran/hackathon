# Implementation Tasks

## Overview

This document outlines the implementation tasks for the SkyMarshal Multi-Round Orchestration rearchitecture. Tasks are organized by component and include property-based tests to validate correctness properties defined in the design document.

**IMPORTANT**: See [PROMPT_HANDLING_CLARIFICATION.md](./PROMPT_HANDLING_CLARIFICATION.md) for details on how natural language prompts are processed using LangChain structured output. Agents use `with_structured_output()` with Pydantic models - NO custom extraction tools or parsing functions are needed.

## Task Organization

- **Phase 1**: Database Schema and Infrastructure (Tasks 1-3)
- **Phase 2**: Core Components (Tasks 4-7)
- **Phase 3**: Agent Updates (Tasks 8-14)
- **Phase 4**: Arbitrator Implementation (Task 15)
- **Phase 5**: Integration and Testing (Tasks 16-18)
- **Phase 6**: Documentation and Deployment (Tasks 19-20)

---

## Phase 1: Database Schema and Infrastructure

### Task 1: Create DynamoDB GSIs

**Validates**: Requirements 4.1-4.12

Create new Global Secondary Indexes on existing DynamoDB tables to support efficient flight-based queries.

**Subtasks**:

- [x] 1.1 Create script `scripts/create_gsis.py` to add new GSIs
  - Add `flight-number-date-index` GSI to flights table (PK: flight_number, SK: scheduled_departure)
  - Add `aircraft-registration-index` GSI to flights table (PK: aircraft_registration)
  - Add `flight-id-index` GSI to bookings table (PK: flight_id)
  - Add `aircraft-registration-index` GSI to MaintenanceWorkOrders table (PK: aircraftRegistration)
- [x] 1.2 Implement GSI activation wait logic
  - Poll GSI status until ACTIVE
  - Timeout after 10 minutes with clear error message
- [x] 1.3 Add rollback capability to remove GSIs if needed
- [x] 1.4 Test GSI creation on development environment
- [x] 1.5 Validate GSI query performance with sample data

**Acceptance Criteria**:

- All new GSIs created successfully
- GSIs reach ACTIVE status
- Sample queries use GSIs (no table scans)
- Script includes error handling and rollback

---

### Task 2: Create Database Constants Module

**Validates**: Requirements 8.1-8.5

Create centralized configuration for table names, GSI names, and agent table access permissions.

**Subtasks**:

- [x] 2.1 Create `src/database/constants.py`
  - Define all table name constants
  - Define all GSI name constants
  - Define AGENT_TABLE_ACCESS dictionary mapping agents to authorized tables
- [x] 2.2 Add type hints and documentation
- [x] 2.3 Create validation function to verify constants match actual DynamoDB tables
- [x] 2.4 Add unit tests for constants module
- [x] 2.5 Update existing code to use constants instead of hardcoded strings

**Acceptance Criteria**:

- All table and GSI names defined as constants
- AGENT_TABLE_ACCESS matches requirements 7.1-7.7
- Validation function confirms constants match deployed tables
- All existing code updated to use constants

---

### Task 3: Create Data Validation Script

**Validates**: Requirements 6.1-6.5

Create a Python script to validate data integrity and identify discrepancies in DynamoDB tables.

**Subtasks**:

- [x] 3.1 Create `scripts/validate_dynamodb_data.py`
  - Check all required attributes present in each table
  - Verify foreign key relationships (e.g., flight_id references exist)
  - Identify orphaned records
  - Validate data type consistency
- [x] 3.2 Implement detailed reporting
  - Generate JSON report with record identifiers and specific issues
  - Include severity levels (error, warning, info)
  - Provide fix suggestions where possible
- [x] 3.3 Add permission validation
  - Verify IAM roles for AgentCore deployment
  - Check agent table access permissions
- [x] 3.4 Add GSI verification after data validation
  - Verify all required GSIs exist on tables
  - Check GSI status (must be ACTIVE)
  - Validate GSI key schema matches requirements
  - Test sample queries use GSIs (no table scans)
- [x] 3.5 Create unit tests for validation logic
- [x] 3.6 Run validation on development environment and fix identified issues

**Acceptance Criteria**:

- Script validates all tables and relationships
- Verifies all required GSIs are created and ACTIVE
- Generates detailed discrepancy report
- Identifies permission issues
- All validation tests pass

---

## Phase 2: Core Components

### Task 4: Create Date/Time Utility Tool

**Validates**: Requirements 1.4, 1.8, 1.9, 1.10

Create a simple utility that provides current date/time for agents. Date parsing is handled by LangChain structured output, not custom parsing functions.

**Subtasks**:

- [x] 4.1 Create `src/utils/datetime_tool.py`
  - Implement `get_current_datetime()` function to return current UTC datetime
  - Remove custom date parsing functions (handled by LangChain structured output)
- [x] 4.2 Create LangChain Tool wrapper for `get_current_datetime()`
  - Tool name: "get_current_datetime"
  - Tool description: "Returns current UTC datetime for date resolution"
- [x] 4.3 Create unit tests for datetime utility
- [x] 4.4 Update documentation to clarify LangChain handles date parsing

**Acceptance Criteria**:

- `get_current_datetime()` returns current UTC datetime
- Tool wrapper available for agents
- No custom date parsing functions exist
- Documentation clarifies LangChain structured output handles parsing

---

### Task 5: Update DynamoDB Client with New Query Methods

**STATUS: NOT APPLICABLE - Tools are defined within each agent, not in centralized files**

~~**Validates**: Requirements 2.2, 3.1-3.6~~

~~Enhance the DynamoDB client with methods to query using the new GSIs.~~

**Architecture Decision**: All DynamoDB query tools must be defined within each agent's implementation file, not in `src/database/dynamodb.py` or `src/database/tools.py`. Each agent defines its own tools as LangChain Tool objects that directly query DynamoDB using boto3.

**Subtasks**:

- [x] 5.1 ~~Update `src/database/dynamodb.py`~~ - NOT APPLICABLE
- [x] 5.2 ~~Ensure all queries use GSIs (no table scans)~~ - Handled per-agent
- [x] 5.3 ~~Add error handling for missing flights/records~~ - Handled per-agent
- [x] 5.4 ~~Add query result caching for repeated lookups~~ - NOT APPLICABLE
- [ ] 5.5 ~~Create unit tests for all new query methods~~ - Handled per-agent
- [ ] 5.6 ~~Write property-based test for GSI usage (Property 4)~~ - Handled per-agent

**Acceptance Criteria**:

- Each agent defines its own DynamoDB query tools
- All query tools use GSIs (no table scans)
- Error handling implemented within each agent's tools
- Tools follow LangChain Tool interface

---

### Task 6: Create Agent Tool Factory

**STATUS: NOT APPLICABLE - Tools are defined within each agent, not in a factory**

~~**Validates**: Requirements 7.1-7.8~~

~~Create a factory to generate agent-specific DynamoDB query tools with table access restrictions.~~

**Architecture Decision**: Each agent defines its own tools directly in its agent.py file. There is no centralized tool factory. This provides better encapsulation and makes each agent self-contained.

**Subtasks**:

- [ ] 6.1 ~~Create `src/database/tools.py`~~ - NOT APPLICABLE
- [ ] 6.2 ~~Implement table access enforcement~~ - Handled per-agent
- [ ] 6.3 ~~Create LangChain Tool wrappers for all database operations~~ - Handled per-agent
- [ ] 6.4 ~~Add tool descriptions for LLM understanding~~ - Handled per-agent
- [ ] 6.5 ~~Create unit tests for tool factory~~ - NOT APPLICABLE
- [ ] 6.6 ~~Write property-based test for table access restrictions (Property 5)~~ - Handled per-agent

**Acceptance Criteria**:

- Each agent defines its own tools in its agent.py file
- Tools are scoped to only the tables that agent needs
- Tool descriptions are clear for LLM understanding
- No centralized tool factory exists

---

### Task 7: Refactor Orchestrator for Passthrough Mode

**Validates**: Requirements 1.6, 9.1-9.8

Simplify the orchestrator to act as a pure coordinator without parsing or data access.

**Subtasks**:

- [x] 7.1 Update `src/main.py`
  - Remove all input parsing logic
  - Remove flight lookup logic
  - Remove date validation logic
  - Update `handle_disruption()` to accept single `user_prompt` parameter
- [x] 7.2 Implement prompt augmentation
  - Add phase-specific instructions to user prompts
  - Phase 1: "Please analyze this disruption and provide your initial recommendation"
  - Phase 2: "Review other agents' recommendations and revise if needed"
  - Preserve original user prompt content (no parsing or extraction)
- [x] 7.3 Update phase execution methods
  - `phase1_initial_recommendations(user_prompt)` - pass prompt to agents
  - `phase2_revision_round(user_prompt, initial_collation)` - pass prompt and collation
  - `phase3_arbitration(revised_collation)` - pass collation to arbitrator
- [x] 7.4 Implement async agent invocation within phases
- [x] 7.5 Implement response collation logic
- [x] 7.6 Add timeout handling (30 seconds per agent)
- [x] 7.7 Create unit tests for orchestrator
- [x] 7.8 Write property-based test for instruction augmentation invariant (Property 1)
- [x] 7.9 Write property-based test for agent autonomy (Property 2)

**Acceptance Criteria**:

- Orchestrator contains no parsing/validation logic
- User prompt content preserved in augmented prompts
- Phase-specific instructions added appropriately
- Three-phase execution implemented
- Async agent invocation working
- Property tests validate instruction augmentation and autonomy

---

## Phase 3: Agent Updates

### Task 8: Create Pydantic Models for Structured Output

**Validates**: Requirements 1.1-1.15, 2.1

Create Pydantic models that agents use with LangChain's `with_structured_output()` to extract flight information from natural language prompts.

**Subtasks**:

- [x] 8.1 Create `src/agents/schemas.py` (or update existing)
  - Define `FlightInfo` Pydantic model with fields: flight_number, date, disruption_event
  - Add Field descriptions for each attribute to guide LLM extraction
  - Add validation rules (e.g., date format, flight number pattern)
- [x] 8.2 Create example usage documentation
  - Show how to use `llm.with_structured_output(FlightInfo)`
  - Provide example prompts and expected outputs
  - Document error handling for extraction failures
- [x] 8.3 Create unit tests for Pydantic models
  - Test model validation
  - Test with various natural language inputs
- [x] 8.4 Write property-based test for flight lookup consistency (Property 3)
  - Generate prompts with same flight info in different phrasings
  - Verify structured output extracts consistent data

**Acceptance Criteria**:

- Pydantic models defined with clear field descriptions
- Models work with LangChain `with_structured_output()`
- Validation rules enforce data quality
- Property test validates consistent extraction across phrasings
- NO custom extraction functions or regex parsing

---

### Task 9: Update Agent Payload Schema

**Validates**: Requirements 1.6, 9.4

Update agent payload schemas to accept natural language prompts instead of structured fields.

**Subtasks**:

- [ ] 9.1 Update `src/agents/schemas.py`
  - Change `DisruptionPayload` to use `user_prompt: str` instead of structured fields
  - Add `extracted_flight_info` to `AgentResponse` schema
  - Update `Collation` schema if needed
- [ ] 9.2 Update Pydantic models with proper validation
- [ ] 9.3 Add schema documentation
- [ ] 9.4 Create unit tests for schema validation

**Acceptance Criteria**:

- Schemas updated to use natural language prompt
- Pydantic validation working
- All schema tests pass

---

### Task 10: Update Crew Compliance Agent

**Validates**: Requirements 1.7, 2.1-2.7, 7.1

Update crew compliance agent to use LangChain structured output for data extraction and define its own DynamoDB query tools.

**Subtasks**:

- [ ] 10.1 Update `src/agents/crew_compliance/agent.py`
  - Import FlightInfo Pydantic model
  - Use `llm.with_structured_output(FlightInfo)` to extract flight data from prompt
  - Define agent-specific DynamoDB query tools as LangChain Tool objects
  - Create tools for: query_flight, query_crew_roster, query_crew_members
  - Update system prompt to explain agent's responsibility for extraction
- [ ] 10.2 Implement DynamoDB query tools
  - Use boto3 to query DynamoDB tables
  - Use GSIs from constants module (FLIGHT_NUMBER_DATE_INDEX, FLIGHT_POSITION_INDEX)
  - Only access authorized tables (flights, CrewRoster, CrewMembers)
- [ ] 10.3 Handle extraction and query errors gracefully
  - Catch Pydantic validation errors
  - Handle missing flight records
  - Return clear error messages
- [ ] 10.4 Test with sample natural language prompts
  - Test various prompt phrasings
  - Test date formats (relative, named, numeric)
  - Test error cases
- [ ] 10.5 Create unit tests for updated agent
  - Test structured output extraction
  - Test tool definitions
  - Test table access restrictions

**Acceptance Criteria**:

- Agent uses LangChain structured output (no custom parsing)
- Agent defines its own DynamoDB query tools
- Agent uses only authorized tables
- Tests pass with natural language input
- NO custom extraction functions exist

---

### Task 11: Update Maintenance Agent

**Validates**: Requirements 1.7, 2.1-2.7, 7.2

Update maintenance agent to use LangChain structured output for data extraction and define its own DynamoDB query tools.

**Subtasks**:

- [ ] 11.1 Update `src/agents/maintenance/agent.py`
  - Import FlightInfo Pydantic model
  - Use `llm.with_structured_output(FlightInfo)` to extract flight data from prompt
  - Define agent-specific DynamoDB query tools as LangChain Tool objects
  - Create tools for: query_flight, query_maintenance_work_orders, query_maintenance_staff, query_maintenance_roster, query_aircraft_availability
  - Update system prompt to explain agent's responsibility for extraction
- [ ] 11.2 Implement DynamoDB query tools
  - Use boto3 to query DynamoDB tables
  - Use GSIs from constants module
  - Only access authorized tables (flights, MaintenanceWorkOrders, MaintenanceStaff, MaintenanceRoster, AircraftAvailability)
- [ ] 11.3 Handle extraction and query errors gracefully
- [ ] 11.4 Test with sample natural language prompts
- [ ] 11.5 Create unit tests for updated agent

**Acceptance Criteria**:

- Agent uses LangChain structured output (no custom parsing)
- Agent defines its own DynamoDB query tools
- Agent uses only authorized tables
- Tests pass with natural language input
- NO custom extraction functions exist

---

### Task 12: Update Regulatory Agent

**Validates**: Requirements 1.7, 2.1-2.7, 7.3

Update regulatory agent to use LangChain structured output for data extraction and define its own DynamoDB query tools.

**Subtasks**:

- [ ] 12.1 Update `src/agents/regulatory/agent.py`
  - Import FlightInfo Pydantic model
  - Use `llm.with_structured_output(FlightInfo)` to extract flight data from prompt
  - Define agent-specific DynamoDB query tools as LangChain Tool objects
  - Create tools for: query_flight, query_crew_roster, query_maintenance_work_orders, query_weather
  - Update system prompt to explain agent's responsibility for extraction
- [ ] 12.2 Implement DynamoDB query tools
  - Use boto3 to query DynamoDB tables
  - Use GSIs from constants module
  - Only access authorized tables (flights, CrewRoster, MaintenanceWorkOrders, Weather)
- [ ] 12.3 Handle extraction and query errors gracefully
- [ ] 12.4 Test with sample natural language prompts
- [ ] 12.5 Create unit tests for updated agent

**Acceptance Criteria**:

- Agent uses LangChain structured output (no custom parsing)
- Agent defines its own DynamoDB query tools
- Agent uses only authorized tables
- Tests pass with natural language input
- NO custom extraction functions exist

---

### Task 13: Update Business Agents (Network, Guest Experience, Cargo, Finance)

**Validates**: Requirements 1.7, 2.1-2.7, 7.4-7.7

Update all business agents to use LangChain structured output for data extraction and define their own DynamoDB query tools.

**Subtasks**:

- [ ] 13.1 Update Network Agent (`src/agents/network/agent.py`)
  - Use `llm.with_structured_output(FlightInfo)` for extraction
  - Define DynamoDB query tools for authorized tables (flights, AircraftAvailability)
  - Use GSIs from constants module
- [ ] 13.2 Update Guest Experience Agent (`src/agents/guest_experience/agent.py`)
  - Use `llm.with_structured_output(FlightInfo)` for extraction
  - Define DynamoDB query tools for authorized tables (flights, bookings, Baggage)
  - Use GSIs from constants module
- [ ] 13.3 Update Cargo Agent (`src/agents/cargo/agent.py`)
  - Use `llm.with_structured_output(FlightInfo)` for extraction
  - Define DynamoDB query tools for authorized tables (flights, CargoFlightAssignments, CargoShipments)
  - Use GSIs from constants module
- [ ] 13.4 Update Finance Agent (`src/agents/finance/agent.py`)
  - Use `llm.with_structured_output(FlightInfo)` for extraction
  - Define DynamoDB query tools for authorized tables (flights, bookings, CargoFlightAssignments, MaintenanceWorkOrders)
  - Use GSIs from constants module
- [ ] 13.5 Test all agents with sample natural language prompts
- [ ] 13.6 Create unit tests for all updated agents

**Acceptance Criteria**:

- All business agents use LangChain structured output (no custom parsing)
- All agents define their own DynamoDB query tools
- All agents use only authorized tables
- Tests pass with natural language input
- NO custom extraction functions exist

---

### Task 14: Implement Revision Round Logic in Agents

**Validates**: Requirements 10.1-10.7

Update all agents to support revision round where they review other agents' recommendations.

**Subtasks**:

- [ ] 14.1 Update all agent implementations
  - Check payload.phase to determine initial vs revision
  - In revision phase, receive other_recommendations
  - Review other agents' findings
  - Revise own recommendation if warranted
  - Maintain domain priorities
- [ ] 14.2 Update system prompts to explain revision process
- [ ] 14.3 Add logic to determine if revision is needed
- [ ] 14.4 Test revision logic with mock collations
- [ ] 14.5 Create unit tests for revision behavior

**Acceptance Criteria**:

- All agents support revision phase
- Agents review other recommendations
- Agents revise when appropriate
- Tests validate revision logic

---

## Phase 4: Arbitrator Implementation

### Task 15: Create Arbitrator Agent

**Validates**: Requirements 11.1-11.7, 12.1-12.5, 13.1-13.5

Create a new arbitrator agent using Claude Opus 4.5 for sophisticated conflict resolution.

**Subtasks**:

- [ ] 15.1 Create `src/agents/arbitrator/` directory
- [ ] 15.2 Create `src/agents/arbitrator/agent.py`
  - Implement `arbitrate()` function
  - Use Claude Opus 4.5 with cross-region inference
  - Implement conflict identification logic
  - Implement safety priority enforcement
  - Implement conservative decision selection for safety conflicts
- [ ] 15.3 Implement AWS service discovery for Opus 4.5 endpoint
  - Use boto3 to discover cross-region inference endpoint
  - Fallback to Sonnet if Opus unavailable
  - Log warning on fallback
- [ ] 15.4 Create structured input/output schemas
  - Define `ArbitratorInput` schema
  - Define `ArbitratorOutput` schema with all required fields
  - Use Pydantic for validation
- [ ] 15.5 Implement arbitration logic
  - Identify conflicts between agent recommendations
  - Extract binding constraints from safety agents
  - Apply safety-first decision rules
  - Generate justification and reasoning
- [ ] 15.6 Create comprehensive system prompt for arbitrator
- [ ] 15.7 Create unit tests for arbitrator
- [ ] 15.8 Write property-based test for safety priority (Property 8)
- [ ] 15.9 Write property-based test for conservative resolution (Property 9)

**Acceptance Criteria**:

- Arbitrator uses Opus 4.5 with cross-region inference
- Structured input/output working
- Conflict resolution logic implemented
- Safety priority enforced
- Property tests validate safety invariants

---

## Phase 5: Integration and Testing

### Task 16: Implement End-to-End Integration Tests

**Validates**: Requirements 9, 10, 11, 15

Create comprehensive integration tests for the complete three-phase flow.

**Subtasks**:

- [ ] 16.1 Create `test/integration/test_three_phase_flow.py`
  - Test complete flow from natural language prompt to final decision
  - Verify agents use LangChain structured output for extraction
  - Verify phase execution order
  - Verify collation accuracy
  - Verify audit trail completeness
- [ ] 16.2 Create test scenarios
  - Simple disruption (no conflicts)
  - Safety vs business conflict
  - Safety vs safety conflict
  - Multiple agent failures
- [ ] 16.3 Write property-based test for execution order (Property 6)
- [ ] 16.4 Write property-based test for parallel execution (Property 7)
- [ ] 16.5 Write property-based test for audit trail completeness (Property 10)
- [ ] 16.6 Write property-based test for graceful degradation (Property 11)

**Acceptance Criteria**:

- End-to-end tests pass for all scenarios
- Property tests validate execution properties
- Audit trail complete for all executions

---

### Task 17: Create Performance and Load Tests

**Validates**: Design performance targets

Create tests to validate system meets performance targets.

**Subtasks**:

- [ ] 17.1 Create `test/performance/test_latency.py`
  - Measure phase execution times
  - Measure end-to-end latency
  - Measure database query latency
- [ ] 17.2 Create load test scenarios
  - Concurrent disruption analysis requests
  - High-frequency agent invocations
  - Database query load
- [ ] 17.3 Validate performance targets
  - Phase 1 < 10 seconds
  - Phase 2 < 10 seconds
  - Phase 3 < 5 seconds
  - End-to-end < 30 seconds
  - Database queries < 100ms
- [ ] 17.4 Create performance monitoring dashboard

**Acceptance Criteria**:

- Performance tests validate all targets met
- Load tests demonstrate system scalability
- Monitoring dashboard operational

---

### Task 18: Create Validation Test Suite

**Validates**: Requirements 5, 6

Create tests to validate permissions and data integrity.

**Subtasks**:

- [ ] 18.1 Create `test/validation/test_permissions.py`
  - Test agent table access restrictions
  - Test IAM role permissions
  - Test unauthorized access attempts
- [ ] 18.2 Create `test/validation/test_data_integrity.py`
  - Test foreign key relationships
  - Test required attributes
  - Test data type consistency
- [ ] 18.3 Run validation script on test environment
- [ ] 18.4 Fix any identified issues

**Acceptance Criteria**:

- Permission tests validate access restrictions
- Data integrity tests pass
- Validation script reports no issues

---

## Phase 6: Documentation and Deployment

### Task 19: Create Data Model Documentation

**Validates**: Requirements 17.1-17.7

Generate comprehensive documentation of the DynamoDB data model.

**Subtasks**:

- [ ] 19.1 Create script to discover deployed schema using AWS CLI
- [ ] 19.2 Generate `.kiro/steering/skymarshal-data-model.md`
  - Document all table names and primary keys
  - Document all GSI configurations
  - Document table relationships
  - Document query patterns for each agent
  - Include multi-table query examples
- [ ] 19.3 Add diagrams for complex relationships
- [ ] 19.4 Include example queries for each pattern
- [ ] 19.5 Review and validate documentation

**Acceptance Criteria**:

- Documentation generated from actual deployed schema
- All tables, GSIs, and relationships documented
- Query patterns explained with examples
- Documentation stored in steering directory

---

### Task 20: Deploy and Validate System

**Validates**: All requirements

Deploy the complete system and validate all functionality.

**Subtasks**:

- [ ] 20.1 Deploy database changes
  - Run GSI creation script
  - Validate GSI activation
  - Run data validation script
- [ ] 20.2 Deploy updated agents
  - Deploy all 7 updated agents
  - Deploy new arbitrator agent
  - Validate agent deployments
- [ ] 20.3 Deploy updated orchestrator
  - Deploy simplified orchestrator
  - Validate three-phase flow
  - Test with sample prompts
- [ ] 20.4 Run complete test suite
  - Unit tests
  - Integration tests
  - Property-based tests
  - Performance tests
- [ ] 20.5 Monitor system in production
  - Check execution metrics
  - Check error rates
  - Check performance targets
- [ ] 20.6 Create runbook for operations team

**Acceptance Criteria**:

- All components deployed successfully
- All tests passing
- System meets performance targets
- Monitoring and alerting operational
- Runbook complete

---

## Property-Based Test Summary

The following property-based tests validate the correctness properties defined in the design:

1. **Property 1 (Orchestrator Instruction Augmentation)**: Task 7.8
2. **Property 2 (Agent Autonomy)**: Task 7.9
3. **Property 3 (Flight Lookup Consistency)**: Task 8.4
4. **Property 4 (GSI Query Optimization)**: Task 5.6
5. **Property 5 (Agent Table Access Restriction)**: Task 6.6
6. **Property 6 (Three-Phase Execution Order)**: Task 16.3
7. **Property 7 (Parallel Agent Execution)**: Task 16.4
8. **Property 8 (Safety Priority Invariant)**: Task 15.8
9. **Property 9 (Conservative Conflict Resolution)**: Task 15.9
10. **Property 10 (Audit Trail Completeness)**: Task 16.5
11. **Property 11 (Graceful Degradation)**: Task 16.6
12. **Property 12 (Structured Output Consistency)**: Task 8.4

---

## Testing Framework

Use **Hypothesis** for property-based testing in Python:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=10))
def test_orchestrator_passthrough(user_prompt):
    """Property 1: Orchestrator passes prompt unchanged"""
    # Test implementation
```

## Execution Order

Tasks should be executed in phase order (1 → 6) to ensure dependencies are met. Within each phase, tasks can be parallelized where appropriate.

## Success Criteria

The implementation is complete when:

- All tasks marked as complete
- All unit tests passing
- All integration tests passing
- All property-based tests passing
- Performance targets met
- System deployed and operational
- Documentation complete
