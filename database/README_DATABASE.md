# SkyMarshal Database Package

Complete database setup for the SkyMarshal airline disruption management system.

---

## 📦 Package Contents

```
database/
├── README_DATABASE.md           # This file
├── schema/
│   └── database_schema.sql      # Complete DDL with tables, indexes, seed data
├── generators/
│   ├── generate_data.py         # Python script to generate realistic test data
│   └── csv_to_sql.py           # Convert CSV outputs to SQL INSERT statements
├── manager/
│   └── database.py             # Python database manager with async operations
├── output/                      # Generated CSV files (8 files)
│   ├── flights.csv
│   ├── passengers.csv
│   ├── bookings.csv
│   ├── baggage.csv
│   ├── cargo_shipments.csv
│   ├── cargo_flight_assignments.csv
│   ├── crew_members.csv
│   └── crew_roster.csv
└── docs/
    ├── SCHEMA_OVERVIEW.md       # Database design documentation
    ├── DATA_STATISTICS.md       # Generated data statistics
    └── IMPROVEMENT_IDEAS.md     # Ideas for iteration and enhancement
```

---

## 🎯 Quick Start

### 1. Create Database

```bash
# PostgreSQL
createdb etihad_aviation

# MySQL
mysql -u root -p -e "CREATE DATABASE etihad_aviation;"
```

### 2. Load Schema

```bash
# PostgreSQL
psql -d etihad_aviation -f schema/database_schema.sql

# MySQL
mysql -u root -p etihad_aviation < schema/database_schema.sql
```

### 3. Generate Data

```bash
cd generators/
python generate_data.py
```

This creates 8 CSV files in `output/` directory with:

- **35 flights** over 7 days
- **8,800+ passengers** with realistic profiles
- **199 cargo shipments** with AWB numbers
- **500+ crew members** with FTL tracking
- **Baggage, bookings, and roster data**

### 4. Import Data (PostgreSQL)

```bash
# Use the Python database manager or psql COPY commands
psql -d etihad_aviation -c "\COPY flights FROM 'output/flights.csv' CSV HEADER"
psql -d etihad_aviation -c "\COPY passengers FROM 'output/passengers.csv' CSV HEADER"
# ... repeat for all tables
```

---

## 📊 Database Overview

### Core Tables (14 total)

#### Aviation Operations

- **aircraft_types** - 9 aircraft (A380, A350, B787, etc.)
- **airports** - 13 airports (AUH hub + 12 destinations)
- **flights** - Flight schedules with status tracking

#### Passenger Management

- **frequent_flyer_tiers** - Etihad Guest tiers (Platinum, Gold, Silver, Bronze)
- **passengers** - Passenger profiles with loyalty data
- **bookings** - Reservations with PNR, seat, class
- **baggage** - Baggage tracking with tags

#### Cargo Operations

- **commodity_types** - 9 commodity types (GEN, PHA, PER, etc.)
- **cargo_shipments** - AWB-based shipments
- **cargo_flight_assignments** - Cargo-to-flight mapping

#### Crew Management

- **crew_positions** - 5 positions (CAPT, FO, CSM, PURSER, FA)
- **crew_members** - Crew profiles with licenses
- **crew_type_ratings** - Aircraft type qualifications
- **crew_roster** - Flight assignments with duty times

---

## 🔧 Configuration

### Data Generation Settings

Edit `generators/generate_data.py`:

```python
# Date range for flights
START_DATE = datetime(2026, 1, 30, 0, 0, 0)
FLIGHTS_PER_DAY = 5
TOTAL_DAYS = 7

# Load factor (passenger capacity utilization)
LOAD_FACTOR_MIN = 0.80
LOAD_FACTOR_MAX = 0.90

# Cargo per flight
CARGO_SHIPMENTS_MIN = 3
CARGO_SHIPMENTS_MAX = 8
```

### Database Connection

Edit `.env` file:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=etihad_aviation
DB_USER=postgres
DB_PASSWORD=your-password
```

---

## 📈 Current Data Statistics

### Flights

- **Total**: 35 flights
- **Period**: 7 days (5 flights/day)
- **Routes**: 12 destinations from/to AUH
- **Aircraft Mix**: 60% Widebody, 40% Narrowbody
- **Status**: All "Scheduled"

### Passengers

- **Total**: ~8,800 passengers
- **Load Factor**: 80-90% of capacity
- **Loyalty Distribution**:
  - 70% Regular passengers
  - 15% Frequent flyers (Platinum/Gold/Silver/Bronze)
  - 10% Connections
  - 3% VIP
  - 2% Medical assistance
- **Class Mix**: 80% Economy, 15% Business, 5% First

### Cargo

- **Total**: 199 shipments
- **AWB Prefix**: 607 (Etihad)
- **Commodity Distribution**:
  - 40% General cargo
  - 15% Pharma (SecureTech)
  - 10% Perishables
  - 10% Fresh (FreshForward)
  - 10% Live Animals (SafeGuard)
  - 10% E-Commerce
  - 5% Other (Human Remains, Valuables)
- **Status**: 75% Confirmed, 15% Queued, 10% Cancelled

### Crew

- **Total**: 500+ crew members
- **Positions**:
  - Captains: 70
  - First Officers: 70
  - Cabin Service Managers: 50
  - Flight Attendants: 350+
- **Base**: All based at AUH
- **Roster**: Full assignments for all 35 flights

---

## 🚀 Improvement Ideas

### 1. Enhanced Realism

#### Flight Operations

- [ ] Add actual flight times based on great circle distance
- [ ] Include realistic gate assignments per terminal
- [ ] Add aircraft registration numbers (tail numbers)
- [ ] Include flight delays and cancellations in historical data
- [ ] Add weather-related disruptions
- [ ] Include maintenance events (MEL items)

#### Passenger Data

- [ ] Add realistic connection patterns (multi-leg journeys)
- [ ] Include family/group bookings (same PNR)
- [ ] Add special meal requests (VGML, KSML, etc.)
- [ ] Include wheelchair/mobility assistance codes
- [ ] Add unaccompanied minors (UM)
- [ ] Include infant passengers

#### Cargo Enhancements

- [ ] Add ULD (Unit Load Device) assignments
- [ ] Include dangerous goods declarations (DGR)
- [ ] Add customs documentation
- [ ] Include multi-leg cargo routing
- [ ] Add cold chain temperature logs
- [ ] Include live animal health certificates

#### Crew Management

- [ ] Add FTL (Flight Time Limitations) calculations
- [ ] Include rest period tracking
- [ ] Add crew qualifications expiry dates
- [ ] Include standby crew pool
- [ ] Add crew preferences and seniority
- [ ] Include training records

### 2. Additional Tables

#### Operational

- [ ] **maintenance_events** - MEL items, AOG status
- [ ] **notams** - NOTAMs affecting airports/routes
- [ ] **weather_conditions** - Weather at airports
- [ ] **slot_restrictions** - ATC slot allocations
- [ ] **curfews** - Airport operating hours

#### Business

- [ ] **fare_classes** - Booking classes with rules
- [ ] **revenue_data** - Ticket prices and revenue
- [ ] **loyalty_transactions** - Miles earned/redeemed
- [ ] **ancillary_services** - Extra baggage, meals, seats
- [ ] **partner_airlines** - Codeshare and interline

#### Disruption Management

- [ ] **disruption_events** - Historical disruptions
- [ ] **recovery_scenarios** - Past recovery actions
- [ ] **passenger_notifications** - SMS/email logs
- [ ] **compensation_claims** - EU261 claims
- [ ] **hotel_accommodations** - Overnight stays

### 3. Data Quality Improvements

#### Constraints

- [ ] Add CHECK constraints for business rules
- [ ] Include triggers for data validation
- [ ] Add audit columns (created_by, updated_by)
- [ ] Include soft delete flags
- [ ] Add version tracking for critical records

#### Indexes

- [ ] Add composite indexes for common queries
- [ ] Include full-text search indexes
- [ ] Add spatial indexes for airport coordinates
- [ ] Include partial indexes for active records

#### Performance

- [ ] Add materialized views for reporting
- [ ] Include partitioning for large tables (by date)
- [ ] Add database statistics for query optimization
- [ ] Include connection pooling configuration

### 4. Integration Points

#### External Systems

- [ ] **SITA** - Flight information exchange
- [ ] **IATA** - NDC (New Distribution Capability)
- [ ] **Amadeus/Sabre** - GDS integration
- [ ] **Customs** - API/PNR data exchange
- [ ] **Immigration** - Passenger manifests

#### APIs

- [ ] RESTful API for flight status
- [ ] GraphQL API for complex queries
- [ ] WebSocket for real-time updates
- [ ] Webhook notifications for disruptions

### 5. Analytics & Reporting

#### Dashboards

- [ ] Real-time operational dashboard
- [ ] Disruption impact analysis
- [ ] Crew utilization reports
- [ ] Cargo revenue optimization
- [ ] Passenger satisfaction metrics

#### Machine Learning

- [ ] Delay prediction models
- [ ] Passenger no-show prediction
- [ ] Cargo demand forecasting
- [ ] Crew fatigue risk assessment
- [ ] Optimal recovery scenario ranking

### 6. Testing & Validation

#### Data Quality

- [ ] Add data validation scripts
- [ ] Include referential integrity checks
- [ ] Add business rule validation
- [ ] Include data profiling reports

#### Test Scenarios

- [ ] Generate disruption test cases
- [ ] Include edge cases (full flights, no alternatives)
- [ ] Add stress test data (multiple simultaneous disruptions)
- [ ] Include regulatory compliance test cases

---

## 🔍 Query Examples

### Find Flights with High-Value Passengers

```sql
SELECT f.flight_number, f.scheduled_departure,
       COUNT(CASE WHEN p.frequent_flyer_tier_id = 1 THEN 1 END) as platinum_count,
       COUNT(CASE WHEN p.is_vip THEN 1 END) as vip_count
FROM flights f
JOIN bookings b ON f.flight_id = b.flight_id
JOIN passengers p ON b.passenger_id = p.passenger_id
WHERE b.booking_status = 'Confirmed'
GROUP BY f.flight_id
HAVING COUNT(CASE WHEN p.frequent_flyer_tier_id = 1 THEN 1 END) > 5
ORDER BY platinum_count DESC;
```

### Find Flights with Temperature-Controlled Cargo

```sql
SELECT f.flight_number, f.scheduled_departure,
       COUNT(cs.shipment_id) as temp_controlled_shipments,
       SUM(cfa.weight_on_flight_kg) as total_weight_kg
FROM flights f
JOIN cargo_flight_assignments cfa ON f.flight_id = cfa.flight_id
JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
WHERE ct.temperature_controlled = TRUE
  AND cfa.loading_status = 'Planned'
GROUP BY f.flight_id
ORDER BY total_weight_kg DESC;
```

### Check Crew FTL Compliance

```sql
SELECT cm.employee_id, cm.first_name, cm.last_name,
       SUM(EXTRACT(EPOCH FROM (cr.duty_end - cr.duty_start))/3600) as total_duty_hours,
       COUNT(cr.roster_id) as flights_assigned
FROM crew_members cm
JOIN crew_roster cr ON cm.crew_id = cr.crew_id
WHERE DATE(cr.duty_start) = CURRENT_DATE
  AND cr.roster_status = 'Assigned'
GROUP BY cm.crew_id
HAVING SUM(EXTRACT(EPOCH FROM (cr.duty_end - cr.duty_start))/3600) > 12
ORDER BY total_duty_hours DESC;
```

### Find Passengers at Risk of Missing Connections

```sql
SELECT p.first_name, p.last_name, p.frequent_flyer_number,
       f.flight_number, f.scheduled_arrival,
       b.pnr, b.seat_number
FROM bookings b
JOIN passengers p ON b.passenger_id = p.passenger_id
JOIN flights f ON b.flight_id = f.flight_id
WHERE b.connection_at_risk = TRUE
  AND b.booking_status = 'Confirmed'
ORDER BY f.scheduled_arrival;
```

---

## 📚 Documentation Files

### SCHEMA_OVERVIEW.md

Detailed explanation of:

- Table relationships (ERD)
- Column descriptions
- Business rules
- Constraints and indexes

### DATA_STATISTICS.md

Statistics about generated data:

- Record counts per table
- Distribution analysis
- Data quality metrics
- Sample queries

### IMPROVEMENT_IDEAS.md

Detailed enhancement proposals:

- Priority ranking
- Implementation complexity
- Expected benefits
- Dependencies

---

## 🛠️ Tools & Utilities

### Database Manager (`manager/database.py`)

Async Python interface with methods:

- `get_flight_details(flight_id)` - Complete flight info
- `get_crew_duty_hours(crew_id, date)` - FTL calculations
- `find_alternative_flights(origin, dest, time)` - Rebooking options
- `get_all_flights()` - Flight list for demo

### Data Generator (`generators/generate_data.py`)

Configurable synthetic data generation:

- Realistic passenger profiles
- Etihad flight numbers (EY prefix)
- AWB numbers (607 prefix)
- Crew assignments with FTL tracking
- Cargo with commodity types

### CSV to SQL Converter (`generators/csv_to_sql.py`)

Convert CSV outputs to SQL INSERT statements:

- Batch inserts (100 rows per statement)
- Proper SQL escaping
- NULL handling
- Master import script

---

## 🔐 Security Considerations

### Current State

- No encryption at rest
- No row-level security
- No audit logging
- Plain text passwords in .env

### Recommended Improvements

- [ ] Enable PostgreSQL SSL/TLS
- [ ] Implement row-level security (RLS)
- [ ] Add audit triggers for sensitive tables
- [ ] Use secrets manager for credentials
- [ ] Implement data masking for PII
- [ ] Add database activity monitoring

---

## 📊 Performance Benchmarks

### Current Performance (35 flights, 8.8K passengers)

- Flight details query: ~50ms
- Alternative flights search: ~30ms
- Crew duty hours calculation: ~20ms
- Passenger list: ~100ms

### Optimization Targets

- [ ] Sub-10ms for single flight queries
- [ ] Sub-50ms for complex joins
- [ ] Support 1000+ concurrent connections
- [ ] Handle 10K+ flights in database

---

## 🧪 Testing

### Unit Tests

```bash
pytest tests/test_database.py
```

### Integration Tests

```bash
pytest tests/test_integration.py
```

### Load Tests

```bash
locust -f tests/load_test.py
```

---

## 📞 Support

For questions or issues:

1. Check documentation in `docs/` folder
2. Review query examples above
3. Examine schema comments in SQL file
4. Test with sample data in `output/` folder

---

## 📝 License

Proprietary - Hackathon Demo

---

**SkyMarshal Database Package - Ready for Iteration and Enhancement**
