"""
Performance testing for SkyMarshal agents in AgentCore dev mode.

Tests agent response times, throughput, and optimization effectiveness.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any
import statistics

import pytest
from bedrock_agentcore import AgentCore


class PerformanceMetrics:
    """Track and analyze performance metrics."""
    
    def __init__(self):
        self.metrics: List[Dict[str, Any]] = []
    
    def record(self, test_name: str, duration: float, success: bool, details: Dict = None):
        """Record a performance measurement."""
        self.metrics.append({
            "test_name": test_name,
            "duration": duration,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """Generate performance summary statistics."""
        if not self.metrics:
            return {}
        
        durations = [m["duration"] for m in self.metrics if m["success"]]
        success_count = sum(1 for m in self.metrics if m["success"])
        
        return {
            "total_tests": len(self.metrics),
            "successful": success_count,
            "failed": len(self.metrics) - success_count,
            "success_rate": success_count / len(self.metrics) * 100,
            "avg_duration": statistics.mean(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "median_duration": statistics.median(durations) if durations else 0,
            "stdev_duration": statistics.stdev(durations) if len(durations) > 1 else 0
        }
    
    def print_report(self):
        """Print formatted performance report."""
        summary = self.get_summary()
        
        print("\n" + "="*80)
        print("PERFORMANCE TEST REPORT")
        print("="*80)
        print(f"\nTest Execution Summary:")
        print(f"  Total Tests: {summary.get('total_tests', 0)}")
        print(f"  Successful: {summary.get('successful', 0)}")
        print(f"  Failed: {summary.get('failed', 0)}")
        print(f"  Success Rate: {summary.get('success_rate', 0):.2f}%")
        
        print(f"\nTiming Statistics (seconds):")
        print(f"  Average: {summary.get('avg_duration', 0):.3f}s")
        print(f"  Median: {summary.get('median_duration', 0):.3f}s")
        print(f"  Min: {summary.get('min_duration', 0):.3f}s")
        print(f"  Max: {summary.get('max_duration', 0):.3f}s")
        print(f"  Std Dev: {summary.get('stdev_duration', 0):.3f}s")
        
        print(f"\nDetailed Results:")
        for metric in self.metrics:
            status = "✓" if metric["success"] else "✗"
            print(f"  {status} {metric['test_name']}: {metric['duration']:.3f}s")
        
        print("="*80 + "\n")


@pytest.fixture
def metrics():
    """Provide performance metrics tracker."""
    return PerformanceMetrics()


@pytest.fixture
def agent_client():
    """Create AgentCore client for dev mode testing."""
    return AgentCore()


# Test payloads
SIMPLE_DISRUPTION = {
    "prompt": json.dumps({
        "disruption_type": "weather",
        "affected_flight": "SK101",
        "departure_airport": "JFK",
        "arrival_airport": "LAX",
        "scheduled_departure": "2026-02-04T10:00:00Z",
        "description": "Severe weather at departure airport causing delays"
    })
}

COMPLEX_DISRUPTION = {
    "prompt": json.dumps({
        "disruption_type": "mechanical",
        "affected_flight": "SK202",
        "departure_airport": "ORD",
        "arrival_airport": "SFO",
        "scheduled_departure": "2026-02-04T14:30:00Z",
        "description": "Aircraft mechanical issue requiring maintenance inspection and potential aircraft swap",
        "passenger_count": 180,
        "cargo_weight_kg": 5000,
        "connecting_flights": ["SK303", "SK304", "SK305"]
    })
}

MULTI_FLIGHT_DISRUPTION = {
    "prompt": json.dumps({
        "disruption_type": "airport_closure",
        "affected_airport": "DEN",
        "description": "Airport closure due to severe snowstorm affecting multiple flights",
        "affected_flights": ["SK401", "SK402", "SK403", "SK404", "SK405"],
        "estimated_closure_duration": "6 hours"
    })
}


@pytest.mark.asyncio
async def test_single_invocation_simple(agent_client, metrics):
    """Test single invocation with simple disruption."""
    start = time.time()
    
    try:
        response = await agent_client.invoke_async(SIMPLE_DISRUPTION)
        duration = time.time() - start
        
        success = response and "error" not in str(response).lower()
        metrics.record("single_simple", duration, success, {
            "response_length": len(str(response))
        })
        
        assert success, "Simple invocation failed"
        assert duration < 30, f"Simple invocation too slow: {duration:.2f}s"
        
    except Exception as e:
        duration = time.time() - start
        metrics.record("single_simple", duration, False, {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_single_invocation_complex(agent_client, metrics):
    """Test single invocation with complex disruption."""
    start = time.time()
    
    try:
        response = await agent_client.invoke_async(COMPLEX_DISRUPTION)
        duration = time.time() - start
        
        success = response and "error" not in str(response).lower()
        metrics.record("single_complex", duration, success, {
            "response_length": len(str(response))
        })
        
        assert success, "Complex invocation failed"
        assert duration < 45, f"Complex invocation too slow: {duration:.2f}s"
        
    except Exception as e:
        duration = time.time() - start
        metrics.record("single_complex", duration, False, {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_concurrent_invocations(agent_client, metrics):
    """Test concurrent invocations to measure throughput."""
    num_concurrent = 3
    
    async def invoke_and_measure(idx: int):
        start = time.time()
        try:
            response = await agent_client.invoke_async(SIMPLE_DISRUPTION)
            duration = time.time() - start
            success = response and "error" not in str(response).lower()
            metrics.record(f"concurrent_{idx}", duration, success)
            return success
        except Exception as e:
            duration = time.time() - start
            metrics.record(f"concurrent_{idx}", duration, False, {"error": str(e)})
            return False
    
    start = time.time()
    results = await asyncio.gather(*[invoke_and_measure(i) for i in range(num_concurrent)])
    total_duration = time.time() - start
    
    success_count = sum(results)
    assert success_count >= num_concurrent * 0.8, f"Too many concurrent failures: {success_count}/{num_concurrent}"
    
    print(f"\nConcurrent test: {num_concurrent} requests in {total_duration:.2f}s")
    print(f"Throughput: {num_concurrent/total_duration:.2f} req/s")


@pytest.mark.asyncio
async def test_response_quality(agent_client, metrics):
    """Test response quality and structure."""
    start = time.time()
    
    try:
        response = await agent_client.invoke_async(COMPLEX_DISRUPTION)
        duration = time.time() - start
        
        # Parse response
        response_str = str(response)
        
        # Check for key components
        has_safety_analysis = any(word in response_str.lower() for word in ["crew", "maintenance", "regulatory", "safety"])
        has_business_analysis = any(word in response_str.lower() for word in ["network", "guest", "cargo", "finance", "business"])
        has_recommendations = "recommend" in response_str.lower() or "suggest" in response_str.lower()
        
        quality_score = sum([has_safety_analysis, has_business_analysis, has_recommendations]) / 3
        
        success = quality_score >= 0.66
        metrics.record("response_quality", duration, success, {
            "quality_score": quality_score,
            "has_safety": has_safety_analysis,
            "has_business": has_business_analysis,
            "has_recommendations": has_recommendations
        })
        
        assert success, f"Response quality insufficient: {quality_score:.2%}"
        
    except Exception as e:
        duration = time.time() - start
        metrics.record("response_quality", duration, False, {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_optimization_effectiveness(agent_client, metrics):
    """Test effectiveness of performance optimizations."""
    
    # Test 1: Batch query efficiency (should be faster than sequential)
    print("\n--- Testing Batch Query Optimization ---")
    
    # Simulate multiple queries
    queries = [SIMPLE_DISRUPTION, COMPLEX_DISRUPTION, SIMPLE_DISRUPTION]
    
    start = time.time()
    results = await asyncio.gather(*[agent_client.invoke_async(q) for q in queries])
    batch_duration = time.time() - start
    
    success = all(r and "error" not in str(r).lower() for r in results)
    metrics.record("batch_optimization", batch_duration, success, {
        "num_queries": len(queries),
        "avg_per_query": batch_duration / len(queries)
    })
    
    print(f"Batch execution: {len(queries)} queries in {batch_duration:.2f}s")
    print(f"Average per query: {batch_duration/len(queries):.2f}s")
    
    # Expected: batch should be faster than 3x single query time
    assert batch_duration < 90, f"Batch optimization not effective: {batch_duration:.2f}s"


@pytest.mark.asyncio
async def test_error_handling(agent_client, metrics):
    """Test error handling and recovery."""
    
    invalid_payload = {
        "prompt": json.dumps({
            "invalid_field": "test"
        })
    }
    
    start = time.time()
    
    try:
        response = await agent_client.invoke_async(invalid_payload)
        duration = time.time() - start
        
        # Should handle gracefully
        has_error_message = "error" in str(response).lower() or "invalid" in str(response).lower()
        
        metrics.record("error_handling", duration, True, {
            "handled_gracefully": has_error_message
        })
        
        # Should respond quickly even with errors
        assert duration < 10, f"Error handling too slow: {duration:.2f}s"
        
    except Exception as e:
        duration = time.time() - start
        metrics.record("error_handling", duration, True, {
            "exception_type": type(e).__name__
        })


@pytest.mark.asyncio
async def test_memory_efficiency(agent_client, metrics):
    """Test memory efficiency with multiple invocations."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Run multiple invocations
    for i in range(5):
        start = time.time()
        try:
            await agent_client.invoke_async(SIMPLE_DISRUPTION)
            duration = time.time() - start
            metrics.record(f"memory_test_{i}", duration, True)
        except Exception as e:
            duration = time.time() - start
            metrics.record(f"memory_test_{i}", duration, False, {"error": str(e)})
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory
    
    print(f"\nMemory usage:")
    print(f"  Initial: {initial_memory:.2f} MB")
    print(f"  Final: {final_memory:.2f} MB")
    print(f"  Increase: {memory_increase:.2f} MB")
    
    # Memory increase should be reasonable (< 100MB for 5 invocations)
    assert memory_increase < 100, f"Excessive memory usage: {memory_increase:.2f} MB"


def test_print_final_report(metrics):
    """Print final performance report."""
    metrics.print_report()
    
    # Save metrics to file
    summary = metrics.get_summary()
    with open("performance_test_results.json", "w") as f:
        json.dump({
            "summary": summary,
            "detailed_metrics": metrics.metrics,
            "timestamp": datetime.now().isoformat()
        }, f, indent=2)
    
    print("Results saved to: performance_test_results.json")
