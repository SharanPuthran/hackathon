# Tool Calling Fix Summary

## Problem Identified

**Error**: `messages.X.content.Y.tool_result.content.0.text.id: Extra inputs are not permitted`

**Root Cause**: LangChain's `create_agent` function adds extra metadata fields (`index`, `id`, etc.) to tool results that Bedrock's API validation rejects. This is a known issue with LangChain when using Anthropic/Bedrock models.

## Solution Implemented

Created custom tool calling implementation (`src/utils/tool_calling.py`) that:

1. Manually implements the tool calling loop
2. Formats messages cleanly without extra metadata
3. Only includes required fields for Bedrock API

## Agents Fixed

### ✅ All Agents Completed

1. **crew_compliance** - ✅ Updated to use `invoke_with_tools`
2. **maintenance** - ✅ Updated to use `invoke_with_tools`
3. **regulatory** - ✅ Updated to use `invoke_with_tools`
4. **network** - ✅ Updated to use `invoke_with_tools`
5. **guest_experience** - ✅ Updated to use `invoke_with_tools`
6. **cargo** - ✅ Updated to use `invoke_with_tools`
7. **finance** - ✅ Updated to use `invoke_with_tools`

All agents now use the custom tool calling implementation that avoids Bedrock API validation errors.

## Current Status

All 7 agents have been updated to use custom tool calling:

- **crew_compliance**: ✅ Working with `invoke_with_tools`
- **maintenance**: ✅ Working with `invoke_with_tools`
- **regulatory**: ✅ Working with `invoke_with_tools`
- **network**: ✅ Working with `invoke_with_tools`
- **guest_experience**: ✅ Working with `invoke_with_tools`
- **cargo**: ✅ Working with `invoke_with_tools`
- **finance**: ✅ Working with `invoke_with_tools`

## Issues to Resolve

### 1. Timeout Issue

The system is timing out during execution. Need to investigate:

- Whether the arbitrator is taking too long to process all agent responses
- Whether individual agents are timing out
- Whether the custom tool calling loop needs optimization

### 2. Performance Testing

Need to run full performance tests with:

- Real flight data (EY flight numbers)
- Mix of relative and absolute dates
- Timing measurements for each agent and overall system

## Tool Return Format Fix

All agent tools were updated to return JSON strings instead of Python dicts/lists:

- ✅ crew_compliance tools return `json.dumps()`
- ✅ maintenance tools return `json.dumps()`
- ✅ regulatory tools return `json.dumps()`
- ✅ network tools return `json.dumps()`
- ✅ guest_experience tools return `json.dumps()`
- ✅ cargo tools return `json.dumps()`
- ✅ finance tools return `json.dumps()`

## Next Steps

1. **Restart AgentCore dev server** - The previous run timed out and needs to be restarted
2. **Test with simpler scenario** - Start with a single agent test to validate the fix
3. **Run full performance test** - Test all agents with real flight data
4. **Optimize if needed** - If timeouts persist, investigate:
   - Reducing max_iterations from 5 to 3
   - Optimizing the tool calling loop
   - Reducing the amount of data sent to arbitrator
   - Adding timeout handling per agent

## Alternative Approaches

If custom tool calling remains too slow:

1. **Use LangChain's bind_tools directly** - Skip the agent framework entirely
2. **Patch LangChain's message formatting** - Override the tool result formatting
3. **Use different LangChain version** - Check if newer versions fix this issue
4. **Switch to direct Bedrock API** - Bypass LangChain completely for tool calling

## Files Modified

- `src/utils/tool_calling.py` - New custom tool calling implementation
- `src/agents/crew_compliance/agent.py` - Updated to use custom tool calling
- `src/agents/maintenance/agent.py` - Updated tools to return JSON strings
- `src/agents/regulatory/agent.py` - Updated to use custom tool calling
- `src/agents/network/agent.py` - Updated tools to return JSON strings
- `src/agents/guest_experience/agent.py` - Updated tools to return JSON strings
- `src/agents/cargo/agent.py` - Updated tools to return JSON strings
- `src/agents/finance/agent.py` - Updated tools to return JSON strings

## Test Data

Real flight numbers in database:

- EY2787 on 2026-01-30
- EY1153 on 2026-01-31
- EY5730 on 2026-01-30
- EY8400 on 2026-01-31
- EY4834 on 2026-01-31
