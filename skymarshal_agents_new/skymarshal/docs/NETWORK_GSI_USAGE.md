# Network Agent - Priority 1 GSI Usage Guide

## Overview

The Network Agent uses 1 Priority 1 GSI to efficiently query aircraft rotation for propagation chain analysis. This GSI provides **100x performance improvement** over table scans and is critical for understanding downstream flight impacts.

## GSI Used by Network Agent

### aircraft-rotation-index (flights table)

**Purpose**: Query complete aircraft rotation for propagation chain analysis

**Performance**:

- Expected Latency: 20-30ms average, 40-50ms p99
- Query Volume: 200+ queries/day
- Performance Improvement: 100x faster than table scan (highest improvement of Priority 1 GSIs)

**Use Cases**:

- Retrieve complete aircraft rotation schedule
- Analyze propagation chains for delayed flights
- Identify downstream flight impacts
- Calculate recovery time for aircraft swaps
- Optimize aircraft utilization during disruptions

**Business Context**:

- Aircraft rotations can span multiple days
- Delays propagate through the rotation chain
- Aircraft swaps affect multiple flights
- Recovery decisions require full rotation visibility

---

## Query Examples

### 1. Basic Aircraft Rotation Query

```python
from langchain_core.tools import tool
import boto3
from database.constants import FLIGHTS_TABLE, AIRCRAFT_ROTATION_INDEX

@tool
def query_aircraft_rotation(aircraft_registration: str, start_date: str = None, end_date: str = None) -> list[dict]:
    """Query complete aircraft rotation ordered by departure time.

    Args:
        aircraft_registration: Aircraft registration (e.g., A6-EYA)
        start_date: Optional start date filter (ISO format: YYYY-MM-DD)
        end_date: Optional end date filter (ISO format: YYYY-MM-DD)

    Returns:
        List of flights ordered by scheduled_departure
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights_table = dynamodb.Table(FLIGHTS_TABLE)

    if start_date and end_date:
        response = flights_table.query(
            IndexName=AIRCRAFT_ROTATION_INDEX,
            KeyConditionExpression="aircraft_registration = :reg AND scheduled_departure BETWEEN :start AND :end",
            ExpressionAttributeValues={
                ":reg": aircraft_registration,
                ":start": start_date,
                ":end": end_date
            }
        )
    else:
        response = flights_table.query(
            IndexName=AIRCRAFT_ROTATION_INDEX,
            KeyConditionExpression="aircraft_registration = :reg",
            ExpressionAttributeValues={":reg": aircraft_registration}
        )

    return response.get("Items", [])
```

### 2. Analyze Propagation Chain

```python
@tool
def analyze_propagation_chain(aircraft_registration: str, disrupted_flight_id: str, reference_time: str) -> dict:
    """Analyze how a disruption propagates through aircraft rotation.

    Args:
        aircraft_registration: Aircraft registration
        disrupted_flight_id: ID of the disrupted flight
        reference_time: Reference time for propagation analysis (ISO format with time)

    Returns:
        Dictionary with propagation chain analysis
    """
    from datetime import datetime, timedelta

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights_table = dynamodb.Table(FLIGHTS_TABLE)

    # Parse reference time
    ref_time = datetime.fromisoformat(reference_time)

    # Query aircraft rotation for next 48 hours
    start_date = ref_time.isoformat()[:10]
    end_date = (ref_time + timedelta(days=2)).isoformat()[:10]

    response = flights_table.query(
        IndexName=AIRCRAFT_ROTATION_INDEX,
        KeyConditionExpression="aircraft_registration = :reg AND scheduled_departure BETWEEN :start AND :end",
        ExpressionAttributeValues={
            ":reg": aircraft_registration,
            ":start": start_date,
            ":end": end_date
        }
    )

    rotation = response.get("Items", [])

    # Sort by departure time
    rotation_sorted = sorted(rotation, key=lambda f: f.get("scheduled_departure", ""))

    # Find disrupted flight index
    disrupted_index = None
    for i, flight in enumerate(rotation_sorted):
        if flight.get("flight_id") == disrupted_flight_id:
            disrupted_index = i
            break

    if disrupted_index is None:
        return {
            "error": "Disrupted flight not found in rotation",
            "aircraft_registration": aircraft_registration
        }

    # Analyze downstream impacts
    disrupted_flight = rotation_sorted[disrupted_index]
    downstream_flights = rotation_sorted[disrupted_index + 1:]

    # Calculate propagation
    propagation_chain = []
    cumulative_delay = 0

    for flight in downstream_flights:
        scheduled_dep = datetime.fromisoformat(flight.get("scheduled_departure", ""))
        scheduled_arr = datetime.fromisoformat(flight.get("scheduled_arrival", ""))

        # Calculate minimum turnaround time (e.g., 45 minutes)
        min_turnaround_minutes = 45

        # If previous flight delayed, check if turnaround is sufficient
        if cumulative_delay > 0:
            available_turnaround = (scheduled_dep - scheduled_arr).total_seconds() / 60
            if available_turnaround < min_turnaround_minutes + cumulative_delay:
                # Delay propagates
                additional_delay = (min_turnaround_minutes + cumulative_delay) - available_turnaround
                cumulative_delay += additional_delay
            else:
                # Buffer absorbs delay
                cumulative_delay = 0

        propagation_chain.append({
            "flight_id": flight.get("flight_id"),
            "flight_number": flight.get("flight_number"),
            "scheduled_departure": flight.get("scheduled_departure"),
            "scheduled_arrival": flight.get("scheduled_arrival"),
            "origin": flight.get("origin_airport_id"),
            "destination": flight.get("destination_airport_id"),
            "cumulative_delay_minutes": round(cumulative_delay, 0),
            "impact_level": "high" if cumulative_delay > 60 else "medium" if cumulative_delay > 30 else "low"
        })

    return {
        "aircraft_registration": aircraft_registration,
        "disrupted_flight": {
            "flight_id": disrupted_flight.get("flight_id"),
            "flight_number": disrupted_flight.get("flight_number"),
            "scheduled_departure": disrupted_flight.get("scheduled_departure")
        },
        "downstream_flight_count": len(downstream_flights),
        "propagation_chain": propagation_chain,
        "max_cumulative_delay_minutes": max([f["cumulative_delay_minutes"] for f in propagation_chain]) if propagation_chain else 0
    }
```

### 3. Identify Aircraft Swap Candidates

```python
@tool
def identify_aircraft_swap_candidates(disrupted_flight_id: str, reference_time: str, max_delay_minutes: int = 120) -> list[dict]:
    """Identify aircraft that could be swapped to minimize disruption.

    Args:
        disrupted_flight_id: ID of the disrupted flight
        reference_time: Reference time for analysis (ISO format with time)
        max_delay_minutes: Maximum acceptable delay for swap (default: 120 minutes)

    Returns:
        List of candidate aircraft with swap feasibility analysis
    """
    from datetime import datetime, timedelta

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights_table = dynamodb.Table(FLIGHTS_TABLE)

    # Get disrupted flight details
    disrupted_flight_response = flights_table.get_item(Key={"flight_id": disrupted_flight_id})
    disrupted_flight = disrupted_flight_response.get("Item", {})

    if not disrupted_flight:
        return []

    disrupted_departure = datetime.fromisoformat(disrupted_flight.get("scheduled_departure", ""))
    disrupted_origin = disrupted_flight.get("origin_airport_id")

    # Query all aircraft rotations for the time window
    search_start = (disrupted_departure - timedelta(hours=2)).isoformat()[:10]
    search_end = (disrupted_departure + timedelta(hours=2)).isoformat()[:10]

    # Get all flights in the time window (simplified - in production, query by airport)
    # This would require an additional GSI or scan
    # For this example, we'll demonstrate the logic

    candidates = []

    # Example: Query specific aircraft registrations
    # In production, this would be more sophisticated
    test_aircraft = ["A6-EYA", "A6-EYB", "A6-EYC", "A6-EYD", "A6-EYE"]

    for aircraft_reg in test_aircraft:
        if aircraft_reg == disrupted_flight.get("aircraft_registration"):
            continue  # Skip the disrupted aircraft

        # Query aircraft rotation
        response = flights_table.query(
            IndexName=AIRCRAFT_ROTATION_INDEX,
            KeyConditionExpression="aircraft_registration = :reg AND scheduled_departure BETWEEN :start AND :end",
            ExpressionAttributeValues={
                ":reg": aircraft_reg,
                ":start": search_start,
                ":end": search_end
            }
        )

        rotation = response.get("Items", [])
        rotation_sorted = sorted(rotation, key=lambda f: f.get("scheduled_departure", ""))

        # Check if aircraft is available at the right time and location
        for i, flight in enumerate(rotation_sorted):
            flight_arrival = datetime.fromisoformat(flight.get("scheduled_arrival", ""))
            flight_destination = flight.get("destination_airport_id")

            # Check if aircraft arrives at disrupted flight's origin before departure
            if flight_destination == disrupted_origin and flight_arrival < disrupted_departure:
                # Calculate available time
                available_time = (disrupted_departure - flight_arrival).total_seconds() / 60

                # Check if next flight allows swap
                next_flight = rotation_sorted[i + 1] if i + 1 < len(rotation_sorted) else None

                if next_flight:
                    next_departure = datetime.fromisoformat(next_flight.get("scheduled_departure", ""))
                    disrupted_arrival = datetime.fromisoformat(disrupted_flight.get("scheduled_arrival", ""))

                    # Check if swap is feasible
                    swap_delay = (disrupted_arrival - next_departure).total_seconds() / 60

                    if swap_delay <= max_delay_minutes:
                        candidates.append({
                            "aircraft_registration": aircraft_reg,
                            "available_time_minutes": round(available_time, 0),
                            "swap_delay_minutes": round(swap_delay, 0) if swap_delay > 0 else 0,
                            "feasibility": "high" if swap_delay <= 30 else "medium" if swap_delay <= 60 else "low",
                            "arriving_flight": {
                                "flight_id": flight.get("flight_id"),
                                "flight_number": flight.get("flight_number"),
                                "arrival_time": flight.get("scheduled_arrival")
                            },
                            "impacted_flight": {
                                "flight_id": next_flight.get("flight_id"),
                                "flight_number": next_flight.get("flight_number"),
                                "departure_time": next_flight.get("scheduled_departure")
                            } if next_flight else None
                        })

    # Sort by feasibility and delay
    candidates_sorted = sorted(candidates, key=lambda c: (c["swap_delay_minutes"], -c["available_time_minutes"]))

    return candidates_sorted
```

### 4. Calculate Aircraft Utilization

```python
@tool
def calculate_aircraft_utilization(aircraft_registration: str, start_date: str, end_date: str) -> dict:
    """Calculate aircraft utilization metrics for a date range.

    Args:
        aircraft_registration: Aircraft registration
        start_date: Start date (ISO format: YYYY-MM-DD)
        end_date: End date (ISO format: YYYY-MM-DD)

    Returns:
        Dictionary with utilization metrics
    """
    from datetime import datetime, timedelta

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights_table = dynamodb.Table(FLIGHTS_TABLE)

    # Query aircraft rotation
    response = flights_table.query(
        IndexName=AIRCRAFT_ROTATION_INDEX,
        KeyConditionExpression="aircraft_registration = :reg AND scheduled_departure BETWEEN :start AND :end",
        ExpressionAttributeValues={
            ":reg": aircraft_registration,
            ":start": start_date,
            ":end": end_date
        }
    )

    flights = response.get("Items", [])

    if not flights:
        return {
            "aircraft_registration": aircraft_registration,
            "period_start": start_date,
            "period_end": end_date,
            "flight_count": 0,
            "total_flight_hours": 0,
            "utilization_percentage": 0
        }

    # Calculate metrics
    total_flight_hours = 0
    total_block_hours = 0
    flight_count = len(flights)

    for flight in flights:
        departure = datetime.fromisoformat(flight.get("scheduled_departure", ""))
        arrival = datetime.fromisoformat(flight.get("scheduled_arrival", ""))

        flight_duration = (arrival - departure).total_seconds() / 3600
        total_flight_hours += flight_duration

    # Calculate period duration
    period_start = datetime.fromisoformat(start_date)
    period_end = datetime.fromisoformat(end_date)
    period_hours = (period_end - period_start).total_seconds() / 3600

    # Calculate utilization (flight hours / available hours)
    utilization_percentage = (total_flight_hours / period_hours) * 100 if period_hours > 0 else 0

    return {
        "aircraft_registration": aircraft_registration,
        "period_start": start_date,
        "period_end": end_date,
        "flight_count": flight_count,
        "total_flight_hours": round(total_flight_hours, 2),
        "period_hours": round(period_hours, 2),
        "utilization_percentage": round(utilization_percentage, 2),
        "average_flight_duration_hours": round(total_flight_hours / flight_count, 2) if flight_count > 0 else 0
    }
```

### 5. Find Next Available Aircraft

```python
@tool
def find_next_available_aircraft(airport_code: str, required_time: str, aircraft_type: str = None) -> list[dict]:
    """Find aircraft that will be available at an airport by a specific time.

    Args:
        airport_code: Airport code (e.g., AUH, DXB)
        required_time: Required availability time (ISO format with time)
        aircraft_type: Optional aircraft type filter (e.g., A380, B777)

    Returns:
        List of available aircraft with arrival details
    """
    from datetime import datetime, timedelta

    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights_table = dynamodb.Table(FLIGHTS_TABLE)

    # Parse required time
    req_time = datetime.fromisoformat(required_time)

    # Search window: 6 hours before required time
    search_start = (req_time - timedelta(hours=6)).isoformat()[:10]
    search_end = req_time.isoformat()[:10]

    # Get all aircraft registrations (in production, this would be from a separate query)
    # For this example, we'll use a sample list
    aircraft_list = ["A6-EYA", "A6-EYB", "A6-EYC", "A6-EYD", "A6-EYE"]

    available_aircraft = []

    for aircraft_reg in aircraft_list:
        # Query aircraft rotation
        response = flights_table.query(
            IndexName=AIRCRAFT_ROTATION_INDEX,
            KeyConditionExpression="aircraft_registration = :reg AND scheduled_departure BETWEEN :start AND :end",
            ExpressionAttributeValues={
                ":reg": aircraft_reg,
                ":start": search_start,
                ":end": search_end
            }
        )

        rotation = response.get("Items", [])

        if not rotation:
            continue

        # Sort by departure time
        rotation_sorted = sorted(rotation, key=lambda f: f.get("scheduled_departure", ""))

        # Find last flight before required time
        last_flight = None
        for flight in rotation_sorted:
            arrival_time = datetime.fromisoformat(flight.get("scheduled_arrival", ""))
            if arrival_time <= req_time and flight.get("destination_airport_id") == airport_code:
                last_flight = flight

        if last_flight:
            arrival_time = datetime.fromisoformat(last_flight.get("scheduled_arrival", ""))
            available_time = (req_time - arrival_time).total_seconds() / 60

            # Check if aircraft type matches (if specified)
            if aircraft_type and last_flight.get("aircraft_type") != aircraft_type:
                continue

            available_aircraft.append({
                "aircraft_registration": aircraft_reg,
                "aircraft_type": last_flight.get("aircraft_type"),
                "arrival_time": last_flight.get("scheduled_arrival"),
                "arrival_flight": {
                    "flight_id": last_flight.get("flight_id"),
                    "flight_number": last_flight.get("flight_number"),
                    "origin": last_flight.get("origin_airport_id")
                },
                "available_time_minutes": round(available_time, 0),
                "availability_status": "available" if available_time >= 45 else "tight_turnaround"
            })

    # Sort by available time (most time available first)
    available_aircraft_sorted = sorted(available_aircraft, key=lambda a: -a["available_time_minutes"])

    return available_aircraft_sorted
```

---

## Performance Monitoring

### Expected Metrics

| Metric            | Target     | Description                            |
| ----------------- | ---------- | -------------------------------------- |
| Average Latency   | 20-30ms    | Typical query response time            |
| P99 Latency       | 40-50ms    | 99th percentile response time          |
| Query Volume      | 200+/day   | Daily query count                      |
| Performance Gain  | 100x       | Highest improvement of Priority 1 GSIs |
| Consumed Capacity | < 50 RCU/s | Read capacity units per second         |
| Throttling Events | 0          | Should not experience throttling       |

### Monitoring Queries

```python
import boto3
from datetime import datetime, timedelta

def monitor_aircraft_rotation_gsi():
    """Monitor aircraft-rotation-index GSI performance."""
    cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

    metrics = {}

    # Get consumed read capacity
    read_capacity = cloudwatch.get_metric_statistics(
        Namespace="AWS/DynamoDB",
        MetricName="ConsumedReadCapacityUnits",
        Dimensions=[
            {"Name": "TableName", "Value": "flights"},
            {"Name": "GlobalSecondaryIndexName", "Value": "aircraft-rotation-index"}
        ],
        StartTime=datetime.now() - timedelta(hours=1),
        EndTime=datetime.now(),
        Period=300,
        Statistics=["Average", "Maximum", "Sum"]
    )

    metrics["consumed_read_capacity"] = read_capacity["Datapoints"]

    # Get throttled requests
    throttled = cloudwatch.get_metric_statistics(
        Namespace="AWS/DynamoDB",
        MetricName="UserErrors",
        Dimensions=[
            {"Name": "TableName", "Value": "flights"},
            {"Name": "GlobalSecondaryIndexName", "Value": "aircraft-rotation-index"}
        ],
        StartTime=datetime.now() - timedelta(hours=1),
        EndTime=datetime.now(),
        Period=300,
        Statistics=["Sum"]
    )

    metrics["throttled_requests"] = throttled["Datapoints"]

    return {
        "gsi_name": "aircraft-rotation-index",
        "table_name": "flights",
        "metrics": metrics
    }
```

---

## Integration with Agent Code

### Complete Agent Tool Example

```python
# In src/agents/network/agent.py

import boto3
from langchain_core.tools import tool
from database.constants import (
    FLIGHTS_TABLE,
    AIRCRAFT_ROTATION_INDEX
)

# Define all tools using @tool decorator
@tool
def query_aircraft_rotation(aircraft_registration: str, start_date: str = None, end_date: str = None) -> list[dict]:
    """Query complete aircraft rotation ordered by departure time."""
    # Implementation as shown above
    pass

@tool
def analyze_propagation_chain(aircraft_registration: str, disrupted_flight_id: str, reference_time: str) -> dict:
    """Analyze how a disruption propagates through aircraft rotation."""
    # Implementation as shown above
    pass

@tool
def identify_aircraft_swap_candidates(disrupted_flight_id: str, reference_time: str, max_delay_minutes: int = 120) -> list[dict]:
    """Identify aircraft that could be swapped to minimize disruption."""
    # Implementation as shown above
    pass

@tool
def calculate_aircraft_utilization(aircraft_registration: str, start_date: str, end_date: str) -> dict:
    """Calculate aircraft utilization metrics for a date range."""
    # Implementation as shown above
    pass

@tool
def find_next_available_aircraft(airport_code: str, required_time: str, aircraft_type: str = None) -> list[dict]:
    """Find aircraft that will be available at an airport by a specific time."""
    # Implementation as shown above
    pass

# Agent implementation
async def analyze_network(payload: dict, llm: Any, mcp_tools: list):
    """Analyze network impact for a disruption."""

    # Tools available to the agent
    tools = [
        query_aircraft_rotation,
        analyze_propagation_chain,
        identify_aircraft_swap_candidates,
        calculate_aircraft_utilization,
        find_next_available_aircraft
    ]

    # Agent uses tools autonomously during reasoning
    # ...
```

---

## Best Practices

### 1. Always Use Date Range Filters

```python
# Good: Query with date range for efficiency
rotation = query_aircraft_rotation(
    aircraft_registration="A6-EYA",
    start_date="2026-01-20",
    end_date="2026-01-22"
)

# Avoid: Querying all flights and filtering in code
all_flights = query_aircraft_rotation(aircraft_registration="A6-EYA")
filtered = [f for f in all_flights if "2026-01-20" <= f["scheduled_departure"][:10] <= "2026-01-22"]
```

### 2. Limit Propagation Analysis Window

```python
# Good: Analyze 24-48 hour window
propagation = analyze_propagation_chain(
    aircraft_registration="A6-EYA",
    disrupted_flight_id="FL123-2026-01-20",
    reference_time="2026-01-20T10:00:00"
)

# Avoid: Analyzing entire rotation (days/weeks of flights)
```

### 3. Cache Aircraft Rotations

```python
from functools import lru_cache

@lru_cache(maxsize=50)
def get_aircraft_rotation_cached(aircraft_registration: str, date: str) -> tuple:
    """Cached version of aircraft rotation query."""
    rotation = query_aircraft_rotation(
        aircraft_registration=aircraft_registration,
        start_date=date,
        end_date=date
    )
    return tuple(rotation)  # Convert to tuple for caching
```

### 4. Handle Pagination for Long Rotations

```python
@tool
def query_aircraft_rotation_paginated(aircraft_registration: str, start_date: str, end_date: str) -> list[dict]:
    """Query aircraft rotation with pagination support."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    flights_table = dynamodb.Table(FLIGHTS_TABLE)

    all_flights = []
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            response = flights_table.query(
                IndexName=AIRCRAFT_ROTATION_INDEX,
                KeyConditionExpression="aircraft_registration = :reg AND scheduled_departure BETWEEN :start AND :end",
                ExpressionAttributeValues={
                    ":reg": aircraft_registration,
                    ":start": start_date,
                    ":end": end_date
                },
                ExclusiveStartKey=last_evaluated_key
            )
        else:
            response = flights_table.query(
                IndexName=AIRCRAFT_ROTATION_INDEX,
                KeyConditionExpression="aircraft_registration = :reg AND scheduled_departure BETWEEN :start AND :end",
                ExpressionAttributeValues={
                    ":reg": aircraft_registration,
                    ":start": start_date,
                    ":end": end_date
                }
            )

        all_flights.extend(response.get("Items", []))
        last_evaluated_key = response.get("LastEvaluatedKey")

        if not last_evaluated_key:
            break

    return all_flights
```

---

## Troubleshooting

### GSI Not Found Error

```
ClientError: An error occurred (ValidationException) when calling the Query operation:
The table does not have the specified index: aircraft-rotation-index
```

**Solution**: Create the Priority 1 GSI:

```bash
cd scripts
python3 create_priority1_gsis.py --table flights
python3 create_priority1_gsis.py --check-status
```

### Slow Queries (>100ms)

If queries exceed 100ms:

1. Verify GSI is ACTIVE: `python3 create_priority1_gsis.py --check-status`
2. Check date range is reasonable (avoid querying months of data)
3. Monitor consumed capacity in CloudWatch
4. Check for throttling events

### Empty Results

If queries return no results:

1. Verify aircraft registration format (e.g., "A6-EYA" not "A6EYA")
2. Check date format is ISO (YYYY-MM-DD)
3. Verify aircraft exists in flights table
4. Check date range includes actual flights

---

## Related Documentation

- [Priority 1 GSIs Overview](../../../scripts/PRIORITY1_GSIS_README.md)
- [Database Constants](../src/database/constants.py)
- [Structured Output Usage](./STRUCTURED_OUTPUT_USAGE.md)
- [Network Agent Implementation](../src/agents/network/agent.py)
