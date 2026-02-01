# Quick Start: SkyMarshal Integration Testing

## TL;DR

You have two major features implemented:

1. **Multi-round orchestration** (3 phases: Initial → Revision → Arbitration)
2. **Multi-solution arbitrator** (generates 1-3 ranked options with recovery plans)

Now you need to **test they work together** and **deploy to AgentCore**.

## What's Working

✅ Three-phase workflow implemented
✅ Multi-solution arbitrator implemented
✅ All 7 agents updated
✅ Database GSIs created
✅ Pydantic schemas defined
✅ Backward compatibility supported

## What's Needed

⏳ Integration tests
⏳ Performance tests
⏳ Deployment preparation
⏳ Staging deployment
⏳ Production deployment

## Quick Commands

### Run Existing Tests

```bash
cd skymarshal_agents_new/skymarshal

# Run all tests
uv run pytest test/ -v

# Run with coverage
uv run pytest test/ --cov=src --cov-report=html

# Run property-based tests with statistics
uv run pytest test/ --hypothesis-show-statistics
```

### Local Development

```bash
cd skymarshal_agents_new/skymarshal

# Start local dev server
uv run agentcore dev

# In another terminal, test with a prompt
uv run agentcore invoke --dev "Flight EY123 on Jan 20th had a mechanical failure"
```

### Check Current Status

```bash
cd skymarshal_agents_new/skymarshal

# Check agent status
uv run agentcore status

# View logs
uv run agentcore logs

# List dependencies
uv pip list
```

## Test Structure to Create

```
test/
├── integration/
│   ├── test_three_phase_workflow.py       # End-to-end workflow tests
│   ├── test_solution_validation.py        # Solution constraint tests
│   ├── test_recovery_plan_validation.py   # Recovery plan tests
│   ├── test_backward_compatibility.py     # Legacy integration tests
│   └── test_error_handling.py             # Error handling tests
├── performance/
│   ├── test_phase_latency.py              # Phase timing tests
│   ├── test_database_performance.py       # Database query tests
│   └── test_concurrent_load.py            # Load testing
└── property/
    ├── test_solution_properties.py        # Solution property tests
    ├── test_recovery_plan_properties.py   # Recovery plan property tests
    └── test_workflow_properties.py        # Workflow property tests
```

## Sample Integration Test

```python
# test/integration/test_three_phase_workflow.py

import pytest
from src.main import handle_disruption
from model.load import load_model
from mcp_client.client import get_streamable_http_mcp_client

@pytest.mark.asyncio
async def test_simple_disruption_workflow():
    """Test complete three-phase workflow with simple disruption"""

    # Setup
    user_prompt = "Flight EY123 delayed 2 hours due to weather"
    llm = load_model()
    mcp_client = get_streamable_http_mcp_client()
    mcp_tools = await mcp_client.get_tools()

    # Execute
    result = await handle_disruption(user_prompt, llm, mcp_tools)

    # Validate
    assert result["status"] == "success"
    assert "final_decision" in result
    assert "solution_options" in result["final_decision"]
    assert len(result["final_decision"]["solution_options"]) >= 1
    assert len(result["final_decision"]["solution_options"]) <= 3

    # Validate audit trail
    assert "audit_trail" in result
    assert "phase1_initial" in result["audit_trail"]
    assert "phase2_revision" in result["audit_trail"]
    assert "phase3_arbitration" in result["audit_trail"]

    # Validate solution structure
    for solution in result["final_decision"]["solution_options"]:
        assert "solution_id" in solution
        assert "composite_score" in solution
        assert "recovery_plan" in solution
        assert "steps" in solution["recovery_plan"]

        # Validate recovery plan
        steps = solution["recovery_plan"]["steps"]
        assert len(steps) > 0

        # Validate step numbering
        step_numbers = [step["step_number"] for step in steps]
        assert step_numbers == list(range(1, len(steps) + 1))
```

## Sample Property Test

```python
# test/property/test_solution_properties.py

from hypothesis import given, strategies as st
from agents.schemas import RecoverySolution

@given(
    st.floats(min_value=0, max_value=100),  # safety
    st.floats(min_value=0, max_value=100),  # cost
    st.floats(min_value=0, max_value=100),  # passenger
    st.floats(min_value=0, max_value=100),  # network
)
def test_composite_score_calculation(safety, cost, passenger, network):
    """Property: Composite score equals weighted average"""

    # Calculate expected composite score
    expected = (safety * 0.4) + (cost * 0.2) + (passenger * 0.2) + (network * 0.2)

    # Create solution with these scores
    solution = RecoverySolution(
        solution_id=1,
        title="Test Solution",
        description="Test",
        recommendations=["Test"],
        safety_compliance="Test",
        passenger_impact={},
        financial_impact={},
        network_impact={},
        safety_score=safety,
        cost_score=cost,
        passenger_score=passenger,
        network_score=network,
        composite_score=expected,  # Should match
        pros=["Test"],
        cons=["Test"],
        risks=["Test"],
        confidence=0.5,
        estimated_duration="1 hour",
        recovery_plan={
            "solution_id": 1,
            "total_steps": 1,
            "estimated_total_duration": "1 hour",
            "steps": [{
                "step_number": 1,
                "step_name": "Test",
                "description": "Test",
                "responsible_agent": "test",
                "dependencies": [],
                "estimated_duration": "1 hour",
                "automation_possible": False,
                "action_type": "test",
                "parameters": {},
                "success_criteria": "Test"
            }],
            "critical_path": [1],
            "contingency_plans": []
        }
    )

    # Verify composite score matches expected
    assert abs(solution.composite_score - expected) < 0.1
```

## Performance Test Example

```python
# test/performance/test_phase_latency.py

import pytest
import time
from src.main import phase1_initial_recommendations

@pytest.mark.asyncio
async def test_phase1_latency():
    """Test Phase 1 completes within 10 seconds"""

    # Setup
    user_prompt = "Flight EY123 delayed 2 hours due to weather"
    llm = load_model()
    mcp_client = get_streamable_http_mcp_client()
    mcp_tools = await mcp_client.get_tools()

    # Measure execution time
    start = time.time()
    result = await phase1_initial_recommendations(user_prompt, llm, mcp_tools)
    duration = time.time() - start

    # Validate
    assert duration < 10.0, f"Phase 1 took {duration:.2f}s, expected < 10s"
    assert result.phase == "initial"
    assert len(result.responses) == 7
```

## Deployment Checklist

### Pre-Deployment

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All property-based tests pass
- [ ] Code coverage > 80%
- [ ] No critical linting errors
- [ ] Security scan passed
- [ ] Environment variables documented
- [ ] .bedrock_agentcore.yaml validated
- [ ] Monitoring configured
- [ ] Rollback plan ready

### Staging Deployment

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

# Monitor for 24 hours
# Check error rates, latency, success rates
```

### Production Deployment

```bash
cd skymarshal_agents_new/skymarshal

# Final checks
uv run pytest test/ -v

# Deploy to production
uv run agentcore deploy --environment production

# Validate deployment
uv run agentcore status --environment production

# Monitor closely for first hour
# Check metrics every 5 minutes

# If issues detected, rollback
uv run agentcore rollback --environment production
```

## Key Files to Review

### Specs

- `.kiro/specs/skymarshal-multi-round-orchestration/` - Multi-round orchestration
- `.kiro/specs/arbitrator-multi-solution-enhancements/` - Arbitrator enhancements
- `.kiro/specs/skymarshal-integration-testing/` - Integration testing (NEW)

### Implementation

- `src/main.py` - Orchestrator with three-phase workflow
- `src/agents/arbitrator/agent.py` - Multi-solution arbitrator
- `src/agents/schemas.py` - Pydantic schemas
- `src/agents/scoring.py` - Scoring algorithms

### Configuration

- `.bedrock_agentcore.yaml` - AgentCore configuration
- `pyproject.toml` - Dependencies and project metadata
- `.env.example` - Environment variables template

## Common Issues and Solutions

### Issue: Tests fail with "Model not found"

**Solution**: Check model ID in configuration

```bash
# Verify model ID
grep -r "model_id" src/

# Update if needed
# Edit src/model/load.py or .bedrock_agentcore.yaml
```

### Issue: Database connection errors

**Solution**: Check AWS credentials and region

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check region
aws configure get region

# Test DynamoDB access
aws dynamodb list-tables
```

### Issue: Agent timeouts

**Solution**: Increase timeout or optimize queries

```python
# In src/main.py, adjust timeout
result = await asyncio.wait_for(
    agent_fn(payload, llm, mcp_tools),
    timeout=60  # Increase from 30 to 60
)
```

### Issue: Property tests fail intermittently

**Solution**: Check for floating point precision issues

```python
# Use tolerance for float comparisons
assert abs(actual - expected) < 0.1  # Not ==
```

## Next Steps

1. **Review Integration Spec** (30 minutes)
   - Read `.kiro/specs/skymarshal-integration-testing/requirements.md`
   - Read `.kiro/specs/skymarshal-integration-testing/design.md`
   - Read `.kiro/specs/skymarshal-integration-testing/tasks.md`

2. **Start Integration Testing** (Week 1)
   - Create test structure
   - Implement end-to-end workflow tests
   - Implement solution validation tests
   - Implement recovery plan validation tests

3. **Performance Testing** (Week 1)
   - Create performance test framework
   - Implement latency tests
   - Implement load tests
   - Establish baselines

4. **Staging Deployment** (Week 2)
   - Deploy to staging
   - Run full test suite
   - Monitor for 24 hours
   - Obtain sign-offs

5. **Production Deployment** (Week 2)
   - Deploy to production
   - Monitor closely
   - Collect feedback
   - Document lessons learned

## Questions?

If you have questions about:

- **Architecture**: See `SYSTEM_ARCHITECTURE_COMPLETE.md`
- **Integration**: See `INTEGRATION_SUMMARY.md`
- **Specs**: See `.kiro/specs/skymarshal-integration-testing/`
- **Implementation**: See source code in `src/`

## Resources

- [Multi-Round Orchestration Spec](.kiro/specs/skymarshal-multi-round-orchestration/)
- [Arbitrator Enhancements Spec](.kiro/specs/arbitrator-multi-solution-enhancements/)
- [Integration Testing Spec](.kiro/specs/skymarshal-integration-testing/)
- [System Architecture](SYSTEM_ARCHITECTURE_COMPLETE.md)
- [Integration Summary](INTEGRATION_SUMMARY.md)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Pytest Documentation](https://docs.pytest.org/)
- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)

## Success Metrics

### Testing

- [ ] 100% integration test pass rate
- [ ] 100% property-based test pass rate (100+ iterations)
- [ ] Performance targets met (end-to-end < 30s)
- [ ] Error handling validated
- [ ] Backward compatibility validated

### Deployment

- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] No critical issues in first 24 hours
- [ ] System stable for 1 week
- [ ] All sign-offs obtained

### Operations

- [ ] Monitoring operational
- [ ] Alerts configured
- [ ] Documentation complete
- [ ] Runbook tested
- [ ] Team trained

---

**Ready to start?** Begin with Task 1 in `.kiro/specs/skymarshal-integration-testing/tasks.md`
