import csv
from datetime import datetime
import pytz
from collections import defaultdict

# Airport mapping (airport_id -> IATA code)
AIRPORT_MAP = {
    '1': 'AUH',   # Abu Dhabi
    '2': 'LHR',   # London Heathrow
    '3': 'JFK',   # New York JFK
    '4': 'SYD',   # Sydney
    '5': 'BKK',   # Bangkok
    '6': 'DEL',   # New Delhi
    '7': 'DXB',   # Dubai
    '8': 'DOH',   # Doha
    '9': 'CAI',   # Cairo
    '10': 'CDG',  # Paris
    '11': 'FCO',  # Rome
    '12': 'FRA',  # Frankfurt
    '13': 'SIN'   # Singapore
}

# Aircraft registration numbers by type
AIRCRAFT_REGISTRATIONS = {
    'A380': ['A6-EYA', 'A6-EYB', 'A6-EYC', 'A6-EYD', 'A6-EYE', 'A6-EYF'],
    'A350': ['A6-EYc', 'A6-EYi', 'A6-EYj', 'A6-EYl', 'A6-EYn', 'A6-EYp'],
    'B787-9': ['A6-EYo', 'A6-EYP', 'A6-EYq', 'A6-EYr', 'A6-EYs', 'A6-EYt'],
    'B787-10': ['A6-EYY', 'A6-EYb', 'A6-EYV', 'A6-EY^', 'A6-EYZ', 'A6-EYa'],
    'B777X': ['A6-EYK', 'A6-EYf', 'A6-EYg', 'A6-EYh', 'A6-EYL', 'A6-EYM'],
    'A320': ['A6-EYR', 'A6-EYJ', 'A6-EYQ', 'A6-EYm', 'A6-EYN', 'A6-EYO'],
    'A320-NEO': ['A6-EYS', 'A6-EYT', 'A6-EYU', 'A6-EYW', 'A6-EYX', 'A6-EY1'],
    'A321': ['A6-EY2', 'A6-EY3', 'A6-EY4', 'A6-EY5', 'A6-EY6', 'A6-EY7'],
    'A321LR': ['A6-EYH', 'A6-EYk', 'A6-EYI', 'A6-EY8', 'A6-EY9', 'A6-EY0']
}

def parse_datetime(dt_str):
    """Parse datetime string to datetime object"""
    return datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')

def convert_to_zulu(dt_str):
    """Convert datetime string to Zulu (UTC) timestamp"""
    try:
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        gst = pytz.timezone('Asia/Dubai')
        dt_gst = gst.localize(dt)
        dt_utc = dt_gst.astimezone(pytz.UTC)
        return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    except:
        return dt_str

def get_local_time(dt_str):
    """Keep local time format"""
    try:
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%dT%H:%M:%S')
    except:
        return dt_str

def enrich_flights_with_rotation(input_file, output_file):
    """Enrich flights with upline and downline rotation information"""
    
    # Read all flights
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        flights = list(reader)
    
    print(f"Loaded {len(flights)} flights")
    
    # Assign aircraft registrations to each flight
    import random
    for flight in flights:
        aircraft_type = flight['aircraft_code']
        if aircraft_type in AIRCRAFT_REGISTRATIONS:
            flight['aircraft_registration'] = random.choice(AIRCRAFT_REGISTRATIONS[aircraft_type])
        else:
            flight['aircraft_registration'] = f"A6-EY{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
    
    # Sort flights by aircraft registration and then by departure time
    flights_sorted = sorted(flights, key=lambda x: (x['aircraft_registration'], parse_datetime(x['scheduled_departure'])))
    
    # Group flights by aircraft registration
    aircraft_rotations = defaultdict(list)
    for flight in flights_sorted:
        aircraft_rotations[flight['aircraft_registration']].append(flight)
    
    # Build rotation chains for each aircraft
    enriched_flights = []
    
    for aircraft_reg, aircraft_flights in aircraft_rotations.items():
        for i, flight in enumerate(aircraft_flights):
            enriched_flight = flight.copy()
            
            # Add aircraft registration
            enriched_flight['aircraft_registration'] = aircraft_reg
            
            # Upline (previous flight)
            if i > 0:
                upline = aircraft_flights[i - 1]
                enriched_flight['upline_airline'] = 'EY'
                enriched_flight['upline_flight_number'] = upline['flight_number']
                enriched_flight['upline_departure_airport'] = AIRPORT_MAP.get(upline['origin_airport_id'], upline['origin_airport_id'])
                enriched_flight['upline_arrival_airport'] = AIRPORT_MAP.get(upline['destination_airport_id'], upline['destination_airport_id'])
                enriched_flight['upline_std_z'] = convert_to_zulu(upline['scheduled_departure'])
                enriched_flight['upline_std_l'] = get_local_time(upline['scheduled_departure'])
                enriched_flight['upline_sta_z'] = convert_to_zulu(upline['scheduled_arrival'])
                enriched_flight['upline_sta_l'] = get_local_time(upline['scheduled_arrival'])
            else:
                # No upline (first flight of the day/rotation)
                enriched_flight['upline_airline'] = ''
                enriched_flight['upline_flight_number'] = ''
                enriched_flight['upline_departure_airport'] = ''
                enriched_flight['upline_arrival_airport'] = ''
                enriched_flight['upline_std_z'] = ''
                enriched_flight['upline_std_l'] = ''
                enriched_flight['upline_sta_z'] = ''
                enriched_flight['upline_sta_l'] = ''
            
            # Downline (next flight)
            if i < len(aircraft_flights) - 1:
                downline = aircraft_flights[i + 1]
                enriched_flight['downline_airline'] = 'EY'
                enriched_flight['downline_flight_number'] = downline['flight_number']
                enriched_flight['downline_departure_airport'] = AIRPORT_MAP.get(downline['origin_airport_id'], downline['origin_airport_id'])
                enriched_flight['downline_arrival_airport'] = AIRPORT_MAP.get(downline['destination_airport_id'], downline['destination_airport_id'])
                enriched_flight['downline_std_z'] = convert_to_zulu(downline['scheduled_departure'])
                enriched_flight['downline_std_l'] = get_local_time(downline['scheduled_departure'])
                enriched_flight['downline_sta_z'] = convert_to_zulu(downline['scheduled_arrival'])
                enriched_flight['downline_sta_l'] = get_local_time(downline['scheduled_arrival'])
            else:
                # No downline (last flight of the day/rotation)
                enriched_flight['downline_airline'] = ''
                enriched_flight['downline_flight_number'] = ''
                enriched_flight['downline_departure_airport'] = ''
                enriched_flight['downline_arrival_airport'] = ''
                enriched_flight['downline_std_z'] = ''
                enriched_flight['downline_std_l'] = ''
                enriched_flight['downline_sta_z'] = ''
                enriched_flight['downline_sta_l'] = ''
            
            enriched_flights.append(enriched_flight)
    
    # Sort back by flight_id to maintain original order
    enriched_flights_sorted = sorted(enriched_flights, key=lambda x: int(x['flight_id']))
    
    # Define output fieldnames
    fieldnames = list(flights[0].keys()) + [
        'aircraft_registration',
        'upline_airline', 'upline_flight_number', 'upline_departure_airport', 'upline_arrival_airport',
        'upline_std_z', 'upline_std_l', 'upline_sta_z', 'upline_sta_l',
        'downline_airline', 'downline_flight_number', 'downline_departure_airport', 'downline_arrival_airport',
        'downline_std_z', 'downline_std_l', 'downline_sta_z', 'downline_sta_l'
    ]
    
    # Write enriched flights
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_flights_sorted)
    
    print(f"✓ Enriched {len(enriched_flights_sorted)} flights with rotation information")
    print(f"✓ Output saved to: {output_file}")
    
    # Statistics
    flights_with_upline = sum(1 for f in enriched_flights_sorted if f['upline_flight_number'])
    flights_with_downline = sum(1 for f in enriched_flights_sorted if f['downline_flight_number'])
    unique_aircraft = len(aircraft_rotations)
    
    print(f"\nStatistics:")
    print(f"  - Total flights: {len(enriched_flights_sorted)}")
    print(f"  - Unique aircraft: {unique_aircraft}")
    print(f"  - Flights with upline: {flights_with_upline}")
    print(f"  - Flights with downline: {flights_with_downline}")
    print(f"  - First flights (no upline): {len(enriched_flights_sorted) - flights_with_upline}")
    print(f"  - Last flights (no downline): {len(enriched_flights_sorted) - flights_with_downline}")

if __name__ == '__main__':
    enrich_flights_with_rotation('output/flights.csv', 'output/flights_enriched.csv')
