"""
Deploy SkyMarshal Arbitrator Agent to AWS Bedrock AgentCore Runtime

This script packages and deploys the arbitrator agent to AgentCore Runtime.
"""

import boto3
import json
import time
import zipfile
import io
from pathlib import Path

# Configuration
AWS_REGION = "us-east-1"
AGENT_NAME = "skymarshal-arbitrator"
AGENT_DESCRIPTION = "Multi-criteria decision maker for airline disruption management"
CLAUDE_MODEL_ID = "us.anthropic.claude-opus-4-5-20251101-v1:0"

# Files to include in deployment package
DEPLOYMENT_FILES = [
    "agentcore_arbitrator.py",
    "agents/arbitrator_agent.py",
    "agents/__init__.py"
]


def create_deployment_package():
    """Create a ZIP package of the agent code"""
    print("📦 Creating deployment package...")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in DEPLOYMENT_FILES:
            if Path(file_path).exists():
                zipf.write(file_path)
                print(f"   ✅ Added: {file_path}")
            else:
                print(f"   ⚠️  Warning: {file_path} not found")

    buffer.seek(0)
    return buffer.getvalue()


def deploy_to_agentcore():
    """Deploy agent to AWS Bedrock AgentCore Runtime"""

    print("\n" + "="*60)
    print("SkyMarshal Arbitrator - AgentCore Deployment")
    print("="*60)

    # Initialize boto3 clients
    print(f"\n🔐 Initializing AWS clients (region: {AWS_REGION})...")

    try:
        # Check if bedrock-agentcore service is available
        session = boto3.Session(region_name=AWS_REGION)

        # Get account info
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"   ✅ AWS Account: {identity['Account']}")
        print(f"   ✅ User: {identity['Arn'].split('/')[-1]}")

        # Note: bedrock-agentcore API may not be fully available in boto3 yet
        # Check available services
        available_services = session.get_available_services()

        if 'bedrock-agentcore' in available_services:
            print(f"   ✅ bedrock-agentcore service available")
            agentcore = session.client('bedrock-agentcore')

            # List existing agents
            print("\n📋 Checking for existing agents...")
            try:
                response = agentcore.list_agents()
                existing_agents = response.get('agents', [])
                print(f"   Found {len(existing_agents)} existing agent(s)")

                for agent in existing_agents:
                    print(f"   - {agent.get('agentName')} (ID: {agent.get('agentId')})")

            except Exception as e:
                print(f"   ⚠️  Could not list agents: {e}")

            # Create deployment package
            deployment_zip = create_deployment_package()

            # Deploy agent
            print(f"\n🚀 Deploying agent: {AGENT_NAME}...")

            try:
                # Note: Actual API may differ - this is based on AgentCore documentation
                create_response = agentcore.create_agent(
                    agentName=AGENT_NAME,
                    description=AGENT_DESCRIPTION,
                    foundationModel=CLAUDE_MODEL_ID,
                    agentResourceRoleArn=f"arn:aws:iam::{identity['Account']}:role/BedrockAgentCoreRole",
                    # Additional parameters based on actual AgentCore API
                )

                agent_id = create_response.get('agentId')
                agent_arn = create_response.get('agentArn')

                print(f"   ✅ Agent created successfully!")
                print(f"   Agent ID: {agent_id}")
                print(f"   Agent ARN: {agent_arn}")

                print(f"\n✅ Deployment complete!")
                print(f"\nTest with:")
                print(f"   python3.11 test_agentcore_deployment.py")

                return {
                    "success": True,
                    "agent_id": agent_id,
                    "agent_arn": agent_arn
                }

            except Exception as e:
                print(f"   ❌ Deployment failed: {e}")
                print(f"\nThis might be because:")
                print(f"   1. bedrock-agentcore API is not yet available in this region")
                print(f"   2. IAM permissions need to be configured")
                print(f"   3. Service requires AWS Console deployment first")
                return {"success": False, "error": str(e)}

        else:
            print(f"   ⚠️  bedrock-agentcore service not found in boto3")
            print(f"   Available services: {', '.join(sorted(available_services)[:10])}...")
            print(f"\n💡 Alternative Deployment Options:")
            print(f"   1. Use AWS Console: https://console.aws.amazon.com/bedrock/")
            print(f"   2. Use AWS CLI if bedrock-agentcore is supported")
            print(f"   3. Deploy as Lambda function with AgentCore Runtime")

            return {"success": False, "error": "Service not available in boto3"}

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    result = deploy_to_agentcore()

    if result["success"]:
        print("\n" + "="*60)
        print("🎉 Deployment Successful!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("⚠️  Deployment requires manual setup")
        print("="*60)
        print("\nNext steps:")
        print("1. Open AWS Bedrock Console")
        print("2. Navigate to AgentCore section")
        print("3. Upload agentcore_arbitrator.py and agents/")
        print("4. Configure with Claude Opus 4.5")
        print("5. Deploy and test")
