import csv
import random
from datetime import datetime, timedelta
import pytz

# Airport mapping
AIRPORTS = {
    'AUH': {'id': 1, 'name': 'Abu Dhabi', 'timezone': 'Asia/Dubai'},
    'LHR': {'id': 2, 'name': 'London', 'timezone': 'Europe/London'},
    'JFK': {'id': 3, 'name': 'New York', 'timezone': 'America/New_York'},
    'SYD': {'id': 4, 'name': 'Sydney', 'timezone': 'Australia/Sydney'},
    'BKK': {'id': 5, 'name': 'Bangkok', 'timezone': 'Asia/Bangkok'},
    'DEL': {'id': 6, 'name': 'Delhi', 'timezone': 'Asia/Kolkata'},
    'DXB': {'id': 7, 'name': 'Dubai', 'timezone': 'Asia/Dubai'},
    'DOH': {'id': 8, 'name': 'Doha', 'timezone': 'Asia/Qatar'},
    'CAI': {'id': 9, 'name': 'Cairo', 'timezone': 'Africa/Cairo'},
    'CDG': {'id': 10, 'name': 'Paris', 'timezone': 'Europe/Paris'},
    'FCO': {'id': 11, 'name': 'Rome', 'timezone': 'Europe/Rome'},
    'FRA': {'id': 12, 'name': 'Frankfurt', 'timezone': 'Europe/Berlin'},
    'SIN': {'id': 13, 'name': 'Singapore', 'timezone': 'Asia/Singapore'}
}

# Aircraft types with their characteristics
AIRCRAFT_TYPES = {
    'A380': {'id': 1, 'capacity': 516, 'cargo': 16000, 'crew': 16, 'range_hours': 14, 'speed': 900},
    'A350': {'id': 2, 'capacity': 283, 'cargo': 12000, 'crew': 12, 'range_hours': 14, 'speed': 900},
    'B787-9': {'id': 3, 'capacity': 289, 'cargo': 11000, 'crew': 12, 'range_hours': 13, 'speed': 900},
    'B787-10': {'id': 4, 'capacity': 318, 'cargo': 11500, 'crew': 14, 'range_hours': 11, 'speed': 900},
    'B777X': {'id': 5, 'capacity': 426, 'cargo': 14000, 'crew': 14, 'range_hours': 13, 'speed': 900},
    'A320': {'id': 6, 'capacity': 154, 'cargo': 3500, 'crew': 4, 'range_hours': 6, 'speed': 800},
    'A320-NEO': {'id': 7, 'capacity': 162, 'cargo': 3600, 'crew': 4, 'range_hours': 6, 'speed': 800},
    'A321': {'id': 8, 'capacity': 185, 'cargo': 4000, 'crew': 5, 'range_hours': 6, 'speed': 800},
    'A321LR': {'id': 9, 'capacity': 206, 'cargo': 4200, 'crew': 6, 'range_hours': 7, 'speed': 800}
}

# Aircraft fleet with registrations
AIRCRAFT_FLEET = {
    'A380': ['A6-EYA', 'A6-EYB', 'A6-EYC', 'A6-EYD'],
    'A350': ['A6-EYE', 'A6-EYF', 'A6-EYG', 'A6-EYH'],
    'B787-9': ['A6-EYI', 'A6-EYJ', 'A6-EYK', 'A6-EYL'],
    'B787-10': ['A6-EYM', 'A6-EYN', 'A6-EYO', 'A6-EYP'],
    'B777X': ['A6-EYQ', 'A6-EYR', 'A6-EYS', 'A6-EYT'],
    'A320': ['A6-EYU', 'A6-EYV', 'A6-EYW', 'A6-EYX'],
    'A320-NEO': ['A6-EYY', 'A6-EYZ'],
    'A321': ['A6-EY1', 'A6-EY2'],
    'A321LR': ['A6-EY3', 'A6-EY4', 'A6-EY5', 'A6-EY6']
}

# Popular routes from AUH
ROUTES = [
    ('AUH', 'LHR', 7.5), ('AUH', 'JFK', 14), ('AUH', 'SYD', 14),
    ('AUH', 'BKK', 6), ('AUH', 'DEL', 3.5), ('AUH', 'DOH', 1),
    ('AUH', 'CAI', 4), ('AUH', 'CDG', 7), ('AUH', 'FCO', 5.5),
    ('AUH', 'FRA', 6.5), ('AUH', 'SIN', 7.5), ('AUH', 'DXB', 0.5)
]

def convert_to_zulu(dt):
    """Convert datetime to Zulu timestamp"""
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def get_local_time(dt):
    """Get local time format"""
    return dt.strftime('%Y-%m-%dT%H:%M:%S')

def calculate_flight_time(origin, dest, base_hours):
    """Calculate flight time with some variation"""
    variation = random.uniform(-0.2, 0.2)
    return base_hours + variation

def generate_aircraft_rotation(aircraft_reg, aircraft_type, start_date, num_days=5):
    """Generate a complete rotation for one aircraft"""
    flights = []
    current_time = start_date
    current_location = 'AUH'  # All aircraft start at hub
    flight_counter = random.randint(1000, 9999)
    
    aircraft_info = AIRCRAFT_TYPES[aircraft_type]
    
    # Generate flights for the rotation period
    while (current_time - start_date).days < num_days:
        # Select destination
        possible_routes = [r for r in ROUTES if r[0] == current_location]
        if not possible_routes:
            # Return to hub
            possible_routes = [(loc, 'AUH', 6) for loc in AIRPORTS.keys() if loc != current_location]
        
        origin, destination, flight_hours = random.choice(possible_routes)
        
        # Calculate times
        flight_time = calculate_flight_time(origin, destination, flight_hours)
        turnaround_time = random.uniform(1.5, 3.5)  # 1.5 to 3.5 hours turnaround
        
        departure_time = current_time
        arrival_time = departure_time + timedelta(hours=flight_time)
        
        # Create flight record
        flight = {
            'flight_number': f'EY{flight_counter}',
            'aircraft_type': aircraft_type,
            'aircraft_registration': aircraft_reg,
            'origin': origin,
            'destination': destination,
            'scheduled_departure': departure_time,
            'scheduled_arrival': arrival_time,
            'flight_hours': flight_time
        }
        
        flights.append(flight)
        
        # Update for next flight
        current_location = destination
        current_time = arrival_time + timedelta(hours=turnaround_time)
        flight_counter += 1
        
        # Limit flights per aircraft
        if len(flights) >= 8:
            break
    
    return flights

def generate_complete_schedule():
    """Generate complete flight schedule with rotations"""
    all_flights = []
    flight_id = 1
    
    # Start date
    start_date = datetime(2026, 1, 30, 0, 0, 0)
    
    # Generate rotations for each aircraft
    for aircraft_type, registrations in AIRCRAFT_FLEET.items():
        for reg in registrations:
            # Stagger start times for different aircraft
            aircraft_start = start_date + timedelta(hours=random.randint(0, 12))
            rotation_flights = generate_aircraft_rotation(reg, aircraft_type, aircraft_start, num_days=5)
            
            for flight in rotation_flights:
                aircraft_info = AIRCRAFT_TYPES[aircraft_type]
                origin_info = AIRPORTS[flight['origin']]
                dest_info = AIRPORTS[flight['destination']]
                
                flight_record = {
                    'flight_id': flight_id,
                    'flight_number': flight['flight_number'],
                    'aircraft_type_id': aircraft_info['id'],
                    'aircraft_code': aircraft_type,
                    'aircraft_capacity': aircraft_info['capacity'],
                    'aircraft_cargo_capacity': aircraft_info['cargo'],
                    'cabin_crew_required': aircraft_info['crew'],
                    'origin_airport_id': origin_info['id'],
                    'destination_airport_id': dest_info['id'],
                    'destination_code': flight['destination'],
                    'scheduled_departure': flight['scheduled_departure'].strftime('%Y-%m-%d %H:%M:%S'),
                    'scheduled_arrival': flight['scheduled_arrival'].strftime('%Y-%m-%d %H:%M:%S'),
                    'actual_departure': '',
                    'actual_arrival': '',
                    'flight_status': 'Scheduled',
                    'gate': f"{random.choice(['A', 'B', 'C', 'D'])}{random.randint(1, 20)}",
                    'terminal': random.randint(1, 3),
                    'aircraft_registration': flight['aircraft_registration']
                }
                
                all_flights.append(flight_record)
                flight_id += 1
    
    # Sort by departure time
    all_flights.sort(key=lambda x: x['scheduled_departure'])
    
    return all_flights

def add_rotation_info(flights):
    """Add upline and downline information to flights"""
    # Group by aircraft
    from collections import defaultdict
    aircraft_flights = defaultdict(list)
    
    for flight in flights:
        aircraft_flights[flight['aircraft_registration']].append(flight)
    
    # Sort each aircraft's flights by time
    for reg in aircraft_flights:
        aircraft_flights[reg].sort(key=lambda x: x['scheduled_departure'])
    
    # Add upline/downline info
    enriched_flights = []
    
    for reg, flight_list in aircraft_flights.items():
        for i, flight in enumerate(flight_list):
            enriched = flight.copy()
            
            # Upline (previous flight)
            if i > 0:
                upline = flight_list[i - 1]
                enriched['upline_airline'] = 'EY'
                enriched['upline_flight_number'] = upline['flight_number']
                enriched['upline_departure_airport'] = upline['destination_code']  # Previous destination
                enriched['upline_arrival_airport'] = list(AIRPORTS.keys())[int(upline['destination_airport_id']) - 1]
                
                dep_dt = datetime.strptime(upline['scheduled_departure'], '%Y-%m-%d %H:%M:%S')
                arr_dt = datetime.strptime(upline['scheduled_arrival'], '%Y-%m-%d %H:%M:%S')
                
                enriched['upline_std_z'] = convert_to_zulu(dep_dt)
                enriched['upline_std_l'] = get_local_time(dep_dt)
                enriched['upline_sta_z'] = convert_to_zulu(arr_dt)
                enriched['upline_sta_l'] = get_local_time(arr_dt)
            else:
                enriched['upline_airline'] = ''
                enriched['upline_flight_number'] = ''
                enriched['upline_departure_airport'] = ''
                enriched['upline_arrival_airport'] = ''
                enriched['upline_std_z'] = ''
                enriched['upline_std_l'] = ''
                enriched['upline_sta_z'] = ''
                enriched['upline_sta_l'] = ''
            
            # Downline (next flight)
            if i < len(flight_list) - 1:
                downline = flight_list[i + 1]
                enriched['downline_airline'] = 'EY'
                enriched['downline_flight_number'] = downline['flight_number']
                enriched['downline_departure_airport'] = downline['destination_code']
                enriched['downline_arrival_airport'] = list(AIRPORTS.keys())[int(downline['destination_airport_id']) - 1]
                
                dep_dt = datetime.strptime(downline['scheduled_departure'], '%Y-%m-%d %H:%M:%S')
                arr_dt = datetime.strptime(downline['scheduled_arrival'], '%Y-%m-%d %H:%M:%S')
                
                enriched['downline_std_z'] = convert_to_zulu(dep_dt)
                enriched['downline_std_l'] = get_local_time(dep_dt)
                enriched['downline_sta_z'] = convert_to_zulu(arr_dt)
                enriched['downline_sta_l'] = get_local_time(arr_dt)
            else:
                enriched['downline_airline'] = ''
                enriched['downline_flight_number'] = ''
                enriched['downline_departure_airport'] = ''
                enriched['downline_arrival_airport'] = ''
                enriched['downline_std_z'] = ''
                enriched['downline_std_l'] = ''
                enriched['downline_sta_z'] = ''
                enriched['downline_sta_l'] = ''
            
            enriched_flights.append(enriched)
    
    # Sort back by flight_id
    enriched_flights.sort(key=lambda x: x['flight_id'])
    
    return enriched_flights

def main():
    print("Generating complete flight schedule with rotations...")
    
    # Generate flights
    flights = generate_complete_schedule()
    print(f"✓ Generated {len(flights)} flights")
    
    # Add rotation information
    enriched_flights = add_rotation_info(flights)
    print(f"✓ Added upline/downline rotation information")
    
    # Define fieldnames
    fieldnames = [
        'flight_id', 'flight_number', 'aircraft_type_id', 'aircraft_code',
        'aircraft_capacity', 'aircraft_cargo_capacity', 'cabin_crew_required',
        'origin_airport_id', 'destination_airport_id', 'destination_code',
        'scheduled_departure', 'scheduled_arrival', 'actual_departure', 'actual_arrival',
        'flight_status', 'gate', 'terminal', 'aircraft_registration',
        'upline_airline', 'upline_flight_number', 'upline_departure_airport', 'upline_arrival_airport',
        'upline_std_z', 'upline_std_l', 'upline_sta_z', 'upline_sta_l',
        'downline_airline', 'downline_flight_number', 'downline_departure_airport', 'downline_arrival_airport',
        'downline_std_z', 'downline_std_l', 'downline_sta_z', 'downline_sta_l'
    ]
    
    # Write to CSV
    with open('output/flights_enriched.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_flights)
    
    print(f"✓ Saved to output/flights_enriched.csv")
    
    # Statistics
    from collections import defaultdict
    aircraft_count = defaultdict(int)
    for flight in enriched_flights:
        aircraft_count[flight['aircraft_registration']] += 1
    
    with_upline = sum(1 for f in enriched_flights if f['upline_flight_number'])
    with_downline = sum(1 for f in enriched_flights if f['downline_flight_number'])
    
    print(f"\nStatistics:")
    print(f"  - Total flights: {len(enriched_flights)}")
    print(f"  - Unique aircraft: {len(aircraft_count)}")
    print(f"  - Flights with upline: {with_upline} ({with_upline/len(enriched_flights)*100:.1f}%)")
    print(f"  - Flights with downline: {with_downline} ({with_downline/len(enriched_flights)*100:.1f}%)")
    print(f"  - Average flights per aircraft: {len(enriched_flights)/len(aircraft_count):.1f}")

if __name__ == '__main__':
    main()
