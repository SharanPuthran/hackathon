# Etihad Airways Database Schema Design

Complete database design for aviation operations including flights, passengers, cargo shipments, and crew management with synthetic data generation for hackathon.

## Overview

This database design supports:
- **35 flights** (5 per day for 7 days) - EY prefix with 3-4 digit flight numbers
- **Two aircraft categories**: Widebody and Narrowbody with specific models
- **Passenger operations**: 80-90% load factor, baggage, connections, VIP/medical status
- **Etihad Guest loyalty program**: Platinum, Gold, Silver, Bronze tiers
- **Cargo operations**: Multiple commodity types, AWB prefix 607, 8-digit master document numbers
- **Crew rostering**: Based on aircraft type and route
- **Hub operations**: Abu Dhabi (AUH) as primary hub

---

## Proposed Database Schema

### Core Aviation Entities

#### 1. **aircraft_types**
Master table for aircraft configurations and capacities.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| aircraft_type_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| aircraft_code | VARCHAR(20) | UNIQUE, NOT NULL | Aircraft model (A380, B787-9, etc.) |
| category | ENUM | NOT NULL | 'Widebody' or 'Narrowbody' |
| passenger_capacity | INT | NOT NULL, CHECK (> 0) | Maximum passenger seats |
| cargo_capacity_kg | DECIMAL(10,2) | NOT NULL, CHECK (> 0) | Cargo capacity in kg |
| crew_required_pilots | INT | NOT NULL, DEFAULT 2 | Minimum pilots required |
| crew_required_cabin | INT | NOT NULL, CHECK (> 0) | Minimum cabin crew required |
| max_range_km | INT | NULL | Maximum flight range |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

**Sample Data**:
- Widebody: A380 (516 pax), A350 (283 pax), B787-9 (289 pax), B787-10 (318 pax), B777X (426 pax)
- Narrowbody: A320 (154 pax), A320-NEO (162 pax), A321 (185 pax), A321LR (206 pax)

---

#### 2. **airports**
Master table for airport information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| airport_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| iata_code | CHAR(3) | UNIQUE, NOT NULL | Airport IATA code (AUH, DXB, etc.) |
| icao_code | CHAR(4) | UNIQUE, NOT NULL | Airport ICAO code |
| airport_name | VARCHAR(200) | NOT NULL | Full airport name |
| city | VARCHAR(100) | NOT NULL | City name |
| country | VARCHAR(100) | NOT NULL | Country name |
| timezone | VARCHAR(50) | NOT NULL | IANA timezone |
| latitude | DECIMAL(10,6) | NOT NULL | Geographic coordinate |
| longitude | DECIMAL(10,6) | NOT NULL | Geographic coordinate |
| is_hub | BOOLEAN | DEFAULT FALSE | Is Etihad hub |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

**Important**: AUH (Abu Dhabi International Airport) should have `is_hub = TRUE`

---

#### 3. **flights**
Core table for flight schedules.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| flight_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| flight_number | VARCHAR(10) | NOT NULL | Format: EY + 3-4 digits (EY123, EY1234) |
| aircraft_type_id | INT | FOREIGN KEY → aircraft_types | Aircraft assigned |
| origin_airport_id | INT | FOREIGN KEY → airports | Departure airport |
| destination_airport_id | INT | FOREIGN KEY → airports | Arrival airport |
| scheduled_departure | DATETIME | NOT NULL | Scheduled departure time (UTC) |
| scheduled_arrival | DATETIME | NOT NULL | Scheduled arrival time (UTC) |
| actual_departure | DATETIME | NULL | Actual departure time (UTC) |
| actual_arrival | DATETIME | NULL | Actual arrival time (UTC) |
| flight_status | ENUM | NOT NULL, DEFAULT 'Scheduled' | 'Scheduled', 'Boarding', 'Departed', 'Arrived', 'Delayed', 'Cancelled' |
| gate | VARCHAR(10) | NULL | Gate number |
| terminal | VARCHAR(5) | NULL | Terminal |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update time |

**Constraints**:
- `CHECK (scheduled_arrival > scheduled_departure)`
- `CHECK (origin_airport_id != destination_airport_id)`
- `UNIQUE(flight_number, scheduled_departure)` - Prevent duplicate flight schedules

**Business Rule**: All flights must have AUH as either origin or destination (enforced at application level or trigger)

---

### Passenger Management

#### 4. **frequent_flyer_tiers**
Etihad Guest loyalty tier definitions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| tier_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| tier_name | VARCHAR(20) | UNIQUE, NOT NULL | Platinum, Gold, Silver, Bronze |
| tier_level | INT | UNIQUE, NOT NULL | Numeric ranking (4=Platinum, 1=Bronze) |
| baggage_allowance_extra_kg | INT | DEFAULT 0 | Extra baggage allowance |
| priority_boarding | BOOLEAN | DEFAULT FALSE | Priority boarding flag |
| lounge_access | BOOLEAN | DEFAULT FALSE | Lounge access flag |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

---

#### 5. **passengers**
Passenger master data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| passenger_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| first_name | VARCHAR(100) | NOT NULL | First name |
| last_name | VARCHAR(100) | NOT NULL | Last name |
| date_of_birth | DATE | NOT NULL, CHECK (< CURRENT_DATE) | Date of birth |
| nationality | VARCHAR(3) | NOT NULL | ISO 3-letter country code |
| passport_number | VARCHAR(20) | UNIQUE, NOT NULL | Passport number |
| passport_expiry | DATE | NOT NULL | Passport expiration date |
| email | VARCHAR(255) | NULL | Email address |
| phone | VARCHAR(20) | NULL | Phone number |
| frequent_flyer_number | VARCHAR(20) | UNIQUE, NULL | Etihad Guest number |
| frequent_flyer_tier_id | INT | FOREIGN KEY → frequent_flyer_tiers, NULL | Current tier |
| is_vip | BOOLEAN | DEFAULT FALSE | VIP passenger flag |
| has_medical_condition | BOOLEAN | DEFAULT FALSE | Medical condition flag |
| medical_notes | TEXT | NULL | Medical condition details |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

---

#### 6. **bookings**
Passenger booking/reservation details.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| booking_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| pnr | VARCHAR(6) | UNIQUE, NOT NULL | 6-character PNR |
| passenger_id | INT | FOREIGN KEY → passengers | Passenger reference |
| flight_id | INT | FOREIGN KEY → flights | Flight reference |
| booking_class | ENUM | NOT NULL | 'Economy', 'Business', 'First' |
| seat_number | VARCHAR(5) | NULL | Assigned seat (e.g., 12A) |
| booking_status | ENUM | NOT NULL, DEFAULT 'Confirmed' | 'Confirmed', 'CheckedIn', 'Boarded', 'NoShow', 'Cancelled' |
| is_connection | BOOLEAN | DEFAULT FALSE | Is connecting flight |
| connection_at_risk | BOOLEAN | DEFAULT FALSE | Connection at risk flag |
| connecting_flight_id | INT | FOREIGN KEY → flights, NULL | Next flight if connection |
| check_in_time | DATETIME | NULL | Check-in timestamp |
| boarding_time | DATETIME | NULL | Boarding timestamp |
| special_service_request | TEXT | NULL | SSR codes (WCHR, VGML, etc.) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update time |

**Constraints**:
- If `is_connection = TRUE`, `connecting_flight_id` must NOT be NULL
- If `connection_at_risk = TRUE`, `is_connection` must be TRUE

---

#### 7. **baggage**
Passenger baggage tracking.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| baggage_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| booking_id | INT | FOREIGN KEY → bookings | Booking reference |
| baggage_tag | VARCHAR(10) | UNIQUE, NOT NULL | Baggage tag number |
| baggage_type | ENUM | NOT NULL | 'CheckedIn', 'CarryOn', 'Sports', 'SpecialHandling' |
| weight_kg | DECIMAL(5,2) | NOT NULL, CHECK (> 0) | Baggage weight |
| is_priority | BOOLEAN | DEFAULT FALSE | Priority handling flag |
| current_location | VARCHAR(3) | NULL | Current airport IATA code |
| final_destination | VARCHAR(3) | NOT NULL | Final destination IATA code |
| baggage_status | ENUM | NOT NULL, DEFAULT 'CheckedIn' | 'CheckedIn', 'Loaded', 'InTransit', 'Arrived', 'Delayed', 'Lost' |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update time |

---

### Cargo Operations

#### 8. **commodity_types**
Master table for cargo commodity categories.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| commodity_type_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| commodity_code | VARCHAR(20) | UNIQUE, NOT NULL | Internal code |
| commodity_name | VARCHAR(100) | NOT NULL | Display name |
| requires_special_handling | BOOLEAN | DEFAULT FALSE | Special handling required |
| temperature_controlled | BOOLEAN | DEFAULT FALSE | Temperature control needed |
| handling_instructions | TEXT | NULL | Special instructions |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

**Sample Commodities**:
- GeneralCargo (GEN)
- LiveAnimals (AVI) - SafeGuard, SkyStables
- Pharma (PHA) - SecureTech
- Perishables (PER) - FreshForward
- Fresh (FRE)
- HumanRemains (HUM)

---

#### 9. **cargo_shipments**
Core cargo shipment/booking table.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| shipment_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| awb_prefix | VARCHAR(3) | NOT NULL, DEFAULT '607' | AWB prefix (607) |
| master_document_number | VARCHAR(8) | NOT NULL | 8-digit AWB number |
| awb_number | VARCHAR(11) | UNIQUE, NOT NULL | Full AWB: prefix + document number |
| shipper_name | VARCHAR(200) | NOT NULL | Shipper name |
| shipper_address | TEXT | NOT NULL | Shipper address |
| consignee_name | VARCHAR(200) | NOT NULL | Consignee name |
| consignee_address | TEXT | NOT NULL | Consignee address |
| origin_airport_id | INT | FOREIGN KEY → airports | Origin airport |
| destination_airport_id | INT | FOREIGN KEY → airports | Final destination |
| commodity_type_id | INT | FOREIGN KEY → commodity_types | Commodity type |
| total_pieces | INT | NOT NULL, CHECK (> 0) | Number of pieces |
| total_weight_kg | DECIMAL(10,2) | NOT NULL, CHECK (> 0) | Total weight |
| total_volume_cbm | DECIMAL(10,3) | NOT NULL, CHECK (> 0) | Total volume |
| declared_value_usd | DECIMAL(12,2) | NULL | Declared value |
| shipment_status | ENUM | NOT NULL, DEFAULT 'Queued' | 'Queued', 'Confirmed', 'Cancelled', 'InTransit', 'Delivered' |
| special_handling_codes | VARCHAR(255) | NULL | SHC codes (EAT, PER, AVI, etc.) |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update time |

**Constraints**:
- `awb_number` should be computed as `awb_prefix + master_document_number`
- `CHECK (awb_prefix = '607')`
- `CHECK (LENGTH(master_document_number) = 8)`
- `CHECK (origin_airport_id != destination_airport_id)`

---

#### 10. **cargo_flight_assignments**
Many-to-many relationship between cargo and flights (for routing).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| assignment_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| shipment_id | INT | FOREIGN KEY → cargo_shipments | Cargo shipment reference |
| flight_id | INT | FOREIGN KEY → flights | Flight reference |
| sequence_number | INT | NOT NULL, DEFAULT 1 | Routing sequence (1=first leg) |
| pieces_on_flight | INT | NOT NULL, CHECK (> 0) | Pieces loaded on this flight |
| weight_on_flight_kg | DECIMAL(10,2) | NOT NULL, CHECK (> 0) | Weight loaded on this flight |
| loading_status | ENUM | NOT NULL, DEFAULT 'Planned' | 'Planned', 'Loaded', 'Offloaded', 'Transferred' |
| loaded_at | DATETIME | NULL | Loading timestamp |
| offloaded_at | DATETIME | NULL | Offloading timestamp |
| uld_number | VARCHAR(20) | NULL | ULD container number |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

**Constraints**:
- `UNIQUE(shipment_id, flight_id, sequence_number)`
- Total `pieces_on_flight` across all assignments for a shipment should not exceed `total_pieces`
- Total `weight_on_flight_kg` should not exceed `total_weight_kg`

---

### Crew Management

#### 11. **crew_positions**
Master table for crew positions/roles.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| position_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| position_code | VARCHAR(10) | UNIQUE, NOT NULL | Position code (CAPT, FO, CSM, FA) |
| position_name | VARCHAR(50) | NOT NULL | Position name |
| is_cockpit_crew | BOOLEAN | DEFAULT FALSE | Is flight deck crew |
| is_cabin_crew | BOOLEAN | DEFAULT FALSE | Is cabin crew |
| requires_type_rating | BOOLEAN | DEFAULT FALSE | Requires aircraft type rating |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

**Sample Positions**:
- CAPT - Captain (cockpit, requires type rating)
- FO - First Officer (cockpit, requires type rating)
- CSM - Cabin Service Manager (cabin)
- FA - Flight Attendant (cabin)
- PURSER - Purser (cabin)

---

#### 12. **crew_members**
Crew member master data.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| crew_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| employee_id | VARCHAR(20) | UNIQUE, NOT NULL | Employee ID |
| first_name | VARCHAR(100) | NOT NULL | First name |
| last_name | VARCHAR(100) | NOT NULL | Last name |
| date_of_birth | DATE | NOT NULL | Date of birth |
| nationality | VARCHAR(3) | NOT NULL | ISO 3-letter country code |
| hire_date | DATE | NOT NULL | Date of hire |
| position_id | INT | FOREIGN KEY → crew_positions | Primary position |
| base_airport_id | INT | FOREIGN KEY → airports | Home base airport |
| is_active | BOOLEAN | DEFAULT TRUE | Active status |
| license_number | VARCHAR(50) | NULL | License/certificate number |
| license_expiry | DATE | NULL | License expiration |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

---

#### 13. **crew_type_ratings**
Aircraft type ratings for cockpit crew.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| rating_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| crew_id | INT | FOREIGN KEY → crew_members | Crew member reference |
| aircraft_type_id | INT | FOREIGN KEY → aircraft_types | Aircraft type |
| rating_date | DATE | NOT NULL | Date rating obtained |
| expiry_date | DATE | NULL | Rating expiration date |
| is_current | BOOLEAN | DEFAULT TRUE | Current/valid rating |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |

**Constraints**:
- `UNIQUE(crew_id, aircraft_type_id)`
- Only applicable for cockpit crew positions

---

#### 14. **crew_roster**
Crew flight duty assignments.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| roster_id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique identifier |
| crew_id | INT | FOREIGN KEY → crew_members | Crew member reference |
| flight_id | INT | FOREIGN KEY → flights | Flight reference |
| position_id | INT | FOREIGN KEY → crew_positions | Position for this flight |
| duty_start | DATETIME | NOT NULL | Duty start time |
| duty_end | DATETIME | NOT NULL | Duty end time |
| is_standby | BOOLEAN | DEFAULT FALSE | Standby duty |
| is_deadhead | BOOLEAN | DEFAULT FALSE | Deadhead positioning |
| roster_status | ENUM | NOT NULL, DEFAULT 'Assigned' | 'Assigned', 'Confirmed', 'Completed', 'Cancelled' |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Record creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | Last update time |

**Constraints**:
- `CHECK (duty_end > duty_start)`
- Cockpit crew must have valid type rating for the aircraft type of the flight
- Crew member cannot be assigned to overlapping duties

---

## Data Generation Strategy

### Flight Generation (35 flights)
```
Period: 2026-01-30 to 2026-02-05 (7 days)
Flights per day: 5
Total flights: 35
Format: EY + random 3-4 digits (e.g., EY123, EY1234)
```

**Aircraft Distribution**:
- 60% Widebody (21 flights): A380, A350, B787-9, B787-10, B777X
- 40% Narrowbody (14 flights): A320, A320-NEO, A321, A321LR

**Route Planning**:
- All flights must involve AUH (origin OR destination)
- Popular routes from AUH: LHR, JFK, SYD, BKK, DEL, DXB, DOH, CAI, CDG, FCO
- Mix of short-haul (2-4 hours) and long-haul (8-16 hours)

### Passenger Generation

**Load Factor**: 80-90% of aircraft capacity
- For A380 (516 pax): 413-465 passengers
- For A320 (154 pax): 123-139 passengers

**Passenger Mix**:
- 70% Regular passengers
- 15% Frequent flyers (distribute across tiers)
- 10% Connecting passengers (some flagged as at-risk)
- 3% VIP passengers
- 2% Medical condition passengers

**Baggage Per Passenger**:
- Economy: 1 checked bag (20-23 kg) + 1 carry-on (7-10 kg)
- Business: 2 checked bags (28-32 kg each) + 1 carry-on (10-12 kg)  
- First: 3 checked bags (32 kg each) + 1 carry-on (12 kg)

### Cargo Generation

**Shipments Per Flight**: 3-8 cargo shipments

**AWB Generation**:
- Prefix: 607 (fixed)
- Master Document Number: 8 random digits (e.g., 60712345678)

**Commodity Distribution**:
- 40% General Cargo
- 15% Pharma (SecureTech)
- 15% Perishables/Fresh (FreshForward)
- 10% Live Animals (SafeGuard, SkyStables)
- 10% E-commerce
- 5% Human Remains
- 5% Other

**Status Distribution**:
- 75% Confirmed
- 15% Queued
- 10% Cancelled

**Routing**:
- 60% Direct (single flight)
- 30% Transit through AUH
- 10% Multi-leg with AUH as intermediary

### Crew Rostering

**Crew Per Flight**:
- **Widebody**: 2 Pilots (CAPT + FO) + 12-16 Cabin Crew (1 CSM + FA)
- **Narrowbody**: 2 Pilots (CAPT + FO) + 4-6 Cabin Crew (1 CSM + FA)

**Assignment Rules**:
1. Cockpit crew must have valid type rating for aircraft
2. Crew base should preferably be AUH
3. Duty times must comply with flight hours regulations
4. No overlapping duty assignments

---

## Validation & Constraints Summary

### Key Business Rules

1. **Flight Constraints**:
   - Every flight must have AUH as origin OR destination
   - Flight number format: EY + 3-4 digits
   - Scheduled arrival > scheduled departure

2. **Passenger Constraints**:
   - Load factor: 80-90% of aircraft capacity
   - PNR must be unique 6-character code
   - If connection flagged, must have connecting_flight_id

3. **Cargo Constraints**:
   - AWB format: 607 + 8 digits
   - Total pieces/weight on flights ≤ shipment total
   - Origin ≠ Destination

4. **Crew Constraints**:
   - Cockpit crew must have type rating for assigned aircraft
   - No overlapping duty periods
   - Minimum crew counts based on aircraft category

### Database Indexes

**Recommended indexes for performance**:
```sql
-- Flights
CREATE INDEX idx_flights_departure ON flights(scheduled_departure);
CREATE INDEX idx_flights_number ON flights(flight_number);
CREATE INDEX idx_flights_status ON flights(flight_status);

-- Bookings
CREATE INDEX idx_bookings_pnr ON bookings(pnr);
CREATE INDEX idx_bookings_passenger ON bookings(passenger_id);
CREATE INDEX idx_bookings_flight ON bookings(flight_id);

-- Cargo
CREATE INDEX idx_cargo_awb ON cargo_shipments(awb_number);
CREATE INDEX idx_cargo_status ON cargo_shipments(shipment_status);

-- Crew
CREATE INDEX idx_roster_crew ON crew_roster(crew_id);
CREATE INDEX idx_roster_flight ON crew_roster(flight_id);
```

---

## Next Steps

1. ✅ Review and approve schema design
2. Create SQL DDL scripts for table creation
3. Create ER diagram visualization
4. Develop synthetic data generation scripts
5. Populate database with test data
6. Validate all constraints and relationships
