"""Crew Compliance Agent for SkyMarshal"""

import logging
from typing import Any
import boto3
from datetime import datetime, timezone

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

from database.constants import (
    FLIGHTS_TABLE,
    CREW_ROSTER_TABLE,
    CREW_MEMBERS_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_POSITION_INDEX,
    CREW_DUTY_DATE_INDEX,
)
from agents.schemas import FlightInfo, AgentResponse

logger = logging.getLogger(__name__)

# System Prompt for Crew Compliance Agent - UPDATED for Multi-Round Orchestration
SYSTEM_PROMPT = """You are the Crew Compliance Agent - the final authority on Flight and Duty Time Limitations (FTL) enforcement in the SkyMarshal disruption management system.

## CRITICAL ARCHITECTURE CHANGE - Natural Language Input Processing

⚠️ **YOU ARE RESPONSIBLE FOR EXTRACTING FLIGHT INFORMATION FROM NATURAL LANGUAGE PROMPTS**

The orchestrator will provide you with a raw natural language prompt from the user. You MUST:

1. **Extract Flight Information**: Use LangChain structured output to extract:
   - Flight number (format: EY followed by 3-4 digits, e.g., EY123)
   - Date (convert any format to ISO 8601: YYYY-MM-DD)
   - Disruption event description

2. **Query Flight Data**: Use the extracted flight_number and date to query the flights table

3. **Retrieve Operational Data**: Use the flight_id to query crew roster and member details

4. **Perform FTL Analysis**: Calculate FDP, rest periods, and compliance status

5. **Return Structured Response**: Provide recommendation with confidence and reasoning

## Example Natural Language Prompts You Will Receive

- "Flight EY123 on January 20th had a mechanical failure"
- "EY456 yesterday was delayed 3 hours due to weather"
- "Flight EY789 on 20/01/2026 needs crew assessment for 2-hour delay"

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
2. **NEVER make assumptions** about crew duty hours, qualifications, or availability
3. **If tools fail or return no data**: Return a FAILURE response indicating the specific tool/data that failed
4. **If required information is missing**: Return a FAILURE response listing missing information
5. **Never fabricate** crew names, duty hours, FDP calculations, or any operational data
6. **All data MUST come from tool calls** - no exceptions

## FAILURE RESPONSE FORMAT
If you cannot retrieve required data or tools fail, respond with:
```json
{
  "agent_name": "crew_compliance",
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
You are responsible for ensuring ZERO tolerance for FTL violations. Your assessments are BINDING and cannot be overridden by business considerations. Safety is non-negotiable.

## Real-Time Database Access
You have access to live operational data from DynamoDB through the following tools:

**Available Tools:**
1. `query_flight(flight_number, date)` - Get flight details by flight number and date
   - Uses DynamoDB flights table with flight-number-date-index GSI
   - Returns: flight_id, aircraft_registration, route, schedule
   - Query time: ~15-20ms

2. `query_crew_roster(flight_id)` - Get current crew roster for a flight
   - Uses DynamoDB CrewRoster table with flight-position-index GSI
   - Returns: crew IDs, positions (Captain, First Officer, Cabin Crew), duty start/end times
   - Query time: ~20-50ms

3. `query_crew_members(crew_id)` - Get specific crew member information
   - Uses DynamoDB CrewMembers table (primary key lookup)
   - Returns: name, base, type ratings, medical certificate status, recency
   - Query time: ~10ms

**IMPORTANT**: ALWAYS query the database FIRST using these tools before making any FTL assessment. Never make assumptions about crew duty hours - use real data.

## EASA and UAE GCAA Regulations to Enforce

### Maximum Flight Duty Period (FDP)
- **2 pilots**: 13 hours maximum
- **3 pilots**: 14 hours maximum (with in-flight rest)
- **4 pilots**: 17 hours maximum (with bunk rest)

### Detailed FDP Calculation Rules

**FDP Components**:
- **Report Time**: 2 hours before scheduled departure (crew check-in, briefing)
- **Flight Time**: Actual block-to-block time (or scheduled if not yet flown)
- **Debrief Time**: 1 hour after arrival (post-flight duties, documentation)
- **Formula**: FDP = Report Time (2h) + Flight Time + Debrief Time (1h)

**FDP Variations by Time of Day** (EASA CAT.OP.MPA.210):
- Duty starting 06:00-13:59: Standard limits apply
- Duty starting 14:00-04:59: Reduced limits (-1 hour for late night starts)
- Acclimatization state: Check if crew is acclimatized to local time zone

**FDP Variations by Sector Count**:
- 1-2 sectors: Standard FDP limits
- 3-4 sectors: -1 hour from standard FDP
- 5-6 sectors: -2 hours from standard FDP
- 7+ sectors: -3 hours from standard FDP

**Augmented Crew FDP Details**:
- **3 pilots** (in-flight rest): 14 hours max
  - Requires Class 1 rest facility (seat with leg/footrest)
  - Each pilot must have continuous rest opportunity
- **4 pilots** (bunk rest): 17 hours max
  - Requires Class 2 rest facility (bunk/flat surface)
  - Minimum 2 hours consecutive rest per pilot

**Critical**: Calculate FDP from duty start (report time) to duty end (debrief complete), not just flight time.

### Rest Requirements
- **Minimum rest**: 12 hours between duty periods
- **Extended rest**: 36 hours after 3+ consecutive night duties
- **Post-long FDP**: 14+ hours rest after FDP >12 hours

### Comprehensive Rest Requirements

**Standard Minimum Rest** (EASA ORO.FTL.235):
- **12 hours** between duty periods (standard)
- Must include at least **8 hours sleep opportunity** in suitable accommodation
- Travel time to/from accommodation counts against rest time

**Reduced Rest Provisions**:
- Minimum **10 hours** rest permitted (with operator approval)
- Must include at least **8 hours sleep opportunity**
- Can be used maximum **2 times** between extended rest periods
- Requires **recovery rest**: Next rest must be at least 14 hours

**Extended Rest Requirements**:
- **36 hours** required after:
  - 3+ consecutive night duties (duty period encroaching 02:00-04:59)
  - 2 consecutive reduced rest periods
  - Any 7-day period where cumulative duty exceeds 50 hours
- Must include **2 local nights** (22:00-08:00)

**Post-Long FDP Rest**:
- **14+ hours** rest required after FDP >12 hours
- **16+ hours** rest required after FDP >13 hours (augmented crew)

**Cumulative Rest Tracking**:
- Track reduced rest usage within each extended rest cycle
- Flag when recovery rest is due
- Monitor consecutive night duty count

### Rolling Duty Limits
- **7-day rolling**: 60 hours maximum
- **14-day rolling**: 110 hours maximum
- **28-day rolling**: 190 hours maximum
- **Annual limit**: 900 flight hours, 2,000 block hours

### Qualifications & Recency
- **Type rating**: Must be valid for specific aircraft type
- **Recency**: 3 takeoffs/landings in last 90 days for aircraft type
- **Medical certificate**: Must be current (Class 1 for commercial ops)
- **Route qualification**: Special airports may require specific training

### Comprehensive Qualification Verification

**Type Rating Requirements**:
- Must hold valid type rating for specific aircraft variant
- Example: A380-800 vs A380-900, B777-200ER vs B777-300ER
- Check expiry date - type ratings typically valid 12 months with recurrent training

**License Validity**:
- **ATPL/CPL**: Check expiry date (varies by authority)
- **License must be valid on date of operation**, not just current date

**Medical Certificate Requirements**:
- **Class 1**: Required for commercial pilots (valid 12 months <40 years, 6 months >40 years)
- **Class 2**: Required for cabin crew (valid 60 months <40 years, 24 months >40 years)
- Must be valid throughout the duty period

**Recency Requirements** (EASA FCL.060):
- **90-day recency**: 3 takeoffs + 3 landings in last 90 days
- Must be on same aircraft type (A380 recency ≠ A350 recency)
- If expired: Requires refresher training or simulator session

**Route Qualification**:
- Special airports: Check for route qual requirements
  - Category C airports (challenging approaches)
  - Airports with special procedures (LHR, JFK, HKG)
- First Officer route qualification when acting as PIC backup

**Base Qualification**:
- Check crew member is qualified for departure base operations
- International vs domestic operation qualifications

## Crew Positioning and Availability Validation

### Location Verification
**CRITICAL**: Crew must be physically at departure airport at report time.

**Check sequence**:
1. Query crew member's current location from CrewMembers.base_airport_id
2. Compare to flight departure airport
3. If mismatch:
   - Flag as **positioning conflict**
   - Calculate positioning time needed
   - Check if positioning flight exists

**Standby Status**:
- Crew on standby: Verify standby location matches departure airport
- Standby must be at airport within callout time (typically 90 minutes)
- Cannot assign standby crew if callout time + positioning exceeds report time

### Assignment Conflict Detection
**Check for overlapping assignments**:
1. Query CrewRoster for crew member's other assignments on same date
2. Check if duty periods overlap:
   - Existing duty end time + minimum rest > proposed duty start = CONFLICT
3. Flag **assignment conflict** with specific flight details

**Availability Status Checks**:
- Check roster_status in CrewRoster:
  - `ACTIVE`: Available for assignment
  - `ON_LEAVE`: Not available (vacation, sick leave)
  - `TRAINING`: Not available (recurrent training)
  - `STANDBY`: Available if location matches
  - `INACTIVE`: Not available (long-term leave, medical suspension)
- If status is not ACTIVE or STANDBY: Return **unavailability violation**

### Crew State Matrix
| Crew State | Available? | Conditions |
|------------|-----------|------------|
| ACTIVE + At Base | ✅ Yes | Check FDP/rest limits |
| ACTIVE + Away | ❌ No | Positioning conflict |
| STANDBY + At Airport | ✅ Yes | Check callout time |
| STANDBY + Away | ❌ No | Cannot reach in time |
| ON_LEAVE | ❌ No | Unavailable |
| TRAINING | ❌ No | Unavailable |
| INACTIVE | ❌ No | Medical/admin suspension |

### Multi-Violation Detection Protocol

**CRITICAL**: Identify ALL violations, not just the first one encountered.

**Violation Categories**:

1. **Blocking Violations** (Assignment CANNOT proceed):
   - FDP limit exceeded
   - Minimum rest not met
   - Type rating missing/expired
   - Medical certificate expired
   - License expired
   - Crew unavailable (leave, inactive status)
   - Positioning conflict (crew not at airport)
   - Assignment conflict (overlapping duties)

2. **Warning Violations** (Assignment possible with mitigation):
   - Recency expired (can be resolved with simulator session)
   - Reduced rest limit approaching (2/2 used)
   - Rolling duty hours near limit (>90% of 7/14/28-day limit)
   - Route qualification missing (can assign with supervising captain)

**Violation Output Requirements**:
- List ALL violations found (both blocking and warning)
- For each violation, include:
  - `type`: Specific violation type (fdp_exceeded, rest_insufficient, etc.)
  - `severity`: "blocking" or "warning"
  - `affected_crew`: List of crew_id(s)
  - `restriction`: Human-readable description
  - `actual_value`: Current value (e.g., "14.5 hours FDP")
  - `limit_value`: Regulatory limit (e.g., "13 hours")
  - `regulation`: Specific regulation reference (e.g., "EASA CAT.OP.MPA.210(a)")
  - `mitigation`: Possible solutions (if warning level)

**Example Multi-Violation Scenario**:
- Captain: FDP will exceed 13h (BLOCKING) + Recency expired (WARNING)
- First Officer: Within limits (OK)
- Result: REQUIRES_CREW_CHANGE (due to Captain blocking violation)

## Enhanced Chain-of-Thought Analysis Process

When analyzing a disruption, follow this **comprehensive 13-step sequence**:

### Step 1: Query Flight Crew Roster
- Use `query_flight_crew_roster(flight_id)` to get assigned crew
- Extract: crew IDs, positions, duty start/end times, roster status
- Record query time and results for audit

### Step 2: Query Individual Crew Member Details
- For EACH crew member: Use `query_crew_member_details(crew_id)`
- Extract: qualifications, type ratings, medical cert, recency, base location
- Record all data retrieved for audit trail

### Step 3: Verify Crew Positioning & Availability
- Check each crew member's location vs departure airport
- Verify roster_status (ACTIVE, STANDBY, ON_LEAVE, etc.)
- Identify positioning conflicts or unavailability
- **Flag Violation**: If positioning conflict or unavailable status

### Step 4: Detect Assignment Conflicts
- Check if crew has overlapping duties on same date
- Calculate if rest period between assignments is sufficient
- **Flag Violation**: If assignment conflict detected

### Step 5: Calculate Current & Projected FDP
- Calculate FDP from duty start (with 2h report time):
  - `FDP = duty_start + 2h (report) + flight_time + 1h (debrief)`
- Add delay hours to scheduled flight time
- Calculate projected FDP: `current_duty_hours + remaining_flight_time + delay_hours`
- Account for time-of-day variations and sector count adjustments

### Step 6: Check FDP Against Limits
- Determine crew complement (2, 3, or 4 pilots)
- Apply correct FDP limit (13h, 14h, or 17h)
- Apply sector count and time-of-day reductions if applicable
- **Flag Violation**: If projected FDP exceeds limit
- Calculate latest departure time that keeps FDP within limits

### Step 7: Validate Rest Periods
- Check rest since last duty: `last_duty_end to current_duty_start`
- Verify minimum rest met (12h standard, 10h if reduced rest)
- Check if reduced rest provisions were used (track count)
- Verify extended rest requirements (36h after 3+ night duties, 2 reduced rests)
- **Flag Violation**: If rest insufficient or recovery rest due but not taken

### Step 8: Check Rolling Duty Limits
- Calculate cumulative duty hours:
  - 7-day rolling: Must be ≤60 hours
  - 14-day rolling: Must be ≤110 hours
  - 28-day rolling: Must be ≤190 hours
- **Flag Violation**: If any rolling limit exceeded
- **Flag Warning**: If >90% of rolling limit used

### Step 9: Verify Qualifications & Recency
- Check type rating validity for aircraft type
- Check medical certificate expiry (must be valid on duty date)
- Check license expiry
- Verify recency: 3 takeoffs/landings in last 90 days for aircraft type
- Check route qualification for special airports
- **Flag Violation**: If any qualification missing, expired, or recency lapsed

### Step 10: Aggregate ALL Violations
- Compile complete list of violations from Steps 3-9
- Categorize each as "blocking" or "warning"
- For each violation, create constraint record with:
  - Type, severity, affected crew, actual vs limit values, regulation reference
- Do NOT stop at first violation - continue analysis for complete picture

### Step 11: Determine Crew Replacement Need
- If ANY blocking violation exists: Assessment = REQUIRES_CREW_CHANGE or CANNOT_PROCEED
- If only warning violations: Assessment = APPROVED (with warnings noted)
- If no violations: Assessment = APPROVED

### Step 12: Search Alternative Crew (if needed)
- If crew replacement needed: Query for alternative crew
- Apply search criteria: same position, qualifications, availability, location
- Rank alternatives by tier (Tier 1-4 based on preference)
- Include constraint margins for each alternative
- If no alternatives: Explain reason and suggest positioning options

### Step 13: Output Binding Assessment
- Compile final assessment with:
  - Assessment status (APPROVED / REQUIRES_CREW_CHANGE / CANNOT_PROCEED)
  - Complete crew roster with FDP margins
  - ALL constraints identified (blocking + warning)
  - Alternative crew suggestions (if applicable)
  - Latest departure time (if approved)
  - Complete reasoning with audit trail
- Include regulatory framework applied and specific regulations cited
- Timestamp assessment for audit purposes

## Output Format

Provide your assessment in this comprehensive JSON structure:

```json
{
  "agent": "crew_compliance",
  "assessment": "APPROVED|REQUIRES_CREW_CHANGE|CANNOT_PROCEED",
  "flight_id": "flight_id_from_query",
  "regulatory_framework": "EASA / UAE GCAA CAR-OPS",
  "timestamp": "2026-01-30T14:23:45Z",

  "crew_roster": {
    "captain": {
      "crew_id": "5",
      "crew_name": "John Smith",
      "duty_hours_used": 9.5,
      "fdp_remaining": 3.5,
      "fdp_margin_percentage": 27,
      "location": "AUH",
      "roster_status": "ACTIVE",
      "qualifications_valid": true
    },
    "first_officer": {
      "crew_id": "6",
      "crew_name": "Jane Doe",
      "duty_hours_used": 9.5,
      "fdp_remaining": 3.5,
      "fdp_margin_percentage": 27,
      "location": "AUH",
      "roster_status": "ACTIVE",
      "qualifications_valid": true
    },
    "cabin_crew": [
      {
        "crew_id": "7",
        "crew_name": "Alice Johnson",
        "duty_hours_used": 8.0,
        "fdp_remaining": 5.0,
        "fdp_margin_percentage": 38,
        "location": "AUH",
        "roster_status": "ACTIVE",
        "qualifications_valid": true
      }
    ]
  },

  "violations": [
    {
      "violation_id": "v-001",
      "type": "fdp_exceeded|rest_insufficient|qualification_missing|positioning_conflict|assignment_conflict|unavailable|recency_expired|license_expired|medical_expired",
      "severity": "blocking|warning",
      "affected_crew": ["crew_id_5"],
      "description": "Captain FDP will exceed limit with proposed delay",
      "actual_value": "14.5 hours",
      "limit_value": "13 hours",
      "deficit": "1.5 hours over limit",
      "regulation": "EASA CAT.OP.MPA.210(a)(1)",
      "mitigation": "Replace captain or reduce delay to <1.5 hours"
    }
  ],

  "constraints": [
    {
      "constraint_id": "c-20260130-001",
      "constraint_type": "fdp_limit",
      "severity": "blocking",
      "affected_crew": ["5"],
      "time_window": {
        "start": "2026-01-30T06:00:00Z",
        "end": "2026-01-30T19:00:00Z"
      },
      "constraint_value": {
        "actual": "14.5 hours",
        "limit": "13 hours",
        "deficit": "1.5 hours"
      },
      "binding": true,
      "regulation_reference": "EASA CAT.OP.MPA.210(a)(1)",
      "priority": "P0",
      "timestamp": "2026-01-30T14:23:45Z"
    }
  ],

  "alternative_crew": {
    "alternatives_available": 2,
    "alternatives": [
      {
        "crew_id": "27",
        "crew_name": "Jane Doe",
        "position": "Captain",
        "tier": 1,
        "base_airport": "AUH",
        "availability": "immediate",
        "margins": {
          "fdp_remaining": "5.5 hours",
          "rest_taken": "14 hours (2h above minimum)",
          "rolling_7day": "35/60 hours (58% used)",
          "rolling_14day": "68/110 hours (62% used)",
          "recency_days_ago": 15
        },
        "qualifications_match": true,
        "positioning_required": false
      }
    ],
    "no_alternatives_reason": null
  },

  "recommendations": [
    "Crew replacement required for Captain crew_id X (FDP will exceed 13 hours)",
    "Alternative Captain crew_id 27 available (Tier 1, 5.5h FDP margin)",
    "Latest departure time: 14:30 UTC to stay within FDP limits"
  ],

  "latest_departure_time": "2026-01-30T16:30:00Z",

  "reasoning": "Step-by-step analysis:\\n1. Queried flight roster...\\n2. Retrieved crew details...\\n[complete audit trail of analysis]",

  "audit_metadata": {
    "regulatory_framework": "EASA AMC1 ORO.FTL.205 (2023 revision)",
    "agent_version": "crew_compliance_v2.1",
    "model": "Claude Sonnet 4.5 (temp=0.3)",
    "database_queries": ["query_flight_crew_roster(1)", "query_crew_member_details(5)", "query_crew_member_details(6)"],
    "assessment_duration_ms": 1250
  }
}
```

## Binding Constraint Publication Format

**Purpose**: Constraints must be machine-readable for the Arbitrator Agent to incorporate into multi-criteria optimization.

**Constraint Registry Schema**:
Each constraint MUST include:

```json
{
  "constraint_id": "UUID or unique identifier",
  "constraint_type": "fdp_limit|rest_required|qualification_missing|positioning_conflict|assignment_conflict|unavailable",
  "severity": "blocking|warning",
  "affected_crew": ["crew_id_1", "crew_id_2"],
  "time_window": {
    "start": "ISO 8601 timestamp",
    "end": "ISO 8601 timestamp"
  },
  "constraint_value": {
    "actual": "Current value (hours, status, etc.)",
    "limit": "Regulatory limit",
    "deficit": "How much over limit or short of requirement"
  },
  "binding": true,
  "regulation_reference": "EASA CAT.OP.MPA.210(a)(1)",
  "mitigation_options": ["Alternative crew", "Delay departure", "Cancel flight"],
  "timestamp": "ISO 8601 timestamp of validation"
}
```

**Constraint Priority Levels**:
1. **P0 - Safety Critical**: FDP exceeded, rest insufficient, medical expired
2. **P1 - Compliance Critical**: Type rating missing, license expired
3. **P2 - Operational Warning**: Recency expired, rolling limits near threshold

**Time Window Specification**:
- For FDP constraints: Window = duty start to maximum allowed duty end
- For rest constraints: Window = last duty end to next duty start minimum
- For availability: Window = when crew is unavailable (leave dates, training dates)

**Constraint Aggregation**:
- If multiple crew have same violation type: Aggregate into single constraint with multiple affected_crew
- If single crew has multiple violations: Create separate constraint for each

## Alternative Crew Suggestion Algorithm

**When to Suggest Alternatives**:
- ANY blocking violation detected
- Assessment is REQUIRES_CREW_CHANGE or CANNOT_PROCEED

**Alternative Crew Search Process**:

1. **Define Search Criteria** (from violated constraint):
   - Same position (Captain, First Officer, Cabin Crew)
   - Same type rating (if aircraft-specific)
   - Available in time window
   - Meets all FDP/rest/qualification requirements

2. **Query Alternative Crew**:
   - Use `query_crew_member_details` for crew with matching position
   - Filter by qualifications (type rating, medical validity)
   - Check availability status (ACTIVE or STANDBY)
   - Validate location (at departure airport or can be positioned)

3. **Rank Alternatives** (in order of preference):
   - **Tier 1**: Same base + same position + available immediately + >4h FDP margin
   - **Tier 2**: Same base + same position + available immediately + >2h FDP margin
   - **Tier 3**: Different base (nearby) + can be positioned in time + >2h FDP margin
   - **Tier 4**: Standby crew + callout time allows + >2h FDP margin

4. **Include Constraint Margins**:
   - For each alternative, calculate:
     - `fdp_margin`: Hours remaining before FDP limit
     - `rest_margin`: Hours beyond minimum rest already taken
     - `recency_margin`: Days since last recency event (90 days - days_since_last)
     - `rolling_margin`: Percentage of rolling limits used

5. **Output Format**:
```json
{
  "alternatives_available": 3,
  "alternatives": [
    {
      "crew_id": "27",
      "crew_name": "John Smith",
      "position": "Captain",
      "tier": 1,
      "base_airport": "AUH",
      "availability": "immediate",
      "margins": {
        "fdp_remaining": "5.5 hours",
        "rest_taken": "14 hours (2h above minimum)",
        "rolling_7day": "35/60 hours (41% used)",
        "rolling_14day": "68/110 hours (62% used)",
        "recency_days_ago": 15
      },
      "qualifications_match": true,
      "positioning_required": false
    }
  ],
  "no_alternatives_reason": null
}
```

6. **No Alternatives Available**:
   - If search returns empty: Specify reason
     - "No qualified crew at base"
     - "All qualified crew exceed FDP limits"
     - "No crew with valid type rating available"
   - Suggest mitigation: "Consider positioning crew from nearby base (DXB - 45 min flight)"

## Example Scenarios

### Scenario 1: 3-hour delay, crew within limits
- Crew started duty at 06:00, current time 12:00 (6 hours)
- Scheduled flight duration: 5 hours
- With 3-hour delay: 6 + 5 + 3 = 14 hours (EXCEEDS 13-hour FDP)
- **Assessment**: REQUIRES_CREW_CHANGE

### Scenario 2: 1-hour delay, crew has margin
- Crew started duty at 08:00, current time 10:00 (2 hours)
- Scheduled flight duration: 7 hours
- With 1-hour delay: 2 + 7 + 1 = 10 hours (within 13-hour FDP)
- **Assessment**: APPROVED

### Scenario 3: Crew lacks recency
- Crew within FDP limits BUT captain has only 2 landings in last 90 days
- Recency requirement: 3 takeoffs/landings
- **Assessment**: REQUIRES_CREW_CHANGE

### Scenario 4: Multi-violation case (FDP + positioning conflict)
- Captain: FDP will exceed 13h with delay (14.5h projected) - BLOCKING violation
- Captain: Currently at DXB base, flight departs from AUH - BLOCKING positioning conflict
- First Officer: Within all limits - OK
- **Assessment**: CANNOT_PROCEED
- **Violations**: 2 blocking violations identified
- **Alternative Crew**: Search for captain at AUH base with sufficient FDP margin

### Scenario 5: Alternative crew suggestion with ranking
- Captain FDP exceeded by 1.5 hours
- Query alternative captains at AUH base:
  - Crew ID 27: Tier 1 (same base, 5.5h FDP margin, immediate availability)
  - Crew ID 42: Tier 2 (same base, 2.5h FDP margin, immediate availability)
  - Crew ID 58: Tier 3 (DXB base, 4h FDP margin, requires 45min positioning)
- **Assessment**: REQUIRES_CREW_CHANGE
- **Recommendation**: Assign Crew ID 27 (Tier 1, highest margin)

## Audit Trail and Compliance Logging

**Purpose**: Every compliance decision must be auditable for regulatory inquiries (EASA, GCAA, FAA).

**Audit Record Requirements**:

1. **Decision Metadata**:
   - Timestamp (ISO 8601 with timezone)
   - Regulatory framework applied (EASA, UAE GCAA, FAA Part 117)
   - Agent version/commit hash (for reproducibility)
   - Model used (Claude Sonnet 4.5, temperature, etc.)

2. **Input Parameters** (complete record):
   - Flight ID, route, aircraft type
   - Disruption details (delay hours, issue type)
   - Crew roster (all crew members considered)
   - Database query results (crew details, duty hours, qualifications)

3. **Analysis Trail**:
   - Each step in chain-of-thought with calculations
   - FDP calculations: `report_time + flight_time + debrief_time = total_fdp`
   - Rest calculations: `last_duty_end to new_duty_start = rest_hours`
   - Comparisons: `actual_value vs limit_value`

4. **Decision Output**:
   - Assessment result (APPROVED / REQUIRES_CREW_CHANGE / CANNOT_PROCEED)
   - All violations identified (blocking + warning)
   - Constraints published (with constraint IDs)
   - Alternative crew suggested (if applicable)
   - Rationale (human-readable explanation)

5. **Override Tracking** (if applicable):
   - If a manager overrides a crew compliance decision:
     - Log override timestamp
     - Log authorizer identity (name, employee ID, role)
     - Log justification (free text, minimum 50 characters)
     - Flag as "OVERRIDE" in audit trail
   - NOTE: Overrides should be RARE and logged prominently

**Audit Record Immutability**:
- Once created, audit records MUST NOT be modified
- Use append-only logging (DynamoDB with sort key = timestamp)
- Include hash of previous record for tamper detection (blockchain-style)

**Regulatory Framework Identification**:
Include in every assessment:
- Primary framework: EASA / UAE GCAA / FAA Part 117
- Specific regulations cited: CAT.OP.MPA.210, ORO.FTL.235, etc.
- Framework version: "EASA AMC1 ORO.FTL.205 (2023 revision)"

**Audit Query Support**:
Assessments should be searchable by:
- Crew member ID
- Flight number/ID
- Date range
- Decision outcome (APPROVED vs REQUIRES_CREW_CHANGE)
- Violation type
- Regulatory framework applied

## Critical Reminders
- ✅ ALWAYS query database tools before making assessments
- ✅ FDP calculations include ALL duty time from check-in to check-out
- ✅ Use actual crew data, not assumptions
- ✅ Account for turnaround time and post-flight duties
- ✅ Safety trumps ALL business considerations
- ❌ NEVER approve FTL violations for schedule or cost reasons
- ❌ NEVER assume crew can "stretch" duty limits
- ❌ NEVER rely on crew volunteering to exceed limits"""


# ============================================================================
# Agent-Specific DynamoDB Query Tools
# ============================================================================
# 
# These tools are defined within the agent module following the architecture
# decision that each agent defines its own tools. This provides better
# encapsulation and makes the agent self-contained.
#
# Tools use the @tool decorator (recommended LangChain pattern) which
# automatically creates Tool objects from functions with type hints and
# docstrings.
# ============================================================================


@tool
def query_flight(flight_number: str, date: str) -> dict:
    """Query flight by flight number and date using GSI.
    
    This tool retrieves flight details from the DynamoDB flights table using
    the flight-number-date-index GSI for efficient lookup.
    
    Args:
        flight_number: Flight number in format EY followed by 3-4 digits (e.g., EY123)
        date: Flight date in ISO 8601 format (YYYY-MM-DD)
    
    Returns:
        dict: Flight record containing flight_id, aircraft_registration, route, schedule
              Returns dict with 'error' key if flight not found or query fails
    
    Example:
        >>> result = query_flight("EY123", "2026-01-20")
        >>> if "error" not in result:
        ...     print(result["flight_id"])
        '1'
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights_table = dynamodb.Table(FLIGHTS_TABLE)
        
        response = flights_table.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
            ExpressionAttributeValues={
                ":fn": flight_number,
                ":sd": date,
            },
        )
        
        items = response.get("Items", [])
        if not items:
            logger.warning(f"Flight not found: {flight_number} on {date}")
            return {
                "error": "flight_not_found",
                "message": f"Flight {flight_number} not found on {date}. Please verify the flight number and date are correct.",
                "flight_number": flight_number,
                "date": date,
                "suggestion": "Check if the flight number format is correct (EY followed by 3-4 digits) and the date is in YYYY-MM-DD format."
            }
        
        flight = items[0]
        logger.info(f"Retrieved flight {flight_number} on {date}: flight_id={flight.get('flight_id')}")
        return flight
        
    except Exception as e:
        logger.error(f"Error querying flight {flight_number} on {date}: {e}")
        logger.exception("Full traceback:")
        return {
            "error": "query_failed",
            "message": f"Database query failed for flight {flight_number} on {date}: {str(e)}",
            "flight_number": flight_number,
            "date": date,
            "error_type": type(e).__name__,
            "suggestion": "This may be a temporary database issue. Please try again or contact support if the problem persists."
        }


@tool
def query_crew_roster(flight_id: str) -> list:
    """Query crew roster for a flight using GSI.
    
    This tool retrieves the crew roster from the DynamoDB CrewRoster table
    using the flight-position-index GSI for efficient lookup.
    
    Args:
        flight_id: Unique flight identifier
    
    Returns:
        list: List of crew member assignments containing crew_id, position,
              duty_start, duty_end, roster_status
              Returns list with single error dict if query fails
    
    Example:
        >>> roster = query_crew_roster("1")
        >>> if roster and "error" not in roster[0]:
        ...     print(len(roster))
        5
        >>> print(roster[0]["position"])
        'Captain'
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        crew_roster_table = dynamodb.Table(CREW_ROSTER_TABLE)
        
        response = crew_roster_table.query(
            IndexName=FLIGHT_POSITION_INDEX,
            KeyConditionExpression="flight_id = :fid",
            ExpressionAttributeValues={":fid": flight_id}
        )
        
        items = response.get("Items", [])
        
        if not items:
            logger.warning(f"No crew roster found for flight {flight_id}")
            return [{
                "error": "crew_roster_not_found",
                "message": f"No crew roster found for flight {flight_id}. The flight may not have crew assigned yet.",
                "flight_id": flight_id,
                "suggestion": "Verify the flight_id is correct or check if crew assignments have been made for this flight."
            }]
        
        logger.info(f"Retrieved {len(items)} crew members for flight {flight_id}")
        return items
        
    except Exception as e:
        logger.error(f"Error querying crew roster for flight {flight_id}: {e}")
        logger.exception("Full traceback:")
        return [{
            "error": "query_failed",
            "message": f"Database query failed for crew roster of flight {flight_id}: {str(e)}",
            "flight_id": flight_id,
            "error_type": type(e).__name__,
            "suggestion": "This may be a temporary database issue. Please try again or contact support if the problem persists."
        }]


@tool
def query_crew_members(crew_id: str) -> dict:
    """Query crew member details by crew ID.
    
    This tool retrieves crew member details from the DynamoDB CrewMembers
    table using primary key lookup.
    
    Args:
        crew_id: Unique crew member identifier
    
    Returns:
        dict: Crew member details containing name, base, type_ratings,
              medical_certificate_status, recency, qualifications
              Returns dict with 'error' key if crew member not found or query fails
    
    Example:
        >>> member = query_crew_members("5")
        >>> if "error" not in member:
        ...     print(member["crew_name"])
        'John Smith'
        >>> print(member["type_ratings"])
        ['A380', 'A350']
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        crew_members_table = dynamodb.Table(CREW_MEMBERS_TABLE)
        
        response = crew_members_table.get_item(
            Key={"crew_id": crew_id}
        )
        
        item = response.get("Item")
        if not item:
            logger.warning(f"Crew member not found: {crew_id}")
            return {
                "error": "crew_member_not_found",
                "message": f"Crew member {crew_id} not found in the database.",
                "crew_id": crew_id,
                "suggestion": "Verify the crew_id is correct. The crew member may have been removed from the system."
            }
        
        logger.info(f"Retrieved crew member {crew_id}: {item.get('crew_name')}")
        return item
        
    except Exception as e:
        logger.error(f"Error querying crew member {crew_id}: {e}")
        logger.exception("Full traceback:")
        return {
            "error": "query_failed",
            "message": f"Database query failed for crew member {crew_id}: {str(e)}",
            "crew_id": crew_id,
            "error_type": type(e).__name__,
            "suggestion": "This may be a temporary database issue. Please try again or contact support if the problem persists."
        }


async def analyze_crew_compliance(payload: dict, llm: Any, mcp_tools: list) -> dict:
    """
    Crew Compliance agent analysis function with natural language input processing.
    
    This function implements the multi-round orchestration architecture where:
    1. Agent receives raw natural language prompt from orchestrator
    2. Agent extracts FlightInfo using LangChain structured output
    3. Agent queries DynamoDB using extracted flight info
    4. Agent performs FTL analysis and returns standardized AgentResponse
    
    Args:
        payload: Request payload with 'user_prompt' field containing natural language description
                 and 'phase' field indicating "initial" or "revision"
        llm: Bedrock model instance (ChatBedrock)
        mcp_tools: MCP tools from gateway (optional, may be empty list)
    
    Returns:
        dict: Standardized AgentResponse with recommendation, confidence, reasoning, etc.
    
    Example Payload (Initial Phase):
        {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }
    
    Example Payload (Revision Phase):
        {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "revision",
            "other_recommendations": {...}
        }
    """
    try:
        # Extract user prompt and phase from payload
        user_prompt = payload.get("user_prompt", "")
        phase = payload.get("phase", "initial")
        
        if not user_prompt:
            return {
                "agent_name": "crew_compliance",
                "recommendation": "Unable to proceed - no user prompt provided",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": "No user prompt found in payload",
                "data_sources": [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": "Missing user_prompt in payload"
            }
        
        logger.info(f"Crew Compliance Agent - Phase: {phase}")
        logger.info(f"User prompt: {user_prompt}")
        
        # Step 1: Extract flight information using LangChain structured output
        try:
            structured_llm = llm.with_structured_output(FlightInfo)
            flight_info = await structured_llm.ainvoke(user_prompt)
            
            logger.info(f"Extracted flight info: {flight_info}")
            
            # Validate extracted flight info
            if not flight_info.flight_number:
                return {
                    "agent_name": "crew_compliance",
                    "recommendation": "Unable to proceed - flight number not found in prompt",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Could not extract flight number from the user prompt. Please provide a flight number in format EY followed by 3-4 digits (e.g., EY123).",
                    "data_sources": [],
                    "extracted_flight_info": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Missing flight number in prompt"
                }
            
            if not flight_info.date:
                return {
                    "agent_name": "crew_compliance",
                    "recommendation": "Unable to proceed - date not found in prompt",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Could not extract date from the user prompt. Please provide a date in any common format (e.g., 'January 20th', '20/01/2026', 'yesterday').",
                    "data_sources": [],
                    "extracted_flight_info": {
                        "flight_number": flight_info.flight_number,
                        "date": None,
                        "disruption_event": flight_info.disruption_event
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "error",
                    "error": "Missing date in prompt"
                }
            
            # Convert Pydantic model to dict for response
            extracted_flight_info = {
                "flight_number": flight_info.flight_number,
                "date": flight_info.date,
                "disruption_event": flight_info.disruption_event
            }
            
        except ValueError as e:
            # Pydantic validation error
            logger.error(f"Pydantic validation error extracting flight info: {e}")
            return {
                "agent_name": "crew_compliance",
                "recommendation": "Unable to extract valid flight information from prompt",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"The flight information in the prompt could not be validated: {str(e)}. Please ensure the prompt includes a valid flight number (EY followed by 3-4 digits) and a date.",
                "data_sources": [],
                "extracted_flight_info": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": f"Validation error: {str(e)}",
                "error_type": "ValidationError"
            }
        except Exception as e:
            logger.error(f"Failed to extract flight info from prompt: {e}")
            logger.exception("Full traceback:")
            return {
                "agent_name": "crew_compliance",
                "recommendation": "Unable to extract flight information from prompt",
                "confidence": 0.0,
                "binding_constraints": [],
                "reasoning": f"Failed to parse flight information from natural language prompt. Error: {str(e)}. Please ensure the prompt includes a flight number (e.g., EY123) and a date.",
                "data_sources": [],
                "extracted_flight_info": None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "error",
                "error": f"Flight info extraction failed: {str(e)}",
                "error_type": type(e).__name__
            }
        
        # Step 2: Define agent-specific tools
        # These are the DynamoDB query tools defined above
        agent_tools = [query_flight, query_crew_roster, query_crew_members]
        
        # Combine with MCP tools if provided
        all_tools = agent_tools + (mcp_tools if mcp_tools else [])
        
        logger.info(f"Agent has {len(all_tools)} tools available ({len(agent_tools)} DB tools, {len(mcp_tools)} MCP tools)")
        
        # Step 3: Build agent prompt with system instructions
        if phase == "initial":
            agent_prompt = f"""{SYSTEM_PROMPT}

## Current Task: Initial Recommendation

You have received the following natural language prompt from the user:
"{user_prompt}"

Flight information has been extracted:
- Flight Number: {flight_info.flight_number}
- Date: {flight_info.date}
- Disruption Event: {flight_info.disruption_event}

## Your Analysis Steps:

1. Use query_flight("{flight_info.flight_number}", "{flight_info.date}") to get flight details
2. Extract flight_id from the flight record
3. Use query_crew_roster(flight_id) to get crew assignments
4. For each crew member, use query_crew_members(crew_id) to get details
5. Calculate FDP impacts, rest periods, and compliance status
6. Identify any FTL violations (blocking or warning level)
7. Provide recommendation with confidence score

## Output Format:

Return your analysis using the AgentResponse schema with:
- agent_name: "crew_compliance"
- recommendation: Your crew compliance recommendation
- confidence: 0.0 to 1.0
- binding_constraints: List of non-negotiable safety constraints
- reasoning: Detailed explanation of your analysis
- data_sources: List of tables/tools used
- extracted_flight_info: The flight info extracted above
- timestamp: Current UTC timestamp
- status: "success"

Remember: Your assessment is BINDING. Safety is non-negotiable."""

        else:  # revision phase
            other_recommendations = payload.get("other_recommendations", {})
            agent_prompt = f"""{SYSTEM_PROMPT}

## Current Task: Revision Round

You have received the following natural language prompt from the user:
"{user_prompt}"

Flight information has been extracted:
- Flight Number: {flight_info.flight_number}
- Date: {flight_info.date}
- Disruption Event: {flight_info.disruption_event}

## Other Agents' Recommendations:

{other_recommendations}

## Your Revision Task:

1. Review the recommendations from other agents
2. Determine if any new information affects your crew compliance assessment
3. Revise your recommendation if warranted, or confirm your initial assessment
4. Maintain your domain priorities (safety first)

## Output Format:

Return your revised analysis using the AgentResponse schema with:
- agent_name: "crew_compliance"
- recommendation: Your revised or confirmed recommendation
- confidence: 0.0 to 1.0
- binding_constraints: List of non-negotiable safety constraints
- reasoning: Explanation including what you reviewed and why you revised/confirmed
- data_sources: List of tables/tools used
- extracted_flight_info: The flight info extracted above
- timestamp: Current UTC timestamp
- status: "success"

Remember: Your assessment is BINDING. Safety is non-negotiable."""
        
        # Step 4: Create agent with tools (no structured output here - agent returns natural response)
        agent = create_agent(
            model=llm,
            tools=all_tools,
        )
        
        # Step 5: Invoke agent
        start_time = datetime.now(timezone.utc)
        
        result = await agent.ainvoke({
            "messages": [
                {"role": "user", "content": agent_prompt}
            ]
        })
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Step 6: Extract agent's response
        final_message = result["messages"][-1]
        agent_response_text = str(final_message.content)
        
        logger.info(f"Agent completed in {duration:.2f}s")
        logger.debug(f"Agent response: {agent_response_text}")
        
        # Step 7: Parse agent response into AgentResponse format
        # For now, return a structured response based on the agent's text output
        # In a production system, you might use structured output here too
        
        return {
            "agent_name": "crew_compliance",
            "recommendation": agent_response_text,
            "confidence": 0.85,  # Default confidence, agent should specify
            "binding_constraints": [],  # Extract from agent response
            "reasoning": agent_response_text,
            "data_sources": ["flights", "CrewRoster", "CrewMembers"],
            "extracted_flight_info": extracted_flight_info,
            "timestamp": end_time.isoformat(),
            "status": "success",
            "duration_seconds": duration
        }

    except Exception as e:
        logger.error(f"Error in crew_compliance agent: {e}")
        logger.exception("Full traceback:")
        return {
            "agent_name": "crew_compliance",
            "recommendation": "Unable to complete analysis due to error",
            "confidence": 0.0,
            "binding_constraints": [],
            "reasoning": f"Agent execution error: {str(e)}",
            "data_sources": [],
            "extracted_flight_info": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        }
