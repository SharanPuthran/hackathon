#!/usr/bin/env python3
"""
Quick script to check DynamoDB data availability for orchestrator testing
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "skymarshal_agents" / "src"))

from database.dynamodb import DynamoDBClient
import json


def check_table_data():
    """Check data availability in all DynamoDB tables"""
    
    print("=" * 80)
    print("DYNAMODB DATA AVAILABILITY CHECK")
    print("=" * 80)
    
    db = DynamoDBClient()
    
    checks = [
        ("Flights", lambda: db.get_flight("1"), "Flight 1"),
        ("Flights (scan)", lambda: db.query_flights(), "All flights"),
        ("Crew Members", lambda: db.get_crew_member("1"), "Crew member 1"),
        ("Crew Roster", lambda: db.query_crew_roster_by_flight("1"), "Flight 1 crew"),
        ("Aircraft Availability", lambda: db.get_aircraft_availability("A6-APX", "2026-01-30T00:00:00Z"), "A6-APX availability"),
        ("Maintenance Workorders", lambda: db.query_maintenance_workorders("A6-APX"), "A6-APX workorders"),
        ("Weather", lambda: db.get_weather("AUH", "2026-01-30T12:00:00Z"), "AUH weather"),
        ("Passengers", lambda: db.get_passenger("1"), "Passenger 1"),
        ("Bookings (by flight)", lambda: db.query_bookings_by_flight("1"), "Flight 1 bookings"),
        ("Bookings (by passenger)", lambda: db.query_bookings_by_passenger("1"), "Passenger 1 bookings"),
        ("Baggage", lambda: db.query_baggage_by_booking("1"), "Booking 1 baggage"),
        ("Cargo Shipments", lambda: db.get_cargo_shipment("1"), "Shipment 1"),
        ("Cargo by Flight", lambda: db.query_cargo_by_flight("1"), "Flight 1 cargo"),
        ("Inbound Flight Impact", lambda: db.get_inbound_flight_impact("DISR-001"), "Scenario DISR-001"),
    ]
    
    results = []
    
    for table_name, check_func, description in checks:
        try:
            result = check_func()
            
            if result:
                if isinstance(result, list):
                    count = len(result)
                    status = f"✅ {count} records"
                    results.append((table_name, True, count, None))
                else:
                    status = "✅ Found"
                    results.append((table_name, True, 1, None))
            else:
                status = "⚠️  Empty"
                results.append((table_name, False, 0, "No data"))
            
            print(f"{status:20} {table_name:30} ({description})")
            
        except Exception as e:
            status = "❌ Error"
            error_msg = str(e)[:50]
            results.append((table_name, False, 0, error_msg))
            print(f"{status:20} {table_name:30} ({error_msg})")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    success_count = sum(1 for _, success, _, _ in results if success)
    total_count = len(results)
    
    print(f"Tables with data: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("\n✅ All tables have data! Ready for orchestrator testing.")
    elif success_count > total_count / 2:
        print("\n⚠️  Some tables are empty. Orchestrator may have limited functionality.")
        print("\nMissing data in:")
        for table, success, _, error in results:
            if not success:
                print(f"   - {table}: {error or 'No data'}")
    else:
        print("\n❌ Most tables are empty. Please populate DynamoDB before testing.")
        print("\nTo populate data:")
        print("   cd database")
        print("   python generators/create_disruption_scenario_v2.py")
        print("   python import_csv_to_dynamodb.py")
    
    # Detailed sample data
    print("\n" + "=" * 80)
    print("SAMPLE DATA")
    print("=" * 80)
    
    # Show sample flight
    flight = db.get_flight("1")
    if flight:
        print("\nFlight 1:")
        print(f"   Flight Number: {flight.get('flight_number', 'N/A')}")
        print(f"   Route: {flight.get('origin_airport_id', 'N/A')} → {flight.get('destination_airport_id', 'N/A')}")
        print(f"   Aircraft: {flight.get('aircraft_registration', 'N/A')}")
        print(f"   Departure: {flight.get('scheduled_departure_zulu', 'N/A')}")
    
    # Show sample crew
    crew = db.query_crew_roster_by_flight("1")
    if crew:
        print(f"\nFlight 1 Crew ({len(crew)} members):")
        for member in crew[:3]:
            print(f"   - Crew {member.get('crew_id')}: Position {member.get('position_id')}")
    
    # Show sample bookings
    bookings = db.query_bookings_by_flight("1", "Confirmed")
    if bookings:
        print(f"\nFlight 1 Bookings ({len(bookings)} confirmed):")
        for booking in bookings[:3]:
            print(f"   - Booking {booking.get('booking_id')}: Passenger {booking.get('passenger_id')}, Class {booking.get('booking_class')}")
    
    # Show sample cargo
    cargo = db.query_cargo_by_flight("1")
    if cargo:
        total_weight = sum(float(c.get('weight_on_flight_kg', 0)) for c in cargo)
        print(f"\nFlight 1 Cargo ({len(cargo)} items, {total_weight:.2f} kg total):")
        for item in cargo[:3]:
            print(f"   - Shipment {item.get('shipment_id')}: {item.get('weight_on_flight_kg')} kg, Status: {item.get('loading_status')}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        check_table_data()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
