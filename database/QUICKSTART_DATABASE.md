# Database Quick Start Guide

Get the SkyMarshal database up and running in 5 minutes.

---

## ⚡ 5-Minute Setup

### Step 1: Create Database (30 seconds)

```bash
# PostgreSQL
createdb etihad_aviation

# MySQL
mysql -u root -p -e "CREATE DATABASE etihad_aviation;"
```

### Step 2: Load Schema (1 minute)

```bash
# PostgreSQL
psql -d etihad_aviation -f schema/database_schema.sql

# MySQL
mysql -u root -p etihad_aviation < schema/database_schema.sql
```

### Step 3: Generate Data (2 minutes)

```bash
cd generators/
python generate_data.py
```

**Output**: 8 CSV files in `output/` directory

### Step 4: Verify (30 seconds)

```bash
# PostgreSQL
psql -d etihad_aviation -c "SELECT COUNT(*) FROM flights;"
# Expected: 35

psql -d etihad_aviation -c "SELECT COUNT(*) FROM passengers;"
# Expected: ~8800
```

### Step 5: Test Query (1 minute)

```sql
-- Find flights with most VIP passengers
SELECT f.flight_number,
       COUNT(p.passenger_id) as vip_count
FROM flights f
JOIN bookings b ON f.flight_id = b.flight_id
JOIN passengers p ON b.passenger_id = p.passenger_id
WHERE p.is_vip = TRUE
GROUP BY f.flight_id
ORDER BY vip_count DESC
LIMIT 5;
```

---

## 📦 What You Get

### Database Tables (14)

✅ 35 flights over 7 days  
✅ 8,800+ passengers with loyalty tiers  
✅ 199 cargo shipments with AWB numbers  
✅ 500+ crew members with FTL tracking  
✅ Complete bookings, baggage, and roster data

### Documentation (4 files)

✅ README_DATABASE.md - Complete guide  
✅ SCHEMA_OVERVIEW.md - Table details  
✅ DATA_STATISTICS.md - Data analysis  
✅ IMPROVEMENT_IDEAS.md - 30+ enhancement ideas

### Tools (3 scripts)

✅ generate_data.py - Data generator  
✅ csv_to_sql.py - CSV to SQL converter  
✅ database.py - Python async manager

---

## 🔧 Configuration

### Environment Variables

Create `.env` file:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=etihad_aviation
DB_USER=postgres
DB_PASSWORD=your-password

# AWS (for SkyMarshal system)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

### Data Generation Settings

Edit `generators/generate_data.py`:

```python
# Customize these values
START_DATE = datetime(2026, 1, 30, 0, 0, 0)
FLIGHTS_PER_DAY = 5
TOTAL_DAYS = 7
LOAD_FACTOR_MIN = 0.80
LOAD_FACTOR_MAX = 0.90
```

---

## 🎯 Common Tasks

### Regenerate Data

```bash
cd generators/
python generate_data.py
```

### Import CSV to Database

```bash
# PostgreSQL
psql -d etihad_aviation -c "\COPY flights FROM 'output/flights.csv' CSV HEADER"
psql -d etihad_aviation -c "\COPY passengers FROM 'output/passengers.csv' CSV HEADER"
psql -d etihad_aviation -c "\COPY bookings FROM 'output/bookings.csv' CSV HEADER"
psql -d etihad_aviation -c "\COPY baggage FROM 'output/baggage.csv' CSV HEADER"
psql -d etihad_aviation -c "\COPY cargo_shipments FROM 'output/cargo_shipments.csv' CSV HEADER"
psql -d etihad_aviation -c "\COPY cargo_flight_assignments FROM 'output/cargo_flight_assignments.csv' CSV HEADER"
psql -d etihad_aviation -c "\COPY crew_members FROM 'output/crew_members.csv' CSV HEADER"
psql -d etihad_aviation -c "\COPY crew_roster FROM 'output/crew_roster.csv' CSV HEADER"
```

### Convert CSV to SQL

```bash
cd generators/
python csv_to_sql.py
# Creates SQL INSERT files in sql_inserts/ directory
```

### Reset Database

```bash
# Drop and recreate
dropdb etihad_aviation
createdb etihad_aviation
psql -d etihad_aviation -f schema/database_schema.sql
```

---

## 🔍 Useful Queries

### Flight Summary

```sql
SELECT
    f.flight_number,
    f.scheduled_departure,
    at.aircraft_code,
    o.iata_code as origin,
    d.iata_code as destination,
    COUNT(b.booking_id) as passengers,
    COUNT(cs.shipment_id) as cargo_shipments
FROM flights f
JOIN aircraft_types at ON f.aircraft_type_id = at.aircraft_type_id
JOIN airports o ON f.origin_airport_id = o.airport_id
JOIN airports d ON f.destination_airport_id = d.airport_id
LEFT JOIN bookings b ON f.flight_id = b.flight_id
LEFT JOIN cargo_flight_assignments cfa ON f.flight_id = cfa.flight_id
LEFT JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
GROUP BY f.flight_id, at.aircraft_code, o.iata_code, d.iata_code
ORDER BY f.scheduled_departure;
```

### High-Value Passengers

```sql
SELECT
    p.first_name,
    p.last_name,
    p.frequent_flyer_number,
    fft.tier_name,
    b.booking_class,
    f.flight_number
FROM passengers p
JOIN bookings b ON p.passenger_id = b.passenger_id
JOIN flights f ON b.flight_id = f.flight_id
LEFT JOIN frequent_flyer_tiers fft ON p.frequent_flyer_tier_id = fft.tier_id
WHERE p.is_vip = TRUE OR p.frequent_flyer_tier_id = 1
ORDER BY fft.tier_level DESC, b.booking_class;
```

### Temperature-Controlled Cargo

```sql
SELECT
    f.flight_number,
    cs.awb_number,
    ct.commodity_name,
    cfa.weight_on_flight_kg,
    cs.shipment_status
FROM flights f
JOIN cargo_flight_assignments cfa ON f.flight_id = cfa.flight_id
JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
WHERE ct.temperature_controlled = TRUE
ORDER BY f.scheduled_departure;
```

### Crew FTL Check

```sql
SELECT
    cm.employee_id,
    cm.first_name,
    cm.last_name,
    cp.position_name,
    COUNT(cr.roster_id) as flights_assigned,
    SUM(EXTRACT(EPOCH FROM (cr.duty_end - cr.duty_start))/3600) as total_duty_hours
FROM crew_members cm
JOIN crew_roster cr ON cm.crew_id = cr.crew_id
JOIN crew_positions cp ON cm.position_id = cp.position_id
WHERE DATE(cr.duty_start) = CURRENT_DATE
GROUP BY cm.crew_id, cp.position_name
ORDER BY total_duty_hours DESC;
```

---

## 🐛 Troubleshooting

### Issue: "Database does not exist"

```bash
# Create it first
createdb etihad_aviation
```

### Issue: "Permission denied"

```bash
# Check PostgreSQL user permissions
psql -d postgres -c "ALTER USER postgres WITH PASSWORD 'your-password';"
```

### Issue: "CSV import fails"

```bash
# Check file paths are correct
ls -la output/*.csv

# Ensure CSV files have headers
head -n 1 output/flights.csv
```

### Issue: "Foreign key constraint fails"

```bash
# Import in correct order:
# 1. Reference tables (aircraft_types, airports, etc.)
# 2. Flights
# 3. Passengers
# 4. Bookings
# 5. Baggage
# 6. Cargo
# 7. Crew
```

### Issue: "Python script fails"

```bash
# Install dependencies
pip install -r requirements.txt

# Check Python version
python --version  # Should be 3.11+
```

---

## 📚 Next Steps

### 1. Explore Documentation

- Read `README_DATABASE.md` for complete guide
- Check `SCHEMA_OVERVIEW.md` for table details
- Review `DATA_STATISTICS.md` for data analysis

### 2. Customize Data

- Edit `generators/generate_data.py`
- Adjust flight counts, load factors, etc.
- Regenerate data

### 3. Implement Improvements

- Review `IMPROVEMENT_IDEAS.md`
- Pick P0 quick wins first
- Implement incrementally

### 4. Integrate with SkyMarshal

- Use `manager/database.py` for async operations
- Connect to agents
- Test disruption scenarios

---

## 🎓 Learning Resources

### PostgreSQL

- [Official Docs](https://www.postgresql.org/docs/)
- [Tutorial](https://www.postgresqltutorial.com/)

### MySQL

- [Official Docs](https://dev.mysql.com/doc/)
- [Tutorial](https://www.mysqltutorial.org/)

### Python AsyncPG

- [AsyncPG Docs](https://magicstack.github.io/asyncpg/)
- [Examples](https://github.com/MagicStack/asyncpg/tree/master/examples)

---

## 💡 Pro Tips

### Tip 1: Use Transactions

```sql
BEGIN;
-- Your queries here
COMMIT;
-- Or ROLLBACK if something fails
```

### Tip 2: Explain Query Plans

```sql
EXPLAIN ANALYZE
SELECT * FROM flights WHERE flight_number = 'EY551';
```

### Tip 3: Monitor Performance

```sql
-- PostgreSQL
SELECT * FROM pg_stat_user_tables;

-- MySQL
SHOW TABLE STATUS;
```

### Tip 4: Backup Regularly

```bash
# PostgreSQL
pg_dump etihad_aviation > backup.sql

# MySQL
mysqldump -u root -p etihad_aviation > backup.sql
```

### Tip 5: Use Indexes Wisely

```sql
-- Check index usage
SELECT * FROM pg_stat_user_indexes;

-- Create index if needed
CREATE INDEX idx_custom ON table_name(column_name);
```

---

## 🚀 Ready to Iterate!

You now have:

- ✅ Working database with realistic data
- ✅ Complete documentation
- ✅ Data generation tools
- ✅ 30+ improvement ideas
- ✅ Query examples

**Start iterating and make it better!**

---

**Quick Start Version**: 1.0  
**Last Updated**: 2026-01-30  
**Setup Time**: 5 minutes
