import csv
from collections import defaultdict

print("=" * 120)
print("COMPREHENSIVE DISRUPTION SCENARIO ANALYSIS V2")
print("=" * 120)
print("\nScenario: Inbound flight delayed by typhoon, causing outbound disruption")
print("Day 1 (08:00H): EY117 (BKK → AUH) delayed by typhoon at Bangkok")
print("Day 2 (00:00H): EY5293 (AUH → BKK) delayed due to late aircraft arrival")
print("Aircraft: B787-10 (A6-EYM)")

# 1. Weather Data
print("\n" + "=" * 120)
print("1. WEATHER FORECAST")
print("=" * 120)

with open('output/weather.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    weather = list(reader)

# Show BKK typhoon weather (Day 1)
bkk_weather = [w for w in weather if w['airport_code'] == 'BKK'][:8]
print("\n>>> BANGKOK (BKK) - TYPHOON CONDITIONS (Day 1):")
for w in bkk_weather:
    print(f"\n  {w['forecast_time_zulu']}")
    print(f"    Condition: {w['condition']}")
    print(f"    Visibility: {w['visibility_km']} km | Wind: {w['wind_speed_kts']} kts gusting {w['wind_gust_kts']} kts")
    print(f"    Precipitation: {w['precipitation_mm_per_hour']} mm/hr")
    print(f"    Impact: {w['operational_impact']}")

# Show AUH weather (Hub operations)
auh_weather = [w for w in weather if w['airport_code'] == 'AUH'][:6]
print("\n>>> ABU DHABI (AUH) - HUB OPERATIONS:")
for w in auh_weather:
    print(f"\n  {w['forecast_time_zulu']}")
    print(f"    Condition: {w['condition']}")
    print(f"    Visibility: {w['visibility_km']} km | Wind: {w['wind_speed_kts']} kts")
    print(f"    Impact: {w['operational_impact']}")

# 2. Inbound Flight Impact
print("\n" + "=" * 120)
print("2. INBOUND FLIGHT IMPACT (BKK → AUH)")
print("=" * 120)

with open('output/inbound_flight_impact.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    inbound_impact = list(reader)

print(f"\nInbound Flight: {inbound_impact[0]['inbound_flight']}")
print(f"Route: {inbound_impact[0]['inbound_origin']} → {inbound_impact[0]['inbound_destination']}")
print(f"Scheduled Arrival at AUH: {inbound_impact[0]['inbound_scheduled_arrival']}")
print(f"Disruption Cause: {inbound_impact[0]['disruption_cause']}")

for scenario in inbound_impact:
    print(f"\n{scenario['scenario'].upper()} SCENARIO:")
    print(f"  Inbound Delay: {scenario['inbound_delay_minutes']} minutes")
    print(f"  New Arrival at AUH: {scenario['inbound_new_arrival_auh']}")
    print(f"  → Outbound Flight Delay: {scenario['outbound_delay_minutes']} minutes")
    print(f"  → New Outbound Departure: {scenario['outbound_new_departure']}")
    print(f"  → Passengers Impacted: {scenario['outbound_passengers_impacted']}")
    print(f"  → Aircraft Swap Recommended: {scenario['aircraft_swap_recommended']}")
    print(f"  → Estimated Cost: ${int(scenario['estimated_compensation_cost_usd']):,}")

# 3. Outbound Passenger Impact
print("\n" + "=" * 120)
print("3. OUTBOUND PASSENGER IMPACT (AUH → BKK)")
print("=" * 120)

with open('output/disrupted_passengers_scenario.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    passengers = list(reader)

total_pax = len(passengers)
with_connections = [p for p in passengers if p['has_connection'] == 'Y']
vvip = [p for p in passengers if p['passenger_category'] == 'VVIP']
vip = [p for p in passengers if p['passenger_category'] == 'VIP']
influencers = [p for p in passengers if p['is_influencer'] == 'Y']

print(f"\nOutbound Flight: {passengers[0]['flight_number']}")
print(f"Route: {passengers[0]['departure_airport']} → {passengers[0]['arrival_airport']}")
print(f"Total Passengers: {total_pax}")
print(f"Passengers with Connections from BKK: {len(with_connections)} ({len(with_connections)/total_pax*100:.1f}%)")
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

for i, p in enumerate(high_risk[:7], 1):
    print(f"\n  {i}. {p['first_name']} {p['last_name']}")
    print(f"     Category: {p['passenger_category']} | Profession: {p['profession']}")
    print(f"     Risk: {p['reputation_risk']}")
    print(f"     CVS: {p['customer_value_score']}/10")
    if p['has_connection'] == 'Y':
        print(f"     Connection: {p['connection_flight']} to {p['connection_destination']}")

# 4. Aircraft Swap Options
print("\n" + "=" * 120)
print("4. AIRCRAFT SWAP OPTIONS AT AUH HUB")
print("=" * 120)

with open('output/aircraft_swap_options.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    swap_options = list(reader)

print(f"\nAvailable Aircraft for Swap at AUH: {len(swap_options)}")

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
    print(f"    Notes: {aircraft['notes']}")

# 5. Decision Matrix
print("\n" + "=" * 120)
print("5. DECISION MATRIX & RECOMMENDATIONS")
print("=" * 120)

print("\nIF INBOUND DELAY IS 2.5 HOURS:")
print("  ✓ Wait for aircraft - no swap needed")
print("  ✓ Outbound delay: 2.5 hours")
print("  ✓ Provide meal vouchers to 8 impacted passengers")
print("  ✓ Rebook 8 passengers on next available flights from BKK")
print("  ✓ Estimated cost: ~$800")

print("\nIF INBOUND DELAY IS 4 HOURS:")
print("  ⚠ Consider aircraft swap")
print("  ✓ Outbound delay: 4 hours")
print("  ✓ Provide meal vouchers to 71 impacted passengers")
print("  ✓ Rebook 71 passengers on next available flights from BKK")
print("  ✓ Priority handling for VIP/VVIP passengers")
print("  ✓ Estimated cost: ~$7,100")

print("\nIF INBOUND DELAY IS 6.5+ HOURS:")
print("  ⚠⚠ AIRCRAFT SWAP HIGHLY RECOMMENDED")
print("  ✓ Outbound delay: 6.5+ hours")
print("  ✓ Provide meal vouchers to 136 impacted passengers")
print("  ✓ Provide hotel accommodation to 136 passengers")
print("  ✓ Rebook 136 passengers on next day flights from BKK")
print("  ⚠ High reputation risk with influencers")
print("  ⚠ Estimated cost: ~$40,000+")
print("\n  RECOMMENDED ACTION:")
print("    1. Activate aircraft swap with A6-EYN at AUH (best option)")
print("    2. Prioritize VIP/VVIP/Influencer passengers")
print("    3. Proactive communication to all passengers")
print("    4. Coordinate with hotels for accommodation at BKK")
print("    5. Prepare compensation packages")
print("    6. Monitor typhoon conditions at BKK for safe operations")

print("\n" + "=" * 120)
print("KEY INSIGHTS:")
print("=" * 120)
print("\n  • Disruption originates from BKK typhoon affecting INBOUND flight")
print("  • Same aircraft (A6-EYM) needed for OUTBOUND flight causes cascading delay")
print("  • Aircraft swap decision made at AUH hub (not at outstation)")
print("  • A6-EYN is best swap option - same type, available at hub, no MEL")
print("  • 62% of outbound passengers have connections from BKK")
print("  • Social media influencers require special attention for reputation management")
print("  • Weather at AUH is normal - disruption is purely from late aircraft")

print("\n" + "=" * 120)
print("✓ COMPREHENSIVE DISRUPTION ANALYSIS V2 COMPLETE")
print("=" * 120)
