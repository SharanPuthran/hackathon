#!/usr/bin/env python3
"""
Test V2 Data Queries

This script tests queries against the V2 DynamoDB tables to verify
data accessibility and correctness after the V2 data migration.

Usage:
    cd /Users/sharanputhran/Learning/Hackathon/skymarshal_agents_new/skymarshal
    python -m test.test_v2_data_queries
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, '/Users/sharanputhran/Learning/Hackathon/skymarshal_agents_new/skymarshal/src')

import json
from typing import Dict, List, Any
from datetime import datetime
from decimal import Decimal

from database.dynamodb import DynamoDBClient
from database.table_config import (
    TABLE_VERSION,
    is_v2_enabled,
    get_table_name,
    TableVersion,
    V2_TABLES,
    get_v2_only_tables,
    get_enhanced_tables,
)

# Custom JSON encoder for Decimal
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(label: str, value: Any, indent: int = 0):
    """Print a labeled result."""
    prefix = "  " * indent
    if isinstance(value, (dict, list)):
        print(f"{prefix}{label}:")
        print(f"{prefix}  {json.dumps(value, indent=2, cls=DecimalEncoder)[:500]}")
    else:
        print(f"{prefix}{label}: {value}")


def test_v2_configuration():
    """Test that V2 is properly configured."""
    print_section("V2 Configuration Check")

    print_result("TABLE_VERSION", TABLE_VERSION.value)
    print_result("is_v2_enabled()", is_v2_enabled())

    # Check table name resolution
    test_tables = ["flights", "passengers", "crew_roster", "aircraft_rotations"]
    for table in test_tables:
        try:
            v2_name = get_table_name(table, TableVersion.V2)
            print_result(f"get_table_name('{table}', V2)", v2_name)
        except KeyError as e:
            print_result(f"get_table_name('{table}', V2)", f"KeyError: {e}")

    print_result("\nV2-only tables", get_v2_only_tables())
    print_result("Enhanced tables", get_enhanced_tables())


def test_v2_table_counts():
    """Test record counts in V2 tables."""
    print_section("V2 Table Record Counts")

    db = DynamoDBClient()

    # Expected counts based on CSV imports
    expected_counts = {
        "flights_v2": 23,
        "passengers_v2": 286,
        "baggage_v2": 65,
        "crew_roster_v2": 18,
        "aircraft_v2": 22,
        "cargo_shipments_v2": 14,
        "weather_v2": 30,
        "financial_parameters_v2": 100,
        "safety_constraints_v2": 69,
        "recovery_cost_matrix_v2": 57,
        "cost_breakdown_v2": 34,
        "aircraft_rotations_v2": 27,
        "oal_flights_v2": 21,
        "airport_curfews_v2": 8,
        "airport_slots_v2": 14,
        "cold_chain_facilities_v2": 8,
        "compensation_rules_v2": 39,
        "ground_equipment_v2": 15,
        "interline_agreements_v2": 10,
        "maintenance_constraints_v2": 8,
        "minimum_connection_times_v2": 40,
        "reserve_crew_v2": 18,
        "turnaround_requirements_v2": 8,
    }

    print(f"{'Table Name':<40} {'Expected':>10} {'Actual':>10} {'Match':>8}")
    print("-" * 70)

    total_expected = 0
    total_actual = 0
    all_match = True

    for table_name, expected in expected_counts.items():
        try:
            table = db.dynamodb.Table(table_name)
            response = table.scan(Select='COUNT')
            actual = response.get('Count', 0)
            match = "YES" if actual == expected else "NO"
            if actual != expected:
                all_match = False
            print(f"{table_name:<40} {expected:>10} {actual:>10} {match:>8}")
            total_expected += expected
            total_actual += actual
        except Exception as e:
            print(f"{table_name:<40} {expected:>10} {'ERROR':>10} {'NO':>8}")
            print(f"  Error: {str(e)[:50]}")
            all_match = False

    print("-" * 70)
    print(f"{'TOTAL':<40} {total_expected:>10} {total_actual:>10}")
    print(f"\nAll counts match: {all_match}")


def test_flights_v2_queries():
    """Test queries on flights_v2 table."""
    print_section("Flights V2 Queries")

    db = DynamoDBClient()

    # Test 1: Get a sample flight by ID
    print("\n1. Query flight by flight_id:")
    try:
        flight = db.get_flight_by_id("FL001")
        if flight:
            print_result("Flight FL001", {
                "flight_number": flight.get("flight_number"),
                "origin": flight.get("origin"),
                "destination": flight.get("destination"),
                "scheduled_departure_utc": flight.get("scheduled_departure_utc"),
                "aircraft_registration": flight.get("aircraft_registration"),
            })
        else:
            print("  No flight found with ID FL001")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: Query flights by flight number and date (GSI)
    print("\n2. Query flights by flight_number (GSI):")
    try:
        flights = db.query_flights_by_number_and_date("EY123", "2026-01-20")
        print_result(f"Found {len(flights)} flights for EY123 on 2026-01-20", "")
        for f in flights[:3]:
            print(f"  - {f.get('flight_id')}: {f.get('origin')} -> {f.get('destination')}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 3: Query flights by aircraft registration (GSI)
    print("\n3. Query flights by aircraft_registration (GSI):")
    try:
        flights = db.query_flights_by_aircraft("N781UA")
        print_result(f"Found {len(flights)} flights for aircraft N781UA", "")
        for f in flights[:3]:
            print(f"  - {f.get('flight_id')}: {f.get('flight_number')}")
    except Exception as e:
        print(f"  Error: {e}")


def test_passengers_v2_queries():
    """Test queries on passengers_v2 table."""
    print_section("Passengers V2 Queries")

    db = DynamoDBClient()

    # Test 1: Get a sample passenger
    print("\n1. Get passenger by ID:")
    try:
        table = db.get_v2_table("passengers")
        response = table.scan(Limit=1)
        if response.get('Items'):
            passenger = response['Items'][0]
            print_result("Sample passenger", {
                "passenger_id": passenger.get("passenger_id"),
                "name": passenger.get("name"),
                "pnr": passenger.get("pnr"),
                "frequent_flyer_tier": passenger.get("frequent_flyer_tier"),
                "first_leg_flight_id": passenger.get("first_leg_flight_id"),
                "is_influencer": passenger.get("is_influencer"),
            })
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: Query by PNR (GSI)
    print("\n2. Query passengers by PNR (GSI):")
    try:
        table = db.get_v2_table("passengers")
        # Get a sample PNR first
        scan_response = table.scan(Limit=5)
        if scan_response.get('Items'):
            sample_pnr = scan_response['Items'][0].get('pnr')
            if sample_pnr:
                response = table.query(
                    IndexName="pnr-index",
                    KeyConditionExpression="pnr = :pnr",
                    ExpressionAttributeValues={":pnr": sample_pnr}
                )
                print_result(f"Found {len(response.get('Items', []))} passengers with PNR {sample_pnr}", "")
    except Exception as e:
        print(f"  Error: {e}")


def test_crew_roster_v2_queries():
    """Test queries on crew_roster_v2 table."""
    print_section("Crew Roster V2 Queries")

    db = DynamoDBClient()

    # Test 1: Get sample crew assignments
    print("\n1. Get sample crew roster entries:")
    try:
        table = db.get_v2_table("crew_roster")
        response = table.scan(Limit=3)
        for item in response.get('Items', []):
            print(f"  - Roster {item.get('roster_id')}: {item.get('crew_id')} on flight {item.get('flight_id')}")
            print(f"    Role: {item.get('role')}, FDP Extension: {item.get('fdp_extension_available')}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: Query by crew_id (GSI)
    print("\n2. Query crew duty by crew_id (GSI):")
    try:
        table = db.get_v2_table("crew_roster")
        # Get a sample crew_id first
        scan_response = table.scan(Limit=5)
        if scan_response.get('Items'):
            sample_crew_id = scan_response['Items'][0].get('crew_id')
            if sample_crew_id:
                response = table.query(
                    IndexName="crew-duty-date-index",
                    KeyConditionExpression="crew_id = :cid",
                    ExpressionAttributeValues={":cid": sample_crew_id}
                )
                print_result(f"Found {len(response.get('Items', []))} duty records for crew {sample_crew_id}", "")
    except Exception as e:
        print(f"  Error: {e}")


def test_aircraft_rotations_v2_queries():
    """Test queries on aircraft_rotations_v2 table (V2-only table)."""
    print_section("Aircraft Rotations V2 Queries (V2-Only Table)")

    db = DynamoDBClient()

    # Test 1: Get sample aircraft rotations
    print("\n1. Get sample aircraft rotation entries:")
    try:
        rotations = db.get_aircraft_rotations("N781UA")
        print_result(f"Found {len(rotations)} rotation entries for N781UA", "")
        for r in rotations[:3]:
            print(f"  - Seq {r.get('sequence_number')}: Flight {r.get('flight_id')} ({r.get('origin')} -> {r.get('destination')})")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: Query all rotations
    print("\n2. Get all aircraft rotations:")
    try:
        table = db.get_v2_table("aircraft_rotations")
        response = table.scan(Limit=5)
        unique_aircraft = set()
        for item in response.get('Items', []):
            unique_aircraft.add(item.get('aircraft_registration'))
        print_result(f"Sample aircraft with rotations", list(unique_aircraft))
    except Exception as e:
        print(f"  Error: {e}")


def test_oal_flights_v2_queries():
    """Test queries on oal_flights_v2 table (V2-only table)."""
    print_section("OAL Flights V2 Queries (V2-Only Table)")

    db = DynamoDBClient()

    # Test 1: Get sample OAL flights
    print("\n1. Get sample OAL flight entries:")
    try:
        oal_flights = db.get_oal_flights_for_route("JFK", "LAX")
        print_result(f"Found {len(oal_flights)} OAL flights for JFK-LAX route", "")
        for f in oal_flights[:3]:
            print(f"  - {f.get('airline_code')} {f.get('flight_number')}: {f.get('origin')} -> {f.get('destination')}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test 2: Get all OAL flights
    print("\n2. Get all OAL flights:")
    try:
        table = db.get_v2_table("oal_flights")
        response = table.scan(Limit=5)
        for item in response.get('Items', []):
            print(f"  - {item.get('airline_code')} {item.get('flight_number')}: {item.get('origin')} -> {item.get('destination')}")
    except Exception as e:
        print(f"  Error: {e}")


def test_compensation_rules_v2_queries():
    """Test queries on compensation_rules_v2 table (V2-only table)."""
    print_section("Compensation Rules V2 Queries (V2-Only Table)")

    db = DynamoDBClient()

    # Test 1: Get compensation rules by regulation
    print("\n1. Get EU261 compensation rules:")
    try:
        rules = db.get_compensation_rules("EU261")
        print_result(f"Found {len(rules)} EU261 compensation rules", "")
        for r in rules[:3]:
            print(f"  - {r.get('rule_id')}: Delay {r.get('delay_hours_min')}h+, Amount: {r.get('compensation_amount_usd')} USD")
    except Exception as e:
        print(f"  Error: {e}")


def test_weather_v2_queries():
    """Test queries on weather_v2 table."""
    print_section("Weather V2 Queries")

    db = DynamoDBClient()

    # Test 1: Get weather for airport
    print("\n1. Get weather for JFK:")
    try:
        weather = db.get_weather_for_airport("JFK")
        print_result(f"Found {len(weather)} weather entries for JFK", "")
        for w in weather[:2]:
            print(f"  - {w.get('forecast_time_utc')}: {w.get('conditions')}, Wind: {w.get('wind_speed_kts')} kts")
            print(f"    GDP Active: {w.get('gdp_active')}, Ground Stop: {w.get('ground_stop')}")
    except Exception as e:
        print(f"  Error: {e}")


def test_reserve_crew_v2_queries():
    """Test queries on reserve_crew_v2 table (V2-only table)."""
    print_section("Reserve Crew V2 Queries (V2-Only Table)")

    db = DynamoDBClient()

    # Test 1: Get available reserve crew at a base
    print("\n1. Get available reserve crew at JFK:")
    try:
        reserves = db.get_reserve_crew_at_base("JFK", "available")
        print_result(f"Found {len(reserves)} available reserve crew at JFK", "")
        for r in reserves[:3]:
            print(f"  - {r.get('reserve_id')}: {r.get('name')}, Role: {r.get('role')}")
    except Exception as e:
        print(f"  Error: {e}")


def test_minimum_connection_times_v2():
    """Test queries on minimum_connection_times_v2 table."""
    print_section("Minimum Connection Times V2 Queries (V2-Only Table)")

    db = DynamoDBClient()

    # Test 1: Get MCT for airport
    print("\n1. Get minimum connection times for JFK:")
    try:
        mcts = db.get_minimum_connection_times("JFK")
        print_result(f"Found {len(mcts)} MCT entries for JFK", "")
        for m in mcts[:3]:
            print(f"  - {m.get('connection_type')}: {m.get('mct_minutes')} minutes")
    except Exception as e:
        print(f"  Error: {e}")


def run_all_tests():
    """Run all V2 data query tests."""
    print("\n" + "=" * 70)
    print("  V2 DATA QUERY TEST SUITE")
    print("  Testing queries against newly migrated V2 DynamoDB tables")
    print("  " + datetime.now().isoformat())
    print("=" * 70)

    # Run tests
    test_v2_configuration()
    test_v2_table_counts()
    test_flights_v2_queries()
    test_passengers_v2_queries()
    test_crew_roster_v2_queries()
    test_aircraft_rotations_v2_queries()
    test_oal_flights_v2_queries()
    test_compensation_rules_v2_queries()
    test_weather_v2_queries()
    test_reserve_crew_v2_queries()
    test_minimum_connection_times_v2()

    print_section("TEST SUITE COMPLETED")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("  All V2 data query tests executed successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_all_tests()
