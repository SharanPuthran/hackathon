"""
Deploy SkyMarshal Arbitrator Agent to AWS Bedrock
Creates a Bedrock agent using the Arbitrator configuration
"""

import boto3
import json
from datetime import datetime

# AWS configuration
REGION = "us-east-1"
AGENT_NAME = "skymarshal-arbitrator"
MODEL_ID = "us.anthropic.claude-opus-4-5-20251101-v1:0"
IAM_ROLE_ARN = "arn:aws:iam::368613657554:role/skymarshal-bedrock-agent-role"

# Agent instruction - mirrors the LangGraph implementation
AGENT_INSTRUCTION = """You are the SkyMarshal Arbitrator Agent - the final decision maker in a multi-agent airline disruption management system.

Your role is to synthesize inputs from safety and business agents and make optimal decisions that:
1. Meet ALL safety requirements (non-negotiable)
2. Optimize for weighted criteria: Safety (40%), Cost (25%), Passengers (20%), Network (10%), Reputation (5%)
3. Balance stakeholder interests
4. Provide clear, actionable rationale

Decision Workflow:
1. Analyze inputs from safety and business agents
2. Generate 3-5 viable recovery scenarios
3. Evaluate each scenario against decision criteria
4. Rank scenarios by weighted score
5. Select optimal scenario
6. Generate comprehensive rationale

Decision Criteria:
- Safety (40%): Zero violations, regulatory compliance
- Cost (25%): Financial impact, operational expenses
- Passengers (20%): Satisfaction, compensation, rebooking
- Network (10%): Downstream delays, connections
- Reputation (5%): Brand impact, customer loyalty

Output Format:
Provide structured decisions with:
- Selected scenario name
- Weighted score (0-100)
- Confidence level (0-100)
- Executive summary
- Safety compliance confirmation
- Cost-benefit analysis
- Passenger impact assessment
- Implementation steps
- Risk mitigation measures

You must be analytical, objective, and decisive. All recommendations must prioritize safety while optimizing business outcomes."""


def create_bedrock_agent():
    """Create the Arbitrator agent in AWS Bedrock"""

    print("=" * 70)
    print("🚀 Deploying SkyMarshal Arbitrator Agent to AWS Bedrock")
    print("=" * 70)

    # Initialize Bedrock Agent client
    bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

    try:
        # Step 1: Create the agent
        print("\n📝 Step 1: Creating Bedrock Agent...")
        print(f"   Name: {AGENT_NAME}")
        print(f"   Model: {MODEL_ID}")
        print(f"   Role: {IAM_ROLE_ARN}")

        create_response = bedrock_agent.create_agent(
            agentName=AGENT_NAME,
            foundationModel=MODEL_ID,
            instruction=AGENT_INSTRUCTION,
            agentResourceRoleArn=IAM_ROLE_ARN,
            description="SkyMarshal Arbitrator - Multi-criteria decision maker using Claude Opus 4.5",
            idleSessionTTLInSeconds=600,  # 10 minutes
            tags={
                "Project": "SkyMarshal",
                "Agent": "Arbitrator",
                "Model": "Claude-Opus-4.5",
                "Environment": "Production"
            }
        )

        agent_id = create_response['agent']['agentId']
        agent_arn = create_response['agent']['agentArn']
        agent_status = create_response['agent']['agentStatus']

        print(f"   ✅ Agent created successfully!")
        print(f"   Agent ID: {agent_id}")
        print(f"   Agent ARN: {agent_arn}")
        print(f"   Status: {agent_status}")

        # Step 2: Prepare the agent (this creates a version)
        print("\n📦 Step 2: Preparing agent version...")

        prepare_response = bedrock_agent.prepare_agent(agentId=agent_id)

        agent_status = prepare_response['agentStatus']
        print(f"   ✅ Agent preparation initiated!")
        print(f"   Status: {agent_status}")

        # Wait for agent to finish preparing
        print("\n⏳ Waiting for agent to finish preparing...")
        import time
        max_wait = 300  # 5 minutes
        wait_interval = 5
        elapsed = 0

        while elapsed < max_wait:
            time.sleep(wait_interval)
            elapsed += wait_interval

            get_response = bedrock_agent.get_agent(agentId=agent_id)
            agent_status = get_response['agent']['agentStatus']

            print(f"   Status: {agent_status} ({elapsed}s elapsed)")

            if agent_status in ['PREPARED', 'NOT_PREPARED', 'FAILED']:
                break

        if agent_status == 'PREPARED':
            print(f"   ✅ Agent is ready!")
        elif agent_status == 'FAILED':
            print(f"   ❌ Agent preparation failed!")
            return None
        else:
            print(f"   ⚠️  Agent status: {agent_status} - continuing anyway")

        # Step 3: Create an alias for the agent
        print("\n🏷️  Step 3: Creating agent alias...")

        alias_response = bedrock_agent.create_agent_alias(
            agentId=agent_id,
            agentAliasName="production",
            description="Production alias for SkyMarshal Arbitrator"
        )

        alias_id = alias_response['agentAlias']['agentAliasId']
        alias_arn = alias_response['agentAlias']['agentAliasArn']

        print(f"   ✅ Alias created successfully!")
        print(f"   Alias ID: {alias_id}")
        print(f"   Alias ARN: {alias_arn}")

        # Step 4: Save deployment info
        deployment_info = {
            "deployment_timestamp": datetime.utcnow().isoformat(),
            "agent_name": AGENT_NAME,
            "agent_id": agent_id,
            "agent_arn": agent_arn,
            "model_id": MODEL_ID,
            "alias_id": alias_id,
            "alias_arn": alias_arn,
            "iam_role": IAM_ROLE_ARN,
            "region": REGION,
            "status": "deployed"
        }

        with open('arbitrator_deployment.json', 'w') as f:
            json.dump(deployment_info, f, indent=2)

        print("\n💾 Deployment info saved to: arbitrator_deployment.json")

        # Step 5: Display test invocation command
        print("\n" + "=" * 70)
        print("✅ DEPLOYMENT COMPLETE!")
        print("=" * 70)
        print("\n📋 Deployment Summary:")
        print(f"   Agent Name: {AGENT_NAME}")
        print(f"   Agent ID: {agent_id}")
        print(f"   Alias ID: {alias_id}")
        print(f"   Model: {MODEL_ID}")
        print(f"   Status: Ready for invocation")

        print("\n🧪 Test Invocation:")
        print(f"   Use test_arbitrator_invocation.py to test the agent")
        print(f"   Or invoke via AWS CLI:")
        print(f"   aws bedrock-agent-runtime invoke-agent \\")
        print(f"       --agent-id {agent_id} \\")
        print(f"       --agent-alias-id {alias_id} \\")
        print(f"       --session-id test-session-001 \\")
        print(f"       --input-text 'Analyze disruption scenario'")

        return deployment_info

    except Exception as e:
        print(f"\n❌ Error during deployment: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = create_bedrock_agent()

    if result:
        print("\n🎉 Arbitrator agent is now deployed to AWS Bedrock!")
        print(f"   Ready to receive disruption scenarios for decision-making")
    else:
        print("\n❌ Deployment failed. Check the error messages above.")
