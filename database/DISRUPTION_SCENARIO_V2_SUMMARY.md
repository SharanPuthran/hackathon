# Disruption Scenario V2 - Summary

## Overview
Updated disruption scenario based on the flowchart showing inbound flight delay causing outbound disruption.

## Scenario Flow

### Day 1 (08:00H Local BKK)
**Inbound Flight: EY117 (BKK → AUH)**
- Aircraft: B787-10 (A6-EYM)
- Scheduled Departure: 2026-02-01 20:00:00 UTC
- Scheduled Arrival at AUH: 2026-02-02 02:00:00 UTC
- **Disruption**: Typhoon at Bangkok causes delay
- Delay scenarios: 2.5 hours, 4 hours, 6.5 hours

### Day 2 (00:00H Local AUH)
**Outbound Flight: EY5293 (AUH → BKK)**
- Aircraft: B787-10 (A6-EYM) - **Same aircraft as inbound**
- Scheduled Departure: 2026-02-02 08:15:00 UTC
- Total Passengers: 346
- **Disruption**: Delayed due to late aircraft arrival from BKK
- Cascading delay: Same duration as inbound delay

## Key Changes from V1

1. **Weather Data**:
   - AUH (Hub): 24 records showing normal operations
   - BKK (Typhoon): 24 records showing severe weather on Day 1, recovery on Days 2-3
   - Total: 48 weather records

2. **Disruption Origin**:
   - V1: Outbound flight disrupted at destination (BKK)
   - V2: Inbound flight disrupted at origin (BKK), causing outbound delay

3. **Aircraft Swap Location**:
   - V1: Swap options at BKK (outstation)
   - V2: Swap options at AUH (hub) - more realistic

4. **Decision Point**:
   - Swap decision made at AUH hub where more aircraft are available
   - Best option: A6-EYN (B787-10) - same type, available at hub, no MEL

## Generated Files

1. **output/weather.csv** (48 records)
   - AUH weather: Normal operations at hub
   - BKK weather: Typhoon conditions causing inbound delay

2. **output/disrupted_passengers_scenario.csv** (346 records)
   - Passengers on outbound flight EY5293
   - 57.8% have connections from BKK
   - 9 social media influencers identified

3. **output/aircraft_swap_options.csv** (4 options)
   - All options at AUH hub or nearby (DXB)
   - A6-EYN: Best option (HIGH feasibility)
   - A6-EYP: Medium option (has MEL)
   - A6-EYA: Medium option (crew issue)
   - A6-EYE: Low option (requires ferry from DXB)

4. **output/inbound_flight_impact.csv** (3 scenarios)
   - Shows how inbound delay cascades to outbound flight
   - Includes passenger impact and cost estimates

## Impact Analysis

### 2.5 Hours Delay
- Inbound arrives: 04:30 UTC
- Outbound departs: 10:45 UTC (2.5h late)
- Passengers impacted: 8
- Cost: ~$800
- **Recommendation**: Wait for aircraft

### 4 Hours Delay
- Inbound arrives: 06:00 UTC
- Outbound departs: 12:15 UTC (4h late)
- Passengers impacted: 71
- Cost: ~$7,100
- **Recommendation**: Consider aircraft swap

### 6.5 Hours Delay
- Inbound arrives: 08:30 UTC
- Outbound departs: 14:45 UTC (6.5h late)
- Passengers impacted: 136
- Requires hotel accommodation
- Cost: ~$40,000+
- **Recommendation**: Aircraft swap highly recommended (A6-EYN)

## Key Insights

1. **Root Cause**: Typhoon at BKK delays inbound flight
2. **Cascading Effect**: Same aircraft needed for outbound causes delay
3. **Hub Advantage**: Aircraft swap at AUH hub is more feasible than at outstation
4. **Weather**: AUH operations normal - disruption is purely aircraft availability
5. **Reputation Risk**: 9 social media influencers require special handling
6. **Best Option**: A6-EYN at AUH - same type, no MEL, crew available, 45 min swap

## Scripts

- **Generator**: `generators/create_disruption_scenario_v2.py`
- **Display**: `show_disruption_scenario_v2.py`

## Usage

```bash
# Generate scenario data
py generators/create_disruption_scenario_v2.py

# Display analysis
py show_disruption_scenario_v2.py
```
