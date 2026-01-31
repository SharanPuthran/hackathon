#!/usr/bin/env python3
"""
Simple test to invoke the orchestrator directly without AgentCore CLI
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "skymarshal_agents" / "src"))

from main import invoke


async def test_orchestrator():
    """Test orchestrator with sample disruption"""
    
    print("=" * 80)
    print("TESTING SKYMARSHAL ORCHESTRATOR")
    print("=" * 80)
    
    # Load sample disruption
    with open("sample_disruption.json", "r") as f:
        disruption = json.load(f)
    
    # Create payload
    payload = {
        "agent": "orchestrator",
        "prompt": f"""Analyze this flight disruption:

Flight: {disruption['flight']['flight_number']}
Route: {disruption['flight']['origin']['iata']} → {disruption['flight']['destination']['iata']}
Issue: {disruption['issue_details']['description']}
Delay: {disruption['issue_details']['estimated_delay_minutes']} minutes
Passengers: {disruption['impact']['passengers_affected']}

Provide comprehensive analysis from all agent perspectives.""",
        "disruption": disruption
    }
    
    print(f"\nDisruption Details:")
    print(f"  Flight: {disruption['flight']['flight_number']}")
    print(f"  Route: {disruption['flight']['origin']['iata']} → {disruption['flight']['destination']['iata']}")
    print(f"  Issue: {disruption['issue_details']['description']}")
    print(f"  Delay: {disruption['issue_details']['estimated_delay_minutes']} minutes")
    print(f"  Passengers: {disruption['impact']['passengers_affected']}")
    print()
    
    print("=" * 80)
    print("INVOKING ORCHESTRATOR...")
    print("=" * 80)
    print()
    
    try:
        # Invoke orchestrator
        result = await invoke(payload)
        
        print("=" * 80)
        print("ORCHESTRATOR RESULT")
        print("=" * 80)
        print()
        
        # Pretty print result
        print(json.dumps(result, indent=2, default=str))
        
        print()
        print("=" * 80)
        print("✅ ORCHESTRATOR TEST COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
        return result
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ ORCHESTRATOR TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_orchestrator())
    
    if result:
        sys.exit(0)
    else:
        sys.exit(1)
