# Task 1: Async Execution Pattern Analysis

## Current Implementation Review

### ✅ What's Working Well

1. **Parallel Execution with asyncio.gather()**
   - Phase 1 (line 408-411): All 7 agents execute in parallel using `asyncio.gather(*agent_tasks)`
   - Phase 2 (line 543-546): All 7 agents execute in parallel using `asyncio.gather(*agent_tasks)`
   - Correct implementation - agents run concurrently within each phase

2. **Phase Synchronization**
   - Phase 1 completes fully before Phase 2 starts (line 783-786)
   - Phase 2 completes fully before Phase 3 starts (line 788-790)
   - Natural synchronization via `await asyncio.gather()` - no race conditions

3. **Error Handling Wrapper**
   - `run_agent_safely()` (lines 169-298) wraps each agent with:
     - Timeout handling via `asyncio.wait_for()`
     - Exception catching with try/except
     - Status tracking (success/timeout/error)
     - Duration measurement
     - Checkpoint persistence

4. **Checkpoint Persistence**
   - Comprehensive checkpoint saving at all stages
   - Thread management for audit trails
   - Proper error state persistence

### 🔧 Areas for Enhancement

1. **Timeout Configuration**
   - **Current**: Fixed 60s timeout for Phase 1, 90s for Phase 2
   - **Issue**: No differentiation between safety-critical and business agents
   - **Enhancement Needed**: Configurable timeouts per agent type
     - Safety agents (crew_compliance, maintenance, regulatory): 60s
     - Business agents (network, guest_experience, cargo, finance): 45s
     - Arbitrator: 90s

2. **Partial Failure Handling**
   - **Current**: Individual agent failures are caught and logged
   - **Issue**: No logic to halt on safety agent failures
   - **Enhancement Needed**:
     - If safety agent fails → halt execution (safety-critical)
     - If business agent fails → continue with available results
     - Track failure counts and percentages

3. **Error Context**
   - **Current**: Errors logged with traceback
   - **Enhancement Needed**: More structured error reporting
     - Error categorization (timeout vs exception vs validation)
     - Retry logic for transient failures
     - Better error messages for debugging

## Implementation Plan

### Enhancement 1: Configurable Timeouts Per Agent Type

**Location**: `src/main.py`

**Changes**:

1. Add timeout configuration constants at module level
2. Update `phase1_initial_recommendations()` to use agent-specific timeouts
3. Update `phase2_revision_round()` to use agent-specific timeouts

```python
# Add after BUSINESS_AGENTS definition
AGENT_TIMEOUTS = {
    "crew_compliance": 60,    # Safety-critical
    "maintenance": 60,         # Safety-critical
    "regulatory": 60,          # Safety-critical
    "network": 45,             # Business optimization
    "guest_experience": 45,    # Business optimization
    "cargo": 45,               # Business optimization
    "finance": 45,             # Business optimization
}

ARBITRATOR_TIMEOUT = 90  # Complex reasoning
```

**Update Phase 1**:

```python
# Line 408-411 - Current
agent_tasks = [
    run_agent_safely(name, fn, payload, llm, mcp_tools, timeout=60, ...)
    for name, fn in all_agents
]

# Enhanced
agent_tasks = [
    run_agent_safely(
        name, fn, payload, llm, mcp_tools,
        timeout=AGENT_TIMEOUTS.get(name, 60),  # Use agent-specific timeout
        thread_id=thread_id,
        checkpoint_saver=checkpoint_saver
    )
    for name, fn in all_agents
]
```

**Update Phase 2**:

```python
# Line 543-546 - Current
agent_tasks = [
    run_agent_safely(name, fn, payload, llm, mcp_tools, timeout=90, ...)
    for name, fn in all_agents
]

# Enhanced
agent_tasks = [
    run_agent_safely(
        name, fn, payload, llm, mcp_tools,
        timeout=AGENT_TIMEOUTS.get(name, 60) + 30,  # Add 30s for revision complexity
        thread_id=thread_id,
        checkpoint_saver=checkpoint_saver
    )
    for name, fn in all_agents
]
```

### Enhancement 2: Safety Agent Failure Halt Logic

**Location**: `src/main.py`

**Changes**:

1. Add safety agent list constant
2. Add failure checking after Phase 1 and Phase 2
3. Halt execution if safety agents fail

```python
# Add after BUSINESS_AGENTS definition
SAFETY_AGENT_NAMES = ["crew_compliance", "maintenance", "regulatory"]
```

**Add to Phase 1** (after line 413):

```python
# Check for safety agent failures
safety_failures = [
    result for result in agent_results
    if result.get("agent") in SAFETY_AGENT_NAMES
    and result.get("status") in ["timeout", "error"]
]

if safety_failures:
    failed_agents = [r.get("agent") for r in safety_failures]
    logger.error(f"❌ SAFETY AGENT FAILURE: {failed_agents}")
    logger.error("   Halting execution - manual intervention required")

    # Save failure checkpoint
    if thread_id and checkpoint_saver:
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="safety_failure_halt",
            state={
                "failed_agents": failed_agents,
                "failures": safety_failures
            },
            metadata={
                "phase": "phase1",
                "status": "halted",
                "reason": "safety_agent_failure",
                "timestamp": datetime.now().isoformat()
            }
        )

    # Return error response
    raise RuntimeError(
        f"Safety-critical agent(s) failed: {failed_agents}. "
        f"Manual intervention required. Cannot proceed with disruption analysis."
    )
```

**Add to Phase 2** (after line 548):

```python
# Check for safety agent failures
safety_failures = [
    result for result in agent_results
    if result.get("agent") in SAFETY_AGENT_NAMES
    and result.get("status") in ["timeout", "error"]
]

if safety_failures:
    failed_agents = [r.get("agent") for r in safety_failures]
    logger.error(f"❌ SAFETY AGENT FAILURE: {failed_agents}")
    logger.error("   Halting execution - manual intervention required")

    # Save failure checkpoint
    if thread_id and checkpoint_saver:
        await checkpoint_saver.save_checkpoint(
            thread_id=thread_id,
            checkpoint_id="safety_failure_halt",
            state={
                "failed_agents": failed_agents,
                "failures": safety_failures
            },
            metadata={
                "phase": "phase2",
                "status": "halted",
                "reason": "safety_agent_failure",
                "timestamp": datetime.now().isoformat()
            }
        )

    # Return error response
    raise RuntimeError(
        f"Safety-critical agent(s) failed in revision: {failed_agents}. "
        f"Manual intervention required. Cannot proceed with disruption analysis."
    )
```

### Enhancement 3: Enhanced Error Logging

**Location**: `src/main.py` - `run_agent_safely()`

**Changes**:

1. Add more context to timeout logs
2. Add more context to error logs
3. Categorize errors for better debugging

**Update Timeout Handling** (line 256-287):

```python
except asyncio.TimeoutError:
    duration = (datetime.now() - start_time).total_seconds()

    # Determine if this is a safety-critical agent
    is_safety_critical = agent_name in SAFETY_AGENT_NAMES

    logger.error(
        f"⏱ {agent_name} timeout after {timeout}s (actual: {duration:.2f}s)"
    )
    if is_safety_critical:
        logger.error(f"   ⚠️  CRITICAL: {agent_name} is a safety-critical agent")

    error_result = {
        "agent": agent_name,
        "status": "timeout",
        "error": f"Agent execution exceeded {timeout} second timeout",
        "duration_seconds": duration,
        "is_safety_critical": is_safety_critical,
        "timeout_threshold": timeout
    }

    # ... rest of checkpoint saving ...
```

**Update Exception Handling** (line 289-298):

```python
except Exception as e:
    duration = (datetime.now() - start_time).total_seconds()

    # Determine if this is a safety-critical agent
    is_safety_critical = agent_name in SAFETY_AGENT_NAMES

    logger.error(f"❌ {agent_name} error after {duration:.2f}s: {e}")
    if is_safety_critical:
        logger.error(f"   ⚠️  CRITICAL: {agent_name} is a safety-critical agent")
    logger.exception(f"Full traceback for {agent_name}:")

    error_result = {
        "agent": agent_name,
        "status": "error",
        "error": str(e),
        "error_type": type(e).__name__,
        "duration_seconds": duration,
        "is_safety_critical": is_safety_critical,
    }

    # ... rest of checkpoint saving ...
```

## Requirements Validation

### Requirement 1.1 ✅

**Phase 1 agents execute asynchronously using asyncio.gather()**

- Current: Line 408-411 uses `asyncio.gather(*agent_tasks)`
- Status: VERIFIED - Working correctly

### Requirement 1.2 ✅

**Phase 2 agents execute asynchronously using asyncio.gather()**

- Current: Line 543-546 uses `asyncio.gather(*agent_tasks)`
- Status: VERIFIED - Working correctly

### Requirement 1.3 ✅

**Orchestrator waits for all Phase 1 agents before Phase 2**

- Current: Line 783-786 awaits Phase 1 completion before starting Phase 2
- Status: VERIFIED - Natural synchronization via await

### Requirement 1.4 ✅

**Orchestrator waits for all Phase 2 agents before Phase 3**

- Current: Line 788-790 awaits Phase 2 completion before starting Phase 3
- Status: VERIFIED - Natural synchronization via await

### Requirement 1.5 🔧

**Timeout handling with graceful continuation**

- Current: Timeout caught in `run_agent_safely()` (line 256)
- Enhancement: Add agent-specific timeouts (safety: 60s, business: 45s)
- Status: NEEDS ENHANCEMENT

### Requirement 1.6 🔧

**Exception handling with graceful continuation**

- Current: Exceptions caught in `run_agent_safely()` (line 289)
- Enhancement: Add safety agent failure halt logic
- Status: NEEDS ENHANCEMENT

## Testing Strategy

### Unit Tests Needed

1. **test_agent_specific_timeouts()**
   - Verify safety agents get 60s timeout
   - Verify business agents get 45s timeout
   - Verify Phase 2 adds 30s to base timeout

2. **test_safety_agent_failure_halts_execution()**
   - Mock crew_compliance to fail
   - Verify execution halts with RuntimeError
   - Verify checkpoint saved with halt status

3. **test_business_agent_failure_continues()**
   - Mock network agent to fail
   - Verify execution continues
   - Verify other agents complete successfully

4. **test_phase_synchronization()**
   - Verify Phase 1 completes before Phase 2 starts
   - Verify Phase 2 completes before Phase 3 starts
   - Use timing assertions

5. **test_partial_failure_handling()**
   - Mock 2 business agents to fail
   - Verify execution continues with 5 successful agents
   - Verify collation includes error statuses

## Summary

**Current State**:

- ✅ Async execution with `asyncio.gather()` is correct
- ✅ Phase synchronization is correct
- ✅ Basic error handling is in place
- ✅ Checkpoint persistence is comprehensive

**Enhancements Needed**:

- 🔧 Add configurable timeouts per agent type
- 🔧 Add safety agent failure halt logic
- 🔧 Enhance error logging with safety-critical flags

**Impact**:

- Better resource utilization (business agents timeout faster)
- Safety-first approach (halt on safety failures)
- Improved debugging (better error context)
- Meets all requirements 1.1-1.6
