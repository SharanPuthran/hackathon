# Crew Compliance Agent - Priority 1 GSI Usage Guide

## Overview

The Crew Compliance Agent uses 1 Priority 1 GSI to efficiently query crew duty history for Flight Duty Period (FDP) and rest calculations. This GSI provides **50x performance improvement** over table scans and is critical for regulatory compliance validation.

## GSI Used by Crew Compliance Agent

### crew-duty-date-index (CrewRoster table)

**Purpose**: Query crew duty history for FDP (Flight Duty Period) and rest calculations

**Performance**:

- Expected Latency: 15-20ms average, 30-40ms p99
- Query Volume: 500+ queries/day (highest volume of all Priority 1 GSIs)
- Performance Improvement: 50x faster than table scan

**Use Cases**:

- Calculate cumulative Flight Duty Period (FDP) for crew members
- Verify rest period compliance between duties
- Check duty time limits (daily, weekly, monthly)
- Validate crew scheduling against regulatory requirements
- Identify crew members approaching duty limits

**Regulatory Context**:

- EASA FTL regulations require tracking of duty periods
- Maximum FDP varies by time of day and number of sectors
- Minimum rest periods required between duties
- Monthly and yearly duty limits must be enforced

---

## Query Examples

### 1. Basic Crew Duty History Query

```python
from langchain_core.tools import tool
import boto3
from database.constants import CREW_ROSTER_TABLE, CREW_DUTY_DATE_INDEX

@tool
def query_crew_duty_history(crew_id: str, start_date: str, end_date: str) -> list[dict]:
    """Query crew duty history within a date range for FDP calculations.

    Args:
        crew_id: Unique crew member identifier (e.g., CREW001)
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)

    Returns:
        List of duty records ordered by duty_date
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    crew_roster_table = dynamodb.Table(CREW_ROSTER_TABLE)

    response = crew_roster_table.query(
        IndexName=CREW_DUTY_DATE_INDEX,
        KeyConditionExpression="crew_id = :cid AND duty_date BETWEEN :start AND :end",
        ExpressionAttributeValues={
            ":cid": crew_id,
            ":start": start_date,
            ":end": end_date
        }
    )

    return response.get("Items", [])
```

### 2. Calculate Cumulative FDP

```python
@tool
def calculate_cumulative_fdp(crew_id: str, reference_date: str, lookback_days: int = 7) -> dict:
    """Calculate cumulative Flight Duty Period for a crew member.

    Args:
        crew_id: Unique crew member identifier
        reference_date: Reference date for calculation (ISO format)
        lookback_days: Number of days to look back (default: 7 for weekly FDP)

    Returns:
        Dictionary with FDP statistics and compliance status
    """
    from datetime import datetime, timedelta

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    crew_roster_table = dynamodb.Table(CREW_ROSTER_TABLE)

    # Calculate date range
    ref_date = datetime.fromisoformat(reference_date)
    start_date = (ref_date - timedelta(days=lookback_days)).isoformat()[:10]
    end_date = reference_date

    # Query duty history
    response = crew_roster_table.query(
        IndexName=CREW_DUTY_DATE_INDEX,
        KeyConditionExpression="crew_id = :cid AND duty_date BETWEEN :start AND :end",
        ExpressionAttributeValues={
            ":cid": crew_id,
            ":start": start_date,
            ":end": end_date
        }
    )

    duties = response.get("Items", [])

    # Calculate cumulative FDP
    total_fdp_minutes = 0
    duty_count = len(duties)

    for duty in duties:
        # Assuming duty records have duty_start and duty_end times
        duty_start = datetime.fromisoformat(duty.get("duty_start", ""))
        duty_end = datetime.fromisoformat(duty.get("duty_end", ""))
        fdp_minutes = (duty_end - duty_start).total_seconds() / 60
        total_fdp_minutes += fdp_minutes

    total_fdp_hours = total_fdp_minutes / 60

    # EASA FTL limits (simplified)
    weekly_limit_hours = 60
    compliance_status = "compliant" if total_fdp_hours <= weekly_limit_hours else "exceeded"

    return {
        "crew_id": crew_id,
        "period_start": start_date,
        "period_end": end_date,
        "duty_count": duty_count,
        "total_fdp_hours": round(total_fdp_hours, 2),
        "weekly_limit_hours": weekly_limit_hours,
        "remaining_hours": round(weekly_limit_hours - total_fdp_hours, 2),
        "compliance_status": compliance_status,
        "duties": duties
    }
```

### 3. Verify Rest Period Compliance

```python
@tool
def verify_rest_period_compliance(crew_id: str, proposed_duty_start: str) -> dict:
    """Verify crew member has adequate rest before proposed duty.

    Args:
        crew_id: Unique crew member identifier
        proposed_duty_start: Proposed duty start time (ISO format with time)

    Returns:
        Dictionary with rest period analysis and compliance status
    """
    from datetime import datetime, timedelta

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    crew_roster_table = dynamodb.Table(CREW_ROSTER_TABLE)

    # Parse proposed duty start
    proposed_start = datetime.fromisoformat(proposed_duty_start)

    # Query recent duties (last 3 days)
    lookback_date = (proposed_start - timedelta(days=3)).isoformat()[:10]
    proposed_date = proposed_start.isoformat()[:10]

    response = crew_roster_table.query(
        IndexName=CREW_DUTY_DATE_INDEX,
        KeyConditionExpression="crew_id = :cid AND duty_date BETWEEN :start AND :end",
        ExpressionAttributeValues={
            ":cid": crew_id,
            ":start": lookback_date,
            ":end": proposed_date
        }
    )

    duties = response.get("Items", [])

    if not duties:
        return {
            "crew_id": crew_id,
            "compliance_status": "compliant",
            "message": "No recent duties found",
            "rest_hours": None,
            "minimum_rest_hours": 12
        }

    # Find most recent duty
    duties_sorted = sorted(duties, key=lambda d: d.get("duty_end", ""), reverse=True)
    last_duty = duties_sorted[0]
    last_duty_end = datetime.fromisoformat(last_duty.get("duty_end", ""))

    # Calculate rest period
    rest_period = proposed_start - last_duty_end
    rest_hours = rest_period.total_seconds() / 3600

    # EASA FTL minimum rest (simplified)
    minimum_rest_hours = 12
    compliance_status = "compliant" if rest_hours >= minimum_rest_hours else "insufficient_rest"

    return {
        "crew_id": crew_id,
        "last_duty_end": last_duty_end.isoformat(),
        "proposed_duty_start": proposed_duty_start,
        "rest_hours": round(rest_hours, 2),
        "minimum_rest_hours": minimum_rest_hours,
        "compliance_status": compliance_status,
        "message": f"Rest period: {rest_hours:.1f}h (minimum: {minimum_rest_hours}h)"
    }
```

### 4. Check Monthly Duty Limits

```python
@tool
def check_monthly_duty_limits(crew_id: str, year: int, month: int) -> dict:
    """Check crew member's monthly duty limits.

    Args:
        crew_id: Unique crew member identifier
        year: Year (e.g., 2026)
        month: Month (1-12)

    Returns:
        Dictionary with monthly duty statistics and compliance status
    """
    from datetime import datetime
    from calendar import monthrange

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    crew_roster_table = dynamodb.Table(CREW_ROSTER_TABLE)

    # Calculate month date range
    start_date = f"{year}-{month:02d}-01"
    last_day = monthrange(year, month)[1]
    end_date = f"{year}-{month:02d}-{last_day}"

    # Query all duties in the month
    response = crew_roster_table.query(
        IndexName=CREW_DUTY_DATE_INDEX,
        KeyConditionExpression="crew_id = :cid AND duty_date BETWEEN :start AND :end",
        ExpressionAttributeValues={
            ":cid": crew_id,
            ":start": start_date,
            ":end": end_date
        }
    )

    duties = response.get("Items", [])

    # Calculate monthly totals
    total_duty_hours = 0
    total_flight_hours = 0
    duty_days = len(duties)

    for duty in duties:
        duty_start = datetime.fromisoformat(duty.get("duty_start", ""))
        duty_end = datetime.fromisoformat(duty.get("duty_end", ""))
        duty_hours = (duty_end - duty_start).total_seconds() / 3600
        total_duty_hours += duty_hours

        # Assuming flight_hours is stored in duty record
        total_flight_hours += duty.get("flight_hours", 0)

    # EASA FTL monthly limits (simplified)
    monthly_duty_limit = 190  # hours
    monthly_flight_limit = 100  # hours

    duty_compliance = "compliant" if total_duty_hours <= monthly_duty_limit else "exceeded"
    flight_compliance = "compliant" if total_flight_hours <= monthly_flight_limit else "exceeded"

    return {
        "crew_id": crew_id,
        "year": year,
        "month": month,
        "duty_days": duty_days,
        "total_duty_hours": round(total_duty_hours, 2),
        "monthly_duty_limit": monthly_duty_limit,
        "duty_compliance": duty_compliance,
        "total_flight_hours": round(total_flight_hours, 2),
        "monthly_flight_limit": monthly_flight_limit,
        "flight_compliance": flight_compliance,
        "overall_compliance": "compliant" if duty_compliance == "compliant" and flight_compliance == "compliant" else "exceeded"
    }
```

### 5. Identify Crew Approaching Limits

```python
@tool
def identify_crew_approaching_limits(crew_id: str, reference_date: str) -> dict:
    """Identify if crew member is approaching duty limits.

    Args:
        crew_id: Unique crew member identifier
        reference_date: Reference date for calculation (ISO format)

    Returns:
        Dictionary with warnings for approaching limits
    """
    from datetime import datetime, timedelta

    # Calculate weekly FDP
    weekly_fdp = calculate_cumulative_fdp(crew_id, reference_date, lookback_days=7)

    # Calculate monthly limits
    ref_date = datetime.fromisoformat(reference_date)
    monthly_limits = check_monthly_duty_limits(crew_id, ref_date.year, ref_date.month)

    warnings = []

    # Check weekly FDP (warn at 80% of limit)
    weekly_threshold = 0.8 * weekly_fdp["weekly_limit_hours"]
    if weekly_fdp["total_fdp_hours"] >= weekly_threshold:
        warnings.append({
            "type": "weekly_fdp",
            "severity": "warning",
            "message": f"Crew approaching weekly FDP limit: {weekly_fdp['total_fdp_hours']:.1f}h / {weekly_fdp['weekly_limit_hours']}h"
        })

    # Check monthly duty hours (warn at 80% of limit)
    monthly_duty_threshold = 0.8 * monthly_limits["monthly_duty_limit"]
    if monthly_limits["total_duty_hours"] >= monthly_duty_threshold:
        warnings.append({
            "type": "monthly_duty",
            "severity": "warning",
            "message": f"Crew approaching monthly duty limit: {monthly_limits['total_duty_hours']:.1f}h / {monthly_limits['monthly_duty_limit']}h"
        })

    # Check monthly flight hours (warn at 80% of limit)
    monthly_flight_threshold = 0.8 * monthly_limits["monthly_flight_limit"]
    if monthly_limits["total_flight_hours"] >= monthly_flight_threshold:
        warnings.append({
            "type": "monthly_flight",
            "severity": "warning",
            "message": f"Crew approaching monthly flight limit: {monthly_limits['total_flight_hours']:.1f}h / {monthly_limits['monthly_flight_limit']}h"
        })

    return {
        "crew_id": crew_id,
        "reference_date": reference_date,
        "warnings": warnings,
        "warning_count": len(warnings),
        "status": "approaching_limits" if warnings else "within_limits",
        "weekly_fdp": weekly_fdp,
        "monthly_limits": monthly_limits
    }
```

---

## Performance Monitoring

### Expected Metrics

| Metric            | Target      | Description                       |
| ----------------- | ----------- | --------------------------------- |
| Average Latency   | 15-20ms     | Typical query response time       |
| P99 Latency       | 30-40ms     | 99th percentile response time     |
| Query Volume      | 500+/day    | Highest volume of Priority 1 GSIs |
| Performance Gain  | 50x         | Improvement over table scan       |
| Consumed Capacity | < 100 RCU/s | Read capacity units per second    |
| Throttling Events | 0           | Should not experience throttling  |

### Monitoring Queries

```python
import boto3
from datetime import datetime, timedelta

def monitor_gsi_performance():
    """Monitor crew-duty-date-index GSI performance."""
    cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

    # Get consumed read capacity
    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/DynamoDB",
        MetricName="ConsumedReadCapacityUnits",
        Dimensions=[
            {"Name": "TableName", "Value": "CrewRoster"},
            {"Name": "GlobalSecondaryIndexName", "Value": "crew-duty-date-index"}
        ],
        StartTime=datetime.now() - timedelta(hours=1),
        EndTime=datetime.now(),
        Period=300,
        Statistics=["Average", "Maximum", "Sum"]
    )

    return {
        "gsi_name": "crew-duty-date-index",
        "table_name": "CrewRoster",
        "metrics": response["Datapoints"]
    }
```

---

## Integration with Agent Code

### Complete Agent Tool Example

```python
# In src/agents/crew_compliance/agent.py

import boto3
from langchain_core.tools import tool
from database.constants import (
    CREW_ROSTER_TABLE,
    CREW_MEMBERS_TABLE,
    CREW_DUTY_DATE_INDEX
)

# Define all tools using @tool decorator
@tool
def query_crew_duty_history(crew_id: str, start_date: str, end_date: str) -> list[dict]:
    """Query crew duty history within a date range for FDP calculations."""
    # Implementation as shown above
    pass

@tool
def calculate_cumulative_fdp(crew_id: str, reference_date: str, lookback_days: int = 7) -> dict:
    """Calculate cumulative Flight Duty Period for a crew member."""
    # Implementation as shown above
    pass

@tool
def verify_rest_period_compliance(crew_id: str, proposed_duty_start: str) -> dict:
    """Verify crew member has adequate rest before proposed duty."""
    # Implementation as shown above
    pass

@tool
def check_monthly_duty_limits(crew_id: str, year: int, month: int) -> dict:
    """Check crew member's monthly duty limits."""
    # Implementation as shown above
    pass

@tool
def identify_crew_approaching_limits(crew_id: str, reference_date: str) -> dict:
    """Identify if crew member is approaching duty limits."""
    # Implementation as shown above
    pass

# Agent implementation
async def analyze_crew_compliance(payload: dict, llm: Any, mcp_tools: list):
    """Analyze crew compliance for a disruption."""

    # Tools available to the agent
    tools = [
        query_crew_duty_history,
        calculate_cumulative_fdp,
        verify_rest_period_compliance,
        check_monthly_duty_limits,
        identify_crew_approaching_limits
    ]

    # Agent uses tools autonomously during reasoning
    # ...
```

---

## Best Practices

### 1. Always Query with Date Range

```python
# Good: Use date range for efficient queries
response = crew_roster_table.query(
    IndexName=CREW_DUTY_DATE_INDEX,
    KeyConditionExpression="crew_id = :cid AND duty_date BETWEEN :start AND :end",
    ExpressionAttributeValues={
        ":cid": crew_id,
        ":start": start_date,
        ":end": end_date
    }
)

# Avoid: Querying all duties and filtering in code
response = crew_roster_table.query(
    IndexName=CREW_DUTY_DATE_INDEX,
    KeyConditionExpression="crew_id = :cid",
    ExpressionAttributeValues={":cid": crew_id}
)
filtered = [d for d in response["Items"] if start_date <= d["duty_date"] <= end_date]
```

### 2. Use Appropriate Lookback Periods

```python
# Weekly FDP: 7 days
weekly_fdp = calculate_cumulative_fdp(crew_id, reference_date, lookback_days=7)

# Rest period check: 3 days
rest_check = verify_rest_period_compliance(crew_id, proposed_duty_start)

# Monthly limits: Full calendar month
monthly_limits = check_monthly_duty_limits(crew_id, year, month)
```

### 3. Handle Pagination for Long Histories

```python
@tool
def query_crew_duty_history_paginated(crew_id: str, start_date: str, end_date: str) -> list[dict]:
    """Query crew duty history with pagination support."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    crew_roster_table = dynamodb.Table(CREW_ROSTER_TABLE)

    all_duties = []
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            response = crew_roster_table.query(
                IndexName=CREW_DUTY_DATE_INDEX,
                KeyConditionExpression="crew_id = :cid AND duty_date BETWEEN :start AND :end",
                ExpressionAttributeValues={
                    ":cid": crew_id,
                    ":start": start_date,
                    ":end": end_date
                },
                ExclusiveStartKey=last_evaluated_key
            )
        else:
            response = crew_roster_table.query(
                IndexName=CREW_DUTY_DATE_INDEX,
                KeyConditionExpression="crew_id = :cid AND duty_date BETWEEN :start AND :end",
                ExpressionAttributeValues={
                    ":cid": crew_id,
                    ":start": start_date,
                    ":end": end_date
                }
            )

        all_duties.extend(response.get("Items", []))
        last_evaluated_key = response.get("LastEvaluatedKey")

        if not last_evaluated_key:
            break

    return all_duties
```

### 4. Cache Frequently Accessed Data

```python
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=100)
def get_crew_duty_history_cached(crew_id: str, start_date: str, end_date: str) -> tuple:
    """Cached version of crew duty history query."""
    duties = query_crew_duty_history(crew_id, start_date, end_date)
    return tuple(duties)  # Convert to tuple for caching
```

---

## Regulatory Compliance

### EASA FTL Regulations (Simplified)

The crew-duty-date-index GSI enables efficient validation of:

1. **Flight Duty Period (FDP) Limits**:
   - Maximum FDP varies by time of day (13-14 hours)
   - Weekly FDP limit: 60 hours
   - Query pattern: 7-day lookback from reference date

2. **Rest Period Requirements**:
   - Minimum rest: 12 hours (can be reduced to 10 hours with compensation)
   - Query pattern: Find last duty end time, calculate rest period

3. **Monthly Limits**:
   - Maximum duty hours: 190 hours/month
   - Maximum flight hours: 100 hours/month
   - Query pattern: Full calendar month

4. **Yearly Limits**:
   - Maximum duty hours: 2000 hours/year
   - Maximum flight hours: 900 hours/year
   - Query pattern: 12-month rolling period

---

## Troubleshooting

### GSI Not Found Error

```
ClientError: An error occurred (ValidationException) when calling the Query operation:
The table does not have the specified index: crew-duty-date-index
```

**Solution**: Create the Priority 1 GSI:

```bash
cd scripts
python3 create_priority1_gsis.py --table CrewRoster
python3 create_priority1_gsis.py --check-status
```

### High Query Volume

If experiencing high query volume (>1000/day):

1. Implement caching for frequently accessed crew histories
2. Batch queries where possible
3. Consider increasing GSI provisioned capacity
4. Monitor consumed capacity in CloudWatch

### Slow Queries

If queries exceed 50ms:

1. Verify GSI is ACTIVE: `python3 create_priority1_gsis.py --check-status`
2. Check for throttling events in CloudWatch
3. Ensure date range is reasonable (avoid querying years of data)
4. Use pagination for large result sets

---

## Related Documentation

- [Priority 1 GSIs Overview](../../../scripts/PRIORITY1_GSIS_README.md)
- [Database Constants](../src/database/constants.py)
- [Structured Output Usage](./STRUCTURED_OUTPUT_USAGE.md)
- [Crew Compliance Agent Implementation](../src/agents/crew_compliance/agent.py)
- [EASA FTL Regulations](https://www.easa.europa.eu/en/document-library/regulations/commission-regulation-eu-no-8302014)
