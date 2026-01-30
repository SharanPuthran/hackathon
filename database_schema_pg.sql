-- ============================================================
-- Etihad Airways Aviation Database - SQL DDL
-- Database: MySQL 8.0+ / PostgreSQL 13+
-- ============================================================

-- Drop existing tables (reverse order of dependencies)
DROP TABLE IF EXISTS crew_roster;
DROP TABLE IF EXISTS crew_type_ratings;
DROP TABLE IF EXISTS crew_members;
DROP TABLE IF EXISTS crew_positions;
DROP TABLE IF EXISTS cargo_flight_assignments;
DROP TABLE IF EXISTS cargo_shipments;
DROP TABLE IF EXISTS commodity_types;
DROP TABLE IF EXISTS baggage;
DROP TABLE IF EXISTS bookings;
DROP TABLE IF EXISTS passengers;
DROP TABLE IF EXISTS frequent_flyer_tiers;
DROP TABLE IF EXISTS flights;
DROP TABLE IF EXISTS airports;
DROP TABLE IF EXISTS aircraft_types;

-- ============================================================
-- CORE AVIATION ENTITIES
-- ============================================================

-- Aircraft Types Table
CREATE TABLE aircraft_types (
    aircraft_type_id SERIAL PRIMARY KEY,
    aircraft_code VARCHAR(20) UNIQUE NOT NULL,
    category VARCHAR(20) CHECK (VALUE IN('Widebody', 'Narrowbody') NOT NULL,
    passenger_capacity INT NOT NULL CHECK (passenger_capacity > 0),
    cargo_capacity_kg DECIMAL(10,2) NOT NULL CHECK (cargo_capacity_kg > 0),
    crew_required_pilots INT NOT NULL DEFAULT 2,
    crew_required_cabin INT NOT NULL CHECK (crew_required_cabin > 0),
    max_range_km INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Airports Table
CREATE TABLE airports (
    airport_id SERIAL PRIMARY KEY,
    iata_code CHAR(3) UNIQUE NOT NULL,
    icao_code CHAR(4) UNIQUE NOT NULL,
    airport_name VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    timezone VARCHAR(50) NOT NULL,
    latitude DECIMAL(10,6) NOT NULL,
    longitude DECIMAL(10,6) NOT NULL,
    is_hub BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Flights Table
CREATE TABLE flights (
    flight_id SERIAL PRIMARY KEY,
    flight_number VARCHAR(10) NOT NULL,
    aircraft_type_id INT NOT NULL,
    origin_airport_id INT NOT NULL,
    destination_airport_id INT NOT NULL,
    scheduled_departure DATETIME NOT NULL,
    scheduled_arrival DATETIME NOT NULL,
    actual_departure DATETIME NULL,
    actual_arrival DATETIME NULL,
    flight_status VARCHAR(20) CHECK (VALUE IN('Scheduled', 'Boarding', 'Departed', 'Arrived', 'Delayed', 'Cancelled') NOT NULL DEFAULT 'Scheduled',
    gate VARCHAR(10) NULL,
    terminal VARCHAR(5) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (aircraft_type_id) REFERENCES aircraft_types(aircraft_type_id),
    FOREIGN KEY (origin_airport_id) REFERENCES airports(airport_id),
    FOREIGN KEY (destination_airport_id) REFERENCES airports(airport_id),
    
    CONSTRAINT chk_different_airports CHECK (origin_airport_id != destination_airport_id),
    CONSTRAINT chk_arrival_after_departure CHECK (scheduled_arrival > scheduled_departure),
    CONSTRAINT unique_flight_schedule UNIQUE(flight_number, scheduled_departure)
);

-- ============================================================
-- PASSENGER MANAGEMENT
-- ============================================================

-- Frequent Flyer Tiers Table
CREATE TABLE frequent_flyer_tiers (
    tier_id SERIAL PRIMARY KEY,
    tier_name VARCHAR(20) UNIQUE NOT NULL,
    tier_level INT UNIQUE NOT NULL,
    baggage_allowance_extra_kg INT DEFAULT 0,
    priority_boarding BOOLEAN DEFAULT FALSE,
    lounge_access BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Passengers Table
CREATE TABLE passengers (
    passenger_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    nationality VARCHAR(3) NOT NULL,
    passport_number VARCHAR(20) UNIQUE NOT NULL,
    passport_expiry DATE NOT NULL,
    email VARCHAR(255) NULL,
    phone VARCHAR(20) NULL,
    frequent_flyer_number VARCHAR(20) UNIQUE NULL,
    frequent_flyer_tier_id INT NULL,
    is_vip BOOLEAN DEFAULT FALSE,
    has_medical_condition BOOLEAN DEFAULT FALSE,
    medical_notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (frequent_flyer_tier_id) REFERENCES frequent_flyer_tiers(tier_id),
    CONSTRAINT chk_dob_past CHECK (date_of_birth < CURRENT_DATE)
);

-- Bookings Table
CREATE TABLE bookings (
    booking_id SERIAL PRIMARY KEY,
    pnr VARCHAR(6) UNIQUE NOT NULL,
    passenger_id INT NOT NULL,
    flight_id INT NOT NULL,
    booking_class VARCHAR(20) CHECK (VALUE IN('Economy', 'Business', 'First') NOT NULL,
    seat_number VARCHAR(5) NULL,
    booking_status VARCHAR(20) CHECK (VALUE IN('Confirmed', 'CheckedIn', 'Boarded', 'NoShow', 'Cancelled') NOT NULL DEFAULT 'Confirmed',
    is_connection BOOLEAN DEFAULT FALSE,
    connection_at_risk BOOLEAN DEFAULT FALSE,
    connecting_flight_id INT NULL,
    check_in_time DATETIME NULL,
    boarding_time DATETIME NULL,
    special_service_request TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id),
    FOREIGN KEY (connecting_flight_id) REFERENCES flights(flight_id)
);

-- Baggage Table
CREATE TABLE baggage (
    baggage_id SERIAL PRIMARY KEY,
    booking_id INT NOT NULL,
    baggage_tag VARCHAR(10) UNIQUE NOT NULL,
    baggage_type VARCHAR(20) CHECK (VALUE IN('CheckedIn', 'CarryOn', 'Sports', 'SpecialHandling') NOT NULL,
    weight_kg DECIMAL(5,2) NOT NULL CHECK (weight_kg > 0),
    is_priority BOOLEAN DEFAULT FALSE,
    current_location VARCHAR(3) NULL,
    final_destination VARCHAR(3) NOT NULL,
    baggage_status VARCHAR(20) CHECK (VALUE IN('CheckedIn', 'Loaded', 'InTransit', 'Arrived', 'Delayed', 'Lost') NOT NULL DEFAULT 'CheckedIn',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);

-- ============================================================
-- CARGO OPERATIONS
-- ============================================================

-- Commodity Types Table
CREATE TABLE commodity_types (
    commodity_type_id SERIAL PRIMARY KEY,
    commodity_code VARCHAR(20) UNIQUE NOT NULL,
    commodity_name VARCHAR(100) NOT NULL,
    requires_special_handling BOOLEAN DEFAULT FALSE,
    temperature_controlled BOOLEAN DEFAULT FALSE,
    handling_instructions TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cargo Shipments Table
CREATE TABLE cargo_shipments (
    shipment_id SERIAL PRIMARY KEY,
    awb_prefix VARCHAR(3) NOT NULL DEFAULT '607',
    master_document_number VARCHAR(8) NOT NULL,
    awb_number VARCHAR(11) UNIQUE NOT NULL,
    shipper_name VARCHAR(200) NOT NULL,
    shipper_address TEXT NOT NULL,
    consignee_name VARCHAR(200) NOT NULL,
    consignee_address TEXT NOT NULL,
    origin_airport_id INT NOT NULL,
    destination_airport_id INT NOT NULL,
    commodity_type_id INT NOT NULL,
    total_pieces INT NOT NULL CHECK (total_pieces > 0),
    total_weight_kg DECIMAL(10,2) NOT NULL CHECK (total_weight_kg > 0),
    total_volume_cbm DECIMAL(10,3) NOT NULL CHECK (total_volume_cbm > 0),
    declared_value_usd DECIMAL(12,2) NULL,
    shipment_status VARCHAR(20) CHECK (VALUE IN('Queued', 'Confirmed', 'Cancelled', 'InTransit', 'Delivered') NOT NULL DEFAULT 'Queued',
    special_handling_codes VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (origin_airport_id) REFERENCES airports(airport_id),
    FOREIGN KEY (destination_airport_id) REFERENCES airports(airport_id),
    FOREIGN KEY (commodity_type_id) REFERENCES commodity_types(commodity_id),
    
    CONSTRAINT chk_awb_prefix CHECK (awb_prefix = '607'),
    CONSTRAINT chk_master_doc_length CHECK (LENGTH(master_document_number) = 8),
    CONSTRAINT chk_cargo_different_airports CHECK (origin_airport_id != destination_airport_id)
);

-- Cargo Flight Assignments Table
CREATE TABLE cargo_flight_assignments (
    assignment_id SERIAL PRIMARY KEY,
    shipment_id INT NOT NULL,
    flight_id INT NOT NULL,
    sequence_number INT NOT NULL DEFAULT 1,
    pieces_on_flight INT NOT NULL CHECK (pieces_on_flight > 0),
    weight_on_flight_kg DECIMAL(10,2) NOT NULL CHECK (weight_on_flight_kg > 0),
    loading_status VARCHAR(20) CHECK (VALUE IN('Planned', 'Loaded', 'Offloaded', 'Transferred') NOT NULL DEFAULT 'Planned',
    loaded_at DATETIME NULL,
    offloaded_at DATETIME NULL,
    uld_number VARCHAR(20) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (shipment_id) REFERENCES cargo_shipments(shipment_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id),
    
    CONSTRAINT unique_cargo_flight_sequence UNIQUE(shipment_id, flight_id, sequence_number)
);

-- ============================================================
-- CREW MANAGEMENT
-- ============================================================

-- Crew Positions Table
CREATE TABLE crew_positions (
    position_id SERIAL PRIMARY KEY,
    position_code VARCHAR(10) UNIQUE NOT NULL,
    position_name VARCHAR(50) NOT NULL,
    is_cockpit_crew BOOLEAN DEFAULT FALSE,
    is_cabin_crew BOOLEAN DEFAULT FALSE,
    requires_type_rating BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crew Members Table
CREATE TABLE crew_members (
    crew_id SERIAL PRIMARY KEY,
    employee_id VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    nationality VARCHAR(3) NOT NULL,
    hire_date DATE NOT NULL,
    position_id INT NOT NULL,
    base_airport_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    license_number VARCHAR(50) NULL,
    license_expiry DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (position_id) REFERENCES crew_positions(position_id),
    FOREIGN KEY (base_airport_id) REFERENCES airports(airport_id)
);

-- Crew Type Ratings Table
CREATE TABLE crew_type_ratings (
    rating_id SERIAL PRIMARY KEY,
    crew_id INT NOT NULL,
    aircraft_type_id INT NOT NULL,
    rating_date DATE NOT NULL,
    expiry_date DATE NULL,
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (crew_id) REFERENCES crew_members(crew_id),
    FOREIGN KEY (aircraft_type_id) REFERENCES aircraft_types(aircraft_type_id),
    
    CONSTRAINT unique_crew_aircraft_rating UNIQUE(crew_id, aircraft_type_id)
);

-- Crew Roster Table
CREATE TABLE crew_roster (
    roster_id SERIAL PRIMARY KEY,
    crew_id INT NOT NULL,
    flight_id INT NOT NULL,
    position_id INT NOT NULL,
    duty_start DATETIME NOT NULL,
    duty_end DATETIME NOT NULL,
    is_standby BOOLEAN DEFAULT FALSE,
    is_deadhead BOOLEAN DEFAULT FALSE,
    roster_status VARCHAR(20) CHECK (VALUE IN('Assigned', 'Confirmed', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Assigned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (crew_id) REFERENCES crew_members(crew_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id),
    FOREIGN KEY (position_id) REFERENCES crew_positions(position_id),
    
    CONSTRAINT chk_duty_end_after_start CHECK (duty_end > duty_start)
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================

-- Flight Indexes
CREATE INDEX idx_flights_departure ON flights(scheduled_departure);
CREATE INDEX idx_flights_number ON flights(flight_number);
CREATE INDEX idx_flights_status ON flights(flight_status);
CREATE INDEX idx_flights_origin ON flights(origin_airport_id);
CREATE INDEX idx_flights_destination ON flights(destination_airport_id);

-- Booking Indexes
CREATE INDEX idx_bookings_pnr ON bookings(pnr);
CREATE INDEX idx_bookings_passenger ON bookings(passenger_id);
CREATE INDEX idx_bookings_flight ON bookings(flight_id);
CREATE INDEX idx_bookings_status ON bookings(booking_status);

-- Passenger Indexes
CREATE INDEX idx_passengers_ffn ON passengers(frequent_flyer_number);
CREATE INDEX idx_passengers_name ON passengers(last_name, first_name);

-- Cargo Indexes
CREATE INDEX idx_cargo_awb ON cargo_shipments(awb_number);
CREATE INDEX idx_cargo_status ON cargo_shipments(shipment_status);
CREATE INDEX idx_cargo_origin ON cargo_shipments(origin_airport_id);
CREATE INDEX idx_cargo_destination ON cargo_shipments(destination_airport_id);

-- Crew Indexes
CREATE INDEX idx_roster_crew ON crew_roster(crew_id);
CREATE INDEX idx_roster_flight ON crew_roster(flight_id);
CREATE INDEX idx_crew_employee ON crew_members(employee_id);

-- ============================================================
-- INITIAL SEED DATA
-- ============================================================

-- Insert Aircraft Types
INSERT INTO aircraft_types (aircraft_code, category, passenger_capacity, cargo_capacity_kg, crew_required_cabin, max_range_km) VALUES
('A380', 'Widebody', 516, 16000.00, 16, 15200),
('A350', 'Widebody', 283, 12000.00, 12, 15000),
('B787-9', 'Widebody', 289, 11000.00, 12, 14140),
('B787-10', 'Widebody', 318, 11500.00, 14, 11910),
('B777X', 'Widebody', 426, 14000.00, 14, 13500),
('A320', 'Narrowbody', 154, 3500.00, 4, 6100),
('A320-NEO', 'Narrowbody', 162, 3600.00, 4, 6500),
('A321', 'Narrowbody', 185, 4000.00, 5, 5950),
('A321LR', 'Narrowbody', 206, 4200.00, 6, 7400);

-- Insert Airports
INSERT INTO airports (iata_code, icao_code, airport_name, city, country, timezone, latitude, longitude, is_hub) VALUES
('AUH', 'OMAA', 'Abu Dhabi International Airport', 'Abu Dhabi', 'United Arab Emirates', 'Asia/Dubai', 24.432972, 54.651138, TRUE),
('LHR', 'EGLL', 'London Heathrow Airport', 'London', 'United Kingdom', 'Europe/London', 51.469603, -0.453566, FALSE),
('JFK', 'KJFK', 'John F. Kennedy International Airport', 'New York', 'United States', 'America/New_York', 40.641766, -73.780968, FALSE),
('SYD', 'YSSY', 'Sydney Kingsford Smith Airport', 'Sydney', 'Australia', 'Australia/Sydney', -33.946111, 151.177222, FALSE),
('BKK', 'VTBS', 'Suvarnabhumi Airport', 'Bangkok', 'Thailand', 'Asia/Bangkok', 13.681108, 100.747283, FALSE),
('DEL', 'VIDP', 'Indira Gandhi International Airport', 'New Delhi', 'India', 'Asia/Kolkata', 28.556160, 77.100280, FALSE),
('DXB', 'OMDB', 'Dubai International Airport', 'Dubai', 'United Arab Emirates', 'Asia/Dubai', 25.252778, 55.364444, FALSE),
('DOH', 'OTHH', 'Hamad International Airport', 'Doha', 'Qatar', 'Asia/Qatar', 25.273056, 51.608056, FALSE),
('CAI', 'HECA', 'Cairo International Airport', 'Cairo', 'Egypt', 'Africa/Cairo', 30.121944, 31.405556, FALSE),
('CDG', 'LFPG', 'Charles de Gaulle Airport', 'Paris', 'France', 'Europe/Paris', 49.009722, 2.547778, FALSE),
('FCO', 'LIRF', 'Leonardo da Vinci-Fiumicino Airport', 'Rome', 'Italy', 'Europe/Rome', 41.804475, 12.250797, FALSE),
('FRA', 'EDDF', 'Frankfurt Airport', 'Frankfurt', 'Germany', 'Europe/Berlin', 50.033333, 8.570556, FALSE),
('SIN', 'WSSS', 'Singapore Changi Airport', 'Singapore', 'Singapore', 'Asia/Singapore', 1.350189, 103.994433, FALSE);

-- Insert Frequent Flyer Tiers
INSERT INTO frequent_flyer_tiers (tier_name, tier_level, baggage_allowance_extra_kg, priority_boarding, lounge_access) VALUES
('Platinum', 4, 20, TRUE, TRUE),
('Gold', 3, 15, TRUE, TRUE),
('Silver', 2, 10, TRUE, FALSE),
('Bronze', 1, 5, FALSE, FALSE);

-- Insert Crew Positions
INSERT INTO crew_positions (position_code, position_name, is_cockpit_crew, is_cabin_crew, requires_type_rating) VALUES
('CAPT', 'Captain', TRUE, FALSE, TRUE),
('FO', 'First Officer', TRUE, FALSE, TRUE),
('CSM', 'Cabin Service Manager', FALSE, TRUE, FALSE),
('PURSER', 'Purser', FALSE, TRUE, FALSE),
('FA', 'Flight Attendant', FALSE, TRUE, FALSE);

-- Insert Commodity Types
INSERT INTO commodity_types (commodity_code, commodity_name, requires_special_handling, temperature_controlled, handling_instructions) VALUES
('GEN', 'General Cargo', FALSE, FALSE, NULL),
('AVI', 'Live Animals - SafeGuard/SkyStables', TRUE, FALSE, 'Handle with care, ensure proper ventilation'),
('PHA', 'Pharma - SecureTech', TRUE, TRUE, 'Temperature controlled 2-8°C, secure handling'),
('PER', 'Perishables', TRUE, TRUE, 'Temperature controlled, expedited handling'),
('FRE', 'Fresh - FreshForward', TRUE, TRUE, 'Keep refrigerated, time sensitive'),
('HUM', 'Human Remains', TRUE, FALSE, 'Handle with dignity and respect, secure storage'),
('VAL', 'Valuable Cargo', TRUE, FALSE, 'Secure handling, limited access'),
('DGR', 'Dangerous Goods', TRUE, FALSE, 'Follow IATA DGR regulations'),
('ECC', 'E-Commerce', FALSE, FALSE, 'Standard handling');

-- ============================================================
-- END OF DDL
-- ============================================================
