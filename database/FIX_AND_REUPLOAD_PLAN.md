# DynamoDB Fix and Re-upload Plan

**Date:** January 31, 2026  
**Objective:** Fix data issues, re-upload to DynamoDB, create GSIs, and validate

---

## Issues to Fix

### 1. CSV Data Issues

#### A. CargoFlightAssignments - Missing loading_priority

- **File:** `database/output/cargo_flight_assignments.csv`
- **Issue:** Missing `loading_priority` column required for GSI
- **Fix:** Add loading_priority based on sequence_number (1-based priority)

#### B. CrewRoster - position_id vs position

- **File:** `database/output/crew_roster_enriched.csv`
- **Issue:** CSV has `position_id` but GSI expects `position`
- **Fix:** Add `position` column with string values (Captain, FO, CM, SI, etc.)

#### C. Baggage - baggage_status vs status

- **File:** `database/output/baggage.csv`
- **Issue:** CSV has `baggage_status` but GSI expects `status`
- **Fix:** Add `status` column (copy from baggage_status)

### 2. Upload Script Issues

#### A. cleanup_and_upload_dynamodb.py

- **Line 114:** `work_order_id` should be `workorder_id`
- **Line 56:** Wrong file for MaintenanceStaff

#### B. async_import_dynamodb.py

- **Line 89:** `work_order_id` should be `workorder_id`
- **Line 82:** Wrong file for MaintenanceStaff

---

## Execution Plan

### Phase 1: Fix CSV Data Files ✓

1. Add loading_priority to cargo_flight_assignments.csv
2. Add position to crew_roster_enriched.csv
3. Add status to baggage.csv

### Phase 2: Fix Upload Scripts ✓

1. Update cleanup_and_upload_dynamodb.py
2. Update async_import_dynamodb.py

### Phase 3: Re-upload Data to DynamoDB ✓

1. Run async_import_dynamodb.py (faster)
2. Verify data uploaded correctly

### Phase 4: Create GSIs ✓

1. Run create_gsis.py
2. Wait for GSIs to become ACTIVE
3. Verify all GSIs created

### Phase 5: Validate Everything ✓

1. Run validate_dynamodb_data.py
2. Test sample queries
3. Verify no table scans

---

## Detailed Steps

### Step 1: Fix cargo_flight_assignments.csv

```python
import pandas as pd

# Read CSV
df = pd.read_csv('database/output/cargo_flight_assignments.csv')

# Add loading_priority based on sequence_number
df['loading_priority'] = df['sequence_number']

# Save
df.to_csv('database/output/cargo_flight_assignments.csv', index=False)
```

### Step 2: Fix crew_roster_enriched.csv

```python
import pandas as pd

# Read CSV
df = pd.read_csv('database/output/crew_roster_enriched.csv')

# Map position_id to position names
position_map = {
    1: 'Captain',
    2: 'First Officer',
    3: 'Cabin Manager',
    4: 'Senior FA',
    5: 'Flight Attendant'
}

df['position'] = df['position_id'].map(position_map).fillna('Unknown')

# Save
df.to_csv('database/output/crew_roster_enriched.csv', index=False)
```

### Step 3: Fix baggage.csv

```python
import pandas as pd

# Read CSV
df = pd.read_csv('database/output/baggage.csv')

# Add status column (copy from baggage_status)
df['status'] = df['baggage_status']

# Save
df.to_csv('database/output/baggage.csv', index=False)
```

### Step 4: Update Upload Scripts

Fix key schema mismatches in both scripts.

### Step 5: Re-upload Data

```bash
cd database
python3 async_import_dynamodb.py
```

### Step 6: Create GSIs

```bash
cd scripts
python3 create_gsis.py
```

### Step 7: Validate

```bash
cd scripts
python3 validate_dynamodb_data.py --output ../database/validation_report.json
```

---

## Success Criteria

- [ ] All CSV files have required attributes
- [ ] All data uploaded to DynamoDB (no errors)
- [ ] All 9 GSIs created and ACTIVE
- [ ] Validation script shows 0 errors
- [ ] Sample queries use GSIs (no table scans)
- [ ] All agents can query their required tables

---

**Status:** Ready to execute
