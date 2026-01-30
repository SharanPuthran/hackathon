import csv
import random
from datetime import datetime, timedelta
from collections import defaultdict

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

# Corporate booking companies
CORPORATE_COMPANIES = ['AWS', 'Microsoft', 'Google', 'Apple', 'Meta', 'Oracle', 'IBM', 'Accenture']

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

def enrich_passengers(input_file, output_file):
    """Enrich passenger data with new columns"""
    
    with open(input_file, 'r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames + [
            'meal_preference', 'pnr', 'passenger_id', 'traveler_id',
            'corporate_booking', 'preferred_language', 'beverage_preference',
            'is_group_booking', 'profession', 'is_agent_booking'
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
        
        # Enrich each passenger in the group
        for idx, passenger_idx in enumerate(group_indices):
            passenger = passengers[passenger_idx].copy()
            
            # Generate tattoo (PT-1, PT-2, etc.)
            tattoo = f"PT-{idx + 1}"
            
            # Add new fields
            passenger['meal_preference'] = random.choice(MEAL_PREFERENCES)
            passenger['pnr'] = pnr
            passenger['passenger_id'] = generate_passenger_id()
            passenger['traveler_id'] = generate_traveler_id(pnr, creation_date, tattoo)
            passenger['corporate_booking'] = corporate_booking
            passenger['preferred_language'] = random.choice(LANGUAGES)
            passenger['beverage_preference'] = random.choice(BEVERAGE_PREFERENCES)
            passenger['is_group_booking'] = is_group
            passenger['profession'] = random.choice(PROFESSIONS)
            passenger['is_agent_booking'] = agent_booking
            
            enriched_passengers.append(passenger)
    
    # Write enriched data
    with open(output_file, 'w', encoding='utf-8', newline='') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_passengers)
    
    print(f"✓ Enriched {len(enriched_passengers)} passengers")
    print(f"✓ Created {len(groups)} booking groups")
    print(f"✓ Output saved to: {output_file}")
    
    # Statistics
    group_bookings = sum(1 for p in enriched_passengers if p['is_group_booking'] == 'Y')
    corporate_bookings = sum(1 for p in enriched_passengers if p['corporate_booking'] == 'Y')
    agent_bookings = sum(1 for p in enriched_passengers if p['is_agent_booking'] == 'Y')
    
    print(f"\nStatistics:")
    print(f"  - Group bookings: {group_bookings} passengers")
    print(f"  - Corporate bookings: {corporate_bookings} passengers")
    print(f"  - Agent bookings: {agent_bookings} passengers")

if __name__ == '__main__':
    enrich_passengers('output/passengers.csv', 'output/passengers_enriched.csv')
