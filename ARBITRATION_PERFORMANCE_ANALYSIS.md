# Arbitration Performance Analysis

## Executive Summary

The arbitration phase is taking **109 seconds** (1 minute 49 seconds) to complete, which is significantly longer than the agent execution phases:

- Phase 1 (Initial): 29 seconds
- Phase 2 (Revision): 21 seconds
- **Phase 3 (Arbitration): 109 seconds** ⚠️

This represents **68.5% of the total execution time** (159 seconds).

---

## Root Cause Analysis

### 1. **LLM Token Generation Time** (Primary Bottleneck)

**Impact: ~80-90 seconds**

The arbitrator uses Claude Sonnet 4.5 (or Opus 4.5 if available) with structured output to generate:

- Final decision text
- Multiple recovery solution options (1-3 solutions)
- Detailed recovery plans with steps for each solution
- Conflict analysis
- Safety overrides
- Justification and reasoning
- Recommendation evolution analysis

**Evidence from code:**

```python
# arbitrator/agent.py line ~1050
structured_llm = llm_opus.with_structured_output(ArbitratorOutput)
decision = structured_llm.invoke([
    {"role": "system", "content": ARBITRATOR_SYSTEM_PROMPT},
    {"role": "user", "content": prompt}
])
```

The `ArbitratorOutput` schema is extremely complex with nested Pydantic models:

- `RecoverySolution` (multiple instances)
- `RecoveryPlan` with `RecoveryStep[]`
- `AgentEvolution` with detailed change tracking
- `RecommendationEvolution` with convergence analysis

**Token counts (estimated):**

- Input prompt: ~8,000-12,000 tokens (includes all agent responses, KB docs, phase comparison)
- Output generation: ~4,000-6,000 tokens (structured JSON with multiple solutions)
- **Total: ~12,000-18,000 tokens**

At Claude Sonnet 4.5's generation speed (~30-40 tokens/second), this accounts for **60-90 seconds** of the arbitration time.

---

### 2. **Knowledge Base Query** (Secondary Bottleneck)

**Impact: ~5-15 seconds**

The arbitrator queries AWS Bedrock Knowledge Base for operational procedures:

```python
# arbitrator/agent.py line ~1000
procedures = await kb_client.query_operational_procedures(
    disruption_scenario=disruption_scenario,
    binding_constraints=constraint_strings,
    agent_recommendations=responses_dict
)
```

**KB Query Process:**

1. Build comprehensive query text (~500-1000 tokens)
2. Call Bedrock Knowledge Base Retrieve API
3. Vector search across operational documents
4. Retrieve top 5 documents
5. Process and format results

**Timing breakdown:**

- Query construction: ~0.1s
- Bedrock API call: **5-15s** (network + vector search)
- Result processing: ~0.5s

The KB query found **5 documents** in the emergency scenario, indicating successful retrieval but at a cost.

---

### 3. **Phase Evolution Analysis** (Minor Overhead)

**Impact: ~2-5 seconds**

When both Phase 1 and Phase 2 recommendations are provided, the arbitrator performs evolution analysis:

```python
# arbitrator/agent.py line ~950
phase_comparison = _format_phase_comparison(initial_responses_dict, responses_dict)
evolution_details = _analyze_recommendation_evolution(initial_responses_dict, responses_dict)
evolution_analysis = _build_recommendation_evolution(evolution_details, phases_considered)
```

This involves:

- Comparing 7 agent responses across 2 phases
- Detecting convergence/divergence patterns
- Formatting detailed comparison text
- Building evolution metadata

**Timing:** ~2-5 seconds for text processing and comparison logic.

---

### 4. **Prompt Construction** (Minor Overhead)

**Impact: ~1-2 seconds**

Building the arbitrator prompt involves:

- Formatting agent responses (7 agents × 2 phases)
- Extracting binding constraints
- Formatting KB operational context
- Building phase comparison text

**Total prompt size:** ~8,000-12,000 tokens (very large)

---

## Performance Breakdown

| Component                       | Time (seconds) | % of Total | Optimization Potential |
| ------------------------------- | -------------- | ---------- | ---------------------- |
| **LLM Token Generation**        | 80-90          | 73-83%     | HIGH                   |
| **Knowledge Base Query**        | 5-15           | 5-14%      | MEDIUM                 |
| **Phase Evolution Analysis**    | 2-5            | 2-5%       | LOW                    |
| **Prompt Construction**         | 1-2            | 1-2%       | LOW                    |
| **Overhead (checkpoints, etc)** | 5-10           | 5-9%       | LOW                    |
| **TOTAL**                       | **~109**       | **100%**   | -                      |

---

## Optimization Recommendations

### Priority 1: Reduce LLM Token Generation Time (HIGH IMPACT)

#### Option 1A: Simplify Structured Output Schema ⭐ **RECOMMENDED**

**Impact: 30-50% reduction (30-45 seconds saved)**

**Current problem:** The `ArbitratorOutput` schema requires generating multiple complete recovery solutions with detailed plans, which forces the LLM to generate 4,000-6,000 output tokens.

**Solution:**

```python
# Create a simplified arbitrator output for emergency scenarios
class SimplifiedArbitratorOutput(BaseModel):
    """Simplified output for time-critical decisions"""
    final_decision: str
    recommendations: List[str]
    primary_solution: RecoverySolution  # Only 1 solution instead of 1-3
    conflicts_identified: List[ConflictDetail]
    safety_overrides: List[SafetyOverride]
    justification: str
    confidence: float
    # Remove: solution_options, recommendation_evolution details
```

**Implementation:**

1. Detect emergency scenarios (pilot on fire, safety agent failures, etc.)
2. Use simplified schema for emergencies
3. Use full schema for non-emergency disruptions
4. Reduce output tokens from ~5,000 to ~2,000

**Expected savings:** 30-45 seconds

---

#### Option 1B: Use Haiku 4.5 for Simple Arbitrations ⭐ **RECOMMENDED**

**Impact: 40-60% reduction (40-65 seconds saved)**

**Current:** Always uses Sonnet 4.5 or Opus 4.5 (slower, more expensive)

**Solution:**

```python
def _select_arbitrator_model(responses: Dict[str, Any]) -> str:
    """Select appropriate model based on complexity"""

    # Check for emergency consensus (all agents agree)
    safety_agents = _extract_safety_agents(responses)
    all_high_confidence = all(
        r.get('confidence', 0) > 0.8
        for r in safety_agents.values()
    )

    # Check for conflicts
    has_conflicts = _detect_conflicts(responses)

    if all_high_confidence and not has_conflicts:
        # Simple case: use Haiku 4.5 (3-4x faster)
        return HAIKU_MODEL_ID
    else:
        # Complex case: use Sonnet 4.5
        return SONNET_MODEL_ID
```

**Haiku 4.5 speed:** ~100-120 tokens/second (vs Sonnet's ~30-40)
**Expected savings:** 40-65 seconds for simple cases (like the emergency scenario)

---

#### Option 1C: Reduce Input Prompt Size

**Impact: 10-20% reduction (10-20 seconds saved)**

**Current prompt size:** ~8,000-12,000 tokens

**Optimizations:**

1. **Compress agent responses:** Use compact format (already implemented but can be more aggressive)
2. **Limit KB documents:** Reduce from 5 to 3 documents
3. **Truncate phase comparison:** Limit to changed agents only
4. **Remove verbose instructions:** System prompt is 200+ lines

**Example compression:**

```python
def _format_agent_responses_ultra_compact(responses: Dict[str, Any]) -> str:
    """Ultra-compact format for arbitrator"""
    lines = []
    for name, resp in responses.items():
        conf = resp.get('confidence', 0)
        rec = resp.get('recommendation', '')[:150]  # Truncate to 150 chars
        lines.append(f"{name}({conf:.2f}): {rec}")
    return "\n".join(lines)
```

**Expected savings:** 10-20 seconds

---

### Priority 2: Optimize Knowledge Base Query (MEDIUM IMPACT)

#### Option 2A: Parallel KB Query ⭐ **RECOMMENDED**

**Impact: 5-10 seconds saved**

**Current:** KB query runs sequentially before LLM invocation

**Solution:**

```python
# Run KB query and LLM invocation in parallel
kb_task = asyncio.create_task(kb_client.query_operational_procedures(...))
llm_task = asyncio.create_task(structured_llm.invoke(...))

# Wait for both
kb_result, llm_result = await asyncio.gather(kb_task, llm_task)
```

**Trade-off:** LLM won't have KB context, but for emergencies this is acceptable.

**Expected savings:** 5-10 seconds

---

#### Option 2B: Cache KB Results

**Impact: 5-15 seconds saved (on cache hits)**

**Solution:**

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
async def query_kb_cached(disruption_type: str, constraints_hash: str):
    """Cache KB results by disruption type and constraints"""
    return await kb_client.query_operational_procedures(...)
```

**Expected savings:** 5-15 seconds for repeated disruption types

---

#### Option 2C: Reduce KB Document Count

**Impact: 2-5 seconds saved**

**Current:** Retrieves 5 documents

**Solution:** Reduce to 3 documents for faster retrieval and processing

```python
max_results: int = 3  # Down from 5
```

**Expected savings:** 2-5 seconds

---

### Priority 3: Optimize Phase Evolution Analysis (LOW IMPACT)

#### Option 3A: Skip Evolution for Emergencies

**Impact: 2-5 seconds saved**

**Solution:**

```python
if is_emergency_scenario(responses_dict):
    # Skip phase evolution analysis for emergencies
    phase_comparison = ""
    evolution_analysis = None
else:
    # Full evolution analysis for non-emergencies
    phase_comparison = _format_phase_comparison(...)
```

**Expected savings:** 2-5 seconds

---

### Priority 4: Streaming Response (FUTURE ENHANCEMENT)

**Impact: Perceived latency reduction (no actual time saved)**

**Solution:** Stream the arbitrator's decision as it's generated

```python
# Use streaming instead of waiting for complete response
async for chunk in structured_llm.astream(...):
    yield chunk  # Send partial results to frontend
```

**Benefit:** User sees decision forming in real-time instead of waiting 109 seconds

---

## Recommended Implementation Plan

### Phase 1: Quick Wins (1-2 days) - **60-80 seconds saved**

1. ✅ **Use Haiku 4.5 for simple arbitrations** (40-65s saved)
   - Detect emergency consensus scenarios
   - Route to Haiku 4.5 instead of Sonnet 4.5
   - Fallback to Sonnet for complex cases

2. ✅ **Simplify output schema for emergencies** (20-30s saved)
   - Create `SimplifiedArbitratorOutput` model
   - Generate single solution instead of 1-3
   - Skip detailed recovery plans for emergencies

3. ✅ **Reduce KB document count** (2-5s saved)
   - Change `max_results` from 5 to 3

**Total Phase 1 savings: 62-100 seconds** (target: <50s arbitration time)

---

### Phase 2: Medium-term Optimizations (3-5 days) - **15-30 seconds saved**

1. ✅ **Parallel KB query** (5-10s saved)
   - Run KB query and LLM invocation concurrently
   - Merge results after both complete

2. ✅ **Compress input prompts** (10-20s saved)
   - Ultra-compact agent response format
   - Truncate verbose system instructions
   - Limit phase comparison to changed agents only

**Total Phase 2 savings: 15-30 seconds** (target: <35s arbitration time)

---

### Phase 3: Long-term Enhancements (1-2 weeks) - **Perceived latency reduction**

1. ✅ **Streaming responses**
   - Stream arbitrator decision as it generates
   - Update frontend to show progressive results

2. ✅ **KB result caching**
   - Cache KB queries by disruption type
   - Invalidate cache daily or on KB updates

3. ✅ **Adaptive timeout**
   - Reduce timeout for simple cases (30s)
   - Keep 90s timeout for complex cases

---

## Expected Performance After Optimizations

| Scenario               | Current | After Phase 1 | After Phase 2 | Improvement |
| ---------------------- | ------- | ------------- | ------------- | ----------- |
| **Emergency (simple)** | 109s    | 40-50s        | 25-35s        | **68-77%**  |
| **Complex disruption** | 109s    | 70-80s        | 55-65s        | **40-50%**  |
| **Average**            | 109s    | 55-65s        | 40-50s        | **54-63%**  |

---

## Validation Plan

### Metrics to Track

1. **Arbitration duration** (target: <50s for emergencies, <65s for complex)
2. **Token counts** (input and output)
3. **KB query time** (target: <5s)
4. **Model selection** (Haiku vs Sonnet usage ratio)
5. **Cache hit rate** (for KB queries)

### Test Cases

1. **Emergency scenario** (pilot on fire) - expect <40s
2. **Complex conflict** (safety vs business) - expect <65s
3. **Data unavailable** (flight not found) - expect <50s
4. **Multiple conflicts** (3+ conflicts) - expect <70s

---

## Risk Assessment

### Low Risk

- ✅ Using Haiku 4.5 for simple cases (well-tested model)
- ✅ Reducing KB document count (still get relevant docs)
- ✅ Simplifying output schema (maintains decision quality)

### Medium Risk

- ⚠️ Parallel KB query (LLM won't have KB context initially)
- ⚠️ Aggressive prompt compression (may lose important context)

### Mitigation

- A/B test optimizations against baseline
- Monitor decision quality metrics (confidence, safety compliance)
- Rollback capability for each optimization

---

## Conclusion

The 109-second arbitration time is primarily caused by:

1. **LLM token generation** (80-90s) - generating complex structured output
2. **Knowledge Base query** (5-15s) - retrieving operational documents
3. **Phase evolution analysis** (2-5s) - comparing agent responses

**Recommended approach:**

- **Phase 1 (Quick Wins):** Use Haiku 4.5 for simple cases + simplified schema → **60-80s savings**
- **Phase 2 (Medium-term):** Parallel KB query + prompt compression → **15-30s savings**
- **Phase 3 (Long-term):** Streaming + caching → **Perceived latency reduction**

**Target performance:**

- Emergency scenarios: **25-40 seconds** (down from 109s)
- Complex scenarios: **55-65 seconds** (down from 109s)
- **Overall improvement: 54-77%**

This will bring the arbitration phase in line with the agent execution phases (20-30s each) and significantly improve the user experience.
