#!/usr/bin/env python3
"""
Etihad Airways Aviation Database - Synthetic Data Generator
Generates realistic test data for hackathon database
"""

import random
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import string

# ============================================================
# CONFIGURATION
# ============================================================

# Date range for flights (7 days starting from tomorrow)
START_DATE = datetime(2026, 1, 30, 0, 0, 0)
FLIGHTS_PER_DAY = 5
TOTAL_DAYS = 7
TOTAL_FLIGHTS = FLIGHTS_PER_DAY * TOTAL_DAYS

# Load factor range
LOAD_FACTOR_MIN = 0.80
LOAD_FACTOR_MAX = 0.90

# Cargo per flight range
CARGO_SHIPMENTS_MIN = 3
CARGO_SHIPMENTS_MAX = 8

# ============================================================
# REFERENCE DATA
# ============================================================

# Aircraft configurations (from seed data)
AIRCRAFT_CONFIG = {
    'Widebody': [
        {'code': 'A380', 'capacity': 516, 'cargo_kg': 16000, 'cabin_crew': 16},
        {'code': 'A350', 'capacity': 283, 'cargo_kg': 12000, 'cabin_crew': 12},
        {'code': 'B787-9', 'capacity': 289, 'cargo_kg': 11000, 'cabin_crew': 12},
        {'code': 'B787-10', 'capacity': 318, 'cargo_kg': 11500, 'cabin_crew': 14},
        {'code': 'B777X', 'capacity': 426, 'cargo_kg': 14000, 'cabin_crew': 14},
    ],
    'Narrowbody': [
        {'code': 'A320', 'capacity': 154, 'cargo_kg': 3500, 'cabin_crew': 4},
        {'code': 'A320-NEO', 'capacity': 162, 'cargo_kg': 3600, 'cabin_crew': 4},
        {'code': 'A321', 'capacity': 185, 'cargo_kg': 4000, 'cabin_crew': 5},
        {'code': 'A321LR', 'capacity': 206, 'cargo_kg': 4200, 'cabin_crew': 6},
    ]
}

# Destination airports (excluding AUH)
AIRPORTS = [
    {'code': 'LHR', 'name': 'London Heathrow', 'flight_time': 460},
    {'code': 'JFK', 'name': 'New York JFK', 'flight_time': 840},
    {'code': 'SYD', 'name': 'Sydney', 'flight_time': 840},
    {'code': 'BKK', 'name': 'Bangkok', 'flight_time': 360},
    {'code': 'DEL', 'name': 'New Delhi', 'flight_time': 210},
    {'code': 'DXB', 'name': 'Dubai', 'flight_time': 50},
    {'code': 'DOH', 'name': 'Doha', 'flight_time': 60},
    {'code': 'CAI', 'name': 'Cairo', 'flight_time': 240},
    {'code': 'CDG', 'name': 'Paris CDG', 'flight_time': 420},
    {'code': 'FCO', 'name': 'Rome', 'flight_time': 330},
    {'code': 'FRA', 'name': 'Frankfurt', 'flight_time': 390},
    {'code': 'SIN', 'name': 'Singapore', 'flight_time': 440},
]

# Etihad Guest tiers
FF_TIERS = ['Platinum', 'Gold', 'Silver', 'Bronze']

# Commodity types
COMMODITY_TYPES = [
    {'code': 'GEN', 'name': 'General Cargo', 'weight': (50, 500)},
    {'code': 'AVI', 'name': 'Live Animals - SafeGuard/SkyStables', 'weight': (100, 1000)},
    {'code': 'PHA', 'name': 'Pharma - SecureTech', 'weight': (20, 200)},
    {'code': 'PER', 'name': 'Perishables', 'weight': (100, 800)},
    {'code': 'FRE', 'name': 'Fresh - FreshForward', 'weight': (150, 700)},
    {'code': 'HUM', 'name': 'Human Remains', 'weight': (80, 150)},
    {'code': 'VAL', 'name': 'Valuable Cargo', 'weight': (10, 100)},
    {'code': 'ECC', 'name': 'E-Commerce', 'weight': (30, 300)},
]

# Commodity distribution weights
COMMODITY_DISTRIBUTION = {
    'GEN': 0.40,
    'PHA': 0.15,
    'PER': 0.10,
    'FRE': 0.10,
    'AVI': 0.10,
    'ECC': 0.10,
    'HUM': 0.03,
    'VAL': 0.02,
}

# Sample names for data generation
FIRST_NAMES = ['Ahmed', 'Fatima', 'Mohammed', 'Sara', 'Ali', 'Layla', 'Omar', 'Aisha',
               'John', 'Emma', 'David', 'Sophia', 'James', 'Olivia', 'Robert', 'Mia',
               'Michael', 'Ava', 'William', 'Isabella', 'Raj', 'Priya', 'Chen', 'Wei']

LAST_NAMES = ['Al-Mansoori', 'Al-Hashimi', 'Al-Jabri', 'Smith', 'Johnson', 'Williams',
              'Brown', 'Jones', 'Garcia', 'Martinez', 'Lee', 'Kim', 'Patel', 'Singh',
              'Kumar', 'Chan', 'Wong', 'Rahman', 'Hassan', 'Ali']

NATIONALITIES = ['ARE', 'USA', 'GBR', 'IND', 'CHN', 'SGP', 'AUS', 'DEU', 'FRA', 'ITA']

# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def generate_pnr() -> str:
    """Generate 6-character PNR"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_passport() -> str:
    """Generate passport number"""
    return ''.join(random.choices(string.ascii_uppercase, k=2)) + ''.join(random.choices(string.digits, k=7))

def generate_awb_number() -> str:
    """Generate AWB number: 607 + 8 digits"""
    master_doc = ''.join(random.choices(string.digits, k=8))
    return f"607{master_doc}"

def generate_baggage_tag() -> str:
    """Generate baggage tag"""
    return 'EY' + ''.join(random.choices(string.digits, k=8))

def generate_employee_id() -> str:
    """Generate employee ID"""
    return 'EY' + ''.join(random.choices(string.digits, k=6))

def generate_flight_number() -> str:
    """Generate EY flight number with 3-4 digits"""
    digits = random.choice([3, 4])
    number = ''.join(random.choices(string.digits, k=digits))
    return f"EY{number}"

def weighted_choice(choices: Dict[str, float]) -> str:
    """Make a weighted random choice"""
    items = list(choices.keys())
    weights = list(choices.values())
    return random.choices(items, weights=weights, k=1)[0]

# ============================================================
# DATA GENERATORS
# ============================================================

class DataGenerator:
    def __init__(self):
        self.flights = []
        self.passengers = []
        self.bookings = []
        self.baggage = []
        self.cargo_shipments = []
        self.cargo_flight_assignments = []
        self.crew_members = []
        self.crew_roster = []
        
        self.used_pnrs = set()
        self.used_passports = set()
        self.used_awbs = set()
        self.used_baggage_tags = set()
        self.used_flight_numbers = set()
        self.used_employee_ids = set()
        self.used_ff_numbers = set()
        
    def generate_unique_pnr(self) -> str:
        while True:
            pnr = generate_pnr()
            if pnr not in self.used_pnrs:
                self.used_pnrs.add(pnr)
                return pnr
    
    def generate_unique_passport(self) -> str:
        while True:
            passport = generate_passport()
            if passport not in self.used_passports:
                self.used_passports.add(passport)
                return passport
    
    def generate_unique_awb(self) -> str:
        while True:
            awb = generate_awb_number()
            if awb not in self.used_awbs:
                self.used_awbs.add(awb)
                return awb
    
    def generate_unique_baggage_tag(self) -> str:
        while True:
            tag = generate_baggage_tag()
            if tag not in self.used_baggage_tags:
                self.used_baggage_tags.add(tag)
                return tag
    
    def generate_unique_flight_number(self) -> str:
        while True:
            fn = generate_flight_number()
            if fn not in self.used_flight_numbers:
                self.used_flight_numbers.add(fn)
                return fn
    
    def generate_unique_employee_id(self) -> str:
        while True:
            emp_id = generate_employee_id()
            if emp_id not in self.used_employee_ids:
                self.used_employee_ids.add(emp_id)
                return emp_id
    
    def generate_unique_ff_number(self) -> str:
        while True:
            ff = 'EG' + ''.join(random.choices(string.digits, k=8))
            if ff not in self.used_ff_numbers:
                self.used_ff_numbers.add(ff)
                return ff
    
    def generate_flights(self):
        """Generate flight schedules"""
        print("Generating flights...")
        
        flight_id = 1
        aircraft_type_id_map = {}
        
        # Build aircraft type ID mapping
        type_id = 1
        for category in ['Widebody', 'Narrowbody']:
            for aircraft in AIRCRAFT_CONFIG[category]:
                aircraft_type_id_map[aircraft['code']] = type_id
                type_id += 1
        
        # Airport ID mapping (AUH is 1, others start from 2)
        airport_id_map = {'AUH': 1}
        airport_id = 2
        for airport in AIRPORTS:
            airport_id_map[airport['code']] = airport_id
            airport_id += 1
        
        for day in range(TOTAL_DAYS):
            current_date = START_DATE + timedelta(days=day)
            
            for flight_num in range(FLIGHTS_PER_DAY):
                # Assign aircraft (60% Widebody, 40% Narrowbody)
                category = 'Widebody' if random.random() < 0.6 else 'Narrowbody'
                aircraft = random.choice(AIRCRAFT_CONFIG[category])
                
                # Select destination airport
                destination = random.choice(AIRPORTS)
                
                # Determine direction (50% outbound from AUH, 50% inbound to AUH)
                is_outbound = random.random() < 0.5
                
                if is_outbound:
                    origin_id = airport_id_map['AUH']
                    dest_id = airport_id_map[destination['code']]
                    dest_code = destination['code']
                else:
                    origin_id = airport_id_map[destination['code']]
                    dest_id = airport_id_map['AUH']
                    dest_code = 'AUH'
                
                # Generate departure time (spread throughout the day)
                hour = random.randint(0, 23)
                minute = random.choice([0, 15, 30, 45])
                departure = current_date.replace(hour=hour, minute=minute)
                
                # Calculate arrival time
                flight_duration = destination['flight_time']
                arrival = departure + timedelta(minutes=flight_duration)
                
                # Generate flight number
                flight_number = self.generate_unique_flight_number()
                
                # Random gate and terminal
                gate = random.choice(['A', 'B', 'C', 'D']) + str(random.randint(1, 20))
                terminal = str(random.randint(1, 3))
                
                flight = {
                    'flight_id': flight_id,
                    'flight_number': flight_number,
                    'aircraft_type_id': aircraft_type_id_map[aircraft['code']],
                    'aircraft_code': aircraft['code'],
                    'aircraft_capacity': aircraft['capacity'],
                    'aircraft_cargo_capacity': aircraft['cargo_kg'],
                    'cabin_crew_required': aircraft['cabin_crew'],
                    'origin_airport_id': origin_id,
                    'destination_airport_id': dest_id,
                    'destination_code': dest_code,
                    'scheduled_departure': departure.strftime('%Y-%m-%d %H:%M:%S'),
                    'scheduled_arrival': arrival.strftime('%Y-%m-%d %H:%M:%S'),
                    'actual_departure': None,
                    'actual_arrival': None,
                    'flight_status': 'Scheduled',
                    'gate': gate,
                    'terminal': terminal,
                }
                
                self.flights.append(flight)
                flight_id += 1
        
        print(f"Generated {len(self.flights)} flights")
    
    def generate_passengers_and_bookings(self):
        """Generate passengers and bookings for each flight"""
        print("Generating passengers and bookings...")
        
        passenger_id = 1
        booking_id = 1
        baggage_id = 1
        
        for flight in self.flights:
            # Calculate number of passengers based on load factor
            capacity = flight['aircraft_capacity']
            load_factor = random.uniform(LOAD_FACTOR_MIN, LOAD_FACTOR_MAX)
            num_passengers = int(capacity * load_factor)
            
            # Passenger mix
            num_regular = int(num_passengers * 0.70)
            num_ff = int(num_passengers * 0.15)
            num_connection = int(num_passengers * 0.10)
            num_vip = int(num_passengers * 0.03)
            num_medical = int(num_passengers * 0.02)
            
            # Adjust for rounding
            total_special = num_ff + num_connection + num_vip + num_medical
            if total_special > num_passengers:
                num_regular = num_passengers - (num_ff + num_connection + num_vip + num_medical)
            else:
                num_regular = num_passengers - total_special
            
            passenger_types = (
                ['regular'] * num_regular +
                ['ff'] * num_ff +
                ['connection'] * num_connection +
                ['vip'] * num_vip +
                ['medical'] * num_medical
            )
            random.shuffle(passenger_types)
            
            for pax_type in passenger_types[:num_passengers]:
                # Generate passenger
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                nationality = random.choice(NATIONALITIES)
                
                # Random DOB (18-80 years old)
                age = random.randint(18, 80)
                dob = datetime.now() - timedelta(days=age*365 + random.randint(0, 365))
                
                passport_number = self.generate_unique_passport()
                passport_expiry = datetime.now() + timedelta(days=random.randint(365, 3650))
                
                # Frequent flyer details
                ff_number = None
                ff_tier_id = None
                if pax_type == 'ff':
                    ff_number = self.generate_unique_ff_number()
                    # Tier distribution: 10% Platinum, 20% Gold, 30% Silver, 40% Bronze
                    tier_choice = random.random()
                    if tier_choice < 0.1:
                        ff_tier_id = 1  # Platinum
                    elif tier_choice < 0.3:
                        ff_tier_id = 2  # Gold
                    elif tier_choice < 0.6:
                        ff_tier_id = 3  # Silver
                    else:
                        ff_tier_id = 4  # Bronze
                
                is_vip = (pax_type == 'vip')
                has_medical = (pax_type == 'medical')
                medical_notes = 'Requires wheelchair assistance' if has_medical else None
                
                passenger = {
                    'passenger_id': passenger_id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': dob.strftime('%Y-%m-%d'),
                    'nationality': nationality,
                    'passport_number': passport_number,
                    'passport_expiry': passport_expiry.strftime('%Y-%m-%d'),
                    'email': f"{first_name.lower()}.{last_name.lower()}@email.com",
                    'phone': '+971' + ''.join(random.choices(string.digits, k=9)),
                    'frequent_flyer_number': ff_number,
                    'frequent_flyer_tier_id': ff_tier_id,
                    'is_vip': 1 if is_vip else 0,
                    'has_medical_condition': 1 if has_medical else 0,
                    'medical_notes': medical_notes,
                }
                
                self.passengers.append(passenger)
                
                # Generate booking
                pnr = self.generate_unique_pnr()
                
                # Class distribution: 80% Economy, 15% Business, 5% First
                class_choice = random.random()
                if class_choice < 0.80:
                    booking_class = 'Economy'
                elif class_choice < 0.95:
                    booking_class = 'Business'
                else:
                    booking_class = 'First'
                
                # Seat assignment
                row = random.randint(1, 60)
                seat_letter = random.choice(['A', 'B', 'C', 'D', 'E', 'F'])
                seat_number = f"{row}{seat_letter}"
                
                is_connection = (pax_type == 'connection')
                connection_at_risk = is_connection and random.random() < 0.3
                
                booking = {
                    'booking_id': booking_id,
                    'pnr': pnr,
                    'passenger_id': passenger_id,
                    'flight_id': flight['flight_id'],
                    'booking_class': booking_class,
                    'seat_number': seat_number,
                    'booking_status': 'Confirmed',
                    'is_connection': 1 if is_connection else 0,
                    'connection_at_risk': 1 if connection_at_risk else 0,
                    'connecting_flight_id': None,  # Simplified - would need another flight
                    'check_in_time': None,
                    'boarding_time': None,
                    'special_service_request': 'WCHR' if has_medical else None,
                }
                
                self.bookings.append(booking)
                
                # Generate baggage
                if booking_class == 'Economy':
                    num_bags = 1
                    bag_weights = [(20, 23)]
                elif booking_class == 'Business':
                    num_bags = 2
                    bag_weights = [(28, 32), (28, 32)]
                else:  # First
                    num_bags = 3
                    bag_weights = [(32, 32), (32, 32), (32, 32)]
                
                for weight_range in bag_weights:
                    weight = random.uniform(weight_range[0], weight_range[1])
                    tag = self.generate_unique_baggage_tag()
                    
                    baggage = {
                        'baggage_id': baggage_id,
                        'booking_id': booking_id,
                        'baggage_tag': tag,
                        'baggage_type': 'CheckedIn',
                        'weight_kg': round(weight, 2),
                        'is_priority': 1 if (is_vip or ff_tier_id in [1, 2]) else 0,
                        'current_location': 'AUH',
                        'final_destination': flight['destination_code'],
                        'baggage_status': 'CheckedIn',
                    }
                    
                    self.baggage.append(baggage)
                    baggage_id += 1
                
                passenger_id += 1
                booking_id += 1
        
        print(f"Generated {len(self.passengers)} passengers")
        print(f"Generated {len(self.bookings)} bookings")
        print(f"Generated {len(self.baggage)} baggage items")
    
    def generate_cargo(self):
        """Generate cargo shipments"""
        print("Generating cargo shipments...")
        
        shipment_id = 1
        assignment_id = 1
        
        # Airport ID mapping
        airport_id_map = {'AUH': 1}
        airport_id = 2
        for airport in AIRPORTS:
            airport_id_map[airport['code']] = airport_id
            airport_id += 1
        
        # Commodity ID mapping
        commodity_id_map = {}
        commodity_id = 1
        for commodity in COMMODITY_TYPES:
            commodity_id_map[commodity['code']] = commodity_id
            commodity_id += 1
        
        for flight in self.flights:
            num_shipments = random.randint(CARGO_SHIPMENTS_MIN, CARGO_SHIPMENTS_MAX)
            
            for _ in range(num_shipments):
                # Select commodity type based on distribution
                commodity_code = weighted_choice(COMMODITY_DISTRIBUTION)
                commodity_info = next(c for c in COMMODITY_TYPES if c['code'] == commodity_code)
                
                # Generate shipment details
                awb = self.generate_unique_awb()
                awb_prefix = awb[:3]
                master_doc = awb[3:]
                
                # Generate shipper/consignee
                shipper_name = f"{random.choice(['Global', 'Express', 'International', 'Swift'])} {random.choice(['Logistics', 'Trading', 'Cargo', 'Freight'])}"
                consignee_name = f"{random.choice(['Alpha', 'Beta', 'Gamma', 'Delta'])} {random.choice(['Corp', 'Industries', 'Solutions', 'Group'])}"
                
                # Routing: 60% direct, 30% via AUH, 10% multi-leg
                routing_type = random.choices(['direct', 'via_auh', 'multi'], weights=[0.6, 0.3, 0.1])[0]
                
                if routing_type == 'direct' or routing_type == 'via_auh':
                    # Use current flight's route
                    origin_id = flight['origin_airport_id']
                    dest_id = flight['destination_airport_id']
                elif routing_type == 'multi':
                    # Random origin/destination with AUH in between
                    other_airport = random.choice(AIRPORTS)
                    if flight['origin_airport_id'] == 1:  # Flight from AUH
                        origin_id = airport_id_map[other_airport['code']]
                        dest_id = flight['destination_airport_id']
                    else:  # Flight to AUH
                        origin_id = flight['origin_airport_id']
                        dest_id = airport_id_map[other_airport['code']]
                
                # Generate cargo specs
                pieces = random.randint(1, 20)
                weight_per_piece = random.uniform(*commodity_info['weight'])
                total_weight = round(pieces * weight_per_piece, 2)
                total_volume = round(total_weight * random.uniform(0.003, 0.006), 3)  # m³
                
                # Shipment status
                status_choice = random.choices(['Confirmed', 'Queued', 'Cancelled'], weights=[0.75, 0.15, 0.10])[0]
                
                shipment = {
                    'shipment_id': shipment_id,
                    'awb_prefix': awb_prefix,
                    'master_document_number': master_doc,
                    'awb_number': awb,
                    'shipper_name': shipper_name,
                    'shipper_address': f"{random.randint(1, 999)} {random.choice(['Main', 'Industrial', 'Trade', 'Export'])} St",
                    'consignee_name': consignee_name,
                    'consignee_address': f"{random.randint(1, 999)} {random.choice(['Business', 'Commerce', 'Import', 'Warehouse'])} Ave",
                    'origin_airport_id': origin_id,
                    'destination_airport_id': dest_id,
                    'commodity_type_id': commodity_id_map[commodity_code],
                    'total_pieces': pieces,
                    'total_weight_kg': total_weight,
                    'total_volume_cbm': total_volume,
                    'declared_value_usd': round(random.uniform(1000, 50000), 2) if random.random() < 0.7 else None,
                    'shipment_status': status_choice,
                    'special_handling_codes': commodity_code if commodity_code != 'GEN' else None,
                }
                
                self.cargo_shipments.append(shipment)
                
                # Create flight assignment
                if status_choice == 'Confirmed':
                    assignment = {
                        'assignment_id': assignment_id,
                        'shipment_id': shipment_id,
                        'flight_id': flight['flight_id'],
                        'sequence_number': 1,
                        'pieces_on_flight': pieces,
                        'weight_on_flight_kg': total_weight,
                        'loading_status': 'Planned',
                        'loaded_at': None,
                        'offloaded_at': None,
                        'uld_number': f"AKE{random.randint(10000, 99999)}EY" if random.random() < 0.5 else None,
                    }
                    
                    self.cargo_flight_assignments.append(assignment)
                    assignment_id += 1
                
                shipment_id += 1
        
        print(f"Generated {len(self.cargo_shipments)} cargo shipments")
        print(f"Generated {len(self.cargo_flight_assignments)} cargo flight assignments")
    
    def generate_crew(self):
        """Generate crew members and roster"""
        print("Generating crew...")
        
        # Generate crew pool
        crew_id = 1
        
        # Position mapping
        positions = {
            'CAPT': 1,
            'FO': 2,
            'CSM': 3,
            'PURSER': 4,
            'FA': 5,
        }
        
        # Create crew pool (enough for all flights)
        # Estimate: 2 pilots + avg 10 cabin crew per flight, with rotation
        num_captains = TOTAL_FLIGHTS * 2
        num_first_officers = TOTAL_FLIGHTS * 2
        num_cabin_crew = TOTAL_FLIGHTS * 15
        
        for position_code in ['CAPT', 'FO']:
            count = num_captains if position_code == 'CAPT' else num_first_officers
            for i in range(count):
                employee_id = self.generate_unique_employee_id()
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                
                age = random.randint(28, 60)
                dob = datetime.now() - timedelta(days=age*365)
                hire_date = datetime.now() - timedelta(days=random.randint(365, 10*365))
                
                crew = {
                    'crew_id': crew_id,
                    'employee_id': employee_id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': dob.strftime('%Y-%m-%d'),
                    'nationality': random.choice(NATIONALITIES),
                    'hire_date': hire_date.strftime('%Y-%m-%d'),
                    'position_id': positions[position_code],
                    'base_airport_id': 1,  # AUH
                    'is_active': 1,
                    'license_number': f"EASA{random.randint(100000, 999999)}",
                    'license_expiry': (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'),
                }
                
                self.crew_members.append(crew)
                crew_id += 1
        
        # Cabin crew
        for position_code in ['CSM', 'FA']:
            count = 50 if position_code == 'CSM' else num_cabin_crew
            for i in range(count):
                employee_id = self.generate_unique_employee_id()
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                
                age = random.randint(22, 55)
                dob = datetime.now() - timedelta(days=age*365)
                hire_date = datetime.now() - timedelta(days=random.randint(180, 8*365))
                
                crew = {
                    'crew_id': crew_id,
                    'employee_id': employee_id,
                    'first_name': first_name,
                    'last_name': last_name,
                    'date_of_birth': dob.strftime('%Y-%m-%d'),
                    'nationality': random.choice(NATIONALITIES),
                    'hire_date': hire_date.strftime('%Y-%m-%d'),
                    'position_id': positions[position_code],
                    'base_airport_id': 1,  # AUH
                    'is_active': 1,
                    'license_number': None,
                    'license_expiry': None,
                }
                
                self.crew_members.append(crew)
                crew_id += 1
        
        print(f"Generated {len(self.crew_members)} crew members")
        
        # Generate roster assignments
        roster_id = 1
        captain_pool = [c for c in self.crew_members if c['position_id'] == 1]
        fo_pool = [c for c in self.crew_members if c['position_id'] == 2]
        csm_pool = [c for c in self.crew_members if c['position_id'] == 3]
        fa_pool = [c for c in self.crew_members if c['position_id'] == 5]
        
        for flight in self.flights:
            # Assign 1 Captain
            captain = random.choice(captain_pool)
            duty_start = datetime.strptime(flight['scheduled_departure'], '%Y-%m-%d %H:%M:%S') - timedelta(hours=2)
            duty_end = datetime.strptime(flight['scheduled_arrival'], '%Y-%m-%d %H:%M:%S') + timedelta(hours=1)
            
            roster = {
                'roster_id': roster_id,
                'crew_id': captain['crew_id'],
                'flight_id': flight['flight_id'],
                'position_id': 1,
                'duty_start': duty_start.strftime('%Y-%m-%d %H:%M:%S'),
                'duty_end': duty_end.strftime('%Y-%m-%d %H:%M:%S'),
                'is_standby': 0,
                'is_deadhead': 0,
                'roster_status': 'Assigned',
            }
            self.crew_roster.append(roster)
            roster_id += 1
            
            # Assign 1 First Officer
            fo = random.choice(fo_pool)
            roster = {
                'roster_id': roster_id,
                'crew_id': fo['crew_id'],
                'flight_id': flight['flight_id'],
                'position_id': 2,
                'duty_start': duty_start.strftime('%Y-%m-%d %H:%M:%S'),
                'duty_end': duty_end.strftime('%Y-%m-%d %H:%M:%S'),
                'is_standby': 0,
                'is_deadhead': 0,
                'roster_status': 'Assigned',
            }
            self.crew_roster.append(roster)
            roster_id += 1
            
            # Assign 1 CSM
            csm = random.choice(csm_pool)
            roster = {
                'roster_id': roster_id,
                'crew_id': csm['crew_id'],
                'flight_id': flight['flight_id'],
                'position_id': 3,
                'duty_start': duty_start.strftime('%Y-%m-%d %H:%M:%S'),
                'duty_end': duty_end.strftime('%Y-%m-%d %H:%M:%S'),
                'is_standby': 0,
                'is_deadhead': 0,
                'roster_status': 'Assigned',
            }
            self.crew_roster.append(roster)
            roster_id += 1
            
            # Assign cabin crew (based on aircraft requirement)
            num_fa = flight['cabin_crew_required'] - 1  # -1 for CSM
            for _ in range(num_fa):
                fa = random.choice(fa_pool)
                roster = {
                    'roster_id': roster_id,
                    'crew_id': fa['crew_id'],
                    'flight_id': flight['flight_id'],
                    'position_id': 5,
                    'duty_start': duty_start.strftime('%Y-%m-%d %H:%M:%S'),
                    'duty_end': duty_end.strftime('%Y-%m-%d %H:%M:%S'),
                    'is_standby': 0,
                    'is_deadhead': 0,
                    'roster_status': 'Assigned',
                }
                self.crew_roster.append(roster)
                roster_id += 1
        
        print(f"Generated {len(self.crew_roster)} crew roster assignments")
    
    def export_to_csv(self, output_dir='output'):
        """Export all data to CSV files"""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Export flights
        with open(f'{output_dir}/flights.csv', 'w', newline='', encoding='utf-8') as f:
            if self.flights:
                writer = csv.DictWriter(f, fieldnames=self.flights[0].keys())
                writer.writeheader()
                writer.writerows(self.flights)
        
        # Export passengers
        with open(f'{output_dir}/passengers.csv', 'w', newline='', encoding='utf-8') as f:
            if self.passengers:
                writer = csv.DictWriter(f, fieldnames=self.passengers[0].keys())
                writer.writeheader()
                writer.writerows(self.passengers)
        
        # Export bookings
        with open(f'{output_dir}/bookings.csv', 'w', newline='', encoding='utf-8') as f:
            if self.bookings:
                writer = csv.DictWriter(f, fieldnames=self.bookings[0].keys())
                writer.writeheader()
                writer.writerows(self.bookings)
        
        # Export baggage
        with open(f'{output_dir}/baggage.csv', 'w', newline='', encoding='utf-8') as f:
            if self.baggage:
                writer = csv.DictWriter(f, fieldnames=self.baggage[0].keys())
                writer.writeheader()
                writer.writerows(self.baggage)
        
        # Export cargo shipments
        with open(f'{output_dir}/cargo_shipments.csv', 'w', newline='', encoding='utf-8') as f:
            if self.cargo_shipments:
                writer = csv.DictWriter(f, fieldnames=self.cargo_shipments[0].keys())
                writer.writeheader()
                writer.writerows(self.cargo_shipments)
        
        # Export cargo flight assignments
        with open(f'{output_dir}/cargo_flight_assignments.csv', 'w', newline='', encoding='utf-8') as f:
            if self.cargo_flight_assignments:
                writer = csv.DictWriter(f, fieldnames=self.cargo_flight_assignments[0].keys())
                writer.writeheader()
                writer.writerows(self.cargo_flight_assignments)
        
        # Export crew members
        with open(f'{output_dir}/crew_members.csv', 'w', newline='', encoding='utf-8') as f:
            if self.crew_members:
                writer = csv.DictWriter(f, fieldnames=self.crew_members[0].keys())
                writer.writeheader()
                writer.writerows(self.crew_members)
        
        # Export crew roster
        with open(f'{output_dir}/crew_roster.csv', 'w', newline='', encoding='utf-8') as f:
            if self.crew_roster:
                writer = csv.DictWriter(f, fieldnames=self.crew_roster[0].keys())
                writer.writeheader()
                writer.writerows(self.crew_roster)
        
        print(f"\nData exported to '{output_dir}/' directory")
        print(f"  - flights.csv ({len(self.flights)} records)")
        print(f"  - passengers.csv ({len(self.passengers)} records)")
        print(f"  - bookings.csv ({len(self.bookings)} records)")
        print(f"  - baggage.csv ({len(self.baggage)} records)")
        print(f"  - cargo_shipments.csv ({len(self.cargo_shipments)} records)")
        print(f"  - cargo_flight_assignments.csv ({len(self.cargo_flight_assignments)} records)")
        print(f"  - crew_members.csv ({len(self.crew_members)} records)")
        print(f"  - crew_roster.csv ({len(self.crew_roster)} records)")

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    print("=" * 60)
    print("Etihad Airways Aviation Database - Data Generator")
    print("=" * 60)
    print(f"Generating data for {TOTAL_FLIGHTS} flights ({FLIGHTS_PER_DAY}/day × {TOTAL_DAYS} days)")
    print(f"Date range: {START_DATE.strftime('%Y-%m-%d')} to {(START_DATE + timedelta(days=TOTAL_DAYS-1)).strftime('%Y-%m-%d')}")
    print("=" * 60)
    print()
    
    generator = DataGenerator()
    
    # Generate data
    generator.generate_flights()
    generator.generate_passengers_and_bookings()
    generator.generate_cargo()
    generator.generate_crew()
    
    # Export to CSV
    generator.export_to_csv()
    
    print("\n" + "=" * 60)
    print("Data generation completed successfully!")
    print("=" * 60)

if __name__ == '__main__':
    main()
