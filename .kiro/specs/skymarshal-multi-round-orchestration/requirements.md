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

### Requirement 4: Database Schema Updates and GSI Requirements

**User Story:** As a system administrator, I want the database schema to support efficient flight-based queries with comprehensive GSI coverage, so that agents can quickly access relevant data without table scans.

#### Acceptance Criteria - Core GSIs (Currently Implemented)

1. THE Flights_Table SHALL have a GSI with flight_number and scheduled_departure as the composite key for flight lookup (flight-number-date-index)
2. THE Flights_Table SHALL have a GSI with aircraft_registration as the partition key for aircraft-based queries (aircraft-registration-index)
3. THE Bookings_Table SHALL have a GSI with flight_id as the partition key for efficient passenger queries (flight-id-index)
4. THE Bookings_Table SHALL have a GSI with passenger_id and flight_id as composite key for passenger booking history (passenger-flight-index)
5. THE Bookings_Table SHALL have a GSI with flight_id and booking_status as composite key for flight manifest queries (flight-status-index)
6. THE MaintenanceWorkOrders_Table SHALL have a GSI with aircraftRegistration as the partition key for aircraft-based maintenance queries (aircraft-registration-index)
7. THE CrewRoster_Table SHALL have a GSI with flight_id and position as composite key for crew roster queries (flight-position-index)
8. THE CargoFlightAssignments_Table SHALL have a GSI with flight_id and loading_status as composite key for cargo manifest queries (flight-loading-index)
9. THE CargoFlightAssignments_Table SHALL have a GSI with shipment_id as partition key for shipment tracking (shipment-index)
10. THE Baggage_Table SHALL have a GSI with booking_id as partition key for baggage queries (booking-index)
11. THE Baggage_Table SHALL have a GSI with current_location and baggage_status as composite key for location-based tracking (location-status-index)
12. THE MaintenanceRoster_Table SHALL have a GSI with workorder_id and shift_start as composite key for staff assignment queries (workorder-shift-index)

#### Acceptance Criteria - Priority 1 GSIs (Critical for Agent Efficiency)

13. THE CrewRoster_Table SHALL have a GSI with crew_id and duty_date as composite key for crew duty history queries (crew-duty-date-index)
    - Purpose: Enable efficient FDP/rest calculations across multiple flights
    - Query Pattern: Find all duties for crew member within date range
    - Estimated Impact: 500+ queries/day, 50x performance improvement
    - Required By: Crew Compliance Agent for duty limit validation

14. THE Flights_Table SHALL have a GSI with aircraft_registration and scheduled_departure as composite key for aircraft rotation queries (aircraft-rotation-index)
    - Purpose: Enable complete aircraft rotation retrieval in single query
    - Query Pattern: Find all flights for aircraft ordered by departure time
    - Estimated Impact: 200+ queries/day, 100x performance improvement
    - Required By: Network Agent for propagation chain analysis

15. THE Passengers_Table SHALL have a GSI with frequent_flyer_tier_id and booking_date as composite key for elite passenger identification (passenger-elite-tier-index)
    - Purpose: Enable efficient VIP passenger identification and prioritization
    - Query Pattern: Find all elite passengers on flight or within date range
    - Estimated Impact: 300+ queries/day, 50x performance improvement
    - Required By: Guest Experience Agent for passenger prioritization

#### Acceptance Criteria - Priority 2 GSIs (High Value for Specific Use Cases)

16. THE Flights_Table SHALL have a GSI with destination_airport_id and scheduled_arrival as composite key for curfew compliance checks (airport-curfew-index)
    - Purpose: Enable efficient curfew compliance validation
    - Query Pattern: Find all flights arriving at airport near curfew time
    - Estimated Impact: 100+ queries/day
    - Required By: Regulatory Agent for curfew validation

17. THE CargoShipments_Table SHALL have a GSI with commodity_type_id and temperature_requirement as composite key for cold chain identification (cargo-temperature-index)
    - Purpose: Enable efficient temperature-sensitive cargo identification
    - Query Pattern: Find all cold chain shipments on flight or within time window
    - Estimated Impact: 150+ queries/day
    - Required By: Cargo Agent for special handling requirements

18. THE MaintenanceWorkOrders_Table SHALL have a GSI with aircraft_registration and scheduled_date as composite key for maintenance conflict detection (aircraft-maintenance-date-index)
    - Purpose: Enable efficient scheduled maintenance conflict detection
    - Query Pattern: Find all scheduled maintenance for aircraft within date range
    - Estimated Impact: 80+ queries/day
    - Required By: Maintenance Agent for conflict detection

#### Acceptance Criteria - Priority 3 GSIs (Nice-to-Have for Future Optimization)

19. THE CargoShipments_Table MAY have a GSI with shipment_value (DESC) for high-value cargo prioritization (cargo-value-index)
    - Purpose: Enable efficient high-value cargo identification
    - Query Pattern: Find all high-value shipments above threshold
    - Estimated Impact: 50+ queries/day
    - Required By: Cargo Agent for prioritization decisions

20. THE Flights_Table MAY have a GSI with flight_id and total_revenue for revenue impact calculations (flight-revenue-index)
    - Purpose: Enable efficient revenue impact analysis
    - Query Pattern: Calculate total revenue for flight or route
    - Estimated Impact: 40+ queries/day
    - Required By: Finance Agent for cost-benefit analysis

#### Acceptance Criteria - Data Relationships and Query Patterns

21. THE System SHALL associate MaintenanceWorkOrders with flights through aircraftRegistration (flights.aircraft_registration = MaintenanceWorkOrders.aircraftRegistration)
22. THE System SHALL access Baggage data through bookings (bookings.flight_id → Baggage.booking_id via booking-index GSI)
23. THE System SHALL access CargoShipments through CargoFlightAssignments (CargoFlightAssignments.flight_id → CargoShipments.shipment_id)
24. THE System SHALL access CrewMembers through CrewRoster (CrewRoster.flight_id → CrewMembers.crew_id)
25. THE System SHALL ensure all query paths are optimized using GSIs to avoid table scans
26. WHEN schema updates are applied, THE System SHALL only create new GSIs without modifying existing table structures or data
27. WHEN GSIs are created, THE System SHALL wait for them to become ACTIVE before proceeding
28. THE System SHALL validate that all GSIs are in ACTIVE status before agent invocation
29. THE System SHALL monitor GSI consumed capacity and throttling metrics
30. THE System SHALL log all queries that result in table scans for optimization review

#### Acceptance Criteria - GSI Creation Retry Logic and Error Handling

31. WHEN a GSI creation fails, THE System SHALL implement exponential backoff retry logic with up to 5 retry attempts
32. THE System SHALL use exponential backoff delays for retries: 30 seconds, 60 seconds, 120 seconds, 240 seconds, 480 seconds
33. WHEN a GSI creation fails due to ResourceInUseException, THE System SHALL wait for the table to become available and retry immediately
34. WHEN a GSI creation fails due to LimitExceededException, THE System SHALL wait 5 minutes and retry
35. WHEN a GSI creation fails due to ValidationException with attribute definition conflicts, THE System SHALL merge existing attribute definitions and retry
36. WHEN a GSI creation fails due to ThrottlingException, THE System SHALL apply exponential backoff and retry
37. WHEN a GSI creation fails due to InternalServerError, THE System SHALL apply exponential backoff and retry
38. THE System SHALL log each retry attempt with timestamp, failure reason, retry count, and next retry delay
39. WHEN all retry attempts are exhausted for a GSI, THE System SHALL generate a detailed failure report containing:
    - GSI name and table name
    - All failure reasons encountered across all attempts
    - Retry history with timestamps
    - Current table status and existing GSIs
    - Recommended manual intervention steps
40. THE System SHALL continue creating remaining GSIs even if one GSI fails after all retries
41. THE System SHALL generate a comprehensive summary report after GSI creation showing:
    - Successfully created GSIs with creation times
    - Failed GSIs with failure reasons and retry counts
    - GSIs that already existed (skipped)
    - Total execution time
    - Success rate percentage
42. WHEN GSI creation is interrupted (script crash, network failure, manual termination), THE System SHALL support resume capability to continue from last successful GSI
43. THE System SHALL maintain a state file (`.gsi_creation_state.json`) tracking:
    - GSI creation progress for each GSI
    - Status: pending, in_progress, active, failed
    - Creation timestamp and retry count
    - Last error message
44. THE System SHALL validate GSI activation status with retry logic:
    - Poll GSI status every 10 seconds
    - Timeout after 15 minutes (90 polling attempts)
    - Retry status query up to 3 times if the query itself fails
    - Log activation progress with elapsed time
45. WHEN a GSI reaches ACTIVE status, THE System SHALL perform a validation query to confirm the GSI is functional
46. WHEN a validation query fails on an ACTIVE GSI, THE System SHALL mark the GSI as "ACTIVE but non-functional" and recommend investigation
47. WHEN a validation query uses table scan instead of GSI, THE System SHALL mark the GSI as "ACTIVE but not used" and recommend schema review
48. THE System SHALL support rollback of partially created GSIs with retry logic:
    - Retry delete operations up to 3 times with 30-second delays
    - Handle ResourceInUseException during delete by waiting and retrying
    - Generate rollback report showing deleted GSIs and failures
49. THE System SHALL save all reports to `scripts/gsi_creation_reports/` directory with timestamps
50. THE System SHALL provide a `--resume` flag to continue interrupted GSI creation from state file
51. THE System SHALL provide a `--retry-failed` flag to retry only previously failed GSIs from state file
52. THE System SHALL clean up state file automatically on successful completion of all GSIs

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

### Requirement 7.1: Agent-Specific Query Patterns and GSI Usage

**User Story:** As an agent developer, I want to understand which GSIs my agent should use for each query pattern, so that I can implement efficient database access without table scans.

#### Acceptance Criteria - Crew Compliance Agent Query Patterns

1. WHEN querying crew roster for a flight, THE Crew_Compliance_Agent SHALL use flight-position-index GSI on CrewRoster table
   - Query Pattern: CrewRoster WHERE flight_id = ? AND position = ?
   - Expected Latency: ~15-20ms
   - Query Volume: High (every disruption analysis)

2. WHEN querying crew member details, THE Crew_Compliance_Agent SHALL use primary key lookup on CrewMembers table
   - Query Pattern: CrewMembers WHERE crew_id = ?
   - Expected Latency: ~5-10ms
   - Query Volume: High (multiple crew per flight)

3. WHEN searching for crew duty history, THE Crew_Compliance_Agent SHALL use crew-duty-date-index GSI on CrewRoster table
   - Query Pattern: CrewRoster WHERE crew_id = ? AND duty_date BETWEEN ? AND ?
   - Expected Latency: ~15-20ms
   - Query Volume: Medium (FDP calculations)
   - Status: Priority 1 GSI (to be created)

4. WHEN searching for qualified crew replacements, THE Crew_Compliance_Agent SHALL use crew-qualification-index GSI on CrewMembers table
   - Query Pattern: CrewMembers WHERE aircraft_type_id = ? AND qualification_expiry > ?
   - Expected Latency: ~20-30ms
   - Query Volume: Low (only when crew replacement needed)
   - Status: Future enhancement

#### Acceptance Criteria - Maintenance Agent Query Patterns

5. WHEN querying aircraft availability, THE Maintenance_Agent SHALL use composite key lookup on AircraftAvailability table
   - Query Pattern: AircraftAvailability WHERE aircraft_registration = ? AND valid_from >= ?
   - Expected Latency: ~10-15ms
   - Query Volume: High (every disruption analysis)

6. WHEN querying maintenance work orders, THE Maintenance_Agent SHALL use aircraft-registration-index GSI on MaintenanceWorkOrders table
   - Query Pattern: MaintenanceWorkOrders WHERE aircraft_registration = ?
   - Expected Latency: ~15-20ms
   - Query Volume: High (every disruption analysis)

7. WHEN querying maintenance roster, THE Maintenance_Agent SHALL use workorder-shift-index GSI on MaintenanceRoster table
   - Query Pattern: MaintenanceRoster WHERE workorder_id = ? AND shift_start >= ?
   - Expected Latency: ~15-20ms
   - Query Volume: Medium (when work orders exist)

8. WHEN checking for maintenance conflicts, THE Maintenance_Agent SHALL use aircraft-maintenance-date-index GSI on MaintenanceWorkOrders table
   - Query Pattern: MaintenanceWorkOrders WHERE aircraft_registration = ? AND scheduled_date BETWEEN ? AND ?
   - Expected Latency: ~20-30ms
   - Query Volume: Medium (conflict detection)
   - Status: Priority 2 GSI (to be created)

#### Acceptance Criteria - Regulatory Agent Query Patterns

9. WHEN querying weather forecasts, THE Regulatory_Agent SHALL use composite key lookup on Weather table
   - Query Pattern: Weather WHERE airport_code = ? AND forecast_time >= ?
   - Expected Latency: ~10-15ms
   - Query Volume: High (origin and destination weather)

10. WHEN querying flight details, THE Regulatory_Agent SHALL use primary key lookup on Flights table
    - Query Pattern: Flights WHERE flight_id = ?
    - Expected Latency: ~5-10ms
    - Query Volume: High (every disruption analysis)

11. WHEN checking curfew compliance, THE Regulatory_Agent SHALL use airport-curfew-index GSI on Flights table
    - Query Pattern: Flights WHERE destination_airport_id = ? AND scheduled_arrival BETWEEN ? AND ?
    - Expected Latency: ~20-30ms
    - Query Volume: Medium (curfew-sensitive airports)
    - Status: Priority 2 GSI (to be created)

#### Acceptance Criteria - Network Agent Query Patterns

12. WHEN querying inbound flight impact, THE Network_Agent SHALL use primary key lookup on InboundFlightImpact table
    - Query Pattern: InboundFlightImpact WHERE scenario = ?
    - Expected Latency: ~10-15ms
    - Query Volume: Medium (scenario-based analysis)

13. WHEN querying aircraft rotation, THE Network_Agent SHALL use aircraft-rotation-index GSI on Flights table
    - Query Pattern: Flights WHERE aircraft_registration = ? ORDER BY scheduled_departure
    - Expected Latency: ~20-30ms
    - Query Volume: High (every disruption analysis)
    - Status: Priority 1 GSI (to be created)

14. WHEN querying flight by number and date, THE Network_Agent SHALL use flight-number-date-index GSI on Flights table
    - Query Pattern: Flights WHERE flight_number = ? AND scheduled_departure = ?
    - Expected Latency: ~15-20ms
    - Query Volume: High (initial flight lookup)

#### Acceptance Criteria - Guest Experience Agent Query Patterns

15. WHEN querying passenger bookings, THE Guest_Experience_Agent SHALL use passenger-flight-index GSI on Bookings table
    - Query Pattern: Bookings WHERE passenger_id = ? AND flight_id = ?
    - Expected Latency: ~15-20ms
    - Query Volume: Medium (passenger history queries)

16. WHEN querying flight bookings, THE Guest_Experience_Agent SHALL use flight-status-index GSI on Bookings table
    - Query Pattern: Bookings WHERE flight_id = ? AND booking_status = ?
    - Expected Latency: ~20-30ms
    - Query Volume: High (passenger manifest queries)

17. WHEN querying passenger baggage, THE Guest_Experience_Agent SHALL use booking-index GSI on Baggage table
    - Query Pattern: Baggage WHERE booking_id = ?
    - Expected Latency: ~10-15ms
    - Query Volume: High (baggage tracking)

18. WHEN querying passenger details, THE Guest_Experience_Agent SHALL use primary key lookup on Passengers table
    - Query Pattern: Passengers WHERE passenger_id = ?
    - Expected Latency: ~5-10ms
    - Query Volume: High (passenger profile queries)

19. WHEN identifying elite passengers, THE Guest_Experience_Agent SHALL use passenger-elite-tier-index GSI on Passengers table
    - Query Pattern: Passengers WHERE frequent_flyer_tier_id = ? AND booking_date >= ?
    - Expected Latency: ~20-30ms
    - Query Volume: Medium (VIP identification)
    - Status: Priority 1 GSI (to be created)

20. WHEN tracking baggage by location, THE Guest_Experience_Agent SHALL use location-status-index GSI on Baggage table
    - Query Pattern: Baggage WHERE current_location = ? AND baggage_status = ?
    - Expected Latency: ~15-20ms
    - Query Volume: Low (mishandled baggage tracking)

#### Acceptance Criteria - Cargo Agent Query Patterns

21. WHEN tracking cargo shipments, THE Cargo_Agent SHALL use shipment-index GSI on CargoFlightAssignments table
    - Query Pattern: CargoFlightAssignments WHERE shipment_id = ?
    - Expected Latency: ~15-20ms
    - Query Volume: Medium (shipment tracking)

22. WHEN querying flight cargo manifest, THE Cargo_Agent SHALL use flight-loading-index GSI on CargoFlightAssignments table
    - Query Pattern: CargoFlightAssignments WHERE flight_id = ? AND loading_status = ?
    - Expected Latency: ~20-30ms
    - Query Volume: High (cargo manifest queries)

23. WHEN querying cargo shipment details, THE Cargo_Agent SHALL use primary key lookup on CargoShipments table
    - Query Pattern: CargoShipments WHERE shipment_id = ?
    - Expected Latency: ~5-10ms
    - Query Volume: High (shipment details)

24. WHEN identifying cold chain shipments, THE Cargo_Agent SHALL use cargo-temperature-index GSI on CargoShipments table
    - Query Pattern: CargoShipments WHERE commodity_type_id = ? AND temperature_requirement IS NOT NULL
    - Expected Latency: ~20-30ms
    - Query Volume: Medium (special handling identification)
    - Status: Priority 2 GSI (to be created)

25. WHEN prioritizing high-value cargo, THE Cargo_Agent SHALL use cargo-value-index GSI on CargoShipments table
    - Query Pattern: CargoShipments WHERE shipment_value > ? ORDER BY shipment_value DESC
    - Expected Latency: ~20-30ms
    - Query Volume: Low (prioritization decisions)
    - Status: Priority 3 GSI (future enhancement)

#### Acceptance Criteria - Finance Agent Query Patterns

26. WHEN querying flight for cost analysis, THE Finance_Agent SHALL use primary key lookup on Flights table
    - Query Pattern: Flights WHERE flight_id = ?
    - Expected Latency: ~5-10ms
    - Query Volume: High (every disruption analysis)

27. WHEN calculating passenger revenue, THE Finance_Agent SHALL use flight-id-index GSI on Bookings table
    - Query Pattern: Bookings WHERE flight_id = ?
    - Expected Latency: ~20-30ms
    - Query Volume: High (revenue calculations)

28. WHEN calculating cargo revenue, THE Finance_Agent SHALL use flight-loading-index GSI on CargoFlightAssignments table
    - Query Pattern: CargoFlightAssignments WHERE flight_id = ?
    - Expected Latency: ~20-30ms
    - Query Volume: High (revenue calculations)

29. WHEN calculating maintenance costs, THE Finance_Agent SHALL use aircraft-registration-index GSI on MaintenanceWorkOrders table
    - Query Pattern: MaintenanceWorkOrders WHERE aircraft_registration = ?
    - Expected Latency: ~15-20ms
    - Query Volume: Medium (cost calculations)

#### Acceptance Criteria - Query Performance Monitoring

30. THE System SHALL log all database queries with execution time and GSI usage
31. THE System SHALL alert when queries exceed 100ms latency threshold
32. THE System SHALL identify queries that result in table scans and log them for optimization
33. THE System SHALL track GSI consumed capacity and throttling events
34. THE System SHALL generate weekly reports on query performance by agent
35. WHEN a table scan is detected, THE System SHALL recommend appropriate GSI creation
36. WHEN GSI throttling occurs, THE System SHALL recommend capacity adjustments or query optimization

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
