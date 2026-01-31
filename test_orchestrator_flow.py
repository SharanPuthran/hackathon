#!/usr/bin/env python3
"""
Test script for SkyMarshal Orchestrator Flow with DynamoDB Integration

This script tests the complete orchestrator flow:
1. Sends a disruption scenario to the orchestrator
2. Orchestrator invokes all 7 agents (safety + business)
3. Each agent queries relevant data from DynamoDB
4. Aggregates results and provides recommendations
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "skymarshal_agents" / "src"))

from main import invoke
from database.dynamodb import DynamoDBClient


def load_sample_disruption():
    """Load sample disruption scenario"""
    with open("sample_disruption.json", "r") as f:
        return json.load(f)


def create_test_payload(disruption_data: dict, agent: str = "orchestrator") -> dict:
    """
    Create test payload for orchestrator invocation.
    
    Args:
        disruption_data: Disruption scenario data
        agent: Target agent ("orchestrator" for all agents, or specific agent name)
    
    Returns:
        dict: Formatted payload for agent invocation
    """
    return {
        "agent": agent,
        "prompt": f"""Analyze this flight disruption and provide comprehensive assessment:

Flight: {disruption_data['flight']['flight_number']}
Route: {disruption_data['flight']['origin']['iata']} → {disruption_data['flight']['destination']['iata']}
Issue: {disruption_data['issue_details']['description']}
Estimated Delay: {disruption_data['issue_details']['estimated_delay_minutes']} minutes
Passengers Affected: {disruption_data['impact']['passengers_affected']}

Provide detailed analysis from your domain perspective.""",
        "disruption": disruption_data
    }


async def test_database_connectivity():
    """Test DynamoDB connectivity before running orchestrator"""
    print("=" * 80)
    print("TESTING DATABASE CONNECTIVITY")
    print("=" * 80)
    
    db = DynamoDBClient()
    
    # Test queries for each agent domain
    tests = [
        ("Flights", lambda: db.get_flight("1")),
        ("Crew Members", lambda: db.get_crew_member("1")),
        ("Aircraft Availability", lambda: db.get_aircraft_availability("A6-APX", "2026-01-30T00:00:00Z")),
        ("Passengers", lambda: db.get_passenger("1")),
        ("Bookings by Flight", lambda: db.query_bookings_by_flight("1")),
        ("Cargo by Flight", lambda: db.query_cargo_by_flight("1")),
        ("Weather", lambda: db.get_weather("AUH", "2026-01-30T12:00:00Z")),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            status = "✅ SUCCESS" if result else "⚠️  NO DATA"
            results.append((test_name, status, result))
            print(f"{status}: {test_name}")
        except Exception as e:
            status = "❌ FAILED"
            results.append((test_name, status, str(e)))
            print(f"{status}: {test_name} - {e}")
    
    print()
    return all(status != "❌ FAILED" for _, status, _ in results)


async def test_individual_agent(agent_name: str, payload: dict):
    """Test individual agent invocation"""
    print(f"\n{'=' * 80}")
    print(f"TESTING AGENT: {agent_name.upper()}")
    print(f"{'=' * 80}")
    
    agent_payload = payload.copy()
    agent_payload["agent"] = agent_name
    
    try:
        start_time = datetime.now()
        result = await invoke(agent_payload)
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"✅ Agent completed in {duration:.2f}s")
        print(f"\nResult Preview:")
        print("-" * 80)
        
        # Pretty print result
        if isinstance(result, dict):
            print(json.dumps(result, indent=2, default=str)[:1000])
            if len(json.dumps(result, default=str)) > 1000:
                print("\n... (truncated)")
        else:
            print(str(result)[:1000])
        
        return {
            "agent": agent_name,
            "status": "success",
            "duration_seconds": duration,
            "result": result
        }
        
    except Exception as e:
        print(f"❌ Agent failed: {e}")
        return {
            "agent": agent_name,
            "status": "error",
            "error": str(e)
        }


async def test_orchestrator_flow(payload: dict):
    """Test complete orchestrator flow with all agents"""
    print("\n" + "=" * 80)
    print("TESTING COMPLETE ORCHESTRATOR FLOW")
    print("=" * 80)
    print(f"Disruption: {payload['disruption']['flight']['flight_number']}")
    print(f"Issue: {payload['disruption']['issue_details']['description']}")
    print(f"Delay: {payload['disruption']['issue_details']['estimated_delay_minutes']} minutes")
    print("=" * 80)
    
    try:
        start_time = datetime.now()
        result = await invoke(payload)
        duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\n✅ ORCHESTRATOR COMPLETED in {duration:.2f}s")
        print("\n" + "=" * 80)
        print("ORCHESTRATOR RESULTS")
        print("=" * 80)
        
        # Pretty print aggregated results
        print(json.dumps(result, indent=2, default=str))
        
        return {
            "status": "success",
            "duration_seconds": duration,
            "result": result
        }
        
    except Exception as e:
        print(f"\n❌ ORCHESTRATOR FAILED: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "error": str(e)
        }


async def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("\n" + "🚀" * 40)
    print("SKYMARSHAL ORCHESTRATOR TEST SUITE")
    print("🚀" * 40)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Step 1: Test database connectivity
    db_ok = await test_database_connectivity()
    if not db_ok:
        print("\n⚠️  WARNING: Some database connectivity issues detected")
        print("Continuing with orchestrator test...\n")
    
    # Step 2: Load disruption scenario
    disruption = load_sample_disruption()
    payload = create_test_payload(disruption, agent="orchestrator")
    
    # Step 3: Test orchestrator flow
    orchestrator_result = await test_orchestrator_flow(payload)
    
    # Step 4: Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if orchestrator_result["status"] == "success":
        print("✅ Orchestrator test PASSED")
        print(f"⏱️  Total duration: {orchestrator_result['duration_seconds']:.2f}s")
        
        # Extract key metrics
        result = orchestrator_result.get("result", {})
        if isinstance(result, dict):
            workflow_status = result.get("workflow_status", "UNKNOWN")
            print(f"📊 Workflow Status: {workflow_status}")
            
            safety = result.get("safety_assessment", {})
            business = result.get("business_assessment", {})
            
            print(f"\n🔒 Safety Agents:")
            for agent in ["crew_compliance", "maintenance", "regulatory"]:
                agent_result = safety.get(agent, {})
                status = agent_result.get("status", "unknown")
                print(f"   - {agent}: {status}")
            
            print(f"\n💼 Business Agents:")
            for agent in ["network", "guest_experience", "cargo", "finance"]:
                agent_result = business.get(agent, {})
                status = agent_result.get("status", "unknown")
                print(f"   - {agent}: {status}")
            
            blocking = safety.get("blocking_constraints", [])
            if blocking:
                print(f"\n⚠️  Blocking Constraints: {len(blocking)}")
                for constraint in blocking:
                    print(f"   - {constraint.get('agent')}: {constraint.get('severity')}")
            else:
                print(f"\n✅ No blocking constraints detected")
            
            recommendations = result.get("recommendations", [])
            if recommendations:
                print(f"\n📋 Recommendations ({len(recommendations)}):")
                for i, rec in enumerate(recommendations[:5], 1):
                    print(f"   {i}. {rec}")
    else:
        print("❌ Orchestrator test FAILED")
        print(f"Error: {orchestrator_result.get('error')}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    return orchestrator_result


async def test_specific_agent_mode():
    """Test individual agents one by one"""
    print("\n" + "🔍" * 40)
    print("INDIVIDUAL AGENT TEST MODE")
    print("🔍" * 40)
    
    disruption = load_sample_disruption()
    payload = create_test_payload(disruption)
    
    agents = [
        "crew_compliance",
        "maintenance", 
        "regulatory",
        "network",
        "guest_experience",
        "cargo",
        "finance"
    ]
    
    results = []
    for agent in agents:
        result = await test_individual_agent(agent, payload)
        results.append(result)
        await asyncio.sleep(1)  # Brief pause between agents
    
    # Summary
    print("\n" + "=" * 80)
    print("INDIVIDUAL AGENT TEST SUMMARY")
    print("=" * 80)
    
    for result in results:
        status_icon = "✅" if result["status"] == "success" else "❌"
        duration = result.get("duration_seconds", 0)
        print(f"{status_icon} {result['agent']}: {result['status']} ({duration:.2f}s)")
    
    success_count = sum(1 for r in results if r["status"] == "success")
    print(f"\nTotal: {success_count}/{len(results)} agents succeeded")
    
    return results


async def main():
    """Main test entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SkyMarshal Orchestrator")
    parser.add_argument(
        "--mode",
        choices=["orchestrator", "individual", "both"],
        default="orchestrator",
        help="Test mode: orchestrator (all agents), individual (one by one), or both"
    )
    parser.add_argument(
        "--agent",
        help="Test specific agent only (e.g., crew_compliance)"
    )
    
    args = parser.parse_args()
    
    if args.agent:
        # Test specific agent
        disruption = load_sample_disruption()
        payload = create_test_payload(disruption)
        await test_individual_agent(args.agent, payload)
    elif args.mode == "orchestrator":
        # Test orchestrator flow
        await run_comprehensive_test()
    elif args.mode == "individual":
        # Test individual agents
        await test_specific_agent_mode()
    elif args.mode == "both":
        # Test both modes
        await run_comprehensive_test()
        await test_specific_agent_mode()


if __name__ == "__main__":
    asyncio.run(main())
