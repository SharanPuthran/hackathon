# Prompt Handling Clarification

## Summary

This document clarifies how natural language prompts are processed in the SkyMarshal multi-round orchestration system.

## Key Principles

### 1. Orchestrator is a Pure Coordinator

The orchestrator:

- ✅ Receives natural language prompts from users
- ✅ Adds phase-specific instructions to guide agents
- ✅ Passes augmented prompts to agents
- ✅ Collates agent responses
- ✅ Coordinates three-phase execution

The orchestrator does NOT:

- ❌ Parse or extract fields from prompts
- ❌ Validate flight numbers or dates
- ❌ Perform database lookups
- ❌ Transform or normalize data

### 2. Agents Handle All Data Processing

Each agent autonomously:

- Receives the user's natural language prompt with added instructions
- Uses LangChain structured output to extract data from the user's prompt
- Queries DynamoDB using extracted information
- Generates recommendations

### 3. LangChain Structured Output for Extraction

**No custom extraction tools or parsing methods are needed.**

Agents use LangChain's `with_structured_output()` method with Pydantic models to extract structured data from natural language prompts.

**Reference**: [LangChain Structured Output Documentation](https://docs.langchain.com/oss/python/langchain/structured-output)

## Implementation Pattern

### Orchestrator Instruction Augmentation

The orchestrator adds phase-specific instructions to guide agents without parsing the user's content:

**Phase 1 - Initial Recommendations:**

```python
augmented_prompt = f"""{user_prompt}

Please analyze this disruption and provide your initial recommendation from your domain perspective.
Extract the flight information, query relevant data, and generate your assessment."""

# Send to all agents
```

**Phase 2 - Revision Round:**

```python
augmented_prompt = f"""{user_prompt}

Other agents have provided the following recommendations:
{json.dumps(initial_collation, indent=2)}

Please review these recommendations and determine whether to revise your initial recommendation.
Consider cross-functional impacts and update your assessment if warranted."""

# Send to all agents
```

**Key Points:**

- User's original prompt is preserved exactly
- Instructions are appended, not inserted
- No parsing or extraction by orchestrator
- Agents receive context about what phase they're in

### Step 1: Define Pydantic Model

```python
from pydantic import BaseModel, Field

class FlightInfo(BaseModel):
    """Structured flight information extracted from natural language."""
    flight_number: str = Field(description="Flight number (e.g., EY123)")
    date: str = Field(description="Flight date in ISO format (YYYY-MM-DD)")
    disruption_event: str = Field(description="Description of the disruption")
```

### Step 2: Use Structured Output

```python
from langchain_aws import ChatBedrock

# Create LLM with structured output
llm = ChatBedrock(model_id="anthropic.claude-sonnet-4-20250514-v1:0")
structured_llm = llm.with_structured_output(FlightInfo)

# Extract data from natural language
user_prompt = "Flight EY123 on January 20th had a mechanical failure"
flight_info = structured_llm.invoke(user_prompt)

# Result: FlightInfo(
#   flight_number="EY123",
#   date="2025-01-20",
#   disruption_event="mechanical failure"
# )
```

### Step 3: Use Extracted Data

```python
# Query DynamoDB using extracted information
flight = query_flight(
    flight_number=flight_info.flight_number,
    date=flight_info.date
)

# Generate recommendation based on data
recommendation = generate_recommendation(flight, flight_info.disruption_event)
```

## Data Flow

```
User Input (Natural Language)
  "Flight EY123 on January 20th had a mechanical failure"
         ↓
Orchestrator (Adds Instructions)
  "Flight EY123 on January 20th had a mechanical failure

   Please analyze this disruption and provide your initial
   recommendation from your domain perspective."
         ↓
Agent Receives Augmented Prompt
         ↓
LangChain Structured Output
  llm.with_structured_output(FlightInfo)
         ↓
Pydantic Model Instance
  FlightInfo(
    flight_number="EY123",
    date="2025-01-20",
    disruption_event="mechanical failure"
  )
         ↓
DynamoDB Query Tools
  query_flight(flight_number="EY123", date="2025-01-20")
         ↓
Agent Recommendation
```

## Benefits of This Approach

1. **Simplicity**: No custom parsing logic needed
2. **Type Safety**: Pydantic models provide validation
3. **Flexibility**: LLMs handle diverse natural language phrasings
4. **Maintainability**: Clear separation of concerns
5. **Testability**: Easy to test with different prompt variations
6. **LangGraph Integration**: Agents can autonomously use tools during reasoning

## What Changed

### Before (Incorrect Approach)

- Orchestrator had extraction tools
- Custom parsing functions for dates
- Validation logic in orchestrator
- Agents received pre-processed data

### After (Correct Approach)

- Orchestrator adds instructions to user prompts
- Orchestrator does NOT parse or extract data
- LangChain structured output handles extraction
- Pydantic models define data structure
- Agents process natural language autonomously

## Testing Strategy

### Unit Tests

- Verify agents use `with_structured_output()`
- Test Pydantic models extract correct data
- Verify orchestrator has no parsing logic
- Verify orchestrator adds appropriate instructions
- Verify user prompt content is preserved in augmented prompt

### Integration Tests

- Test with diverse natural language phrasings
- Verify consistent extraction across agents
- Test date format handling (relative, named, numeric)

### Property-Based Tests

- Generate random natural language prompts
- Verify consistent structured output
- Test extraction robustness

## References

- [LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)
- [Pydantic Models](https://docs.pydantic.dev/latest/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
