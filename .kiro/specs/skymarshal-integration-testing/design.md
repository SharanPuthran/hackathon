# Design Document: SkyMarshal Integration Testing & Deployment

## Overview

This design document specifies the integration testing strategy and deployment plan for the complete SkyMarshal system. The system combines two major enhancements:

1. **Multi-Round Orchestration**: Three-phase workflow (Initial → Revision → Arbitration) with natural language input processing
2. **Multi-Solution Arbitrator**: Enhanced arbitrator that generates 1-3 ranked solution options with detailed recovery plans

Both components have been implemented independently and now need comprehensive integration testing to ensure they work together seamlessly before AgentCore deployment.

## Current Implementation Status

### Completed Components

**Multi-Round Orchestration (✅ Complete)**:

- Three-phase workflow in `src/main.py`
- Natural language prompt handling
- Prompt augmentation for each phase
- Parallel agent execution
- Response collation with Pydantic models
- Audit trail preservation

**Arbitrator Enhancements (✅ Complete)**:

- Multi-solution generation in `src/agents/arbitrator/agent.py`
- Recovery plan generation with step dependencies
- Multi-dimensional scoring (safety, cost, passenger, network)
- Solution ranking by composite score
- Backward compatibility fields
- Structured output with Pydantic schemas

**Agent Updates (✅ Complete)**:

- All 7 agents updated for multi-round workflow
- LangChain structured output for data extraction
- Agent-specific DynamoDB query tools
- Phase-aware processing (initial vs revision)

**Database Infrastructure (✅ Complete)**:

- Core GSIs created and validated
- Priority 1 GSIs created and validated
- Priority 2 GSIs created and validated
- Data validation scripts operational

### Integration Gaps

The following areas need validation and testing:

1. **End-to-End Workflow**: Complete flow from user prompt through all three phases to multi-solution output
2. **Solution Validation**: Ensuring all solutions satisfy binding constraints
3. **Recovery Plan Consistency**: Validating recovery plans are logically sound
4. **Performance**: Validating latency targets are met
5. **Error Handling**: Ensuring graceful degradation works correctly
6. **Backward Compatibility**: Validating legacy integrations still work

## Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Input                               │
│  Natural language prompt: "Flight EY123 on Jan 20th had a       │
│  mechanical failure"                                             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator (main.py)                        │
│                                                                   │
│  Phase 1: Initial Recommendations                                │
│  ├─ Augment prompt with "provide initial recommendation"         │
│  ├─ Invoke all 7 agents in parallel                              │
│  └─ Collate responses → Collation                                │
│                                                                   │
│  Phase 2: Revision Round                                         │
│  ├─ Augment prompt with "review and revise"                      │
│  ├─ Include Phase 1 collation                                    │
│  ├─ Invoke all 7 agents in parallel                              │
│  └─ Collate responses → Collation                                │
│                                                                   │
│  Phase 3: Arbitration                                            │
│  ├─ Pass Phase 2 collation to arbitrator                         │
│  └─ Receive multi-solution output                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Arbitrator (arbitrator/agent.py)                    │
│                                                                   │
│  1. Extract binding constraints from safety agents               │
│  2. Identify conflicts between recommendations                   │
│  3. Generate 1-3 solution options                                │
│  4. Score each solution (safety, cost, passenger, network)       │
│  5. Generate recovery plan for each solution                     │
│  6. Rank solutions by composite score                            │
│  7. Validate all solutions satisfy binding constraints           │
│  8. Populate backward compatibility fields                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-Solution Output                         │
│                                                                   │
│  {                                                                │
│    "final_decision": "...",  // From recommended solution        │
│    "recommendations": [...], // From recommended solution        │
│    "solution_options": [     // NEW: Multiple solutions          │
│      {                                                            │
│        "solution_id": 1,                                          │
│        "title": "Conservative Safety-First",                     │
│        "composite_score": 78,                                    │
│        "recovery_plan": {                                        │
│          "steps": [...],                                         │
│          "critical_path": [...]                                  │
│        }                                                          │
│      },                                                           │
│      ...                                                          │
│    ],                                                             │
│    "recommended_solution_id": 1,                                 │
│    "audit_trail": {          // Complete history                 │
│      "phase1_initial": {...},                                    │
│      "phase2_revision": {...},                                   │
│      "phase3_arbitration": {...}                                 │
│    }                                                              │
│  }                                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Test Strategy

### Test Categories

#### 1. End-to-End Workflow Tests

**Purpose**: Validate complete three-phase workflow produces multi-solution output

**Test Scenarios**:

1. **Simple Disruption (No Conflicts)**
   - Input: "Flight EY123 delayed 2 hours due to weather"
   - Expected: 1-3 solutions, all agents agree, high confidence
   - Validation: All phases execute, solutions ranked, recovery plans complete

2. **Safety vs Business Conflict**
   - Input: "Flight EY456 crew exceeds FDP, network wants minimal delay"
   - Expected: Safety constraint enforced, business recommendation overridden
   - Validation: Safety override documented, conservative solution recommended

3. **Safety vs Safety Conflict**
   - Input: "Flight EY789 has both crew FDP violation and maintenance issue"
   - Expected: Most conservative option chosen (likely cancellation)
   - Validation: Both constraints satisfied, reasoning explains choice

4. **Multiple Agent Failures**
   - Input: Valid disruption, but 2 agents timeout
   - Expected: System continues with available responses, lower confidence
   - Validation: Audit trail shows failures, fallback logic works

5. **Partial Data Scenario**
   - Input: Disruption for flight with incomplete database records
   - Expected: Solutions generated with uncertainty indicators
   - Validation: Confidence scores reflect data quality, warnings present

#### 2. Solution Validation Tests

**Purpose**: Ensure all solutions satisfy binding constraints

**Test Scenarios**:

1. **Constraint Satisfaction**
   - Generate solutions with various binding constraints
   - Verify all solutions satisfy all constraints
   - Verify solutions violating constraints are rejected

2. **Pareto Optimality**
   - Generate multiple solutions
   - Verify no solution dominates another across all dimensions
   - Verify solutions represent different trade-off points

3. **Score Calculation**
   - Verify composite score = (safety × 0.4) + (cost × 0.2) + (passenger × 0.2) + (network × 0.2)
   - Verify all individual scores in range [0, 100]
   - Verify safety score used as tiebreaker

#### 3. Recovery Plan Validation Tests

**Purpose**: Ensure recovery plans are logically consistent

**Test Scenarios**:

1. **Dependency Validation**
   - Verify no circular dependencies
   - Verify no self-dependencies
   - Verify all dependency references are valid
   - Verify dependencies only reference earlier steps

2. **Step Completeness**
   - Verify all required fields populated
   - Verify step numbers sequential starting from 1
   - Verify critical path is valid
   - Verify responsible agents are specified

3. **Execution Readiness**
   - Verify success criteria defined for each step
   - Verify rollback procedures provided where needed
   - Verify automation flags set correctly
   - Verify estimated durations reasonable

#### 4. Performance Tests

**Purpose**: Validate system meets latency targets

**Test Scenarios**:

1. **Phase Latency**
   - Measure Phase 1 execution time (target: < 10s)
   - Measure Phase 2 execution time (target: < 10s)
   - Measure Phase 3 execution time (target: < 5s)
   - Measure end-to-end time (target: < 30s)

2. **Database Query Performance**
   - Measure query latency for all GSIs
   - Verify no table scans occur
   - Verify p99 latency < 100ms
   - Verify queries use correct GSIs

3. **Concurrent Load**
   - Test with 10 concurrent disruption requests
   - Verify no performance degradation
   - Verify no resource exhaustion
   - Verify error rates remain low

#### 5. Backward Compatibility Tests

**Purpose**: Ensure existing integrations continue to work

**Test Scenarios**:

1. **Legacy Field Population**
   - Verify final_decision populated from recommended solution
   - Verify recommendations populated from recommended solution
   - Verify existing response structure maintained
   - Verify API contracts unchanged

2. **Single-Solution Mode**
   - Test with scenarios that generate only 1 solution
   - Verify backward compatibility fields work correctly
   - Verify no breaking changes for legacy clients

3. **Migration Path**
   - Test gradual migration from single to multi-solution
   - Verify clients can ignore new fields
   - Verify clients can adopt new fields incrementally

#### 6. Error Handling Tests

**Purpose**: Validate graceful degradation

**Test Scenarios**:

1. **Agent Failures**
   - Test with 1 agent timeout
   - Test with multiple agent timeouts
   - Test with agent errors
   - Verify system continues with available data

2. **Arbitrator Failures**
   - Test with arbitrator model unavailable
   - Test with arbitrator timeout
   - Test with invalid arbitrator output
   - Verify conservative fallback works

3. **Database Failures**
   - Test with database connection errors
   - Test with query timeouts
   - Test with missing data
   - Verify error messages are actionable

## Test Implementation

### Test Structure

```
test/
├── integration/
│   ├── test_three_phase_workflow.py
│   ├── test_solution_validation.py
│   ├── test_recovery_plan_validation.py
│   ├── test_backward_compatibility.py
│   └── test_error_handling.py
├── performance/
│   ├── test_phase_latency.py
│   ├── test_database_performance.py
│   └── test_concurrent_load.py
└── property/
    ├── test_solution_properties.py
    ├── test_recovery_plan_properties.py
    └── test_workflow_properties.py
```

### Key Test Fixtures

```python
@pytest.fixture
async def orchestrator_with_mocks():
    """Orchestrator with mocked agents for controlled testing"""
    # Mock LLM, MCP tools, agents
    # Return configured orchestrator
    pass

@pytest.fixture
def sample_disruption_prompts():
    """Collection of test disruption prompts"""
    return [
        "Flight EY123 delayed 2 hours due to weather",
        "Flight EY456 crew exceeds FDP limit",
        "Flight EY789 has maintenance issue and crew problem",
        # ... more scenarios
    ]

@pytest.fixture
def sample_agent_responses():
    """Sample agent responses for testing arbitrator"""
    return {
        "crew_compliance": {
            "recommendation": "...",
            "binding_constraints": ["..."],
            "confidence": 0.95
        },
        # ... other agents
    }
```

### Property-Based Tests

Using Hypothesis for property-based testing:

```python
from hypothesis import given, strategies as st

@given(st.lists(st.floats(min_value=0, max_value=100), min_size=4, max_size=4))
def test_composite_score_calculation(scores):
    """Property: Composite score equals weighted average"""
    safety, cost, passenger, network = scores
    expected = (safety * 0.4) + (cost * 0.2) + (passenger * 0.2) + (network * 0.2)

    solution = create_solution_with_scores(safety, cost, passenger, network)

    assert abs(solution.composite_score - expected) < 0.1

@given(st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=10))
def test_no_circular_dependencies(step_count):
    """Property: Recovery plans have no circular dependencies"""
    plan = generate_recovery_plan(step_count)

    # Build dependency graph
    graph = build_dependency_graph(plan.steps)

    # Verify no cycles
    assert not has_cycles(graph)
```

## Deployment Strategy

### Pre-Deployment Checklist

1. **Code Quality**
   - [ ] All unit tests pass
   - [ ] All integration tests pass
   - [ ] All property-based tests pass
   - [ ] Code coverage > 80%
   - [ ] No critical linting errors
   - [ ] Security scan passed

2. **Configuration**
   - [ ] Environment variables documented
   - [ ] .bedrock_agentcore.yaml validated
   - [ ] pyproject.toml dependencies verified
   - [ ] Model IDs configured correctly
   - [ ] Database connections tested

3. **Documentation**
   - [ ] README updated
   - [ ] API documentation complete
   - [ ] Deployment guide reviewed
   - [ ] Runbook tested
   - [ ] Troubleshooting guide updated

4. **Monitoring**
   - [ ] Health check endpoint working
   - [ ] Metrics endpoint configured
   - [ ] Alerts configured
   - [ ] Dashboards created
   - [ ] Log aggregation working

### Deployment Steps

#### 1. Staging Deployment

```bash
cd skymarshal_agents_new/skymarshal

# Run full test suite
uv run pytest test/ -v --hypothesis-show-statistics

# Deploy to staging
uv run agentcore deploy --environment staging

# Validate deployment
uv run agentcore status --environment staging

# Run smoke tests
uv run pytest test/integration/test_smoke.py --environment staging
```

#### 2. Production Deployment

```bash
# Deploy to production
uv run agentcore deploy --environment production

# Validate deployment
uv run agentcore status --environment production

# Monitor for 1 hour
# Check error rates, latency, success rates

# If issues detected, rollback
uv run agentcore rollback --environment production
```

### Rollback Procedure

If issues are detected in production:

1. **Immediate Rollback**

   ```bash
   uv run agentcore rollback --environment production
   ```

2. **Verify Rollback**
   - Check health endpoint returns 200
   - Verify error rates return to normal
   - Verify latency returns to baseline

3. **Root Cause Analysis**
   - Review logs for errors
   - Check metrics for anomalies
   - Identify failing component

4. **Fix and Redeploy**
   - Fix identified issue
   - Test fix in staging
   - Redeploy to production

## Monitoring and Alerting

### Key Metrics

1. **Success Rates**
   - Phase 1 success rate (target: > 95%)
   - Phase 2 success rate (target: > 95%)
   - Phase 3 success rate (target: > 98%)
   - End-to-end success rate (target: > 90%)

2. **Latency**
   - Phase 1 p50 latency (target: < 5s)
   - Phase 1 p99 latency (target: < 10s)
   - Phase 2 p50 latency (target: < 5s)
   - Phase 2 p99 latency (target: < 10s)
   - Phase 3 p50 latency (target: < 3s)
   - Phase 3 p99 latency (target: < 5s)
   - End-to-end p50 latency (target: < 15s)
   - End-to-end p99 latency (target: < 30s)

3. **Error Rates**
   - Agent timeout rate (target: < 5%)
   - Agent error rate (target: < 2%)
   - Arbitrator error rate (target: < 1%)
   - Database error rate (target: < 1%)

### Alerts

1. **Critical Alerts** (Page on-call)
   - End-to-end success rate < 80%
   - Arbitrator error rate > 5%
   - Database connection failures
   - System unavailable

2. **Warning Alerts** (Slack notification)
   - End-to-end success rate < 90%
   - Phase latency exceeds target
   - Agent timeout rate > 10%
   - High error rate for specific agent

3. **Info Alerts** (Dashboard only)
   - Performance degradation
   - Increased load
   - Model fallback usage
   - Data quality warnings

## Success Criteria

The integration is complete and ready for production when:

1. **Testing**
   - [ ] All integration tests pass (100%)
   - [ ] All property-based tests pass (100+ iterations)
   - [ ] Performance tests meet targets
   - [ ] Error handling tests pass
   - [ ] Backward compatibility validated

2. **Deployment**
   - [ ] Staging deployment successful
   - [ ] Smoke tests pass in staging
   - [ ] Production deployment successful
   - [ ] Monitoring operational
   - [ ] Alerts configured

3. **Documentation**
   - [ ] README complete
   - [ ] API docs complete
   - [ ] Deployment guide complete
   - [ ] Runbook complete
   - [ ] Troubleshooting guide complete

4. **Sign-off**
   - [ ] Engineering team approval
   - [ ] Safety team approval
   - [ ] Operations team approval
   - [ ] Product team approval

## Risk Mitigation

### Identified Risks

1. **Performance Degradation**
   - Risk: System slower than expected
   - Mitigation: Performance tests, load testing, optimization
   - Fallback: Increase timeout limits, optimize queries

2. **Integration Issues**
   - Risk: Components don't work together correctly
   - Mitigation: Comprehensive integration tests
   - Fallback: Rollback to previous version

3. **Data Quality Issues**
   - Risk: Incomplete or incorrect data affects decisions
   - Mitigation: Data validation, confidence scoring
   - Fallback: Manual review for low confidence

4. **Model Availability**
   - Risk: Opus 4.5 unavailable
   - Mitigation: Automatic fallback to Sonnet
   - Fallback: Manual arbitration

5. **Backward Compatibility**
   - Risk: Breaking changes for existing clients
   - Mitigation: Backward compatibility tests, versioning
   - Fallback: Maintain legacy endpoints

## Next Steps

1. **Implement Integration Tests** (Week 1)
   - Create test structure
   - Implement end-to-end tests
   - Implement solution validation tests
   - Implement recovery plan tests

2. **Implement Performance Tests** (Week 1)
   - Create performance test framework
   - Implement latency tests
   - Implement load tests
   - Establish baselines

3. **Staging Deployment** (Week 2)
   - Deploy to staging
   - Run full test suite
   - Validate monitoring
   - Test rollback procedure

4. **Production Deployment** (Week 2)
   - Deploy to production
   - Monitor for 24 hours
   - Validate success metrics
   - Document lessons learned

5. **Post-Deployment** (Week 3)
   - Monitor for 1 week
   - Collect feedback
   - Optimize performance
   - Plan next iteration
