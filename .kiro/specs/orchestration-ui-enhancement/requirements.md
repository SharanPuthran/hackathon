# Requirements Document

## Introduction

The SkyMarshal frontend UI needs to be enhanced to properly display the three-phase orchestration workflow returned by the AgentCore Runtime API. The current implementation uses mock data and does not correctly parse the actual API response structure, which contains nested phase data (phase1_initial, phase2_revision, phase3_arbitration) with detailed agent responses and solution options. This enhancement will enable the UI to visualize the complete orchestration process with proper loading states, sequential agent message display, and interactive solution selection.

## Glossary

- **OrchestrationView**: The main React component that displays the agent orchestration workflow
- **AgentMessage**: React component that renders individual agent assessment messages
- **ArbitratorPanel**: Right-side panel component that displays live synthesis and solution options
- **Phase1_Initial**: First phase of orchestration containing initial agent assessments
- **Phase2_Revision**: Second phase containing cross-impact analysis from agents
- **Phase3_Arbitration**: Final phase containing synthesized solution options from the arbitrator
- **API_Response**: The complete response object from the AgentCore Runtime API
- **Audit_Trail**: Nested object in API response containing all three phases
- **Solution_Option**: A strategic recovery option with scoring and detailed impact analysis
- **ResponseMapper**: Service class that transforms API responses into UI data structures
- **Sequential_Display**: Animation pattern where agent messages appear one after another
- **Loading_State**: UI state showing progress information while API processing occurs

## Requirements

### Requirement 1: API Response Parsing

**User Story:** As a developer, I want the UI to correctly parse the three-phase API response structure, so that all orchestration data is properly extracted and displayed.

#### Acceptance Criteria

1. WHEN the API returns a response with `assessment.audit_trail`, THE ResponseMapper SHALL extract phase1_initial responses
2. WHEN the API returns a response with `assessment.audit_trail`, THE ResponseMapper SHALL extract phase2_revision responses
3. WHEN the API returns a response with `assessment.audit_trail`, THE ResponseMapper SHALL extract phase3_arbitration solution options
4. WHEN parsing agent responses, THE ResponseMapper SHALL map agent_name to the correct AgentType
5. WHEN parsing agent responses, THE ResponseMapper SHALL extract recommendation, reasoning, and data_sources fields
6. WHEN parsing solution options, THE ResponseMapper SHALL extract all required fields including solution_id, title, description, recommendations, scoring properties, and impact details
7. WHEN the API response is missing expected fields, THE ResponseMapper SHALL handle gracefully with default values

### Requirement 2: Phase 1 Initial Assessment Display

**User Story:** As an operations manager, I want to see initial agent assessments displayed sequentially, so that I can understand each agent's perspective on the disruption.

#### Acceptance Criteria

1. WHEN status becomes "complete", THE OrchestrationView SHALL parse phase1_initial responses
2. WHEN displaying phase1 messages, THE OrchestrationView SHALL show agent messages sequentially with animation delays
3. WHEN an agent is being processed, THE OrchestrationView SHALL display a thinking indicator for that agent
4. WHEN an agent message is displayed, THE AgentMessage SHALL show the agent avatar, name, recommendation, reasoning, and data_sources
5. WHEN all phase1 agents have been displayed, THE OrchestrationView SHALL update the arbitrator analysis text
6. WHEN all phase1 agents have been displayed, THE OrchestrationView SHALL transition stage to "waiting_for_user"

### Requirement 3: Loading State Management

**User Story:** As a user, I want to see detailed loading information while the system processes my request, so that I understand what is happening.

#### Acceptance Criteria

1. WHEN a user submits a disruption prompt, THE App SHALL navigate to OrchestrationView immediately
2. WHEN OrchestrationView mounts, THE component SHALL display a centered loading indicator
3. WHEN the API is processing, THE OrchestrationView SHALL show dynamic loading messages in the arbitrator panel
4. WHEN the status is not "complete", THE OrchestrationView SHALL keep the loading pane visible at the bottom
5. WHEN the status becomes "complete", THE OrchestrationView SHALL hide the loading indicator and display agent messages

### Requirement 4: Phase 2 Cross-Impact Analysis

**User Story:** As an operations manager, I want to trigger cross-impact analysis and see revised agent assessments, so that I can understand how agents' recommendations change based on interdependencies.

#### Acceptance Criteria

1. WHEN phase1 is complete, THE OrchestrationView SHALL display a "Run Cross-Impact Analysis" button
2. WHEN the user clicks the cross-impact button, THE OrchestrationView SHALL make an API call with the session_id
3. WHEN the cross-impact API call is made, THE OrchestrationView SHALL update the arbitrator analysis text to indicate processing
4. WHEN the cross-impact response is received, THE OrchestrationView SHALL parse phase2_revision responses
5. WHEN displaying phase2 messages, THE OrchestrationView SHALL mark them with isCrossImpactRound flag
6. WHEN displaying phase2 messages, THE OrchestrationView SHALL show them sequentially with the same animation pattern as phase1
7. WHEN cross-impact analysis completes, THE OrchestrationView SHALL transition stage to "decision_phase"

### Requirement 5: Phase 3 Solution Display

**User Story:** As an operations manager, I want to see strategic solution options with detailed information, so that I can make an informed decision about disruption recovery.

#### Acceptance Criteria

1. WHEN stage is "decision_phase", THE ArbitratorPanel SHALL display solution option cards
2. WHEN displaying solution cards, THE ArbitratorPanel SHALL show 1-3 options from phase3_arbitration
3. WHEN a solution has recommended_solution_id matching its solution_id, THE card SHALL be marked as "AI Recommended"
4. WHEN displaying a solution card, THE component SHALL show title, description, recommendations array content, and risk flag
5. WHEN displaying a solution card, THE component SHALL derive risk level from scoring properties (safety_score, passenger_score, network_score, cost_score, composite_score)
6. WHEN a user clicks a solution card, THE ArbitratorPanel SHALL expand to show detailed view
7. WHEN displaying expanded solution view, THE component SHALL show justification, reasoning, passenger_impact, financial_impact, network_impact, pros, cons, and risks

### Requirement 6: Sequential Animation

**User Story:** As a user, I want to see agent messages appear one at a time with smooth animations, so that I can follow the orchestration process naturally.

#### Acceptance Criteria

1. WHEN displaying agent messages, THE OrchestrationView SHALL show a thinking indicator before each message
2. WHEN a thinking indicator is shown, THE component SHALL display it for 800 milliseconds
3. WHEN a message is added, THE OrchestrationView SHALL mark the agent as "speaking" with activeAgent state
4. WHEN a message is displayed, THE component SHALL wait 1000 milliseconds before proceeding to the next agent
5. WHEN messages are added, THE OrchestrationView SHALL auto-scroll to keep the latest message visible
6. WHEN an agent is thinking or speaking, THE AgentAvatar SHALL display the appropriate status indicator

### Requirement 7: Error Handling

**User Story:** As a user, I want the system to handle errors gracefully, so that I can understand what went wrong and take appropriate action.

#### Acceptance Criteria

1. WHEN an agent response has status "error", THE AgentMessage SHALL display an error indicator
2. WHEN the API response is missing assessment data, THE OrchestrationView SHALL display a warning message
3. WHEN the cross-impact API call fails, THE OrchestrationView SHALL log the error and proceed with phase1 data
4. WHEN the cross-impact API call fails, THE OrchestrationView SHALL update the arbitrator analysis to indicate the error
5. WHEN parsing fails for a specific field, THE ResponseMapper SHALL use default values and continue processing
6. WHEN the API returns an error status, THE OrchestrationView SHALL display the error message to the user

### Requirement 8: Solution Selection

**User Story:** As an operations manager, I want to select a solution option and see confirmation, so that I can execute the chosen recovery strategy.

#### Acceptance Criteria

1. WHEN a user clicks a solution card, THE ArbitratorPanel SHALL call the onSelectSolution callback
2. WHEN a solution is selected, THE OrchestrationView SHALL add a decision message to the message stream
3. WHEN a decision message is displayed, THE AgentMessage SHALL render it with special decision card styling
4. WHEN a solution is selected, THE ArbitratorPanel SHALL update selectedSolutionId state
5. WHEN a solution is selected, THE ArbitratorPanel SHALL disable other solution cards
6. WHEN a solution is selected, THE ArbitratorPanel SHALL update the arbitrator analysis text to show execution status

### Requirement 9: Responsive Design

**User Story:** As a user on different devices, I want the UI to adapt to my screen size, so that I can use the system effectively on any device.

#### Acceptance Criteria

1. WHEN the viewport width is less than 768px, THE OrchestrationView SHALL hide the ArbitratorPanel
2. WHEN the viewport width is greater than 768px, THE OrchestrationView SHALL display the ArbitratorPanel at 28% width
3. WHEN displaying agent avatars, THE component SHALL use responsive gap spacing (4 on mobile, 6 on desktop)
4. WHEN displaying messages, THE component SHALL use responsive padding (4 on mobile, 12 on desktop)
5. WHEN the ArbitratorPanel is hidden, THE solution selection SHALL still be accessible through an alternative UI pattern

### Requirement 10: Data Source Display

**User Story:** As an operations manager, I want to see which data sources each agent used, so that I can verify the basis for their assessments.

#### Acceptance Criteria

1. WHEN an agent response includes data_sources, THE AgentMessage SHALL display them in the message
2. WHEN displaying data_sources, THE component SHALL format them as a list or inline references
3. WHEN data_sources is empty or missing, THE AgentMessage SHALL not display a data sources section
4. WHEN data_sources contains database queries, THE component SHALL format them readably
5. WHEN data_sources contains multiple items, THE component SHALL display them with clear separation
