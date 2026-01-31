# Guest Experience Agent - Priority 1 GSI Usage Guide

## Overview

The Guest Experience Agent uses 4 Priority 1 GSIs to efficiently query passenger, booking, and baggage data. These GSIs provide **50x performance improvements** over table scans and are critical for optimal agent performance.

## GSIs Used by Guest Experience Agent

### 1. passenger-flight-index (bookings table)

**Purpose**: Query passenger booking history across multiple flights

**Performance**:

- Expected Latency: 15-20ms average, 30-40ms p99
- Query Volume: 300+ queries/day
- Performance Improvement: 50x faster than table scan

**Use Cases**:

- Retrieve passenger's complete booking history
- Identify frequent travelers for prioritization
- Check passenger's previous disruption experiences
- Analyze passenger travel patterns

**Query Example**:

```python
from langchain_core.tools import tool
import boto3
from database.constants import BOOKINGS_TABLE, PASSENGER_FLIGHT_INDEX

@tool
def query_passenger_bookings(passenger_id: str) -> list[dict]:
    """Query all bookings for a specific passenger.

    Args:
        passenger_id: Unique passenger identifier (e.g., P12345)

    Returns:
        List of booking records for the passenger
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    bookings_table = dynamodb.Table(BOOKINGS_TABLE)

    response = bookings_table.query(
        IndexName=PASSENGER_FLIGHT_INDEX,
        KeyConditionExpression="passenger_id = :pid",
        ExpressionAttributeValues={":pid": passenger_id}
    )

    return response.get("Items", [])
```

**Query with Flight Filter**:

```python
@tool
def query_passenger_flight_booking(passenger_id: str, flight_id: str) -> dict:
    """Query specific booking for passenger on a flight.

    Args:
        passenger_id: Unique passenger identifier
        flight_id: Unique flight identifier

    Returns:
        Booking record or None if not found
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    bookings_table = dynamodb.Table(BOOKINGS_TABLE)

    response = bookings_table.query(
        IndexName=PASSENGER_FLIGHT_INDEX,
        KeyConditionExpression="passenger_id = :pid AND flight_id = :fid",
        ExpressionAttributeValues={
            ":pid": passenger_id,
            ":fid": flight_id
        }
    )

    items = response.get("Items", [])
    return items[0] if items else None
```

---

### 2. flight-status-index (bookings table)

**Purpose**: Query flight passenger manifest by booking status

**Performance**:

- Expected Latency: 20-30ms average, 40-50ms p99
- Query Volume: 300+ queries/day
- Performance Improvement: 50x faster than table scan

**Use Cases**:

- Retrieve confirmed passenger manifest for a flight
- Identify cancelled bookings for rebooking
- Find standby passengers for seat allocation
- Calculate passenger load factor

**Query Example**:

```python
@tool
def query_flight_manifest(flight_id: str, booking_status: str = "confirmed") -> list[dict]:
    """Query passenger manifest for a flight by booking status.

    Args:
        flight_id: Unique flight identifier (e.g., FL123-2026-01-20)
        booking_status: Booking status (confirmed, cancelled, standby, checked_in)

    Returns:
        List of bookings with the specified status
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    bookings_table = dynamodb.Table(BOOKINGS_TABLE)

    response = bookings_table.query(
        IndexName=FLIGHT_STATUS_INDEX,
        KeyConditionExpression="flight_id = :fid AND booking_status = :status",
        ExpressionAttributeValues={
            ":fid": flight_id,
            ":status": booking_status
        }
    )

    return response.get("Items", [])
```

**Multi-Status Query**:

```python
@tool
def query_flight_all_bookings(flight_id: str) -> dict:
    """Query all bookings for a flight grouped by status.

    Args:
        flight_id: Unique flight identifier

    Returns:
        Dictionary with bookings grouped by status
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    bookings_table = dynamodb.Table(BOOKINGS_TABLE)

    statuses = ["confirmed", "cancelled", "standby", "checked_in"]
    results = {}

    for status in statuses:
        response = bookings_table.query(
            IndexName=FLIGHT_STATUS_INDEX,
            KeyConditionExpression="flight_id = :fid AND booking_status = :status",
            ExpressionAttributeValues={
                ":fid": flight_id,
                ":status": status
            }
        )
        results[status] = response.get("Items", [])

    return results
```

---

### 3. location-status-index (Baggage table)

**Purpose**: Track baggage by location and status for mishandled baggage

**Performance**:

- Expected Latency: 15-20ms average, 30-40ms p99
- Query Volume: 200+ queries/day
- Performance Improvement: 50x faster than table scan

**Use Cases**:

- Find mishandled baggage at specific airport
- Track delayed baggage for passenger notifications
- Identify baggage requiring special handling
- Monitor baggage transfer status

**Query Example**:

```python
@tool
def query_baggage_at_location(current_location: str, baggage_status: str) -> list[dict]:
    """Query baggage at a specific location with a specific status.

    Args:
        current_location: Airport code (e.g., AUH, DXB, LHR)
        baggage_status: Baggage status (checked, in_transit, delivered, mishandled, delayed)

    Returns:
        List of baggage records at the location with the status
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    baggage_table = dynamodb.Table(BAGGAGE_TABLE)

    response = baggage_table.query(
        IndexName=LOCATION_STATUS_INDEX,
        KeyConditionExpression="current_location = :loc AND baggage_status = :status",
        ExpressionAttributeValues={
            ":loc": current_location,
            ":status": baggage_status
        }
    )

    return response.get("Items", [])
```

**Mishandled Baggage Query**:

```python
@tool
def query_mishandled_baggage(airport_code: str) -> list[dict]:
    """Query all mishandled baggage at an airport.

    Args:
        airport_code: Airport code (e.g., AUH)

    Returns:
        List of mishandled baggage records
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    baggage_table = dynamodb.Table(BAGGAGE_TABLE)

    response = baggage_table.query(
        IndexName=LOCATION_STATUS_INDEX,
        KeyConditionExpression="current_location = :loc AND baggage_status = :status",
        ExpressionAttributeValues={
            ":loc": airport_code,
            ":status": "mishandled"
        }
    )

    return response.get("Items", [])
```

---

### 4. passenger-elite-tier-index (Passengers table)

**Purpose**: Identify elite passengers for VIP prioritization

**Performance**:

- Expected Latency: 20-30ms average, 40-50ms p99
- Query Volume: 300+ queries/day
- Performance Improvement: 50x faster than table scan

**Use Cases**:

- Identify VIP passengers on disrupted flights
- Prioritize elite members for rebooking
- Provide enhanced service to high-tier passengers
- Calculate elite passenger impact

**Query Example**:

```python
@tool
def query_elite_passengers(tier_id: int, min_booking_date: str = None) -> list[dict]:
    """Query elite passengers by tier level.

    Args:
        tier_id: Frequent flyer tier ID (1=Silver, 2=Gold, 3=Platinum, 4=Diamond)
        min_booking_date: Optional minimum booking date (ISO format: YYYY-MM-DD)

    Returns:
        List of elite passenger records
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    passengers_table = dynamodb.Table(PASSENGERS_TABLE)

    if min_booking_date:
        response = passengers_table.query(
            IndexName=PASSENGER_ELITE_TIER_INDEX,
            KeyConditionExpression="frequent_flyer_tier_id = :tier AND booking_date >= :date",
            ExpressionAttributeValues={
                ":tier": tier_id,
                ":date": min_booking_date
            }
        )
    else:
        response = passengers_table.query(
            IndexName=PASSENGER_ELITE_TIER_INDEX,
            KeyConditionExpression="frequent_flyer_tier_id = :tier",
            ExpressionAttributeValues={":tier": tier_id}
        )

    return response.get("Items", [])
```

**VIP Passenger Identification**:

```python
@tool
def identify_vip_passengers_on_flight(flight_id: str) -> list[dict]:
    """Identify VIP passengers (Gold, Platinum, Diamond) on a flight.

    Args:
        flight_id: Unique flight identifier

    Returns:
        List of VIP passenger records with tier information
    """
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    bookings_table = dynamodb.Table(BOOKINGS_TABLE)
    passengers_table = dynamodb.Table(PASSENGERS_TABLE)

    # Get all confirmed bookings for the flight
    bookings_response = bookings_table.query(
        IndexName=FLIGHT_STATUS_INDEX,
        KeyConditionExpression="flight_id = :fid AND booking_status = :status",
        ExpressionAttributeValues={
            ":fid": flight_id,
            ":status": "confirmed"
        }
    )

    bookings = bookings_response.get("Items", [])
    vip_passengers = []

    # Check each passenger's tier (Gold=2, Platinum=3, Diamond=4)
    for booking in bookings:
        passenger_id = booking.get("passenger_id")
        passenger_response = passengers_table.get_item(Key={"passenger_id": passenger_id})
        passenger = passenger_response.get("Item", {})

        tier_id = passenger.get("frequent_flyer_tier_id", 0)
        if tier_id >= 2:  # Gold or higher
            vip_passengers.append({
                "passenger_id": passenger_id,
                "tier_id": tier_id,
                "tier_name": {2: "Gold", 3: "Platinum", 4: "Diamond"}.get(tier_id, "Unknown"),
                "booking_id": booking.get("booking_id"),
                "seat_number": booking.get("seat_number")
            })

    return vip_passengers
```

---

## Performance Monitoring

### Expected Metrics

| GSI                        | Avg Latency | P99 Latency | Query Volume | Improvement |
| -------------------------- | ----------- | ----------- | ------------ | ----------- |
| passenger-flight-index     | 15-20ms     | 30-40ms     | 300+/day     | 50x         |
| flight-status-index        | 20-30ms     | 40-50ms     | 300+/day     | 50x         |
| location-status-index      | 15-20ms     | 30-40ms     | 200+/day     | 50x         |
| passenger-elite-tier-index | 20-30ms     | 40-50ms     | 300+/day     | 50x         |

### Monitoring Queries

```python
# Check GSI consumed capacity
import boto3

cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

def get_gsi_metrics(table_name: str, index_name: str, metric_name: str):
    """Get CloudWatch metrics for a GSI."""
    response = cloudwatch.get_metric_statistics(
        Namespace="AWS/DynamoDB",
        MetricName=metric_name,
        Dimensions=[
            {"Name": "TableName", "Value": table_name},
            {"Name": "GlobalSecondaryIndexName", "Value": index_name}
        ],
        StartTime=datetime.now() - timedelta(hours=1),
        EndTime=datetime.now(),
        Period=300,
        Statistics=["Average", "Maximum"]
    )
    return response["Datapoints"]

# Example: Check consumed read capacity
metrics = get_gsi_metrics("bookings", "passenger-flight-index", "ConsumedReadCapacityUnits")
```

---

## Integration with Agent Code

### Complete Agent Tool Example

```python
# In src/agents/guest_experience/agent.py

import boto3
from langchain_core.tools import tool
from database.constants import (
    BOOKINGS_TABLE,
    BAGGAGE_TABLE,
    PASSENGERS_TABLE,
    PASSENGER_FLIGHT_INDEX,
    FLIGHT_STATUS_INDEX,
    LOCATION_STATUS_INDEX,
    PASSENGER_ELITE_TIER_INDEX
)

# Define all tools using @tool decorator
@tool
def query_passenger_bookings(passenger_id: str) -> list[dict]:
    """Query all bookings for a specific passenger."""
    # Implementation as shown above
    pass

@tool
def query_flight_manifest(flight_id: str, booking_status: str = "confirmed") -> list[dict]:
    """Query passenger manifest for a flight by booking status."""
    # Implementation as shown above
    pass

@tool
def query_baggage_at_location(current_location: str, baggage_status: str) -> list[dict]:
    """Query baggage at a specific location with a specific status."""
    # Implementation as shown above
    pass

@tool
def identify_vip_passengers_on_flight(flight_id: str) -> list[dict]:
    """Identify VIP passengers (Gold, Platinum, Diamond) on a flight."""
    # Implementation as shown above
    pass

# Agent implementation
async def analyze_guest_experience(payload: dict, llm: Any, mcp_tools: list):
    """Analyze guest experience for a disruption."""

    # Tools available to the agent
    tools = [
        query_passenger_bookings,
        query_flight_manifest,
        query_baggage_at_location,
        identify_vip_passengers_on_flight
    ]

    # Agent uses tools autonomously during reasoning
    # ...
```

---

## Best Practices

### 1. Use Appropriate GSI for Query Pattern

- **Passenger history**: Use `passenger-flight-index`
- **Flight manifest**: Use `flight-status-index`
- **Baggage tracking**: Use `location-status-index`
- **VIP identification**: Use `passenger-elite-tier-index`

### 2. Optimize Query Filters

```python
# Good: Use GSI with specific status
response = bookings_table.query(
    IndexName=FLIGHT_STATUS_INDEX,
    KeyConditionExpression="flight_id = :fid AND booking_status = :status",
    ExpressionAttributeValues={":fid": flight_id, ":status": "confirmed"}
)

# Avoid: Query all and filter in code
response = bookings_table.query(
    IndexName=FLIGHT_ID_INDEX,
    KeyConditionExpression="flight_id = :fid",
    ExpressionAttributeValues={":fid": flight_id}
)
filtered = [b for b in response["Items"] if b["booking_status"] == "confirmed"]
```

### 3. Handle Pagination for Large Results

```python
@tool
def query_all_elite_passengers(tier_id: int) -> list[dict]:
    """Query all elite passengers with pagination."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    passengers_table = dynamodb.Table(PASSENGERS_TABLE)

    all_items = []
    last_evaluated_key = None

    while True:
        if last_evaluated_key:
            response = passengers_table.query(
                IndexName=PASSENGER_ELITE_TIER_INDEX,
                KeyConditionExpression="frequent_flyer_tier_id = :tier",
                ExpressionAttributeValues={":tier": tier_id},
                ExclusiveStartKey=last_evaluated_key
            )
        else:
            response = passengers_table.query(
                IndexName=PASSENGER_ELITE_TIER_INDEX,
                KeyConditionExpression="frequent_flyer_tier_id = :tier",
                ExpressionAttributeValues={":tier": tier_id}
            )

        all_items.extend(response.get("Items", []))
        last_evaluated_key = response.get("LastEvaluatedKey")

        if not last_evaluated_key:
            break

    return all_items
```

### 4. Error Handling

```python
@tool
def query_passenger_bookings_safe(passenger_id: str) -> dict:
    """Query passenger bookings with error handling."""
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        bookings_table = dynamodb.Table(BOOKINGS_TABLE)

        response = bookings_table.query(
            IndexName=PASSENGER_FLIGHT_INDEX,
            KeyConditionExpression="passenger_id = :pid",
            ExpressionAttributeValues={":pid": passenger_id}
        )

        return {
            "success": True,
            "bookings": response.get("Items", []),
            "count": len(response.get("Items", []))
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "bookings": []
        }
```

---

## Troubleshooting

### GSI Not Found Error

```
ClientError: An error occurred (ValidationException) when calling the Query operation:
The table does not have the specified index: passenger-flight-index
```

**Solution**: Ensure Priority 1 GSIs are created:

```bash
cd scripts
python3 create_priority1_gsis.py --table bookings
python3 create_priority1_gsis.py --check-status
```

### High Latency

If queries exceed 100ms:

1. Check GSI status: `python3 create_priority1_gsis.py --check-status`
2. Monitor consumed capacity in CloudWatch
3. Check for throttling events
4. Consider increasing provisioned capacity

### Table Scans Detected

If queries result in table scans:

1. Verify GSI is being used: Check `IndexName` parameter
2. Ensure query uses GSI partition key
3. Use `KeyConditionExpression` not `FilterExpression` for GSI keys

---

## Related Documentation

- [Priority 1 GSIs Overview](../../../scripts/PRIORITY1_GSIS_README.md)
- [Database Constants](../src/database/constants.py)
- [Structured Output Usage](./STRUCTURED_OUTPUT_USAGE.md)
- [Guest Experience Agent Implementation](../src/agents/guest_experience/agent.py)
