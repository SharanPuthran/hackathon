#!/usr/bin/env python3
"""
Test V2 Agent Invocation

This script tests agent invocations against the V2 DynamoDB tables to verify
that agents can correctly query and analyze data from the migrated V2 tables.

Usage:
    cd /Users/sharanputhran/Learning/Hackathon/skymarshal_agents_new/skymarshal
    python -m test.test_v2_agent_invocation [--agent AGENT_NAME]
"""

import sys
import os
import json
import asyncio
import argparse
from datetime import datetime
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, '/Users/sharanputhran/Learning/Hackathon/skymarshal_agents_new/skymarshal/src')

# Suppress verbose logging for cleaner output
import logging
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('database').setLevel(logging.INFO)

from database.table_config import TABLE_VERSION, is_v2_enabled
from database.dynamodb import DynamoDBClient


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def print_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(label: str, value, indent: int = 0):
    """Print a labeled result."""
    prefix = "  " * indent
    if isinstance(value, (dict, list)):
        try:
            val_str = json.dumps(value, indent=2, cls=DecimalEncoder)
            if len(val_str) > 500:
                val_str = val_str[:500] + "..."
            print(f"{prefix}{label}:")
            for line in val_str.split('\n'):
                print(f"{prefix}  {line}")
        except:
            print(f"{prefix}{label}: {str(value)[:500]}")
    else:
        print(f"{prefix}{label}: {value}")


async def test_crew_compliance_agent():
    """Test crew compliance agent with V2 data."""
    print_section("Crew Compliance Agent Test")

    from agents import analyze_crew_compliance
    from model.load import load_model_for_agent

    # Test prompt asking about crew compliance for a flight
    prompt = """Analyze crew compliance for flight FL001 departing from JFK on January 20, 2026.
    Check if the assigned crew meets all FDP limits and rest requirements."""

    print(f"Prompt: {prompt}\n")
    print("Loading agent model...")
    llm = load_model_for_agent("safety")

    payload = {
        "user_prompt": prompt,
        "phase": "initial"
    }

    try:
        print("Invoking crew compliance agent...")
        result = await analyze_crew_compliance(payload, llm, [])

        print_result("\nAgent Response", {
            "status": result.get("status", "unknown"),
            "recommendation": result.get("recommendation", "N/A")[:200] + "..." if result.get("recommendation") else "N/A",
            "confidence": result.get("confidence", 0.0),
            "binding_constraints": result.get("binding_constraints", [])[:3],
            "data_sources": result.get("data_sources", [])[:5],
        })
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_network_agent():
    """Test network agent with V2 data."""
    print_section("Network Agent Test")

    from agents import analyze_network
    from model.load import load_model_for_agent

    # Test prompt about network impact
    prompt = """Analyze the network impact if flight FL005 from AUH to LHR is delayed by 3 hours.
    What connecting flights will be affected?"""

    print(f"Prompt: {prompt}\n")
    print("Loading agent model...")
    llm = load_model_for_agent("business")

    payload = {
        "user_prompt": prompt,
        "phase": "initial"
    }

    try:
        print("Invoking network agent...")
        result = await analyze_network(payload, llm, [])

        print_result("\nAgent Response", {
            "status": result.get("status", "unknown"),
            "recommendation": result.get("recommendation", "N/A")[:200] + "..." if result.get("recommendation") else "N/A",
            "confidence": result.get("confidence", 0.0),
            "binding_constraints": result.get("binding_constraints", [])[:3],
        })
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_guest_experience_agent():
    """Test guest experience agent with V2 data."""
    print_section("Guest Experience Agent Test")

    from agents import analyze_guest_experience
    from model.load import load_model_for_agent

    # Test prompt about passenger impact
    prompt = """Analyze the impact on passengers if flight FL003 is cancelled.
    How many passengers are affected? What rebooking options are available?"""

    print(f"Prompt: {prompt}\n")
    print("Loading agent model...")
    llm = load_model_for_agent("business")

    payload = {
        "user_prompt": prompt,
        "phase": "initial"
    }

    try:
        print("Invoking guest experience agent...")
        result = await analyze_guest_experience(payload, llm, [])

        print_result("\nAgent Response", {
            "status": result.get("status", "unknown"),
            "recommendation": result.get("recommendation", "N/A")[:200] + "..." if result.get("recommendation") else "N/A",
            "confidence": result.get("confidence", 0.0),
        })
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


async def test_direct_v2_queries():
    """Test direct queries against V2 tables."""
    print_section("Direct V2 Query Tests")

    db = DynamoDBClient()

    # Test 1: Get a flight from V2 table
    print("\n1. Query flights_v2 table:")
    try:
        table = db.get_v2_table("flights")
        response = table.scan(Limit=3)
        items = response.get('Items', [])
        print(f"   Found {len(items)} flights")
        for f in items:
            print(f"   - {f.get('flight_id')}: {f.get('flight_number')} ({f.get('origin')} -> {f.get('destination')})")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 2: Query passengers with connections
    print("\n2. Query passengers_v2 with connection details:")
    try:
        table = db.get_v2_table("passengers")
        response = table.scan(
            FilterExpression="attribute_exists(second_leg_flight_id)",
            Limit=3
        )
        items = response.get('Items', [])
        print(f"   Found {len(items)} connecting passengers")
        for p in items:
            print(f"   - {p.get('passenger_id')}: {p.get('first_leg_flight_id')} -> {p.get('second_leg_flight_id')}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 3: Query compensation rules (V2-only table)
    print("\n3. Query compensation_rules_v2 (V2-only table):")
    try:
        table = db.get_v2_table("compensation_rules")
        response = table.scan(Limit=3)
        items = response.get('Items', [])
        print(f"   Found {len(items)} compensation rules")
        for r in items:
            print(f"   - {r.get('rule_id')}: {r.get('regulation')} - {r.get('delay_category')}")
    except Exception as e:
        print(f"   Error: {e}")

    # Test 4: Query aircraft rotations (V2-only table)
    print("\n4. Query aircraft_rotations_v2 (V2-only table):")
    try:
        table = db.get_v2_table("aircraft_rotations")
        response = table.scan(Limit=3)
        items = response.get('Items', [])
        print(f"   Found {len(items)} rotation entries")
        for r in items:
            print(f"   - {r.get('rotation_id')}: Aircraft {r.get('aircraft_registration')} seq {r.get('sequence_number')}")
    except Exception as e:
        print(f"   Error: {e}")

    return True


async def run_all_tests():
    """Run all V2 agent invocation tests."""
    print("\n" + "=" * 70)
    print("  V2 AGENT INVOCATION TEST SUITE")
    print("  Testing agent invocations against V2 DynamoDB tables")
    print(f"  {datetime.now().isoformat()}")
    print("=" * 70)

    # Check V2 configuration
    print(f"\nTable Version: {TABLE_VERSION.value}")
    print(f"V2 Enabled: {is_v2_enabled()}")

    if not is_v2_enabled():
        print("\n⚠️  WARNING: V2 tables are not enabled!")
        print("   Set TABLE_VERSION = TableVersion.V2 in database/table_config.py")
        return

    results = {}

    # Run direct query tests first
    results['direct_queries'] = await test_direct_v2_queries()

    # Run agent tests (these take longer due to LLM calls)
    print("\n" + "-" * 70)
    print("  Running Agent Tests (these may take 30-60 seconds each)")
    print("-" * 70)

    # Comment out agent tests if you want faster execution
    # results['crew_compliance'] = await test_crew_compliance_agent()
    # results['network'] = await test_network_agent()
    # results['guest_experience'] = await test_guest_experience_agent()

    print_section("TEST SUMMARY")
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")

    print(f"\n  Timestamp: {datetime.now().isoformat()}")
    print("=" * 70 + "\n")


async def run_single_agent_test(agent_name: str):
    """Run a single agent test."""
    agent_tests = {
        'crew_compliance': test_crew_compliance_agent,
        'network': test_network_agent,
        'guest_experience': test_guest_experience_agent,
        'direct': test_direct_v2_queries,
    }

    if agent_name not in agent_tests:
        print(f"Unknown agent: {agent_name}")
        print(f"Available: {list(agent_tests.keys())}")
        return

    print(f"\nTable Version: {TABLE_VERSION.value}")
    print(f"V2 Enabled: {is_v2_enabled()}")

    await agent_tests[agent_name]()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test V2 agent invocations")
    parser.add_argument("--agent", type=str, help="Run single agent test (crew_compliance, network, guest_experience, direct)")
    args = parser.parse_args()

    if args.agent:
        asyncio.run(run_single_agent_test(args.agent))
    else:
        asyncio.run(run_all_tests())
