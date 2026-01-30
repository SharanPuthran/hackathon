"""Load CSV data into PostgreSQL database"""

import psycopg2
import csv
import os
from pathlib import Path

# Database connection
conn = psycopg2.connect(
    host="localhost",
    database="etihad_aviation",
    user=os.getenv("USER"),  # Use current user
    password=""  # Local PostgreSQL typically doesn't need password
)
cursor = conn.cursor()

print("="*60)
print("Loading Etihad Aviation Database")
print("="*60)

# Create tables with PostgreSQL syntax
print("\nCreating tables...")

# Drop existing tables
cursor.execute("""
DROP TABLE IF EXISTS crew_roster CASCADE;
DROP TABLE IF EXISTS crew_type_ratings CASCADE;
DROP TABLE IF EXISTS crew_members CASCADE;
DROP TABLE IF EXISTS crew_positions CASCADE;
DROP TABLE IF EXISTS cargo_flight_assignments CASCADE;
DROP TABLE IF EXISTS cargo_shipments CASCADE;
DROP TABLE IF EXISTS commodity_types CASCADE;
DROP TABLE IF EXISTS baggage CASCADE;
DROP TABLE IF EXISTS bookings CASCADE;
DROP TABLE IF EXISTS passengers CASCADE;
DROP TABLE IF EXISTS frequent_flyer_tiers CASCADE;
DROP TABLE IF EXISTS flights CASCADE;
DROP TABLE IF EXISTS airports CASCADE;
DROP TABLE IF EXISTS aircraft_types CASCADE;
""")

# Create aircraft_types table
cursor.execute("""
CREATE TABLE aircraft_types (
    aircraft_type_id SERIAL PRIMARY KEY,
    aircraft_code VARCHAR(20) UNIQUE NOT NULL,
    category VARCHAR(20) NOT NULL,
    passenger_capacity INT NOT NULL,
    cargo_capacity_kg DECIMAL(10,2) NOT NULL,
    crew_required_pilots INT NOT NULL DEFAULT 2,
    crew_required_cabin INT NOT NULL,
    max_range_km INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Create airports table
cursor.execute("""
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
)
""")

# Create frequent_flyer_tiers table
cursor.execute("""
CREATE TABLE frequent_flyer_tiers (
    tier_id SERIAL PRIMARY KEY,
    tier_name VARCHAR(20) UNIQUE NOT NULL,
    tier_level INT UNIQUE NOT NULL,
    baggage_allowance_extra_kg INT DEFAULT 0,
    priority_boarding BOOLEAN DEFAULT FALSE,
    lounge_access BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Create crew_positions table
cursor.execute("""
CREATE TABLE crew_positions (
    position_id SERIAL PRIMARY KEY,
    position_code VARCHAR(10) UNIQUE NOT NULL,
    position_name VARCHAR(100) NOT NULL,
    is_cockpit_crew BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Create commodity_types table
cursor.execute("""
CREATE TABLE commodity_types (
    commodity_type_id SERIAL PRIMARY KEY,
    commodity_code VARCHAR(20) UNIQUE NOT NULL,
    commodity_name VARCHAR(100) NOT NULL,
    requires_special_handling BOOLEAN DEFAULT FALSE,
    temperature_controlled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Insert seed data
print("Inserting seed data...")

# Aircraft types
aircraft_types = [
    ('A380', 'Widebody', 615, 84200, 2, 16, 15200),
    ('B787', 'Widebody', 290, 49600, 2, 10, 14140),
    ('B777', 'Widebody', 346, 63200, 2, 12, 13650),
    ('A350', 'Widebody', 315, 53000, 2, 10, 15380),
    ('A320', 'Narrowbody', 180, 21000, 2, 6, 6150),
    ('B737', 'Narrowbody', 189, 23305, 2, 6, 6570)
]

for aircraft in aircraft_types:
    cursor.execute("""
        INSERT INTO aircraft_types (aircraft_code, category, passenger_capacity,
                                   cargo_capacity_kg, crew_required_pilots,
                                   crew_required_cabin, max_range_km)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, aircraft)

# Airports
airports = [
    ('AUH', 'OMAA', 'Abu Dhabi International Airport', 'Abu Dhabi', 'United Arab Emirates', 'Asia/Dubai', 24.433056, 54.651111, True),
    ('LHR', 'EGLL', 'London Heathrow Airport', 'London', 'United Kingdom', 'Europe/London', 51.4775, -0.461389, False),
    ('JFK', 'KJFK', 'John F Kennedy International Airport', 'New York', 'United States', 'America/New_York', 40.6413, -73.7781, False),
    ('SYD', 'YSSY', 'Sydney Airport', 'Sydney', 'Australia', 'Australia/Sydney', -33.9461, 151.177, False),
    ('SIN', 'WSSS', 'Singapore Changi Airport', 'Singapore', 'Singapore', 'Asia/Singapore', 1.35917, 103.989, False),
]

for airport in airports:
    cursor.execute("""
        INSERT INTO airports (iata_code, icao_code, airport_name, city, country,
                            timezone, latitude, longitude, is_hub)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, airport)

# Frequent flyer tiers
tiers = [
    ('Bronze', 1, 0, False, False),
    ('Silver', 2, 5, True, False),
    ('Gold', 3, 10, True, True),
    ('Platinum', 4, 20, True, True)
]

for tier in tiers:
    cursor.execute("""
        INSERT INTO frequent_flyer_tiers (tier_name, tier_level, baggage_allowance_extra_kg,
                                         priority_boarding, lounge_access)
        VALUES (%s, %s, %s, %s, %s)
    """, tier)

# Crew positions
positions = [
    ('CPT', 'Captain', True),
    ('FO', 'First Officer', True),
    ('CSM', 'Cabin Service Manager', False),
    ('FA', 'Flight Attendant', False)
]

for pos in positions:
    cursor.execute("""
        INSERT INTO crew_positions (position_code, position_name, is_cockpit_crew)
        VALUES (%s, %s, %s)
    """, pos)

# Commodity types
commodities = [
    ('GEN', 'General Cargo', False, False),
    ('PER', 'Perishables', True, True),
    ('PHA', 'Pharmaceuticals', True, True),
    ('AVI', 'Live Animals', True, False),
    ('VAL', 'Valuables', True, False)
]

for commodity in commodities:
    cursor.execute("""
        INSERT INTO commodity_types (commodity_code, commodity_name,
                                     requires_special_handling, temperature_controlled)
        VALUES (%s, %s, %s, %s)
    """, commodity)

conn.commit()
print("✓ Seed data loaded")

# Create remaining tables
print("\nCreating transactional tables...")

cursor.execute("""
CREATE TABLE flights (
    flight_id SERIAL PRIMARY KEY,
    flight_number VARCHAR(10) NOT NULL,
    aircraft_type_id INT NOT NULL,
    origin_airport_id INT NOT NULL,
    destination_airport_id INT NOT NULL,
    scheduled_departure TIMESTAMP NOT NULL,
    scheduled_arrival TIMESTAMP NOT NULL,
    actual_departure TIMESTAMP NULL,
    actual_arrival TIMESTAMP NULL,
    flight_status VARCHAR(20) NOT NULL DEFAULT 'Scheduled',
    gate VARCHAR(10) NULL,
    terminal VARCHAR(5) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (aircraft_type_id) REFERENCES aircraft_types(aircraft_type_id),
    FOREIGN KEY (origin_airport_id) REFERENCES airports(airport_id),
    FOREIGN KEY (destination_airport_id) REFERENCES airports(airport_id)
)
""")

cursor.execute("""
CREATE TABLE passengers (
    passenger_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    passport_number VARCHAR(20) UNIQUE NOT NULL,
    nationality VARCHAR(100) NOT NULL,
    email VARCHAR(200) NULL,
    phone VARCHAR(20) NULL,
    frequent_flyer_number VARCHAR(20) NULL,
    frequent_flyer_tier_id INT NULL,
    is_vip BOOLEAN DEFAULT FALSE,
    special_service_request TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (frequent_flyer_tier_id) REFERENCES frequent_flyer_tiers(tier_id)
)
""")

cursor.execute("""
CREATE TABLE bookings (
    booking_id SERIAL PRIMARY KEY,
    pnr VARCHAR(6) UNIQUE NOT NULL,
    passenger_id INT NOT NULL,
    flight_id INT NOT NULL,
    booking_class VARCHAR(1) NOT NULL,
    seat_number VARCHAR(5) NULL,
    booking_status VARCHAR(20) NOT NULL,
    checked_in BOOLEAN DEFAULT FALSE,
    connection_at_risk BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
)
""")

cursor.execute("""
CREATE TABLE baggage (
    baggage_id SERIAL PRIMARY KEY,
    baggage_tag_number VARCHAR(10) UNIQUE NOT NULL,
    booking_id INT NOT NULL,
    weight_kg DECIMAL(5,2) NOT NULL,
    is_checked BOOLEAN DEFAULT TRUE,
    is_priority BOOLEAN DEFAULT FALSE,
    current_location VARCHAR(100) NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
)
""")

cursor.execute("""
CREATE TABLE cargo_shipments (
    shipment_id SERIAL PRIMARY KEY,
    awb_number VARCHAR(11) UNIQUE NOT NULL,
    commodity_type_id INT NOT NULL,
    shipper_name VARCHAR(200) NOT NULL,
    consignee_name VARCHAR(200) NOT NULL,
    origin_airport_id INT NOT NULL,
    destination_airport_id INT NOT NULL,
    total_pieces INT NOT NULL,
    total_weight_kg DECIMAL(10,2) NOT NULL,
    total_volume_cbm DECIMAL(10,2) NOT NULL,
    declared_value_usd DECIMAL(12,2) NULL,
    shipment_status VARCHAR(20) NOT NULL,
    special_handling_codes VARCHAR(50) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (commodity_type_id) REFERENCES commodity_types(commodity_type_id),
    FOREIGN KEY (origin_airport_id) REFERENCES airports(airport_id),
    FOREIGN KEY (destination_airport_id) REFERENCES airports(airport_id)
)
""")

cursor.execute("""
CREATE TABLE cargo_flight_assignments (
    assignment_id SERIAL PRIMARY KEY,
    shipment_id INT NOT NULL,
    flight_id INT NOT NULL,
    pieces_on_flight INT NOT NULL,
    weight_on_flight_kg DECIMAL(10,2) NOT NULL,
    loaded BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES cargo_shipments(shipment_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
)
""")

cursor.execute("""
CREATE TABLE crew_members (
    crew_id SERIAL PRIMARY KEY,
    employee_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    position_id INT NOT NULL,
    base_airport_id INT NOT NULL,
    hire_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (position_id) REFERENCES crew_positions(position_id),
    FOREIGN KEY (base_airport_id) REFERENCES airports(airport_id)
)
""")

cursor.execute("""
CREATE TABLE crew_roster (
    roster_id SERIAL PRIMARY KEY,
    crew_id INT NOT NULL,
    flight_id INT NOT NULL,
    position_id INT NOT NULL,
    duty_start TIMESTAMP NOT NULL,
    duty_end TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (crew_id) REFERENCES crew_members(crew_id),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id),
    FOREIGN KEY (position_id) REFERENCES crew_positions(position_id)
)
""")

conn.commit()
print("✓ Tables created")

print("\nDatabase schema ready!")
print("\nNext: Load CSV data from output/ directory")
cursor.close()
conn.close()
