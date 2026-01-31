# Requirements Document

## Introduction

This document specifies the requirements for rearchitecting the SkyMarshal agent system to implement a multi-round orchestration flow with improved data access patterns, agent tool organization, and a new arbitrator agent for conflict resolution. The system will transition from a two-phase execution model to a three-phase process with initial recommendations, revision rounds, and final arbitration.

## Glossary

- **Orchestrator**: The main coordination component that manages agent invocations and collates responses
- **Agent**: A specialized AI component that analyzes specific aspects of flight disruptions (not user-facing, invoked only by the orchestrator)
- **Safety_Agent**: Agents responsible for safety-critical analysis (crew compliance, maintenance, regulatory)
- **Business_Agent**: Agents responsible for operational and financial analysis (network, guest experience, cargo, finance)
- **Arbitrator**: A specialized agent that resolves conflicts and makes final decisions
- **End_User**: The disruption manager who provides flight number, date, and disruption event description
- **Flight_ID**: Unique identifier for a flight instance (combination of flight number and date)
- **GSI**: Global Secondary Index in DynamoDB for efficient querying
- **Disruption_Event**: An incident affecting flight operations requiring analysis (e.g., delay, mechanical failure, rerouted plane)
- **Binding_Constraint**: A non-negotiable requirement from safety agents that must be satisfied
- **Revision_Round**: The second phase where agents review and adjust their recommendations
- **Collation**: Aggregated collection of all agent recommendations
- **Cross_Region_Inference**: AWS Bedrock capability for using models across regions

## Requirements

### Requirement 1: User Input Handling

**User Story:** As a disruption manager, I want to provide flight number, date, and disruption event details in a natural language prompt, so that the system can analyze the specific incident without requiring strict formatting or structured fields.

#### Acceptance Criteria

1. THE End_User SHALL provide input as a single natural language prompt containing flight number, date, and disruption description
2. THE End_User MAY use any natural phrasing (e.g., "Flight EY123 on January 20th had a mechanical failure", "EY456 yesterday was delayed due to weather")
3. THE End_User SHALL include a flight number in the format EY followed by 3 or 4 digits (e.g., EY123, EY1234)
4. THE End_User MAY provide a date in any common format including:
   - Numeric formats (dd/mm/yyyy, dd-mm-yy, yyyy-mm-dd, mm/dd/yyyy)
   - Named formats (20 Jan, 20th January, January 20th 2026)
   - Relative dates (yesterday, today, tomorrow)
5. THE End_User SHALL provide a disruption event description (e.g., delay, mechanical failure, rerouted plane, weather diversion)
6. THE Orchestrator SHALL pass the complete natural language prompt to all agents without parsing or extracting fields
7. THE Orchestrator SHALL NOT require tools for extraction, validation, or database access - it operates purely on natural language prompts
8. THE Agents SHALL be responsible for extracting flight number, date, and disruption details from the natural language prompt using their LLM reasoning capabilities
9. THE Agents SHALL have access to date/time lookup tools to determine the current date and resolve relative dates
10. THE Agents SHALL parse dates and convert them to the format required by DynamoDB queries
11. THE Agents SHALL assume European date format (dd/mm/yyyy) when numeric format is ambiguous
12. THE End_User SHALL NOT be able to directly query operational data (crew manifests, cargo details, passenger lists)
13. WHEN any required input is missing from the prompt, THE Agent SHALL return a message requesting the missing information
14. WHEN the flight number format is invalid, THE Agent SHALL return a message specifying the correct format
15. WHEN the date cannot be parsed, THE Agent SHALL return a message requesting clarification
16. WHEN all required inputs are extracted and validated, THE Agent SHALL proceed with flight lookup and analysis

### Requirement 2: Flight Search and Identification

**User Story:** As an agent, I want to search for flights by flight number and date extracted from the user prompt, so that I can retrieve all relevant operational data for the disruption event.

#### Acceptance Criteria

1. THE Agent SHALL extract the flight number and date from the natural language prompt using its LLM reasoning capabilities
2. THE Agent SHALL use its database query tools to retrieve the flight record using a DynamoDB GSI
3. WHEN a valid flight number and date are extracted, THE Agent SHALL retrieve the flight record using a DynamoDB GSI
4. WHEN a flight is found, THE Agent SHALL use the flight_id for subsequent queries
5. WHEN a flight is not found, THE Agent SHALL return a descriptive error message indicating the flight does not exist
6. THE Agent SHALL use the flight_id to query related operational data (crew, maintenance, cargo, passengers)
7. THE Agent SHALL include the user-provided disruption event description in its analysis
8. THE Orchestrator SHALL NOT perform any flight lookups or data queries - all lookups are performed by agents
9. THE Orchestrator SHALL NOT require tools for extraction or validation - agents handle all data operations

### Requirement 3: Flight-Based Data Association

**User Story:** As an agent (invoked by the orchestrator), I want to query operational data using flight_id, so that I can access all related crew, maintenance, cargo, and passenger information.

#### Acceptance Criteria

1. WHEN an agent queries crew data with a flight_id, THE CrewRoster_Table SHALL return all crew members using the flight-position-index GSI
2. WHEN an agent queries booking data with a flight_id, THE Bookings_Table SHALL return all passenger bookings using the flight_id GSI
3. WHEN an agent queries cargo data with a flight_id, THE CargoFlightAssignments_Table SHALL return cargo assignments using the flight-loading-index GSI, then THE System SHALL retrieve CargoShipments details using shipment_id
4. WHEN an agent queries maintenance data with a flight_id, THE System SHALL first retrieve the aircraft_registration from flights, then query MaintenanceWorkOrders using the aircraftRegistration GSI
5. WHEN an agent queries baggage data with a flight_id, THE System SHALL first query bookings using the flight_id GSI, then query Baggage using the booking-index GSI with booking_id values
6. THE System SHALL ensure all query paths are optimized using GSIs to avoid table scans
7. THE End_User SHALL NOT have direct access to these query operations

### Requirement 4: Database Schema Updates

**User Story:** As a system administrator, I want the database schema to support efficient flight-based queries, so that agents can quickly access relevant data.

#### Acceptance Criteria

1. THE Flights_Table SHALL have a GSI with flight_number and scheduled_departure as the composite key for flight lookup
2. THE Flights_Table SHALL have a GSI with aircraftRegistration as the partition key for aircraft-based queries
3. THE Bookings_Table SHALL have a GSI with flight_id as the partition key for efficient passenger queries
4. THE MaintenanceWorkOrders_Table SHALL have a GSI with aircraftRegistration as the partition key for aircraft-based maintenance queries
5. THE System SHALL associate MaintenanceWorkOrders with flights through aircraftRegistration (flights.aircraft_registration = MaintenanceWorkOrders.aircraftRegistration)
6. THE System SHALL access Baggage data through bookings (bookings.flight_id → Baggage.booking_id via booking-index GSI)
7. THE System SHALL access CargoShipments through CargoFlightAssignments (CargoFlightAssignments.flight_id → CargoShipments.shipment_id)
8. THE CrewRoster_Table SHALL maintain its existing flight-position-index GSI
9. THE CargoFlightAssignments_Table SHALL maintain its existing flight-loading-index GSI
10. THE Baggage_Table SHALL maintain its existing booking-index GSI
11. WHEN schema updates are applied, THE System SHALL only create new GSIs without modifying existing table structures or data
12. WHEN GSIs are created, THE System SHALL wait for them to become ACTIVE before proceeding

### Requirement 5: Database Permissions Validation

**User Story:** As a security administrator, I want to validate that all agents have correct DynamoDB permissions, so that the system operates securely and reliably.

#### Acceptance Criteria

1. THE Validation_Script SHALL verify each agent has read access to its required tables
2. THE Validation_Script SHALL verify the orchestrator has access to all tables
3. THE Validation_Script SHALL verify the arbitrator has read access to all agent outputs
4. WHEN permission issues are detected, THE Validation_Script SHALL report specific missing permissions
5. THE Validation_Script SHALL validate IAM roles and policies for AgentCore deployment

### Requirement 6: Database Data Integrity Validation

**User Story:** As a data administrator, I want to validate all data in DynamoDB tables and verify GSI configurations, so that I can identify and fix inconsistencies before they cause operational issues.

#### Acceptance Criteria

1. THE Validation_Script SHALL check all required attributes are present in each table record
2. THE Validation_Script SHALL verify all foreign key relationships are valid (e.g., flight_id references exist)
3. THE Validation_Script SHALL identify orphaned records with no valid associations
4. THE Validation_Script SHALL validate data type consistency for all attributes
5. THE Validation_Script SHALL verify all required GSIs exist on their respective tables
6. THE Validation_Script SHALL check that all GSIs are in ACTIVE status
7. THE Validation_Script SHALL validate GSI key schemas match the design requirements
8. THE Validation_Script SHALL test that sample queries use GSIs and do not perform table scans
9. WHEN discrepancies are found, THE Validation_Script SHALL generate a detailed report with record identifiers and specific issues

### Requirement 7: Agent Tool Organization

**User Story:** As a system architect, I want agent tools organized logically by agent responsibility, so that the system is maintainable and agents have appropriate data access.

**ARCHITECTURE NOTE**: Each agent defines its own DynamoDB query tools directly in its agent.py file as LangChain Tool objects. There is NO centralized tool factory or shared tool module (no `src/database/tools.py`). Tools are co-located with agent logic for better encapsulation.

#### Acceptance Criteria

1. THE Crew_Compliance_Agent SHALL define tools that access only flights, CrewRoster, and CrewMembers tables
2. THE Maintenance_Agent SHALL define tools that access only flights, MaintenanceWorkOrders, MaintenanceStaff, MaintenanceRoster, and AircraftAvailability tables
3. THE Regulatory_Agent SHALL define tools that access only flights, CrewRoster, MaintenanceWorkOrders, and Weather tables
4. THE Network_Agent SHALL define tools that access only flights and AircraftAvailability tables
5. THE Guest_Experience_Agent SHALL define tools that access only flights, bookings, and Baggage tables
6. THE Cargo_Agent SHALL define tools that access only flights, CargoFlightAssignments, and CargoShipments tables
7. THE Finance_Agent SHALL define tools that access only flights, bookings, CargoFlightAssignments, and MaintenanceWorkOrders tables
8. EACH Agent SHALL define its tools as LangChain Tool objects within its own agent.py file
9. EACH Agent's tools SHALL use boto3 directly to query DynamoDB tables using appropriate GSIs
10. WHEN an agent attempts to access unauthorized tables, THE Tool implementation SHALL deny the request with a clear error message

### Requirement 8: Agent Table Constants

**User Story:** As a developer, I want table names defined as constants for each agent, so that configuration is centralized and changes are easy to manage.

#### Acceptance Criteria

1. THE System SHALL define table name constants in a centralized configuration module
2. WHEN an agent is initialized, THE System SHALL load only the table constants for that agent
3. THE System SHALL validate table constants against actual DynamoDB table names at startup
4. WHEN table names change, THE System SHALL require updates only in the constants module
5. THE System SHALL use type-safe constants to prevent runtime errors

### Requirement 9: Phase 1 - Initial Recommendations

**User Story:** As an orchestrator, I want to collect initial recommendations from all agents in parallel, so that I can efficiently gather diverse perspectives on the disruption.

#### Acceptance Criteria

1. WHEN a disruption event is received, THE Orchestrator SHALL invoke all agents asynchronously with the raw natural language prompt
2. THE Orchestrator SHALL NOT parse, extract, or validate any fields from the user prompt
3. THE Orchestrator SHALL NOT perform any database lookups or queries
4. THE Orchestrator SHALL pass the complete user prompt to each agent unchanged
5. THE Agents SHALL be responsible for extracting flight information and performing all necessary lookups
6. THE Orchestrator SHALL wait for all agents to complete or timeout (maximum 30 seconds per agent)
7. WHEN an agent times out, THE Orchestrator SHALL log the timeout and continue with available responses
8. THE Orchestrator SHALL collate all initial recommendations grouped by agent name

### Requirement 10: Phase 2 - Revision Round

**User Story:** As an agent, I want to review other agents' recommendations and revise my own, so that I can adjust my analysis based on cross-functional insights.

#### Acceptance Criteria

1. WHEN the revision round begins, THE Orchestrator SHALL send all initial recommendations to each agent
2. WHEN an agent receives the collation, THE Agent SHALL review recommendations from other agents
3. WHEN reviewing recommendations, THE Agent SHALL prioritize its own domain constraints and requirements
4. THE Agent SHALL revise its recommendation if other agents' insights warrant changes
5. THE Agent SHALL maintain its original recommendation if no revision is needed
6. THE Orchestrator SHALL invoke all agents asynchronously during the revision round
7. THE Orchestrator SHALL collate all revised recommendations grouped by agent name

### Requirement 11: Phase 3 - Arbitration

**User Story:** As an arbitrator, I want to resolve conflicts between agent recommendations and make a final decision, so that the system provides a single coherent response.

#### Acceptance Criteria

1. WHEN the arbitration phase begins, THE Orchestrator SHALL invoke the Arbitrator with all revised recommendations
2. THE Arbitrator SHALL identify conflicting requirements between agents
3. WHEN safety agents provide binding constraints, THE Arbitrator SHALL treat them as non-negotiable
4. WHEN multiple safety agents conflict, THE Arbitrator SHALL select the most conservative decision
5. THE Arbitrator SHALL prioritize flight cancellation or rerouting over operational compromises when safety is at risk
6. THE Arbitrator SHALL generate a final decision with recommendations, justification, and reasoning
7. THE Arbitrator SHALL return structured output to the Orchestrator

### Requirement 12: Arbitrator Agent Implementation

**User Story:** As a system architect, I want a dedicated arbitrator agent using advanced reasoning capabilities, so that conflict resolution is sophisticated and reliable.

#### Acceptance Criteria

1. THE Arbitrator SHALL use Claude Opus 4.5 with cross-region inference for enhanced reasoning
2. THE Arbitrator SHALL be invoked as a tool with structured input schema
3. THE Arbitrator SHALL return structured output conforming to a predefined schema
4. THE Arbitrator SHALL use AWS service discovery to locate the Opus 4.5 cross-region inference endpoint
5. WHEN the endpoint is unavailable, THE Arbitrator SHALL fall back to the default Sonnet model with a warning

### Requirement 13: Safety-First Decision Making

**User Story:** As a safety officer, I want safety agent decisions to always override business considerations, so that flight operations never compromise passenger or crew safety.

#### Acceptance Criteria

1. WHEN a safety agent recommends flight cancellation, THE Arbitrator SHALL not override this decision
2. WHEN a safety agent identifies a binding constraint, THE Arbitrator SHALL ensure the final decision satisfies it
3. WHEN business agents conflict with safety agents, THE Arbitrator SHALL prioritize safety recommendations
4. THE Arbitrator SHALL document all safety overrides in the final decision rationale
5. THE Arbitrator SHALL assign maximum confidence scores to safety-driven decisions

### Requirement 14: Subagent Usage for Context Management

**User Story:** As a system architect, I want to use subagents for isolated tasks, so that context usage is minimized and agent prompts remain focused.

#### Acceptance Criteria

1. WHEN an agent needs to perform a discrete subtask, THE Agent SHALL invoke a subagent
2. THE Subagent SHALL operate with isolated context separate from the parent agent
3. WHEN a subagent completes, THE Agent SHALL receive only the relevant output without full context pollution
4. THE System SHALL support nested subagent invocations up to 3 levels deep
5. THE System SHALL track subagent invocations for debugging and audit purposes

### Requirement 15: Audit Trail and Explainability

**User Story:** As a compliance officer, I want complete audit trails for all decisions, so that I can demonstrate regulatory compliance and explain system behavior.

#### Acceptance Criteria

1. THE System SHALL log all agent invocations with timestamps and input parameters
2. THE System SHALL log all agent responses with confidence scores and reasoning
3. THE System SHALL log all arbitrator decisions with conflict resolutions and justifications
4. THE System SHALL preserve the complete decision chain from initial recommendations through final arbitration
5. WHEN a decision is queried, THE System SHALL provide the full audit trail in human-readable format

### Requirement 16: Error Handling and Fallbacks

**User Story:** As a system operator, I want graceful error handling and conservative fallbacks, so that the system remains reliable even when components fail.

#### Acceptance Criteria

1. WHEN an agent fails to respond, THE Orchestrator SHALL continue with available agent responses
2. WHEN the arbitrator fails, THE Orchestrator SHALL apply the most conservative safety recommendation
3. WHEN database queries fail, THE Agent SHALL report insufficient data and recommend manual review
4. WHEN the cross-region inference endpoint is unavailable, THE Arbitrator SHALL fall back to the default model
5. THE System SHALL log all errors with sufficient detail for debugging and recovery

### Requirement 17: Data Model Documentation

**User Story:** As a developer, I want comprehensive documentation of the SkyMarshal data model, so that I can understand table relationships and query patterns.

#### Acceptance Criteria

1. THE System SHALL provide a steering document describing the complete DynamoDB data model
2. THE Documentation SHALL include all table names, primary keys, and GSI configurations
3. THE Documentation SHALL describe the relationships between tables (e.g., flights → bookings via flight_id)
4. THE Documentation SHALL specify the query patterns for each agent's data access
5. THE Documentation SHALL include examples of multi-table queries (e.g., flight → aircraft_registration → maintenance)
6. THE Documentation SHALL be generated using AWS CLI to discover the actual deployed schema
7. THE Documentation SHALL be stored in .kiro/steering/skymarshal-data-model.md
