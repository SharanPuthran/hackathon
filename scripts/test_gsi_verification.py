#!/usr/bin/env python3
"""
Test script for GSI verification functionality (Task 3.4)

This script tests the comprehensive GSI validation added to validate_dynamodb_data.py
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, "skymarshal_agents_new/skymarshal/src")

from validate_dynamodb_data import DynamoDBValidator
from database.constants import (
    FLIGHTS_TABLE,
    BOOKINGS_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    CREW_ROSTER_TABLE,
    CARGO_FLIGHT_ASSIGNMENTS_TABLE,
    BAGGAGE_TABLE,
    DEFAULT_AWS_REGION
)


def test_gsi_validation():
    """Test the comprehensive GSI validation functionality"""
    print("=" * 60)
    print("Testing GSI Verification (Task 3.4)")
    print("=" * 60)
    
    # Create validator
    validator = DynamoDBValidator(region=DEFAULT_AWS_REGION)
    
    # Test individual GSI validation methods
    print("\n1. Testing individual GSI validation methods...")
    
    # Test Flights table GSIs
    print(f"\n  Testing {FLIGHTS_TABLE} GSIs...")
    gsi1_exists = validator.validate_gsi_exists(FLIGHTS_TABLE, "flight-number-date-index")
    gsi2_exists = validator.validate_gsi_exists(FLIGHTS_TABLE, "aircraft-registration-index")
    
    if gsi1_exists:
        print(f"    ✅ flight-number-date-index exists and is ACTIVE")
        validator.validate_gsi_key_schema(
            FLIGHTS_TABLE,
            "flight-number-date-index",
            {"HASH": "flight_number", "RANGE": "scheduled_departure"}
        )
    else:
        print(f"    ❌ flight-number-date-index missing or not ACTIVE")
    
    if gsi2_exists:
        print(f"    ✅ aircraft-registration-index exists and is ACTIVE")
        validator.validate_gsi_key_schema(
            FLIGHTS_TABLE,
            "aircraft-registration-index",
            {"HASH": "aircraft_registration"}
        )
    else:
        print(f"    ❌ aircraft-registration-index missing or not ACTIVE")
    
    # Test Bookings table GSI
    print(f"\n  Testing {BOOKINGS_TABLE} GSI...")
    gsi_exists = validator.validate_gsi_exists(BOOKINGS_TABLE, "flight-id-index")
    if gsi_exists:
        print(f"    ✅ flight-id-index exists and is ACTIVE")
        validator.validate_gsi_key_schema(
            BOOKINGS_TABLE,
            "flight-id-index",
            {"HASH": "flight_id"}
        )
    else:
        print(f"    ❌ flight-id-index missing or not ACTIVE")
    
    # Test MaintenanceWorkOrders table GSI
    print(f"\n  Testing {MAINTENANCE_WORK_ORDERS_TABLE} GSI...")
    gsi_exists = validator.validate_gsi_exists(MAINTENANCE_WORK_ORDERS_TABLE, "aircraft-registration-index")
    if gsi_exists:
        print(f"    ✅ aircraft-registration-index exists and is ACTIVE")
        validator.validate_gsi_key_schema(
            MAINTENANCE_WORK_ORDERS_TABLE,
            "aircraft-registration-index",
            {"HASH": "aircraftRegistration"}
        )
    else:
        print(f"    ❌ aircraft-registration-index missing or not ACTIVE")
    
    # Test CrewRoster table GSI
    print(f"\n  Testing {CREW_ROSTER_TABLE} GSI...")
    gsi_exists = validator.validate_gsi_exists(CREW_ROSTER_TABLE, "flight-position-index")
    if gsi_exists:
        print(f"    ✅ flight-position-index exists and is ACTIVE")
        validator.validate_gsi_key_schema(
            CREW_ROSTER_TABLE,
            "flight-position-index",
            {"HASH": "flight_id", "RANGE": "position"}
        )
    else:
        print(f"    ❌ flight-position-index missing or not ACTIVE")
    
    # Test CargoFlightAssignments table GSI
    print(f"\n  Testing {CARGO_FLIGHT_ASSIGNMENTS_TABLE} GSI...")
    gsi_exists = validator.validate_gsi_exists(CARGO_FLIGHT_ASSIGNMENTS_TABLE, "flight-loading-index")
    if gsi_exists:
        print(f"    ✅ flight-loading-index exists and is ACTIVE")
        validator.validate_gsi_key_schema(
            CARGO_FLIGHT_ASSIGNMENTS_TABLE,
            "flight-loading-index",
            {"HASH": "flight_id", "RANGE": "loading_priority"}
        )
    else:
        print(f"    ❌ flight-loading-index missing or not ACTIVE")
    
    # Test Baggage table GSI
    print(f"\n  Testing {BAGGAGE_TABLE} GSI...")
    gsi_exists = validator.validate_gsi_exists(BAGGAGE_TABLE, "booking-index")
    if gsi_exists:
        print(f"    ✅ booking-index exists and is ACTIVE")
        validator.validate_gsi_key_schema(
            BAGGAGE_TABLE,
            "booking-index",
            {"HASH": "booking_id"}
        )
    else:
        print(f"    ❌ booking-index missing or not ACTIVE")
    
    # Test comprehensive GSI validation
    print("\n2. Testing comprehensive GSI validation...")
    gsi_results = validator.validate_all_gsis()
    
    print(f"\n{'=' * 60}")
    print("GSI Validation Test Results")
    print(f"{'=' * 60}")
    print(f"Total GSIs Required: {gsi_results['total_gsis']}")
    print(f"Successfully Validated: {gsi_results['validated']}")
    print(f"Missing or Inactive: {gsi_results['missing']}")
    print(f"Schema Mismatches: {gsi_results['schema_mismatch']}")
    print(f"Query Tests Passed: {gsi_results['query_test_passed']}")
    print(f"Query Tests Failed: {gsi_results['query_test_failed']}")
    
    # Check for issues
    print(f"\n3. Checking validation issues...")
    gsi_issues = [issue for issue in validator.issues if "gsi" in issue.issue_type.lower()]
    
    if gsi_issues:
        print(f"\n  Found {len(gsi_issues)} GSI-related issues:")
        for issue in gsi_issues:
            severity_icon = "❌" if issue.severity == "error" else "⚠️" if issue.severity == "warning" else "ℹ️"
            print(f"    {severity_icon} [{issue.table}] {issue.description}")
            if issue.fix_suggestion:
                print(f"       Fix: {issue.fix_suggestion}")
    else:
        print("  ✅ No GSI-related issues found")
    
    # Summary
    print(f"\n{'=' * 60}")
    print("Test Summary")
    print(f"{'=' * 60}")
    
    if gsi_results['validated'] == gsi_results['total_gsis'] and gsi_results['missing'] == 0:
        print("✅ All GSI validation tests PASSED")
        print("   - All required GSIs exist and are ACTIVE")
        print("   - All GSI key schemas match requirements")
        print("   - Sample queries use GSIs (no table scans)")
        return True
    else:
        print("❌ GSI validation tests FAILED")
        print(f"   - {gsi_results['missing']} GSIs missing or not ACTIVE")
        print(f"   - {gsi_results['schema_mismatch']} GSI schema mismatches")
        print(f"   - {gsi_results['query_test_failed']} query tests failed")
        print("\n   Run scripts/create_gsis.py to create missing GSIs")
        return False


if __name__ == "__main__":
    try:
        success = test_gsi_validation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
