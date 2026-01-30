import csv
import random
from datetime import datetime, timedelta
from collections import defaultdict

# Scenario: AUH-BKK flight disrupted by typhoon
DISRUPTED_FLIGHT = 'EY5293'
ORIGIN = 'AUH'
DESTINATION = 'BKK'
SCHEDULED_DEPARTURE = '2026-02-02 08:15:00'
SCHEDULED_ARRIVAL = '2026-02-02 14:15:00'
TOTAL_PASSENGERS = 370
AIRCRAFT_REG = 'A6-EYM'
AIRCRAFT_TYPE = 'B787-10'

# Return flight
RETURN_FLIGHT = 'EY117'
RETURN_DEPARTURE = '2026-02-03 04:30:00'
RETURN_ARRIVAL = '2026-02-03 10:30:00'

# Delay scenarios
DELAY_SCENARIOS = {
    '2.5_hours': {
        'delay_minutes': 150,
        'impacted_passengers': 20,
        'requires_accommodation': False,
        'requires_meal_vouchers': True
    },
    '4_hours': {
        'delay_minutes': 240,
        'impacted_passengers': 120,
        'requires_accommodation': False,
        'requires_meal_vouchers': True
    },
    '6.5_hours': {
        'delay_minutes': 390,
        'impacted_passengers': 210,
        'requires_accommodation': True,
        'requires_meal_vouchers': True
    }
}

def create_weather_forecast():
    """Create weather forecast data for key airports"""
    weather_data = []
    
    # Weather conditions
    conditions = ['Clear', 'Partly Cloudy', 'Cloudy', 'Rain', 'Heavy Rain', 'Thunderstorm', 'Typhoon', 'Fog']
    
    # Airports to monitor
    airports = ['AUH', 'BKK', 'DEL', 'SIN', 'DOH', 'DXB']
    
    # Generate forecast for next 24 hours
    base_time = datetime.strptime('2026-02-02 00:00:00', '%Y-%m-%d %H:%M:%S')
    
    for airport in airports:
        for hour in range(0, 25, 3):  # Every 3 hours
            forecast_time = base_time + timedelta(hours=hour)
            
            # BKK has typhoon conditions
            if airport == 'BKK' and 6 <= hour <= 18:
                condition = 'Typhoon'
                visibility_km = random.uniform(0.5, 2.0)
                wind_speed_kts = random.randint(50, 80)
                wind_gust_kts = random.randint(70, 100)
                temperature_c = random.randint(26, 29)
                pressure_hpa = random.randint(980, 995)
                precipitation_mm = random.randint(50, 150)
                operational_impact = 'SEVERE - Airport may close, all operations suspended'
            elif airport == 'BKK':
                condition = random.choice(['Heavy Rain', 'Thunderstorm', 'Rain'])
                visibility_km = random.uniform(3.0, 8.0)
                wind_speed_kts = random.randint(20, 35)
                wind_gust_kts = random.randint(30, 45)
                temperature_c = random.randint(27, 31)
                pressure_hpa = random.randint(1005, 1012)
                precipitation_mm = random.randint(10, 40)
                operational_impact = 'MODERATE - Delays expected, monitor closely'
            else:
                condition = random.choice(['Clear', 'Partly Cloudy', 'Cloudy'])
                visibility_km = random.uniform(8.0, 10.0)
                wind_speed_kts = random.randint(5, 15)
                wind_gust_kts = random.randint(10, 20)
                temperature_c = random.randint(20, 35)
                pressure_hpa = random.randint(1010, 1020)
                precipitation_mm = 0
                operational_impact = 'NONE - Normal operations'
            
            weather_data.append({
                'airport_code': airport,
                'forecast_time_zulu': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'forecast_valid_from': forecast_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'forecast_valid_to': (forecast_time + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'condition': condition,
                'visibility_km': f"{visibility_km:.1f}",
                'wind_speed_kts': wind_speed_kts,
                'wind_direction': random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
                'wind_gust_kts': wind_gust_kts,
                'temperature_c': temperature_c,
                'pressure_hpa': pressure_hpa,
                'precipitation_mm_per_hour': precipitation_mm,
                'cloud_base_ft': random.randint(500, 8000) if condition != 'Clear' else 25000,
                'operational_impact': operational_impact,
                'runway_condition': 'WET' if precipitation_mm > 0 else 'DRY',
                'crosswind_component_kts': random.randint(0, 15)
            })
    
    return weather_data

def create_disruption_passengers():
    """Create passenger data for disrupted flight with connection details"""
    passengers = []
    
    # Read existing passengers
    with open('output/passengers_enriched_final.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        all_passengers = [p for p in reader if p['flight_number'] == DISRUPTED_FLIGHT]
    
    # If we don't have enough, we'll create synthetic ones
    if len(all_passengers) < TOTAL_PASSENGERS:
        print(f"Note: Only found {len(all_passengers)} passengers for {DISRUPTED_FLIGHT}, creating additional synthetic data")
    
    # Take first 370 passengers or all available
    selected_passengers = all_passengers[:TOTAL_PASSENGERS]
    
    # Assign connection status
    for i, pax in enumerate(selected_passengers):
        # Determine if passenger has connection
        has_connection = random.random() < 0.60  # 60% have connections
        
        if has_connection:
            # Assign to delay scenario
            scenario_choice = random.random()
            if scenario_choice < 0.05:  # 5% affected by 2.5hr delay
                connection_buffer_minutes = random.randint(150, 180)
                delay_scenario = '2.5_hours'
            elif scenario_choice < 0.35:  # 30% affected by 4hr delay
                connection_buffer_minutes = random.randint(240, 300)
                delay_scenario = '4_hours'
            else:  # 65% affected by 6.5hr delay
                connection_buffer_minutes = random.randint(390, 480)
                delay_scenario = '6.5_hours'
            
            # Connection flight details
            connecting_flights = ['EY8086', 'EY6005', 'EY2348', 'EY259', 'EY767']
            connecting_destinations = ['FCO', 'FRA', 'LHR', 'CDG', 'JFK']
            
            conn_flight = random.choice(connecting_flights)
            conn_dest = random.choice(connecting_destinations)
            
            arrival_time = datetime.strptime(SCHEDULED_ARRIVAL, '%Y-%m-%d %H:%M:%S')
            connection_time = arrival_time + timedelta(minutes=connection_buffer_minutes)
            
            pax['has_connection'] = 'Y'
            pax['connection_flight'] = conn_flight
            pax['connection_destination'] = conn_dest
            pax['connection_departure_time'] = connection_time.strftime('%Y-%m-%d %H:%M:%S')
            pax['connection_buffer_minutes'] = connection_buffer_minutes
            pax['delay_scenario_impacted'] = delay_scenario
            pax['will_miss_connection'] = 'Y'
            pax['requires_rebooking'] = 'Y'
            pax['requires_meal_voucher'] = 'Y' if DELAY_SCENARIOS[delay_scenario]['requires_meal_vouchers'] else 'N'
            pax['requires_hotel'] = 'Y' if DELAY_SCENARIOS[delay_scenario]['requires_accommodation'] else 'N'
            
            # Calculate compensation based on passenger category and delay
            if pax['passenger_category'] == 'VVIP':
                pax['compensation_priority'] = '1-HIGHEST'
                pax['lounge_access'] = 'First Class Lounge'
                pax['meal_voucher_amount_usd'] = '150'
                pax['hotel_category'] = '5-Star'
            elif pax['passenger_category'] == 'VIP':
                pax['compensation_priority'] = '2-HIGH'
                pax['lounge_access'] = 'Business Class Lounge'
                pax['meal_voucher_amount_usd'] = '100'
                pax['hotel_category'] = '4-Star'
            elif pax['is_influencer'] == 'Y':
                pax['compensation_priority'] = '2-HIGH'
                pax['lounge_access'] = 'Business Class Lounge'
                pax['meal_voucher_amount_usd'] = '100'
                pax['hotel_category'] = '4-Star'
                pax['reputation_risk'] = 'HIGH - Social media influencer'
            elif float(pax['customer_value_score']) >= 7.0:
                pax['compensation_priority'] = '3-MEDIUM'
                pax['lounge_access'] = 'Business Class Lounge'
                pax['meal_voucher_amount_usd'] = '75'
                pax['hotel_category'] = '3-Star'
            else:
                pax['compensation_priority'] = '4-STANDARD'
                pax['lounge_access'] = 'Standard Lounge'
                pax['meal_voucher_amount_usd'] = '50'
                pax['hotel_category'] = '3-Star'
            
            # Reputation risk
            if pax.get('reputation_risk', '') == '':
                if pax['is_influencer'] == 'Y':
                    pax['reputation_risk'] = 'HIGH - Social media influencer'
                elif pax['passenger_category'] in ['VIP', 'VVIP']:
                    pax['reputation_risk'] = 'MEDIUM - VIP passenger'
                else:
                    pax['reputation_risk'] = 'LOW'
        else:
            pax['has_connection'] = 'N'
            pax['connection_flight'] = ''
            pax['connection_destination'] = ''
            pax['connection_departure_time'] = ''
            pax['connection_buffer_minutes'] = ''
            pax['delay_scenario_impacted'] = 'none'
            pax['will_miss_connection'] = 'N'
            pax['requires_rebooking'] = 'N'
            pax['requires_meal_voucher'] = 'Y'  # All get meal vouchers
            pax['requires_hotel'] = 'N'
            pax['compensation_priority'] = '4-STANDARD'
            pax['lounge_access'] = 'Standard Lounge'
            pax['meal_voucher_amount_usd'] = '30'
            pax['hotel_category'] = 'N/A'
            pax['reputation_risk'] = 'LOW'
        
        passengers.append(pax)
    
    return passengers

def create_aircraft_swap_options():
    """Create aircraft swap options at BKK"""
    swap_options = []
    
    # Aircraft potentially available at BKK or nearby
    available_aircraft = [
        {'registration': 'A6-EYN', 'type': 'B787-10', 'location': 'BKK', 'status': 'AVAILABLE', 'mel_status': 'CLEAR'},
        {'registration': 'A6-EYP', 'type': 'B787-10', 'location': 'BKK', 'status': 'AVAILABLE', 'mel_status': 'ACTIVE'},
        {'registration': 'A6-EYQ', 'type': 'B777X', 'location': 'SIN', 'status': 'AVAILABLE', 'mel_status': 'CLEAR'},
        {'registration': 'A6-EYE', 'type': 'A350', 'location': 'DEL', 'status': 'AVAILABLE', 'mel_status': 'CLEAR'},
    ]
    
    for aircraft in available_aircraft:
        ferry_time = 0 if aircraft['location'] == 'BKK' else random.randint(90, 180)
        
        swap_options.append({
            'aircraft_registration': aircraft['registration'],
            'aircraft_type': aircraft['type'],
            'current_location': aircraft['location'],
            'availability_status': aircraft['status'],
            'mel_status': aircraft['mel_status'],
            'ferry_flight_required': 'Y' if aircraft['location'] != 'BKK' else 'N',
            'ferry_time_minutes': ferry_time,
            'crew_available': random.choice(['Y', 'Y', 'N']),
            'swap_feasibility': 'HIGH' if aircraft['location'] == 'BKK' and aircraft['mel_status'] == 'CLEAR' else 'MEDIUM',
            'estimated_swap_time_minutes': 45 if aircraft['location'] == 'BKK' else 45 + ferry_time,
            'passenger_capacity': 318 if 'B787' in aircraft['type'] else 426 if 'B777' in aircraft['type'] else 283,
            'suitable_for_route': 'Y' if aircraft['type'] in ['B787-10', 'B777X', 'A350'] else 'N'
        })
    
    return swap_options

def create_return_flight_impact():
    """Create impact analysis for return flight BKK-AUH"""
    impact_data = []
    
    for delay_scenario, details in DELAY_SCENARIOS.items():
        delay_minutes = details['delay_minutes']
        
        # Calculate new arrival time at BKK
        original_arrival = datetime.strptime(SCHEDULED_ARRIVAL, '%Y-%m-%d %H:%M:%S')
        delayed_arrival = original_arrival + timedelta(minutes=delay_minutes)
        
        # Minimum turnaround time
        min_turnaround = 90  # minutes
        
        # Return flight original departure
        return_departure = datetime.strptime(RETURN_DEPARTURE, '%Y-%m-%d %H:%M:%S')
        
        # Calculate return flight delay
        earliest_return_departure = delayed_arrival + timedelta(minutes=min_turnaround)
        return_delay_minutes = max(0, (earliest_return_departure - return_departure).total_seconds() / 60)
        
        # Passengers impacted on return flight
        return_passengers_total = 350
        return_passengers_with_connections = int(return_passengers_total * 0.55)
        
        # Calculate how many miss connections
        if return_delay_minutes <= 120:
            return_impacted = int(return_passengers_with_connections * 0.10)
        elif return_delay_minutes <= 240:
            return_impacted = int(return_passengers_with_connections * 0.40)
        else:
            return_impacted = int(return_passengers_with_connections * 0.75)
        
        impact_data.append({
            'scenario': delay_scenario,
            'outbound_delay_minutes': delay_minutes,
            'outbound_new_arrival_bkk': delayed_arrival.strftime('%Y-%m-%d %H:%M:%S'),
            'return_flight_number': RETURN_FLIGHT,
            'return_original_departure': RETURN_DEPARTURE,
            'return_earliest_departure': earliest_return_departure.strftime('%Y-%m-%d %H:%M:%S'),
            'return_delay_minutes': int(return_delay_minutes),
            'return_total_passengers': return_passengers_total,
            'return_passengers_with_connections': return_passengers_with_connections,
            'return_passengers_impacted': return_impacted,
            'aircraft_swap_recommended': 'YES' if return_delay_minutes > 240 else 'CONSIDER' if return_delay_minutes > 120 else 'NO',
            'total_passengers_impacted_both_flights': details['impacted_passengers'] + return_impacted,
            'total_compensation_cost_estimate_usd': (details['impacted_passengers'] * 100) + (return_impacted * 100)
        })
    
    return impact_data

def main():
    print("=" * 100)
    print("CREATING COMPREHENSIVE DISRUPTION SCENARIO DATA")
    print("=" * 100)
    print(f"\nScenario: Flight {DISRUPTED_FLIGHT} ({ORIGIN}-{DESTINATION})")
    print(f"Disruption: Typhoon at {DESTINATION}")
    print(f"Aircraft: {AIRCRAFT_TYPE} ({AIRCRAFT_REG})")
    print(f"Passengers: {TOTAL_PASSENGERS}")
    
    # 1. Weather forecast
    print("\n1. Creating weather forecast data...")
    weather_data = create_weather_forecast()
    with open('output/weather.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=weather_data[0].keys())
        writer.writeheader()
        writer.writerows(weather_data)
    print(f"   ✓ Created {len(weather_data)} weather forecast records")
    
    # 2. Disrupted passengers
    print("\n2. Creating disrupted passenger data...")
    passengers = create_disruption_passengers()
    
    fieldnames = list(passengers[0].keys())
    with open('output/disrupted_passengers_scenario.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(passengers)
    print(f"   ✓ Created {len(passengers)} passenger records with connection details")
    
    # Statistics
    with_connections = sum(1 for p in passengers if p['has_connection'] == 'Y')
    scenario_25 = sum(1 for p in passengers if p['delay_scenario_impacted'] == '2.5_hours')
    scenario_4 = sum(1 for p in passengers if p['delay_scenario_impacted'] == '4_hours')
    scenario_65 = sum(1 for p in passengers if p['delay_scenario_impacted'] == '6.5_hours')
    
    print(f"   - Passengers with connections: {with_connections}")
    print(f"   - Impacted by 2.5hr delay: {scenario_25}")
    print(f"   - Impacted by 4hr delay: {scenario_4}")
    print(f"   - Impacted by 6.5hr delay: {scenario_65}")
    
    # 3. Aircraft swap options
    print("\n3. Creating aircraft swap options...")
    swap_options = create_aircraft_swap_options()
    with open('output/aircraft_swap_options.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=swap_options[0].keys())
        writer.writeheader()
        writer.writerows(swap_options)
    print(f"   ✓ Created {len(swap_options)} aircraft swap options")
    
    # 4. Return flight impact
    print("\n4. Creating return flight impact analysis...")
    return_impact = create_return_flight_impact()
    with open('output/return_flight_impact.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=return_impact[0].keys())
        writer.writeheader()
        writer.writerows(return_impact)
    print(f"   ✓ Created {len(return_impact)} return flight impact scenarios")
    
    print("\n" + "=" * 100)
    print("✓ DISRUPTION SCENARIO DATA CREATED SUCCESSFULLY")
    print("=" * 100)
    print("\nFiles created:")
    print("  1. output/weather.csv - Weather forecast for key airports")
    print("  2. output/disrupted_passengers_scenario.csv - Passenger impact analysis")
    print("  3. output/aircraft_swap_options.csv - Aircraft swap alternatives")
    print("  4. output/return_flight_impact.csv - Return flight impact analysis")

if __name__ == '__main__':
    main()
