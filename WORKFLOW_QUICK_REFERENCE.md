# SkyMarshal Workflow Quick Reference

## One-Page Summary

### System Flow

```
User Prompt → Phase 1 (Initial) → Phase 2 (Revision) → Phase 3 (Arbitration) → Human Decision
```

### Phase 1: Initial Recommendations (8-10s)

**What Happens**:

- All 7 agents execute in parallel
- Each agent queries DynamoDB for relevant data
- Each agent performs domain-specific analysis
- Returns: Initial recommendations with confidence scores

**Agents**:

- Safety: Crew Compliance, Maintenance, Regulatory (with binding constraints)
- Business: Network, Guest Experience, Cargo, Finance

**Output**: Phase 1 Collation (all agent responses)

### Phase 2: Revision Round (8-10s)

**What Happens**:

- All 7 agents execute again in parallel
- Each agent receives Phase 1 recommendations from ALL agents
- Agents review others' recommendations and revise their own
- Returns: Revised recommendations accounting for cross-agent insights

**Key Difference**: Agents now consider binding constraints and other agents' analysis

**Output**: Phase 2 Collation (revised responses)

### Phase 3: Arbitration (4-5s)

**What Happens**:

- Arbitrator (Claude Opus 4.5) receives Phase 2 collation
- Extracts binding constraints from safety agents
- Identifies conflicts between recommendations
- Applies decision rules (Safety > Business, Most Conservative)
- Generates 1-3 distinct solution options
- Scores each solution (Safety, Cost, Passenger, Network)
- Ranks by composite score
- Creates recovery plan for each solution

**Output**: Multi-solution arbitrator output with recommended solution

### Arbitrator's Plan of Action (Detailed)

**Step 1**: Extract binding constraints from safety agents
**Step 2**: Identify conflicts (Safety vs Business, Safety vs Safety, Business vs Business)
**Step 3**: Apply decision rules to resolve conflicts
**Step 4**: Generate 1-3 solution options that satisfy ALL constraints
**Step 5**: Score each solution across 4 dimensions
**Step 6**: Create detailed recovery plan for each solution
**Step 7**: Rank solutions by composite score
**Step 8**: Populate backward compatibility fields
**Step 9**: Return complete output with justification

### Post-Arbitration: Human Decision

**Step 1**: Orchestrator assembles complete response with audit trail
**Step 2**: Response sent to frontend/API
**Step 3**: Duty Manager reviews:

- Recommended solution (highest composite score)
- Alternative solutions (different trade-offs)
- Recovery plans (step-by-step execution)
- Audit trail (full transparency)
  **Step 4**: Duty Manager approves a solution
  **Step 5**: Solution execution begins following recovery plan
  **Step 6**: Outcome recorded in historical knowledge base

### Example Solution Output

**Solution 1**: Next-Day Departure (Score: 62.0)

- Safety: 100, Cost: 45, Passenger: 40, Network: 35
- Cost: $185k, Delay: 24h

**Solution 2**: Crew Change Same-Day (Score: 75.5) ⭐ RECOMMENDED

- Safety: 95, Cost: 70, Passenger: 65, Network: 75
- Cost: $95k, Delay: 8h

**Solution 3**: Flight Cancellation (Score: 68.0)

- Safety: 100, Cost: 20, Passenger: 50, Network: 100
- Cost: $275k, Cancellation

### Key Principles

1. **Safety First**: Binding constraints are non-negotiable
2. **Multi-Solution**: 1-3 options, not just one decision
3. **Human-in-the-Loop**: System recommends, human approves
4. **Complete Transparency**: Full audit trail preserved
5. **Historical Learning**: Outcomes stored for future improvement

### Performance

- Phase 1: ~8.5s
- Phase 2: ~9.2s
- Phase 3: ~4.8s
- **Total: ~22.5s** (target: < 30s)

### Files

- Orchestrator: `skymarshal_agents_new/skymarshal/src/main.py`
- Arbitrator: `skymarshal_agents_new/skymarshal/src/agents/arbitrator/agent.py`
- Schemas: `skymarshal_agents_new/skymarshal/src/agents/schemas.py`

### Next Steps

1. Run integration tests (`.kiro/specs/skymarshal-integration-testing/`)
2. Deploy to staging
3. Validate with smoke tests
4. Deploy to production
5. Monitor and iterate
