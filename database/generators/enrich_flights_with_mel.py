import csv
import random
from datetime import datetime, timedelta

# MEL Categories and Items
MEL_ITEMS = {
    'A': {  # Category A - No dispatch allowed
        'items': [],  # We won't use this as aircraft can't fly
        'expiry_days': 0
    },
    'B': {  # Category B - Rectification required within 3 days
        'items': [
            'APU (Auxiliary Power Unit) Inoperative',
            'One Hydraulic System Inoperative',
            'One Air Conditioning Pack Inoperative',
            'Weather Radar Inoperative',
            'TCAS (Traffic Collision Avoidance System) Degraded'
        ],
        'expiry_days': [1, 2, 3]
    },
    'C': {  # Category C - Rectification required within 10 days
        'items': [
            'One Engine Thrust Reverser Inoperative',
            'One Fuel Quantity Indicator Inoperative',
            'One VHF Radio Inoperative',
            'One Landing Light Inoperative',
            'One Window Heat Inoperative',
            'Passenger Entertainment System Partially Inoperative',
            'One Galley Oven Inoperative',
            'One Lavatory Inoperative'
        ],
        'expiry_days': [7, 10]
    },
    'D': {  # Category D - Rectification required within 120 days
        'items': [
            'Cabin Reading Light Inoperative',
            'Passenger Service Unit Light Inoperative',
            'Seat Recline Mechanism Inoperative',
            'Window Shade Inoperative',
            'Coat Hook Inoperative',
            'Magazine Pocket Damaged',
            'Tray Table Latch Weak'
        ],
        'expiry_days': [30, 60, 90, 120]
    }
}

# Operational restrictions based on MEL
MEL_RESTRICTIONS = {
    'APU (Auxiliary Power Unit) Inoperative': 'Ground power unit required at all stations',
    'One Hydraulic System Inoperative': 'Reduced flap settings, increased landing distance',
    'One Air Conditioning Pack Inoperative': 'Altitude restriction to FL250, passenger load may be reduced',
    'Weather Radar Inoperative': 'VMC (Visual Meteorological Conditions) only, no flight into known precipitation',
    'TCAS (Traffic Collision Avoidance System) Degraded': 'ATC must provide enhanced separation',
    'One Engine Thrust Reverser Inoperative': 'Increased landing distance, wet runway restrictions',
    'One Fuel Quantity Indicator Inoperative': 'Manual fuel calculations required',
    'One VHF Radio Inoperative': 'Backup communication procedures',
    'One Landing Light Inoperative': 'Daylight operations preferred',
    'One Window Heat Inoperative': 'Altitude restriction, avoid icing conditions',
    'Passenger Entertainment System Partially Inoperative': 'Passenger notification required',
    'One Galley Oven Inoperative': 'Reduced meal service',
    'One Lavatory Inoperative': 'Passenger load may be reduced',
    'Cabin Reading Light Inoperative': 'None',
    'Passenger Service Unit Light Inoperative': 'None',
    'Seat Recline Mechanism Inoperative': 'Seat blocked from sale',
    'Window Shade Inoperative': 'None',
    'Coat Hook Inoperative': 'None',
    'Magazine Pocket Damaged': 'None',
    'Tray Table Latch Weak': 'Seat blocked from sale'
}

def generate_mel_item():
    """Generate a random MEL item with category and expiry"""
    # 70% chance of no MEL, 30% chance of having MEL
    if random.random() < 0.70:
        return {
            'mel_status': 'CLEAR',
            'mel_category': '',
            'mel_item': '',
            'mel_reference': '',
            'mel_reported_date': '',
            'mel_expiry_date': '',
            'mel_days_remaining': '',
            'mel_restrictions': ''
        }
    
    # Select category (B=50%, C=35%, D=15%)
    category_choice = random.random()
    if category_choice < 0.50:
        category = 'B'
    elif category_choice < 0.85:
        category = 'C'
    else:
        category = 'D'
    
    # Select item from category
    mel_item = random.choice(MEL_ITEMS[category]['items'])
    
    # Generate MEL reference number
    mel_ref = f"MEL-{random.randint(10, 99)}-{random.randint(100, 999)}"
    
    # Generate reported date (within last 30 days)
    reported_days_ago = random.randint(0, 30)
    reported_date = datetime.now() - timedelta(days=reported_days_ago)
    
    # Calculate expiry date
    expiry_days = random.choice(MEL_ITEMS[category]['expiry_days'])
    expiry_date = reported_date + timedelta(days=expiry_days)
    
    # Calculate days remaining
    days_remaining = (expiry_date - datetime.now()).days
    
    # Get restrictions
    restrictions = MEL_RESTRICTIONS.get(mel_item, 'None')
    
    return {
        'mel_status': 'ACTIVE',
        'mel_category': category,
        'mel_item': mel_item,
        'mel_reference': mel_ref,
        'mel_reported_date': reported_date.strftime('%Y-%m-%d'),
        'mel_expiry_date': expiry_date.strftime('%Y-%m-%d'),
        'mel_days_remaining': str(days_remaining) if days_remaining > 0 else '0',
        'mel_restrictions': restrictions
    }

def enrich_flights_with_mel(input_file, output_file):
    """Enrich flights with MEL information"""
    
    # Read flights
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        flights = list(reader)
    
    print(f"Loaded {len(flights)} flights")
    
    # Group flights by aircraft to maintain consistency
    from collections import defaultdict
    aircraft_mel = {}
    
    # Assign MEL to each unique aircraft
    unique_aircraft = set(f['aircraft_registration'] for f in flights)
    for aircraft in unique_aircraft:
        aircraft_mel[aircraft] = generate_mel_item()
    
    # Enrich flights with MEL data
    enriched_flights = []
    for flight in flights:
        enriched = flight.copy()
        mel_data = aircraft_mel[flight['aircraft_registration']]
        enriched.update(mel_data)
        enriched_flights.append(enriched)
    
    # Define fieldnames
    fieldnames = list(flights[0].keys()) + [
        'mel_status', 'mel_category', 'mel_item', 'mel_reference',
        'mel_reported_date', 'mel_expiry_date', 'mel_days_remaining', 'mel_restrictions'
    ]
    
    # Write enriched flights
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_flights)
    
    print(f"✓ Enriched {len(enriched_flights)} flights with MEL information")
    print(f"✓ Output saved to: {output_file}")
    
    # Statistics
    mel_active = sum(1 for f in enriched_flights if f['mel_status'] == 'ACTIVE')
    mel_clear = sum(1 for f in enriched_flights if f['mel_status'] == 'CLEAR')
    
    category_counts = defaultdict(int)
    for flight in enriched_flights:
        if flight['mel_category']:
            category_counts[flight['mel_category']] += 1
    
    # Count unique aircraft with MEL
    aircraft_with_mel = set()
    for flight in enriched_flights:
        if flight['mel_status'] == 'ACTIVE':
            aircraft_with_mel.add(flight['aircraft_registration'])
    
    print(f"\nStatistics:")
    print(f"  - Total flights: {len(enriched_flights)}")
    print(f"  - Flights with MEL: {mel_active} ({mel_active/len(enriched_flights)*100:.1f}%)")
    print(f"  - Flights clear (no MEL): {mel_clear} ({mel_clear/len(enriched_flights)*100:.1f}%)")
    print(f"  - Unique aircraft with MEL: {len(aircraft_with_mel)}")
    print(f"\n  MEL by Category:")
    for cat in ['B', 'C', 'D']:
        if cat in category_counts:
            print(f"    Category {cat}: {category_counts[cat]} flights")
    
    # Show expiry urgency
    urgent = sum(1 for f in enriched_flights if f['mel_days_remaining'] and int(f['mel_days_remaining']) <= 3)
    moderate = sum(1 for f in enriched_flights if f['mel_days_remaining'] and 3 < int(f['mel_days_remaining']) <= 10)
    long_term = sum(1 for f in enriched_flights if f['mel_days_remaining'] and int(f['mel_days_remaining']) > 10)
    
    print(f"\n  MEL Expiry Urgency:")
    print(f"    Urgent (≤3 days): {urgent} flights")
    print(f"    Moderate (4-10 days): {moderate} flights")
    print(f"    Long-term (>10 days): {long_term} flights")

if __name__ == '__main__':
    enrich_flights_with_mel('output/flights_enriched.csv', 'output/flights_enriched_mel.csv')
