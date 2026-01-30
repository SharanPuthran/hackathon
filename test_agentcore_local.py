"""
Test SkyMarshal Arbitrator Agent Locally (AgentCore Runtime)

This script tests the AgentCore-wrapped arbitrator agent running locally
before deploying to AWS.

Usage:
    # Terminal 1: Start the local AgentCore server
    python3 agentcore_arbitrator.py

    # Terminal 2: Run this test
    python3 test_agentcore_local.py
"""

import requests
import json
from datetime import datetime


def test_healthcheck():
    """Test the healthcheck endpoint"""
    print("\n" + "=" * 60)
    print("Testing AgentCore Healthcheck")
    print("=" * 60)

    try:
        response = requests.get("http://localhost:8080/healthcheck")
        response.raise_for_status()

        health = response.json()
        print(f"✅ Status: {health.get('status')}")
        print(f"   Agent: {health.get('agent')}")
        print(f"   Model: {health.get('model')}")
        print(f"   Framework: {health.get('framework')}")
        print(f"   Runtime: {health.get('runtime')}")
        return True

    except Exception as e:
        print(f"❌ Healthcheck failed: {e}")
        return False


def test_simple_prompt():
    """Test with a simple prompt"""
    print("\n" + "=" * 60)
    print("Testing Simple Prompt")
    print("=" * 60)

    payload = {
        "prompt": "Hello, AgentCore!"
    }

    try:
        response = requests.post(
            "http://localhost:8080/invoke",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        result = response.json()
        print(f"✅ Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Capabilities: {len(result.get('capabilities', []))} listed")
        return True

    except Exception as e:
        print(f"❌ Simple prompt test failed: {e}")
        return False


def test_full_arbitrator():
    """Test with full disruption scenario"""
    print("\n" + "=" * 60)
    print("Testing Full Arbitrator Agent")
    print("=" * 60)

    payload = {
        "disruption_scenario": {
            "flight_number": "EY123",
            "route": "AUH → LHR",
            "issue": "Hydraulic system fault detected",
            "delay_hours": 3,
            "passengers": 615,
            "connections_at_risk": 87,
            "cargo_critical": True
        },
        "safety_assessments": {
            "crew_compliance": {
                "status": "APPROVED",
                "ftl_remaining": "3.5 hours",
                "crew_fit": True
            },
            "maintenance": {
                "status": "MEL_CATEGORY_B",
                "deferrable": True,
                "repair_time_estimate": "4 hours"
            },
            "regulatory": {
                "status": "CURFEW_RISK",
                "latest_departure": "20:00",
                "requires_slot": True
            }
        },
        "business_proposals": {
            "network": {
                "priority": "HIGH",
                "downstream_impact": "$450K",
                "alternative_routes": 2
            },
            "guest_experience": {
                "compensation": "€125K",
                "satisfaction_risk": "MEDIUM",
                "rebooking_options": 5
            },
            "cargo": {
                "critical_shipments": 3,
                "offload_recommended": False,
                "delay_penalties": "$85K"
            },
            "finance": {
                "cancel_cost": "€1.2M",
                "delay_cost": "€210K",
                "preferred_action": "delay"
            }
        }
    }

    print("\n📊 Test Scenario:")
    print(f"   Flight: {payload['disruption_scenario']['flight_number']}")
    print(f"   Route: {payload['disruption_scenario']['route']}")
    print(f"   Issue: {payload['disruption_scenario']['issue']}")
    print(f"   Passengers: {payload['disruption_scenario']['passengers']}")

    print("\n🤖 Invoking AgentCore Arbitrator...")

    try:
        response = requests.post(
            "http://localhost:8080/invoke",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120  # 2 minute timeout for complex decision
        )
        response.raise_for_status()

        result = response.json()

        if result.get("status") == "success":
            print("\n✅ Decision Made Successfully!")
            print("\n" + "-" * 60)

            decision = result.get("decision", {})
            print(f"📋 Selected Scenario: {decision.get('scenario_id')}")
            print(f"   Name: {decision.get('scenario_name')}")
            print(f"   Score: {decision.get('overall_score')}/100")
            print(f"   Action: {decision.get('recommended_action')}")

            print(f"\n🎯 Confidence: {result.get('confidence_score')}%")

            print("\n💡 Rationale:")
            rationale = result.get("rationale", "")
            # Print first 500 characters of rationale
            if len(rationale) > 500:
                print(f"   {rationale[:500]}...")
            else:
                print(f"   {rationale}")

            scenarios = result.get("scenarios_evaluated", [])
            if scenarios:
                print(f"\n📊 Scenarios Evaluated: {len(scenarios)}")
                for i, scenario in enumerate(scenarios[:3], 1):  # Top 3
                    print(f"   {i}. {scenario.get('id')}: {scenario.get('name')} (Score: {scenario.get('score')})")

            print("\n" + "-" * 60)
            return True
        else:
            print(f"❌ Error: {result.get('error_message')}")
            return False

    except requests.Timeout:
        print("❌ Request timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Full arbitrator test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("SkyMarshal Arbitrator Agent - AgentCore Local Testing")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Target: http://localhost:8080")

    # Check if server is running
    try:
        requests.get("http://localhost:8080/healthcheck", timeout=2)
    except:
        print("\n❌ ERROR: AgentCore server is not running!")
        print("\nPlease start the server first:")
        print("  python3 agentcore_arbitrator.py")
        print("\nThen run this test again.")
        return

    # Run tests
    results = {
        "healthcheck": test_healthcheck(),
        "simple_prompt": test_simple_prompt(),
        "full_arbitrator": test_full_arbitrator()
    }

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    total = len(results)
    passed = sum(results.values())

    print("\n" + "-" * 80)
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! Ready to deploy to AgentCore Runtime.")
        print("\nNext steps:")
        print("  1. agentcore configure -e agentcore_arbitrator.py")
        print("  2. agentcore deploy")
        print("  3. python3 test_agentcore_deployment.py")
    else:
        print("\n⚠️ Some tests failed. Please fix issues before deploying.")

    print("=" * 80)


if __name__ == "__main__":
    main()
