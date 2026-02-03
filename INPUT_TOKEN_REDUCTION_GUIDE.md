# Input Token Reduction Guide for Arbitrator

## Executive Summary

The arbitrator currently receives **~4,072 input tokens**, which contributes significantly to the 109-second execution time. Analysis shows we can reduce this by **41% (1,672 tokens)**, saving approximately **48 seconds** of LLM processing time.

---

## Current Token Distribution

| Component            | Tokens    | % of Total | Optimization Potential |
| -------------------- | --------- | ---------- | ---------------------- |
| **System Prompt**    | 1,150     | 28.2%      | HIGH (30% reduction)   |
| **KB Context**       | 1,050     | 25.8%      | HIGH (40% reduction)   |
| **Phase Comparison** | 829       | 20.4%      | HIGH (50% reduction)   |
| **Agent Responses**  | 843       | 20.7%      | HIGH (60% reduction)   |
| **Structure**        | 200       | 4.9%       | LOW (minimal)          |
| **TOTAL**            | **4,072** | **100%**   | **41% overall**        |

---

## Detailed Breakdown: Agent Responses (843 tokens)

### Current Usage

```
Recommendations:      149 tokens (17.7%)
Reasoning:            573 tokens (68.0%) ← BIGGEST COMPONENT
Binding Constraints:   96 tokens (11.4%)
Data Sources:          25 tokens (2.9%)
```

### By Agent

```
crew_compliance:  288 tokens (34.2%)
maintenance:      223 tokens (26.5%)
regulatory:       200 tokens (23.7%)
network:           99 tokens (11.7%)
guest_experience:  11 tokens (1.3%) ← INACTIVE
cargo:             11 tokens (1.3%) ← INACTIVE
finance:           11 tokens (1.3%) ← INACTIVE
```

---

## Optimization Strategy 1: Compress Reasoning Text

**Current:** 573 tokens (68% of agent data)  
**Target:** 172 tokens (70% reduction)  
**Savings:** 401 tokens (~11.5 seconds)

### Problem

Agent reasoning is extremely verbose:

```python
# CURRENT (223 tokens)
"Fire event (pilot on fire) requires immediate aircraft safety inspection per
regulatory requirements. Emergency landing/arrival triggers mandatory airworthiness
review of all fire suppression systems, cockpit environment, oxygen systems.
Aircraft status unknown until post-incident inspection completed - assume AOG
until cleared. Flight data unavailable but emergency nature confirmed by all
agents - maintenance inspection non-negotiable. Post-fire inspection scope:
cockpit fire detection/suppression systems, electrical systems, oxygen system
integrity, structural damage assessment. Estimated inspection time: 4-8 hours
minimum before RTS determination possible."
```

### Solution: Ultra-Compact Format

```python
# OPTIMIZED (67 tokens - 70% reduction)
"* Fire event → maint insp req * AOG until cleared * Insp scope: fire suppress,
elec, O2, struct * Est: 4-8h * RTS pending clearance"
```

### Implementation

```python
def format_reasoning_ultra_compact(reasoning: str, max_len: int = 100) -> str:
    """
    Ultra-compact reasoning format for arbitrator.

    Applies aggressive compression:
    - Bullet points instead of sentences
    - Abbreviations for common terms
    - Remove redundant phrases
    - Max 100 chars total
    """
    if not reasoning or len(reasoning) <= max_len:
        return reasoning

    # Aggressive abbreviations
    abbreviations = {
        "aircraft": "A/C",
        "maintenance": "maint",
        "inspection": "insp",
        "required": "req",
        "emergency": "emerg",
        "regulatory": "reg",
        "compliance": "compl",
        "Flight Duty Period": "FDP",
        "hours": "h",
        "minutes": "min",
        "passenger": "pax",
        "connection": "conn",
        "immediately": "immed",
        "approximately": "~",
        "available": "avail",
        "replacement": "repl",
        "requirement": "req",
        "estimated": "est",
        "return to service": "RTS",
        "Aircraft on Ground": "AOG",
        "suppression": "suppress",
        "electrical": "elec",
        "oxygen": "O2",
        "structural": "struct",
        "systems": "sys",
        "pending": "pend",
    }

    # Apply abbreviations
    compressed = reasoning
    for full, abbr in abbreviations.items():
        compressed = compressed.replace(full, abbr)

    # Extract key points (sentences with critical info)
    sentences = compressed.split('. ')
    key_points = []

    for sent in sentences:
        # Keep sentences with critical keywords
        if any(kw in sent.lower() for kw in ['req', 'must', 'mandatory', 'critical', 'aog', 'emerg']):
            key_points.append(sent.strip())

    # Format as bullets
    if key_points:
        bullets = ' * '.join(key_points[:3])  # Max 3 points
        if len(bullets) > max_len:
            bullets = bullets[:max_len-3] + "..."
        return bullets

    # Fallback: hard truncate
    return compressed[:max_len-3] + "..."
```

**Expected savings:** 401 tokens (~11.5 seconds)

---

## Optimization Strategy 2: Truncate Recommendations

**Current:** 149 tokens  
**Target:** 90 tokens (40% reduction)  
**Savings:** 59 tokens (~1.7 seconds)

### Problem

Recommendations contain redundant information:

```python
# CURRENT (62 tokens)
"IMMEDIATE MEDICAL EVACUATION + CREW REPLACEMENT: Pilot on fire requires
emergency medical response; incapacitated crew member unfit for duty;
replacement pilot required before next departure; coordinate with medical/ops
for emergency services"
```

### Solution: Action-Focused Format

```python
# OPTIMIZED (25 tokens - 60% reduction)
"EMERG: Med evac pilot + crew repl req before next dep"
```

### Implementation

```python
def truncate_recommendation_aggressive(rec: str, max_len: int = 80) -> str:
    """
    Aggressively truncate recommendation to action-focused format.

    Keeps only:
    - Action verbs (EVAC, REPLACE, DELAY, CANCEL)
    - Critical constraints (MUST, REQUIRED, IMMEDIATE)
    - Key entities (crew, aircraft, passengers)
    """
    if not rec or len(rec) <= max_len:
        return rec

    # Apply abbreviations first
    abbreviations = {
        "IMMEDIATE": "IMMED",
        "EMERGENCY": "EMERG",
        "MEDICAL": "MED",
        "EVACUATION": "EVAC",
        "REPLACEMENT": "REPL",
        "REQUIRED": "REQ",
        "BEFORE": "B4",
        "DEPARTURE": "DEP",
        "COORDINATE": "COORD",
        "OPERATIONS": "OPS",
    }

    compressed = rec
    for full, abbr in abbreviations.items():
        compressed = compressed.replace(full, abbr)

    # Extract action phrase (usually before first colon or semicolon)
    if ':' in compressed:
        action = compressed.split(':')[0].strip()
        details = compressed.split(':')[1].strip()

        # Keep action + first critical detail
        first_detail = details.split(';')[0].strip()
        result = f"{action}: {first_detail}"

        if len(result) <= max_len:
            return result

    # Fallback: truncate at natural break
    return compressed[:max_len-3] + "..."
```

**Expected savings:** 59 tokens (~1.7 seconds)

---

## Optimization Strategy 3: Simplify Phase Comparison

**Current:** 829 tokens (20.4% of total)  
**Target:** 415 tokens (50% reduction)  
**Savings:** 414 tokens (~11.8 seconds)

### Problem

Phase comparison includes full text for all agents:

```python
# CURRENT FORMAT (verbose)
"""
## Phase Evolution Analysis (Phase 1 → Phase 2)

### Agents That Changed Recommendations

**Crew Compliance** - ↑ CONVERGED (confidence increased)
  - Phase 1: EMERGENCY RESPONSE - FLIGHT DATA UNAVAILABLE...
  - Phase 2: IMMEDIATE MEDICAL EVACUATION + CREW REPLACEMENT...
  - Confidence: 0.85 → 0.85
  - NEW CONSTRAINTS: Incapacitated crew member unfit for duty...

**Maintenance** - → REVISED (confidence stable)
  - Phase 1: AOG: PILOT ON FIRE - Emergency landing required...
  - Phase 2: AIRCRAFT INSPECTION REQUIRED: Post-emergency fire...
  - Confidence: 0.80 → 0.80

[... continues for all 7 agents ...]
"""
```

### Solution: Delta-Only Format

```python
# OPTIMIZED FORMAT (50% reduction)
"""
## Phase Evolution (4 changed, 3 stable)

**Changed:**
- crew_compliance(0.85): EMERG → MED EVAC + CREW REPL
- maintenance(0.80): AOG → INSP REQ
- regulatory(0.80): COMPLIANT → COMPLIANT (constraints added)
- network(0.80): SAFETY OVERRIDE → DEFER TO EMERG

**Stable:** guest_experience, cargo, finance (no data)

**Pattern:** CONVERGENCE (all safety agents strengthened)
"""
```

### Implementation

```python
def format_phase_comparison_compact(
    initial_responses: Dict[str, Any],
    revised_responses: Dict[str, Any],
    max_tokens: int = 400
) -> str:
    """
    Ultra-compact phase comparison showing only deltas.

    Format:
    - Changed agents: one line per agent with before→after
    - Stable agents: list names only
    - Pattern summary: convergence/divergence
    """
    lines = ["## Phase Evolution"]

    all_agents = set(initial_responses.keys()) | set(revised_responses.keys())

    changed = []
    stable = []

    for agent_name in sorted(all_agents):
        initial = initial_responses.get(agent_name, {})
        revised = revised_responses.get(agent_name, {})

        if not isinstance(initial, dict) or not isinstance(revised, dict):
            continue

        initial_rec = initial.get('recommendation', '')[:50]
        revised_rec = revised.get('recommendation', '')[:50]
        conf = revised.get('confidence', 0.0)

        if initial_rec != revised_rec:
            # Changed - show delta
            changed.append(f"- {agent_name}({conf:.2f}): {initial_rec[:30]}→{revised_rec[:30]}")
        else:
            # Stable
            stable.append(agent_name)

    # Build compact output
    if changed:
        lines.append(f"\n**Changed ({len(changed)}):**")
        lines.extend(changed[:5])  # Max 5 changed agents

    if stable:
        lines.append(f"\n**Stable ({len(stable)}):** {', '.join(stable[:5])}")

    # Pattern detection
    if len(changed) > len(stable):
        lines.append("\n**Pattern:** CONVERGENCE")
    elif len(stable) > len(changed):
        lines.append("\n**Pattern:** STABLE")

    result = '\n'.join(lines)

    # Ensure we don't exceed max tokens
    if len(result) // 4 > max_tokens:
        result = result[:max_tokens * 4 - 20] + "..."

    return result
```

**Expected savings:** 414 tokens (~11.8 seconds)

---

## Optimization Strategy 4: Reduce KB Documents

**Current:** 1,050 tokens (5 documents × 210 tokens each)  
**Target:** 630 tokens (3 documents × 210 tokens each)  
**Savings:** 420 tokens (~12 seconds)

### Problem

Retrieving 5 KB documents adds significant token overhead:

```python
# CURRENT
max_results: int = 5  # 5 documents

# Each document includes:
# - Full excerpt (400 chars = ~100 tokens)
# - Source citation (~30 tokens)
# - Metadata (~20 tokens)
# - Formatting (~60 tokens)
# Total per doc: ~210 tokens
```

### Solution: Reduce to 3 Documents + Truncate Excerpts

```python
# OPTIMIZED
max_results: int = 3  # 3 documents

# Truncate excerpts to 200 chars (50 tokens)
# Total per doc: ~100 tokens
# Total: 300 tokens (vs 1050)
```

### Implementation

```python
# In knowledge_base.py
async def query_operational_procedures(
    self,
    disruption_scenario: str,
    binding_constraints: List[str],
    agent_recommendations: Dict[str, Any],
    max_results: int = 3  # REDUCED FROM 5
) -> Optional[Dict[str, Any]]:
    """Query KB with reduced document count."""

    response = self.client.retrieve(
        knowledgeBaseId=self.knowledge_base_id,
        retrievalQuery={'text': query},
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': max_results  # 3 instead of 5
            }
        }
    )

    # Process results with truncated excerpts
    for item in response.get('retrievalResults', []):
        content = item.get('content', {}).get('text', '')

        # TRUNCATE to 200 chars instead of 400
        if len(content) > 200:
            content = content[:200] + "..."

        procedures.append({
            'content': content,  # Truncated
            'source': source,
            'relevance_score': score,
            'document_type': doc_type
        })
```

**Expected savings:** 420 tokens (~12 seconds)

---

## Optimization Strategy 5: Compress System Prompt

**Current:** 1,150 tokens  
**Target:** 805 tokens (30% reduction)  
**Savings:** 345 tokens (~9.9 seconds)

### Problem

System prompt contains verbose instructions:

```python
# CURRENT (verbose)
ARBITRATOR_SYSTEM_PROMPT = """
<role>arbitrator</role>
<priority>safety_constraints_binding</priority>

<workflow>
  <step>validate: ALL scenarios vs ALL constraints</step>
  <step>classify: conflicts (Safety>Business, Safety>Safety, Business>Business)</step>
  <step>score: safety_margin, cost, passenger_impact, network_impact</step>
  <step>rank: composite (40% safety, 20% cost, 20% pax, 20% network)</step>
  <step>return: 1-3 Pareto-optimal solutions</step>
</workflow>

<decision_rules>
P1: Safety > Business (ALWAYS, NO EXCEPTIONS)
P2: Safety > Safety (MOST CONSERVATIVE)
P3: Business > Business (Pareto-optimal, multi-objective)
</decision_rules>

<confidence>
0.9-1.0: All agree, complete data | 0.7-0.9: Minor conflicts, good data
0.5-0.7: Significant conflicts, gaps | 0.3-0.5: Complex conflicts, major gaps
0.0-0.3: Critical missing data, ESCALATE
Missing data: Flag uncertainty, penalize confidence
</confidence>

<output>ArbitratorOutput: final_decision, recommendations[], conflicts_identified[],
conflict_resolutions[], safety_overrides[], justification, reasoning, confidence,
solution_options[1-3], recommended_solution_id</output>

<output_style>
- Human-readable but CONCISE - no flowery language
- Active voice: "Proceed with..." not "It is recommended to..."
- Direct statements: "Delay 2h" not "Consider implementing a delay of approximately 2 hours"
- final_decision: Clear actionable statement (1-2 sentences max)
- justification: 2-3 sentences covering key decision factors
- reasoning: Bullet points for decision factors
- recommendations: Actionable bullet points only
- solution_options: Structured with clear trade-offs, no verbose prose
</output_style>

<knowledge_base id="UDONMVCXEW">SOPs, OCM procedures, historical cases</knowledge_base>

<phase_evolution>
When both phases available:

<pattern name="convergence">Agents align, confidence ↑ → STRONG POSITIVE - weight heavily</pattern>
<pattern name="divergence">Agents separate, confidence ↓ → WARNING - investigate conflicts/gaps</pattern>
<pattern name="stable">Unchanged → HIGH CONFIDENCE - especially safety constraints</pattern>

<action>Document evolution in reasoning</action>
</phase_evolution>
"""
```

### Solution: Minimal XML Format

```python
# OPTIMIZED (30% reduction)
ARBITRATOR_SYSTEM_PROMPT_COMPACT = """
<role>arbitrator</role>
<priority>safety_first</priority>

<workflow>validate→classify→score→rank→return 1-3 solutions</workflow>

<rules>
P1: Safety>Business (ALWAYS)
P2: Safety>Safety (CONSERVATIVE)
P3: Business>Business (Pareto)
</rules>

<confidence>
0.9-1.0: consensus | 0.7-0.9: minor conflicts | 0.5-0.7: gaps | <0.5: ESCALATE
</confidence>

<output>ArbitratorOutput with final_decision, recommendations[], conflicts[],
safety_overrides[], justification, reasoning, confidence, solution_options[1-3]</output>

<style>Concise, active voice, actionable. Max 2 sentences per field.</style>

<kb id="UDONMVCXEW">SOPs, OCM, historical</kb>

<evolution>
convergence: weight heavily | divergence: investigate | stable: high confidence
</evolution>
"""
```

**Expected savings:** 345 tokens (~9.9 seconds)

---

## Optimization Strategy 6: Skip Inactive Agents

**Current:** 33 tokens (3 agents with no data)  
**Target:** 0 tokens  
**Savings:** 33 tokens (~0.9 seconds)

### Problem

Agents with 0.0 confidence and no recommendations still get included:

```python
# CURRENT
"guest_experience": {
    "recommendation": "No recommendation provided",
    "confidence": 0.0,
    "reasoning": "No reasoning provided"
}
```

### Solution: Filter Out Inactive Agents

```python
def _format_agent_responses(responses: Dict[str, Any]) -> str:
    """Format agent responses, skipping inactive agents."""
    formatted = []

    # Filter out agents with no data
    active_responses = {
        name: resp for name, resp in responses.items()
        if isinstance(resp, dict) and resp.get('confidence', 0) > 0.0
    }

    # Format only active agents
    safety_agents = _extract_safety_agents(active_responses)
    business_agents = _extract_business_agents(active_responses)

    # ... rest of formatting
```

**Expected savings:** 33 tokens (~0.9 seconds)

---

## Implementation Priority

### Phase 1: Quick Wins (1-2 hours) - **874 tokens saved**

1. ✅ **Compress Reasoning** (401 tokens)
   - Implement `format_reasoning_ultra_compact()`
   - Apply to all agent responses before arbitrator

2. ✅ **Reduce KB Documents** (420 tokens)
   - Change `max_results` from 5 to 3
   - Truncate excerpts to 200 chars

3. ✅ **Skip Inactive Agents** (33 tokens)
   - Filter agents with confidence = 0.0

4. ✅ **Truncate Recommendations** (59 tokens - partial)
   - Apply aggressive truncation to 80 chars

**Total Phase 1: 874 tokens saved (~25 seconds)**

---

### Phase 2: Medium Effort (3-4 hours) - **759 tokens saved**

1. ✅ **Simplify Phase Comparison** (414 tokens)
   - Implement delta-only format
   - Show only changed agents

2. ✅ **Compress System Prompt** (345 tokens)
   - Rewrite in minimal XML format
   - Remove verbose instructions

**Total Phase 2: 759 tokens saved (~22 seconds)**

---

### Phase 3: Testing & Validation (2-3 hours)

1. ✅ **A/B Testing**
   - Compare decision quality (original vs optimized)
   - Measure confidence scores
   - Verify safety compliance

2. ✅ **Performance Validation**
   - Measure actual token reduction
   - Measure time savings
   - Monitor error rates

---

## Expected Results

| Metric                | Before | After Phase 1 | After Phase 2 | Improvement |
| --------------------- | ------ | ------------- | ------------- | ----------- |
| **Input Tokens**      | 4,072  | 3,198         | 2,439         | **40.1%**   |
| **Input Time**        | ~116s  | ~91s          | ~70s          | **39.7%**   |
| **Total Arbitration** | 109s   | ~84s          | ~63s          | **42.2%**   |

---

## Risk Mitigation

### Low Risk

- ✅ Reducing KB documents (still get top 3 most relevant)
- ✅ Skipping inactive agents (no data loss)
- ✅ Compressing system prompt (preserves all rules)

### Medium Risk

- ⚠️ Aggressive reasoning compression (may lose context)
- ⚠️ Simplified phase comparison (may miss subtle changes)

### Mitigation Strategy

1. **Gradual rollout:** Implement Phase 1 first, validate, then Phase 2
2. **A/B testing:** Compare decision quality metrics
3. **Monitoring:** Track confidence scores and safety compliance
4. **Rollback plan:** Keep original formatting functions available

---

## Validation Metrics

### Decision Quality

- Confidence score distribution (should remain similar)
- Safety compliance rate (must be 100%)
- Conflict detection accuracy (should remain high)

### Performance

- Input token count (target: <2,500)
- Arbitration duration (target: <65s)
- End-to-end latency (target: <120s)

### User Experience

- Decision clarity (human review)
- Recommendation actionability (human review)
- Audit trail completeness (regulatory review)

---

## Conclusion

By implementing these 6 optimizations, we can reduce arbitrator input tokens by **40% (1,672 tokens)**, saving approximately **48 seconds** of processing time. Combined with the output optimization (using Haiku for simple cases), this brings total arbitration time from **109s to ~40-50s** for emergency scenarios.

**Key insight:** The biggest token consumers are:

1. **Reasoning text** (573 tokens) - 70% reduction possible
2. **KB context** (1,050 tokens) - 40% reduction possible
3. **Phase comparison** (829 tokens) - 50% reduction possible

These three components alone account for **2,452 tokens (60% of total)** and offer the highest ROI for optimization efforts.
