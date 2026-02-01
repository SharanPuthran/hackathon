# SkyMarshal Complete System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│  "Flight EY123 on January 20th had a mechanical failure"                   │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
                                 │ Natural Language Prompt
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR (main.py)                               │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 1: INITIAL RECOMMENDATIONS                                     │   │
│  │                                                                       │   │
│  │ Augmented Prompt: "{user_prompt}\n\nPlease analyze this disruption  │   │
│  │                    and provide your initial recommendation"          │   │
│  │                                                                       │   │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │ │  Crew    │ │  Maint   │ │   Reg    │ │ Network  │ │  Guest   │  │   │
│  │ │Compliance│ │          │ │          │ │          │ │Experience│  │   │
│  │ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │   │
│  │      │            │            │            │            │          │   │
│  │ ┌──────────┐ ┌──────────┐                                          │   │
│  │ │  Cargo   │ │ Finance  │                                          │   │
│  │ └────┬─────┘ └────┬─────┘                                          │   │
│  │      │            │                                                 │   │
│  │      └────────────┴──────────────┬──────────────┬──────────────┘   │   │
│  │                                   │              │                  │   │
│  │                                   ▼              ▼                  │   │
│  │                          ┌─────────────────────────────┐           │   │
│  │                          │  Collation 1 (Pydantic)     │           │   │
│  │                          │  - 7 agent responses        │           │   │
│  │                          │  - Binding constraints      │           │   │
│  │                          │  - Confidence scores        │           │   │
│  │                          └─────────────┬───────────────┘           │   │
│  └──────────────────────────────────────────┬──────────────────────────┘   │
│                                             │                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 2: REVISION ROUND                                             │   │
│  │                                                                       │   │
│  │ Augmented Prompt: "{user_prompt}\n\nOther agents have provided:     │   │
│  │                    {collation_1}\n\nReview and revise if needed"    │   │
│  │                                                                       │   │
│  │ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │ │  Crew    │ │  Maint   │ │   Reg    │ │ Network  │ │  Guest   │  │   │
│  │ │Compliance│ │          │ │          │ │          │ │Experience│  │   │
│  │ │ (Revise) │ │ (Revise) │ │ (Revise) │ │ (Revise) │ │ (Revise) │  │   │
│  │ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │   │
│  │      │            │            │            │            │          │   │
│  │ ┌──────────┐ ┌──────────┐                                          │   │
│  │ │  Cargo   │ │ Finance  │                                          │   │
│  │ │ (Revise) │ │ (Revise) │                                          │   │
│  │ └────┬─────┘ └────┬─────┘                                          │   │
│  │      │            │                                                 │   │
│  │      └────────────┴──────────────┬──────────────┬──────────────┘   │   │
│  │                                   │              │                  │   │
│  │                                   ▼              ▼                  │   │
│  │                          ┌─────────────────────────────┐           │   │
│  │                          │  Collation 2 (Pydantic)     │           │   │
│  │                          │  - 7 revised responses      │           │   │
│  │                          │  - Updated constraints      │           │   │
│  │                          │  - Revised confidence       │           │   │
│  │                          └─────────────┬───────────────┘           │   │
│  └──────────────────────────────────────────┬──────────────────────────┘   │
│                                             │                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ PHASE 3: ARBITRATION                                                │   │
│  │                                                                       │   │
│  │                          ┌─────────────────────────────┐            │   │
│  │                          │  Arbitrator (Opus 4.5)      │            │   │
│  │                          │  - Extract constraints      │            │   │
│  │                          │  - Identify conflicts       │            │   │
│  │                          │  - Generate 1-3 solutions   │            │   │
│  │                          │  - Score each solution      │            │   │
│  │                          │  - Create recovery plans    │            │   │
│  │                          │  - Rank by composite score  │            │   │
│  │                          └─────────────┬───────────────┘            │   │
│  └──────────────────────────────────────────┬──────────────────────────┘   │
└────────────────────────────────────────────────┬──────────────────────────┘
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-SOLUTION OUTPUT                                │
│                                                                               │
│  {                                                                            │
│    "status": "success",                                                      │
│    "final_decision": "Delay flight 10 hours for crew rest...",              │
│    "recommendations": ["Notify crew scheduling", "Rebook passengers", ...], │
│                                                                               │
│    "solution_options": [                                                     │
│      {                                                                        │
│        "solution_id": 1,                                                     │
│        "title": "Conservative Safety-First Approach",                        │
│        "description": "Delay flight 10 hours to allow full crew rest...",   │
│        "composite_score": 78,                                                │
│        "safety_score": 100,  // 40% weight                                  │
│        "cost_score": 40,     // 20% weight                                  │
│        "passenger_score": 55, // 20% weight                                 │
│        "network_score": 50,  // 20% weight                                  │
│        "pros": ["Full regulatory compliance", "Zero safety risk"],          │
│        "cons": ["High cost ($180k)", "Significant passenger impact"],       │
│        "risks": ["Downstream flight delays"],                               │
│        "recovery_plan": {                                                    │
│          "total_steps": 7,                                                   │
│          "steps": [                                                          │
│            {                                                                 │
│              "step_number": 1,                                               │
│              "step_name": "Notify Crew Scheduling",                          │
│              "dependencies": [],                                             │
│              "estimated_duration": "15 minutes",                             │
│              "responsible_agent": "crew_scheduling",                         │
│              "automation_possible": true,                                    │
│              "success_criteria": "Crew scheduling confirms receipt",         │
│              ...                                                             │
│            },                                                                │
│            ...                                                               │
│          ],                                                                  │
│          "critical_path": [1, 3, 4, 6, 7]                                   │
│        }                                                                     │
│      },                                                                      │
│      {                                                                        │
│        "solution_id": 2,                                                     │
│        "title": "Crew Change with Minimal Delay",                           │
│        "composite_score": 72,                                                │
│        "safety_score": 95,                                                   │
│        "cost_score": 65,                                                     │
│        "passenger_score": 70,                                                │
│        "network_score": 75,                                                  │
│        ...                                                                   │
│      },                                                                      │
│      {                                                                        │
│        "solution_id": 3,                                                     │
│        "title": "Flight Cancellation",                                       │
│        "composite_score": 65,                                                │
│        "safety_score": 100,                                                  │
│        "cost_score": 30,                                                     │
│        "passenger_score": 40,                                                │
│        "network_score": 45,                                                  │
│        ...                                                                   │
│      }                                                                        │
│    ],                                                                        │
│                                                                               │
│    "recommended_solution_id": 1,                                             │
│                                                                               │
│    "conflicts_identified": [                                                 │
│      {                                                                        │
│        "agents_involved": ["crew_compliance", "network"],                   │
│        "conflict_type": "safety_vs_business",                               │
│        "description": "Crew requires 10h rest, network wants 2h delay"      │
│      }                                                                        │
│    ],                                                                        │
│                                                                               │
│    "conflict_resolutions": [                                                 │
│      {                                                                        │
│        "conflict": {...},                                                    │
│        "resolution": "Safety constraint enforced",                           │
│        "rationale": "Crew rest is non-negotiable per regulations"           │
│      }                                                                        │
│    ],                                                                        │
│                                                                               │
│    "audit_trail": {                                                          │
│      "user_prompt": "Flight EY123 on January 20th...",                      │
│      "phase1_initial": {                                                     │
│        "phase": "initial",                                                   │
│        "responses": {...},                                                   │
│        "duration_seconds": 8.5                                               │
│      },                                                                      │
│      "phase2_revision": {                                                    │
│        "phase": "revision",                                                  │
│        "responses": {...},                                                   │
│        "duration_seconds": 7.2                                               │
│      },                                                                      │
│      "phase3_arbitration": {                                                 │
│        "phase": "arbitration",                                               │
│        "solution_options": [...],                                            │
│        "duration_seconds": 4.1                                               │
│      }                                                                        │
│    },                                                                        │
│                                                                               │
│    "total_duration_seconds": 19.8                                            │
│  }                                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### Orchestrator (main.py)

**Responsibilities**:

- Accept natural language prompts
- Augment prompts with phase-specific instructions
- Invoke agents in parallel within each phase
- Collate responses using Pydantic models
- Preserve complete audit trail

**Key Functions**:

- `handle_disruption()` - Main entry point
- `phase1_initial_recommendations()` - Phase 1 execution
- `phase2_revision_round()` - Phase 2 execution
- `phase3_arbitration()` - Phase 3 execution
- `augment_prompt_phase1()` - Add Phase 1 instructions
- `augment_prompt_phase2()` - Add Phase 2 instructions

### Agents (7 total)

**Safety Agents** (Binding Constraints):

1. **Crew Compliance**: Duty limits, rest requirements, qualifications
2. **Maintenance**: Airworthiness, MEL compliance, inspections
3. **Regulatory**: Curfews, slots, regulatory compliance

**Business Agents** (Impact Assessments): 4. **Network**: Flight propagation, connections, aircraft rotation 5. **Guest Experience**: Passenger impact, reprotection, compensation 6. **Cargo**: Cargo manifest, special handling, cold chain 7. **Finance**: Costs, revenue impact, scenario comparison

**Agent Capabilities**:

- Extract flight info from natural language using LangChain structured output
- Query DynamoDB using agent-specific tools
- Provide initial recommendations (Phase 1)
- Review others' recommendations and revise (Phase 2)
- Return structured responses with confidence scores

### Arbitrator (arbitrator/agent.py)

**Model**: Claude Opus 4.5 (with fallback to Sonnet 4.5)

**Responsibilities**:

- Extract binding constraints from safety agents
- Identify conflicts between recommendations
- Generate 1-3 distinct solution options
- Score each solution across 4 dimensions
- Generate recovery plan for each solution
- Rank solutions by composite score
- Validate all solutions satisfy binding constraints
- Populate backward compatibility fields

**Scoring Weights**:

- Safety: 40% (highest priority)
- Cost: 20%
- Passenger Impact: 20%
- Network Impact: 20%

**Decision Rules**:

1. Safety vs Business: Always choose safety
2. Safety vs Safety: Choose most conservative
3. Business vs Business: Balance operational impact

### Recovery Plans

**Structure**:

- Sequential steps with dependencies
- Responsible agent for each step
- Estimated duration per step
- Success criteria and rollback procedures
- Critical path identification
- Contingency plans

**Validation**:

- No circular dependencies
- No self-dependencies
- All dependency references valid
- Step numbers sequential starting from 1

### Database (DynamoDB)

**Core GSIs**:

- `flight-number-date-index` - Flight lookup
- `aircraft-registration-index` - Aircraft queries
- `flight-id-index` - Passenger bookings
- `flight-position-index` - Crew roster
- `flight-loading-index` - Cargo manifest

**Priority 1 GSIs** (Critical):

- `crew-duty-date-index` - Crew duty history
- `aircraft-rotation-index` - Aircraft rotation
- `passenger-elite-tier-index` - Elite passengers

**Priority 2 GSIs** (High Value):

- `airport-curfew-index` - Curfew compliance
- `cargo-temperature-index` - Cold chain
- `aircraft-maintenance-date-index` - Maintenance conflicts

## Data Flow

### Phase 1: Initial Recommendations

```
User Prompt
    ↓
Orchestrator augments: "provide initial recommendation"
    ↓
7 Agents (parallel)
    ├─ Extract flight info (LangChain structured output)
    ├─ Query DynamoDB (agent-specific tools)
    ├─ Analyze disruption
    └─ Return recommendation
    ↓
Collation 1 (Pydantic model)
    ├─ 7 agent responses
    ├─ Binding constraints
    └─ Confidence scores
```

### Phase 2: Revision Round

```
User Prompt + Collation 1
    ↓
Orchestrator augments: "review and revise"
    ↓
7 Agents (parallel)
    ├─ Review others' recommendations
    ├─ Revise own recommendation if needed
    └─ Return revised recommendation
    ↓
Collation 2 (Pydantic model)
    ├─ 7 revised responses
    ├─ Updated constraints
    └─ Revised confidence
```

### Phase 3: Arbitration

```
Collation 2
    ↓
Arbitrator (Opus 4.5)
    ├─ Extract binding constraints
    ├─ Identify conflicts
    ├─ Generate 1-3 solutions
    ├─ Score each solution
    ├─ Generate recovery plans
    ├─ Rank by composite score
    ├─ Validate constraints
    └─ Populate backward compatibility
    ↓
Multi-Solution Output
    ├─ solution_options array (1-3 solutions)
    ├─ recommended_solution_id
    ├─ conflicts_identified
    ├─ conflict_resolutions
    ├─ audit_trail (all 3 phases)
    └─ backward compatibility fields
```

## Integration Points

### 1. Orchestrator ↔ Agents

**Interface**: `analyze_<agent_name>(payload, llm, mcp_tools)`

**Payload**:

```python
{
  "user_prompt": str,  # Augmented with phase instructions
  "phase": "initial" | "revision",
  "other_recommendations": dict  # Only in revision phase
}
```

**Response**:

```python
{
  "agent_name": str,
  "recommendation": str,
  "confidence": float,
  "binding_constraints": list[str],  # Safety agents only
  "reasoning": str,
  "data_sources": list[str],
  "extracted_flight_info": dict,
  "timestamp": str
}
```

### 2. Orchestrator ↔ Arbitrator

**Interface**: `arbitrate(revised_recommendations, llm_opus)`

**Input**: Collation 2 (all revised agent responses)

**Output**: ArbitratorOutput with solution_options

### 3. Arbitrator ↔ Schemas

**Schemas Used**:

- `RecoverySolution` - Individual solution option
- `RecoveryPlan` - Step-by-step recovery workflow
- `RecoveryStep` - Single recovery step
- `ArbitratorOutput` - Complete arbitrator response
- `ConflictDetail` - Conflict information
- `ResolutionDetail` - How conflict was resolved
- `SafetyOverride` - Safety constraint enforcement

## Performance Targets

### Latency

- Phase 1: < 10 seconds
- Phase 2: < 10 seconds
- Phase 3: < 5 seconds
- End-to-end: < 30 seconds

### Database

- Query latency: < 100ms (p99)
- No table scans
- All queries use GSIs

### Reliability

- Phase 1 success rate: > 95%
- Phase 2 success rate: > 95%
- Phase 3 success rate: > 98%
- End-to-end success rate: > 90%

## Backward Compatibility

### Legacy Fields (Maintained)

```python
{
  "final_decision": str,      # Populated from recommended solution
  "recommendations": list[str], # Populated from recommended solution
  "conflicts_identified": list,
  "conflict_resolutions": list,
  "safety_overrides": list,
  "justification": str,
  "reasoning": str,
  "confidence": float
}
```

### New Fields (Added)

```python
{
  "solution_options": list[RecoverySolution],  # 1-3 solutions
  "recommended_solution_id": int,              # ID of recommended solution
  "audit_trail": {                             # Complete history
    "phase1_initial": dict,
    "phase2_revision": dict,
    "phase3_arbitration": dict
  }
}
```

## Error Handling

### Agent Failures

- Continue with available responses
- Log failures in audit trail
- Reduce confidence scores
- Provide warnings in output

### Arbitrator Failures

- Return conservative fallback decision
- Single solution recommending manual review
- Confidence score: 0.0
- Error details in response

### Database Failures

- Report insufficient data
- Request missing information
- Provide actionable error messages
- Never expose internal details

## Monitoring

### Key Metrics

- Success rates by phase
- Latency by phase
- Error rates by agent
- Database query performance
- Model availability
- Solution quality metrics

### Alerts

- **Critical**: End-to-end success < 80%, system unavailable
- **Warning**: Phase latency exceeds target, agent timeout > 10%
- **Info**: Performance degradation, increased load

## Next Steps

1. **Integration Testing** - Validate all components work together
2. **Performance Testing** - Validate latency targets met
3. **Staging Deployment** - Deploy and validate in staging
4. **Production Deployment** - Deploy to production with monitoring
5. **Post-Deployment** - Monitor, optimize, iterate
