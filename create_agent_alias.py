"""Create alias for the deployed Arbitrator agent"""

import boto3
import json
from datetime import datetime

REGION = "us-east-1"
AGENT_ID = "GBMIHM7VP0"
AGENT_NAME = "skymarshal-arbitrator"
MODEL_ID = "us.anthropic.claude-opus-4-5-20251101-v1:0"
IAM_ROLE_ARN = "arn:aws:iam::368613657554:role/skymarshal-bedrock-agent-role"

bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

print("=" * 70)
print("🏷️  Creating alias for SkyMarshal Arbitrator Agent")
print("=" * 70)

try:
    # Create the alias
    print(f"\nAgent ID: {AGENT_ID}")
    print(f"Creating 'production' alias...")

    alias_response = bedrock_agent.create_agent_alias(
        agentId=AGENT_ID,
        agentAliasName="production",
        description="Production alias for SkyMarshal Arbitrator"
    )

    alias_id = alias_response['agentAlias']['agentAliasId']
    alias_arn = alias_response['agentAlias']['agentAliasArn']
    alias_status = alias_response['agentAlias']['agentAliasStatus']

    print(f"✅ Alias created successfully!")
    print(f"   Alias ID: {alias_id}")
    print(f"   Alias ARN: {alias_arn}")
    print(f"   Status: {alias_status}")

    # Get agent ARN
    agent_response = bedrock_agent.get_agent(agentId=AGENT_ID)
    agent_arn = agent_response['agent']['agentArn']

    # Save deployment info
    deployment_info = {
        "deployment_timestamp": datetime.utcnow().isoformat(),
        "agent_name": AGENT_NAME,
        "agent_id": AGENT_ID,
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

    # Display summary
    print("\n" + "=" * 70)
    print("✅ DEPLOYMENT COMPLETE!")
    print("=" * 70)
    print("\n📋 Deployment Summary:")
    print(f"   Agent Name: {AGENT_NAME}")
    print(f"   Agent ID: {AGENT_ID}")
    print(f"   Alias ID: {alias_id}")
    print(f"   Model: {MODEL_ID}")
    print(f"   Status: Ready for invocation")

    print("\n🧪 Test the agent:")
    print(f"   python3 test_arbitrator_invocation.py")

    print("\n📖 AWS Console:")
    print(f"   https://console.aws.amazon.com/bedrock/home?region={REGION}#/agents/{AGENT_ID}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
