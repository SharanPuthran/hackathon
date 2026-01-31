#!/usr/bin/env python3
"""Test orchestrator using agentcore invoke command"""

import json
import subprocess
import sys
from pathlib import Path

def test_orchestrator():
    """Test the orchestrator with sample disruption"""
    
    # Load sample disruption
    with open("sample_disruption.json", "r") as f:
        disruption = json.load(f)
    
    # Create test payload
    payload = {
        "agent": "orchestrator",
        "prompt": "Analyze this flight disruption and provide recommendations",
        "disruption": disruption
    }
    
    # Convert payload to JSON string
    payload_json = json.dumps(payload)
    
    print("=" * 80)
    print("🧪 Testing SkyMarshal Orchestrator")
    print("=" * 80)
    print(f"   Agent: {payload['agent']}")
    print(f"   Flight: {disruption['flight']['flight_number']}")
    print(f"   Issue: {disruption['issue_details']['description']}")
    print()
    
    # Invoke using agentcore
    print("🚀 Invoking orchestrator...")
    print()
    
    try:
        result = subprocess.run(
            ["uv", "run", "agentcore", "invoke", "--dev", "--port", "8082", payload_json],
            cwd="skymarshal_agents",
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        print("=" * 80)
        print("📤 STDOUT:")
        print("=" * 80)
        print(result.stdout)
        
        if result.stderr:
            print()
            print("=" * 80)
            print("⚠️  STDERR:")
            print("=" * 80)
            print(result.stderr)
        
        print()
        print("=" * 80)
        print(f"✅ Exit Code: {result.returncode}")
        print("=" * 80)
        
        # Try to parse JSON response
        try:
            response = json.loads(result.stdout)
            print()
            print("📊 Parsed Response:")
            print(json.dumps(response, indent=2))
        except json.JSONDecodeError:
            print()
            print("⚠️  Could not parse response as JSON")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print()
        print("=" * 80)
        print("⏱  TIMEOUT: Orchestrator took longer than 5 minutes")
        print("=" * 80)
        return False
    
    except Exception as e:
        print()
        print("=" * 80)
        print(f"❌ ERROR: {e}")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = test_orchestrator()
    sys.exit(0 if success else 1)
