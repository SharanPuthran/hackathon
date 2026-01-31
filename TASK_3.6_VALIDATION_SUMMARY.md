# Task 3.6 Validation Summary

## Validation Execution Date

2026-01-31 12:52:22 UTC

## Overall Summary

- **Total Issues**: 180
- **Errors**: 160
- **Warnings**: 19
- **Info**: 1

## Critical Issues Found

### 1. Missing Tables (4 errors)

- **Flights table**: Does not exist
- **Bookings table**: Does not exist

**Impact**: These are core tables required for the multi-round orchestration. Without them, agents cannot perform flight lookups or passenger queries.

**Fix**: These tables need to be created. However, based on the codebase structure, it appears the system is using different table names or the tables exist with different capitalization.

### 2. Missing GSIs (10 warnings)

The following GSIs are missing from tables:

- **CrewRoster**: Missing `flight-position-index`
- **MaintenanceWorkOrders**: Missing `aircraft-registration-index`
- **CargoFlightAssignments**: Missing `flight-loading-index` and `shipment-index`
- **Baggage**: Missing `booking-index`

**Impact**: Without these GSIs, queries will perform table scans, leading to poor performance and higher costs.

**Fix**: Run `scripts/create_gsis.py` to add the required GSIs.

### 3. Invalid Foreign Key References (154 errors)

- **CargoFlightAssignments table**: 154 records have invalid `flight_id` references
- These records reference flight IDs that don't exist in the Flights table

**Impact**: Data integrity issue. These orphaned records cannot be used for cargo analysis.

**Fix**: Either:

- Remove orphaned records, OR
- Add missing Flights entries (if the flights should exist)

### 4. IAM Permission Issues (11 issues)

- **Missing DynamoDB permissions**: The AgentCore runtime role lacks DynamoDB access permissions
- **Agent table access incomplete**: All 8 agents (including arbitrator) may not have access to their required tables

**Impact**: Agents will fail when attempting to query DynamoDB tables.

**Fix**: Update IAM role policies to grant DynamoDB read access to required tables.

## Issues by Table

| Table                  | Total | Errors | Warnings | Info |
| ---------------------- | ----- | ------ | -------- | ---- |
| Flights                | 2     | 2      | 0        | 0    |
| Bookings               | 2     | 2      | 0        | 0    |
| CrewRoster             | 2     | 0      | 2        | 0    |
| MaintenanceWorkOrders  | 2     | 0      | 2        | 0    |
| CargoFlightAssignments | 157   | 154    | 3        | 0    |
| Baggage                | 3     | 0      | 3        | 0    |
| GSI_VALIDATION         | 1     | 1      | 0        | 0    |
| IAM                    | 11    | 1      | 9        | 1    |

## Recommended Fix Priority

### Priority 1: Table Name Investigation

The validation script reports that `Flights` and `Bookings` tables don't exist, but the system has been working. This suggests:

1. Tables may exist with different names (e.g., lowercase `flights`, `bookings`)
2. The validation script may be using incorrect table names

**Action**: Verify actual table names in DynamoDB and update constants if needed.

### Priority 2: Create Missing GSIs

Once table names are confirmed, create the missing GSIs using the `create_gsis.py` script.

**Action**: Run `python3 scripts/create_gsis.py`

### Priority 3: Fix IAM Permissions

Update the AgentCore runtime role to include DynamoDB permissions.

**Action**: Add DynamoDB read permissions to the role policy.

### Priority 4: Clean Up Orphaned Records

Remove or fix the 154 orphaned CargoFlightAssignments records.

**Action**: Run data cleanup script or manually remove invalid records.

## Next Steps

1. Investigate table naming (Priority 1)
2. Update validation script if table names are incorrect
3. Re-run validation to get accurate results
4. Fix remaining issues based on updated validation results
