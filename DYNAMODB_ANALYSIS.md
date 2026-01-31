# DynamoDB Tables and GSI Analysis for SkyMarshal

**Analysis Date:** January 31, 2026  
**Purpose:** Assess if current DynamoDB tables and GSIs are sufficient for all use cases

---

## Executive Summary

**Current State:**

- **23 DynamoDB tables** deployed
- **11 Global Secondary Indexes (GSIs)** across 6 tables
- **7 specialized agents** with specific data access patterns

**Assessment:** ⚠️ **GAPS IDENTIFIED** - Missing critical GSIs and potential query inefficiencies

---

## 1. Current Table Inventory

### Operational Tables (16)

| Table Name                      | Primary Key                 | Purpose                     | Agent Usage                      |
| ------------------------------- | --------------------------- | --------------------------- | -------------------------------- |
| `flights`                       | `flight_id` (N)             | Flight schedules and status | All agents                       |
| `bookings`                      | `booking_id` (N)            | Passenger bookings          | Guest Experience, Finance        |
| `passengers`                    | `passenger_id` (N)          | Passenger profiles          | Guest Experience                 |
| `CrewMembers`                   | `crew_id` (N)               | Crew member details         | Crew Compliance, Regulatory      |
| `CrewRoster`                    | `roster_id` (N)             | Crew flight assignments     | Crew Compliance, Regulatory      |
| `AircraftAvailability`          | `aircraftRegistration` (S)  | Aircraft MEL status         | Maintenance, Network             |
| `MaintenanceWorkOrders`         | `workorder_id` (S)          | Maintenance tasks           | Maintenance, Regulatory, Finance |
| `MaintenanceStaff`              | `roster_id` (N)             | Maintenance personnel       | Maintenance                      |
| `MaintenanceRoster`             | Composite                   | Staff work assignments      | Maintenance                      |
| `CargoShipments`                | `shipment_id` (N)           | Cargo shipment details      | Cargo, Finance                   |
| `CargoFlightAssignments`        | `assignment_id` (N)         | Cargo-to-flight mapping     | Cargo, Finance                   |
| `Baggage`                       | `baggage_id` (N)            | Baggage tracking            | Guest Experience                 |
| `Weather`                       | Composite                   | Weather forecasts           | Regulatory                       |
| `aircraft_swap_options`         | `aircraft_registration` (S) | Aircraft swap scenarios     | Network                          |
| `inbound_flight_impact`         | `scenario` (S)              | Network impact analysis     | Network                          |
| `disrupted_passengers_scenario` | `passenger_id` (N)          | Disruption scenarios        | Guest Experience                 |

### Supporting Tables (7)

- `disruption_events` - Historical disruptions
- `recovery_scenarios` - Recovery options
- `recovery_actions` - Action catalog
- `business_impact_assessment` - Impact data
- `safety_constraints` - Safety rules
- `financial_parameters` - Cost parameters
- `financial_transactions` - Transaction history
- `disruption_costs` - Cost tracking

---

## 2. Current GSI Inventory

### Flights Table (2 GSIs) ✅

| GSI Name                      | Keys                                                  | Use Case                        | Status    |
| ----------------------------- | ----------------------------------------------------- | ------------------------------- | --------- |
| `flight-number-date-index`    | `flight_number` (HASH), `scheduled_departure` (RANGE) | Query by flight number and date | ✅ Active |
| `aircraft-registration-index` | `aircraft_registration` (HASH)                        | Query flights by aircraft       | ✅ Active |

### Bookings Table (1 GSI) ⚠️

| GSI Name          | Keys               | Use Case                 | Status    |
| ----------------- | ------------------ | ------------------------ | --------- |
| `flight-id-index` | `flight_id` (HASH) | Query bookings by flight | ✅ Active |

**MISSING:**

- `passenger-flight-index` - Query bookings by passenger (defined in constants but not created)
- `flight-status-index` - Query bookings by flight and status (defined in constants but not created)

### CrewRoster Table (1 GSI) ✅

| GSI Name                | Keys                                   | Use Case                          | Status    |
| ----------------------- | -------------------------------------- | --------------------------------- | --------- |
| `flight-position-index` | `flight_id` (HASH), `position` (RANGE) | Query crew by flight and position | ✅ Active |

### MaintenanceWorkOrders Table (1 GSI) ✅

| GSI Name                      | Keys                          | Use Case                      | Status    |
| ----------------------------- | ----------------------------- | ----------------------------- | --------- |
| `aircraft-registration-index` | `aircraftRegistration` (HASH) | Query work orders by aircraft | ✅ Active |

### CargoFlightAssignments Table (2 GSIs) ⚠️

| GSI Name               | Keys                                           | Use Case                      | Status    |
| ---------------------- | ---------------------------------------------- | ----------------------------- | --------- |
| `flight-loading-index` | `flight_id` (HASH), `loading_priority` (RANGE) | Query cargo by flight         | ✅ Active |
| `shipment-index`       | `shipment_id` (HASH)                           | Track shipment across flights | ✅ Active |

**NOTE:** `loading_priority` field may not exist in data - needs verification

### Baggage Table (1 GSI) ⚠️

| GSI Name        | Keys                | Use Case                 | Status    |
| --------------- | ------------------- | ------------------------ | --------- |
| `booking-index` | `booking_id` (HASH) | Query baggage by booking | ✅ Active |

**MISSING:**

- `location-status-index` - Query baggage by location and status (defined in constants but not created)

### Passengers Table (0 GSIs) ❌

**MISSING:**

- No GSIs exist, but none are defined in constants either
- May need GSI for frequent flyer number lookups

### MaintenanceRoster Table (0 GSIs) ⚠️

**MISSING:**

- `workorder-shift-index` - Query staff by work order (defined in constants but not created)

---

## 3. Agent Query Pattern Analysis

### 3.1 Crew Compliance Agent

**Tables Accessed:** `flights`, `CrewRoster`, `CrewMembers`

**Query Patterns:**

- ✅ Query crew roster by flight → Uses `flight-position-index`
- ✅ Get crew member details → Direct key lookup
- ✅ Efficient access patterns

**Assessment:** **SUFFICIENT** ✅

---

### 3.2 Maintenance Agent

**Tables Accessed:** `flights`, `MaintenanceWorkOrders`, `MaintenanceStaff`, `MaintenanceRoster`, `AircraftAvailability`

**Query Patterns:**

- ✅ Get aircraft availability → Direct composite key lookup
- ✅ Query work orders by aircraft → Uses `aircraft-registration-index`
- ⚠️ Query maintenance roster by work order → **MISSING GSI** (`workorder-shift-index`)
- ✅ Get maintenance staff → Direct key lookup

**Assessment:** **GAPS IDENTIFIED** ⚠️

- Missing `workorder-shift-index` on `MaintenanceRoster` table
- Currently must use table scan or inefficient queries

---

### 3.3 Regulatory Agent

**Tables Accessed:** `flights`, `CrewRoster`, `MaintenanceWorkOrders`, `Weather`

**Query Patterns:**

- ✅ Get weather forecast → Direct composite key lookup
- ✅ Get flight details → Direct key lookup
- ✅ Query crew roster → Uses `flight-position-index`
- ✅ Query work orders → Uses `aircraft-registration-index`

**Assessment:** **SUFFICIENT** ✅

---

### 3.4 Network Agent

**Tables Accessed:** `flights`, `AircraftAvailability`

**Query Patterns:**

- ✅ Get inbound flight impact → Direct key lookup
- ✅ Query flights by aircraft → Uses `aircraft-registration-index`
- ✅ Query flights by number and date → Uses `flight-number-date-index`
- ✅ Get aircraft availability → Direct composite key lookup

**Assessment:** **SUFFICIENT** ✅

---

### 3.5 Guest Experience Agent

**Tables Accessed:** `flights`, `bookings`, `Baggage`, `passengers`

**Query Patterns:**

- ⚠️ Query bookings by passenger → **MISSING GSI** (`passenger-flight-index`)
- ✅ Query bookings by flight → Uses `flight-id-index`
- ⚠️ Query bookings by flight and status → **MISSING GSI** (`flight-status-index`)
- ✅ Query baggage by booking → Uses `booking-index`
- ⚠️ Query baggage by location/status → **MISSING GSI** (`location-status-index`)
- ✅ Get passenger details → Direct key lookup

**Assessment:** **CRITICAL GAPS** ❌

- Missing `passenger-flight-index` - forces table scan for passenger booking history
- Missing `flight-status-index` - inefficient filtering of bookings by status
- Missing `location-status-index` - cannot efficiently track mishandled baggage

---

### 3.6 Cargo Agent

**Tables Accessed:** `flights`, `CargoFlightAssignments`, `CargoShipments`

**Query Patterns:**

- ✅ Track shipment across flights → Uses `shipment-index`
- ⚠️ Query cargo by flight → Uses `flight-loading-index` (but `loading_priority` field may not exist)
- ✅ Get cargo shipment details → Direct key lookup

**Assessment:** **POTENTIAL ISSUE** ⚠️

- `flight-loading-index` uses `loading_priority` as range key, but this field may not exist in data
- May need to verify data schema or adjust GSI definition

---

### 3.7 Finance Agent

**Tables Accessed:** `flights`, `bookings`, `CargoFlightAssignments`, `MaintenanceWorkOrders`

**Query Patterns:**

- ✅ Get flight details → Direct key lookup
- ✅ Query bookings by flight → Uses `flight-id-index`
- ✅ Query cargo by flight → Uses `flight-loading-index`
- ✅ Query work orders by aircraft → Uses `aircraft-registration-index`

**Assessment:** **SUFFICIENT** ✅

---

## 4. Critical Gaps Summary

### High Priority (Blocking Agent Functionality) 🔴

1. **`passenger-flight-index` on `bookings` table**
   - **Impact:** Guest Experience agent cannot efficiently query passenger booking history
   - **Current Workaround:** Table scan (expensive and slow)
   - **Defined in constants:** ✅ Yes
   - **Created in DynamoDB:** ❌ No

2. **`flight-status-index` on `bookings` table**
   - **Impact:** Cannot efficiently filter bookings by status (e.g., "Confirmed" passengers)
   - **Current Workaround:** Client-side filtering after fetching all bookings
   - **Defined in constants:** ✅ Yes
   - **Created in DynamoDB:** ❌ No

3. **`workorder-shift-index` on `MaintenanceRoster` table**
   - **Impact:** Maintenance agent cannot efficiently query staff assignments by work order
   - **Current Workaround:** Table scan or inefficient queries
   - **Defined in constants:** ✅ Yes
   - **Created in DynamoDB:** ❌ No

### Medium Priority (Performance Impact) 🟡

4. **`location-status-index` on `Baggage` table**
   - **Impact:** Cannot efficiently track mishandled baggage by location
   - **Current Workaround:** Table scan or client-side filtering
   - **Defined in constants:** ✅ Yes
   - **Created in DynamoDB:** ❌ No

### Low Priority (Data Validation) 🟢

5. **Verify `loading_priority` field exists in `CargoFlightAssignments` data**
   - **Impact:** `flight-loading-index` may not work if field is missing
   - **Action:** Verify data schema and add field if missing

---

## 5. Additional Observations

### Table Scan Usage ⚠️

The `query_flights()` method in `dynamodb.py` uses table scan and is deprecated:

```python
def query_flights(self, **kwargs) -> List[Dict[str, Any]]:
    """DEPRECATED: Generic query method that uses table scan."""
```

- **Good:** Method is marked deprecated with warning
- **Action:** Ensure no agents are using this method

### Missing Tables

Based on SQL schema, these tables are defined but not in DynamoDB:

- `aircraft_types` - Aircraft specifications
- `airports` - Airport details
- `frequent_flyer_tiers` - Loyalty tiers
- `crew_positions` - Position definitions
- `commodity_types` - Cargo commodity types
- `crew_type_ratings` - Pilot type ratings

**Assessment:** These appear to be reference/lookup tables that may be:

- Hardcoded in application logic
- Stored in configuration files
- Not needed for disruption management use cases

### Passengers Table

- Has no GSIs currently
- May need GSI for frequent flyer number lookups if that becomes a query pattern
- Current direct key lookup by `passenger_id` is sufficient for existing use cases

---

## 6. Recommendations

### Immediate Actions (Week 1) 🔴

1. **Create Missing GSIs**

   ```bash
   # Run the GSI creation script for missing indexes
   python3 scripts/create_remaining_gsi.py
   ```

   Create these GSIs:
   - `passenger-flight-index` on `bookings` (passenger_id as HASH)
   - `flight-status-index` on `bookings` (flight_id as HASH, booking_status as RANGE)
   - `workorder-shift-index` on `MaintenanceRoster` (workorder_id as HASH, shift_start as RANGE)
   - `location-status-index` on `Baggage` (current_location as HASH, baggage_status as RANGE)

2. **Verify Data Schema**
   - Check if `loading_priority` field exists in `CargoFlightAssignments` data
   - If missing, either add field or modify GSI to use different range key

3. **Update Agent Code**
   - Ensure all agents use the new GSIs
   - Remove any table scan fallbacks
   - Add error handling for missing GSIs

### Short-term Actions (Week 2-3) 🟡

4. **Performance Testing**
   - Test query performance with new GSIs
   - Measure latency improvements
   - Validate GSI backfill completed successfully

5. **Code Audit**
   - Verify no agents are using deprecated `query_flights()` method
   - Ensure all queries use appropriate GSIs
   - Add logging for query performance metrics

6. **Documentation**
   - Update database documentation with GSI usage patterns
   - Document query patterns for each agent
   - Create troubleshooting guide for GSI issues

### Long-term Considerations (Month 2+) 🟢

7. **Monitoring & Optimization**
   - Set up CloudWatch alarms for GSI throttling
   - Monitor GSI consumed capacity
   - Optimize projection types (ALL vs KEYS_ONLY) based on usage

8. **Data Model Review**
   - Consider if reference tables (aircraft_types, airports) should be in DynamoDB
   - Evaluate if additional GSIs are needed for future features
   - Review composite key design for better query patterns

9. **Multi-Round Orchestration Support**
   - Verify GSIs support multi-round query patterns
   - Test concurrent agent queries under load
   - Optimize for parallel agent execution

---

## 7. Cost Impact Analysis

### Current GSI Count: 11 GSIs

### Proposed GSI Count: 15 GSIs (+4)

**Cost Considerations:**

- DynamoDB GSIs use PAY_PER_REQUEST billing (same as base tables)
- No additional storage cost (data is replicated)
- Read/write costs apply to GSI queries
- GSI backfill is one-time cost during creation

**Estimated Impact:**

- **Storage:** Minimal (GSIs use same data)
- **Read Costs:** Reduced (more efficient queries, fewer scans)
- **Write Costs:** Slightly increased (writes propagate to GSIs)
- **Overall:** Net positive (efficiency gains outweigh write overhead)

---

## 8. Conclusion

### Current State Assessment: ⚠️ **FUNCTIONAL BUT INCOMPLETE**

**Strengths:**

- Core query patterns for most agents are well-supported
- Critical GSIs for flights, crew, and maintenance exist
- No blocking issues for basic functionality

**Weaknesses:**

- Guest Experience agent has significant gaps (missing 3 GSIs)
- Maintenance roster queries are inefficient
- Some GSIs defined in code but not created in DynamoDB

**Risk Level:**

- **Production Readiness:** 🟡 Medium Risk
- **Performance:** 🟡 Degraded for guest experience queries
- **Scalability:** 🔴 High risk of throttling on table scans

### Recommendation: **CREATE MISSING GSIs BEFORE PRODUCTION DEPLOYMENT**

The system is functional but will experience performance issues and potential throttling under load, particularly for:

- Passenger booking history queries
- Baggage tracking by location
- Maintenance staff assignment queries

**Priority:** Create the 4 missing GSIs within the next week to ensure production readiness.

---

## Appendix A: GSI Creation Script

The missing GSIs can be created using the existing script:

```bash
cd /Users/sharanputhran/Learning/Hackathon
python3 scripts/create_remaining_gsi.py
```

Or manually using AWS CLI:

```bash
# Example: Create passenger-flight-index
aws dynamodb update-table \
  --table-name bookings \
  --attribute-definitions \
    AttributeName=passenger_id,AttributeType=N \
    AttributeName=flight_id,AttributeType=N \
  --global-secondary-index-updates \
    "[{\"Create\":{\"IndexName\":\"passenger-flight-index\",\"KeySchema\":[{\"AttributeName\":\"passenger_id\",\"KeyType\":\"HASH\"},{\"AttributeName\":\"flight_id\",\"KeyType\":\"RANGE\"}],\"Projection\":{\"ProjectionType\":\"ALL\"}}}]"
```

---

## Appendix B: Query Pattern Reference

### Efficient Query Patterns ✅

- Query by primary key (direct lookup)
- Query using GSI with HASH key
- Query using GSI with HASH + RANGE key

### Inefficient Query Patterns ❌

- Table scan (avoid at all costs)
- Query with filter expression only (no key condition)
- Client-side filtering of large result sets

### Best Practices

- Always use key conditions (not filter expressions alone)
- Use GSIs for alternate access patterns
- Limit result sets with pagination
- Use projection expressions to reduce data transfer
- Monitor consumed capacity and throttling

---

**End of Analysis**
