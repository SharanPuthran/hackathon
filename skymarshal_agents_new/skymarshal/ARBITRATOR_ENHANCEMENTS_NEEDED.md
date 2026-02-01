# Arbitrator Enhancements - Requirements Analysis

**Date:** February 1, 2026  
**Status:** 📋 Requirements Identified - Implementation Needed

## Current State ✅

The arbitrator is **fully functional** with the following capabilities:

### Working Features:

1. ✅ **Conflict Identification**: Identifies safety vs business, safety vs safety conflicts
2. ✅ **Safety-First Decision Making**: Enforces binding constraints
3. ✅ **Structured Output**: Returns final_decision, recommendations, conflicts, resolutions
4. ✅ **Confidence Scoring**: Provides 0.0-1.0 confidence with explanation
5. ✅ **Audit Trail**: Complete reasoning and justification
6. ✅ **Model Fallback**: Opus 4.5 → Sonnet 4.5 automatic fallback

### Current Output Structure:

```python
{
    "final_decision": str,              # Single recommended decision
    "recommendations": List[str],        # Action items (3-7)
    "conflicts_identified": List[dict],  # Conflicts found
    "conflict_resolutions": List[dict],  # How resolved
    "safety_overrides": List[dict],      # Safety constraints enforced
    "justification": str,                # Overall explanation
    "reasoning": str,                    # Detailed analysis
    "confidence": float,                 # 0.0-1.0
    "timestamp": str,
    "model_used": str,
    "duration_seconds": float
}
```

## Required Enhancements 🎯

### 1. Multiple Solution Options (1-3 Ranked Solutions)

**Requirement:**

> Arbitrator should provide 1-3 ranked solution options to make it easier for human-in-the-loop to decide

**Current Gap:**

- Arbitrator currently provides ONE final decision
- No ranking of alternative solutions
- No comparison between options

**Needed Changes:**

#### A. Schema Enhancement

Add new fields to `ArbitratorOutput`:

```python
class RecoverySolution(BaseModel):
    """A single recovery solution option"""
    solution_id: int  # 1, 2, or 3
    title: str  # Short title (e.g., "6-Hour Delay with Crew Change")
    description: str  # Detailed description
    recommendations: List[str]  # Specific action steps

    # Impact Assessment
    safety_compliance: str  # How it satisfies safety constraints
    passenger_impact: Dict[str, Any]  # Passengers affected, delays, etc.
    financial_impact: Dict[str, Any]  # Costs, revenue impact
    network_impact: Dict[str, Any]  # Downstream effects

    # Scoring
    safety_score: float  # 0-100
    cost_score: float  # 0-100
    passenger_score: float  # 0-100
    network_score: float  # 0-100
    composite_score: float  # Weighted average

    # Metadata
    pros: List[str]  # Advantages
    cons: List[str]  # Disadvantages
    risks: List[str]  # Potential risks
    confidence: float  # 0.0-1.0
    estimated_duration: str  # Time to implement

class ArbitratorOutput(BaseModel):
    # ... existing fields ...

    # NEW: Multiple solution options
    solution_options: List[RecoverySolution] = Field(
        description="1-3 ranked recovery solution options",
        min_items=1,
        max_items=3
    )
    recommended_solution_id: int = Field(
        description="ID of the recommended solution (1, 2, or 3)"
    )
```

#### B. Prompt Enhancement

Update arbitrator system prompt to:

- Generate 1-3 distinct solution options
- Rank by composite score
- Identify Pareto-optimal solutions (different trade-off points)
- Clearly mark recommended solution

**Example Output:**

```json
{
  "solution_options": [
    {
      "solution_id": 1,
      "title": "6-Hour Delay with Crew Change",
      "description": "Delay flight 6 hours to complete maintenance inspection and arrange crew change",
      "recommendations": [
        "Delay flight by 6 hours",
        "Source replacement crew",
        "Complete full maintenance inspection",
        "Notify passengers and provide accommodation"
      ],
      "safety_compliance": "Fully satisfies all safety constraints",
      "passenger_impact": {
        "affected_passengers": 180,
        "delay_hours": 6,
        "compensation_cost": 45000
      },
      "financial_impact": {
        "total_cost": 120000,
        "revenue_loss": 30000
      },
      "composite_score": 85.0,
      "pros": [
        "Fully compliant with all safety requirements",
        "Allows thorough maintenance inspection",
        "High confidence in successful execution"
      ],
      "cons": [
        "Higher cost than shorter delay",
        "Significant passenger inconvenience"
      ],
      "confidence": 0.95
    },
    {
      "solution_id": 2,
      "title": "Flight Cancellation with Rebooking",
      "description": "Cancel flight and rebook passengers on alternative flights",
      "composite_score": 70.0,
      "confidence": 0.85
    }
  ],
  "recommended_solution_id": 1
}
```

---

### 2. S3 Knowledge Base Integration for Historical Learning

**Requirement:**

> Once solution is selected by human, push to S3 knowledge base bucket for historical learning

**Current Gap:**

- No S3 integration in arbitrator
- No mechanism to store human-selected decisions
- No feedback loop for learning

**Needed Changes:**

#### A. Decision Record Schema

```python
class DecisionRecord(BaseModel):
    """Record of a decision for historical learning"""

    # Disruption Context
    disruption_id: str  # Unique ID
    timestamp: str  # ISO 8601
    flight_number: str
    disruption_type: str
    disruption_severity: str  # low, medium, high, critical

    # Agent Recommendations
    agent_responses: Dict[str, Any]  # All agent responses

    # Arbitrator Analysis
    solution_options: List[RecoverySolution]  # All options presented
    recommended_solution_id: int  # Arbitrator's recommendation

    # Human Decision
    selected_solution_id: int  # What human chose
    selection_rationale: Optional[str]  # Why human chose it
    human_override: bool  # Did human override arbitrator?

    # Outcome (filled in later)
    outcome_status: Optional[str]  # success, partial_success, failure
    actual_delay: Optional[float]  # Actual delay in hours
    actual_cost: Optional[float]  # Actual cost
    lessons_learned: Optional[str]  # Post-incident analysis
```

#### B. S3 Integration Function

```python
async def store_decision_to_s3(
    decision_record: DecisionRecord,
    bucket_name: str = "skymarshal-prod-knowledge-base-368613657554"
) -> bool:
    """
    Store decision record to S3 for historical learning.

    File structure:
    s3://bucket/decisions/YYYY/MM/DD/{disruption_id}.json

    This enables:
    - Historical pattern analysis
    - Success rate tracking
    - Continuous learning
    """
    import boto3
    import json
    from datetime import datetime

    s3 = boto3.client('s3')

    # Generate S3 key with date partitioning
    dt = datetime.fromisoformat(decision_record.timestamp)
    s3_key = f"decisions/{dt.year}/{dt.month:02d}/{dt.day:02d}/{decision_record.disruption_id}.json"

    # Upload to S3
    s3.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=json.dumps(decision_record.model_dump(), indent=2),
        ContentType='application/json',
        Metadata={
            'disruption_type': decision_record.disruption_type,
            'flight_number': decision_record.flight_number,
            'selected_solution': str(decision_record.selected_solution_id)
        }
    )

    return True
```

#### C. API Endpoint for Human Selection

```python
@app.post("/api/select-solution")
async def select_solution(
    disruption_id: str,
    selected_solution_id: int,
    rationale: Optional[str] = None
):
    """
    Record human's solution selection and store to S3.

    This endpoint is called when the Duty Manager selects
    a solution from the arbitrator's recommendations.
    """
    # Load original decision
    decision_record = load_decision_record(disruption_id)

    # Update with human selection
    decision_record.selected_solution_id = selected_solution_id
    decision_record.selection_rationale = rationale
    decision_record.human_override = (
        selected_solution_id != decision_record.recommended_solution_id
    )

    # Store to S3 for historical learning
    await store_decision_to_s3(decision_record)

    return {"status": "success", "message": "Decision recorded for historical learning"}
```

---

### 3. Recovery Mechanisms and Steps

**Requirement:**

> Arbitrator should suggest recovery mechanisms and steps for later implementation by recovery agents

**Current Gap:**

- Recommendations are high-level action items
- No detailed recovery procedures
- No structured recovery workflow

**Needed Changes:**

#### A. Recovery Step Schema

```python
class RecoveryStep(BaseModel):
    """A single step in the recovery process"""
    step_number: int
    step_name: str
    description: str
    responsible_agent: str  # Which agent/system executes this
    dependencies: List[int]  # Step numbers that must complete first
    estimated_duration: str  # e.g., "15 minutes", "2 hours"
    automation_possible: bool  # Can this be automated?

    # Execution details
    action_type: str  # "notify", "rebook", "schedule", "coordinate", etc.
    parameters: Dict[str, Any]  # Parameters for execution

    # Validation
    success_criteria: str  # How to verify step completed
    rollback_procedure: Optional[str]  # What to do if step fails

class RecoveryPlan(BaseModel):
    """Complete recovery plan for a solution"""
    solution_id: int
    total_steps: int
    estimated_total_duration: str

    steps: List[RecoveryStep]

    # Critical path
    critical_path: List[int]  # Step numbers on critical path

    # Contingencies
    contingency_plans: List[Dict[str, Any]]  # What if steps fail?
```

#### B. Enhanced Solution with Recovery Plan

```python
class RecoverySolution(BaseModel):
    # ... existing fields ...

    # NEW: Detailed recovery plan
    recovery_plan: RecoveryPlan = Field(
        description="Detailed step-by-step recovery plan"
    )
```

**Example Recovery Plan:**

```json
{
  "solution_id": 1,
  "title": "6-Hour Delay with Crew Change",
  "recovery_plan": {
    "total_steps": 8,
    "estimated_total_duration": "6 hours 30 minutes",
    "steps": [
      {
        "step_number": 1,
        "step_name": "Notify Crew Scheduling",
        "description": "Contact crew scheduling to source replacement crew",
        "responsible_agent": "crew_compliance",
        "dependencies": [],
        "estimated_duration": "15 minutes",
        "automation_possible": true,
        "action_type": "coordinate",
        "parameters": {
          "crew_type": "qualified_pilots",
          "required_certifications": ["A380", "international"],
          "availability_window": "6 hours"
        },
        "success_criteria": "Replacement crew confirmed and en route"
      },
      {
        "step_number": 2,
        "step_name": "Notify Passengers",
        "description": "Send delay notification to all 180 passengers",
        "responsible_agent": "guest_experience",
        "dependencies": [],
        "estimated_duration": "10 minutes",
        "automation_possible": true,
        "action_type": "notify",
        "parameters": {
          "notification_channels": ["email", "sms", "app"],
          "message_template": "delay_notification",
          "delay_hours": 6
        },
        "success_criteria": "All passengers notified successfully"
      },
      {
        "step_number": 3,
        "step_name": "Schedule Maintenance Inspection",
        "description": "Schedule comprehensive 6-hour maintenance inspection",
        "responsible_agent": "maintenance",
        "dependencies": [],
        "estimated_duration": "6 hours",
        "automation_possible": false,
        "action_type": "schedule",
        "parameters": {
          "inspection_type": "comprehensive",
          "aircraft_id": "A6-EUE",
          "inspection_items": ["hydraulics", "landing_gear", "engines"]
        },
        "success_criteria": "Inspection complete and aircraft cleared"
      }
      // ... more steps
    ],
    "critical_path": [3, 1, 7], // Maintenance, crew, departure
    "contingency_plans": [
      {
        "trigger": "Replacement crew not available",
        "action": "Escalate to flight cancellation (Solution 2)"
      }
    ]
  }
}
```

---

### 4. Detailed Decision Report

**Requirement:**

> Detailed report of decision with thought process, assessments, impact, considerations - can be downloaded later

**Current Gap:**

- Reasoning is text-based, not structured
- No downloadable report format
- Limited impact analysis detail

**Needed Changes:**

#### A. Decision Report Schema

```python
class ImpactAssessment(BaseModel):
    """Detailed impact assessment"""
    category: str  # "safety", "financial", "passenger", "network", "cargo"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    quantitative_metrics: Dict[str, Any]
    mitigation_strategies: List[str]

class DecisionReport(BaseModel):
    """Comprehensive decision report for download"""

    # Header
    report_id: str
    generated_at: str
    disruption_summary: str

    # Agent Analysis Section
    agent_assessments: Dict[str, Dict[str, Any]]  # All agent responses

    # Conflict Analysis Section
    conflicts_identified: List[ConflictDetail]
    conflict_resolutions: List[ResolutionDetail]
    safety_overrides: List[SafetyOverride]

    # Solution Options Section
    solution_options: List[RecoverySolution]
    recommended_solution: RecoverySolution

    # Impact Analysis Section
    impact_assessments: List[ImpactAssessment]

    # Decision Rationale Section
    decision_rationale: str
    key_considerations: List[str]
    assumptions_made: List[str]
    uncertainties: List[str]

    # Historical Context Section
    similar_past_events: List[Dict[str, Any]]
    historical_success_rates: Dict[str, float]
    lessons_applied: List[str]

    # Confidence Analysis Section
    confidence_score: float
    confidence_factors: Dict[str, str]  # What increases/decreases confidence
    data_quality_assessment: str

    # Metadata
    model_used: str
    processing_time: float
    agents_consulted: List[str]
```

#### B. Report Generation Function

```python
def generate_decision_report(
    arbitrator_output: ArbitratorOutput,
    agent_responses: Dict[str, AgentResponse],
    user_prompt: str
) -> DecisionReport:
    """
    Generate comprehensive decision report from arbitrator output.

    This report can be:
    - Downloaded as PDF
    - Exported as JSON
    - Stored for regulatory compliance
    - Used for post-incident analysis
    """
    # ... implementation ...
```

#### C. Report Export Formats

```python
# PDF Export
async def export_report_pdf(report: DecisionReport) -> bytes:
    """Generate PDF report using reportlab or weasyprint"""
    pass

# JSON Export
async def export_report_json(report: DecisionReport) -> str:
    """Export as structured JSON"""
    return report.model_dump_json(indent=2)

# Markdown Export
async def export_report_markdown(report: DecisionReport) -> str:
    """Export as human-readable markdown"""
    pass
```

---

## Implementation Priority

### Phase 1: Multiple Solutions (High Priority) 🔴

- **Effort**: Medium (2-3 days)
- **Impact**: High - Improves human decision-making
- **Dependencies**: None
- **Tasks**:
  1. Extend `ArbitratorOutput` schema with `RecoverySolution`
  2. Update arbitrator prompt to generate 1-3 solutions
  3. Add solution ranking logic
  4. Update tests

### Phase 2: Recovery Plans (High Priority) 🔴

- **Effort**: Medium (2-3 days)
- **Impact**: High - Enables automated recovery
- **Dependencies**: Phase 1
- **Tasks**:
  1. Create `RecoveryStep` and `RecoveryPlan` schemas
  2. Update arbitrator prompt to generate recovery steps
  3. Add recovery plan validation
  4. Update tests

### Phase 3: S3 Integration (Medium Priority) 🟡

- **Effort**: Low (1 day)
- **Impact**: Medium - Enables historical learning
- **Dependencies**: None
- **Tasks**:
  1. Create `DecisionRecord` schema
  2. Implement `store_decision_to_s3()` function
  3. Add API endpoint for human selection
  4. Test S3 upload

### Phase 4: Decision Reports (Medium Priority) 🟡

- **Effort**: Medium (2 days)
- **Impact**: Medium - Improves auditability
- **Dependencies**: Phase 1, Phase 2
- **Tasks**:
  1. Create `DecisionReport` schema
  2. Implement report generation
  3. Add PDF/JSON/Markdown export
  4. Update tests

---

## Total Effort Estimate

- **Phase 1**: 2-3 days
- **Phase 2**: 2-3 days
- **Phase 3**: 1 day
- **Phase 4**: 2 days

**Total**: 7-9 days for complete implementation

---

## Testing Strategy

### Unit Tests

- Test solution ranking logic
- Test recovery plan generation
- Test S3 upload/download
- Test report generation

### Integration Tests

- Test complete workflow with multiple solutions
- Test human selection and S3 storage
- Test report export in all formats

### Property-Based Tests

- Verify all solutions satisfy safety constraints
- Verify recovery plans are valid (no circular dependencies)
- Verify reports contain all required sections

---

## Next Steps

1. **Review Requirements**: Confirm these enhancements match expectations
2. **Prioritize Phases**: Decide which phases to implement first
3. **Create Spec**: Create detailed spec for each phase
4. **Implement**: Execute implementation in phases
5. **Test**: Comprehensive testing at each phase
6. **Deploy**: Deploy to production

---

**Status**: 📋 Requirements documented, awaiting approval to proceed with implementation
