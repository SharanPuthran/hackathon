# Priority 1 GSIs - Critical for Agent Efficiency

This document describes the Priority 1 (Critical) Global Secondary Indexes created by `create_priority1_gsis.py`.

## Overview

Priority 1 GSIs provide **50-100x performance improvements** for high-frequency agent queries. These GSIs are critical for optimal agent performance and should be created before deploying the multi-round orchestration system.

## GSI Definitions

### 1. bookings: passenger-flight-index

**Purpose**: Query passenger booking history across flights

**Key Schema**:

- Partition Key: `passenger_id` (String)
- Sort Key: `flight_id` (String)

**Required By**: Guest Experience Agent

**Query Pattern**: Find all bookings for a specific passenger across multiple flights

**Estimated Impact**: 50x performance improvement, 300+ queries/day

**Example Query**:

```python
response = bookings_table.query(
    IndexName='passenger-flight-index',
    KeyConditionExpression='passenger_id = :pid',
    ExpressionAttributeValues={':pid': 'P12345'}
)
```

---

### 2. bookings: flight-status-index

**Purpose**: Query flight passenger manifest by booking status

**Key Schema**:

- Partition Key: `flight_id` (String)
- Sort Key: `booking_status` (String)

**Required By**: Guest Experience Agent

**Query Pattern**: Find all passengers on a flight with a specific booking status (e.g., confirmed, cancelled)

**Estimated Impact**: 50x performance improvement, 300+ queries/day

**Example Query**:

```python
response = bookings_table.query(
    IndexName='flight-status-index',
    KeyConditionExpression='flight_id = :fid AND booking_status = :status',
    ExpressionAttributeValues={
        ':fid': 'FL123-2026-01-20',
        ':status': 'confirmed'
    }
)
```

---

### 3. Baggage: location-status-index

**Purpose**: Track baggage by location and status for mishandled baggage

**Key Schema**:

- Partition Key: `current_location` (String)
- Sort Key: `baggage_status` (String)

**Required By**: Guest Experience Agent

**Query Pattern**: Find all baggage at a specific location with a specific status (e.g., mishandled, delayed)

**Estimated Impact**: 50x performance improvement, 200+ queries/day

**Example Query**:

```python
response = baggage_table.query(
    IndexName='location-status-index',
    KeyConditionExpression='current_location = :loc AND baggage_status = :status',
    ExpressionAttributeValues={
        ':loc': 'AUH',
        ':status': 'mishandled'
    }
)
```

---

### 4. CrewRoster: crew-duty-date-index

**Purpose**: Query crew duty history for FDP (Flight Duty Period) and rest calculations

**Key Schema**:

- Partition Key: `crew_id` (String)
- Sort Key: `duty_date` (String)

**Required By**: Crew Compliance Agent

**Query Pattern**: Find all duties for a crew member within a date range for FDP calculations

**Estimated Impact**: 50x performance improvement, 500+ queries/day

**Example Query**:

```python
response = crew_roster_table.query(
    IndexName='crew-duty-date-index',
    KeyConditionExpression='crew_id = :cid AND duty_date BETWEEN :start AND :end',
    ExpressionAttributeValues={
        ':cid': 'CREW001',
        ':start': '2026-01-15',
        ':end': '2026-01-20'
    }
)
```

---

### 5. flights: aircraft-rotation-index

**Purpose**: Query complete aircraft rotation for propagation chain analysis

**Key Schema**:

- Partition Key: `aircraft_registration` (String)
- Sort Key: `scheduled_departure` (String)

**Required By**: Network Agent

**Query Pattern**: Find all flights for a specific aircraft ordered by departure time to analyze propagation chains

**Estimated Impact**: 100x performance improvement, 200+ queries/day

**Example Query**:

```python
response = flights_table.query(
    IndexName='aircraft-rotation-index',
    KeyConditionExpression='aircraft_registration = :reg',
    ExpressionAttributeValues={':reg': 'A6-EYA'}
)
```

---

### 6. passengers: passenger-elite-tier-index

**Purpose**: Identify elite passengers for VIP prioritization

**Key Schema**:

- Partition Key: `frequent_flyer_tier_id` (Number)
- Sort Key: `booking_date` (String)

**Required By**: Guest Experience Agent

**Query Pattern**: Find all elite passengers (e.g., Gold, Platinum) for prioritization decisions

**Estimated Impact**: 50x performance improvement, 300+ queries/day

**Example Query**:

```python
response = passengers_table.query(
    IndexName='passenger-elite-tier-index',
    KeyConditionExpression='frequent_flyer_tier_id = :tier AND booking_date >= :date',
    ExpressionAttributeValues={
        ':tier': 3,  # Platinum tier
        ':date': '2026-01-01'
    }
)
```

---

## Usage

### Create All Priority 1 GSIs

```bash
python3 scripts/create_priority1_gsis.py
```

### Create GSIs for Specific Table

```bash
python3 scripts/create_priority1_gsis.py --table bookings
```

### Check GSI Status

```bash
python3 scripts/create_priority1_gsis.py --check-status
```

### Validate GSI Performance

```bash
python3 scripts/create_priority1_gsis.py --validate
```

### Rollback (Delete GSIs)

```bash
python3 scripts/create_priority1_gsis.py --rollback
```

## Performance Expectations

| Agent            | GSI                        | Query Volume | Performance Improvement |
| ---------------- | -------------------------- | ------------ | ----------------------- |
| Guest Experience | passenger-flight-index     | 300+/day     | 50x faster              |
| Guest Experience | flight-status-index        | 300+/day     | 50x faster              |
| Guest Experience | location-status-index      | 200+/day     | 50x faster              |
| Guest Experience | passenger-elite-tier-index | 300+/day     | 50x faster              |
| Crew Compliance  | crew-duty-date-index       | 500+/day     | 50x faster              |
| Network          | aircraft-rotation-index    | 200+/day     | 100x faster             |

## Integration with Agent Code

After creating the GSIs, update agent code to use the new constants:

```python
from database.constants import (
    CREW_DUTY_DATE_INDEX,
    AIRCRAFT_ROTATION_INDEX,
    PASSENGER_ELITE_TIER_INDEX,
    PASSENGER_FLIGHT_INDEX,
    FLIGHT_STATUS_INDEX,
    LOCATION_STATUS_INDEX
)

# Example: Crew Compliance Agent
@tool
def query_crew_duty_history(crew_id: str, start_date: str, end_date: str) -> list[dict]:
    """Query crew duty history for FDP calculations."""
    response = crew_roster_table.query(
        IndexName=CREW_DUTY_DATE_INDEX,
        KeyConditionExpression='crew_id = :cid AND duty_date BETWEEN :start AND :end',
        ExpressionAttributeValues={
            ':cid': crew_id,
            ':start': start_date,
            ':end': end_date
        }
    )
    return response.get('Items', [])
```

## Monitoring

After deployment, monitor:

1. **Query Latency**: Should be < 50ms average, < 100ms p99
2. **GSI Consumed Capacity**: Track read/write capacity usage
3. **Table Scans**: Should be 0 (all queries use GSIs)
4. **Throttling Events**: Should be minimal

## Next Steps

1. Create Priority 1 GSIs: `python3 scripts/create_priority1_gsis.py`
2. Validate GSI status: `python3 scripts/create_priority1_gsis.py --check-status`
3. Update agent code to use new GSIs
4. Run validation script: `python3 scripts/validate_dynamodb_data.py`
5. Deploy updated agents
6. Monitor query performance

## Related Documentation

- [Core GSIs](./create_gsis.py) - Core GSIs created in Task 1.1-1.5
- [Priority 2 GSIs](./create_priority2_gsis.py) - High-value GSIs (to be created)
- [Priority 3 GSIs](./create_priority3_gsis.py) - Future enhancement GSIs (to be created)
- [Database Constants](../skymarshal_agents_new/skymarshal/src/database/constants.py) - Centralized table and GSI names
