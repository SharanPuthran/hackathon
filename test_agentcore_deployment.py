"""
Test SkyMarshal Arbitrator Agent Deployed on AgentCore Runtime

This script tests the arbitrator agent after deployment to AWS Bedrock AgentCore.

Prerequisites:
    1. Deploy agent: agentcore deploy
    2. Note the agent runtime ARN from deployment output
    3. Update AGENT_RUNTIME_ARN below with your ARN

Usage:
    python3 test_agentcore_deployment.py
"""

import boto3
import uuid
import json
from datetime import datetime


# CONFIGURATION: Update with your deployed agent ARN
AGENT_RUNTIME_ARN = "arn:aws:bedrock-agentcore:us-east-1:368613657554:agent-runtime/skymarshal-arbitrator"
REGION = "us-east-1"


def test_agentcore_invocation():
    """Test invoking the deployed AgentCore agent"""

    print("=" * 80)
    print("SkyMarshal Arbitrator - AgentCore Deployment Test")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Agent ARN: {AGENT_RUNTIME_ARN}")
    print(f"Region: {REGION}")
    print()

    # Initialize AgentCore client
    try:
        agentcore_client = boto3.client('bedrock-agentcore', region_name=REGION)
        print("✅ AgentCore client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize AgentCore client: {e}")
        print("\nNote: If 'bedrock-agentcore' is not recognized, ensure:")
        print("  1. AWS SDK/boto3 is updated: pip install --upgrade boto3")
        print("  2. AgentCore is available in your region")
        return

    # Test 1: Simple healthcheck/prompt
    print("\n" + "-" * 80)
    print("Test 1: Simple Prompt")
    print("-" * 80)

    simple_payload = {
        "prompt": "Hello from AgentCore deployment test!"
    }

    try:
        session_id = str(uuid.uuid4())
        print(f"Session ID: {session_id}")
        print("Invoking agent...")

        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=simple_payload
        )

        result = json.loads(response.get('output', '{}'))
        print(f"\n✅ Response received:")
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")

    except Exception as e:
        print(f"❌ Simple prompt test failed: {e}")

    # Test 2: Full disruption scenario
    print("\n" + "-" * 80)
    print("Test 2: Full Disruption Analysis")
    print("-" * 80)

    disruption_payload = {
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
    print(f"   Flight: {disruption_payload['disruption_scenario']['flight_number']}")
    print(f"   Route: {disruption_payload['disruption_scenario']['route']}")
    print(f"   Issue: {disruption_payload['disruption_scenario']['issue']}")
    print(f"   Passengers: {disruption_payload['disruption_scenario']['passengers']}")

    print("\n🤖 Invoking AgentCore Arbitrator (deployed)...")

    try:
        session_id = str(uuid.uuid4())
        print(f"Session ID: {session_id}")

        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_RUNTIME_ARN,
            runtimeSessionId=session_id,
            payload=disruption_payload
        )

        result = json.loads(response.get('output', '{}'))

        if result.get("status") == "success":
            print("\n✅ Decision Made Successfully!")
            print("\n" + "=" * 80)

            decision = result.get("decision", {})
            print(f"📋 Selected Scenario: {decision.get('scenario_id')}")
            print(f"   Name: {decision.get('scenario_name')}")
            print(f"   Score: {decision.get('overall_score')}/100")
            print(f"   Action: {decision.get('recommended_action')}")

            print(f"\n🎯 Confidence: {result.get('confidence_score')}%")

            print("\n💡 Rationale:")
            rationale = result.get("rationale", "")
            if len(rationale) > 500:
                print(f"   {rationale[:500]}...")
                print(f"   ... (truncated, {len(rationale)} total characters)")
            else:
                print(f"   {rationale}")

            scenarios = result.get("scenarios_evaluated", [])
            if scenarios:
                print(f"\n📊 Scenarios Evaluated: {len(scenarios)}")
                for i, scenario in enumerate(scenarios[:5], 1):
                    print(f"   {i}. {scenario.get('id')}: {scenario.get('name')} (Score: {scenario.get('score')})")

            context = result.get("disruption_context", {})
            print(f"\n🔍 Disruption Context:")
            print(f"   Flight: {context.get('flight_number')}")
            print(f"   Route: {context.get('route')}")
            print(f"   Issue: {context.get('issue')}")

            print(f"\n⏱️  Timestamp: {result.get('timestamp')}")
            print("=" * 80)

            print("\n🎉 AgentCore deployment test PASSED!")
            print("\nThe arbitrator agent is successfully deployed and operational.")

        else:
            print(f"\n❌ Error in agent response:")
            print(f"   Status: {result.get('status')}")
            print(f"   Error: {result.get('error_message')}")
            print(f"   Type: {result.get('error_type')}")

    except Exception as e:
        print(f"\n❌ Full disruption test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify agent is deployed: agentcore list")
        print("  2. Check agent ARN is correct in this script")
        print("  3. Verify IAM permissions for bedrock-agentcore:InvokeAgentRuntime")
        print("  4. Check CloudWatch logs: /aws/bedrock-agentcore/runtime/skymarshal")

    print("\n" + "=" * 80)


def main():
    """Run deployment tests"""

    # Check configuration
    if "your-agent-runtime-arn" in AGENT_RUNTIME_ARN.lower() or not AGENT_RUNTIME_ARN.startswith("arn:"):
        print("\n❌ ERROR: AGENT_RUNTIME_ARN not configured!")
        print("\nPlease update the AGENT_RUNTIME_ARN variable in this script.")
        print("\nTo get the ARN:")
        print("  1. Deploy agent: agentcore deploy")
        print("  2. Note the agent runtime ARN from output")
        print("  3. Update AGENT_RUNTIME_ARN at the top of this file")
        return

    # Run tests
    test_agentcore_invocation()


if __name__ == "__main__":
    main()
