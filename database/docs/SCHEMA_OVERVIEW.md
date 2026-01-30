# Database Schema Overview

Complete schema documentation for SkyMarshal aviation database.

---

## 📐 Entity Relationship Diagram

```
┌─────────────────┐
│ aircraft_types  │
│ ─────────────── │
│ PK aircraft_id  │
│    aircraft_code│
│    capacity     │
│    cargo_kg     │
└────────┬────────┘
         │
         │ 1:N
         │
┌────────▼────────┐      ┌─────────────────┐
│    flights      │──────│    airports     │
│ ─────────────── │ N:1  │ ─────────────── │
│ PK flight_id    │      │ PK airport_id   │
│ FK aircraft_id  │      │    iata_code    │
│ FK origin_id    │      │    icao_code    │
│ FK dest_id      │      │    city         │
│    flight_number│      │    country      │
│    sched_dep    │      │    is_hub       │
│    sched_arr    │      └─────────────────┘
│    status       │
└────────┬────────┘
         │
         ├──────────────────────────┐
         │                          │
         │ 1:N                      │ 1:N
         │                          │
┌────────▼────────┐        ┌────────▼────────────┐
│    bookings     │        │  crew_roster        │
│ ─────────────── │        │ ─────────────────── │
│ PK booking_id   │        │ PK roster_id        │
│ FK passenger_id │        │ FK crew_id          │
│ FK flight_id    │        │ FK flight_id        │
│    pnr          │        │ FK position_id      │
│    seat_number  │        │    duty_start       │
│    class        │        │    duty_end         │
│    status       │        └─────────────────────┘
└────────┬────────┘
         │
         │ N:1
         │
┌────────▼────────┐        ┌─────────────────────┐
│   passengers    │        │ frequent_flyer_tiers│
│ ─────────────── │────────│ ─────────────────── │
│ PK passenger_id │ N:1    │ PK tier_id          │
│ FK ff_tier_id   │        │    tier_name        │
│    first_name   │        │    tier_level       │
│    last_name    │        │    baggage_extra    │
│    passport_num │        │    priority_board   │
│    ff_number    │        │    lounge_access    │
│    is_vip       │        └─────────────────────┘
└─────────────────┘

┌─────────────────┐        ┌─────────────────────┐
│ cargo_shipments │        │  commodity_types    │
│ ─────────────── │────────│ ─────────────────── │
│ PK shipment_id  │ N:1    │ PK commodity_id     │
│ FK commodity_id │        │    commodity_code   │
│ FK origin_id    │        │    commodity_name   │
│ FK dest_id      │        │    special_handling │
│    awb_number   │        │    temp_controlled  │
│    total_weight │        └─────────────────────┘
│    total_pieces │
│    status       │
└────────┬────────┘
         │
         │ 1:N
         │
┌────────▼────────────────┐
│ cargo_flight_assignments│
│ ─────────────────────── │
│ PK assignment_id        │
│ FK shipment_id          │
│ FK flight_id            │
│    pieces_on_flight     │
│    weight_on_flight     │
│    loading_status       │
└─────────────────────────┘

┌─────────────────┐        ┌─────────────────────┐
│  crew_members   │        │  crew_positions     │
│ ─────────────── │────────│ ─────────────────── │
│ PK crew_id      │ N:1    │ PK position_id      │
│ FK position_id  │        │    position_code    │
│ FK base_airport │        │    position_name    │
│    employee_id  │        │    is_cockpit_crew  │
│    first_name   │        │    is_cabin_crew    │
│    last_name    │        │    requires_rating  │
│    license_num  │        └─────────────────────┘
│    is_active    │
└─────────────────┘
```

---

## 📋 Table Descriptions

### Core Aviation Tables

#### aircraft_types

**Purpose**: Aircraft fleet configuration  
**Records**: 9 aircraft types  
**Key Columns**:

- `aircraft_code` - IATA code (A380, B787, etc.)
- `category` - Widebody or Narrowbody
- `passenger_capacity` - Maximum seats
- `cargo_capacity_kg` - Maximum cargo weight
- `crew_required_cabin` - Minimum cabin crew

**Business Rules**:

- Each aircraft type has fixed capacity
- Crew requirements vary by aircraft size
- Widebody aircraft for long-haul routes

#### airports

**Purpose**: Airport master data  
**Records**: 13 airports (AUH + 12 destinations)  
**Key Columns**:

- `iata_code` - 3-letter code (AUH, LHR, JFK)
- `icao_code` - 4-letter code (OMAA, EGLL, KJFK)
- `is_hub` - TRUE for AUH only
- `timezone` - For schedule calculations
- `latitude/longitude` - For distance calculations

**Business Rules**:

- AUH is the only hub
- All flights originate from or terminate at AUH
- Timezone critical for duty time calculations

#### flights

**Purpose**: Flight schedule and status  
**Records**: 35 flights (5/day × 7 days)  
**Key Columns**:

- `flight_number` - EY prefix (EY551, EY12, etc.)
- `scheduled_departure/arrival` - Planned times
- `actual_departure/arrival` - Actual times (NULL if not departed)
- `flight_status` - Scheduled, Boarding, Departed, Arrived, Delayed, Cancelled
- `gate/terminal` - Airport infrastructure

**Business Rules**:

- Flight number must be unique per departure time
- Arrival must be after departure
- Origin and destination must be different
- Status transitions: Scheduled → Boarding → Departed → Arrived

**Indexes**:

- `idx_flights_departure` - For time-based queries
- `idx_flights_number` - For flight lookup
- `idx_flights_status` - For operational dashboards

---

### Passenger Management Tables

#### frequent_flyer_tiers

**Purpose**: Etihad Guest loyalty program tiers  
**Records**: 4 tiers  
**Tiers**:

1. **Platinum** - Top tier, 20kg extra baggage, lounge access
2. **Gold** - 15kg extra, lounge access
3. **Silver** - 10kg extra, priority boarding
4. **Bronze** - 5kg extra

**Business Rules**:

- Higher tiers get more benefits
- Tier affects rebooking priority during disruptions
- VIP passengers may not have tier but get special treatment

#### passengers

**Purpose**: Passenger profiles  
**Records**: ~8,800 passengers  
**Key Columns**:

- `passport_number` - Unique identifier
- `frequent_flyer_number` - EG prefix (EG12345678)
- `frequent_flyer_tier_id` - Link to tier (NULL for non-members)
- `is_vip` - Special handling flag
- `has_medical_condition` - Requires assistance
- `medical_notes` - Wheelchair, oxygen, etc.

**Business Rules**:

- Passport must be valid (expiry > travel date)
- VIP passengers get priority in disruptions
- Medical conditions affect rebooking options
- Frequent flyer number optional

**Privacy Considerations**:

- PII data - requires encryption
- GDPR compliance needed
- Passport data retention limits

#### bookings

**Purpose**: Flight reservations  
**Records**: ~8,800 bookings (1 per passenger in demo)  
**Key Columns**:

- `pnr` - 6-character booking reference
- `booking_class` - Economy, Business, First
- `seat_number` - Assigned seat (e.g., 12A)
- `booking_status` - Confirmed, CheckedIn, Boarded, NoShow, Cancelled
- `is_connection` - Multi-leg journey flag
- `connection_at_risk` - Tight connection flag
- `connecting_flight_id` - Next flight in journey

**Business Rules**:

- PNR must be unique
- Seat number unique per flight
- Connection time minimum: 60 minutes (domestic), 90 minutes (international)
- Status transitions: Confirmed → CheckedIn → Boarded

**Disruption Impact**:

- Connections at risk are high priority
- Business/First class passengers prioritized
- VIP and high-tier FF members prioritized

#### baggage

**Purpose**: Baggage tracking  
**Records**: ~15,000 bags  
**Key Columns**:

- `baggage_tag` - EY prefix + 8 digits
- `baggage_type` - CheckedIn, CarryOn, Sports, SpecialHandling
- `weight_kg` - For capacity planning
- `is_priority` - VIP/high-tier bags
- `current_location` - IATA code
- `final_destination` - IATA code
- `baggage_status` - CheckedIn, Loaded, InTransit, Arrived, Delayed, Lost

**Business Rules**:

- Economy: 1 bag × 23kg
- Business: 2 bags × 32kg
- First: 3 bags × 32kg
- Priority bags loaded last (first off)
- Baggage must travel with passenger (security)

---

### Cargo Operations Tables

#### commodity_types

**Purpose**: Cargo classification  
**Records**: 9 commodity types  
**Key Types**:

- **GEN** - General cargo (40% of shipments)
- **PHA** - Pharma/SecureTech (15%, temp-controlled)
- **PER** - Perishables (10%, temp-controlled)
- **FRE** - Fresh/FreshForward (10%, temp-controlled)
- **AVI** - Live Animals/SafeGuard (10%, special handling)
- **ECC** - E-Commerce (10%)
- **HUM** - Human Remains (3%, special handling)
- **VAL** - Valuable Cargo (2%, special handling)
- **DGR** - Dangerous Goods (special handling)

**Business Rules**:

- Temperature-controlled cargo has priority
- Special handling increases cost
- Some commodities cannot be mixed (DGR)

#### cargo_shipments

**Purpose**: Air Waybill (AWB) based shipments  
**Records**: 199 shipments  
**Key Columns**:

- `awb_number` - 607 prefix + 8 digits (607 = Etihad)
- `awb_prefix` - Always "607"
- `master_document_number` - 8-digit unique number
- `total_pieces` - Number of packages
- `total_weight_kg` - Total weight
- `total_volume_cbm` - Cubic meters
- `declared_value_usd` - For insurance
- `shipment_status` - Queued, Confirmed, Cancelled, InTransit, Delivered
- `special_handling_codes` - PHA, AVI, DGR, etc.

**Business Rules**:

- AWB number must be globally unique
- Weight and volume determine aircraft capacity usage
- High-value cargo requires special security
- Temperature-controlled cargo cannot be delayed

#### cargo_flight_assignments

**Purpose**: Map cargo to specific flights  
**Records**: ~150 assignments  
**Key Columns**:

- `sequence_number` - For multi-leg shipments
- `pieces_on_flight` - May split shipment
- `weight_on_flight_kg` - Partial weight
- `loading_status` - Planned, Loaded, Offloaded, Transferred
- `uld_number` - Unit Load Device (container)

**Business Rules**:

- Cargo may be split across multiple flights
- ULD assignment for efficient loading
- Loading sequence affects aircraft balance
- Offload priority: lowest value first

---

### Crew Management Tables

#### crew_positions

**Purpose**: Job roles and requirements  
**Records**: 5 positions  
**Positions**:

1. **CAPT** - Captain (cockpit, requires type rating)
2. **FO** - First Officer (cockpit, requires type rating)
3. **CSM** - Cabin Service Manager (cabin)
4. **PURSER** - Purser (cabin)
5. **FA** - Flight Attendant (cabin)

**Business Rules**:

- Cockpit crew requires type rating for aircraft
- Minimum 2 pilots per flight
- Cabin crew count varies by aircraft size

#### crew_members

**Purpose**: Crew profiles  
**Records**: 500+ crew members  
**Key Columns**:

- `employee_id` - EY prefix + 6 digits
- `position_id` - Link to crew_positions
- `base_airport_id` - Home base (all AUH in demo)
- `is_active` - Employment status
- `license_number` - For pilots (EASA format)
- `license_expiry` - Must be valid

**Business Rules**:

- All crew based at AUH
- Pilots must have valid license
- License expiry checked before assignment
- Inactive crew cannot be assigned

#### crew_type_ratings

**Purpose**: Aircraft qualifications for pilots  
**Records**: Variable (not in demo data)  
**Key Columns**:

- `crew_id` - Pilot
- `aircraft_type_id` - Qualified aircraft
- `rating_date` - When qualified
- `expiry_date` - Requalification needed
- `is_current` - Valid flag

**Business Rules**:

- Pilots can only fly aircraft they're rated for
- Ratings expire and need renewal
- Type rating required for Captain and FO only

#### crew_roster

**Purpose**: Flight assignments  
**Records**: ~350 assignments  
**Key Columns**:

- `duty_start` - Report time (2 hours before departure)
- `duty_end` - Release time (1 hour after arrival)
- `is_standby` - Reserve crew
- `is_deadhead` - Positioning flight
- `roster_status` - Assigned, Confirmed, Completed, Cancelled

**Business Rules**:

- Duty time includes pre/post flight duties
- FTL limits: 12 hours/day, 60 hours/7 days, 190 hours/28 days
- Minimum rest: 12 hours between duties
- Standby crew available for disruptions

---

## 🔗 Relationships

### One-to-Many (1:N)

1. **aircraft_types → flights**
   - One aircraft type used by many flights
   - FK: `flights.aircraft_type_id`

2. **airports → flights (origin)**
   - One airport is origin for many flights
   - FK: `flights.origin_airport_id`

3. **airports → flights (destination)**
   - One airport is destination for many flights
   - FK: `flights.destination_airport_id`

4. **flights → bookings**
   - One flight has many bookings
   - FK: `bookings.flight_id`

5. **passengers → bookings**
   - One passenger can have many bookings
   - FK: `bookings.passenger_id`

6. **bookings → baggage**
   - One booking can have many bags
   - FK: `baggage.booking_id`

7. **flights → cargo_flight_assignments**
   - One flight carries many cargo shipments
   - FK: `cargo_flight_assignments.flight_id`

8. **cargo_shipments → cargo_flight_assignments**
   - One shipment can be on many flights (multi-leg)
   - FK: `cargo_flight_assignments.shipment_id`

9. **crew_members → crew_roster**
   - One crew member has many assignments
   - FK: `crew_roster.crew_id`

10. **flights → crew_roster**
    - One flight has many crew assignments
    - FK: `crew_roster.flight_id`

### Many-to-One (N:1)

1. **passengers → frequent_flyer_tiers**
   - Many passengers in one tier
   - FK: `passengers.frequent_flyer_tier_id`

2. **cargo_shipments → commodity_types**
   - Many shipments of one commodity type
   - FK: `cargo_shipments.commodity_type_id`

3. **crew_members → crew_positions**
   - Many crew members in one position
   - FK: `crew_members.position_id`

4. **crew_members → airports (base)**
   - Many crew members based at one airport
   - FK: `crew_members.base_airport_id`

---

## 🔒 Constraints

### Primary Keys

- All tables have auto-increment integer primary keys
- Named as `{table}_id` (e.g., `flight_id`, `passenger_id`)

### Foreign Keys

- All relationships enforced with FK constraints
- ON DELETE behavior varies by table:
  - CASCADE: Bookings deleted when flight cancelled
  - RESTRICT: Cannot delete airport with active flights
  - SET NULL: Optional relationships

### Unique Constraints

- `flight_number + scheduled_departure` - No duplicate flights
- `pnr` - Unique booking reference
- `passport_number` - One passport per passenger
- `awb_number` - Unique cargo tracking
- `baggage_tag` - Unique bag identifier
- `employee_id` - Unique crew identifier

### Check Constraints

- `passenger_capacity > 0` - Positive capacity
- `cargo_capacity_kg > 0` - Positive cargo weight
- `scheduled_arrival > scheduled_departure` - Logical times
- `origin_airport_id != destination_airport_id` - Different airports
- `duty_end > duty_start` - Logical duty times
- `awb_prefix = '607'` - Etihad AWB prefix
- `date_of_birth < CURRENT_DATE` - Past birth dates

---

## 📊 Indexes

### Performance Indexes

#### flights

- `idx_flights_departure` - Time-based queries
- `idx_flights_number` - Flight lookup
- `idx_flights_status` - Operational dashboards
- `idx_flights_origin` - Route analysis
- `idx_flights_destination` - Route analysis

#### bookings

- `idx_bookings_pnr` - PNR lookup
- `idx_bookings_passenger` - Passenger history
- `idx_bookings_flight` - Flight manifest
- `idx_bookings_status` - Status filtering

#### passengers

- `idx_passengers_ffn` - Loyalty lookup
- `idx_passengers_name` - Name search

#### cargo_shipments

- `idx_cargo_awb` - AWB tracking
- `idx_cargo_status` - Status filtering
- `idx_cargo_origin` - Route analysis
- `idx_cargo_destination` - Route analysis

#### crew_roster

- `idx_roster_crew` - Crew schedule
- `idx_roster_flight` - Flight crew list

#### crew_members

- `idx_crew_employee` - Employee lookup

---

## 📈 Data Volumes

### Current (Demo)

- Flights: 35
- Passengers: 8,800
- Bookings: 8,800
- Baggage: 15,000
- Cargo Shipments: 199
- Cargo Assignments: 150
- Crew Members: 500
- Crew Roster: 350

### Production Estimates (Annual)

- Flights: 50,000+
- Passengers: 15 million+
- Bookings: 15 million+
- Baggage: 25 million+
- Cargo Shipments: 100,000+
- Crew Members: 5,000+
- Crew Roster: 200,000+

### Storage Estimates

- Demo: ~50 MB
- Production: ~500 GB (with indexes)
- Archive (5 years): ~2.5 TB

---

## 🔄 Data Lifecycle

### Real-time Updates

- Flight status changes
- Booking status changes
- Baggage location updates
- Cargo loading status

### Batch Updates

- Crew roster assignments (daily)
- Flight schedules (weekly)
- Passenger manifests (hourly)

### Archival

- Completed flights (after 90 days)
- Cancelled bookings (after 30 days)
- Historical crew rosters (after 1 year)

---

## 🛡️ Data Quality Rules

### Mandatory Fields

- All foreign keys must reference valid records
- Flight times must be logical
- Passenger passport must be valid
- Crew licenses must be current

### Data Validation

- Email format validation
- Phone number format validation
- IATA/ICAO code validation
- AWB number format validation

### Business Logic

- No overbooking (bookings ≤ capacity)
- No overweight cargo (cargo ≤ capacity)
- FTL compliance for crew
- Connection time minimums

---

**Schema Version**: 1.0  
**Last Updated**: 2026-01-30  
**Database**: PostgreSQL 13+ / MySQL 8.0+
