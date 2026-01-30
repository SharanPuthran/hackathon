# Etihad Airways Aviation Database - Synthetic Data Project

Complete database schema and synthetic data generator for hackathon aviation operations including flights, passengers, cargo shipments, and crew management.

## 📊 Project Overview

This project provides a comprehensive aviation database design for **Etihad Airways** operations with realistic synthetic data generation capabilities.

### Key Statistics
- **35 Flights** (5 flights/day × 7 days)
- **8,820 Passengers** with 80-90% load factor
- **11,052 Baggage Items** tracked end-to-end
- **199 Cargo Shipments** with AWB prefix 607
- **715 Crew Members** (pilots and cabin crew)
- **448 Crew Roster Assignments** across all flights

---

## 🗂️ Database Schema

### Tables (14 Total)

#### Core Aviation (3 tables)
1. **aircraft_types** - Aircraft configurations (A380, B787, A320, etc.)
2. **airports** - Airport master data (AUH hub + 12 destinations)
3. **flights** - Flight schedules with EY prefix

#### Passenger Management (4 tables)
4. **frequent_flyer_tiers** - Etihad Guest loyalty tiers
5. **passengers** - Passenger profiles
6. **bookings** - Flight reservations with PNR
7. **baggage** - Baggage tracking

#### Cargo Operations (3 tables)
8. **commodity_types** - Cargo categories
9. **cargo_shipments** - AWB and shipment details
10. **cargo_flight_assignments** - Cargo-to-flight routing

#### Crew Management (4 tables)
11. **crew_positions** - Job positions/roles
12. **crew_members** - Crew employee records
13. **crew_type_ratings** - Aircraft certifications
14. **crew_roster** - Flight duty assignments

---

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- MySQL 8.0+ or PostgreSQL 13+

### Step 1: Create Database

```bash
# For MySQL
mysql -u root -p

CREATE DATABASE etihad_aviation;
USE etihad_aviation;
SOURCE database_schema.sql;
```

```bash
# For PostgreSQL
psql -U postgres

CREATE DATABASE etihad_aviation;
\c etihad_aviation
\i database_schema.sql
```

### Step 2: Generate Synthetic Data

```bash
python3 generate_data.py
```

This will create an `output/` directory with 8 CSV files containing all synthetic data.

### Step 3: Load Data into Database

#### Option A: Manual Import (MySQL)
```sql
LOAD DATA LOCAL INFILE 'output/flights.csv'
INTO TABLE flights
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

-- Repeat for other tables...
```

#### Option B: Using SQL Inserts
A separate script `import_data.py` can generate SQL INSERT statements from the CSV files (see below).

---

## 📁 Project Structure

```
etihad-aviation-db/
├── README.md                    # This file
├── database_schema.sql          # Complete DDL with seed data
├── generate_data.py             # Python data generator
├── import_data.py               # CSV to SQL converter (optional)
└── output/                      # Generated CSV files
    ├── flights.csv
    ├── passengers.csv
    ├── bookings.csv
    ├── baggage.csv
    ├── cargo_shipments.csv
    ├── cargo_flight_assignments.csv
    ├── crew_members.csv
    └── crew_roster.csv
```

---

## 🎯 Data Features

### Flights
- **Flight Numbers**: EY + 3-4 random digits (e.g., EY123, EY4567)
- **Aircraft Mix**: 60% Widebody / 40% Narrowbody
- **Hub Operations**: All flights originate from or arrive at AUH
- **Date Range**: 2026-01-30 to 2026-02-05

### Passengers
- **Load Factor**: 80-90% of aircraft capacity
- **Mix**: 70% regular, 15% frequent flyers, 10% connections, 3% VIP, 2% medical
- **Loyalty Tiers**: Platinum, Gold, Silver, Bronze
- **Realistic Names**: Multi-cultural first/last names
- **Complete Profiles**: Passport, nationality, contact info

### Baggage
- **Economy**: 1 checked bag (20-23 kg)
- **Business**: 2 checked bags (28-32 kg each)
- **First Class**: 3 checked bags (32 kg each)
- **Priority Handling**: For VIP and high-tier frequent flyers

### Cargo
- **AWB Format**: 607 + 8 digits (e.g., 60712345678)
- **Commodity Types**: 
  - General Cargo (40%)
  - Pharma - SecureTech (15%)
  - Perishables/Fresh - FreshForward (20%)
  - Live Animals - SafeGuard/SkyStables (10%)
  - E-Commerce (10%)
  - Human Remains, Valuables (5%)
- **Shipment Status**: 75% Confirmed, 15% Queued, 10% Cancelled
- **Routing**: Direct, via AUH, or multi-leg

### Crew
- **Cockpit Crew**: Captain + First Officer per flight
- **Cabin Crew**: 4-16 based on aircraft type
- **Realistic Assignments**: Duty start/end times around flight schedule
- **Base**: All crew based at AUH

---

## 📊 Sample Queries

### Find all widebody flights on a specific day
```sql
SELECT f.flight_number, a.aircraft_code, 
       f.scheduled_departure, f.scheduled_arrival,
       orig.iata_code AS origin, dest.iata_code AS destination
FROM flights f
JOIN aircraft_types a ON f.aircraft_type_id = a.aircraft_type_id
JOIN airports orig ON f.origin_airport_id = orig.airport_id
JOIN airports dest ON f.destination_airport_id = dest.airport_id
WHERE a.category = 'Widebody'
  AND DATE(f.scheduled_departure) = '2026-01-30';
```

### Get passenger count by flight
```sql
SELECT f.flight_number, COUNT(b.booking_id) AS passenger_count,
       a.passenger_capacity,
       ROUND(COUNT(b.booking_id) / a.passenger_capacity * 100, 2) AS load_factor_pct
FROM flights f
JOIN bookings b ON f.flight_id = b.flight_id
JOIN aircraft_types a ON f.aircraft_type_id = a.aircraft_type_id
GROUP BY f.flight_id
ORDER BY load_factor_pct DESC;
```

### Find VIP passengers with connections at risk
```sql
SELECT p.first_name, p.last_name, b.pnr,
       f.flight_number, p.frequent_flyer_tier_id
FROM passengers p
JOIN bookings b ON p.passenger_id = b.passenger_id
JOIN flights f ON b.flight_id = f.flight_id
WHERE p.is_vip = 1 AND b.connection_at_risk = 1;
```

### Cargo shipments by commodity type
```sql
SELECT c.commodity_name, 
       COUNT(cs.shipment_id) AS shipment_count,
       SUM(cs.total_pieces) AS total_pieces,
       ROUND(SUM(cs.total_weight_kg), 2) AS total_weight_kg
FROM cargo_shipments cs
JOIN commodity_types c ON cs.commodity_type_id = c.commodity_type_id
GROUP BY c.commodity_name
ORDER BY total_weight_kg DESC;
```

### Crew roster for a specific flight
```sql
SELECT cr.roster_id, cm.first_name, cm.last_name,
       cp.position_name, cr.duty_start, cr.duty_end
FROM crew_roster cr
JOIN crew_members cm ON cr.crew_id = cm.crew_id
JOIN crew_positions cp ON cr.position_id = cp.position_id
JOIN flights f ON cr.flight_id = f.flight_id
WHERE f.flight_number = 'EY123'
ORDER BY cp.is_cockpit_crew DESC, cp.position_name;
```

---

## 🔧 Customization

### Modify Date Range
Edit `generate_data.py`:
```python
START_DATE = datetime(2026, 2, 1, 0, 0, 0)  # Change start date
TOTAL_DAYS = 14  # Change number of days
```

### Adjust Flights Per Day
```python
FLIGHTS_PER_DAY = 10  # Change from 5 to 10
```

### Change Load Factor
```python
LOAD_FACTOR_MIN = 0.85  # Minimum 85%
LOAD_FACTOR_MAX = 0.95  # Maximum 95%
```

### Modify Cargo Volume
```python
CARGO_SHIPMENTS_MIN = 5  # Minimum per flight
CARGO_SHIPMENTS_MAX = 12  # Maximum per flight
```

---

## 📈 Data Validation

The generated data ensures:

✅ All flights involve AUH (hub operations)  
✅ Flight numbers start with "EY"  
✅ AWB numbers have prefix "607" with 8-digit master document numbers  
✅ Load factors between 80-90%  
✅ Realistic baggage weights by class  
✅ No duplicate PNRs, passports, or AWB numbers  
✅ Crew assignments don't overlap in time  
✅ Cargo pieces/weight on flights ≤ shipment totals  

---

## 🎓 Use Cases

This database is perfect for:

- **Hackathon Projects**: Pre-populated realistic aviation data
- **ML Model Training**: Predicting delays, load factors, connection risks
- **Dashboard Development**: Aviation operations dashboards
- **API Testing**: Backend services for flight/cargo/crew management
- **Educational Purposes**: Learning SQL and database design
- **Performance Testing**: Large-scale data scenarios

---

## 📝 License

This is a synthetic dataset created for educational and hackathon purposes. All data is randomly generated and does not represent real Etihad Airways operations.

---

## 🙋‍♂️ Support

For questions or issues with the data generator:

1. Review the schema documentation in `database_schema.sql`
2. Check the ER diagram in the artifacts folder
3. Examine sample data in the `output/` CSV files

---

## 🎉 Credits

Database design and data generator created for Etihad Airways hackathon project.

**Generated Data Summary:**
- 35 flights across 7 days
- 8,820 unique passengers
- 199 cargo shipments
- 715 crew members with realistic assignments

Happy hacking! ✈️
