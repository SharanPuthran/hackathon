#!/usr/bin/env python3
"""
Quick performance test for AgentCore dev mode.
Run this while agentcore dev is running.
"""

import asyncio
import json
import time
from datetime import datetime


async def test_agent_performance():
    """Test agent performance in dev mode."""
    
    print("="*80)
    print("SKYMARSHAL AGENT PERFORMANCE TEST")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Import AgentCore client
    try:
        from bedrock_agentcore import AgentCore
        client = AgentCore()
        print("✓ AgentCore client initialized\n")
    except Exception as e:
        print(f"✗ Failed to initialize AgentCore client: {e}")
        return
    
    # Test cases
    test_cases = [
        {
            "name": "Simple Weather Disruption",
            "payload": {
                "disruption_type": "weather",
                "affected_flight": "SK101",
                "departure_airport": "JFK",
                "arrival_airport": "LAX",
                "scheduled_departure": "2026-02-04T10:00:00Z",
                "description": "Severe weather at departure airport"
            }
        },
        {
            "name": "Complex Mechanical Issue",
            "payload": {
                "disruption_type": "mechanical",
                "affected_flight": "SK202",
                "departure_airport": "ORD",
                "arrival_airport": "SFO",
                "scheduled_departure": "2026-02-04T14:30:00Z",
                "description": "Aircraft mechanical issue requiring inspection",
                "passenger_count": 180,
                "cargo_weight_kg": 5000
            }
        },
        {
            "name": "Airport Closure",
            "payload": {
                "disruption_type": "airport_closure",
                "affected_airport": "DEN",
                "description": "Severe snowstorm affecting multiple flights",
                "estimated_closure_duration": "6 hours"
            }
        }
    ]
    
    results = []
    
    # Run tests
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}/{len(test_cases)}: {test_case['name']}")
        print("-" * 80)
        
        start_time = time.time()
        
        try:
            # Invoke agent
            response = await client.invoke_async({
                "prompt": json.dumps(test_case["payload"])
            })
            
            duration = time.time() - start_time
            
            # Analyze response
            response_str = str(response)
            response_length = len(response_str)
            
            # Check for key components
            has_safety = any(word in response_str.lower() for word in ["crew", "maintenance", "regulatory", "safety"])
            has_business = any(word in response_str.lower() for word in ["network", "guest", "cargo", "finance"])
            has_recommendations = "recommend" in response_str.lower()
            
            result = {
                "test": test_case["name"],
                "duration": duration,
                "success": True,
                "response_length": response_length,
                "has_safety_analysis": has_safety,
                "has_business_analysis": has_business,
                "has_recommendations": has_recommendations
            }
            
            results.append(result)
            
            print(f"  ✓ Success")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Response length: {response_length:,} chars")
            print(f"  Safety analysis: {'✓' if has_safety else '✗'}")
            print(f"  Business analysis: {'✓' if has_business else '✗'}")
            print(f"  Recommendations: {'✓' if has_recommendations else '✗'}")
            
        except Exception as e:
            duration = time.time() - start_time
            result = {
                "test": test_case["name"],
                "duration": duration,
                "success": False,
                "error": str(e)
            }
            results.append(result)
            
            print(f"  ✗ Failed: {e}")
            print(f"  Duration: {duration:.2f}s")
        
        print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\nTests Run: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")
    
    if successful:
        avg_duration = sum(r["duration"] for r in successful) / len(successful)
        min_duration = min(r["duration"] for r in successful)
        max_duration = max(r["duration"] for r in successful)
        
        print(f"\nTiming Statistics:")
        print(f"  Average: {avg_duration:.2f}s")
        print(f"  Min: {min_duration:.2f}s")
        print(f"  Max: {max_duration:.2f}s")
        
        # Quality metrics
        safety_count = sum(1 for r in successful if r.get("has_safety_analysis"))
        business_count = sum(1 for r in successful if r.get("has_business_analysis"))
        rec_count = sum(1 for r in successful if r.get("has_recommendations"))
        
        print(f"\nResponse Quality:")
        print(f"  Safety analysis: {safety_count}/{len(successful)}")
        print(f"  Business analysis: {business_count}/{len(successful)}")
        print(f"  Recommendations: {rec_count}/{len(successful)}")
    
    # Performance assessment
    print(f"\nPerformance Assessment:")
    if successful:
        if avg_duration < 20:
            print("  ✓ EXCELLENT - Average response time < 20s")
        elif avg_duration < 30:
            print("  ✓ GOOD - Average response time < 30s")
        elif avg_duration < 45:
            print("  ⚠ ACCEPTABLE - Average response time < 45s")
        else:
            print("  ✗ NEEDS IMPROVEMENT - Average response time > 45s")
    
    # Save results
    output_file = "dev_performance_results.json"
    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "total": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "avg_duration": avg_duration if successful else 0
            }
        }, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(test_agent_performance())
