# Implementation Plan: Arbitrator Multi-Solution Enhancements

## Overview

This implementation plan extends the SkyMarshal arbitrator to provide 1-3 ranked solution options with detailed recovery plans, S3 integration for historical learning, and comprehensive decision reports. The implementation is organized into four phases: schema extensions, arbitrator enhancements, S3 integration, and report generation.

## Tasks

- [x] 1. Extend Pydantic schemas for multi-solution support
  - Add RecoveryStep, RecoveryPlan, and RecoverySolution schemas to schemas.py
  - Extend ArbitratorOutput with solution_options and recommended_solution_id fields
  - Add validation logic for composite score calculation and dependency checking
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1-2.10, 3.1-3.10_

- [ ]\* 1.1 Write property test for composite score calculation
  - **Property 8: Composite Score Calculation**
  - **Validates: Requirements 2.6**

- [ ]\* 1.2 Write property test for sequential step numbering
  - **Property 11: Sequential Step Numbering**
  - **Validates: Requirements 3.2**

- [ ]\* 1.3 Write property test for no circular dependencies
  - **Property 14: No Circular Dependencies**
  - **Validates: Requirements 10.2**

- [ ]\* 1.4 Write property test for valid dependency references
  - **Property 15: Valid Dependency References**
  - **Validates: Requirements 10.3**

- [x] 2. Implement scoring algorithms
  - Create scoring module with functions for safety, cost, passenger, and network scores
  - Implement composite score calculation with proper weighting (40% safety, 20% each for others)
  - Add score validation and range checking
  - _Requirements: 2.1-2.6_

- [ ]\* 2.1 Write unit tests for scoring algorithms
  - Test safety score with various margins
  - Test cost score with different cost ranges
  - Test passenger score with different impacts
  - Test network score with different propagation
  - _Requirements: 2.1-2.6_

- [ ]\* 2.2 Write property test for score range validation
  - **Property 7: Score Range Validation**
  - **Validates: Requirements 2.1-2.5**

- [x] 3. Enhance arbitrator agent to generate multiple solutions
  - Update arbitrate() function to generate 1-3 solution options
  - Implement \_generate_solution_options() helper function
  - Implement \_score_solution() helper function
  - Implement solution ranking by composite score
  - Ensure all solutions satisfy binding constraints
  - _Requirements: 1.1-1.6, 9.1-9.5_

- [ ]\* 3.1 Write property test for solution count bounds
  - **Property 1: Solution Count Bounds**
  - **Validates: Requirements 1.1**

- [ ]\* 3.2 Write property test for solution ranking
  - **Property 2: Solution Ranking Invariant**
  - **Validates: Requirements 1.2**

- [ ]\* 3.3 Write property test for binding constraint satisfaction
  - **Property 5: Binding Constraint Satisfaction**
  - **Validates: Requirements 1.5, 9.1**

- [ ]\* 3.4 Write property test for recommended solution validity
  - **Property 4: Recommended Solution Validity**
  - **Validates: Requirements 1.4**

- [x] 4. Implement recovery plan generation
  - Create \_generate_recovery_plan() helper function
  - Implement step generation with dependencies
  - Implement critical path identification
  - Add recovery plan validation logic
  - _Requirements: 3.1-3.10, 10.1-10.4_

- [ ]\* 4.1 Write unit tests for recovery plan generation
  - Test step generation with various solution types
  - Test critical path calculation
  - Test contingency plan generation
  - _Requirements: 3.1-3.10_

- [ ]\* 4.2 Write property test for recovery step completeness
  - **Property 12: Recovery Step Completeness**
  - **Validates: Requirements 3.3-3.7**

- [ ]\* 4.3 Write property test for no self-dependencies
  - **Property 13: No Self-Dependencies**
  - **Validates: Requirements 10.1**

- [x] 5. Update arbitrator prompt for multi-solution generation
  - Enhance ARBITRATOR_SYSTEM_PROMPT to request 1-3 solutions
  - Add instructions for solution scoring and ranking
  - Add instructions for recovery plan generation
  - Add instructions for Pareto optimality identification
  - _Requirements: 1.1-1.6, 2.1-2.10, 3.1-3.10_

- [x] 6. Implement backward compatibility
  - Add \_populate_backward_compatible_fields() helper function
  - Populate final_decision from recommended solution
  - Populate recommendations from recommended solution
  - Ensure existing orchestrator integration works
  - _Requirements: 8.1-8.6_

- [ ]\* 6.1 Write property test for backward compatibility
  - **Property 24-25: Backward Compatibility**
  - **Validates: Requirements 8.1, 8.2, 8.5**

- [ ]\* 6.2 Write integration test for three-phase workflow
  - Test complete workflow still functions correctly
  - Verify legacy fields are populated
  - _Requirements: 8.6_

- [x] 7. Checkpoint - Ensure all arbitrator tests pass
  - Run all unit tests and property tests
  - Verify arbitrator generates valid multi-solution output
  - Ask the user if questions arise

- [x] 8. Create DecisionRecord schema and S3 storage module
  - Add DecisionRecord schema to schemas.py
  - Create s3_storage.py module with store_decision_to_s3() function
  - Implement S3 key generation with date partitioning
  - Add metadata tagging for S3 objects
  - _Requirements: 4.1-4.7, 5.1-5.9_

- [ ]\* 8.1 Write property test for S3 key format
  - **Property 17: S3 Key Format**
  - **Validates: Requirements 4.4**

- [ ]\* 8.2 Write property test for human override flag
  - **Property 19: Human Override Flag Consistency**
  - **Validates: Requirements 4.6**

- [ ]\* 8.3 Write unit tests for S3 storage
  - Test S3 key generation with various timestamps
  - Test metadata extraction
  - Test error handling for bucket failures
  - Mock S3 client to verify API calls
  - _Requirements: 4.1-4.7_

- [x] 9. Create API endpoint for solution selection
  - Create api/endpoints.py with /api/select-solution endpoint
  - Implement SolutionSelectionRequest and SolutionSelectionResponse schemas
  - Add validation for disruption_id and selected_solution_id
  - Integrate with S3 storage module
  - _Requirements: 6.1-6.8_

- [ ]\* 9.1 Write unit tests for API endpoint
  - Test successful solution selection
  - Test error cases (invalid IDs, missing fields)
  - Test S3 storage integration
  - _Requirements: 6.1-6.8_

- [ ]\* 9.2 Write property test for API error handling
  - **Property 21: API Error Handling**
  - **Validates: Requirements 6.8**

- [x] 10. Checkpoint - Ensure S3 integration tests pass
  - Run all S3 storage tests
  - Verify API endpoint works correctly
  - Test with mock S3 buckets
  - Ask the user if questions arise

- [x] 11. Create DecisionReport schema and report generation module
  - Add DecisionReport and ImpactAssessment schemas to schemas.py
  - Create report_generator.py module
  - Implement generate_decision_report() function
  - Add helper functions for extracting report sections
  - _Requirements: 7.1-7.5_

- [ ]\* 11.1 Write property test for report completeness
  - **Property 22: Report Completeness**
  - **Validates: Requirements 7.1-7.5**

- [ ]\* 11.2 Write unit tests for report generation
  - Test report generation with complete data
  - Test report generation with missing data
  - Test impact assessment generation
  - _Requirements: 7.1-7.5_

- [x] 12. Implement report export functions
  - Implement export_report_json() function
  - Implement export_report_markdown() function
  - Implement export_report_pdf() function (or placeholder)
  - Add format validation for each export type
  - _Requirements: 7.6-7.8_

- [ ]\* 12.1 Write property test for JSON export validity
  - **Property 23: Report Export Format Validity**
  - **Validates: Requirements 7.7**

- [ ]\* 12.2 Write unit tests for report export
  - Test JSON export format
  - Test Markdown export format
  - Test PDF export (if implemented)
  - _Requirements: 7.6-7.8_

- [x] 13. Integration testing for complete workflow
  - Test end-to-end flow: arbitration → solution selection → S3 storage → report generation
  - Test with realistic agent responses
  - Verify all components work together
  - Test error handling across components
  - _Requirements: All_

- [ ]\* 13.1 Write integration test for solution selection flow
  - Test complete flow from arbitrator output to S3 storage
  - Verify decision record is created correctly
  - Verify both S3 buckets receive the record
  - _Requirements: 4.1-4.7, 6.1-6.8_

- [ ]\* 13.2 Write integration test for report generation flow
  - Test report generation from arbitrator output
  - Test export in all formats
  - Verify report completeness
  - _Requirements: 7.1-7.8_

- [x] 14. Final checkpoint - Ensure all tests pass
  - Run complete test suite with coverage
  - Verify all property tests pass (100+ iterations each)
  - Verify all integration tests pass
  - Review test coverage and add missing tests
  - Ask the user if questions arise

- [x] 15. Update documentation
  - Update arbitrator agent docstrings
  - Add examples for new schemas
  - Document API endpoint usage
  - Document S3 storage structure
  - Update README with new capabilities
  - _Requirements: All_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- Working directory: `skymarshal_agents_new/skymarshal/`
- Use `uv run pytest` for running tests
- Use `uv run pytest --hypothesis-show-statistics` for property test details
