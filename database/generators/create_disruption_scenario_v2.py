import csv
import random
from datetime import datetime, timedelta
from collections import defaultdict

"""
COMPREHENSIVE DISRUPTION SCENARIO GENERATOR V2

Based on flowchart:
Day 1 (08:00H): Flight EY117 (BKK → AUH) INBOUND delayed by typhoon at Bangkok
Day 2 (00:00H): Flight EY5293 (AUH → BKK) OUTBOUND delayed due to late aircraft arrival

Key Points:
- Inbound flight from BKK delayed by typhoon (Day 1)
- Same aircraft needed for outbound flight to BKK (Day 2)
- 370 passengers on outbound flight affected
- Weather data for both AUH (hub) and BKK (typhoon)
- Aircraft swap decisions at AUH hub
- Connecting passengers from AUH to other destinations
"""

# INBOUND FLIGHT (Day 1) - Delayed by typhoon at BKK
INBOUND_FLIGHT = 'EY117'
INBOUND_ORIGIN = 'BKK'
INBOUND_DESTINATION = 'AUH'
INBOUND_SCHEDULED_DEPARTURE = '2026-02-01 20:00:00'  # Day 1, 08:00H local BKK
INBOUND_SCHEDULED_ARRIVAL = '2026-02-02 02:00:00'    # Day 2, 02:00H local AUH
INBOUND_AIRCRAFT_REG = 'A6-EYM'
INBOUND_AIRCRAFT_TYPE = 'B787-10'

# OUTBOUND FLIGHT (Day 2) - Delayed due to late inbound aircraft
OUTBOUND_FLIGHT = 'EY5293'
OUTBOUND_ORIGIN = 'AUH'
OUTBOUND_DESTINATION = 'BKK'
OUTBOUND_SCHEDULED_DEPARTURE = '2026-02-02 08:15:00'  # Day 2, 00:00H local AUH
OUTBOUND_SCHEDULED_ARRIVAL = '2026-02-02 14:15:00'
OUTBOUND_TOTAL_PASSENGERS = 370
OUTBOUND_AIRCRAFT_REG = 'A6-EYM'  # Same aircraft as inbound
OUTBOUND_AIRCRAFT_TYPE = 'B787-10'

# Delay scenarios for INBOUND flight (causes outbound delay)
INBOUND_DELAY_SCENARIOS = {
    '2.5_hours': {
        'inbound_delay_minutes': 150,
        'inbound_new_arrival_auh': '2026-02-02 04:30:00',
        'outbound_delay_minutes': 150,
        'outbound_new_departure': '2026-02-02 10:45:00',
        'impacted_passengers': 8,
        'requires_accommodation': False,
        'requires_meal_vouchers': True
    },
    '4_hours': {
        'inbound_delay_minutes': 240,
        'inbound_new_arrival_auh': '2026-02-02 06:00:00',
        'outbound_delay_minutes': 240,
        'outbound_new_departure': '2026-02-02 12:15:00',
        'impacted_passengers': 71,
        'requires_accommodation': False,
        'requires_meal_vouchers': True
    },
    '6.5_hours': {
        'inbound_delay_minutes': 390,
        'inbound_new_arrival_auh': '2026-02-02 08:30:00',
        'outbound_delay_minutes': 390,
        'outbound_new_departure': '2026-02-02 14:45:00',
        'impacted_passengers': 136,
        'requires_accommodation': True,
        'requires_meal_vouchers': True
    }
}

# Load existing data
print("Loading existing datasets...")
with open('output/passengers_enriched_final.csv', 'r', encoding='utf-8') as f:
    all_passengers = list(csv.DictReader(f))

with open('output/flights_enriched_mel.csv', 'r', encoding='utf-8') as f:
    all_flights = list(csv.DictReader(f))

with open('output/aircraft_availability_enriched_mel.csv', 'r', encoding='utf-8') as f:
    aircraft_availability = list(csv.DictReader(f))

print(f"Loaded {len(all_passengers)} passengers, {len(all_flights)} flights, {len(aircraft_availability)} aircraft records")

# ============================================================================
# 1. GENERATE WEATHER DATA FOR AUH (HUB) AND BKK (TYPHOON)
# ============================================================================
print("\n1. Generating weather data...")

weather_data = []

# AUH Weather (Normal operations at hub)
auh_conditions = ['Clear', 'Partly Cloudy', 'Cloudy']
for day in range(3):  # 3 days
    for hour in range(0, 24, 3):  # Every 3 hours
        forecast_time = datetime(2026, 2, 1 + day, hour, 0, 0)
        weather_data.append({
            'airport_code': 'AUH',
            'forecast_time_zulu': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'forecast_valid_from': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'forecast_valid_to': (forecast_time + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'condition': random.choice(auh_conditions),
            'visibility_km': round(random.uniform(8.0, 10.0), 1),
            'wind_speed_kts': random.randint(5, 15),
            'wind_direction': random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
            'wind_gust_kts': random.randint(10, 20),
            'temperature_c': random.randint(20, 35),
            'pressure_hpa': random.randint(1010, 1020),
            'precipitation_mm_per_hour': 0,
            'cloud_base_ft': random.choice([25000, random.randint(1000, 5000)]),
            'operational_impact': 'NONE - Normal operations',
            'runway_condition': 'DRY',
            'crosswind_component_kts': random.randint(0, 12)
        })

# BKK Weather (Typhoon on Day 1)
bkk_conditions_day1 = [
    ('Thunderstorm', 3.0, 34, 32, 32, 'MODERATE - Delays expected, monitor closely'),
    ('Heavy Rain', 4.8, 27, 31, 12, 'MODERATE - Delays expected, monitor closely'),
    ('Typhoon', 0.8, 65, 78, 115, 'SEVERE - Airport may close, all operations suspended'),
    ('Typhoon', 1.2, 50, 92, 62, 'SEVERE - Airport may close, all operations suspended'),
    ('Typhoon', 1.2, 56, 91, 96, 'SEVERE - Airport may close, all operations suspended'),
    ('Typhoon', 0.8, 78, 82, 61, 'SEVERE - Airport may close, all operations suspended'),
    ('Typhoon', 1.0, 55, 93, 128, 'SEVERE - Airport may close, all operations suspended'),
    ('Heavy Rain', 3.6, 20, 33, 30, 'MODERATE - Delays expected, monitor closely')
]

for i, (condition, vis, wind, gust, precip, impact) in enumerate(bkk_conditions_day1):
    forecast_time = datetime(2026, 2, 1, i * 3, 0, 0)
    weather_data.append({
        'airport_code': 'BKK',
        'forecast_time_zulu': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'forecast_valid_from': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'forecast_valid_to': (forecast_time + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'condition': condition,
        'visibility_km': vis,
        'wind_speed_kts': wind,
        'wind_direction': random.choice(['N', 'NE', 'E', 'SE']),
        'wind_gust_kts': gust,
        'temperature_c': random.randint(24, 28),
        'pressure_hpa': random.randint(990, 1005),
        'precipitation_mm_per_hour': precip,
        'cloud_base_ft': random.randint(500, 2000) if 'Typhoon' in condition else random.randint(2000, 5000),
        'operational_impact': impact,
        'runway_condition': 'WET' if precip > 0 else 'DRY',
        'crosswind_component_kts': random.randint(15, 35) if 'Typhoon' in condition else random.randint(5, 15)
    })

# BKK Weather (Recovery on Day 2 and 3)
bkk_recovery_conditions = ['Cloudy', 'Light Rain', 'Partly Cloudy', 'Clear']
for day in range(2, 4):  # Days 2-3
    for hour in range(0, 24, 3):
        forecast_time = datetime(2026, 2, day, hour, 0, 0)
        condition = random.choice(bkk_recovery_conditions)
        precip = random.randint(0, 5) if 'Rain' in condition else 0
        weather_data.append({
            'airport_code': 'BKK',
            'forecast_time_zulu': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'forecast_valid_from': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'forecast_valid_to': (forecast_time + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'condition': condition,
            'visibility_km': round(random.uniform(6.0, 10.0), 1),
            'wind_speed_kts': random.randint(10, 25),
            'wind_direction': random.choice(['N', 'NE', 'E', 'SE', 'S']),
            'wind_gust_kts': random.randint(15, 30),
            'temperature_c': random.randint(25, 30),
            'pressure_hpa': random.randint(1005, 1015),
            'precipitation_mm_per_hour': precip,
            'cloud_base_ft': random.randint(2000, 8000),
            'operational_impact': 'MINOR - Some delays possible' if precip > 0 else 'NONE - Normal operations',
            'runway_condition': 'WET' if precip > 0 else 'DAMP',
            'crosswind_component_kts': random.randint(5, 15)
        })

# Write weather data
with open('output/weather.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=weather_data[0].keys())
    writer.writeheader()
    writer.writerows(weather_data)

print(f"✓ Generated {len(weather_data)} weather records (AUH hub + BKK typhoon)")

# ============================================================================
# 2. GENERATE DISRUPTED PASSENGERS FOR OUTBOUND FLIGHT (AUH → BKK)
# ============================================================================
print("\n2. Generating disrupted passenger data...")

# Get passengers on the outbound flight
outbound_passengers = [p for p in all_passengers if p['flight_number'] == OUTBOUND_FLIGHT]
print(f"Found {len(outbound_passengers)} passengers on {OUTBOUND_FLIGHT}")

disrupted_passengers = []
for passenger in outbound_passengers:
    # Determine if passenger has connection from BKK
    has_connection = random.random() < 0.62  # 62% have connections
    
    connection_flight = ''
    connection_destination = ''
    connection_departure_time = ''
    connection_buffer_minutes = 0
    delay_scenario_impacted = 'none'
    requires_hotel = 'N'
    requires_meal_voucher = 'N'
    meal_voucher_amount = 0
    compensation_priority = '5-NORMAL'
    reputation_risk = 'LOW'
    
    if has_connection:
        # Random connecting flight from BKK
        conn_destinations = ['SIN', 'HKG', 'DEL', 'SYD', 'MEL', 'PER', 'KUL', 'SGN', 'HAN', 'MNL', 'JKT', 'DPS']
        connection_destination = random.choice(conn_destinations)
        connection_flight = f"EY{random.randint(100, 9999)}"
        
        # Connection departure time (various buffers)
        arrival_bkk = datetime.strptime(OUTBOUND_SCHEDULED_ARRIVAL, '%Y-%m-%d %H:%M:%S')
        connection_buffer_minutes = random.choice([90, 120, 150, 180, 240, 300, 360, 420, 480])
        connection_departure = arrival_bkk + timedelta(minutes=connection_buffer_minutes)
        connection_departure_time = connection_departure.strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine which delay scenario impacts this passenger
        if connection_buffer_minutes <= 150:
            delay_scenario_impacted = '2.5_hours'
            requires_meal_voucher = 'Y'
            meal_voucher_amount = 50
        elif connection_buffer_minutes <= 240:
            delay_scenario_impacted = '4_hours'
            requires_meal_voucher = 'Y'
            meal_voucher_amount = 50
        elif connection_buffer_minutes <= 390:
            delay_scenario_impacted = '6.5_hours'
            requires_meal_voucher = 'Y'
            requires_hotel = 'Y'
            meal_voucher_amount = 50
    
    # Compensation priority
    if passenger['passenger_category'] == 'VVIP':
        compensation_priority = '1-HIGHEST'
    elif passenger['passenger_category'] == 'VIP':
        compensation_priority = '2-HIGH'
    elif passenger['is_influencer'] == 'Y':
        compensation_priority = '2-HIGH'
        reputation_risk = 'HIGH - Social media influencer'
    elif float(passenger['customer_value_score']) >= 7.0:
        compensation_priority = '3-MEDIUM-HIGH'
    elif passenger['frequent_flyer_tier_id'] in ['3', '4']:  # Assuming 3=Gold, 4=Platinum
        compensation_priority = '3-MEDIUM-HIGH'
    
    disrupted_passengers.append({
        'flight_number': passenger['flight_number'],
        'departure_airport': passenger['departure_airport'],
        'arrival_airport': passenger['arrival_airport'],
        'scheduled_departure': passenger['departure_time_zulu'],
        'aircraft_registration': passenger['aircraft_registration'],
        'aircraft_type': passenger['aircraft_type'],
        'pnr': passenger['pnr'],
        'passenger_id': passenger['passenger_id'],
        'traveler_id': passenger['traveler_id'],
        'first_name': passenger['first_name'],
        'last_name': passenger['last_name'],
        'passenger_category': passenger['passenger_category'],
        'frequent_flyer_tier_id': passenger['frequent_flyer_tier_id'],
        'profession': passenger['profession'],
        'is_influencer': passenger['is_influencer'],
        'customer_value_score': passenger['customer_value_score'],
        'has_connection': 'Y' if has_connection else 'N',
        'connection_flight': connection_flight,
        'connection_destination': connection_destination,
        'connection_departure_time': connection_departure_time,
        'connection_buffer_minutes': connection_buffer_minutes,
        'delay_scenario_impacted': delay_scenario_impacted,
        'requires_hotel': requires_hotel,
        'requires_meal_voucher': requires_meal_voucher,
        'meal_voucher_amount_usd': meal_voucher_amount,
        'compensation_priority': compensation_priority,
        'reputation_risk': reputation_risk
    })

# Write disrupted passengers
with open('output/disrupted_passengers_scenario.csv', 'w', newline='', encoding='utf-8') as f:
    if disrupted_passengers:
        writer = csv.DictWriter(f, fieldnames=disrupted_passengers[0].keys())
        writer.writeheader()
        writer.writerows(disrupted_passengers)

print(f"✓ Generated {len(disrupted_passengers)} disrupted passenger records")

# ============================================================================
# 3. GENERATE AIRCRAFT SWAP OPTIONS AT AUH HUB
# ============================================================================
print("\n3. Generating aircraft swap options at AUH...")

# Available aircraft at AUH or nearby
swap_options = [
    {
        'aircraft_registration': 'A6-EYN',
        'aircraft_type': 'B787-10',
        'current_location': 'AUH',
        'availability_status': 'AVAILABLE',
        'mel_status': 'CLEAR',
        'passenger_capacity': 318,
        'ferry_flight_required': 'N',
        'ferry_time_minutes': 0,
        'estimated_swap_time_minutes': 45,
        'swap_feasibility': 'HIGH',
        'crew_available': 'Y',
        'notes': 'Best option - same aircraft type, available at hub'
    },
    {
        'aircraft_registration': 'A6-EYP',
        'aircraft_type': 'B787-10',
        'current_location': 'AUH',
        'availability_status': 'AVAILABLE',
        'mel_status': 'ACTIVE',
        'passenger_capacity': 318,
        'ferry_flight_required': 'N',
        'ferry_time_minutes': 0,
        'estimated_swap_time_minutes': 45,
        'swap_feasibility': 'MEDIUM',
        'crew_available': 'Y',
        'notes': 'Same type but has active MEL - Category C'
    },
    {
        'aircraft_registration': 'A6-EYA',
        'aircraft_type': 'A380',
        'current_location': 'AUH',
        'availability_status': 'AVAILABLE',
        'mel_status': 'CLEAR',
        'passenger_capacity': 615,
        'ferry_flight_required': 'N',
        'ferry_time_minutes': 0,
        'estimated_swap_time_minutes': 60,
        'swap_feasibility': 'MEDIUM',
        'crew_available': 'N',
        'notes': 'Larger aircraft - crew availability issue, longer turnaround'
    },
    {
        'aircraft_registration': 'A6-EYE',
        'aircraft_type': 'A350',
        'current_location': 'DXB',
        'availability_status': 'AVAILABLE',
        'mel_status': 'CLEAR',
        'passenger_capacity': 283,
        'ferry_flight_required': 'Y',
        'ferry_time_minutes': 25,
        'estimated_swap_time_minutes': 70,
        'swap_feasibility': 'LOW',
        'crew_available': 'N',
        'notes': 'Requires ferry from DXB, smaller capacity, crew issue'
    }
]

# Write aircraft swap options
with open('output/aircraft_swap_options.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=swap_options[0].keys())
    writer.writeheader()
    writer.writerows(swap_options)

print(f"✓ Generated {len(swap_options)} aircraft swap options at AUH")

# ============================================================================
# 4. GENERATE INBOUND FLIGHT IMPACT ANALYSIS
# ============================================================================
print("\n4. Generating inbound flight impact analysis...")

inbound_impact = []
for scenario_name, scenario_data in INBOUND_DELAY_SCENARIOS.items():
    inbound_impact.append({
        'scenario': scenario_name,
        'inbound_flight': INBOUND_FLIGHT,
        'inbound_origin': INBOUND_ORIGIN,
        'inbound_destination': INBOUND_DESTINATION,
        'inbound_scheduled_arrival': INBOUND_SCHEDULED_ARRIVAL,
        'inbound_delay_minutes': scenario_data['inbound_delay_minutes'],
        'inbound_new_arrival_auh': scenario_data['inbound_new_arrival_auh'],
        'outbound_flight': OUTBOUND_FLIGHT,
        'outbound_scheduled_departure': OUTBOUND_SCHEDULED_DEPARTURE,
        'outbound_delay_minutes': scenario_data['outbound_delay_minutes'],
        'outbound_new_departure': scenario_data['outbound_new_departure'],
        'outbound_total_passengers': OUTBOUND_TOTAL_PASSENGERS,
        'outbound_passengers_impacted': scenario_data['impacted_passengers'],
        'aircraft_swap_recommended': 'YES' if scenario_data['outbound_delay_minutes'] >= 360 else 'NO',
        'requires_hotel_accommodation': 'YES' if scenario_data['requires_accommodation'] else 'NO',
        'requires_meal_vouchers': 'YES' if scenario_data['requires_meal_vouchers'] else 'NO',
        'estimated_compensation_cost_usd': scenario_data['impacted_passengers'] * 100,
        'disruption_cause': 'Typhoon at BKK - Inbound flight delayed',
        'recommended_action': 'Aircraft swap at AUH' if scenario_data['outbound_delay_minutes'] >= 360 else 'Wait for aircraft'
    })

# Write inbound impact
with open('output/inbound_flight_impact.csv', 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=inbound_impact[0].keys())
    writer.writeheader()
    writer.writerows(inbound_impact)

print(f"✓ Generated {len(inbound_impact)} inbound flight impact scenarios")

print("\n" + "="*80)
print("✓ COMPREHENSIVE DISRUPTION SCENARIO V2 GENERATED SUCCESSFULLY")
print("="*80)
print("\nGenerated files:")
print("  1. output/weather.csv - Weather for AUH (hub) and BKK (typhoon)")
print("  2. output/disrupted_passengers_scenario.csv - Outbound passengers impacted")
print("  3. output/aircraft_swap_options.csv - Swap options at AUH hub")
print("  4. output/inbound_flight_impact.csv - Inbound delay impact on outbound")
print("\nScenario Summary:")
print(f"  Inbound: {INBOUND_FLIGHT} ({INBOUND_ORIGIN}→{INBOUND_DESTINATION}) - Delayed by typhoon")
print(f"  Outbound: {OUTBOUND_FLIGHT} ({OUTBOUND_ORIGIN}→{OUTBOUND_DESTINATION}) - Delayed by late aircraft")
print(f"  Aircraft: {OUTBOUND_AIRCRAFT_REG} ({OUTBOUND_AIRCRAFT_TYPE})")
print(f"  Passengers: {len(disrupted_passengers)} on outbound flight")
