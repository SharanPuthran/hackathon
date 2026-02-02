# Implementation Plan: Arbitrator Dual-Phase Input

## Overview

This implementation enhances the SkyMarshal Arbitrator to receive and analyze both Phase 1 (initial) and Phase 2 (revised) agent recommendations. The implementation follows a bottom-up approach: first adding the new schemas, then the helper functions, then updating the arbitrator, and finally wiring everything together in the orchestrator.

## Tasks

- [x] 1. Add new Pydantic schemas for recommendation evolution
  - [x] 1.1 Add AgentEvolution model to agents/schemas.py
    - Define fields: agent_name, phase1_recommendation, phase2_recommendation, phase1_confidence, phase2_confidence, change_type, binding_constraints_added, binding_constraints_removed, change_summary
    - Add field validators for change_type (must be one of: unchanged, converged, diverged, new_in_phase2, dropped_in_phase2)
    - _Requirements: 4.2, 4.3, 4.4, 5.1, 5.2_
  - [x] 1.2 Add RecommendationEvolution model to agents/schemas.py
    - Define fields: phases_available, agents_changed, agents_unchanged, convergence_detected, divergence_detected, evolution_details, analysis_summary
    - _Requirements: 4.1, 6.1_
  - [x] 1.3 Update ArbitratorOutput model with new optional fields
    - Add recommendation_evolution: Optional[RecommendationEvolution]
    - Add phases_considered: List[str] with default ["phase2"]
    - _Requirements: 4.1, 6.1_
  - [ ]\* 1.4 Write unit tests for new schema models
    - Test AgentEvolution with all change_type values
    - Test RecommendationEvolution serialization/deserialization
    - Test ArbitratorOutput backward compatibility (new fields optional)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 2. Checkpoint - Ensure schema tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Add helper functions for phase comparison
  - [x] 3.1 Implement \_format_phase_comparison function in agents/arbitrator/agent.py
    - Accept initial_responses and revised_responses dicts
    - Generate formatted comparison text showing Phase 1 vs Phase 2 for each agent
    - Include recommendation text, confidence scores, binding constraints
    - Highlight agents that changed with change direction
    - Handle missing agents in either phase
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  - [x] 3.2 Implement \_analyze_recommendation_evolution function in agents/arbitrator/agent.py
    - Accept initial_responses and revised_responses dicts
    - Return List[AgentEvolution] with change analysis for each agent
    - Classify changes as unchanged/converged/diverged/new_in_phase2/dropped_in_phase2
    - Track binding constraints added/removed
    - Generate change_summary for each agent
    - _Requirements: 4.2, 4.3, 4.4, 5.1, 5.2, 5.3_
  - [x] 3.3 Implement \_build_recommendation_evolution function in agents/arbitrator/agent.py
    - Accept evolution_details list from \_analyze_recommendation_evolution
    - Build complete RecommendationEvolution model
    - Calculate agents_changed and agents_unchanged counts
    - Determine convergence_detected and divergence_detected flags
    - Generate analysis_summary
    - _Requirements: 4.1, 4.2, 4.3_
  - [ ]\* 3.4 Write property test for phase comparison formatting
    - **Property 2: Phase Comparison Formatting Completeness**
    - Generate random Collation pairs with Hypothesis
    - Verify formatted output contains all agents with required fields
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
  - [ ]\* 3.5 Write property test for recommendation evolution analysis
    - **Property 3: Recommendation Evolution Output Completeness**
    - Generate random Collation pairs with Hypothesis
    - Verify evolution output has all required fields
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
  - [ ]\* 3.6 Write property test for partial data handling
    - **Property 4: Partial Data Handling**
    - Generate collations with asymmetric agents and mixed statuses
    - Verify correct classification of each agent's evolution
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [x] 4. Checkpoint - Ensure helper function tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Update arbitrator system prompt with phase evolution instructions
  - [x] 5.1 Add PHASE_EVOLUTION_INSTRUCTIONS constant to agents/arbitrator/agent.py
    - Include guidance on interpreting convergence as positive signal
    - Include guidance on investigating divergence patterns
    - Include guidance on weighting stable safety constraints
    - Include guidance on documenting phase evolution in reasoning
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  - [x] 5.2 Integrate phase evolution instructions into ARBITRATOR_SYSTEM_PROMPT
    - Append PHASE_EVOLUTION_INSTRUCTIONS to existing system prompt
    - Ensure instructions are conditional on both phases being available
    - _Requirements: 3.1_
  - [ ]\* 5.3 Write unit tests for system prompt content
    - Verify PHASE_EVOLUTION_INSTRUCTIONS contains convergence guidance
    - Verify PHASE_EVOLUTION_INSTRUCTIONS contains divergence guidance
    - Verify PHASE_EVOLUTION_INSTRUCTIONS contains stability guidance
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 6. Update arbitrate function to accept dual-phase input
  - [x] 6.1 Update arbitrate function signature in agents/arbitrator/agent.py
    - Add optional parameter: initial_recommendations: Optional[Union[Collation, dict]] = None
    - Maintain backward compatibility (None default)
    - _Requirements: 1.2, 1.3_
  - [x] 6.2 Add phase comparison to arbitrator prompt construction
    - Check if initial_recommendations is provided
    - If provided, call \_format_phase_comparison and include in prompt
    - Include phase comparison section after agent responses, before binding constraints
    - _Requirements: 2.1, 7.3_
  - [x] 6.3 Add recommendation evolution to arbitrator output
    - If initial_recommendations provided, call \_analyze_recommendation_evolution
    - Build RecommendationEvolution using \_build_recommendation_evolution
    - Add to ArbitratorOutput before returning
    - Set phases_considered based on available phases
    - _Requirements: 4.1, 6.1, 6.2_
  - [x] 6.4 Ensure knowledge base query remains independent
    - Verify KB query occurs regardless of initial_recommendations
    - Verify prompt includes both operational context and phase comparison
    - _Requirements: 7.1, 7.2, 7.3_
  - [ ]\* 6.5 Write property test for dual collation acceptance
    - **Property 1: Dual Collation Acceptance**
    - Generate random valid Collation pairs with Hypothesis
    - Verify arbitrate accepts both without error
    - **Validates: Requirements 1.1, 1.2**
  - [ ]\* 6.6 Write property test for knowledge base independence
    - **Property 6: Knowledge Base Independence**
    - Generate arbitration calls with/without initial_collation
    - Verify KB query occurs in both cases
    - **Validates: Requirements 7.2, 7.3**

- [x] 7. Checkpoint - Ensure arbitrator tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Update phase3_arbitration function in main.py
  - [x] 8.1 Update phase3_arbitration function signature
    - Add optional parameter: initial_collation: Optional[Collation] = None
    - Maintain backward compatibility (None default)
    - _Requirements: 1.1, 1.3_
  - [x] 8.2 Pass initial_collation to arbitrate function
    - Convert initial_collation to dict if provided
    - Pass as initial_recommendations parameter to arbitrate
    - _Requirements: 1.1_
  - [x] 8.3 Update checkpoint saving to include initial_collation
    - Save initial_collation in phase3_start checkpoint state
    - Include phases_considered in checkpoint metadata
    - _Requirements: 6.2, 6.3_
  - [ ]\* 8.4 Write unit test for phase3_arbitration backward compatibility
    - Test calling phase3_arbitration without initial_collation
    - Verify output structure unchanged
    - _Requirements: 1.3, 1.4_

- [x] 9. Update handle_disruption to pass both collations
  - [x] 9.1 Update phase3_arbitration call in handle_disruption
    - Pass initial_collation from Phase 1 to phase3_arbitration
    - _Requirements: 1.1_
  - [x] 9.2 Update audit trail to include phase comparison
    - Add phases_considered to response
    - Include recommendation_evolution in audit_trail if available
    - _Requirements: 6.2, 6.3_
  - [ ]\* 9.3 Write property test for output structure preservation
    - **Property 5: Output Structure Preservation**
    - Generate arbitration results with/without initial_collation
    - Verify output contains phases_considered and knowledge_base metadata
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 7.4, 7.5**

- [x] 10. Update existing tests for new signatures
  - [x] 10.1 Update test_phase_execution.py for new phase3_arbitration signature
    - Update test_phase3_arbitration to test with both collations
    - Add test for backward compatibility (no initial_collation)
    - _Requirements: 1.1, 1.3_
  - [x] 10.2 Update test_arbitrator.py for new arbitrate signature
    - Update test_arbitrate_with_mock_llm to include initial_recommendations
    - Add test for backward compatibility (no initial_recommendations)
    - Update test_arbitrate_with_collation_object to test dual input
    - _Requirements: 1.2, 1.3_
  - [ ]\* 10.3 Write integration test for end-to-end flow
    - Test full handle_disruption with mocked agents
    - Verify Phase 1 collation passed to Phase 3
    - Verify audit trail contains both phases and evolution analysis
    - _Requirements: 1.1, 6.2, 6.3_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis
- Unit tests validate specific examples and edge cases
- The implementation maintains full backward compatibility - existing code calling phase3_arbitration or arbitrate without the new parameters will continue to work
