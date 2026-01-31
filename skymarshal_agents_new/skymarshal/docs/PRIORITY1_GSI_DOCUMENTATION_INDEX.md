# Priority 1 GSI Documentation Index

## Overview

This document provides an index to all Priority 1 GSI usage documentation. Priority 1 GSIs are critical for agent performance, providing **50-100x performance improvements** over table scans.

## Documentation by Agent

### Guest Experience Agent

**File**: [GUEST_EXPERIENCE_GSI_USAGE.md](./GUEST_EXPERIENCE_GSI_USAGE.md)

**GSIs Used**: 4 Priority 1 GSIs

1. **passenger-flight-index** (bookings table)
   - Query passenger booking history
   - Expected Latency: 15-20ms
   - Query Volume: 300+/day
   - Performance Gain: 50x

2. **flight-status-index** (bookings table)
   - Query flight passenger manifest by status
   - Expected Latency: 20-30ms
   - Query Volume: 300+/day
   - Performance Gain: 50x

3. **location-status-index** (Baggage table)
   - Track baggage by location and status
   - Expected Latency: 15-20ms
   - Query Volume: 200+/day
   - Performance Gain: 50x

4. **passenger-elite-tier-index** (Passengers table)
   - Identify elite passengers for VIP prioritization
   - Expected Latency: 20-30ms
   - Query Volume: 300+/day
   - Performance Gain: 50x

**Key Use Cases**:

- Passenger rebooking and prioritization
- VIP passenger identification
- Baggage tracking and mishandled baggage
- Flight manifest queries

---

### Crew Compliance Agent

**File**: [CREW_COMPLIANCE_GSI_USAGE.md](./CREW_COMPLIANCE_GSI_USAGE.md)

**GSIs Used**: 1 Priority 1 GSI

1. **crew-duty-date-index** (CrewRoster table)
   - Query crew duty history for FDP calculations
   - Expected Latency: 15-20ms
   - Query Volume: 500+/day (highest volume)
   - Performance Gain: 50x

**Key Use Cases**:

- Flight Duty Period (FDP) calculations
- Rest period compliance verification
- Monthly and yearly duty limit checks
- Crew scheduling validation
- Regulatory compliance (EASA FTL)

---

### Network Agent

**File**: [NETWORK_GSI_USAGE.md](./NETWORK_GSI_USAGE.md)

**GSIs Used**: 1 Priority 1 GSI

1. **aircraft-rotation-index** (flights table)
   - Query complete aircraft rotation
   - Expected Latency: 20-30ms
   - Query Volume: 200+/day
   - Performance Gain: 100x (highest improvement)

**Key Use Cases**:

- Propagation chain analysis
- Aircraft swap candidate identification
- Aircraft utilization calculations
- Downstream flight impact assessment
- Recovery time optimization

---

## Quick Reference

### GSI Performance Summary

| GSI Name                   | Table      | Agent(s)         | Latency | Volume   | Gain |
| -------------------------- | ---------- | ---------------- | ------- | -------- | ---- |
| passenger-flight-index     | bookings   | Guest Experience | 15-20ms | 300+/day | 50x  |
| flight-status-index        | bookings   | Guest Experience | 20-30ms | 300+/day | 50x  |
| location-status-index      | Baggage    | Guest Experience | 15-20ms | 200+/day | 50x  |
| passenger-elite-tier-index | Passengers | Guest Experience | 20-30ms | 300+/day | 50x  |
| crew-duty-date-index       | CrewRoster | Crew Compliance  | 15-20ms | 500+/day | 50x  |
| aircraft-rotation-index    | flights    | Network          | 20-30ms | 200+/day | 100x |

### Total Impact

- **Total GSIs**: 6 Priority 1 GSIs
- **Total Query Volume**: 1,800+ queries/day
- **Average Performance Gain**: 58x faster than table scans
- **Agents Benefiting**: 3 agents (Guest Experience, Crew Compliance, Network)

---

## Getting Started

### 1. Create Priority 1 GSIs

```bash
cd scripts
python3 create_priority1_gsis.py
```

### 2. Verify GSI Status

```bash
python3 create_priority1_gsis.py --check-status
```

### 3. Validate GSI Performance

```bash
python3 test_priority1_gsis.py
```

### 4. Review Agent-Specific Documentation

- [Guest Experience Agent GSI Usage](./GUEST_EXPERIENCE_GSI_USAGE.md)
- [Crew Compliance Agent GSI Usage](./CREW_COMPLIANCE_GSI_USAGE.md)
- [Network Agent GSI Usage](./NETWORK_GSI_USAGE.md)

---

## Implementation Checklist

### Database Setup

- [ ] Create all 6 Priority 1 GSIs using `create_priority1_gsis.py`
- [ ] Verify all GSIs are ACTIVE
- [ ] Run validation script to test GSI queries
- [ ] Monitor GSI consumed capacity in CloudWatch

### Agent Implementation

#### Guest Experience Agent

- [ ] Implement `query_passenger_bookings` tool
- [ ] Implement `query_flight_manifest` tool
- [ ] Implement `query_baggage_at_location` tool
- [ ] Implement `identify_vip_passengers_on_flight` tool
- [ ] Test all tools with sample data
- [ ] Verify queries use GSIs (no table scans)

#### Crew Compliance Agent

- [ ] Implement `query_crew_duty_history` tool
- [ ] Implement `calculate_cumulative_fdp` tool
- [ ] Implement `verify_rest_period_compliance` tool
- [ ] Implement `check_monthly_duty_limits` tool
- [ ] Implement `identify_crew_approaching_limits` tool
- [ ] Test all tools with sample data
- [ ] Verify queries use GSIs (no table scans)

#### Network Agent

- [ ] Implement `query_aircraft_rotation` tool
- [ ] Implement `analyze_propagation_chain` tool
- [ ] Implement `identify_aircraft_swap_candidates` tool
- [ ] Implement `calculate_aircraft_utilization` tool
- [ ] Implement `find_next_available_aircraft` tool
- [ ] Test all tools with sample data
- [ ] Verify queries use GSIs (no table scans)

### Testing and Validation

- [ ] Run unit tests for all agent tools
- [ ] Run integration tests for multi-agent scenarios
- [ ] Validate query latency meets targets (<100ms)
- [ ] Verify no table scans occur
- [ ] Monitor GSI consumed capacity
- [ ] Check for throttling events

### Documentation

- [x] Create Guest Experience Agent GSI usage guide
- [x] Create Crew Compliance Agent GSI usage guide
- [x] Create Network Agent GSI usage guide
- [x] Create Priority 1 GSI documentation index
- [ ] Update agent README files with GSI references
- [ ] Add GSI usage examples to agent code comments

---

## Performance Monitoring

### CloudWatch Metrics to Monitor

1. **ConsumedReadCapacityUnits**: Track read capacity usage per GSI
2. **UserErrors**: Monitor throttling events
3. **SystemErrors**: Track DynamoDB service errors
4. **SuccessfulRequestLatency**: Measure query response times

### Monitoring Script

```python
import boto3
from datetime import datetime, timedelta

def monitor_all_priority1_gsis():
    """Monitor all Priority 1 GSIs."""
    cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

    gsis = [
        ("bookings", "passenger-flight-index"),
        ("bookings", "flight-status-index"),
        ("Baggage", "location-status-index"),
        ("Passengers", "passenger-elite-tier-index"),
        ("CrewRoster", "crew-duty-date-index"),
        ("flights", "aircraft-rotation-index")
    ]

    results = {}

    for table_name, index_name in gsis:
        response = cloudwatch.get_metric_statistics(
            Namespace="AWS/DynamoDB",
            MetricName="ConsumedReadCapacityUnits",
            Dimensions=[
                {"Name": "TableName", "Value": table_name},
                {"Name": "GlobalSecondaryIndexName", "Value": index_name}
            ],
            StartTime=datetime.now() - timedelta(hours=1),
            EndTime=datetime.now(),
            Period=300,
            Statistics=["Average", "Maximum", "Sum"]
        )

        results[f"{table_name}.{index_name}"] = response["Datapoints"]

    return results
```

### Performance Targets

| Metric            | Target      | Action if Exceeded                      |
| ----------------- | ----------- | --------------------------------------- |
| Average Latency   | < 50ms      | Investigate query patterns              |
| P99 Latency       | < 100ms     | Check for throttling, increase capacity |
| Consumed Capacity | < 100 RCU/s | Monitor for spikes, adjust capacity     |
| Throttling Events | 0           | Increase provisioned capacity           |
| Table Scans       | 0           | Fix queries to use GSIs                 |

---

## Troubleshooting

### Common Issues

#### 1. GSI Not Found

**Error**: `ValidationException: The table does not have the specified index`

**Solution**:

```bash
cd scripts
python3 create_priority1_gsis.py --table <table_name>
python3 create_priority1_gsis.py --check-status
```

#### 2. High Latency (>100ms)

**Causes**:

- GSI not ACTIVE
- Throttling due to insufficient capacity
- Large result sets without pagination
- Network issues

**Solutions**:

- Verify GSI status
- Check CloudWatch for throttling events
- Implement pagination for large queries
- Use date range filters to limit results

#### 3. Table Scans Detected

**Causes**:

- Not using GSI in query
- Using FilterExpression instead of KeyConditionExpression
- Incorrect GSI key attributes

**Solutions**:

- Verify IndexName parameter is set
- Use KeyConditionExpression for GSI keys
- Check GSI key schema matches query

#### 4. Empty Results

**Causes**:

- Incorrect key format (e.g., date format)
- Data not present in table
- GSI not fully populated

**Solutions**:

- Verify key format matches table schema
- Check data exists in base table
- Wait for GSI to finish backfilling

---

## Related Documentation

### Core Documentation

- [Priority 1 GSIs Overview](../../../scripts/PRIORITY1_GSIS_README.md) - GSI creation and management
- [Database Constants](../src/database/constants.py) - Centralized table and GSI names
- [Structured Output Usage](./STRUCTURED_OUTPUT_USAGE.md) - LangChain structured output guide

### Agent Documentation

- [Guest Experience Agent Implementation](../src/agents/guest_experience/agent.py)
- [Crew Compliance Agent Implementation](../src/agents/crew_compliance/agent.py)
- [Network Agent Implementation](../src/agents/network/agent.py)

### Requirements and Design

- [Requirements Document](../../../.kiro/specs/skymarshal-multi-round-orchestration/requirements.md)
- [Design Document](../../../.kiro/specs/skymarshal-multi-round-orchestration/design.md)
- [Tasks Document](../../../.kiro/specs/skymarshal-multi-round-orchestration/tasks.md)

---

## Next Steps

1. **Create GSIs**: Run `python3 scripts/create_priority1_gsis.py`
2. **Implement Agent Tools**: Follow agent-specific documentation
3. **Test Performance**: Validate query latency meets targets
4. **Monitor Production**: Set up CloudWatch alarms
5. **Iterate**: Optimize based on production metrics

---

## Support

For questions or issues:

1. Check agent-specific documentation for detailed examples
2. Review troubleshooting section above
3. Check CloudWatch metrics for performance issues
4. Consult requirements and design documents for context

---

**Last Updated**: January 31, 2026

**Version**: 1.0

**Status**: Complete - All Priority 1 GSI documentation created
