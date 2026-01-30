import csv
import random
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

# Configuration data
MEAL_PREFERENCES = [
    'Continental', 'Asian Vegetarian', 'Kosher', 'Halal', 'Vegan', 
    'Gluten-Free', 'Low-Sodium', 'Diabetic', 'Seafood', 'Child Meal'
]

LANGUAGES = ['English', 'Arabic', 'French', 'Malayalam', 'Hindi', 'Spanish']

BEVERAGE_PREFERENCES = [
    'Hot Latte', 'Cappuccino', 'Espresso', 'Green Tea', 'Champagne',
    'Orange Juice', 'Sparkling Water', 'Red Wine', 'White Wine', 'Cognac'
]

PROFESSIONS = [
    'Business_Executive', 'Software_Engineer', 'Doctor', 'Consultant',
    'Investment_Banker', 'Entrepreneur', 'Lawyer', 'Architect',
    'Social_Media_Influencer', 'Professor', 'Sales_Director', 'CEO',
    'Marketing_Manager', 'Financial_Analyst', 'Engineer', 'Pilot'
]

# VIP/VVIP professions
VVIP_PROFESSIONS = ['CEO', 'Investment_Banker', 'Entrepreneur']
VIP_PROFESSIONS = ['Business_Executive', 'Doctor', 'Consultant', 'Lawyer', 'Sales_Director']

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

# Aircraft registration numbers by type (from maintenance records)
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

def generate_pnr(is_corporate):
    """Generate a 6-character alphanumeric PNR"""
    letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
    numbers = ''.join(random.choices('0123456789', k=3))
    pnr = letters + numbers
    if is_corporate:
        pnr += '/' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
    return pnr

def generate_traveler_id(pnr, creation_date, tattoo):
    """Generate traveler_id: PNR-YYYY-MM-DD-PT-X"""
    return f"{pnr.split('/')[0]}-{creation_date}-{tattoo}"

def generate_passenger_id():
    """Generate unique passenger_id for each leg"""
    letters = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))
    numbers = ''.join(random.choices('0123456789', k=8))
    suffix = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    return f"{letters}{numbers}{suffix}"

def generate_document_number():
    """Generate unique document/ticket number"""
    prefix = ''.join(random.choices('0123456789', k=3))
    middle = ''.join(random.choices('0123456789', k=10))
    return f"{prefix}-{middle}"

def convert_to_zulu(datetime_str):
    """Convert datetime string to Zulu (UTC) timestamp"""
    try:
        # Parse the datetime (assuming it's in local time)
        dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        # Assume it's in Gulf Standard Time (GST/UAE time = UTC+4)
        gst = pytz.timezone('Asia/Dubai')
        dt_gst = gst.localize(dt)
        # Convert to UTC
        dt_utc = dt_gst.astimezone(pytz.UTC)
        # Format as Zulu time
        return dt_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    except:
        return datetime_str

def calculate_customer_value_score(booking_class, frequent_flyer_tier_id, vip_status, is_corporate, is_influencer):
    """
    Calculate Customer Value Score (CVS) out of 10 based on multiple factors
    
    Categories:
    1. Financial Value (max 25 points)
    2. Loyalty Behavior (max 20 points)
    3. Experience History (max 20 points)
    4. Operational Pattern (max 15 points)
    5. Relationship Depth (max 10 points)
    6. Advocacy Level (max 10 points)
    Total: 100 points -> converted to /10 scale
    """
    score = 0
    
    # 1. Financial Value (25 points max)
    # Based on booking class and corporate status
    if booking_class == 'First':
        score += 22
    elif booking_class == 'Business':
        if is_corporate == 'Y':
            score += 18
        else:
            score += 15
    else:  # Economy
        if is_corporate == 'Y':
            score += 10
        else:
            score += 5
    
    # Add bonus for high-value premium
    if vip_status == 'VVIP':
        score += 3  # Ultra-premium bonus
    
    # 2. Loyalty Behavior (20 points max)
    if frequent_flyer_tier_id:
        tier = int(frequent_flyer_tier_id)
        if tier == 4:  # Platinum
            score += 20
        elif tier == 3:  # Gold
            score += 18
        elif tier == 2:  # Silver
            score += 13
        elif tier == 1:  # Bronze
            score += 8
    else:
        score += 3  # No loyalty
    
    # 3. Experience History (20 points max)
    # VIP/VVIP tend to have better experience
    if vip_status == 'VVIP':
        score += 20  # Promoter with praise
    elif vip_status == 'VIP':
        score += 18  # Consistently delighted
    else:
        # Random distribution for regular passengers
        experience_rand = random.random()
        if experience_rand < 0.15:
            score += 15  # Generally satisfied
        elif experience_rand < 0.40:
            score += 13  # Generally satisfied
        elif experience_rand < 0.70:
            score += 10  # Mixed
        else:
            score += 8   # Mixed/inconsistent
    
    # 4. Operational Pattern (15 points max)
    # VIP/Corporate tend to have smoother travel
    if vip_status in ['VIP', 'VVIP'] or is_corporate == 'Y':
        score += random.choice([12, 15])  # Mostly smooth to very predictable
    else:
        operational_rand = random.random()
        if operational_rand < 0.20:
            score += 15  # Very predictable
        elif operational_rand < 0.50:
            score += 12  # Mostly smooth
        elif operational_rand < 0.80:
            score += 8   # Occasional disruptions
        else:
            score += 5   # Some cost to serve
    
    # 5. Relationship Depth (10 points max)
    if vip_status == 'VVIP':
        score += 10  # Highly personalized
    elif vip_status == 'VIP':
        score += 8   # Multiple preferences known
    elif frequent_flyer_tier_id and int(frequent_flyer_tier_id) >= 3:
        score += 8   # Multiple preferences
    elif frequent_flyer_tier_id:
        score += 5   # Basic preferences
    else:
        score += 2   # Anonymous
    
    # 6. Advocacy Level (10 points max)
    if is_influencer == 'Y':
        score += 10  # Influencer/decision-maker
    elif vip_status == 'VVIP':
        score += 9   # Strong promoter
    elif vip_status == 'VIP':
        score += 7   # Occasional advocate
    elif frequent_flyer_tier_id and int(frequent_flyer_tier_id) >= 3:
        score += 7   # Occasional advocate
    else:
        advocacy_rand = random.random()
        if advocacy_rand < 0.10:
            score += 7   # Occasional advocate
        elif advocacy_rand < 0.40:
            score += 4   # Passive
        else:
            score += 2   # Passive/neutral
    
    # Convert to /10 scale and round to 1 decimal
    cvs = round(score / 10, 1)
    return cvs

def determine_vip_status(profession):
    """Determine VIP status based on profession - very rare (target: 10 VVIP, 40 VIP)"""
    # Only 0.025% chance for VVIP (targeting ~10 out of 11000)
    if profession in VVIP_PROFESSIONS and random.random() < 0.0025:
        return 'VVIP'
    # Only 0.13% chance for VIP (targeting ~40 out of 11000)
    elif profession in VIP_PROFESSIONS and random.random() < 0.013:
        return 'VIP'
    else:
        # Extremely small random chance for other passengers
        rand = random.random()
        if rand < 0.00008:
            return 'VVIP'
        elif rand < 0.0009:
            return 'VIP'
        else:
            return 'Regular'

def load_flights(flights_file):
    """Load all available flights with aircraft assignments"""
    with open(flights_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        flights = []
        for flight in reader:
            # Assign a random aircraft registration for this flight based on aircraft type
            aircraft_type = flight['aircraft_code']
            if aircraft_type in AIRCRAFT_REGISTRATIONS:
                flight['aircraft_registration'] = random.choice(AIRCRAFT_REGISTRATIONS[aircraft_type])
            else:
                flight['aircraft_registration'] = f"A6-EY{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
            flights.append(flight)
    return flights

def enrich_passengers(input_file, flights_file, output_file):
    """Enrich passenger data with new columns including flight assignments"""
    
    # Load flights
    flights = load_flights(flights_file)
    print(f"Loaded {len(flights)} flights")
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        # Remove original passenger_id from fieldnames as we'll regenerate it
        original_fieldnames = [f for f in reader.fieldnames if f != 'passenger_id']
        fieldnames = original_fieldnames + [
            'meal_preference', 'pnr', 'passenger_id', 'traveler_id',
            'corporate_booking', 'preferred_language', 'beverage_preference',
            'is_group_booking', 'profession', 'is_agent_booking',
            'passenger_category', 'is_influencer', 'customer_value_score',
            'flight_number', 'aircraft_type', 'aircraft_registration',
            'departure_airport', 'arrival_airport',
            'departure_date', 'departure_time_zulu', 'document_number'
        ]
        
        passengers = list(reader)
    
    # Group passengers for group bookings
    total_passengers = len(passengers)
    groups = []
    i = 0
    
    while i < total_passengers:
        # Decide group size (70% single, 20% pairs, 10% groups of 3-6)
        rand = random.random()
        if rand < 0.70:
            group_size = 1
        elif rand < 0.90:
            group_size = 2
        else:
            group_size = random.randint(3, 6)
        
        # Don't exceed remaining passengers
        group_size = min(group_size, total_passengers - i)
        groups.append(list(range(i, i + group_size)))
        i += group_size
    
    # Enrich each group
    enriched_passengers = []
    
    for group_indices in groups:
        group_size = len(group_indices)
        is_group = 'Y' if group_size >= 3 else 'N'
        
        # 30% chance of corporate booking for groups, 10% for individuals
        is_corporate = random.random() < (0.30 if group_size > 1 else 0.10)
        corporate_booking = 'Y' if is_corporate else 'N'
        
        # 40% chance of agent booking
        is_agent = random.random() < 0.40
        agent_booking = 'Y' if is_agent else 'N'
        
        # Generate common PNR for the group
        pnr = generate_pnr(is_corporate)
        
        # Generate PNR creation date (random date in last 6 months)
        days_ago = random.randint(1, 180)
        creation_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        
        # Decide if this PNR has multi-leg journey (20% chance)
        is_multi_leg = random.random() < 0.20
        num_legs = random.randint(2, 3) if is_multi_leg else 1
        
        # Assign flights for each leg
        group_flights = []
        for leg in range(num_legs):
            # Select a random flight
            flight = random.choice(flights)
            group_flights.append(flight)
        
        # Enrich each passenger in the group
        for idx, passenger_idx in enumerate(group_indices):
            passenger = passengers[passenger_idx].copy()
            
            # Generate tattoo (PT-1, PT-2, etc.)
            tattoo = f"PT-{idx + 1}"
            
            # Select profession
            profession = random.choice(PROFESSIONS)
            
            # Determine VIP status
            vip_status = determine_vip_status(profession)
            
            # Determine if influencer (independent of profession - 2% chance)
            # Doctors, CEOs, Social Media Influencers have higher chance
            if profession in ['Social_Media_Influencer', 'CEO', 'Doctor']:
                is_influencer = 'Y' if random.random() < 0.15 else 'N'
            elif vip_status in ['VIP', 'VVIP']:
                is_influencer = 'Y' if random.random() < 0.08 else 'N'
            else:
                is_influencer = 'Y' if random.random() < 0.015 else 'N'
            
            # Determine booking class (for CVS calculation)
            # VIP/VVIP more likely to have premium classes
            if vip_status == 'VVIP':
                booking_class = random.choice(['First', 'Business', 'Business'])
            elif vip_status == 'VIP':
                booking_class = random.choice(['Business', 'Business', 'Economy'])
            else:
                booking_class = random.choice(['Economy', 'Economy', 'Economy', 'Business'])
            
            # Calculate Customer Value Score
            cvs = calculate_customer_value_score(
                booking_class,
                passenger.get('frequent_flyer_tier_id', ''),
                vip_status,
                corporate_booking,
                is_influencer
            )
            
            # Add new fields (common for all legs)
            passenger['meal_preference'] = random.choice(MEAL_PREFERENCES)
            passenger['pnr'] = pnr
            passenger['traveler_id'] = generate_traveler_id(pnr, creation_date, tattoo)
            passenger['corporate_booking'] = corporate_booking
            passenger['preferred_language'] = random.choice(LANGUAGES)
            passenger['beverage_preference'] = random.choice(BEVERAGE_PREFERENCES)
            passenger['is_group_booking'] = is_group
            passenger['profession'] = profession
            passenger['is_agent_booking'] = agent_booking
            passenger['passenger_category'] = vip_status
            passenger['is_influencer'] = is_influencer
            passenger['customer_value_score'] = cvs
            
            # Create entry for each leg
            for leg_idx, flight in enumerate(group_flights):
                leg_passenger = passenger.copy()
                
                # Generate unique passenger_id and document_number for each leg
                leg_passenger['passenger_id'] = generate_passenger_id()
                leg_passenger['document_number'] = generate_document_number()
                
                # Add flight details with airport codes and aircraft info
                leg_passenger['flight_number'] = flight['flight_number']
                leg_passenger['aircraft_type'] = flight['aircraft_code']
                leg_passenger['aircraft_registration'] = flight['aircraft_registration']
                leg_passenger['departure_airport'] = AIRPORT_MAP.get(flight['origin_airport_id'], flight['origin_airport_id'])
                leg_passenger['arrival_airport'] = AIRPORT_MAP.get(flight['destination_airport_id'], flight['destination_airport_id'])
                
                # Parse flight datetime and convert to Zulu
                flight_datetime = flight['scheduled_departure']
                flight_date = flight_datetime.split(' ')[0]
                
                # Convert to Zulu timestamp
                departure_time_zulu = convert_to_zulu(flight_datetime)
                
                leg_passenger['departure_date'] = flight_date
                leg_passenger['departure_time_zulu'] = departure_time_zulu
                
                enriched_passengers.append(leg_passenger)
    
    # Write enriched data
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_passengers)
    
    print(f"✓ Enriched {len(enriched_passengers)} passenger records (including multi-leg journeys)")
    print(f"✓ Created {len(groups)} booking groups")
    print(f"✓ Output saved to: {output_file}")
    
    # Statistics
    group_bookings = sum(1 for p in enriched_passengers if p['is_group_booking'] == 'Y')
    corporate_bookings = sum(1 for p in enriched_passengers if p['corporate_booking'] == 'Y')
    agent_bookings = sum(1 for p in enriched_passengers if p['is_agent_booking'] == 'Y')
    vvip_count = sum(1 for p in enriched_passengers if p['passenger_category'] == 'VVIP')
    vip_count = sum(1 for p in enriched_passengers if p['passenger_category'] == 'VIP')
    influencer_count = sum(1 for p in enriched_passengers if p['is_influencer'] == 'Y')
    
    # Count unique travelers
    unique_travelers = len(set(p['traveler_id'] for p in enriched_passengers))
    
    # CVS statistics
    cvs_scores = [float(p['customer_value_score']) for p in enriched_passengers]
    avg_cvs = sum(cvs_scores) / len(cvs_scores)
    max_cvs = max(cvs_scores)
    min_cvs = min(cvs_scores)
    
    print(f"\nStatistics:")
    print(f"  - Unique travelers: {unique_travelers}")
    print(f"  - Total passenger records (with legs): {len(enriched_passengers)}")
    print(f"  - Group bookings: {group_bookings} records")
    print(f"  - Corporate bookings: {corporate_bookings} records")
    print(f"  - Agent bookings: {agent_bookings} records")
    print(f"  - VVIP passengers: {vvip_count} records")
    print(f"  - VIP passengers: {vip_count} records")
    print(f"  - Regular passengers: {len(enriched_passengers) - vvip_count - vip_count} records")
    print(f"  - Influencers: {influencer_count} records ({influencer_count/len(enriched_passengers)*100:.2f}%)")
    print(f"  - Customer Value Score: Avg={avg_cvs:.1f}, Min={min_cvs:.1f}, Max={max_cvs:.1f}")

if __name__ == '__main__':
    enrich_passengers('output/passengers.csv', 'output/flights.csv', 'output/passengers_enriched_final.csv')
