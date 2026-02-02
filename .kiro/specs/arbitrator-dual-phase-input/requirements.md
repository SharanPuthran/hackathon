# Requirements Document

## Introduction

This feature enhances the SkyMarshal Arbitrator to consider both Phase 1 (initial) and Phase 2 (revised) agent recommendations when making final decisions. Currently, the arbitrator only receives Phase 2 revised recommendations, missing valuable context about how agent recommendations evolved during the multi-round orchestration process. By providing both phases, the arbitrator can make more informed conflict resolution decisions by understanding which agents changed their recommendations and why.

## Glossary

- **Arbitrator**: The central decision-making agent that resolves conflicts between agent recommendations and makes the final decision
- **Phase_1_Collation**: The aggregated initial recommendations from all 7 agents before they see each other's recommendations
- **Phase_2_Collation**: The aggregated revised recommendations from all 7 agents after reviewing each other's initial recommendations
- **Collation**: A Pydantic model containing aggregated agent responses with metadata (phase, timestamp, duration)
- **Binding_Constraint**: A non-negotiable safety requirement from safety agents (crew_compliance, maintenance, regulatory)
- **Recommendation_Evolution**: The change in an agent's recommendation between Phase 1 and Phase 2
- **Convergence**: When agents move toward agreement after seeing each other's recommendations
- **Divergence**: When agents move further apart after seeing each other's recommendations

## Requirements

### Requirement 1: Pass Both Collations to Arbitrator

**User Story:** As a system operator, I want the arbitrator to receive both Phase 1 and Phase 2 collations, so that it has complete context about the recommendation evolution.

#### Acceptance Criteria

1. WHEN the orchestrator invokes phase3_arbitration, THE Orchestrator SHALL pass both initial_collation and revised_collation as parameters
2. WHEN the arbitrate function is called, THE Arbitrator SHALL accept both initial_recommendations and revised_recommendations parameters
3. THE phase3_arbitration function SHALL maintain backward compatibility by making initial_collation an optional parameter with None default
4. IF initial_collation is None, THEN THE Arbitrator SHALL proceed with only revised_collation (backward compatible behavior)

### Requirement 2: Format Phase Comparison for Arbitrator Prompt

**User Story:** As a system operator, I want the arbitrator to see a clear comparison of Phase 1 vs Phase 2 recommendations, so that it can understand how recommendations evolved.

#### Acceptance Criteria

1. WHEN both collations are provided, THE Arbitrator SHALL format a comparison section showing Phase 1 vs Phase 2 recommendations for each agent
2. WHEN formatting the comparison, THE Arbitrator SHALL highlight agents whose recommendations changed between phases
3. WHEN formatting the comparison, THE Arbitrator SHALL indicate the direction of change (converged, diverged, or unchanged)
4. THE comparison format SHALL include recommendation text, confidence scores, and binding constraints for both phases

### Requirement 3: Update Arbitrator System Prompt

**User Story:** As a system operator, I want the arbitrator to understand how to use Phase 1 context, so that it can make better conflict resolution decisions.

#### Acceptance Criteria

1. THE Arbitrator_System_Prompt SHALL include instructions on how to interpret Phase 1 vs Phase 2 differences
2. THE Arbitrator_System_Prompt SHALL instruct the arbitrator to consider recommendation stability when assessing confidence
3. THE Arbitrator_System_Prompt SHALL instruct the arbitrator to identify convergence patterns as positive signals
4. THE Arbitrator_System_Prompt SHALL instruct the arbitrator to investigate divergence patterns for potential conflicts

### Requirement 4: Include Phase Evolution in Arbitrator Output

**User Story:** As a system operator, I want the arbitrator output to include analysis of recommendation evolution, so that I can understand how the multi-round process influenced the final decision.

#### Acceptance Criteria

1. WHEN both collations are provided, THE Arbitrator_Output SHALL include a recommendation_evolution field
2. THE recommendation_evolution field SHALL list agents that changed recommendations with before/after summaries
3. THE recommendation_evolution field SHALL indicate whether changes were toward convergence or divergence
4. THE recommendation_evolution field SHALL note any binding constraints that were added or removed between phases

### Requirement 5: Handle Partial Phase Data

**User Story:** As a system operator, I want the system to handle cases where Phase 1 data is incomplete, so that the arbitrator can still function with partial information.

#### Acceptance Criteria

1. IF an agent has a response in Phase 2 but not Phase 1, THEN THE Arbitrator SHALL note this as "new in revision phase"
2. IF an agent has a response in Phase 1 but not Phase 2, THEN THE Arbitrator SHALL note this as "dropped in revision phase"
3. IF an agent timed out or errored in one phase but succeeded in another, THEN THE Arbitrator SHALL use the successful response and note the discrepancy
4. THE Arbitrator SHALL log warnings when phase data is incomplete but continue processing

### Requirement 6: Maintain Audit Trail

**User Story:** As a compliance officer, I want the audit trail to include both Phase 1 and Phase 2 data in the arbitrator context, so that I can review the complete decision-making process.

#### Acceptance Criteria

1. THE arbitrator result SHALL include a phases_considered field indicating which phases were available
2. WHEN both phases are provided, THE audit trail SHALL include the phase comparison analysis
3. THE audit trail SHALL preserve the original Phase 1 and Phase 2 collations in the response
4. THE knowledge_base metadata SHALL remain unchanged and continue to be included in the output

### Requirement 7: Preserve Knowledge Base Integration

**User Story:** As a system operator, I want the knowledge base integration to remain unchanged, so that the arbitrator continues to reference operational procedures when making decisions.

#### Acceptance Criteria

1. THE Arbitrator SHALL continue to query the AWS Bedrock Knowledge Base (ID: UDONMVCXEW) for operational procedures
2. THE knowledge base query SHALL occur independently of the dual-phase input enhancement
3. THE operational procedures context SHALL be included in the arbitrator prompt alongside the phase comparison
4. THE knowledgeBaseConsidered flag SHALL continue to indicate whether knowledge base documents were found and used
5. THE knowledge_base metadata in the output SHALL continue to include documents_found, applicable_protocols, and query_timestamp
