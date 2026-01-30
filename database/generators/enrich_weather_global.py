import csv
import random
from datetime import datetime, timedelta

"""
Enrich weather data with major airports from:
- Australia: SYD, MEL, PER, BNE
- Japan: NRT, HND, KIX
- Indonesia: CGK, DPS
- UK: LHR, LGW
- France: CDG, ORY
- Spain: MAD, BCN
- Italy: FCO, MXP
"""

# Load existing weather data
print("Loading existing weather data...")
with open('output/weather.csv', 'r', encoding='utf-8') as f:
    existing_weather = list(csv.DictReader(f))

print(f"Existing weather records: {len(existing_weather)}")

# Airport configurations with typical weather patterns
AIRPORTS = {
    # Australia (Summer in Feb - hot, occasional storms)
    'SYD': {
        'name': 'Sydney',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Thunderstorm'],
        'condition_weights': [0.4, 0.3, 0.15, 0.1, 0.05],
        'temp_range': (22, 32),
        'visibility_range': (7.0, 10.0),
        'wind_range': (8, 20),
        'pressure_range': (1010, 1020)
    },
    'MEL': {
        'name': 'Melbourne',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Rain'],
        'condition_weights': [0.35, 0.3, 0.2, 0.1, 0.05],
        'temp_range': (18, 28),
        'visibility_range': (6.5, 10.0),
        'wind_range': (10, 25),
        'pressure_range': (1008, 1018)
    },
    'PER': {
        'name': 'Perth',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy'],
        'condition_weights': [0.6, 0.3, 0.1],
        'temp_range': (24, 35),
        'visibility_range': (8.0, 10.0),
        'wind_range': (12, 22),
        'pressure_range': (1012, 1020)
    },
    'BNE': {
        'name': 'Brisbane',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Thunderstorm'],
        'condition_weights': [0.45, 0.3, 0.15, 0.07, 0.03],
        'temp_range': (23, 31),
        'visibility_range': (7.5, 10.0),
        'wind_range': (8, 18),
        'pressure_range': (1010, 1018)
    },
    
    # Japan (Winter in Feb - cold, dry, occasional snow)
    'NRT': {
        'name': 'Tokyo Narita',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Snow', 'Overcast'],
        'condition_weights': [0.4, 0.25, 0.2, 0.1, 0.05],
        'temp_range': (2, 10),
        'visibility_range': (6.0, 10.0),
        'wind_range': (10, 25),
        'pressure_range': (1015, 1025)
    },
    'HND': {
        'name': 'Tokyo Haneda',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Snow', 'Overcast'],
        'condition_weights': [0.4, 0.25, 0.2, 0.1, 0.05],
        'temp_range': (3, 11),
        'visibility_range': (6.0, 10.0),
        'wind_range': (10, 25),
        'pressure_range': (1015, 1025)
    },
    'KIX': {
        'name': 'Osaka Kansai',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Overcast'],
        'condition_weights': [0.35, 0.3, 0.2, 0.1, 0.05],
        'temp_range': (4, 12),
        'visibility_range': (6.5, 10.0),
        'wind_range': (8, 20),
        'pressure_range': (1015, 1023)
    },
    
    # Indonesia (Rainy season in Feb - hot, humid, frequent rain)
    'CGK': {
        'name': 'Jakarta',
        'conditions': ['Partly Cloudy', 'Cloudy', 'Light Rain', 'Rain', 'Thunderstorm'],
        'condition_weights': [0.25, 0.3, 0.25, 0.15, 0.05],
        'temp_range': (24, 32),
        'visibility_range': (5.0, 9.0),
        'wind_range': (5, 15),
        'pressure_range': (1008, 1015)
    },
    'DPS': {
        'name': 'Bali Denpasar',
        'conditions': ['Partly Cloudy', 'Cloudy', 'Light Rain', 'Rain', 'Thunderstorm'],
        'condition_weights': [0.3, 0.3, 0.2, 0.15, 0.05],
        'temp_range': (25, 31),
        'visibility_range': (6.0, 9.5),
        'wind_range': (8, 18),
        'pressure_range': (1008, 1014)
    },
    
    # UK (Winter in Feb - cold, wet, cloudy)
    'LHR': {
        'name': 'London Heathrow',
        'conditions': ['Cloudy', 'Overcast', 'Light Rain', 'Rain', 'Fog', 'Partly Cloudy'],
        'condition_weights': [0.3, 0.25, 0.2, 0.1, 0.1, 0.05],
        'temp_range': (3, 10),
        'visibility_range': (4.0, 9.0),
        'wind_range': (12, 28),
        'pressure_range': (1005, 1020)
    },
    'LGW': {
        'name': 'London Gatwick',
        'conditions': ['Cloudy', 'Overcast', 'Light Rain', 'Rain', 'Fog', 'Partly Cloudy'],
        'condition_weights': [0.3, 0.25, 0.2, 0.1, 0.1, 0.05],
        'temp_range': (3, 10),
        'visibility_range': (4.0, 9.0),
        'wind_range': (12, 28),
        'pressure_range': (1005, 1020)
    },
    
    # France (Winter in Feb - cold, variable)
    'CDG': {
        'name': 'Paris Charles de Gaulle',
        'conditions': ['Cloudy', 'Overcast', 'Light Rain', 'Partly Cloudy', 'Clear', 'Fog'],
        'condition_weights': [0.3, 0.25, 0.2, 0.15, 0.05, 0.05],
        'temp_range': (2, 9),
        'visibility_range': (4.5, 9.5),
        'wind_range': (10, 25),
        'pressure_range': (1008, 1022)
    },
    'ORY': {
        'name': 'Paris Orly',
        'conditions': ['Cloudy', 'Overcast', 'Light Rain', 'Partly Cloudy', 'Clear', 'Fog'],
        'condition_weights': [0.3, 0.25, 0.2, 0.15, 0.05, 0.05],
        'temp_range': (2, 9),
        'visibility_range': (4.5, 9.5),
        'wind_range': (10, 25),
        'pressure_range': (1008, 1022)
    },
    
    # Spain (Mild winter in Feb)
    'MAD': {
        'name': 'Madrid',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Overcast'],
        'condition_weights': [0.35, 0.3, 0.2, 0.1, 0.05],
        'temp_range': (5, 14),
        'visibility_range': (7.0, 10.0),
        'wind_range': (8, 20),
        'pressure_range': (1012, 1024)
    },
    'BCN': {
        'name': 'Barcelona',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Rain'],
        'condition_weights': [0.4, 0.35, 0.2, 0.05],
        'temp_range': (8, 15),
        'visibility_range': (7.5, 10.0),
        'wind_range': (10, 22),
        'pressure_range': (1012, 1022)
    },
    
    # Italy (Cool winter in Feb)
    'FCO': {
        'name': 'Rome Fiumicino',
        'conditions': ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Overcast'],
        'condition_weights': [0.3, 0.3, 0.25, 0.1, 0.05],
        'temp_range': (6, 14),
        'visibility_range': (6.5, 10.0),
        'wind_range': (8, 20),
        'pressure_range': (1010, 1020)
    },
    'MXP': {
        'name': 'Milan Malpensa',
        'conditions': ['Cloudy', 'Overcast', 'Fog', 'Light Rain', 'Partly Cloudy', 'Clear'],
        'condition_weights': [0.3, 0.25, 0.15, 0.15, 0.1, 0.05],
        'temp_range': (2, 10),
        'visibility_range': (4.0, 9.0),
        'wind_range': (5, 18),
        'pressure_range': (1008, 1020)
    }
}

# Generate weather data for 3 days
new_weather = []

for airport_code, config in AIRPORTS.items():
    print(f"Generating weather for {airport_code} ({config['name']})...")
    
    for day in range(3):  # 3 days (Feb 1-3, 2026)
        for hour in range(0, 24, 3):  # Every 3 hours
            forecast_time = datetime(2026, 2, 1 + day, hour, 0, 0)
            
            # Select condition based on weights
            condition = random.choices(
                config['conditions'],
                weights=config['condition_weights']
            )[0]
            
            # Determine precipitation based on condition
            if 'Thunderstorm' in condition:
                precip = random.randint(15, 40)
            elif 'Rain' in condition and 'Light' not in condition:
                precip = random.randint(5, 15)
            elif 'Light Rain' in condition or 'Light Snow' in condition:
                precip = random.randint(1, 5)
            else:
                precip = 0
            
            # Determine visibility based on condition
            if 'Fog' in condition:
                visibility = round(random.uniform(1.0, 4.0), 1)
            elif 'Rain' in condition or 'Snow' in condition:
                visibility = round(random.uniform(4.0, 7.0), 1)
            else:
                visibility = round(random.uniform(
                    config['visibility_range'][0],
                    config['visibility_range'][1]
                ), 1)
            
            # Determine operational impact
            if visibility < 2.0 or precip > 30:
                impact = 'SEVERE - Airport may close, all operations suspended'
                runway = 'WET'
            elif visibility < 5.0 or precip > 15:
                impact = 'MODERATE - Delays expected, monitor closely'
                runway = 'WET' if precip > 0 else 'DAMP'
            elif precip > 5:
                impact = 'MINOR - Some delays possible'
                runway = 'WET'
            else:
                impact = 'NONE - Normal operations'
                runway = 'DRY' if precip == 0 else 'DAMP'
            
            # Cloud base
            if 'Clear' in condition:
                cloud_base = 25000
            elif 'Fog' in condition or 'Overcast' in condition:
                cloud_base = random.randint(300, 1000)
            elif 'Cloudy' in condition:
                cloud_base = random.randint(1000, 4000)
            else:
                cloud_base = random.randint(4000, 15000)
            
            new_weather.append({
                'airport_code': airport_code,
                'forecast_time_zulu': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'forecast_valid_from': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'forecast_valid_to': (forecast_time + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'condition': condition,
                'visibility_km': visibility,
                'wind_speed_kts': random.randint(config['wind_range'][0], config['wind_range'][1]),
                'wind_direction': random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
                'wind_gust_kts': random.randint(config['wind_range'][0] + 5, config['wind_range'][1] + 10),
                'temperature_c': random.randint(config['temp_range'][0], config['temp_range'][1]),
                'pressure_hpa': random.randint(config['pressure_range'][0], config['pressure_range'][1]),
                'precipitation_mm_per_hour': precip,
                'cloud_base_ft': cloud_base,
                'operational_impact': impact,
                'runway_condition': runway,
                'crosswind_component_kts': random.randint(0, 15)
            })

print(f"\n✓ Generated {len(new_weather)} new weather records")

# Combine with existing weather
all_weather = existing_weather + new_weather

# Write combined weather data
with open('output/weather.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=all_weather[0].keys())
    writer.writeheader()
    writer.writerows(all_weather)

print(f"✓ Total weather records: {len(all_weather)}")

# Summary by airport
print("\n" + "="*80)
print("WEATHER DATA SUMMARY")
print("="*80)

from collections import Counter
airport_counts = Counter(w['airport_code'] for w in all_weather)

print("\nRecords by Airport:")
for airport, count in sorted(airport_counts.items()):
    airport_name = AIRPORTS.get(airport, {}).get('name', 'Unknown')
    if airport_name == 'Unknown':
        # Check if it's from existing data
        if airport in ['AUH', 'BKK']:
            airport_name = 'Abu Dhabi' if airport == 'AUH' else 'Bangkok'
    print(f"  {airport}: {count} records ({airport_name})")

print(f"\nTotal Airports: {len(airport_counts)}")
print(f"Total Records: {len(all_weather)}")
print(f"Date Range: 2026-02-01 to 2026-02-03 (3 days)")
print(f"Frequency: Every 3 hours")

print("\n" + "="*80)
print("✓ WEATHER DATA ENRICHMENT COMPLETE")
print("="*80)
