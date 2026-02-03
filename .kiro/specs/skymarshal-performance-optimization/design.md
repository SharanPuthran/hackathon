# Design Document

## Overview

This document describes the design for optimizing the SkyMarshal multi-agent system performance. The system currently orchestrates 7 specialized agents across 3 phases (initial recommendations, revision, arbitration) for airline disruption management. The optimization focuses on four key areas:

1. **Async Agent Execution**: Ensuring proper async invocation and synchronization across phases
2. **Prompt Optimization**: Optimizing all prompts for agent-to-agent communication using Claude best practices
3. **DynamoDB Batch Queries**: Implementing batch operations to reduce database latency
4. **Model Configuration**: Migrating to AWS Global CRIS models for improved availability and performance

The current system already uses `asyncio.gather()` for parallel execution within phases, but this design will verify and enhance async patterns, optimize prompts for machine-to-machine communication, add batch query support, and update model configurations.

## Architecture

### Current System Architecture

The SkyMarshal system follows a three-phase orchestration pattern:

**Phase 1 (Initial Recommendations)**:

- All 7 agents execute in parallel using `asyncio.gather()`
- Each agent receives augmented prompt with phase-specific instructions
- Agents query DynamoDB for operational data
- Results collated into `Collation` model

**Phase 2 (Revision Round)**:

- All 7 agents execute in parallel with Phase 1 results
- Agents review other recommendations and revise their own
- Results collated into second `Collation` model

**Phase 3 (Arbitration)**:

- Single arbitrator agent resolves conflicts
- Produces final decision with justification

### Key Components

1. **Orchestrator** (`src/main.py`): Manages phase execution and agent coordination
2. **Agents** (`src/agents/*/agent.py`): 7 specialized agents with SYSTEM_PROMPT
3. **Model Loader** (`src/model/load.py`): Loads Bedrock models with fallback logic
4. **DynamoDB Client** (`src/database/dynamodb.py`): Singleton client for data access
5. **Database Tools** (`src/database/tools.py`): Tool factories for agent-specific queries

## Components and Interfaces

### 1. Async Execution Enhancement

**Current State**:

- Agents already execute in parallel using `asyncio.gather()` in Phase 1 and Phase 2
- `run_agent_safely()` wraps each agent with timeout and error handling
- Synchronization happens naturally via `await asyncio.gather()`

**Design Changes**:

- **Verify** existing async patterns are optimal
- **Enhance** error handling for partial failures
- **Add** timeout configuration per agent type (safety vs business)
- **Ensure** proper cleanup on timeout/error

**Interface**:

```python
async def run_agent_safely(
    agent_name: str,
    agent_fn: Callable,
    payload: dict,
    llm: Any,
    mcp_tools: list,
    timeout: int = 60,  # Configurable per agent
    thread_id: str = None,
    checkpoint_saver: CheckpointSaver = None,
) -> dict:
    """
    Run agent with timeout, error handling, and checkpoint persistence.

    Returns:
        dict: Agent result with status (success|timeout|error)
    """
```

**Timeout Strategy**:

- Safety agents (crew_compliance, maintenance, regulatory): 60s (critical path)
- Business agents (network, guest_experience, cargo, finance): 45s (can tolerate partial results)
- Arbitrator: 90s (complex reasoning)

### 2. Prompt Optimization for A2A Communication

**Research Findings** ([Anthropic Documentation](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)):

Key principles for Claude prompt optimization:

1. **Use XML tags** for structure (Claude trained on XML)
2. **Be specific and concise** - avoid verbose explanations
3. **Consistent tag naming** throughout prompts
4. **Nest tags hierarchically** for complex structures
5. **Remove human-oriented language** for A2A communication

**Current State**:

- Prompts contain human-oriented explanations
- Some redundant context in multi-round communication
- Verbose instructions that could be condensed

**Design Changes**:

**Orchestrator Prompts**:

```xml
<!-- Phase 1: Initial (Current - Verbose) -->
{user_prompt}

Please analyze this disruption and provide your initial recommendation from your domain perspective.

<!-- Phase 1: Initial (Optimized - Concise) -->
<disruption>{user_prompt}</disruption>
<task>initial_analysis</task>
```

```xml
<!-- Phase 2: Revision (Current - Verbose) -->
{user_prompt}

Other agents have provided the following recommendations:

CREW_COMPLIANCE:
  Recommendation: {recommendation}
  Confidence: {confidence}
  ...

Review other agents' recommendations and revise if needed.

<!-- Phase 2: Revision (Optimized - Structured) -->
<disruption>{user_prompt}</disruption>
<task>revision</task>
<context>
  <agent name="crew_compliance">
    <recommendation>{recommendation}</recommendation>
    <confidence>{confidence}</confidence>
    <constraints>{binding_constraints}</constraints>
  </agent>
  ...
</context>
```

**Agent System Prompts**:

```xml
<!-- Current (Verbose) -->
<role>Crew Compliance: validate FDP limits, rest requirements, qualifications</role>

<critical>
Safety constraints are BINDING. Reject any scenario violating crew duty limits. Zero tolerance for FTL violations.
</critical>

<workflow>
1. Extract: flight_number, date, event from user prompt
2. Query: query_flight() → flight_id, then query_crew_roster() → crew list
3. Calculate FDP: (duty_end - duty_start) + delays + positioning
4. Validate: FDP ≤ max_fdp, rest ≥ min_rest, qualifications current
5. Assess: Fatigue risk = (current_fdp / max_fdp) × 100%
6. Return: APPROVED | DENIED | REQUIRES_CREW_CHANGE with binding constraints
</workflow>

<!-- Optimized (Concise) -->
<role>crew_compliance</role>
<constraints type="binding">fdp_limits, rest_requirements, qualifications</constraints>
<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → crew_roster → crew_members</step>
  <step>calculate: fdp = duty_end - duty_start + delays</step>
  <step>validate: fdp ≤ max_fdp, rest ≥ min_rest, quals_current</step>
  <step>assess: risk = (fdp / max_fdp) × 100</step>
  <step>return: APPROVED|DENIED|CREW_CHANGE + constraints</step>
</workflow>
```

**Arbitrator Prompts**:

```xml
<!-- Current (Verbose) -->
You are the final arbitrator for SkyMarshal disruption management.
Review all agent recommendations and resolve conflicts.
Safety constraints are binding and cannot be overridden.

<!-- Optimized (Structured) -->
<role>arbitrator</role>
<priority>safety_constraints_binding</priority>
<input>
  <phase1>{initial_collation}</phase1>
  <phase2>{revised_collation}</phase2>
</input>
<task>resolve_conflicts, final_decision</task>
```

**Token Savings Estimate**:

- Orchestrator prompts: ~30% reduction (200 → 140 tokens per agent)
- Agent system prompts: ~40% reduction (800 → 480 tokens per agent)
- Arbitrator prompts: ~35% reduction (400 → 260 tokens)
- Total per request: ~2,500 tokens saved (7 agents × 2 phases + arbitrator)

### 3. DynamoDB Batch Query Implementation

**Current State**:

- All queries use individual `get_item()` or `query()` operations
- Multiple sequential queries when agents need related data
- Example: Getting crew roster requires N+1 queries (1 for roster, N for crew members)

**Design Changes**:

**Batch Query Interface**:

```python
class DynamoDBClient:
    def batch_get_items(
        self,
        table_name: str,
        keys: List[Dict[str, Any]],
        max_batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Batch get items from DynamoDB table.

        Automatically splits requests into batches of max_batch_size.
        Handles unprocessed keys with exponential backoff retry.

        Args:
            table_name: DynamoDB table name
            keys: List of primary key dicts
            max_batch_size: Max items per batch (default 100, AWS limit)

        Returns:
            List of items retrieved
        """

    def batch_get_crew_members(
        self,
        crew_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Batch get crew member details.

        Optimized for crew compliance agent.
        """

    def batch_get_flights(
        self,
        flight_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Batch get flight details.

        Optimized for network agent.
        """
```

**Implementation Strategy**:

```python
def batch_get_items(self, table_name: str, keys: List[Dict], max_batch_size: int = 100):
    """Batch get with automatic splitting and retry logic"""

    # Split into batches of max_batch_size
    batches = [keys[i:i + max_batch_size] for i in range(0, len(keys), max_batch_size)]

    all_items = []
    for batch in batches:
        unprocessed = batch
        retry_count = 0
        max_retries = 3

        while unprocessed and retry_count < max_retries:
            response = self.client.batch_get_item(
                RequestItems={
                    table_name: {'Keys': unprocessed}
                }
            )

            # Collect successful items
            all_items.extend(response['Responses'].get(table_name, []))

            # Handle unprocessed keys
            unprocessed = response.get('UnprocessedKeys', {}).get(table_name, {}).get('Keys', [])

            if unprocessed:
                # Exponential backoff
                wait_time = (2 ** retry_count) * 0.1
                await asyncio.sleep(wait_time)
                retry_count += 1

        if unprocessed:
            logger.warning(f"Failed to process {len(unprocessed)} keys after {max_retries} retries")

    return all_items
```

**Agent Tool Updates**:

Agents will use batch queries when multiple items are needed:

```python
# Crew Compliance Agent - Before
def query_crew_roster_and_members(flight_id: str) -> dict:
    roster = query_crew_roster_by_flight(flight_id)  # 1 query
    crew_members = []
    for assignment in roster:
        member = get_crew_member(assignment['crew_id'])  # N queries
        crew_members.append(member)
    return {"roster": roster, "members": crew_members}

# Crew Compliance Agent - After (Batch)
def query_crew_roster_and_members(flight_id: str) -> dict:
    roster = query_crew_roster_by_flight(flight_id)  # 1 query
    crew_ids = [a['crew_id'] for a in roster]
    crew_members = batch_get_crew_members(crew_ids)  # 1 batch query
    return {"roster": roster, "members": crew_members}
```

**Performance Impact**:

- Crew compliance: 1 + N queries → 2 queries (typical N=4-6 crew members)
- Network agent: 1 + M queries → 2 queries (typical M=3-5 connecting flights)
- Guest experience: 1 + P queries → 2 queries (typical P=50-200 passengers)
- Estimated latency reduction: 60-80% for multi-item lookups

### 4. Model Configuration Updates

**Research Findings** ([AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference-support.html)):

AWS Global Cross-Region Inference (CRIS) provides:

- **Global routing**: Requests routed to optimal commercial regions worldwide
- **Higher throughput**: Better availability during peak usage
- **Reduced throttling**: Distributed load across multiple regions
- **Same pricing**: No additional cost for global inference

**Model IDs** (from AWS documentation):

- **Global Haiku 4.5**: `global.anthropic.claude-haiku-4-5-20251001-v1:0`
- **Global Sonnet 4.5**: `global.anthropic.claude-sonnet-4-5-20250929-v1:0`
- **Global Opus 4.5**: `global.anthropic.claude-opus-4-5-20251101-v1:0`

**Current State**:

```python
# src/model/load.py - Current
MODEL_PRIORITY = [
    {
        "id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",  # Already using Global CRIS
        "name": "Claude Sonnet 4.5 (Global CRIS)",
        ...
    },
    ...
]

def load_model() -> ChatBedrock:
    """Uses Claude Sonnet 4.5 Global CRIS"""

def load_fast_model() -> ChatBedrock:
    """Uses Claude Haiku 4.5 Global CRIS"""

def load_arbitrator_model() -> ChatBedrock:
    """Uses Claude Sonnet 4.5 Global CRIS"""
```

**Design Changes**:

The current implementation already uses Global CRIS models correctly. However, we need to:

1. **Update agent model assignments**:
   - Safety agents (crew_compliance, maintenance, regulatory): Keep Sonnet 4.5 (accuracy critical)
   - Business agents (network, guest_experience, cargo, finance): Switch to Haiku 4.5 (speed priority)
   - Orchestrator: Keep Sonnet 4.5 (coordination requires reasoning)
   - Arbitrator: Keep Sonnet 4.5 (complex conflict resolution)

2. **Add model configuration per agent type**:

```python
# src/model/load.py - Enhanced
AGENT_MODEL_CONFIG = {
    "safety": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "temperature": 0.3,
        "max_tokens": 8192,
        "reason": "Safety-critical analysis requires high accuracy"
    },
    "business": {
        "model_id": "global.anthropic.claude-haiku-4-5-20251001-v1:0",
        "temperature": 0.3,
        "max_tokens": 4096,
        "reason": "Business analysis prioritizes speed over deep reasoning"
    },
    "arbitrator": {
        "model_id": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "temperature": 0.2,
        "max_tokens": 8192,
        "reason": "Conflict resolution requires balanced reasoning"
    }
}

def load_model_for_agent(agent_type: str = "safety") -> ChatBedrock:
    """Load model optimized for agent type"""
    config = AGENT_MODEL_CONFIG[agent_type]
    return ChatBedrock(
        model_id=config["model_id"],
        model_kwargs={
            "temperature": config["temperature"],
            "max_tokens": config["max_tokens"],
        },
        config=BOTO_CONFIG
    )
```

3. **Update orchestrator to use agent-specific models**:

```python
# src/main.py - Enhanced
async def run_agent_safely(
    agent_name: str,
    agent_fn: Callable,
    payload: dict,
    llm: Any,  # Will be agent-specific model
    mcp_tools: list,
    ...
) -> dict:
    """Run agent with appropriate model"""
```

**Performance Impact**:

- Business agents: 2-3x faster response (Haiku vs Sonnet)
- Cost reduction: ~70% for business agents (Haiku is cheaper)
- Safety agents: No change (accuracy maintained)
- Overall system: 30-40% faster execution

## Data Models

### Batch Query Request/Response

```python
from typing import List, Dict, Any
from pydantic import BaseModel, Field

class BatchGetRequest(BaseModel):
    """Request for batch get operation"""
    table_name: str = Field(..., description="DynamoDB table name")
    keys: List[Dict[str, Any]] = Field(..., description="List of primary keys")
    max_batch_size: int = Field(default=100, description="Max items per batch")

class BatchGetResponse(BaseModel):
    """Response from batch get operation"""
    items: List[Dict[str, Any]] = Field(..., description="Retrieved items")
    unprocessed_keys: List[Dict[str, Any]] = Field(default_factory=list, description="Keys that failed")
    retry_count: int = Field(default=0, description="Number of retries performed")
```

### Agent Model Configuration

```python
from enum import Enum
from pydantic import BaseModel

class AgentType(str, Enum):
    """Agent type for model selection"""
    SAFETY = "safety"
    BUSINESS = "business"
    ARBITRATOR = "arbitrator"

class ModelConfig(BaseModel):
    """Model configuration for agent type"""
    model_id: str
    temperature: float
    max_tokens: int
    reason: str
```

### Optimized Prompt Structure

```python
from pydantic import BaseModel
from typing import Optional, Dict, List

class OptimizedPrompt(BaseModel):
    """Structured prompt for A2A communication"""
    disruption: str = Field(..., description="User's disruption description")
    task: str = Field(..., description="Task type: initial_analysis|revision")
    context: Optional[Dict[str, Any]] = Field(None, description="Phase 1 results for revision")

    def to_xml(self) -> str:
        """Convert to XML format for Claude"""
        xml = f"<disruption>{self.disruption}</disruption>\n"
        xml += f"<task>{self.task}</task>\n"
        if self.context:
            xml += "<context>\n"
            for agent_name, response in self.context.items():
                xml += f'  <agent name="{agent_name}">\n'
                xml += f"    <recommendation>{response['recommendation']}</recommendation>\n"
                xml += f"    <confidence>{response['confidence']}</confidence>\n"
                if response.get('binding_constraints'):
                    xml += f"    <constraints>{response['binding_constraints']}</constraints>\n"
                xml += "  </agent>\n"
            xml += "</context>\n"
        return xml
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property 1: Phase Synchronization

_For any_ orchestration execution, when a phase completes, all agents in that phase must have returned results (success, timeout, or error) before the next phase begins.

**Validates: Requirements 1.3, 1.4**

### Property 2: Agent Failure Resilience

_For any_ agent execution, when an agent times out or raises an exception, the orchestrator must capture the failure, log it with context, and continue execution with remaining agents.

**Validates: Requirements 1.5, 1.6, 6.1, 6.5**

### Property 3: Prompt Structure Compliance

_For any_ generated prompt (Phase 1, Phase 2, or Arbitrator), the prompt must use XML tag structure without verbose human-oriented explanations, and total token count must be at least 30% less than baseline.

**Validates: Requirements 2.1, 2.2, 2.7**

### Property 4: Batch Query Usage

_For any_ agent request requiring multiple items from the same table, the DynamoDB client must use BatchGetItem instead of multiple individual get_item calls.

**Validates: Requirements 3.1, 3.7**

### Property 5: Batch Size Handling

_For any_ batch query request with N items where N > 100, the system must automatically split the request into ⌈N/100⌉ batches and execute them sequentially.

**Validates: Requirements 3.3**

### Property 6: Batch Query Retry Logic

_For any_ batch query that returns unprocessed keys or fails, the system must retry those keys with exponential backoff (wait time = 2^retry_count × 0.1 seconds) up to 3 attempts.

**Validates: Requirements 3.4, 3.5**

### Property 7: Partial Batch Failure Handling

_For any_ batch query where some items succeed and some fail, the system must return all successful items and report failed items separately, allowing the caller to handle partial results.

**Validates: Requirements 6.2**

### Property 8: Model Retry with Backoff

_For any_ model invocation failure, the system must retry up to 3 times with exponential backoff before returning a degraded response.

**Validates: Requirements 6.3**

### Property 9: Safety Agent Failure Halt

_For any_ execution where a critical safety agent (crew_compliance, maintenance, or regulatory) fails after all retries, the system must halt execution and return an error requiring manual intervention.

**Validates: Requirements 6.6**

### Property 10: Execution Time Measurement

_For any_ orchestration execution, the system must record duration_seconds for each agent, each phase, and the total execution, with all durations being non-negative numbers.

**Validates: Requirements 5.4, 5.5**

### Property 11: Backward Compatibility

_For any_ existing query pattern using single-item methods (get_item, query), the system must continue to support those methods with identical behavior after batch query implementation.

**Validates: Requirements 7.1**

### Property 12: Output Quality Preservation

_For any_ test case with baseline output, after applying optimizations (prompt changes, model changes), the new output must be functionally equivalent (same recommendations, similar confidence scores ±0.1, same binding constraints).

**Validates: Requirements 5.6, 7.2, 7.3**

## Error Handling

### Async Execution Errors

**Timeout Handling**:

- Each agent has configurable timeout (safety: 60s, business: 45s, arbitrator: 90s)
- On timeout: Log warning, mark agent as "timeout" status, continue with other agents
- Checkpoint saved with timeout status for audit trail

**Exception Handling**:

- All agent exceptions caught by `run_agent_safely()` wrapper
- Exception logged with full traceback
- Agent marked as "error" status with error details
- Checkpoint saved with error information
- Orchestrator continues with remaining agents

**Partial Failure Strategy**:

- If <50% of agents fail: Continue with available results
- If ≥50% of agents fail: Return degraded response with warning
- If all safety agents fail: Halt execution (safety-critical)

### Batch Query Errors

**Retry Logic**:

```python
max_retries = 3
retry_count = 0
wait_time = 0.1  # Initial wait

while unprocessed_keys and retry_count < max_retries:
    # Retry unprocessed keys
    wait_time = (2 ** retry_count) * 0.1  # Exponential backoff
    await asyncio.sleep(wait_time)
    retry_count += 1
```

**Partial Success Handling**:

- Return all successfully retrieved items
- Log warning for failed items
- Include `unprocessed_keys` in response for caller to handle
- Don't fail entire operation if some items succeed

**Throttling Handling**:

- DynamoDB throttling triggers exponential backoff
- After 3 retries, return partial results with warning
- Log throttling events for capacity planning

### Model Invocation Errors

**Retry Strategy**:

- Transient errors (throttling, network): Retry with backoff
- Permanent errors (invalid model ID, auth): Fail immediately
- After 3 retries: Return degraded response

**Fallback Models**:

- If primary model fails: Try next model in priority list
- Model priority: Sonnet 4.5 → Haiku 4.5 → Opus 4.5 → Nova 2 Lite
- Log model fallback for monitoring

### Prompt Optimization Errors

**Validation**:

- Validate XML structure before sending to model
- Ensure all required tags present
- Verify no malformed XML

**Fallback**:

- If XML generation fails: Use plain text format
- Log XML generation errors
- Don't block execution on prompt formatting issues

## Testing Strategy

### Dual Testing Approach

The testing strategy combines unit tests for specific scenarios and property-based tests for universal correctness:

**Unit Tests**: Verify specific examples, edge cases, and error conditions

- Specific timeout scenarios (agent times out at exactly 60s)
- Specific batch sizes (100 items, 101 items, 250 items)
- Specific error conditions (DynamoDB throttling, model unavailable)
- Integration points between components

**Property-Based Tests**: Verify universal properties across all inputs

- Phase synchronization holds for any agent execution pattern
- Batch query splitting works for any N > 100
- Retry logic works for any failure pattern
- Output quality preserved for any test case

Together, these approaches provide comprehensive coverage: unit tests catch concrete bugs, property tests verify general correctness.

### Property-Based Testing Configuration

**Library**: Hypothesis (Python property-based testing library)

**Configuration**:

- Minimum 100 iterations per property test (due to randomization)
- Each property test references its design document property
- Tag format: `# Feature: skymarshal-performance-optimization, Property {number}: {property_text}`

**Example Property Test**:

```python
from hypothesis import given, strategies as st
import pytest

# Feature: skymarshal-performance-optimization, Property 5: Batch Size Handling
@given(item_count=st.integers(min_value=101, max_value=1000))
@pytest.mark.property_test
def test_batch_splitting_for_large_requests(item_count):
    """
    Property: For any batch query with N > 100 items,
    the system splits into ceil(N/100) batches.
    """
    keys = [{"id": str(i)} for i in range(item_count)]

    # Execute batch query
    result = dynamodb_client.batch_get_items("TestTable", keys)

    # Verify correct number of batches
    expected_batches = (item_count + 99) // 100  # Ceiling division
    assert result.batch_count == expected_batches

    # Verify all items retrieved (or properly reported as failed)
    assert len(result.items) + len(result.unprocessed_keys) == item_count
```

### Unit Test Coverage

**Async Execution Tests**:

- `test_phase1_parallel_execution()`: Verify all 7 agents run in parallel
- `test_phase2_parallel_execution()`: Verify Phase 2 parallelism
- `test_agent_timeout_handling()`: Verify timeout at 60s
- `test_agent_exception_handling()`: Verify exception capture
- `test_phase_synchronization()`: Verify Phase 1 completes before Phase 2

**Prompt Optimization Tests**:

- `test_phase1_prompt_xml_structure()`: Verify XML format
- `test_phase2_prompt_xml_structure()`: Verify XML with context
- `test_arbitrator_prompt_xml_structure()`: Verify arbitrator XML
- `test_prompt_token_reduction()`: Verify 30% token reduction
- `test_prompt_no_verbose_text()`: Verify no human-oriented text

**Batch Query Tests**:

- `test_batch_get_100_items()`: Verify 100-item batch works
- `test_batch_get_101_items()`: Verify automatic splitting
- `test_batch_get_with_failures()`: Verify partial failure handling
- `test_batch_retry_logic()`: Verify exponential backoff
- `test_batch_unprocessed_keys()`: Verify unprocessed key retry

**Model Configuration Tests**:

- `test_safety_agent_uses_sonnet()`: Verify safety agents use Sonnet
- `test_business_agent_uses_haiku()`: Verify business agents use Haiku
- `test_arbitrator_uses_sonnet()`: Verify arbitrator uses Sonnet
- `test_model_fallback()`: Verify fallback to next model on failure

**Error Handling Tests**:

- `test_safety_agent_failure_halts()`: Verify system halts on safety failure
- `test_business_agent_failure_continues()`: Verify system continues on business failure
- `test_model_retry_exhaustion()`: Verify degraded response after 3 retries
- `test_batch_query_throttling()`: Verify throttling handling

### Integration Tests

**End-to-End Optimization Tests**:

- `test_optimized_execution_faster()`: Verify overall speedup
- `test_optimized_output_equivalent()`: Verify output quality preserved
- `test_optimized_cost_reduction()`: Verify cost reduction from Haiku usage
- `test_optimized_backward_compatible()`: Verify old queries still work

### Performance Benchmarks

**Baseline Measurements** (before optimization):

- Phase 1 duration: ~45s (7 agents × ~6s each, parallel)
- Phase 2 duration: ~60s (7 agents × ~8s each, parallel)
- Phase 3 duration: ~15s (arbitrator)
- Total: ~120s
- Token usage: ~15,000 tokens per request
- Cost: ~$0.15 per request (Sonnet pricing)

**Target Measurements** (after optimization):

- Phase 1 duration: ~35s (safety agents 6s, business agents 3s)
- Phase 2 duration: ~45s (safety agents 8s, business agents 4s)
- Phase 3 duration: ~15s (arbitrator unchanged)
- Total: ~95s (21% improvement)
- Token usage: ~10,500 tokens per request (30% reduction)
- Cost: ~$0.08 per request (47% reduction from Haiku + token savings)

**Measurement Approach**:

- Run 100 test cases with baseline system
- Run same 100 test cases with optimized system
- Compare median, p95, and p99 latencies
- Verify output quality equivalence (recommendations match, confidence within ±0.1)
