# Performance Optimization Analysis

**Date**: February 3, 2026  
**Status**: 🔍 DEBUGGING IN PROGRESS

---

## Performance Baseline

### Previous Execution (Before Optimizations)

- **Total Time**: 162 seconds (2.7 minutes)
- **Phase 1**: 47s (all 7 agents parallel)
- **Phase 2**: 60s (hit timeout)
- **Phase 3**: 49s (arbitration)
- **Model**: `us.anthropic.claude-sonnet-4-5-20250929-v1:0` (Global CRIS)

### Agent-Level Breakdown

| Agent            | Duration | Status     | Issue             |
| ---------------- | -------- | ---------- | ----------------- |
| guest_experience | 47s      | ⚠️ Slowest | Complex reasoning |
| cargo            | 45s      | ⚠️ Slow    | Complex reasoning |
| finance          | 37s      | Moderate   | -                 |
| crew_compliance  | 36s      | Moderate   | -                 |
| regulatory       | 30s      | OK         | -                 |
| maintenance      | 17s      | ✅ Fast    | -                 |
| network          | 17s      | ✅ Fast    | -                 |

---

## Root Cause Analysis

### Issue 1: Bedrock API Read Timeouts ⚠️ CRITICAL

**Symptom**: Model invocations timing out after 60 seconds

```
botocore.exceptions.ReadTimeoutError: Read timeout on endpoint URL:
"https://bedrock-runtime.us-east-1.amazonaws.com/model/global.anthropic.claude-sonnet-4-5-20250929-v1%3A0/invoke"
```

**Root Cause**:

- Claude Sonnet 4.5 is generating very long, detailed responses
- Agents have verbose system prompts with extensive chain-of-thought reasoning
- Each agent is making multiple tool calls (database queries)
- Bedrock API has 60s read timeout by default

**Impact**: Agents cannot complete, causing cascading failures

### Issue 2: Phase 2 Timeout

**Symptom**: Phase 2 hitting 60s timeout, agents not completing

**Root Cause**:

- Phase 2 agents review ALL other agents' recommendations (large context)
- Augmented prompt includes full Phase 1 responses
- More reasoning required = longer execution time

**Impact**: Incomplete agent responses, degraded decision quality

### Issue 3: Model Test Overhead (FIXED ✅)

**Previous Issue**: Testing model availability added 5-10s per cold start

**Fix Applied**: Added `skip_test=True` parameter to `load_model()`

**Impact**: Eliminated 5-10s startup latency

---

## Optimizations Applied

### ✅ 1. Skip Model Testing (COMPLETED)

**Change**: Modified `load_model()` to skip availability test by default

```python
def load_model(skip_test: bool = True) -> ChatBedrock:
    # Skip test for faster startup when using Global CRIS endpoints
    if skip_test:
        logger.info(f"✅ Using {model_name} (skip_test=True)")
        return ChatBedrock(model_id=model_id, ...)
```

**Impact**: -5-10s startup time

### ✅ 2. Increased Phase 2 Timeout (COMPLETED)

**Change**: Increased Phase 2 timeout from 60s to 90s

```python
# Phase 2 has longer timeout (90s) since agents review other recommendations
agent_tasks = [
    run_agent_safely(name, fn, payload, llm, mcp_tools, timeout=90, ...)
]
```

**Impact**: Prevents premature timeout in Phase 2

### ✅ 3. Added Fast Model Function (COMPLETED)

**Change**: Created `load_fast_model()` for business agents

```python
def load_fast_model() -> ChatBedrock:
    """Load Claude Haiku 4.5 for faster responses"""
    return ChatBedrock(
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        model_kwargs={"temperature": 0.2, "max_tokens": 4096}
    )
```

**Status**: Function created but NOT YET INTEGRATED

**Potential Impact**: -20-30s for business agents

---

## Recommended Optimizations (NOT YET APPLIED)

### 🔧 1. Use Haiku for Business Agents (HIGH PRIORITY)

**Rationale**: Business agents (network, guest_experience, cargo, finance) don't need deep reasoning like safety agents

**Implementation**:

```python
# In main.py handle_disruption()
llm_fast = load_fast_model()  # Haiku for business agents
llm = load_model()  # Sonnet for safety agents + arbitrator

# Phase 1: Use appropriate model per agent type
for name, fn in SAFETY_AGENTS:
    run_agent_safely(name, fn, payload, llm, ...)  # Sonnet
for name, fn in BUSINESS_AGENTS:
    run_agent_safely(name, fn, payload, llm_fast, ...)  # Haiku
```

**Expected Impact**:

- Business agents: 45s → 15-20s (60-70% faster)
- Total Phase 1: 47s → 25-30s
- Total execution: 162s → 110-120s

### 🔧 2. Reduce max_tokens for Faster Completion (MEDIUM PRIORITY)

**Current**: `max_tokens: 8192` for all agents

**Proposed**:

- Safety agents: 8192 (need detailed reasoning)
- Business agents: 4096 (faster, sufficient)
- Arbitrator: 8192 (complex decision-making)

**Expected Impact**: -10-15s total

### 🔧 3. Optimize Agent Prompts (MEDIUM PRIORITY)

**Issue**: Agent prompts are very verbose with extensive instructions

**Proposed**:

- Remove redundant instructions
- Use more concise language
- Move examples to separate documentation
- Reduce chain-of-thought verbosity

**Expected Impact**: -15-20s (faster model processing)

### 🔧 4. Implement Early Termination (LOW PRIORITY)

**Scenario**: When flight data is not found, skip Phase 2 and Phase 3

**Implementation**:

```python
# After Phase 1
if all_agents_report_data_unavailable(initial_collation):
    return {
        "status": "data_unavailable",
        "final_decision": "Cannot proceed - flight data not found",
        "recommendations": ["Verify flight exists", "Check database"]
    }
```

**Expected Impact**: 162s → 50s for data unavailability scenarios

### 🔧 5. Parallel Phase Execution (ADVANCED)

**Current**: Phase 1 → Phase 2 → Phase 3 (sequential)

**Proposed**: Run safety and business agents in separate phases

- Phase 1a: Safety agents (crew, maintenance, regulatory)
- Phase 1b: Business agents (network, guest, cargo, finance) - START IMMEDIATELY
- Phase 2: Revision (only if needed)
- Phase 3: Arbitration

**Expected Impact**: -20-30s (overlapping execution)

**Risk**: Higher complexity, potential for race conditions

---

## Immediate Action Plan

### Step 1: Fix Bedrock Timeout Issue ⚠️ URGENT

**Problem**: 60s read timeout is too short for complex agent reasoning

**Options**:

**Option A: Increase Boto3 Timeout (RECOMMENDED)**

```python
# In model/load.py
import boto3
from botocore.config import Config

config = Config(
    read_timeout=120,  # 2 minutes
    connect_timeout=10
)

bedrock_runtime = boto3.client('bedrock-runtime', config=config)
```

**Option B: Use Streaming API**

```python
# Use Bedrock streaming to avoid timeout
response = bedrock_runtime.invoke_model_with_response_stream(...)
```

**Option C: Simplify Agent Prompts**

- Reduce verbosity
- Remove unnecessary examples
- Streamline reasoning steps

### Step 2: Integrate Fast Model for Business Agents

**Change**: Modify `handle_disruption()` to use Haiku for business agents

**Files to modify**:

- `src/main.py` - Add `llm_fast = load_fast_model()`
- Pass `llm_fast` to business agents in Phase 1 and Phase 2

### Step 3: Test and Measure

**Test Scenario**: Same flight prompt (EY123 delayed 3 hours)

**Success Criteria**:

- Total execution < 90 seconds
- No timeouts
- All agents complete successfully

---

## Performance Targets

### Current State

- **Total**: 162s
- **Phase 1**: 47s
- **Phase 2**: 60s (timeout)
- **Phase 3**: 49s

### Target State (After All Optimizations)

- **Total**: 60-80s (50-60% improvement)
- **Phase 1**: 20-25s (safety: Sonnet, business: Haiku)
- **Phase 2**: 25-30s (faster model + increased timeout)
- **Phase 3**: 15-20s (optimized arbitrator prompt)

### Stretch Goal

- **Total**: 40-50s (70% improvement)
- Requires: Parallel phases + aggressive prompt optimization

---

## Risk Assessment

| Optimization                  | Risk                    | Mitigation                                 |
| ----------------------------- | ----------------------- | ------------------------------------------ |
| Use Haiku for business agents | Lower quality reasoning | Test thoroughly, compare outputs           |
| Reduce max_tokens             | Incomplete responses    | Monitor truncation, adjust if needed       |
| Simplify prompts              | Miss edge cases         | Comprehensive testing, gradual rollout     |
| Parallel phases               | Race conditions         | Careful synchronization, extensive testing |
| Early termination             | Skip valid scenarios    | Conservative detection logic               |

---

## Next Steps

1. **IMMEDIATE**: Fix Bedrock timeout (increase to 120s)
2. **HIGH PRIORITY**: Integrate Haiku for business agents
3. **MEDIUM PRIORITY**: Optimize agent prompts
4. **LOW PRIORITY**: Implement early termination
5. **FUTURE**: Consider parallel phase execution

---

## Monitoring and Metrics

### Key Metrics to Track

- Total execution time
- Per-agent execution time
- Timeout rate
- Model token usage
- Cost per request
- Error rate

### CloudWatch Alarms

- Alert if execution time > 120s
- Alert if timeout rate > 5%
- Alert if error rate > 2%

---

**Report Generated**: February 3, 2026  
**Status**: Debugging in progress - Bedrock timeout issue identified  
**Next Action**: Increase Boto3 read timeout to 120s
