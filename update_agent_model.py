"""Update agent model to test different models"""

import boto3
import sys
import time

REGION = "us-east-1"
AGENT_ID = "GBMIHM7VP0"

bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

if len(sys.argv) < 2:
    print("Usage: python3 update_agent_model.py <model_id>")
    print("Examples:")
    print("  python3 update_agent_model.py us.amazon.nova-premier-v1:0")
    print("  python3 update_agent_model.py us.anthropic.claude-opus-4-5-20251101-v1:0")
    sys.exit(1)

new_model_id = sys.argv[1]

print(f"Updating agent {AGENT_ID} to use model: {new_model_id}...")

try:
    # Update the agent
    response = bedrock_agent.update_agent(
        agentId=AGENT_ID,
        agentName="skymarshal-arbitrator",
        foundationModel=new_model_id,
        agentResourceRoleArn="arn:aws:iam::368613657554:role/skymarshal-bedrock-agent-role",
        instruction="""You are the SkyMarshal Arbitrator Agent - the final decision maker in a multi-agent airline disruption management system.

Your role is to synthesize inputs from safety and business agents and make optimal decisions that:
1. Meet ALL safety requirements (non-negotiable)
2. Optimize for weighted criteria: Safety (40%), Cost (25%), Passengers (20%), Network (10%), Reputation (5%)
3. Balance stakeholder interests
4. Provide clear, actionable rationale"""
    )

    print(f"✅ Agent updated")

    # Prepare the agent
    print("\nPreparing agent...")
    bedrock_agent.prepare_agent(agentId=AGENT_ID)

    # Wait for preparation
    time.sleep(10)

    print("✅ Agent is ready to test")
    print(f"\nRun: python3 test_arbitrator_invocation.py")

except Exception as e:
    print(f"❌ Error: {e}")
