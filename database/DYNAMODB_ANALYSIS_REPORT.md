# DynamoDB Database Analysis Report

**Date:** January 31, 2026  
**Region:** us-east-1  
**Analysis Scope:** Data integrity, GSI configuration, and schema alignment

---

## Executive Summary

### Critical Issues Found

1. **Missing GSIs**: All required Global Secondary Indexes are missing from tables
2. **Data Type Mismatches**: Several CSV files have incorrect data types for GSI key attributes
3. **Missing Attributes**: Critical attributes required for GSIs are missing from CSV data
4. **Schema Inconsistencies**: Upload scripts have mismatched key schemas vs. actual table definitions

### Current State

- **31 tables exist** in DynamoDB
- **Data is present** in most tables (ItemCount shows 0 but scans return data - eventually consistent)
- **0 GSIs configured** across all tables
- **Key schema is correct** for most tables

---

## Detailed Findings

### 1. Missing Global Secondary Indexes

**All tables are missing their required GSIs:**

#### flights Table

- ❌ Missing: `flight-number-date-index` (HASH: flight_number, RANGE: scheduled_departure)
- ❌ Missing: `aircraft-registration-index` (HASH: aircraft_registration)
- ✅ Primary Key: flight_id (correct)
- ✅ Data: Present with correct attributes

#### bookings Table

- ❌ Missing: `flight-id-index` (HASH: flight_id)
- ✅ Primary Key: booking_id (correct)
- ✅ Data: Present
- ⚠️ Issue: flight_id is stored as Number (N) type - correct for GSI

#### CrewRoster Table

- ❌ Missing: `flight-position-index` (HASH: flight_id, RANGE: position)
- ✅ Primary Key: roster_id (correct)
- ✅ Data: Present
- ⚠️ Issue: CSV has `position_id` but GSI expects `position` attribute

#### MaintenanceWorkOrders Table

- ❌ Missing: `aircraft-registration-index` (HASH: aircraftRegistration)
- ✅ Primary Key: workorder_id (correct)
- ✅ Data: Present with aircraftRegistration attribute

#### CargoFlightAssignments Table

- ❌ Missing: `flight-loading-index` (HASH: flight_id, RANGE: loading_priority)
- ❌ Missing: `shipment-index` (HASH: shipment_id)
- ✅ Primary Key: assignment_id (correct)
- ✅ Data: Present
- ❌ **CRITICAL**: `loading_priority` attribute is **completely missing** from CSV and DynamoDB data

#### Baggage Table

- ❌ Missing: `booking-index` (HASH: booking_id)
- ❌ Missing: `location-status-index` (HASH: current_location, RANGE: status)
- ✅ Primary Key: baggage_id (correct)
- ✅ Data: Present

---

## 2. Data Quality Issues

### CargoFlightAssignments - Missing loading_priority

**CSV Schema:**

```
assignment_id,shipment_id,flight_id,sequence_number,pieces_on_flight,weight_on_flight_kg,loading_status,loaded_at,offloaded_at,uld_number
```

**Missing Attribute:** `loading_priority` (required for GSI)

**Impact:** Cannot create `flight-loading-index` GSI without this attribute

**Fix Required:** Add loading_priority column to CSV data generation

### CrewRoster - Attribute Name Mismatch

**CSV has:** `position_id`  
**GSI expects:** `position`

**Current Data Sample:**

```csv
roster_id,crew_id,flight_id,position_id,duty_start,...
1,30,1.0,1,2026-01-30 01:00:00,...
```

**Impact:** GSI creation will fail or not work as expected

**Fix Required:** Either:

- Option A: Rename `position_id` to `position` in CSV
- Option B: Update GSI definition to use `position_id`

### Bookings - Data Type Consistency

**Current State:** flight_id stored as Number (N) type ✅  
**CSV Data:** flight_id as integer ✅  
**Status:** Correct - no issues

---

## 3. Upload Script Issues

### cleanup_and_upload_dynamodb.py Issues

**Line 114-116:** MaintenanceWorkOrders configuration

```python
'MaintenanceWorkOrders': {
    'file': os.path.join(OUTPUT_DIR, 'aircraft_maintenance_workorders.csv'),
    'key_schema': [{'AttributeName': 'work_order_id', 'KeyType': 'HASH'}],  # ❌ WRONG
```

**Actual Table Schema:** `workorder_id` (not `work_order_id`)

**Line 56:** MaintenanceStaff configuration

```python
'MaintenanceStaff': {
    'file': os.path.join(OUTPUT_DIR, 'maintenance_roster.csv'),  # ❌ WRONG FILE
```

**Should be:** `maintenance_staff.csv`

---

## 4. GSI Creation Requirements

### Required GSIs by Table

| Table                  | GSI Name                    | Partition Key             | Sort Key                | Status                  |
| ---------------------- | --------------------------- | ------------------------- | ----------------------- | ----------------------- |
| flights                | flight-number-date-index    | flight_number (S)         | scheduled_departure (S) | ❌ Missing              |
| flights                | aircraft-registration-index | aircraft_registration (S) | -                       | ❌ Missing              |
| bookings               | flight-id-index             | flight_id (N)             | -                       | ❌ Missing              |
| CrewRoster             | flight-position-index       | flight_id (S)             | position (S)            | ❌ Missing              |
| MaintenanceWorkOrders  | aircraft-registration-index | aircraftRegistration (S)  | -                       | ❌ Missing              |
| CargoFlightAssignments | flight-loading-index        | flight_id (N)             | loading_priority (N)    | ❌ Missing + Data Issue |
| CargoFlightAssignments | shipment-index              | shipment_id (N)           | -                       | ❌ Missing              |
| Baggage                | booking-index               | booking_id (N)            | -                       | ❌ Missing              |
| Baggage                | location-status-index       | current_location (S)      | status (S)              | ❌ Missing              |

---

## 5. Recommended Fix Strategy

### Phase 1: Fix Data Issues (CRITICAL)

1. **Add loading_priority to CargoFlightAssignments CSV**
   - Regenerate `cargo_flight_assignments.csv` with loading_priority column
   - Use sequence_number or weight-based priority logic

2. **Fix CrewRoster position attribute**
   - Option A: Rename `position_id` → `position` in CSV
   - Option B: Update constants.py to use `position_id` in GSI definition

3. **Fix upload script key schema mismatches**
   - Change `work_order_id` → `workorder_id` in MaintenanceWorkOrders config
   - Change file path for MaintenanceStaff

### Phase 2: Create GSIs

1. **Run GSI creation script**

   ```bash
   cd scripts
   python3 create_gsis.py
   ```

2. **Wait for GSI backfill** (10-30 minutes depending on data size)

3. **Verify GSI status**
   ```bash
   python3 create_gsis.py --check-status
   ```

### Phase 3: Validate Data Integrity

1. **Run validation script**

   ```bash
   cd scripts
   python3 validate_dynamodb_data.py --output validation_report.json
   ```

2. **Review foreign key relationships**
3. **Test GSI query performance**

### Phase 4: Re-upload Data (if needed)

Only if Phase 1 fixes require data regeneration:

```bash
cd database
python3 async_import_dynamodb.py
```

---

## 6. Data Type Reference

### Correct Attribute Types for GSIs

| Attribute             | Type       | Used In                    |
| --------------------- | ---------- | -------------------------- |
| flight_number         | String (S) | flights GSI                |
| scheduled_departure   | String (S) | flights GSI                |
| aircraft_registration | String (S) | flights GSI                |
| flight_id             | Number (N) | bookings, cargo GSIs       |
| position              | String (S) | CrewRoster GSI             |
| aircraftRegistration  | String (S) | MaintenanceWorkOrders GSI  |
| loading_priority      | Number (N) | CargoFlightAssignments GSI |
| shipment_id           | Number (N) | CargoFlightAssignments GSI |
| booking_id            | Number (N) | Baggage GSI                |
| current_location      | String (S) | Baggage GSI                |
| status                | String (S) | Baggage GSI                |

---

## 7. Files Requiring Updates

### CSV Data Files

- ✅ `flights_enriched_mel.csv` - OK
- ✅ `bookings.csv` - OK
- ⚠️ `crew_roster_enriched.csv` - Needs position attribute fix
- ✅ `aircraft_maintenance_workorders.csv` - OK
- ❌ `cargo_flight_assignments.csv` - Missing loading_priority
- ✅ `baggage.csv` - OK (need to verify current_location and status exist)

### Python Scripts

- ⚠️ `database/cleanup_and_upload_dynamodb.py` - Fix key schema mismatches
- ⚠️ `database/async_import_dynamodb.py` - Fix key schema mismatches
- ✅ `scripts/create_gsis.py` - Ready to use
- ✅ `scripts/validate_dynamodb_data.py` - Ready to use

---

## 8. Next Steps

### Immediate Actions Required

1. ✅ **Review this analysis** with team
2. ❌ **Fix cargo_flight_assignments.csv** - Add loading_priority column
3. ❌ **Fix crew_roster_enriched.csv** - Resolve position vs position_id
4. ❌ **Update upload scripts** - Fix key schema mismatches
5. ❌ **Create all GSIs** - Run create_gsis.py
6. ❌ **Validate data** - Run validation script
7. ❌ **Test agent queries** - Ensure GSIs work correctly

### Estimated Timeline

- Data fixes: 1-2 hours
- GSI creation: 30-60 minutes (automated)
- Validation: 15 minutes
- Testing: 30 minutes

**Total: 2-3 hours**

---

## 9. Risk Assessment

### High Risk

- ❌ Missing loading_priority will block cargo agent functionality
- ❌ No GSIs means all queries are table scans (slow, expensive)

### Medium Risk

- ⚠️ position vs position_id mismatch may cause crew queries to fail
- ⚠️ Upload script mismatches could cause re-upload failures

### Low Risk

- ✅ Most data is present and correct
- ✅ Table schemas are correct
- ✅ Primary keys are working

---

## 10. Validation Checklist

Before marking as complete:

- [ ] All CSV files have correct attributes for GSIs
- [ ] All GSIs created and ACTIVE
- [ ] Sample queries use GSIs (no table scans)
- [ ] Foreign key relationships validated
- [ ] Agent-specific table access tested
- [ ] No orphaned records
- [ ] Data type consistency verified
- [ ] Upload scripts updated and tested

---

**Report Generated:** January 31, 2026  
**Analyst:** Kiro AI Assistant  
**Status:** Awaiting user approval for fixes
