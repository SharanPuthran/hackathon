# Arbitrator Multi-Solution Enhancement Guide

## Overview

The SkyMarshal arbitrator has been enhanced to provide 1-3 ranked solution options instead of a single decision. This enables better human-in-the-loop decision making by presenting multiple viable alternatives with detailed trade-off analysis.

## Key Features

### 1. Multiple Solution Options (1-3 Ranked)

The arbitrator now generates between 1 and 3 solution options, each with:

- **Multi-dimensional scoring**: Safety (40%), Cost (20%), Passenger Impact (20%), Network Impact (20%)
- **Composite score**: Weighted average of all dimensions
- **Pros, cons, and risks**: Clear trade-off analysis
- **Confidence level**: How confident the arbitrator is in this solution
- **Detailed recovery plan**: Step-by-step implementation workflow

### 2. Recovery Plans

Each solution includes a complete recovery plan with:

- **Sequential steps**: Ordered workflow with dependencies
- **Responsible agents**: Who executes each step
- **Automation flags**: Which steps can be automated
- **Success criteria**: How to verify completion
- **Rollback procedures**: What to do if a step fails
- **Contingency plans**: Alternative approaches for failures
- **Critical path**: Longest dependency chain (bottleneck)

### 3. S3 Integration

Decision records are automatically stored to two S3 buckets:

- **Knowledge Base Bucket** (`skymarshal-prod-knowledge-base-368613657554`): For historical learning and pattern recognition
- **Decisions Bucket** (`skymarshal-prod-decisions-368613657554`): For audit trails and regulatory compliance

Storage features:

- Date-partitioned keys: `decisions/YYYY/MM/DD/disruption_id.json`
- Metadata tagging for easy retrieval
- Human override flag tracking
- Automatic deduplication

### 4. Solution Selection API

A new API endpoint allows recording which solution was selected by the human operator:

```python
from api.endpoints import handle_solution_selection, SolutionSelectionRequest

# Record solution selection
request = SolutionSelectionRequest(
    disruption_id="DISR-2026-001",
    selected_solution_id=2,
    selection_rationale="Prioritized passenger experience over cost"
)

response = await handle_solution_selection(request)
# Response includes S3 storage status and decision record
```

### 5. Decision Reports

Generate comprehensive audit-ready reports in multiple formats:

```python
from agents.report_generator import generate_decision_report, export_report

# Generate report
report = generate_decision_report(
    arbitrator_output=output,
    disruption_id="DISR-2026-001",
    flight_number="EY123",
    disruption_type="crew"
)

# Export as JSON
json_str = export_report(report, format="json")

# Export as Markdown
md_str = export_report(report, format="markdown")

# Export to file
export_report(report, format="markdown", output_path="report.md")
```

## Usage Examples

### Example 1: Basic Multi-Solution Workflow

```python
from agents.arbitrator import arbitrate
from model.load import load_model

# Load model
llm = await load_model()

# Arbitrate with agent responses
result = await arbitrate(
    phase1_responses=phase1_responses,
    phase2_responses=phase2_responses,
    llm=llm
)

# Access solution options
print(f"Generated {len(result.solution_options)} solutions")
for solution in result.solution_options:
    print(f"Solution {solution.solution_id}: {solution.title}")
    print(f"  Composite Score: {solution.composite_score:.1f}/100")
    print(f"  Safety: {solution.safety_score:.1f}, Cost: {solution.cost_score:.1f}")
    print(f"  Passenger: {solution.passenger_score:.1f}, Network: {solution.network_score:.1f}")
    print(f"  Pros: {', '.join(solution.pros)}")
    print(f"  Cons: {', '.join(solution.cons)}")
    print()

# Get recommended solution
recommended_id = result.recommended_solution_id
recommended = next(s for s in result.solution_options if s.solution_id == recommended_id)
print(f"Recommended: {recommended.title}")
```

### Example 2: Accessing Recovery Plans

```python
# Get recovery plan for a solution
solution = result.solution_options[0]
recovery_plan = solution.recovery_plan

print(f"Total Steps: {recovery_plan.total_steps}")
print(f"Estimated Duration: {recovery_plan.estimated_total_duration}")
print(f"Critical Path: {recovery_plan.critical_path}")

# Iterate through steps
for step in recovery_plan.steps:
    print(f"\nStep {step.step_number}: {step.step_name}")
    print(f"  Description: {step.description}")
    print(f"  Responsible: {step.responsible_agent}")
    print(f"  Duration: {step.estimated_duration}")
    print(f"  Dependencies: {step.dependencies}")
    print(f"  Automation: {'Yes' if step.automation_possible else 'No'}")
    print(f"  Success Criteria: {step.success_criteria}")
    if step.rollback_procedure:
        print(f"  Rollback: {step.rollback_procedure}")
```

### Example 3: Recording Human Selection

```python
from api.endpoints import register_arbitrator_output, handle_solution_selection
from api.endpoints import SolutionSelectionRequest

# Step 1: Register arbitrator output
register_arbitrator_output("DISR-2026-001", arbitrator_output)

# Step 2: Human selects a solution (e.g., via UI)
selected_id = 2  # Human chose solution 2

# Step 3: Record the selection
request = SolutionSelectionRequest(
    disruption_id="DISR-2026-001",
    selected_solution_id=selected_id,
    selection_rationale="Prioritized passenger experience despite higher cost"
)

response = await handle_solution_selection(request)

# Check storage status
if response.s3_storage_status["skymarshal-prod-knowledge-base-368613657554"]:
    print("✓ Stored to knowledge base for learning")
if response.s3_storage_status["skymarshal-prod-decisions-368613657554"]:
    print("✓ Stored to decisions bucket for audit")

# Check if human overrode recommendation
if response.decision_record.human_override:
    print("⚠ Human selected different solution than recommended")
```

### Example 4: Generating Decision Reports

```python
from agents.report_generator import (
    generate_decision_report,
    export_report,
    validate_report_completeness
)

# Generate comprehensive report
report = generate_decision_report(
    arbitrator_output=result,
    disruption_id="DISR-2026-001",
    flight_number="EY123",
    disruption_type="crew"
)

# Validate completeness
validation = validate_report_completeness(report)
if all(validation.values()):
    print("✓ Report is complete")
else:
    missing = [k for k, v in validation.items() if not v]
    print(f"⚠ Missing sections: {', '.join(missing)}")

# Export in multiple formats
json_report = export_report(report, format="json", output_path="report.json")
md_report = export_report(report, format="markdown", output_path="report.md")

print(f"Reports saved: {json_report}, {md_report}")
```

## Schema Reference

### RecoverySolution

```python
class RecoverySolution(BaseModel):
    solution_id: int  # 1-3
    title: str
    description: str

    # Scoring (0-100 scale)
    safety_score: float
    cost_score: float
    passenger_score: float
    network_score: float
    composite_score: float  # Weighted average

    # Impact details
    safety_compliance: str
    passenger_impact: Dict[str, Any]
    financial_impact: Dict[str, Any]
    network_impact: Dict[str, Any]

    # Trade-off analysis
    pros: List[str]
    cons: List[str]
    risks: List[str]

    # Metadata
    estimated_duration: str
    confidence: float  # 0.0-1.0
    recommendations: List[str]

    # Recovery workflow
    recovery_plan: RecoveryPlan
```

### RecoveryPlan

```python
class RecoveryPlan(BaseModel):
    solution_id: int
    total_steps: int
    estimated_total_duration: str
    steps: List[RecoveryStep]
    critical_path: List[int]  # Step numbers on critical path
    contingency_plans: List[Dict[str, Any]]
```

### RecoveryStep

```python
class RecoveryStep(BaseModel):
    step_number: int
    step_name: str
    description: str
    responsible_agent: str
    dependencies: List[int]  # Step numbers that must complete first
    estimated_duration: str
    automation_possible: bool
    action_type: str  # notify, rebook, schedule, coordinate, etc.
    parameters: Dict[str, Any]
    success_criteria: str
    rollback_procedure: Optional[str]
```

### DecisionRecord

```python
class DecisionRecord(BaseModel):
    disruption_id: str
    timestamp: str  # ISO format
    flight_number: str
    disruption_type: str
    disruption_severity: str

    # Agent responses
    agent_responses: Dict[str, Any]

    # Solutions
    solution_options: List[RecoverySolution]
    recommended_solution_id: int
    selected_solution_id: int
    selection_rationale: str

    # Conflicts
    conflicts_identified: List[ConflictDetail]
    conflict_resolutions: List[ResolutionDetail]

    # Metadata
    human_override: bool  # True if selected != recommended
```

## Scoring Algorithm

The composite score is calculated as a weighted average:

```
composite_score = (safety_score × 0.4) +
                  (cost_score × 0.2) +
                  (passenger_score × 0.2) +
                  (network_score × 0.2)
```

### Score Interpretation

- **90-100**: Excellent - Minimal impact, high compliance
- **70-89**: Good - Acceptable trade-offs
- **50-69**: Fair - Significant trade-offs required
- **Below 50**: Poor - Major compromises needed

### Dimension-Specific Scoring

**Safety Score (40% weight)**:

- Based on margin above minimum regulatory requirements
- Higher score = more safety buffer
- Never compromised for business reasons

**Cost Score (20% weight)**:

- Based on total financial impact
- Higher score = lower cost
- Includes crew, passenger compensation, operational costs

**Passenger Score (20% weight)**:

- Based on delay hours and affected passenger count
- Higher score = less passenger impact
- Considers cancellations, rebooking, compensation

**Network Score (20% weight)**:

- Based on downstream flight impacts
- Higher score = less network disruption
- Considers connection misses, propagation effects

## Backward Compatibility

The enhanced arbitrator maintains full backward compatibility:

- **Legacy fields populated**: `final_decision` and `recommendations` are automatically populated from the recommended solution
- **Existing integrations work**: The orchestrator and other components continue to function without changes
- **Optional new fields**: `solution_options` and `recommended_solution_id` are optional, defaulting to `None`

Example of backward-compatible output:

```python
# New multi-solution output
output = ArbitratorOutput(
    solution_options=[solution1, solution2, solution3],
    recommended_solution_id=1,
    # Legacy fields auto-populated from solution 1:
    final_decision="Assign standby crew...",
    recommendations=["Contact standby crew", "Update manifest", ...]
)

# Legacy code still works
print(output.final_decision)  # Works!
print(output.recommendations)  # Works!

# New code can access solutions
print(output.solution_options)  # New feature!
```

## Best Practices

### 1. Always Register Arbitrator Output

Before recording solution selection, register the arbitrator output:

```python
register_arbitrator_output(disruption_id, arbitrator_output)
```

This enables the API to validate solution IDs and detect human overrides.

### 2. Provide Selection Rationale

Always include a rationale when recording human selection:

```python
request = SolutionSelectionRequest(
    disruption_id="DISR-2026-001",
    selected_solution_id=2,
    selection_rationale="Crew availability changed, making solution 2 more viable"
)
```

This helps with historical learning and pattern recognition.

### 3. Check S3 Storage Status

Always verify that decision records were successfully stored:

```python
response = await handle_solution_selection(request)
for bucket, status in response.s3_storage_status.items():
    if not status:
        logger.error(f"Failed to store to {bucket}")
```

### 4. Generate Reports for Audit

For regulatory compliance, always generate and archive decision reports:

```python
report = generate_decision_report(output, disruption_id, flight_number, disruption_type)
export_report(report, format="json", output_path=f"reports/{disruption_id}.json")
export_report(report, format="markdown", output_path=f"reports/{disruption_id}.md")
```

### 5. Validate Recovery Plans

Before executing a recovery plan, validate its structure:

```python
recovery_plan = solution.recovery_plan

# Check for circular dependencies
assert len(recovery_plan.critical_path) > 0, "Critical path must be defined"

# Verify all dependencies are valid
for step in recovery_plan.steps:
    for dep in step.dependencies:
        assert 1 <= dep < step.step_number, f"Invalid dependency {dep} in step {step.step_number}"
```

## Testing

Comprehensive test suites are available:

- **test_arbitrator.py**: 31 tests for arbitrator functionality
- **test_s3_storage.py**: 12 tests for S3 integration
- **test_api_endpoints.py**: 18 tests for API endpoints

Run all tests:

```bash
uv run pytest test/test_arbitrator.py test/test_s3_storage.py test/test_api_endpoints.py -v
```

## Troubleshooting

### Issue: Solution options not generated

**Symptom**: `solution_options` is `None` or empty

**Solution**: Check that the LLM is responding with the correct format. The arbitrator prompt has been updated to request 1-3 solutions. If using a mock LLM for testing, ensure it returns properly formatted solution options.

### Issue: Composite score validation error

**Symptom**: `ValidationError: Composite score X does not match weighted average Y`

**Solution**: Ensure the composite score matches the weighted formula:

```python
composite = (safety * 0.4) + (cost * 0.2) + (passenger * 0.2) + (network * 0.2)
```

### Issue: S3 storage fails

**Symptom**: `s3_storage_status` shows `False` for one or both buckets

**Solution**:

1. Verify AWS credentials are configured
2. Check bucket names are correct
3. Ensure IAM permissions include `s3:PutObject` and `s3:PutObjectTagging`
4. Check bucket exists in the correct region

### Issue: Recovery plan validation fails

**Symptom**: `ValidationError: Step X cannot depend on later step Y`

**Solution**: Ensure all dependencies reference earlier steps only. Dependencies must form a directed acyclic graph (DAG) with no cycles.

## Future Enhancements

Potential future improvements:

1. **Machine Learning Integration**: Use historical decision records to train models that predict optimal solutions
2. **Real-time Collaboration**: Allow multiple operators to review and vote on solutions
3. **Simulation Mode**: Test recovery plans in simulation before execution
4. **Cost Optimization**: Automatically suggest cost-saving alternatives
5. **PDF Report Generation**: Implement full PDF export with charts and visualizations

## Support

For questions or issues:

- Review the design document: `.kiro/specs/arbitrator-multi-solution-enhancements/design.md`
- Check the requirements: `.kiro/specs/arbitrator-multi-solution-enhancements/requirements.md`
- Run the test suite to verify functionality
- Check logs for detailed error messages
