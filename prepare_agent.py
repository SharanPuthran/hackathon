"""Prepare the Arbitrator agent after IAM policy update"""

import boto3
import time

REGION = "us-east-1"
AGENT_ID = "GBMIHM7VP0"

bedrock_agent = boto3.client('bedrock-agent', region_name=REGION)

print(f"Preparing agent {AGENT_ID} after IAM policy update...")

try:
    # Prepare the agent again
    response = bedrock_agent.prepare_agent(agentId=AGENT_ID)

    print(f"✅ Agent preparation initiated")
    print(f"   Status: {response['agentStatus']}")

    # Wait for preparation to complete
    print("\n⏳ Waiting for agent to finish preparing...")
    max_wait = 300
    wait_interval = 5
    elapsed = 0

    while elapsed < max_wait:
        time.sleep(wait_interval)
        elapsed += wait_interval

        get_response = bedrock_agent.get_agent(agentId=AGENT_ID)
        agent_status = get_response['agent']['agentStatus']

        print(f"   Status: {agent_status} ({elapsed}s elapsed)")

        if agent_status in ['PREPARED', 'NOT_PREPARED', 'FAILED']:
            break

    if agent_status == 'PREPARED':
        print(f"\n✅ Agent is ready!")
        print(f"   The agent can now use Claude Opus 4.5")
        print(f"\n🧪 Test with: python3 test_arbitrator_invocation.py")
    elif agent_status == 'FAILED':
        print(f"\n❌ Agent preparation failed!")
    else:
        print(f"\n⚠️  Agent status: {agent_status}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
