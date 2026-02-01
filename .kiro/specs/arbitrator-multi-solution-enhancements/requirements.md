# Requirements Document

## Introduction

This document specifies requirements for enhancing the SkyMarshal arbitrator agent to provide multiple ranked solution options, detailed recovery plans, S3 integration for historical learning, and comprehensive decision reports. The arbitrator currently provides a single final decision; these enhancements will enable human-in-the-loop decision makers to choose from multiple options with complete recovery workflows and audit trails.

## Glossary

- **Arbitrator**: The agent responsible for resolving conflicts between agent recommendations and making final decisions in Phase 3 of the multi-round orchestration workflow
- **Recovery_Solution**: A complete solution option including recommendations, impact assessments, scoring, and recovery plan
- **Recovery_Plan**: A detailed step-by-step workflow for implementing a solution, including dependencies, success criteria, and rollback procedures
- **Decision_Record**: A historical record of a disruption event, arbitrator analysis, human selection, and outcome for learning purposes
- **Composite_Score**: A weighted average score across multiple dimensions (safety, cost, passenger impact, network impact) used to rank solutions
- **Binding_Constraint**: A non-negotiable safety requirement from safety agents (crew_compliance, maintenance, regulatory) that all solutions must satisfy
- **S3_Knowledge_Base**: AWS S3 bucket storing historical decision records for pattern analysis and continuous learning
- **Human_Override**: When a human decision maker selects a solution different from the arbitrator's recommended solution

## Requirements

### Requirement 1: Multiple Ranked Solution Options

**User Story:** As a Duty Manager, I want to see 1-3 ranked solution options from the arbitrator, so that I can choose the best approach based on current operational priorities and constraints.

#### Acceptance Criteria

1. WHEN the arbitrator completes analysis, THE Arbitrator SHALL generate between 1 and 3 distinct solution options
2. WHEN multiple solutions exist, THE Arbitrator SHALL rank solutions by composite score from highest to lowest
3. WHEN solutions have equal composite scores, THE Arbitrator SHALL use safety score as the tiebreaker
4. THE Arbitrator SHALL identify the recommended solution and mark it clearly
5. WHEN generating solutions, THE Arbitrator SHALL ensure all solutions satisfy all binding constraints from safety agents
6. WHEN solutions represent different trade-off points, THE Arbitrator SHALL identify them as Pareto-optimal alternatives

### Requirement 2: Solution Scoring and Assessment

**User Story:** As a Duty Manager, I want each solution scored across multiple dimensions with clear pros and cons, so that I can understand the trade-offs and make an informed decision.

#### Acceptance Criteria

1. THE Arbitrator SHALL score each solution across safety, cost, passenger impact, and network impact dimensions
2. WHEN scoring safety, THE Arbitrator SHALL assign scores from 0 to 100 based on safety margin above minimum requirements
3. WHEN scoring cost, THE Arbitrator SHALL assign scores from 0 to 100 with lower costs receiving higher scores
4. WHEN scoring passenger impact, THE Arbitrator SHALL assign scores from 0 to 100 with fewer affected passengers receiving higher scores
5. WHEN scoring network impact, THE Arbitrator SHALL assign scores from 0 to 100 with less propagation receiving higher scores
6. THE Arbitrator SHALL calculate composite score as a weighted average with safety weighted at 40%, cost at 20%, passenger impact at 20%, and network impact at 20%
7. THE Arbitrator SHALL provide a list of pros (advantages) for each solution
8. THE Arbitrator SHALL provide a list of cons (disadvantages) for each solution
9. THE Arbitrator SHALL provide a list of risks for each solution
10. THE Arbitrator SHALL provide an estimated implementation duration for each solution

### Requirement 3: Detailed Recovery Plans

**User Story:** As a Recovery Coordinator, I want detailed step-by-step recovery plans for each solution, so that I can execute the chosen solution efficiently and track progress.

#### Acceptance Criteria

1. THE Arbitrator SHALL generate a complete recovery plan for each solution option
2. WHEN creating recovery steps, THE Arbitrator SHALL number steps sequentially starting from 1
3. WHEN creating recovery steps, THE Arbitrator SHALL specify which agent or system is responsible for executing each step
4. WHEN creating recovery steps, THE Arbitrator SHALL identify dependencies between steps using step numbers
5. WHEN creating recovery steps, THE Arbitrator SHALL estimate the duration for each step
6. WHEN creating recovery steps, THE Arbitrator SHALL indicate whether the step can be automated
7. WHEN creating recovery steps, THE Arbitrator SHALL specify success criteria for verifying step completion
8. WHEN creating recovery steps, THE Arbitrator SHALL provide rollback procedures for steps that may fail
9. THE Arbitrator SHALL identify the critical path through the recovery plan
10. THE Arbitrator SHALL provide contingency plans for handling step failures

### Requirement 4: S3 Knowledge Base Integration

**User Story:** As a System Administrator, I want human-selected solutions stored to S3 for historical learning, so that the system can improve recommendations over time based on past outcomes.

#### Acceptance Criteria

1. WHEN a human selects a solution, THE System SHALL create a decision record containing disruption context, agent responses, arbitrator analysis, and human selection
2. WHEN storing to S3, THE System SHALL write to the knowledge base bucket at s3://skymarshal-prod-knowledge-base-368613657554
3. WHEN storing to S3, THE System SHALL write to the decisions bucket at s3://skymarshal-prod-decisions-368613657554
4. WHEN generating S3 keys, THE System SHALL use date partitioning in format decisions/YYYY/MM/DD/{disruption_id}.json
5. WHEN storing decision records, THE System SHALL include metadata tags for disruption_type, flight_number, and selected_solution_id
6. WHEN a human selects a solution different from the recommended solution, THE System SHALL mark the record with human_override flag set to true
7. THE System SHALL store decision records in JSON format with proper indentation for readability

### Requirement 5: Decision Record Schema

**User Story:** As a Data Analyst, I want decision records to capture complete context and outcomes, so that I can analyze patterns and measure success rates of different solution types.

#### Acceptance Criteria

1. THE Decision_Record SHALL include a unique disruption_id for tracking
2. THE Decision_Record SHALL include the timestamp of the decision in ISO 8601 format
3. THE Decision_Record SHALL include the flight_number and disruption_type
4. THE Decision_Record SHALL include all agent responses from the analysis
5. THE Decision_Record SHALL include all solution options presented by the arbitrator
6. THE Decision_Record SHALL include the arbitrator's recommended_solution_id
7. THE Decision_Record SHALL include the human's selected_solution_id
8. THE Decision_Record SHALL include optional selection_rationale explaining why the human chose that solution
9. THE Decision_Record SHALL include optional outcome fields (outcome_status, actual_delay, actual_cost, lessons_learned) to be filled in after execution

### Requirement 6: API Endpoint for Solution Selection

**User Story:** As a Frontend Developer, I want an API endpoint to record human solution selections, so that the UI can submit decisions and trigger S3 storage.

#### Acceptance Criteria

1. THE System SHALL provide a POST endpoint at /api/select-solution
2. WHEN receiving a selection request, THE System SHALL require disruption_id and selected_solution_id parameters
3. WHEN receiving a selection request, THE System SHALL accept an optional rationale parameter
4. WHEN processing a selection, THE System SHALL load the original arbitrator output for that disruption_id
5. WHEN processing a selection, THE System SHALL create a decision record with the human's selection
6. WHEN processing a selection, THE System SHALL store the decision record to both S3 buckets
7. WHEN storage succeeds, THE System SHALL return a success response with confirmation message
8. WHEN storage fails, THE System SHALL return an error response with details

### Requirement 7: Comprehensive Decision Reports

**User Story:** As a Compliance Officer, I want to download comprehensive decision reports in multiple formats, so that I can review decisions for regulatory compliance and audit purposes.

#### Acceptance Criteria

1. THE System SHALL generate decision reports containing all agent assessments, conflicts, resolutions, and solution options
2. THE Decision_Report SHALL include an impact assessment section with safety, financial, passenger, network, and cargo impacts
3. THE Decision_Report SHALL include a decision rationale section explaining key considerations and assumptions
4. THE Decision_Report SHALL include a historical context section with similar past events and success rates
5. THE Decision_Report SHALL include a confidence analysis section explaining factors affecting confidence
6. THE System SHALL support exporting decision reports in PDF format
7. THE System SHALL support exporting decision reports in JSON format
8. THE System SHALL support exporting decision reports in Markdown format

### Requirement 8: Backward Compatibility

**User Story:** As a System Maintainer, I want the enhanced arbitrator to remain compatible with existing workflows, so that current integrations continue to work without modification.

#### Acceptance Criteria

1. THE Arbitrator SHALL continue to provide the final_decision field in its output
2. THE Arbitrator SHALL continue to provide the recommendations field as a list of strings
3. THE Arbitrator SHALL continue to provide conflicts_identified, conflict_resolutions, and safety_overrides fields
4. WHEN only one solution exists, THE Arbitrator SHALL populate final_decision and recommendations from that single solution
5. WHEN multiple solutions exist, THE Arbitrator SHALL populate final_decision and recommendations from the recommended solution
6. THE Arbitrator SHALL maintain the existing three-phase workflow (initial → revision → arbitration)

### Requirement 9: Solution Validation

**User Story:** As a Safety Officer, I want all solution options validated against safety constraints, so that I can be confident no unsafe options are presented to decision makers.

#### Acceptance Criteria

1. WHEN generating solutions, THE Arbitrator SHALL validate each solution against all binding constraints
2. WHEN a solution violates any binding constraint, THE Arbitrator SHALL reject that solution and not include it in the output
3. WHEN all potential solutions violate binding constraints, THE Arbitrator SHALL return a single conservative solution recommending manual review
4. THE Arbitrator SHALL document which binding constraints were validated for each solution
5. THE Arbitrator SHALL include safety compliance details in each solution's description

### Requirement 10: Recovery Step Validation

**User Story:** As a Recovery Coordinator, I want recovery plans validated for logical consistency, so that I can trust the execution workflow will not have circular dependencies or missing steps.

#### Acceptance Criteria

1. WHEN generating recovery plans, THE Arbitrator SHALL ensure no step depends on itself
2. WHEN generating recovery plans, THE Arbitrator SHALL ensure no circular dependencies exist between steps
3. WHEN generating recovery plans, THE Arbitrator SHALL ensure all dependency step numbers reference valid steps
4. WHEN generating recovery plans, THE Arbitrator SHALL ensure the critical path includes only steps that are actually on the critical path
5. WHEN validation fails, THE Arbitrator SHALL log a warning and attempt to correct the recovery plan
