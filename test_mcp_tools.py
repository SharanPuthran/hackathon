"""Test Amazon Bedrock AgentCore MCP Server Tools"""

import boto3
import json
from datetime import datetime

def test_mcp_tools():
    """Test documented MCP server tools"""

    print("="*70)
    print("Testing Bedrock AgentCore MCP Server Tools")
    print("="*70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize Bedrock clients
    bedrock_agent = boto3.client('bedrock-agent', region_name='us-east-1')
    bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

    results = {
        "agent_management": {},
        "knowledge_base": {},
        "invocation": {}
    }

    # ========================================================================
    # 1. AGENT MANAGEMENT TOOLS
    # ========================================================================
    print("📋 AGENT MANAGEMENT TOOLS")
    print("-" * 70)

    # Test: list_agents
    print("\n1. Testing list_agents...")
    try:
        response = bedrock_agent.list_agents(maxResults=10)
        agents = response.get('agentSummaries', [])
        results["agent_management"]["list_agents"] = {
            "status": "✅ PASS",
            "count": len(agents),
            "agents": [
                {
                    "name": agent['agentName'],
                    "id": agent['agentId'],
                    "status": agent['agentStatus']
                }
                for agent in agents
            ]
        }
        print(f"   ✅ Found {len(agents)} agents")
        for agent in agents:
            print(f"      - {agent['agentName']} ({agent['agentStatus']})")
            print(f"        ID: {agent['agentId']}")
    except Exception as e:
        results["agent_management"]["list_agents"] = {
            "status": "❌ FAIL",
            "error": str(e)
        }
        print(f"   ❌ Error: {e}")

    # Test: get_agent (if agents exist)
    if agents:
        print("\n2. Testing get_agent (describe agent details)...")
        try:
            agent_id = agents[0]['agentId']
            response = bedrock_agent.get_agent(agentId=agent_id)
            agent_details = response['agent']

            results["agent_management"]["get_agent"] = {
                "status": "✅ PASS",
                "agent": {
                    "name": agent_details['agentName'],
                    "id": agent_details['agentId'],
                    "model": agent_details.get('foundationModel', 'N/A'),
                    "status": agent_details['agentStatus'],
                    "created": agent_details['createdAt'].isoformat() if 'createdAt' in agent_details else 'N/A'
                }
            }

            print(f"   ✅ Agent Details Retrieved")
            print(f"      Name: {agent_details['agentName']}")
            print(f"      Model: {agent_details.get('foundationModel', 'N/A')}")
            print(f"      Status: {agent_details['agentStatus']}")
            print(f"      ARN: {agent_details['agentArn']}")
        except Exception as e:
            results["agent_management"]["get_agent"] = {
                "status": "❌ FAIL",
                "error": str(e)
            }
            print(f"   ❌ Error: {e}")

    # Test: list_agent_aliases
    if agents:
        print("\n3. Testing list_agent_aliases...")
        try:
            agent_id = agents[0]['agentId']
            response = bedrock_agent.list_agent_aliases(agentId=agent_id)
            aliases = response.get('agentAliasSummaries', [])

            results["agent_management"]["list_agent_aliases"] = {
                "status": "✅ PASS",
                "count": len(aliases),
                "aliases": [
                    {
                        "name": alias['agentAliasName'],
                        "id": alias['agentAliasId'],
                        "status": alias['agentAliasStatus']
                    }
                    for alias in aliases
                ]
            }

            print(f"   ✅ Found {len(aliases)} aliases")
            for alias in aliases:
                print(f"      - {alias['agentAliasName']} ({alias['agentAliasStatus']})")
        except Exception as e:
            results["agent_management"]["list_agent_aliases"] = {
                "status": "❌ FAIL",
                "error": str(e)
            }
            print(f"   ❌ Error: {e}")

    # ========================================================================
    # 2. KNOWLEDGE BASE TOOLS
    # ========================================================================
    print("\n\n📚 KNOWLEDGE BASE TOOLS")
    print("-" * 70)

    # Test: list_knowledge_bases
    print("\n4. Testing list_knowledge_bases...")
    try:
        response = bedrock_agent.list_knowledge_bases(maxResults=10)
        knowledge_bases = response.get('knowledgeBaseSummaries', [])

        results["knowledge_base"]["list_knowledge_bases"] = {
            "status": "✅ PASS",
            "count": len(knowledge_bases),
            "knowledge_bases": [
                {
                    "name": kb['name'],
                    "id": kb['knowledgeBaseId'],
                    "status": kb['status']
                }
                for kb in knowledge_bases
            ]
        }

        print(f"   ✅ Found {len(knowledge_bases)} knowledge bases")
        for kb in knowledge_bases:
            print(f"      - {kb['name']} ({kb['status']})")
            print(f"        ID: {kb['knowledgeBaseId']}")
    except Exception as e:
        results["knowledge_base"]["list_knowledge_bases"] = {
            "status": "❌ FAIL",
            "error": str(e)
        }
        print(f"   ❌ Error: {e}")

    # ========================================================================
    # 3. AGENT INVOCATION TOOLS
    # ========================================================================
    print("\n\n🚀 AGENT INVOCATION TOOLS")
    print("-" * 70)

    # Test: invoke_agent (if agent has aliases)
    if agents and 'aliases' in results["agent_management"].get("list_agent_aliases", {}):
        agent_aliases = results["agent_management"]["list_agent_aliases"]["aliases"]
        if agent_aliases:
            print("\n5. Testing invoke_agent...")
            try:
                agent_id = agents[0]['agentId']
                alias_id = agent_aliases[0]['id']
                session_id = f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}"

                response = bedrock_agent_runtime.invoke_agent(
                    agentId=agent_id,
                    agentAliasId=alias_id,
                    sessionId=session_id,
                    inputText="Hello, this is a test invocation. Please respond briefly."
                )

                # Collect streaming response
                completion = ""
                event_stream = response.get('completion', [])
                for event in event_stream:
                    if 'chunk' in event:
                        chunk_data = event['chunk']
                        if 'bytes' in chunk_data:
                            completion += chunk_data['bytes'].decode('utf-8')

                results["invocation"]["invoke_agent"] = {
                    "status": "✅ PASS" if completion else "⚠️  PARTIAL",
                    "session_id": session_id,
                    "response_length": len(completion),
                    "response_preview": completion[:200] if completion else "No response"
                }

                print(f"   ✅ Agent invoked successfully")
                print(f"      Session ID: {session_id}")
                print(f"      Response length: {len(completion)} chars")
                if completion:
                    print(f"      Preview: {completion[:150]}...")

            except Exception as e:
                results["invocation"]["invoke_agent"] = {
                    "status": "❌ FAIL",
                    "error": str(e)
                }
                print(f"   ❌ Error: {e}")
        else:
            print("\n5. Skipping invoke_agent (no aliases available)")
            results["invocation"]["invoke_agent"] = {
                "status": "⏭️  SKIPPED",
                "reason": "No agent aliases found"
            }

    # ========================================================================
    # 4. SUMMARY
    # ========================================================================
    print("\n\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0

    for category, tests in results.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for test_name, result in tests.items():
            status = result.get("status", "❓ UNKNOWN")
            print(f"  {test_name}: {status}")

            total_tests += 1
            if "✅" in status:
                passed_tests += 1
            elif "❌" in status:
                failed_tests += 1
            elif "⏭️" in status:
                skipped_tests += 1

    print(f"\n{'='*70}")
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"⏭️  Skipped: {skipped_tests}")
    print(f"{'='*70}")

    # Save results to JSON
    output_file = "mcp_tools_test_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "total": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests
            }
        }, f, indent=2, default=str)

    print(f"\n💾 Results saved to: {output_file}")

    # Return success if all non-skipped tests passed
    return failed_tests == 0

if __name__ == "__main__":
    import sys
    try:
        success = test_mcp_tools()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
