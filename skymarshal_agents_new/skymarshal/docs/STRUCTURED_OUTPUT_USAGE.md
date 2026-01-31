# Structured Output Usage Guide

## Overview

This guide demonstrates how to use LangChain's `with_structured_output()` method with the `FlightInfo` Pydantic model to extract structured flight information from natural language prompts.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Example Prompts and Outputs](#example-prompts-and-outputs)
- [Error Handling](#error-handling)
- [Integration with Agents](#integration-with-agents)
- [Best Practices](#best-practices)

---

## Basic Usage

### Step 1: Import Required Modules

```python
from langchain_aws import ChatBedrock
from agents.schemas import FlightInfo
```

### Step 2: Initialize the LLM

```python
# Initialize the Bedrock model
llm = ChatBedrock(
    model_id="anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="us-east-1"
)
```

### Step 3: Create Structured Output LLM

```python
# Wrap the LLM with structured output capability
structured_llm = llm.with_structured_output(FlightInfo)
```

### Step 4: Extract Flight Information

```python
# User's natural language prompt
user_prompt = "Flight EY123 on January 20th had a mechanical failure"

# Extract structured data
flight_info = structured_llm.invoke(user_prompt)

# Access extracted fields
print(f"Flight Number: {flight_info.flight_number}")  # EY123
print(f"Date: {flight_info.date}")                    # 2026-01-20
print(f"Event: {flight_info.disruption_event}")       # mechanical failure
```

---

## Example Prompts and Outputs

### Example 1: Numeric Date Format

**Input Prompt:**

```
"Flight EY456 on 15/03/2026 was delayed due to weather"
```

**Expected Output:**

```python
FlightInfo(
    flight_number="EY456",
    date="2026-03-15",
    disruption_event="delayed due to weather"
)
```

### Example 2: Named Date Format

**Input Prompt:**

```
"EY789 on 20th January had a crew shortage"
```

**Expected Output:**

```python
FlightInfo(
    flight_number="EY789",
    date="2026-01-20",
    disruption_event="crew shortage"
)
```

### Example 3: Relative Date Format

**Input Prompt:**

```
"Yesterday's EY1234 flight was rerouted due to a maintenance issue"
```

**Expected Output:**

```python
FlightInfo(
    flight_number="EY1234",
    date="2026-01-30",  # Assuming today is 2026-01-31
    disruption_event="rerouted due to a maintenance issue"
)
```

### Example 4: Verbose Natural Language

**Input Prompt:**

```
"We had a problem with flight EY321 scheduled for tomorrow.
The aircraft experienced a mechanical failure during pre-flight checks."
```

**Expected Output:**

```python
FlightInfo(
    flight_number="EY321",
    date="2026-02-01",  # Assuming today is 2026-01-31
    disruption_event="mechanical failure during pre-flight checks"
)
```

### Example 5: Multiple Date Formats

**Input Prompt:**

```
"Flight EY555 on Jan 25th 2026 had a weather diversion"
```

**Expected Output:**

```python
FlightInfo(
    flight_number="EY555",
    date="2026-01-25",
    disruption_event="weather diversion"
)
```

### Example 6: Ambiguous Date (European Format Assumed)

**Input Prompt:**

```
"EY888 on 03/04/2026 was delayed"
```

**Expected Output:**

```python
FlightInfo(
    flight_number="EY888",
    date="2026-04-03",  # Interpreted as 3rd April (dd/mm/yyyy)
    disruption_event="delayed"
)
```

---

## Error Handling

### Handling Extraction Failures

When the LLM cannot extract valid flight information, you should catch and handle exceptions:

```python
from pydantic import ValidationError

def extract_flight_info_safely(user_prompt: str, llm: ChatBedrock) -> dict:
    """
    Safely extract flight information with error handling.

    Args:
        user_prompt: Natural language prompt from user
        llm: Bedrock model instance

    Returns:
        dict with either flight_info or error details
    """
    try:
        # Create structured output LLM
        structured_llm = llm.with_structured_output(FlightInfo)

        # Extract flight information
        flight_info = structured_llm.invoke(user_prompt)

        return {
            "success": True,
            "flight_info": flight_info,
            "error": None
        }

    except ValidationError as e:
        # Pydantic validation failed
        return {
            "success": False,
            "flight_info": None,
            "error": f"Validation error: {str(e)}",
            "error_type": "validation",
            "details": e.errors()
        }

    except Exception as e:
        # Other extraction errors
        return {
            "success": False,
            "flight_info": None,
            "error": f"Extraction error: {str(e)}",
            "error_type": "extraction"
        }
```

### Common Error Scenarios

#### 1. Invalid Flight Number Format

**Input Prompt:**

```
"Flight AB123 on January 20th had a delay"
```

**Error:**

```python
ValidationError: Invalid flight number format: AB123.
Expected format: EY followed by 3 or 4 digits (e.g., EY123, EY1234)
```

**Handling:**

```python
result = extract_flight_info_safely(user_prompt, llm)

if not result["success"]:
    if "flight number" in result["error"].lower():
        return {
            "status": "error",
            "message": "Invalid flight number. Please provide a flight number in format EY123 or EY1234."
        }
```

#### 2. Missing Flight Number

**Input Prompt:**

```
"A flight on January 20th had a mechanical failure"
```

**Error:**

```python
ValidationError: Field required: flight_number
```

**Handling:**

```python
result = extract_flight_info_safely(user_prompt, llm)

if not result["success"]:
    if "flight_number" in str(result.get("details", [])):
        return {
            "status": "error",
            "message": "Flight number is required. Please specify the flight number (e.g., EY123)."
        }
```

#### 3. Invalid Date Format

**Input Prompt:**

```
"Flight EY123 on someday had a delay"
```

**Error:**

```python
ValidationError: Invalid date format: someday.
Expected ISO 8601 format (YYYY-MM-DD).
```

**Handling:**

```python
result = extract_flight_info_safely(user_prompt, llm)

if not result["success"]:
    if "date" in result["error"].lower():
        return {
            "status": "error",
            "message": "Could not parse date. Please provide a valid date (e.g., January 20th, 20/01/2026, yesterday)."
        }
```

#### 4. Missing Disruption Event

**Input Prompt:**

```
"Flight EY123 on January 20th"
```

**Error:**

```python
ValidationError: Disruption event description cannot be empty.
```

**Handling:**

```python
result = extract_flight_info_safely(user_prompt, llm)

if not result["success"]:
    if "disruption" in result["error"].lower():
        return {
            "status": "error",
            "message": "Please describe the disruption event (e.g., delay, mechanical failure, weather diversion)."
        }
```

### Complete Error Handling Example

```python
async def process_user_prompt(user_prompt: str, llm: ChatBedrock) -> dict:
    """
    Process user prompt with comprehensive error handling.

    Args:
        user_prompt: Natural language prompt from user
        llm: Bedrock model instance

    Returns:
        dict with processing result
    """
    # Extract flight information
    result = extract_flight_info_safely(user_prompt, llm)

    if not result["success"]:
        # Map error types to user-friendly messages
        error_messages = {
            "flight_number": "Invalid or missing flight number. Please provide a flight number in format EY123 or EY1234.",
            "date": "Could not parse date. Please provide a valid date (e.g., January 20th, 20/01/2026, yesterday).",
            "disruption_event": "Please describe the disruption event (e.g., delay, mechanical failure, weather diversion)."
        }

        # Check which field caused the error
        error_details = result.get("details", [])
        if error_details:
            field = error_details[0].get("loc", ["unknown"])[0]
            message = error_messages.get(field, f"Validation error: {result['error']}")
        else:
            message = f"Could not extract flight information: {result['error']}"

        return {
            "status": "error",
            "message": message,
            "error_details": result
        }

    # Success - proceed with flight lookup
    flight_info = result["flight_info"]

    return {
        "status": "success",
        "flight_info": flight_info,
        "message": f"Successfully extracted flight {flight_info.flight_number} on {flight_info.date}"
    }
```

---

## Integration with Agents

### Agent Implementation Pattern

Here's how agents should integrate structured output extraction:

```python
from langchain_aws import ChatBedrock
from agents.schemas import FlightInfo, AgentResponse
from datetime import datetime, timezone

async def analyze_crew_compliance(
    payload: dict,
    llm: ChatBedrock,
    tools: list
) -> dict:
    """
    Analyze crew compliance for a disruption.

    Args:
        payload: {
            "user_prompt": str,
            "phase": "initial" | "revision",
            "other_recommendations": dict (optional)
        }
        llm: Bedrock model instance
        tools: Agent-specific DynamoDB query tools

    Returns:
        AgentResponse dict
    """
    user_prompt = payload["user_prompt"]
    phase = payload["phase"]

    try:
        # Step 1: Extract flight information using structured output
        structured_llm = llm.with_structured_output(FlightInfo)
        flight_info = structured_llm.invoke(user_prompt)

        # Step 2: Query flight data using extracted information
        # (Agent uses its own DynamoDB query tools here)
        flight_record = query_flight(
            flight_number=flight_info.flight_number,
            date=flight_info.date
        )

        if not flight_record:
            return {
                "agent_name": "crew_compliance",
                "recommendation": f"Flight {flight_info.flight_number} on {flight_info.date} not found in database.",
                "confidence": 0.0,
                "reasoning": "Cannot proceed without valid flight data.",
                "data_sources": [],
                "extracted_flight_info": flight_info.model_dump(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": "Flight not found"
            }

        # Step 3: Perform agent-specific analysis
        # (Agent logic here...)

        # Step 4: Return structured response
        return {
            "agent_name": "crew_compliance",
            "recommendation": "Flight can proceed with current crew",
            "confidence": 0.95,
            "binding_constraints": ["Crew must have 10 hours rest before next duty"],
            "reasoning": "All crew members meet regulatory requirements...",
            "data_sources": ["flights", "CrewRoster", "CrewMembers"],
            "extracted_flight_info": flight_info.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "success"
        }

    except ValidationError as e:
        # Handle extraction validation errors
        return {
            "agent_name": "crew_compliance",
            "recommendation": "Cannot analyze - invalid input",
            "confidence": 0.0,
            "reasoning": f"Failed to extract flight information: {str(e)}",
            "data_sources": [],
            "extracted_flight_info": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": f"Validation error: {str(e)}"
        }

    except Exception as e:
        # Handle other errors
        return {
            "agent_name": "crew_compliance",
            "recommendation": "Cannot analyze - system error",
            "confidence": 0.0,
            "reasoning": f"Unexpected error: {str(e)}",
            "data_sources": [],
            "extracted_flight_info": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e)
        }
```

---

## Best Practices

### 1. Always Use Error Handling

Never invoke structured output without try-except blocks:

```python
# ❌ BAD - No error handling
flight_info = structured_llm.invoke(user_prompt)

# ✅ GOOD - Proper error handling
try:
    flight_info = structured_llm.invoke(user_prompt)
except ValidationError as e:
    # Handle validation errors
    pass
except Exception as e:
    # Handle other errors
    pass
```

### 2. Provide Context for Relative Dates

When users provide relative dates (yesterday, today, tomorrow), ensure the LLM has access to current date/time:

```python
from utils.datetime_tool import get_current_datetime_tool

# Include datetime tool in agent's tool list
tools = [
    get_current_datetime_tool,
    query_flight,
    query_crew_roster
]

# The LLM can now resolve relative dates by calling the datetime tool
```

### 3. Log Extracted Information

Always log what was extracted for debugging and audit trails:

```python
import logging

logger = logging.getLogger(__name__)

try:
    flight_info = structured_llm.invoke(user_prompt)
    logger.info(
        f"Extracted flight info: {flight_info.flight_number} "
        f"on {flight_info.date} - {flight_info.disruption_event}"
    )
except Exception as e:
    logger.error(f"Failed to extract flight info: {str(e)}")
```

### 4. Include Extracted Info in Response

Always include the extracted flight information in the agent response:

```python
return {
    "agent_name": "crew_compliance",
    "recommendation": "...",
    "confidence": 0.95,
    "reasoning": "...",
    "data_sources": ["flights", "CrewRoster"],
    "extracted_flight_info": flight_info.model_dump(),  # ✅ Include this
    "timestamp": datetime.now(timezone.utc).isoformat()
}
```

### 5. Validate Before Database Queries

Use the extracted and validated FlightInfo before querying the database:

```python
# ✅ GOOD - Use validated data
flight_info = structured_llm.invoke(user_prompt)
flight_record = query_flight(
    flight_number=flight_info.flight_number,  # Already validated
    date=flight_info.date                      # Already in ISO format
)

# ❌ BAD - Parse prompt manually
flight_number = extract_flight_number_regex(user_prompt)  # Don't do this
```

### 6. Handle Ambiguous Dates Explicitly

When dates are ambiguous, document the assumption:

```python
try:
    flight_info = structured_llm.invoke(user_prompt)
    logger.info(
        f"Date '{user_prompt}' interpreted as {flight_info.date} "
        "(assuming European format dd/mm/yyyy)"
    )
except ValidationError as e:
    logger.error(f"Could not parse date: {str(e)}")
```

### 7. Test with Various Prompt Formats

Always test your agent with different prompt formats:

```python
test_prompts = [
    "Flight EY123 on January 20th had a mechanical failure",
    "EY456 yesterday was delayed due to weather",
    "Flight EY789 on 15/03/2026 had a crew shortage",
    "Tomorrow's EY321 flight needs maintenance",
    "EY555 on Jan 25th 2026 had a weather diversion"
]

for prompt in test_prompts:
    result = extract_flight_info_safely(prompt, llm)
    assert result["success"], f"Failed to extract from: {prompt}"
```

---

## Summary

- Use `llm.with_structured_output(FlightInfo)` to extract flight information from natural language
- Always wrap extraction in try-except blocks to handle validation errors
- Include extracted flight info in agent responses for audit trails
- Test with various date formats and prompt phrasings
- Log extraction results for debugging
- Let the LLM handle date parsing - don't write custom regex or parsing functions

For more information, see:

- [LangChain Structured Output Documentation](https://docs.langchain.com/oss/python/langchain/structured-output)
- [Pydantic Models Documentation](https://docs.pydantic.dev/)
- [FlightInfo Schema Definition](../src/agents/schemas.py)
