#!/usr/bin/env python3
"""
Direct test of the orchestrator using the venv Python
"""

import asyncio
import json
import sys
from pathlib import Path

# Use the venv Python
venv_path = Path(__file__).parent / "skymarshal_agents" / ".venv" / "lib"
python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
site_packages = list(venv_path.glob(f"{python_version}/site-packages"))
if site_packages:
    sys.path.insert(0, str(site_packages[0]))

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "skymarshal_agents" / "src"))

print("=" * 80)
print("TESTING SKYMARSHAL ORCHESTRATOR (Direct)")
print("=" * 80)
print(f"Python: {sys.version}")
print(f"Path: {sys.path[:3]}")
print()

try:
    from main import invoke
    print("✅ Successfully imported main.invoke")
except ImportError as e:
    print(f"❌ Failed to import: {e}")
    sys.exit(1)


async def test_simple():
    """Test with a simple payload"""
    
    print("\n" + "=" * 80)
    print("TEST 1: Simple Crew Compliance Agent")
    print("=" * 80)
    
    payload = {
        "agent": "crew_compliance",
        "prompt": "Check crew compliance for flight 1",
        "disruption": {
            "flight_id": "1",
            "delay_hours": 3
        }
    }
    
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nInvoking agent...")
    
    try:
        result = await invoke(payload)
        print("\n✅ Agent invocation successful!")
        print(f"Result keys: {list(result.keys())}")
        print(f"\nResult preview:")
        print(json.dumps(result, indent=2, default=str)[:500])
        return True
    except Exception as e:
        print(f"\n❌ Agent invocation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_orchestrator():
    """Test full orchestrator"""
    
    print("\n" + "=" * 80)
    print("TEST 2: Full Orchestrator")
    print("=" * 80)
    
    # Load sample disruption
    with open("sample_disruption.json", "r") as f:
        disruption = json.load(f)
    
    payload = {
        "agent": "orchestrator",
        "prompt": f"Analyze disruption for flight {disruption['flight']['flight_number']}",
        "disruption": disruption
    }
    
    print(f"Flight: {disruption['flight']['flight_number']}")
    print(f"Delay: {disruption['issue_details']['estimated_delay_minutes']} minutes")
    print("\nInvoking orchestrator...")
    
    try:
        result = await invoke(payload)
        print("\n✅ Orchestrator invocation successful!")
        print(f"Result keys: {list(result.keys())}")
        
        if "workflow_status" in result:
            print(f"\nWorkflow Status: {result['workflow_status']}")
        
        if "safety_assessment" in result:
            safety = result["safety_assessment"]
            print(f"\nSafety Agents:")
            for agent in ["crew_compliance", "maintenance", "regulatory"]:
                if agent in safety:
                    status = safety[agent].get("status", "unknown")
                    print(f"  - {agent}: {status}")
        
        if "business_assessment" in result:
            business = result["business_assessment"]
            print(f"\nBusiness Agents:")
            for agent in ["network", "guest_experience", "cargo", "finance"]:
                if agent in business:
                    status = business[agent].get("status", "unknown")
                    print(f"  - {agent}: {status}")
        
        return True
    except Exception as e:
        print(f"\n❌ Orchestrator invocation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run tests"""
    
    # Test 1: Simple agent
    test1_passed = await test_simple()
    
    # Test 2: Full orchestrator
    test2_passed = await test_orchestrator()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Test 1 (Simple Agent): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Orchestrator): {'✅ PASSED' if test2_passed else '❌ FAILED'}")
    print("=" * 80)
    
    return test1_passed and test2_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
