"""Check status of the deployed Arbitrator agent"""

import boto3

REGION = "us-east-1"
AGENT_ID = "GBMIHM7VP0"  # From deployment output

bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

print(f"Checking agent status: {AGENT_ID}")

try:
    response = bedrock_agent.get_agent(agentId=AGENT_ID)
    agent = response['agent']

    print(f"\nAgent Name: {agent['agentName']}")
    print(f"Agent ID: {agent['agentId']}")
    print(f"Status: {agent['agentStatus']}")
    print(f"Model: {agent.get('foundationModel', 'N/A')}")
    print(f"Created: {agent.get('createdAt', 'N/A')}")
    print(f"Updated: {agent.get('updatedAt', 'N/A')}")

    if agent['agentStatus'] == 'PREPARED':
        print("\n✅ Agent is ready! You can now create an alias.")
    elif agent['agentStatus'] == 'PREPARING':
        print("\n⏳ Agent is still preparing. Wait a moment and check again.")
    elif agent['agentStatus'] == 'FAILED':
        print("\n❌ Agent preparation failed!")
    else:
        print(f"\n⚠️  Agent status: {agent['agentStatus']}")

except Exception as e:
    print(f"Error: {e}")
