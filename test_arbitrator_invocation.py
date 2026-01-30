"""
Test SkyMarshal Arbitrator Agent invocation via AWS Bedrock
Tests the deployed Bedrock agent with a sample disruption scenario
"""

import boto3
import json
from datetime import datetime

REGION = "us-east-1"


def load_deployment_info():
    """Load deployment info from file"""
    try:
        with open('arbitrator_deployment.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Deployment info not found. Run deploy_arbitrator.py first.")
        return None


def invoke_arbitrator(agent_id, alias_id, disruption_scenario, safety_assessments, business_proposals):
    """Invoke the Arbitrator agent via Bedrock"""

    print("=" * 70)
    print("🧪 Testing SkyMarshal Arbitrator Agent")
    print("=" * 70)

    # Initialize Bedrock Agent Runtime client
    bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=REGION)

    # Create input text with all context
    input_text = f"""Analyze this airline disruption and provide a decision:

DISRUPTION SCENARIO:
{json.dumps(disruption_scenario, indent=2)}

SAFETY ASSESSMENTS:
{json.dumps(safety_assessments, indent=2)}

BUSINESS PROPOSALS:
{json.dumps(business_proposals, indent=2)}

Provide:
1. Analysis of the situation
2. 3-5 viable recovery scenarios
3. Evaluation of each scenario
4. Final decision with rationale
5. Confidence score
"""

    try:
        print(f"\n📤 Sending request to agent...")
        print(f"   Agent ID: {agent_id}")
        print(f"   Alias ID: {alias_id}")

        # Generate session ID
        session_id = f"test-session-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        # Invoke the agent
        response = bedrock_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=input_text
        )

        print(f"   ✅ Request sent successfully!")
        print(f"   Session ID: {session_id}")

        # Process the response stream
        print(f"\n📥 Processing response stream...")

        completion = ""
        event_stream = response['completion']

        for event in event_stream:
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    completion += chunk_text
                    print(".", end="", flush=True)

        print("\n")

        # Display results
        print("=" * 70)
        print("✅ ARBITRATOR DECISION")
        print("=" * 70)
        print(completion)
        print("=" * 70)

        # Save the result
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "agent_id": agent_id,
            "alias_id": alias_id,
            "input": {
                "disruption": disruption_scenario,
                "safety": safety_assessments,
                "business": business_proposals
            },
            "output": completion
        }

        output_file = f"arbitrator_test_result_{session_id}.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"\n💾 Result saved to: {output_file}")

        return result

    except Exception as e:
        print(f"\n❌ Error invoking agent: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main test function"""

    # Load deployment info
    deployment_info = load_deployment_info()
    if not deployment_info:
        return

    agent_id = deployment_info['agent_id']
    alias_id = deployment_info['alias_id']

    print(f"\n📋 Using deployed agent:")
    print(f"   Agent: {deployment_info['agent_name']}")
    print(f"   Model: {deployment_info['model_id']}")
    print(f"   Deployed: {deployment_info['deployment_timestamp']}")

    # Sample test data - same as used in arbitrator_agent.py test
    test_disruption = {
        "flight_number": "EY123",
        "route": "AUH → LHR",
        "issue": "Hydraulic system fault",
        "delay_hours": 3,
        "passengers": 615,
        "connections_at_risk": 87
    }

    test_safety = {
        "crew_compliance": {"status": "APPROVED", "ftl_remaining": "3.5 hours"},
        "maintenance": {"status": "MEL_CATEGORY_B", "deferrable": True},
        "regulatory": {"status": "CURFEW_RISK", "latest_departure": "20:00"}
    }

    test_business = {
        "network": {"priority": "HIGH", "downstream_impact": "$450K"},
        "guest_experience": {"compensation": "€125K", "satisfaction_risk": "MEDIUM"},
        "cargo": {"critical_shipments": 3, "offload_recommended": False},
        "finance": {"cancel_cost": "€1.2M", "delay_cost": "€210K"}
    }

    # Invoke the agent
    result = invoke_arbitrator(
        agent_id=agent_id,
        alias_id=alias_id,
        disruption_scenario=test_disruption,
        safety_assessments=test_safety,
        business_proposals=test_business
    )

    if result:
        print("\n🎉 Test completed successfully!")
        print("   The Arbitrator agent is working in AWS Bedrock")
    else:
        print("\n❌ Test failed")


if __name__ == "__main__":
    main()
