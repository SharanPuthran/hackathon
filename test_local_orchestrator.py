#!/usr/bin/env python3
"""
Local test script for SkyMarshal Orchestrator (without AgentCore deployment)

This script tests the orchestrator logic locally by directly calling agent functions
and simulating the DynamoDB queries.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "skymarshal_agents" / "src"))


async def test_dynamodb_connection():
    """Test DynamoDB connection and basic queries"""
    print("=" * 80)
    print("STEP 1: Testing DynamoDB Connection")
    print("=" * 80)
    
    try:
        from database.dynamodb import DynamoDBClient
        
        db = DynamoDBClient()
        print("✅ DynamoDB client initialized")
        print(f"   Region: {db.client.meta.region_name}")
        
        # Test basic queries
        print("\nTesting basic queries:")
        
        # Test 1: Get a flight
        print("\n1. Query Flight (ID=1):")
        flight = db.get_flight("1")
        if flight:
            print(f"   ✅ Found flight: {flight.get('flight_number', 'N/A')}")
            print(f"      Route: {flight.get('origin_airport_id', 'N/A')} → {flight.get('destination_airport_id', 'N/A')}")
        else:
            print("   ⚠️  No flight data found")
        
        # Test 2: Get crew roster
        print("\n2. Query Crew Roster (Flight ID=1):")
        crew = db.query_crew_roster_by_flight("1")
        if crew:
            print(f"   ✅ Found {len(crew)} crew members")
            for member in crew[:3]:
                print(f"      - Crew {member.get('crew_id')}: Position {member.get('position_id')}")
        else:
            print("   ⚠️  No crew roster found")
        
        # Test 3: Get aircraft availability
        print("\n3. Query Aircraft Availability (A6-APX):")
        aircraft = db.get_aircraft_availability("A6-APX", "2026-01-30T00:00:00Z")
        if aircraft:
            print(f"   ✅ Found aircraft: {aircraft.get('aircraftRegistration')}")
            print(f"      Status: {aircraft.get('availability_status', 'N/A')}")
            mel_items = aircraft.get('mel_items_json', '[]')
            print(f"      MEL Items: {len(json.loads(mel_items)) if mel_items else 0}")
        else:
            print("   ⚠️  No aircraft data found")
        
        # Test 4: Get passenger bookings
        print("\n4. Query Bookings (Flight ID=1):")
        bookings = db.query_bookings_by_flight("1", "Confirmed")
        if bookings:
            print(f"   ✅ Found {len(bookings)} confirmed bookings")
        else:
            print("   ⚠️  No bookings found")
        
        # Test 5: Get cargo
        print("\n5. Query Cargo (Flight ID=1):")
        cargo = db.query_cargo_by_flight("1")
        if cargo:
            total_weight = sum(float(c.get('weight_on_flight_kg', 0)) for c in cargo)
            print(f"   ✅ Found {len(cargo)} cargo items")
            print(f"      Total weight: {total_weight:.2f} kg")
        else:
            print("   ⚠️  No cargo found")
        
        print("\n✅ Database connectivity test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Database connectivity test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_tools():
    """Test agent database tools"""
    print("\n" + "=" * 80)
    print("STEP 2: Testing Agent Database Tools")
    print("=" * 80)
    
    try:
        from database.tools import (
            get_crew_compliance_tools,
            get_maintenance_tools,
            get_regulatory_tools,
            get_network_tools,
            get_guest_experience_tools,
            get_cargo_tools,
            get_finance_tools
        )
        
        tool_sets = [
            ("Crew Compliance", get_crew_compliance_tools),
            ("Maintenance", get_maintenance_tools),
            ("Regulatory", get_regulatory_tools),
            ("Network", get_network_tools),
            ("Guest Experience", get_guest_experience_tools),
            ("Cargo", get_cargo_tools),
            ("Finance", get_finance_tools),
        ]
        
        for agent_name, tool_func in tool_sets:
            tools = tool_func()
            print(f"\n{agent_name} Agent:")
            print(f"   ✅ {len(tools)} tools available")
            for tool in tools:
                print(f"      - {tool.name}")
        
        # Test a specific tool
        print("\n" + "-" * 80)
        print("Testing Crew Compliance Tool:")
        crew_tools = get_crew_compliance_tools()
        query_roster = crew_tools[0]  # query_flight_crew_roster
        
        result = query_roster.invoke({"flight_id": "1"})
        result_data = json.loads(result)
        
        if "error" not in result_data:
            print(f"   ✅ Tool executed successfully")
            print(f"      Crew count: {result_data.get('crew_count', 0)}")
        else:
            print(f"   ⚠️  Tool returned error: {result_data.get('error')}")
        
        print("\n✅ Agent tools test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Agent tools test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_orchestrator_logic():
    """Test orchestrator logic without full agent execution"""
    print("\n" + "=" * 80)
    print("STEP 3: Testing Orchestrator Logic")
    print("=" * 80)
    
    try:
        # Load sample disruption
        with open("sample_disruption.json", "r") as f:
            disruption = json.load(f)
        
        print(f"\nDisruption Scenario:")
        print(f"   Flight: {disruption['flight']['flight_number']}")
        print(f"   Route: {disruption['flight']['origin']['iata']} → {disruption['flight']['destination']['iata']}")
        print(f"   Issue: {disruption['issue_details']['description']}")
        print(f"   Delay: {disruption['issue_details']['estimated_delay_minutes']} minutes")
        print(f"   Passengers: {disruption['impact']['passengers_affected']}")
        
        # Test response aggregation
        from utils.response import (
            aggregate_agent_responses,
            determine_status,
            extract_blocking_constraints
        )
        
        # Simulate safety agent results
        safety_results = [
            {
                "agent": "crew_compliance",
                "category": "safety",
                "status": "success",
                "result": "Crew FDP analysis: 8.5 hours remaining, within limits for 3-hour delay"
            },
            {
                "agent": "maintenance",
                "category": "safety",
                "status": "success",
                "result": "Aircraft A6-APX: Hydraulic system requires 2-hour maintenance window, MEL Category B deferral available"
            },
            {
                "agent": "regulatory",
                "category": "safety",
                "status": "success",
                "result": "LHR curfew at 23:00 UTC, delayed arrival at 21:30 UTC is within limits"
            }
        ]
        
        # Simulate business agent results
        business_results = [
            {
                "agent": "network",
                "category": "business",
                "status": "success",
                "result": "Network impact: 2 downstream flights affected, 87 connecting passengers at risk"
            },
            {
                "agent": "guest_experience",
                "category": "business",
                "status": "success",
                "result": "615 passengers affected, 12 VIP passengers require special handling"
            },
            {
                "agent": "cargo",
                "category": "business",
                "status": "success",
                "result": "15 cargo shipments affected, 2 time-sensitive (pharmaceuticals, perishables)"
            },
            {
                "agent": "finance",
                "category": "business",
                "status": "success",
                "result": "Estimated cost: $850K revenue at risk, $125K compensation liability"
            }
        ]
        
        print("\n" + "-" * 80)
        print("Aggregating Agent Results:")
        
        # Test status determination
        status = determine_status(safety_results)
        print(f"   Workflow Status: {status}")
        
        # Test constraint extraction
        constraints = extract_blocking_constraints(safety_results)
        print(f"   Blocking Constraints: {len(constraints)}")
        
        # Test aggregation
        aggregated = aggregate_agent_responses(safety_results, business_results)
        print(f"   ✅ Aggregation successful")
        print(f"      Safety agents: {len(safety_results)}")
        print(f"      Business agents: {len(business_results)}")
        print(f"      Recommendations: {len(aggregated.get('recommendations', []))}")
        
        print("\n✅ Orchestrator logic test PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ Orchestrator logic test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_orchestrator():
    """Test full orchestrator with actual agent execution"""
    print("\n" + "=" * 80)
    print("STEP 4: Testing Full Orchestrator Flow")
    print("=" * 80)
    print("\n⚠️  This requires the orchestrator to be deployed to AgentCore")
    print("   Use 'agentcore dev' to run locally, or 'agentcore deploy' for cloud deployment")
    print("\n   To test locally:")
    print("   1. cd skymarshal_agents")
    print("   2. agentcore dev")
    print("   3. In another terminal: agentcore invoke --dev 'Analyze disruption'")
    
    return True


async def main():
    """Main test runner"""
    print("\n" + "🚀" * 40)
    print("SKYMARSHAL LOCAL ORCHESTRATOR TEST")
    print("🚀" * 40)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    results = []
    
    # Test 1: Database connection
    db_ok = await test_dynamodb_connection()
    results.append(("Database Connection", db_ok))
    
    if not db_ok:
        print("\n⚠️  Skipping remaining tests due to database connection failure")
        print("   Please ensure:")
        print("   1. AWS credentials are configured")
        print("   2. DynamoDB tables exist in us-east-1")
        print("   3. Tables are populated with data")
        return
    
    # Test 2: Agent tools
    tools_ok = await test_agent_tools()
    results.append(("Agent Tools", tools_ok))
    
    # Test 3: Orchestrator logic
    logic_ok = await test_orchestrator_logic()
    results.append(("Orchestrator Logic", logic_ok))
    
    # Test 4: Full orchestrator (info only)
    await test_full_orchestrator()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests PASSED! The orchestrator is ready to use.")
        print("\nNext steps:")
        print("1. Deploy to AgentCore: cd skymarshal_agents && agentcore deploy")
        print("2. Test with real disruption: agentcore invoke 'Analyze flight disruption'")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
