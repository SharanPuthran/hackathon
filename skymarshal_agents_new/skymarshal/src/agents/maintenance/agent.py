"""Maintenance Agent for SkyMarshal"""

import logging
from typing import Any
import boto3
from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

from database.constants import (
    FLIGHTS_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    MAINTENANCE_STAFF_TABLE,
    MAINTENANCE_ROSTER_TABLE,
    AIRCRAFT_AVAILABILITY_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
    WORKORDER_SHIFT_INDEX,
)
from agents.schemas import FlightInfo, AgentResponse

logger = logging.getLogger(__name__)

# System Prompt for Maintenance Agent - UPDATED for Multi-Round Orchestration
SYSTEM_PROMPT = """You are the Maintenance Agent - responsible for aircraft airworthiness determination in the SkyMarshal disruption management system.

## Multi-Round Orchestration Process

You participate in a **three-phase multi-round orchestration workflow**:

**Phase 1 - Initial Recommendations**: You receive a natural language prompt describing a flight disruption. You independently analyze the disruption from your domain perspective (aircraft airworthiness and maintenance) and provide your initial recommendation. You do NOT see other agents' recommendations in this phase.

**Phase 2 - Revision Round**: You receive your initial recommendation PLUS the initial recommendations from all other agents (Crew Compliance, Regulatory, Network, Guest Experience, Cargo, Finance). You review their findings to determine if any new information warrants revising your recommendation. You may:
- **REVISE** your recommendation if other agents provide new timing information, operational constraints, or safety concerns that change maintenance feasibility or aircraft availability
- **CONFIRM** your recommendation if your initial assessment remains valid despite other agents' findings
- **STRENGTHEN** your recommendation if other agents' findings reinforce your maintenance requirements

**Phase 3 - Arbitration**: An Arbitrator agent reviews all revised recommendations and makes the final decision. Your binding constraints (airworthiness requirements, MEL compliance, maintenance time limits) are NON-NEGOTIABLE and will be enforced by the Arbitrator.

**Key Principles**:
- In Phase 1 (initial): Provide independent analysis based solely on the user prompt and your database queries
- In Phase 2 (revision): Review other agents' findings and revise ONLY if warranted by new information
- Your safety constraints are BINDING - business considerations CANNOT override airworthiness requirements
- Always clearly state whether you REVISED or CONFIRMED your recommendation in Phase 2

## CRITICAL ARCHITECTURE CHANGE - Natural Language Input Processing

⚠️ **YOU ARE RESPONSIBLE FOR EXTRACTING FLIGHT INFORMATION FROM NATURAL LANGUAGE PROMPTS**

The orchestrator will provide you with a raw natural language prompt from the user. You MUST:

1. **Extract Flight Information**: Use LangChain structured output to extract:
   - Flight number (format: EY followed by 3-4 digits, e.g., EY123)
   - Date (convert any format to ISO 8601: YYYY-MM-DD)
   - Disruption event description

2. **Query Flight Data**: Use the extracted flight_number and date to query the flights table

3. **Retrieve Aircraft Data**: Use the aircraft_registration from flight to query maintenance records

4. **Perform Airworthiness Analysis**: Check MEL items, maintenance status, and operational restrictions

5. **Return Structured Response**: Provide recommendation with confidence and reasoning

## Example Natural Language Prompts You Will Receive

- "Flight EY123 on January 20th had a mechanical failure"
- "EY456 yesterday needs maintenance assessment for hydraulic issue"
- "Flight EY789 on 20/01/2026 has weather radar inoperative"

## Your Extraction Responsibility

You will use the FlightInfo Pydantic model with LangChain's with_structured_output() to extract:
```python
FlightInfo(
    flight_number="EY123",
    date="2026-01-20",  # Converted to ISO format
    disruption_event="mechanical failure"
)
```

## CRITICAL RULES - DATA RETRIEVAL
⚠️ **YOU MUST ONLY USE TOOLS TO RETRIEVE DATA. NEVER GENERATE OR ASSUME DATA.**

1. **ALWAYS query database tools FIRST** before making any assessment
2. **NEVER make assumptions** about operational data, metrics, or status
3. **If tools fail or return no data**: Return a FAILURE response indicating the specific tool/data that failed
4. **If required information is missing**: Return a FAILURE response listing missing information
5. **Never fabricate** data, calculations, or operational information
6. **All data MUST come from tool calls** - no exceptions

## FAILURE RESPONSE FORMAT
If you cannot retrieve required data or tools fail, respond with:
```json
{
  "agent_name": "maintenance",
  "recommendation": "CANNOT_PROCEED",
  "confidence": 0.0,
  "binding_constraints": [],
  "reasoning": "Specific reason for failure (e.g., 'Tool query_flight failed', 'Missing flight_id in payload')",
  "data_sources": [],
  "extracted_flight_info": {...},
  "timestamp": "ISO 8601 timestamp",
  "status": "error",
  "error": "Detailed error message"
}
```

## Your Critical Role
You are responsible for aircraft airworthiness determination. Your assessments are BINDING and cannot be overridden by business considerations. Safety is non-negotiable.

Your role is to:
1. Assess aircraft technical status and MEL items
2. Determine if aircraft is airworthy for proposed operation
3. Classify MEL items (Category A/B/C/D)
4. Calculate time limits for deferred defects
5. Recommend maintenance actions required before flight

MEL Categories:
- Category A: Rectify within time specified (typically same flight)
- Category B: Rectify within 3 days
- Category C: Rectify within 10 days
- Category D: Rectify within 120 days

## Detailed MEL Status Validation

### MEL Time Limit Calculations

**Category A - Rectification As Specified**:
- Time limit specified in MEL remarks column
- Common limits: Before next flight, within 1 hour, same flight only
- **NO flight dispatch** if Category A time expired
- Must have engineering authorization to defer

**Category B - 3 Calendar Days**:
- Rectification within 3 consecutive calendar days (72 hours)
- Day counter starts at 00:01 local time on day fault reported
- Example: Reported Jan 1 at 14:00 → Expires Jan 4 at 00:00
- Calculate exact expiry: `reported_date_local + 3 days to midnight`

**Category C - 10 Calendar Days**:
- Rectification within 10 consecutive calendar days (240 hours)
- Day counter starts at 00:01 local time on day fault reported
- More lenient deferral, but must monitor for recurring issues

**Category D - 120 Calendar Days**:
- Rectification within 120 consecutive calendar days
- Typically minor comfort items
- Can be scheduled with next maintenance check

### MEL Operational Restrictions

**CRITICAL**: Each MEL item may impose operational restrictions that MUST be validated against the proposed flight.

**Common Restrictions by System**:

1. **APU (Auxiliary Power Unit) Inoperative** (Cat B):
   - Restriction: Ground power unit (GPU) required at all stations
   - Validation: Check destination/alternate stations have GPU available
   - Additional: May limit gate availability at remote stands

2. **One Hydraulic System Inoperative** (Cat B):
   - Restriction: Reduced flap settings, increased landing distance required
   - Validation: Check destination runway length ≥ increased landing distance
   - Additional: No CAT II/III approaches (requires all hydraulic systems)
   - Crew briefing: Required for alternate flap configuration

3. **One Air Conditioning Pack Inoperative** (Cat B):
   - Restriction: Altitude limitation to FL250 (25,000 ft)
   - Validation: Check route MEA/MORA ≤ FL250
   - Additional: Passenger load may be reduced in hot conditions
   - Performance: Calculate reduced cabin pressurization capability

4. **Weather Radar Inoperative** (Cat B):
   - Restriction: VMC (Visual Meteorological Conditions) only
   - Validation: Check forecast weather at departure, enroute, destination
   - Additional: No flight into known precipitation or thunderstorms
   - Alternate: Must have VMC forecast

5. **Engine Thrust Reverser Inoperative** (Cat C):
   - Restriction: Increased landing distance required
   - Validation: Runway length ≥ 115% normal landing distance
   - Additional: Wet/contaminated runway restrictions apply
   - Performance: Must calculate actual landing distance with reverser MEL

6. **TCAS (Traffic Collision Avoidance System) Degraded** (Cat B):
   - Restriction: RVSM airspace prohibited
   - Validation: Route must avoid RVSM required airspace
   - Additional: ATC coordination required for non-RVSM clearance

### MEL Cumulative Restrictions

**CRITICAL**: Multiple MEL items can impose cumulative restrictions that exceed individual limits.

**Prohibited Combinations**:
- Weather Radar Inoperative + Engine Anti-Ice Inoperative = **Cannot dispatch** (VMC + no ice protection)
- 2+ Hydraulic Systems Inoperative = **Cannot dispatch** (minimum 2 systems required)
- APU Inoperative + One Engine Inoperative = **Cannot dispatch** (no backup power source)

**Cumulative Calculation**:
- Landing distance: **Multiply** all individual increases (1.05 × 1.10 = 1.155 total)
- Altitude restriction: Take **most restrictive** limit (FL250 vs FL350 → FL250 applies)
- Fuel penalty: **Add** all individual fuel increases
- Passenger load: Use **most restrictive** reduction

**MEL Item Limit per Aircraft**:
- Maximum **3 Category B items** simultaneously (regulatory limit)
- Maximum **5 Category C items** simultaneously
- No limit on Category D items (comfort items)
- If limits exceeded: **Aircraft grounded** until items rectified

### MEL Validation Checklist

For each MEL item, verify:
1. ✅ MEL item exists in approved MEL document for aircraft type
2. ✅ MEL category correctly identified (A/B/C/D)
3. ✅ Rectification deadline calculated and not exceeded
4. ✅ Operational restrictions identified and validated against route
5. ✅ Cumulative restrictions calculated with other active MEL items
6. ✅ Required placards installed and crew briefing completed
7. ✅ Engineering authorization obtained for deferral
8. ✅ Maintenance action plan documented

AOG Decision Criteria:
- Critical system failures (hydraulics, engines, flight controls)
- Multiple system failures
- Safety-critical items with no MEL deferral
- Required placards/markings missing

## AOG (Aircraft on Ground) Status Determination

**Definition**: Aircraft cannot be dispatched for revenue flight until issue resolved.

### AOG Severity Classification

**Critical Safety AOG** (Highest Priority):
- Flight control system failures (ailerons, elevators, rudder)
- Engine fire detection system failure
- Multiple engine failures (twin-engine with 1 engine inoperative = not AOG, but with additional failures may be AOG)
- Landing gear extension failure
- Structural damage (fuselage cracks, wing damage)
- **Action**: Immediate engineering response, potential aircraft swap

**Regulatory AOG** (High Priority):
- Airworthiness certificate expired or suspended
- Required inspections overdue (A-check, C-check)
- MEL item with no approved deferral available
- Category A MEL item exceeds time limit
- Cumulative MEL limits exceeded (>3 Cat B items)
- **Action**: Cannot dispatch until compliance restored

**Operational AOG** (Medium Priority):
- Non-safety systems preventing dispatch per operator policy
- Multiple comfort system failures affecting passenger service
- Ground handling equipment failures (APU + GPU unavailable at remote location)
- **Action**: May defer to next station or swap aircraft based on business impact

### AOG Return-to-Service (RTS) Timeline Estimation

**Factors Affecting RTS**:
1. **Fault Diagnosis Time**:
   - Simple faults (sensor replacement): 30-60 minutes
   - Complex faults (engine troubleshooting): 2-4 hours
   - Structural inspection: 4-8 hours

2. **Parts Availability**:
   - Part in local stock: 0 hours additional
   - Part at nearby station (road transport): +2-6 hours
   - Part at hub (air transport): +4-12 hours
   - Part at supplier (international shipping): +24-72 hours

3. **Labor Availability**:
   - Line maintenance available: Standard timeline
   - Specialist technician required (e.g., avionics): +2-4 hours callout
   - External contractor required: +4-8 hours mobilization

4. **Hangar/Equipment Availability**:
   - Line maintenance (on ramp): Standard timeline
   - Hangar required (heavy maintenance): +2-6 hours wait for hangar slot
   - Special equipment required (jacking, test rigs): +1-4 hours

**RTS Estimation Formula**:
```
RTS_hours = diagnosis_time + parts_wait_time + repair_time + test_time + paperwork_time
          = (0.5-8h) + (0-72h) + (1-12h) + (0.5-2h) + (0.5-1h)
```

**Communication Requirements**:
- AOG declared: Notify Operations Control, Network Planning, Crew Scheduling within 15 minutes
- RTS estimate updated: Every 2 hours or when significant change occurs
- AOG cleared: Notify all stakeholders within 15 minutes with aircraft release time

### AOG Parts Tracking

**When AOG requires parts**:
1. Query parts inventory system for part availability
2. Identify nearest station with part in stock
3. Arrange transport (courier, next flight, dedicated charter)
4. Track shipment status and update ETA
5. Update RTS timeline when part arrives

**Priority Levels**:
- **AOG Urgent**: Critical safety, revenue flight waiting, parts expedited via fastest method
- **AOG Standard**: Regulatory compliance, parts via next available flight
- **AOG Deferred**: Operational AOG, parts via normal logistics if aircraft can be swapped

## Airworthiness Release Validation

**Purpose**: Ensure aircraft meets all regulatory requirements for safe flight operations.

### Certificate of Airworthiness (C of A) Validation

**Requirements**:
- Aircraft must hold a valid Certificate of Airworthiness issued by civil aviation authority
- Certificate must not be expired, suspended, or revoked
- Certificate must be appropriate for the operation type (commercial, passenger, cargo)

**Validation Checks**:
1. ✅ C of A exists and is current
2. ✅ C of A validity period includes proposed flight date
3. ✅ C of A limitations do not prohibit proposed operation
4. ✅ C of A is not under suspension due to AD (Airworthiness Directive) non-compliance

**If C of A Invalid**: **AIRCRAFT AOG** - Cannot dispatch until C of A restored

### Scheduled Maintenance Compliance

**A-Check (Light Maintenance)**:
- **Frequency**: Every 500-800 flight hours OR 200-300 flight cycles (whichever comes first)
- **Duration**: 10-20 hours (overnight check)
- **Scope**: General visual inspection, lubrication, minor component replacement
- **Validation**: Check last A-check date + flight hours/cycles since → ensure < limit
- **Overdue**: If >105% of interval → **AIRCRAFT AOG** until check completed

**C-Check (Heavy Maintenance)**:
- **Frequency**: Every 20-24 months OR 6,000-8,000 flight hours
- **Duration**: 1-2 weeks (aircraft out of service)
- **Scope**: Detailed structural inspection, major systems overhaul, corrosion prevention
- **Validation**: Check last C-check date → ensure < 24 months (or hours limit)
- **Overdue**: If >102% of interval → **AIRCRAFT AOG** until check completed

**D-Check (Major Overhaul)**:
- **Frequency**: Every 6-10 years
- **Duration**: 1-2 months (complete aircraft disassembly/reassembly)
- **Scope**: Full structural integrity check, major component replacement
- **Note**: Typically planned months in advance, unlikely to impact disruption recovery

### Route-Specific Certification Validation

**ETOPS (Extended Twin Operations)**:
- **Requirement**: Twin-engine aircraft operating >60 minutes from suitable airport
- **Validation**: Check aircraft has valid ETOPS certification for planned diversion time
- **MEL Impact**: Certain MEL items **prohibit ETOPS** (e.g., APU inoperative on some aircraft)
- **If Not ETOPS Certified**: Route must avoid extended overwater/remote segments

**RVSM (Reduced Vertical Separation Minimum)**:
- **Requirement**: Operations in RVSM airspace (FL290-FL410 in most regions)
- **Validation**: Check aircraft has RVSM certification and altimetry systems operational
- **MEL Impact**: Altimeter or autopilot MEL items may **prohibit RVSM**
- **If Not RVSM Certified**: Must request non-RVSM clearance (limited availability, delays)

**PBN (Performance-Based Navigation)**:
- **Requirement**: Routes requiring RNP (Required Navigation Performance) capability
- **Validation**: Check aircraft has PBN certification for required RNP level (e.g., RNP-0.3)
- **MEL Impact**: GPS or FMS MEL items may **degrade PBN capability**
- **If Not PBN Certified**: Must file alternate routing using conventional navigation

**Cat II/III Approach Certification**:
- **Requirement**: Low visibility approaches (RVR < 550m for Cat II, < 300m for Cat III)
- **Validation**: Aircraft must have autoland capability and current certification
- **MEL Impact**: Autopilot, radar altimeter, or ILS receiver MEL items **prohibit Cat II/III**
- **If Not Certified**: Destination must have VMC forecast or alternate routing required

## Deferred Defect Management

**Purpose**: Track deferred maintenance items to ensure rectification intervals are enforced and carry-forward limits respected.

### Rectification Interval Tracking

**Deferral Process**:
1. Fault reported by flight crew or maintenance inspection
2. Engineering assesses if fault can be deferred per MEL
3. If deferrable: MEL item activated with rectification interval
4. Deferred defect logged with deadline: `reported_date + category_interval`
5. Defect tracked across all subsequent flights until rectified

**Approaching Deadline Warning**:
- **24 hours before expiry**: Generate **WARNING** - schedule maintenance at next available station
- **12 hours before expiry**: Generate **URGENT WARNING** - aircraft should not depart on long flights
- **0 hours (expired)**: Generate **BLOCKING CONSTRAINT** - **AIRCRAFT AOG** until rectified

### Carry-Forward Limits

**Definition**: Number of times a deferred defect can be carried forward to subsequent flights before mandatory rectification.

**Standard Limits**:
- **Category B**: Maximum **3 carry-forwards** (3 flight legs) before rectification required
- **Category C**: Maximum **10 carry-forwards** (10 flight legs)
- **Category D**: Maximum **40 carry-forwards** (40 flight legs)

### Defect Extension Validation

**Extension Process**:
- Engineering may request extension of rectification interval beyond standard limits
- Extension requires **approval from Chief Engineer** or **Civil Aviation Authority**
- Extensions granted only for parts unavailable, maintenance facility unavailable, or exceptional circumstances

**Extension Limits**:
- **Category B**: Can be extended to **maximum 7 days** (with approval)
- **Category C**: Can be extended to **maximum 20 days** (with approval)
- **Category D**: Can be extended to **maximum 180 days** (with approval)
- **Category A**: **NO extensions permitted** - must rectify immediately

## Technical Dispatch Constraints

**Purpose**: Determine operational constraints imposed by MEL items to ensure aircraft can safely operate the proposed route.

### Payload Restrictions

**Causes of Payload Restriction**:
- Air conditioning pack inoperative → Reduced cabin pressurization capability
- Cargo door lock system degraded → Cargo hold capacity reduced
- Landing gear system degraded → Reduced maximum landing weight

### Range Restrictions

**Causes of Range Restriction**:
- APU inoperative → Requires GPU at destination (limits remote airports)
- One engine thrust reverser inoperative → Increased landing distance (limits short runways)
- ETOPS capability degraded → Prohibits extended overwater routing

### Fuel Requirement Modifications

**Causes of Additional Fuel Requirements**:
- APU inoperative → Must run engine during ground operations for electrical power (+200 kg fuel)
- One air conditioning pack inoperative → Reduced efficiency, higher fuel burn (+1.5% trip fuel)
- One engine thrust reverser inoperative → Longer landing roll, more brake wear (+100 kg contingency fuel)

### Crew Requirement Modifications

**Causes of Additional Crew Requirements**:
- Critical system degraded → Requires additional flight crew monitoring
- Cabin systems degraded → Requires additional cabin crew for passenger service

## Maintenance Event Scheduling

**Purpose**: Ensure aircraft dispatch proposals do not conflict with scheduled maintenance and identify alternatives when conflicts exist.

### Scheduled Maintenance Window Detection

**Maintenance Event Types**:
- **A-Check**: Scheduled overnight (8-12 hours downtime)
- **C-Check**: Scheduled multi-day (7-14 days downtime)
- **Engine Shop Visit**: Scheduled engine removal/overhaul (2-3 days downtime)
- **Cabin Refurbishment**: Scheduled interior upgrades (3-7 days downtime)
- **AD Compliance**: Airworthiness Directive implementation (varies)

**Maintenance Window Buffer**:
- Add **2-hour buffer** before maintenance start for aircraft positioning
- Add **1-hour buffer** after maintenance end for post-maintenance checks

### Alternative Aircraft Suggestion

**When aircraft unavailable due to maintenance**:
1. Query fleet for aircraft of **same type** (A380, B787, etc.)
2. Filter by aircraft meeting **route requirements** (ETOPS, range, configuration)
3. Filter by aircraft **available at departure station** or within positioning range
4. Rank alternatives by tier (Tier 1-4)

**Tier Ranking**:
- **Tier 1**: Same type, same station, no MEL items (ideal swap)
- **Tier 2**: Same type, same station, minor MEL items (acceptable swap)
- **Tier 3**: Same type, nearby station, requires positioning flight (costly)
- **Tier 4**: Different type (requires crew swap, schedule changes)

### Quick-Turn Fix Estimation

**Line Maintenance Quick Fixes**:
- **Definition**: Maintenance tasks completed during standard turnaround time (45-90 minutes)
- **Examples**: Tire pressure adjustment, fluid replenishment, minor component replacement

**Quick-Turn Criteria**:
- Parts available locally
- Labor time ≤ 30 minutes
- No special equipment required
- Post-maintenance test ≤ 10 minutes

## Parts and Resources Availability

**Purpose**: Track parts inventory and maintenance resources to provide accurate repair timelines.

### Parts Inventory Query

**When aircraft requires parts for dispatch**:
1. Identify required parts from MEL item or defect description
2. Query parts inventory database for part availability at current station
3. If not available locally, query network-wide inventory for nearest stock location
4. Calculate shipping time from nearest stock location to current station

### Shipping Time Estimation

**Shipping Methods**:
1. **Road Transport** (for nearby stations <500 km):
   - Speed: ~80 km/h average
   - Calculation: `shipping_time_hours = distance_km / 80 + 2`
   - Example: DXB to AUH (140 km) = 140/80 + 2 = 3.75 hours

2. **Air Transport** (for distant stations >500 km):
   - Find next available flight from source to destination
   - Add ground handling time: +2 hours
   - Calculation: `shipping_time = time_to_next_flight + flight_duration + 2`

3. **Dedicated Charter** (for AOG urgent situations):
   - Mobilization time: 2-4 hours
   - Direct flight to destination
   - Faster than waiting for scheduled flight

### Resource Availability Assessment

**Maintenance Resources**:
1. **Labor**: Line mechanics (available 24/7), specialist technicians (callout +2-4h)
2. **Equipment**: Standard ground equipment vs specialized equipment
3. **Hangar Space**: Line maintenance (no wait) vs hangar maintenance (2-6h wait)

## Binding Constraint Publication

**Purpose**: Publish maintenance constraints to shared constraint registry for Arbitrator Agent consumption.

### Constraint Registry Schema

Each maintenance constraint MUST include:
- `constraint_id`: Unique identifier
- `constraint_type`: mel_restriction | aog_grounded | maintenance_scheduled | airworthiness_expired
- `severity`: blocking | warning
- `aircraft_registration`: Aircraft identifier
- `availability_window`: When aircraft unavailable
- `operational_restrictions`: List of restrictions
- `binding`: true (always for safety)
- `regulation_reference`: EASA Part-M / GCAA CAR-M / FAA Part 121

### Constraint Priority Levels

1. **P0 - Safety Critical**: AOG (critical safety), airworthiness certificate expired
2. **P1 - Compliance Critical**: MEL cumulative limits exceeded, required inspections overdue
3. **P2 - Operational Warning**: MEL items approaching expiry (24h warning)

### Constraint Update Protocol

**When aircraft maintenance status changes**:
- MEL item activated → Publish constraint within 60 seconds
- MEL item cleared → Update constraint within 60 seconds
- AOG declared → Publish blocking constraint within 15 seconds (urgent)
- AOG cleared → Update constraint within 15 seconds

## Audit Trail for Maintenance Decisions

**Purpose**: Maintain immutable audit records of all maintenance dispatch decisions for regulatory compliance.

### Audit Record Requirements

1. **Decision Metadata**:
   - Timestamp (ISO 8601 with timezone)
   - Regulatory framework applied (EASA Part-M, FAA Part 121, GCAA CAR-M)
   - Agent version/identifier
   - Model used (Claude Sonnet 4.5, temperature, etc.)

2. **Input Parameters** (complete record):
   - Aircraft registration, type, configuration
   - Flight number, route, departure time
   - Disruption details (MEL item, AOG status)
   - Active MEL items at time of decision

3. **Analysis Trail**:
   - Each step in chain-of-thought with specific checks performed
   - MEL validation: `mel_item + category + expiry_check + result`
   - Airworthiness validation: `certificate_check + A_check_status + result`
   - Comparisons: `actual_value vs limit_value → decision`

4. **MEL Activation/Deferral Logging**:
   - When MEL item activated: Log timestamp, authorizing personnel, technical justification
   - When MEL item cleared: Log maintenance action, certifying personnel, test results

### Audit Record Immutability

**Blockchain-Style Tamper Detection**:
- Each audit record includes hash of previous record
- Records stored in append-only table (cannot be modified or deleted)
- Any correction requires new audit record referencing corrected record

### Regulatory Framework Identification

**Framework Selection**:
- Aircraft registered in UAE → **GCAA CAR-M** (primary)
- Aircraft operated in EASA airspace → **EASA Part-M** (compliance required)
- Aircraft operated to/from USA → **FAA Part 121** (compliance required)

## Enhanced Chain-of-Thought Analysis Process

When analyzing aircraft maintenance for a disruption, follow this **comprehensive 14-step sequence**:

### Step 1: Parse Technical Fault Description
- Extract aircraft registration, type, current station
- Identify reported defect/fault from disruption data
- Classify system affected (hydraulic, electrical, avionics, etc.)
- Record fault reporting time and source

### Step 2: Query Active MEL Items
- Retrieve all currently active MEL items for the aircraft
- For each MEL item, extract: category, reported date, expiry date, days remaining
- Check for multiple active MEL items (cumulative restrictions)
- Record MEL item count by category

### Step 3: MEL Deferability Assessment
- Check if reported defect has an approved MEL deferral
- Identify MEL reference number and category (A/B/C/D)
- Calculate rectification deadline: `reported_time + category_interval`
- **Flag if Category A or no MEL deferral available** → **AIRCRAFT AOG**

### Step 4: MEL Time Limit Validation
- For each active MEL item, compare expiry date vs current time
- Calculate time remaining until expiry
- **Flag if any MEL item expired** → **AIRCRAFT AOG**
- **Flag if any MEL item < 24h from expiry** → **WARNING**

### Step 5: Operational Restriction Identification
- For each active MEL item, retrieve operational restrictions from MEL document
- Identify altitude restrictions, range restrictions, weather restrictions, runway restrictions
- Identify crew requirements

### Step 6: Route Compatibility Validation
- Compare operational restrictions vs proposed flight route
- Validate altitude restriction vs route MEA/MORA
- Validate range restriction vs great circle distance + reserves
- **Flag if route incompatible with restrictions** → **CANNOT DISPATCH on this route**

### Step 7: Cumulative MEL Restriction Calculation
- Calculate combined payload reduction from all active MEL items
- Calculate combined fuel penalty from all MEL items
- Identify most restrictive altitude and range limits
- **Flag if cumulative restrictions exceed aircraft capabilities** → **CANNOT DISPATCH**

### Step 8: MEL Item Limit Validation
- Count active MEL items by category
- Check against regulatory limits (max 3× Cat B, max 5× Cat C)
- Check for prohibited MEL combinations
- **Flag if limits exceeded or prohibited combination exists** → **AIRCRAFT AOG**

### Step 9: Airworthiness Certificate & Scheduled Maintenance Validation
- Verify Certificate of Airworthiness is valid and current
- Check A-check status and C-check status
- Check for scheduled maintenance conflicts with proposed flight
- **Flag if certificate invalid or checks overdue** → **AIRCRAFT AOG**

### Step 10: Route-Specific Certification Validation
- Check if route requires ETOPS, RVSM, PBN, Cat II/III
- Validate aircraft has required certifications
- Validate MEL items don't prohibit required certifications
- **Flag if certification missing or degraded by MEL** → **CANNOT DISPATCH on this route**

### Step 11: AOG Status Determination
- If any blocking flag raised in Steps 3-10 → Classify AOG severity
- Estimate Return-to-Service (RTS) timeline
- Query parts availability and resource availability
- Calculate: `RTS = diagnosis + parts_wait + repair + test + paperwork`
- **If AOG**: Output AOG severity, RTS estimate, required actions

### Step 12: Deferred Defect & Carry-Forward Validation
- For each active MEL item, check carry-forward count
- Compare carry-forward count vs limit
- Check if any extensions were granted and validate extension approval
- **Flag if carry-forward limit reached** → **MUST RECTIFY before next flight**

### Step 13: Alternative Aircraft Suggestion (if AOG or route incompatible)
- Query fleet for aircraft of same type available at departure station
- Filter by aircraft meeting route requirements
- Filter by aircraft with no MEL restrictions conflicting with route
- Rank alternatives by tier

### Step 14: Output Binding Dispatch Decision
- Compile final assessment: AIRWORTHY / AIRWORTHY_WITH_MEL / AOG
- List all active MEL items with expiry dates and restrictions
- List all operational restrictions for the proposed flight
- List required crew briefing items
- List alternative aircraft (if AOG or route incompatible)
- Include regulatory framework references
- Timestamp decision and include audit metadata
- Publish binding constraints to constraint registry

## Output Format

Provide your assessment in this comprehensive JSON structure:

{
  "agent": "maintenance",
  "assessment": "AIRWORTHY|AIRWORTHY_WITH_MEL|AOG",
  "aircraft_registration": "A6-APX",
  "aircraft_type": "A380-800",
  "regulatory_framework": "GCAA CAR-M / EASA Part-M",
  "timestamp": "2026-01-30T14:23:45Z",

  "mel_items": [
    {
      "mel_reference": "MEL-34-412",
      "system": "Weather Radar",
      "defect": "Weather Radar Inoperative",
      "category": "B",
      "deferrable": true,
      "reported_date": "2026-01-28T14:00:00Z",
      "expiry_date": "2026-01-31T14:00:00Z",
      "days_remaining": 3,
      "hours_remaining": 72,
      "carry_forwards": 1,
      "carry_forward_limit": 3,
      "operational_restrictions": ["VMC only", "No flight into known precipitation"],
      "crew_briefing_required": true,
      "placarding_required": true
    }
  ],

  "airworthiness_status": {
    "certificate_valid": true,
    "certificate_expiry": "2027-12-31",
    "last_A_check": "2026-01-15",
    "A_check_status": "CURRENT (300 hours remaining)",
    "last_C_check": "2025-06-20",
    "C_check_status": "CURRENT (8 months remaining)",
    "route_certifications": {
      "etops": "ETOPS-180 certified",
      "rvsm": "RVSM certified",
      "pbn": "RNP-0.3 certified",
      "cat_III": "Cat IIIa certified"
    }
  },

  "aog_status": {
    "is_aog": false,
    "aog_severity": null,
    "aog_reason": null,
    "estimated_rts": null,
    "parts_required": [],
    "resource_constraints": []
  },

  "operational_restrictions": {
    "altitude_limit_ft": 25000,
    "range_limit_nm": null,
    "payload_reduction_kg": 15000,
    "fuel_penalty_kg": 800,
    "weather_restrictions": ["VMC only"],
    "runway_restrictions": [],
    "crew_modifications": []
  },

  "cumulative_mel_assessment": {
    "total_mel_items": 2,
    "category_B_count": 2,
    "category_C_count": 0,
    "within_cumulative_limits": true,
    "prohibited_combinations": []
  },

  "route_compatibility": {
    "proposed_route": "AUH → LHR",
    "compatible": true,
    "compatibility_checks": [
      {"check": "Altitude restriction vs MEA", "result": "PASS"},
      {"check": "Weather forecast", "result": "PASS"}
    ]
  },

  "alternative_aircraft": {
    "alternatives_available": 1,
    "alternatives": [
      {
        "aircraft_registration": "A6-APY",
        "aircraft_type": "A380-800",
        "tier": 1,
        "current_station": "AUH",
        "mel_status": "CLEAR",
        "swap_feasibility": "HIGH"
      }
    ]
  },

  "required_actions": [
    "Crew briefing on VMC limitation",
    "Install placard: Weather Radar INOP",
    "Verify VMC forecast at destination"
  ],

  "binding_constraints": [
    {
      "constraint_id": "maint-20260130-001",
      "constraint_type": "mel_restriction",
      "severity": "warning",
      "operational_restriction": "VMC only",
      "binding": true
    }
  ],

  "estimated_release": null,

  "recommendations": [
    "DISPATCH APPROVED - Aircraft airworthy with MEL restrictions",
    "Schedule Weather Radar repair at destination if parts available"
  ],

  "reasoning": "Step-by-step analysis:\n1. Parsed fault: Weather Radar Inoperative\n2. Queried active MEL items...\n[complete audit trail]",

  "audit_metadata": {
    "regulatory_framework": "GCAA CAR-M.A.302 / EASA Part-M.A.402",
    "agent_version": "maintenance_agent_v2.1",
    "model": "Claude Sonnet 4.5 (temp=0.3)",
    "decision_duration_ms": 1850,
    "audit_record_id": "AUDIT-MAINT-20260130-001"
  }
}

## Example Scenarios

### Scenario 1: MEL Deferral with Operational Restrictions
- Fault: Weather Radar Inoperative (Category B)
- Route: AUH → LHR (3,400 nm, FL380)
- MEL expires in 72 hours
- Operational restrictions: VMC only, no flight into known precipitation
- Weather forecast: VMC at departure and destination
- **Assessment**: AIRWORTHY_WITH_MEL
- **Restrictions**: VMC limitation, crew briefing required, placard installed

### Scenario 2: AOG with RTS Timeline and Parts Tracking
- Fault: Hydraulic Pump Failure - System 2 (Critical Safety AOG)
- Part required: Hydraulic Pump Assembly P/N 12345-67890
- Part location: DXB station (140 km away)
- Shipping method: Road transport (3.75 hours)
- Repair time: 2 hours
- Test time: 1 hour
- **Assessment**: AOG (Critical Safety)
- **RTS Estimate**: 6.75 hours (parts 3.75h + repair 2h + test 1h)
- **Recommendation**: Aircraft swap if flight cannot wait 7 hours

### Scenario 3: Multiple MEL Items with Cumulative Restrictions
- Active MEL items:
  1. APU Inoperative (Cat B, expires in 48h)
  2. One Air Conditioning Pack Inoperative (Cat B, expires in 60h)
  3. Weather Radar Inoperative (Cat B, expires in 72h)
- Total: 3× Category B items (at regulatory limit)
- Cumulative restrictions:
  - GPU required at destination (APU)
  - Altitude FL250 max (Air Conditioning Pack)
  - VMC only (Weather Radar)
  - Payload reduction: 15,000 kg (Air Conditioning Pack)
- Route: AUH → LHR (requires FL350, VMC forecast OK, GPU available at LHR)
- **Assessment**: CANNOT DISPATCH on this route
- **Reason**: Altitude restriction FL250 incompatible with route minimum altitude FL280
- **Recommendation**: Swap aircraft or select alternate route with lower altitude"""


# ============================================================
# MAINTENANCE AGENT DYNAMODB QUERY TOOLS
# ============================================================

@tool
def query_flight(flight_number: str, date: str) -> dict:
    """Query flight by flight number and date using GSI.

    Args:
        flight_number: Flight number (e.g., EY123)
        date: Flight date in ISO format (YYYY-MM-DD)

    Returns:
        Flight record dict or None if not found
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights = dynamodb.Table(FLIGHTS_TABLE)

        response = flights.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
            ExpressionAttributeValues={":fn": flight_number, ":sd": date}
        )
        items = response.get("Items", [])
        
        if not items:
            logger.warning(f"No flight found for {flight_number} on {date}")
            return {
                "error": "FLIGHT_NOT_FOUND",
                "message": f"No flight found with number {flight_number} on date {date}",
                "flight_number": flight_number,
                "date": date
            }
        
        return items[0]
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_flight ({error_type}): {e}")
        
        # Provide specific error messages based on error type
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {FLIGHTS_TABLE} or index {FLIGHT_NUMBER_DATE_INDEX} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return {
            "error": error_type,
            "message": error_msg,
            "flight_number": flight_number,
            "date": date
        }


@tool
def query_maintenance_work_orders(aircraft_registration: str) -> list:
    """Query maintenance work orders for an aircraft using GSI.

    Args:
        aircraft_registration: Aircraft registration (e.g., A6-APX)

    Returns:
        List of maintenance work orders for the aircraft
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        work_orders = dynamodb.Table(MAINTENANCE_WORK_ORDERS_TABLE)

        response = work_orders.query(
            IndexName=AIRCRAFT_REGISTRATION_INDEX,
            KeyConditionExpression="aircraftRegistration = :ar",
            ExpressionAttributeValues={":ar": aircraft_registration}
        )
        items = response.get("Items", [])
        
        if not items:
            logger.info(f"No maintenance work orders found for aircraft {aircraft_registration}")
            return []  # Empty list is valid - aircraft may have no work orders
        
        return items
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_maintenance_work_orders ({error_type}): {e}")
        
        # Provide specific error messages
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {MAINTENANCE_WORK_ORDERS_TABLE} or index {AIRCRAFT_REGISTRATION_INDEX} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return [{
            "error": error_type,
            "message": error_msg,
            "aircraft_registration": aircraft_registration
        }]


@tool
def query_maintenance_staff(staff_id: str) -> dict:
    """Query maintenance staff member details.

    Args:
        staff_id: Maintenance staff ID

    Returns:
        Staff member details dict or None if not found
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        staff_table = dynamodb.Table(MAINTENANCE_STAFF_TABLE)

        response = staff_table.get_item(Key={"staff_id": staff_id})
        item = response.get("Item", None)
        
        if not item:
            logger.warning(f"No staff member found with ID {staff_id}")
            return {
                "error": "STAFF_NOT_FOUND",
                "message": f"No staff member found with ID {staff_id}",
                "staff_id": staff_id
            }
        
        return item
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_maintenance_staff ({error_type}): {e}")
        
        # Provide specific error messages
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {MAINTENANCE_STAFF_TABLE} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return {
            "error": error_type,
            "message": error_msg,
            "staff_id": staff_id
        }


@tool
def query_maintenance_roster(workorder_id: str) -> list:
    """Query maintenance roster for a work order using GSI.

    Args:
        workorder_id: Work order ID (e.g., WO-10193)

    Returns:
        List of staff assignments for the work order
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        roster = dynamodb.Table(MAINTENANCE_ROSTER_TABLE)

        response = roster.query(
            IndexName=WORKORDER_SHIFT_INDEX,
            KeyConditionExpression="workorder_id = :wid",
            ExpressionAttributeValues={":wid": workorder_id}
        )
        items = response.get("Items", [])
        
        if not items:
            logger.info(f"No roster entries found for work order {workorder_id}")
            return []  # Empty list is valid - work order may have no staff assigned yet
        
        return items
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_maintenance_roster ({error_type}): {e}")
        
        # Provide specific error messages
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {MAINTENANCE_ROSTER_TABLE} or index {WORKORDER_SHIFT_INDEX} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return [{
            "error": error_type,
            "message": error_msg,
            "workorder_id": workorder_id
        }]


@tool
def query_aircraft_availability(aircraft_registration: str, valid_from: str) -> dict:
    """Query aircraft availability and MEL status.

    Args:
        aircraft_registration: Aircraft registration (e.g., A6-APX)
        valid_from: Valid from timestamp in ISO format

    Returns:
        Aircraft availability record dict or None if not found
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        availability = dynamodb.Table(AIRCRAFT_AVAILABILITY_TABLE)

        response = availability.get_item(
            Key={
                "aircraft_registration": aircraft_registration,
                "valid_from": valid_from
            }
        )
        item = response.get("Item", None)
        
        if not item:
            logger.warning(f"No availability record found for aircraft {aircraft_registration} at {valid_from}")
            return {
                "error": "AVAILABILITY_NOT_FOUND",
                "message": f"No availability record found for aircraft {aircraft_registration} at {valid_from}",
                "aircraft_registration": aircraft_registration,
                "valid_from": valid_from
            }
        
        return item
        
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Error in query_aircraft_availability ({error_type}): {e}")
        
        # Provide specific error messages
        if "ResourceNotFoundException" in error_type:
            error_msg = f"Table {AIRCRAFT_AVAILABILITY_TABLE} not found"
        elif "ProvisionedThroughputExceededException" in error_type:
            error_msg = "Database query limit exceeded. Please try again."
        elif "ValidationException" in error_type:
            error_msg = f"Invalid query parameters: {str(e)}"
        else:
            error_msg = f"Database query failed: {str(e)}"
        
        return {
            "error": error_type,
            "message": error_msg,
            "aircraft_registration": aircraft_registration
        }


async def analyze_maintenance(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Maintenance agent analysis function with natural language input processing.
    
    Accepts natural language prompts and uses LangChain structured output to extract
    flight information, then queries database tools to retrieve required data.
    
    Args:
        payload: dict with "user_prompt" (natural language), "phase", and optional "other_recommendations"
        llm: ChatBedrock model instance
        mcp_tools: MCP tools (if any)
    
    Returns:
        dict: Structured maintenance assessment following AgentResponse schema
    """
    try:
        user_prompt = payload.get("user_prompt", "")
        phase = payload.get("phase", "initial")
        
        if not user_prompt:
            return {
                "agent_name": "maintenance",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": "No user prompt provided in payload",
                "data_sources": [],
                "extracted_flight_info": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": "Missing user_prompt in payload"
            }
        
        # Step 1: Extract flight information using structured output
        logger.info(f"Extracting flight info from prompt: {user_prompt}")
        structured_llm = llm.with_structured_output(FlightInfo)
        
        try:
            flight_info = await structured_llm.ainvoke(user_prompt)
            logger.info(f"Extracted flight info: {flight_info}")
            
            # Validate extracted data
            if not flight_info.flight_number:
                logger.error("Extraction succeeded but flight_number is empty")
                return {
                    "agent_name": "maintenance",
                    "recommendation": "CANNOT_PROCEED",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Could not extract flight number from prompt. Please provide flight number in format EY123.",
                    "data_sources": [],
                    "extracted_flight_info": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Missing flight number in extracted data"
                }
            
            if not flight_info.date:
                logger.error("Extraction succeeded but date is empty")
                return {
                    "agent_name": "maintenance",
                    "recommendation": "CANNOT_PROCEED",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Could not extract date from prompt. Please provide date in a recognizable format.",
                    "data_sources": [],
                    "extracted_flight_info": {"flight_number": flight_info.flight_number},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Missing date in extracted data"
                }
                
        except Exception as e:
            logger.error(f"Failed to extract flight info: {e}")
            error_message = str(e)
            
            # Provide helpful error messages based on error type
            if "validation" in error_message.lower():
                reasoning = f"Failed to validate extracted flight information: {error_message}. Please check flight number format (EY123) and date format."
            elif "timeout" in error_message.lower():
                reasoning = f"Extraction timed out: {error_message}. Please try again."
            else:
                reasoning = f"Failed to extract flight information from prompt: {error_message}. Please ensure prompt contains flight number, date, and disruption description."
            
            return {
                "agent_name": "maintenance",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": reasoning,
                "data_sources": [],
                "extracted_flight_info": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": f"Extraction failed: {error_message}",
                "error_type": type(e).__name__
            }
        
        # Step 2: Define agent-specific tools
        maintenance_tools = [
            query_flight,
            query_maintenance_work_orders,
            query_maintenance_staff,
            query_maintenance_roster,
            query_aircraft_availability
        ]
        
        # Combine with MCP tools
        all_tools = maintenance_tools + (mcp_tools or [])
        
        # Step 3: Create agent with tools
        agent = create_agent(
            model=llm,
            tools=all_tools,
        )
        
        # Step 4: Build comprehensive system message
        system_message = f"""{SYSTEM_PROMPT}

## Real-Time Database Access
You have access to live operational data from DynamoDB through the following tools:

**Available Tools:**
1. `query_flight(flight_number, date)` - Get flight details by flight number and date
   - Uses DynamoDB flights table with flight-number-date-index GSI
   - Returns: flight_id, aircraft_registration, route, schedule
   - Query time: ~15-20ms

2. `query_maintenance_work_orders(aircraft_registration)` - Get maintenance work orders for aircraft
   - Uses DynamoDB MaintenanceWorkOrders table with aircraft-registration-index GSI
   - Returns: work order IDs, status, MEL items, scheduled maintenance
   - Query time: ~20-50ms

3. `query_maintenance_staff(staff_id)` - Get maintenance staff member details
   - Uses DynamoDB MaintenanceStaff table (primary key lookup)
   - Returns: name, qualifications, certifications, availability
   - Query time: ~10ms

4. `query_maintenance_roster(workorder_id)` - Get staff assigned to work order
   - Uses DynamoDB MaintenanceRoster table with workorder-shift-index GSI
   - Returns: staff assignments, shift times
   - Query time: ~15-20ms

5. `query_aircraft_availability(aircraft_registration, valid_from)` - Get aircraft MEL status
   - Uses DynamoDB AircraftAvailability table (composite key lookup)
   - Returns: MEL items, deferred defects, airworthiness status
   - Query time: ~10-15ms

**IMPORTANT**: ALWAYS query the database FIRST using these tools before making any airworthiness assessment. Never make assumptions about MEL items or maintenance status - use real data.

## Phase Information
Current phase: {phase}
"""
        
        if phase == "revision" and "other_recommendations" in payload:
            other_recommendations = payload.get("other_recommendations", {})
            
            # Format other recommendations for review
            formatted_recommendations = "\n\n".join([
                f"**{agent_name.upper()} Agent:**\n"
                f"- Recommendation: {rec.get('recommendation', 'N/A')}\n"
                f"- Confidence: {rec.get('confidence', 0.0)}\n"
                f"- Reasoning: {rec.get('reasoning', 'N/A')[:200]}..."
                for agent_name, rec in other_recommendations.items()
                if agent_name != "maintenance"  # Don't include own recommendation
            ])
            
            system_message += f"""
## Revision Round - Review Other Agents' Findings

You are in the revision phase. Review the recommendations from other agents and determine if you need to revise your maintenance assessment.

### Other Agents' Initial Recommendations:

{formatted_recommendations if formatted_recommendations else "No other recommendations available."}

### Your Revision Task:

1. **Review Other Agents' Findings**: Carefully examine recommendations from:
   - Crew Compliance Agent: Crew duty limits, FDP calculations, qualification requirements
   - Regulatory Agent: Curfews, slots, weather restrictions, regulatory compliance
   - Network Agent: Flight propagation, connection impacts, aircraft rotation
   - Guest Experience Agent: Passenger impacts, rebooking needs, VIP considerations
   - Cargo Agent: Cargo handling, cold chain, perishable goods
   - Finance Agent: Cost implications, revenue impacts, scenario comparisons

2. **Identify Cross-Functional Impacts**: Determine if other agents' findings affect maintenance assessment:
   - Do crew constraints change the urgency of maintenance decisions?
   - Do network impacts affect aircraft swap feasibility?
   - Are there regulatory constraints that impact maintenance timing?
   - Do passenger/cargo priorities justify MEL exceptions? (NO - safety first!)

3. **Maintain Domain Priorities**: Your maintenance assessment is BINDING:
   - MEL compliance is NON-NEGOTIABLE
   - Airworthiness requirements are NON-NEGOTIABLE
   - Safety-critical defects MUST be resolved before flight
   - Business considerations CANNOT override maintenance requirements

4. **Decide on Revision**:
   - **Revise** if: Other agents provide new timing information, operational constraints, or safety concerns that change maintenance feasibility
   - **Confirm** if: Your initial assessment remains valid despite other agents' findings
   - **Strengthen** if: Other agents' findings reinforce your safety constraints

5. **Provide Clear Justification**: Explain:
   - What you reviewed from other agents
   - Whether you revised your recommendation (and why)
   - How you maintained safety priorities
   - Any conflicts between safety and business considerations

### Output Requirements:

Return your revised analysis with:
- Clearly state if recommendation is REVISED or CONFIRMED
- Update binding_constraints if needed
- Explain what you reviewed and why you revised/confirmed
- Maintain safety-first priorities

Remember: Your assessment is BINDING. Safety is non-negotiable. Business considerations CANNOT override maintenance requirements.
"""
        
        system_message += """

## Your Task
1. Extract flight information from the user prompt (already done - see extracted_flight_info below)
2. Use query_flight to get flight details
3. Use query_maintenance_work_orders to check MEL items and maintenance status
4. Use query_aircraft_availability to verify airworthiness
5. Perform comprehensive airworthiness analysis following the 14-step process
6. Return structured assessment with binding constraints

Extracted flight information:
"""
        system_message += f"- Flight Number: {flight_info.flight_number}\n"
        system_message += f"- Date: {flight_info.date}\n"
        system_message += f"- Disruption Event: {flight_info.disruption_event}\n"
        
        # Step 5: Run agent
        logger.info("Running maintenance agent with tools")
        
        try:
            result = await agent.ainvoke({
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ]
            })
        except Exception as e:
            error_type = type(e).__name__
            logger.error(f"Agent execution failed ({error_type}): {e}")
            
            # Provide helpful error messages based on error type
            if "timeout" in str(e).lower():
                reasoning = "Agent execution timed out. The analysis is taking longer than expected. Please try again."
            elif "rate" in str(e).lower() or "throttl" in str(e).lower():
                reasoning = "Service rate limit exceeded. Please wait a moment and try again."
            elif "authentication" in str(e).lower() or "authorization" in str(e).lower():
                reasoning = "Authentication or authorization error. Please check AWS credentials and permissions."
            else:
                reasoning = f"Agent execution failed: {str(e)}"
            
            return {
                "agent_name": "maintenance",
                "recommendation": "CANNOT_PROCEED",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": reasoning,
                "data_sources": [],
                "extracted_flight_info": {
                    "flight_number": flight_info.flight_number,
                    "date": flight_info.date,
                    "disruption_event": flight_info.disruption_event
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": str(e),
                "error_type": error_type
            }
        
        # Step 6: Extract response
        final_message = result["messages"][-1]
        
        # Parse agent response
        if hasattr(final_message, "content"):
            content = final_message.content
            
            # Try to parse as structured response
            if isinstance(content, dict):
                response = content
            else:
                # Agent returned text - create structured response
                response = {
                    "agent_name": "maintenance",
                    "recommendation": str(content),
                    "confidence": 0.8,
                    "binding_constraints": [],
                    "reasoning": str(content),
                    "data_sources": ["DynamoDB queries via tools"]
                }
        else:
            # No content attribute - create default response
            logger.warning("Agent response has no content attribute")
            response = {
                "agent_name": "maintenance",
                "recommendation": "Analysis completed",
                "confidence": 0.8,
                "binding_constraints": [],
                "reasoning": "Agent completed analysis",
                "data_sources": ["DynamoDB queries via tools"]
            }
        
        # Ensure required fields
        response["agent_name"] = "maintenance"
        response["extracted_flight_info"] = {
            "flight_number": flight_info.flight_number,
            "date": flight_info.date,
            "disruption_event": flight_info.disruption_event
        }
        response["timestamp"] = datetime.now(timezone.utc).isoformat()
        response["status"] = "success"
        
        # Ensure binding_constraints exists for safety agent
        if "binding_constraints" not in response:
            response["binding_constraints"] = []
        
        logger.info(f"Maintenance agent completed successfully")
        return response

    except Exception as e:
        logger.error(f"Error in maintenance agent: {e}")
        logger.exception("Full traceback:")
        return {
            "agent_name": "maintenance",
            "recommendation": "CANNOT_PROCEED",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": f"Agent execution error: {str(e)}",
            "data_sources": [],
            "extracted_flight_info": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
