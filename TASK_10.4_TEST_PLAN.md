# Task 10.4 Test Plan: Natural Language Prompt Testing

## Overview

Task 10.4 requires testing the Crew Compliance agent with sample natural language prompts to verify:

1. Various prompt phrasings work correctly
2. Different date formats are handled properly
3. Error cases are handled gracefully

## Prerequisites

- AWS credentials configured
- DynamoDB tables deployed with test data
- GSIs created and active
- Agent deployed or running locally

## Test Scenarios

### Scenario 1: Standard Prompt Formats

#### Test 1.1: Full Date Format

```
Prompt: "Flight EY123 on January 20th, 2026 had a mechanical failure"
Expected:
- flight_number: "EY123"
- date: "2026-01-20"
- disruption_event: "mechanical failure"
```

#### Test 1.2: Short Date Format

```
Prompt: "Flight EY456 on 20/01/2026 was delayed due to weather"
Expected:
- flight_number: "EY456"
- date: "2026-01-20"
- disruption_event: "delayed due to weather"
```

#### Test 1.3: ISO Date Format

```
Prompt: "Flight EY789 on 2026-01-20 needs crew assessment for 2-hour delay"
Expected:
- flight_number: "EY789"
- date: "2026-01-20"
- disruption_event: "2-hour delay"
```

### Scenario 2: Relative Date Formats

#### Test 2.1: Yesterday

```
Prompt: "Flight EY123 yesterday had a mechanical issue"
Expected:
- flight_number: "EY123"
- date: <yesterday's date in ISO format>
- disruption_event: "mechanical issue"
```

#### Test 2.2: Today

```
Prompt: "Flight EY456 today is delayed 3 hours"
Expected:
- flight_number: "EY456"
- date: <today's date in ISO format>
- disruption_event: "delayed 3 hours"
```

#### Test 2.3: Tomorrow

```
Prompt: "Flight EY789 tomorrow may need crew replacement"
Expected:
- flight_number: "EY789"
- date: <tomorrow's date in ISO format>
- disruption_event: "may need crew replacement"
```

### Scenario 3: Named Date Formats

#### Test 3.1: Day and Month

```
Prompt: "Flight EY123 on 20 Jan had crew issues"
Expected:
- flight_number: "EY123"
- date: "2026-01-20"
- disruption_event: "crew issues"
```

#### Test 3.2: Full Month Name

```
Prompt: "Flight EY456 on January 20th needs analysis"
Expected:
- flight_number: "EY456"
- date: "2026-01-20"
- disruption_event: "needs analysis"
```

### Scenario 4: Various Prompt Phrasings

#### Test 4.1: Formal Phrasing

```
Prompt: "Please analyze Flight EY123 scheduled for January 20th, 2026, which experienced a mechanical failure requiring crew assessment."
Expected:
- flight_number: "EY123"
- date: "2026-01-20"
- disruption_event: "mechanical failure requiring crew assessment"
```

#### Test 4.2: Casual Phrasing

```
Prompt: "EY456 on Jan 20 - delayed 2 hours, check crew"
Expected:
- flight_number: "EY456"
- date: "2026-01-20"
- disruption_event: "delayed 2 hours"
```

#### Test 4.3: Question Format

```
Prompt: "Can you check if the crew for Flight EY789 on 20/01/2026 can handle a 3-hour delay?"
Expected:
- flight_number: "EY789"
- date: "2026-01-20"
- disruption_event: "3-hour delay"
```

### Scenario 5: Error Cases

#### Test 5.1: Missing Flight Number

```
Prompt: "Flight on January 20th had a delay"
Expected:
- Error response indicating missing flight number
- Clear error message requesting flight number
```

#### Test 5.2: Invalid Flight Number Format

```
Prompt: "Flight ABC123 on January 20th had a delay"
Expected:
- Error response indicating invalid flight number format
- Message specifying correct format (EY followed by 3-4 digits)
```

#### Test 5.3: Missing Date

```
Prompt: "Flight EY123 had a mechanical failure"
Expected:
- Error response indicating missing date
- Clear error message requesting date
```

#### Test 5.4: Ambiguous Date

```
Prompt: "Flight EY123 on 01/02/2026 had a delay"
Expected:
- Date parsed as 1st February 2026 (European format assumed)
- Or error requesting clarification
```

#### Test 5.5: Flight Not Found

```
Prompt: "Flight EY999 on January 20th, 2026 had a delay"
Expected:
- Error response indicating flight not found
- Message with flight number and date attempted
```

#### Test 5.6: No Crew Assigned

```
Prompt: "Flight EY123 on January 20th, 2026 had a delay"
(Assuming flight exists but has no crew roster)
Expected:
- Error response indicating no crew assigned
- Clear message about missing crew data
```

### Scenario 6: Complex Disruption Descriptions

#### Test 6.1: Multiple Issues

```
Prompt: "Flight EY123 on January 20th had a mechanical failure and weather delay, total 4 hours"
Expected:
- flight_number: "EY123"
- date: "2026-01-20"
- disruption_event: "mechanical failure and weather delay, total 4 hours"
```

#### Test 6.2: Technical Details

```
Prompt: "Flight EY456 on 20/01/2026 - APU failure, estimated 2-hour repair time, crew FDP impact assessment needed"
Expected:
- flight_number: "EY456"
- date: "2026-01-20"
- disruption_event: "APU failure, estimated 2-hour repair time, crew FDP impact assessment needed"
```

## Test Execution

### Manual Testing

1. **Setup Environment**

   ```bash
   cd skymarshal_agents_new/skymarshal
   source .venv/bin/activate
   export AWS_PROFILE=<your-profile>
   export AWS_REGION=us-east-1
   ```

2. **Run Agent Locally**

   ```bash
   uv run agentcore dev
   ```

3. **Test Each Scenario**

   ```bash
   uv run agentcore invoke --dev "<test prompt>"
   ```

4. **Record Results**
   - Document extracted flight info
   - Verify database queries executed
   - Check error handling
   - Validate response format

### Automated Testing (Future)

Create integration test file: `test/integration/test_crew_compliance_prompts.py`

```python
import pytest
from agents.crew_compliance.agent import analyze_crew_compliance
from model.load import load_model

@pytest.mark.integration
@pytest.mark.asyncio
async def test_standard_prompt_format():
    """Test agent with standard prompt format."""
    llm = load_model("crew_compliance")

    payload = {
        "user_prompt": "Flight EY123 on January 20th, 2026 had a mechanical failure",
        "phase": "initial"
    }

    result = await analyze_crew_compliance(payload, llm, [])

    assert result["status"] == "success"
    assert result["extracted_flight_info"]["flight_number"] == "EY123"
    assert result["extracted_flight_info"]["date"] == "2026-01-20"
    assert "mechanical failure" in result["extracted_flight_info"]["disruption_event"]

# Add more tests for each scenario...
```

## Success Criteria

- ✅ All standard prompt formats extract correct flight info
- ✅ All relative date formats resolve to correct dates
- ✅ All named date formats parse correctly
- ✅ Various prompt phrasings work correctly
- ✅ Error cases return clear error messages
- ✅ Complex disruption descriptions are preserved
- ✅ Agent queries DynamoDB successfully
- ✅ Agent returns structured response

## Notes

- This testing requires AWS credentials and deployed infrastructure
- Test data must exist in DynamoDB for successful queries
- Some tests may need to be adjusted based on current date
- Integration tests should be run in a test environment, not production

## Next Steps

1. Deploy test environment with sample data
2. Execute manual tests for each scenario
3. Document results and any issues found
4. Create automated integration tests
5. Add to CI/CD pipeline for regression testing
