# Date Parsing and Natural Language Processing Guide

## Overview

SkyMarshal agents use **LangChain structured output** to extract flight information, including dates, from natural language prompts. This guide explains how date parsing works and why we don't use custom parsing functions.

## Key Principle: No Custom Parsing

❌ **We do NOT use:**

- Custom date parsing functions
- Regular expressions for date extraction
- Manual format conversion logic
- String manipulation for date parsing

✅ **We DO use:**

- LangChain's `with_structured_output()` method
- Pydantic models for data structure definition
- LLM capabilities for natural language understanding
- Type-safe data extraction

## How It Works

### 1. Define Pydantic Model

```python
from pydantic import BaseModel, Field

class FlightInfo(BaseModel):
    """Structured flight information extracted from natural language."""
    flight_number: str = Field(description="Flight number (e.g., EY123)")
    date: str = Field(description="Flight date in ISO format (YYYY-MM-DD)")
    disruption_event: str = Field(description="Description of the disruption")
```

### 2. Use LangChain Structured Output

```python
from langchain_aws import ChatBedrock

# Create LLM with structured output capability
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

### 3. Use Extracted Data

```python
# Query DynamoDB using extracted information
flight = query_flight(
    flight_number=flight_info.flight_number,
    date=flight_info.date
)
```

## Supported Date Formats

LangChain structured output handles all common date formats automatically:

### Numeric Formats

- `dd/mm/yyyy` → "20/01/2026"
- `dd-mm-yy` → "20-01-26"
- `yyyy-mm-dd` → "2026-01-20"
- `mm/dd/yyyy` → "01/20/2026"

### Named Formats

- `dd Mon` → "20 Jan"
- `dd Month` → "20th January"
- `Month dd, yyyy` → "January 20th, 2026"

### Relative Dates

- `yesterday` → Previous day
- `today` → Current day
- `tomorrow` → Next day

**Note**: When numeric format is ambiguous, European format (dd/mm/yyyy) is assumed.

## Date/Time Utility Tool

The `get_current_datetime_tool()` provides the current UTC datetime for resolving relative dates:

```python
from utils.datetime_tool import get_current_datetime_tool

# This tool is available to agents
tools = [get_current_datetime_tool, ...]

# Agents can use it to resolve relative dates
# Example: "yesterday" needs current date to calculate
```

**Important**: This tool does NOT parse dates. It only provides the current datetime as a reference point. All date parsing is handled by LangChain structured output.

## Benefits of This Approach

### 1. Simplicity

- No complex parsing logic to maintain
- No regex patterns to debug
- No edge cases to handle manually

### 2. Flexibility

- Handles diverse natural language phrasings
- Adapts to different date formats automatically
- Understands context and ambiguity

### 3. Type Safety

- Pydantic models provide validation
- Type hints catch errors at development time
- Structured data throughout the pipeline

### 4. Maintainability

- Clear separation of concerns
- LangChain handles parsing complexity
- Easy to test with different prompt variations

### 5. Reliability

- LLM-powered extraction is robust
- Handles typos and variations gracefully
- Consistent results across different phrasings

## Example Use Cases

### Example 1: Numeric Date

```python
prompt = "Flight EY123 on 20/01/2026 was delayed"
flight_info = structured_llm.invoke(prompt)
# Result: FlightInfo(flight_number="EY123", date="2026-01-20", ...)
```

### Example 2: Named Date

```python
prompt = "EY456 on January 20th had a mechanical issue"
flight_info = structured_llm.invoke(prompt)
# Result: FlightInfo(flight_number="EY456", date="2026-01-20", ...)
```

### Example 3: Relative Date

```python
prompt = "Flight EY789 yesterday experienced a delay"
flight_info = structured_llm.invoke(prompt)
# Result: FlightInfo(flight_number="EY789", date="2026-01-30", ...)
# (Assuming today is 2026-01-31)
```

### Example 4: Multiple Formats in Same Prompt

```python
prompt = "EY123 on 20 Jan and EY456 on January 21st both delayed"
# LangChain can extract multiple dates and associate them correctly
```

## Testing Strategy

### Unit Tests

Test that agents use structured output correctly:

```python
def test_agent_uses_structured_output():
    """Verify agent uses LangChain structured output for extraction."""
    # Verify agent code uses with_structured_output()
    # Verify no custom parsing functions exist
    # Verify Pydantic models are defined
```

### Integration Tests

Test with diverse natural language inputs:

```python
@pytest.mark.parametrize("prompt,expected_date", [
    ("Flight EY123 on 20/01/2026", "2026-01-20"),
    ("EY123 on January 20th", "2026-01-20"),
    ("EY123 yesterday", "2026-01-30"),  # Assuming today is 2026-01-31
])
def test_date_extraction(prompt, expected_date):
    """Test date extraction from various formats."""
    flight_info = structured_llm.invoke(prompt)
    assert flight_info.date == expected_date
```

### Property-Based Tests

Test consistency across phrasings:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=10))
def test_extraction_consistency(prompt):
    """Verify consistent extraction across different phrasings."""
    # Generate prompts with same flight info in different ways
    # Verify extracted data is consistent
```

## Common Mistakes to Avoid

### ❌ Don't Create Custom Parsing Functions

```python
# BAD - Don't do this!
def parse_date(date_string: str) -> str:
    """Custom date parsing function."""
    if "/" in date_string:
        # Manual parsing logic...
        pass
    elif "-" in date_string:
        # More manual parsing...
        pass
    # This is unnecessary and error-prone!
```

### ❌ Don't Use Regex for Date Extraction

```python
# BAD - Don't do this!
import re

date_pattern = r"\d{2}/\d{2}/\d{4}"
match = re.search(date_pattern, prompt)
# LangChain handles this better!
```

### ❌ Don't Pre-Process Prompts in Orchestrator

```python
# BAD - Don't do this!
def orchestrator(prompt):
    # Extract date from prompt
    date = extract_date(prompt)  # NO!
    # Pass to agents
    # Agents should extract dates themselves!
```

### ✅ Do Use Structured Output

```python
# GOOD - Do this!
from pydantic import BaseModel
from langchain_aws import ChatBedrock

class FlightInfo(BaseModel):
    flight_number: str
    date: str
    disruption_event: str

llm = ChatBedrock(model_id="...")
structured_llm = llm.with_structured_output(FlightInfo)
flight_info = structured_llm.invoke(prompt)
```

## Architecture Diagram

```
User Input (Natural Language)
  "Flight EY123 on January 20th had a mechanical failure"
         ↓
Orchestrator (Adds Instructions Only)
  - Does NOT parse or extract
  - Adds phase-specific instructions
  - Passes augmented prompt to agents
         ↓
Agent Receives Prompt
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
DynamoDB Query
  query_flight(flight_number="EY123", date="2025-01-20")
         ↓
Agent Analysis & Recommendation
```

## References

- [LangChain Structured Output Documentation](https://docs.langchain.com/oss/python/langchain/structured-output)
- [Pydantic Models Documentation](https://docs.pydantic.dev/latest/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [SkyMarshal Design Document](.kiro/specs/skymarshal-multi-round-orchestration/design.md)
- [Prompt Handling Clarification](.kiro/specs/skymarshal-multi-round-orchestration/PROMPT_HANDLING_CLARIFICATION.md)

## Summary

**Key Takeaway**: Date parsing in SkyMarshal is handled entirely by LangChain structured output using Pydantic models. No custom parsing functions are needed or should be created. The `get_current_datetime_tool()` only provides the current datetime for reference - it does NOT parse dates.

This approach provides simplicity, flexibility, type safety, and reliability while reducing maintenance burden and potential bugs.
