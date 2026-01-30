import csv
from collections import defaultdict

print("=" * 120)
print("COMPREHENSIVE DISRUPTION SCENARIO ANALYSIS")
print("=" * 120)
print("\nFlight: EY5293 (AUH → BKK)")
print("Disruption: Typhoon at Bangkok")
print("Aircraft: B787-10 (A6-EYM)")

# 1. Weather Data
print("\n" + "=" * 120)
print("1. WEATHER FORECAST - BANGKOK (BKK)")
print("=" * 120)

with open('output/weather.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    weather = [w for w in reader if w['airport_code'] == 'BKK']

print("\nCritical Weather Periods:")
for w in weather[:8]:
    print(f"\n  {w['forecast_time_zulu']}")
    print(f"    Condition: {w['condition']}")
    print(f"    Visibility: {w['visibility_km']} km | Wind: {w['wind_speed_kts']} kts gusting {w['wind_gust_kts']} kts")
    print(f"    Precipitation: {w['precipitation_mm_per_hour']} mm/hr")
    print(f"    Impact: {w['operational_impact']}")

# 2. Passenger Impact
print("\n" + "=" * 120)
print("2. PASSENGER IMPACT ANALYSIS")
print("=" * 120)

with open('output/disrupted_passengers_scenario.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    passengers = list(reader)

total_pax = len(passengers)
with_connections = [p for p in passengers if p['has_connection'] == 'Y']
vvip = [p for p in passengers if p['passenger_category'] == 'VVIP']
vip = [p for p in passengers if p['passenger_category'] == 'VIP']
influencers = [p for p in passengers if p['is_influencer'] == 'Y']

print(f"\nTotal Passengers: {total_pax}")
print(f"Passengers with Connections: {len(with_connections)} ({len(with_connections)/total_pax*100:.1f}%)")
print(f"VVIP Passengers: {len(vvip)}")
print(f"VIP Passengers: {len(vip)}")
print(f"Social Media Influencers: {len(influencers)}")

# By delay scenario
print("\n" + "-" * 120)
print("IMPACT BY DELAY SCENARIO:")
print("-" * 120)

scenarios = defaultdict(list)
for p in with_connections:
    scenarios[p['delay_scenario_impacted']].append(p)

for scenario, pax_list in sorted(scenarios.items()):
    if scenario == 'none':
        continue
    print(f"\n{scenario.upper()} DELAY:")
    print(f"  Passengers Missing Connections: {len(pax_list)}")
    
    needs_hotel = sum(1 for p in pax_list if p['requires_hotel'] == 'Y')
    needs_meal = sum(1 for p in pax_list if p['requires_meal_voucher'] == 'Y')
    high_priority = sum(1 for p in pax_list if p['compensation_priority'] in ['1-HIGHEST', '2-HIGH'])
    
    print(f"  Require Hotel: {needs_hotel}")
    print(f"  Require Meal Vouchers: {needs_meal}")
    print(f"  High Priority (VIP/VVIP/Influencer): {high_priority}")
    
    # Calculate costs
    total_meal_cost = sum(int(p['meal_voucher_amount_usd']) for p in pax_list)
    print(f"  Estimated Meal Voucher Cost: ${total_meal_cost:,}")
    
    if needs_hotel > 0:
        hotel_cost = needs_hotel * 200  # Average hotel cost
        print(f"  Estimated Hotel Cost: ${hotel_cost:,}")

# High-risk passengers
print("\n" + "-" * 120)
print("HIGH-RISK PASSENGERS (Reputation Impact):")
print("-" * 120)

high_risk = [p for p in passengers if 'HIGH' in p.get('reputation_risk', '')]
print(f"\nTotal High-Risk Passengers: {len(high_risk)}")

for i, p in enumerate(high_risk[:5], 1):
    print(f"\n  {i}. {p['first_name']} {p['last_name']}")
    print(f"     Category: {p['passenger_category']} | Profession: {p['profession']}")
    print(f"     Risk: {p['reputation_risk']}")
    print(f"     CVS: {p['customer_value_score']}/10")
    if p['has_connection'] == 'Y':
        print(f"     Connection: {p['connection_flight']} to {p['connection_destination']}")

# 3. Aircraft Swap Options
print("\n" + "=" * 120)
print("3. AIRCRAFT SWAP OPTIONS AT BKK")
print("=" * 120)

with open('output/aircraft_swap_options.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    swap_options = list(reader)

print(f"\nAvailable Aircraft for Swap: {len(swap_options)}")

for i, aircraft in enumerate(swap_options, 1):
    print(f"\n  Option {i}: {aircraft['aircraft_registration']} ({aircraft['aircraft_type']})")
    print(f"    Location: {aircraft['current_location']}")
    print(f"    Status: {aircraft['availability_status']} | MEL: {aircraft['mel_status']}")
    print(f"    Capacity: {aircraft['passenger_capacity']} passengers")
    print(f"    Ferry Required: {aircraft['ferry_flight_required']}")
    if aircraft['ferry_flight_required'] == 'Y':
        print(f"    Ferry Time: {aircraft['ferry_time_minutes']} minutes")
    print(f"    Swap Time: {aircraft['estimated_swap_time_minutes']} minutes")
    print(f"    Feasibility: {aircraft['swap_feasibility']}")
    print(f"    Crew Available: {aircraft['crew_available']}")

# 4. Return Flight Impact
print("\n" + "=" * 120)
print("4. RETURN FLIGHT IMPACT (BKK → AUH)")
print("=" * 120)

with open('output/return_flight_impact.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    return_impact = list(reader)

print(f"\nReturn Flight: {return_impact[0]['return_flight_number']}")
print(f"Original Departure: {return_impact[0]['return_original_departure']}")

for scenario in return_impact:
    print(f"\n{scenario['scenario'].upper()} SCENARIO:")
    print(f"  Outbound Delay: {scenario['outbound_delay_minutes']} minutes")
    print(f"  New Arrival at BKK: {scenario['outbound_new_arrival_bkk']}")
    print(f"  Return Flight Delay: {scenario['return_delay_minutes']} minutes")
    print(f"  Earliest Return Departure: {scenario['return_earliest_departure']}")
    print(f"  Return Passengers Total: {scenario['return_total_passengers']}")
    print(f"  Return Passengers with Connections: {scenario['return_passengers_with_connections']}")
    print(f"  Return Passengers Impacted: {scenario['return_passengers_impacted']}")
    print(f"  Aircraft Swap Recommended: {scenario['aircraft_swap_recommended']}")
    print(f"  Total Impacted (Both Flights): {scenario['total_passengers_impacted_both_flights']}")
    print(f"  Estimated Total Cost: ${int(scenario['total_compensation_cost_estimate_usd']):,}")

# 5. Decision Matrix
print("\n" + "=" * 120)
print("5. DECISION MATRIX & RECOMMENDATIONS")
print("=" * 120)

print("\nIF DELAY IS 2.5 HOURS:")
print("  ✓ No aircraft swap needed")
print("  ✓ Provide meal vouchers to 8 impacted passengers")
print("  ✓ Rebook 8 passengers on next available flights")
print("  ✓ Return flight minimal impact")
print("  ✓ Estimated cost: ~$1,000")

print("\nIF DELAY IS 4 HOURS:")
print("  ⚠ Consider aircraft swap")
print("  ✓ Provide meal vouchers to 71 impacted passengers")
print("  ✓ Rebook 71 passengers on next available flights")
print("  ✓ Priority handling for VIP/VVIP passengers")
print("  ⚠ Return flight delayed ~2 hours, 40 passengers impacted")
print("  ✓ Estimated cost: ~$16,000")

print("\nIF DELAY IS 6.5+ HOURS:")
print("  ⚠ AIRCRAFT SWAP HIGHLY RECOMMENDED")
print("  ✓ Provide meal vouchers to 136 impacted passengers")
print("  ✓ Provide hotel accommodation to 136 passengers")
print("  ✓ Rebook 136 passengers on next day flights")
print("  ⚠ Return flight delayed ~4+ hours, 140+ passengers impacted")
print("  ⚠ High reputation risk with influencers")
print("  ⚠ Estimated cost: ~$50,000+")
print("\n  RECOMMENDED ACTION:")
print("    1. Activate aircraft swap with A6-EYN (available at BKK)")
print("    2. Prioritize VIP/VVIP/Influencer passengers")
print("    3. Proactive communication to all passengers")
print("    4. Coordinate with hotels for accommodation")
print("    5. Prepare compensation packages")

print("\n" + "=" * 120)
print("✓ COMPREHENSIVE DISRUPTION ANALYSIS COMPLETE")
print("=" * 120)
