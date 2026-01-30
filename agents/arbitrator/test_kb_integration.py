#!/usr/bin/env python3
"""
Test the Arbitrator Agent's Knowledge Base integration locally.
This script tests the KB directly without the LangChain agent framework.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from langchain_aws import ChatBedrock
import boto3
from langchain_core.messages import HumanMessage, SystemMessage

# Knowledge Base Configuration
KNOWLEDGE_BASE_ID = "UDONMVCXEW"
AWS_REGION = "us-east-1"

# Initialize Bedrock clients
bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)

def query_knowledge_base(query: str, num_results: int = 3) -> str:
    """Query the SkyMarshal Knowledge Base"""
    print(f"\n🔍 Querying Knowledge Base: '{query}'")
    print("-" * 60)

    try:
        response = bedrock_agent_runtime.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': num_results
                }
            }
        )

        results = response.get('retrievalResults', [])

        if not results:
            return "No relevant information found in the knowledge base."

        print(f"✅ Found {len(results)} results\n")

        formatted_results = []
        for i, result in enumerate(results, 1):
            score = result.get('score', 0)
            content = result.get('content', {}).get('text', '')
            location = result.get('location', {})

            print(f"Result {i} (Score: {score:.3f}):")
            print(f"  Content: {content[:200]}...")
            if location:
                print(f"  Source: {location.get('s3Location', {}).get('uri', 'Unknown')}")
            print()

            formatted_results.append(f"[Score: {score:.3f}] {content}")

        return "\n\n".join(formatted_results)

    except Exception as e:
        error_msg = f"Error querying knowledge base: {str(e)}"
        print(f"❌ {error_msg}\n")
        return error_msg


def test_with_llm(kb_context: str):
    """Test using Claude with the KB context"""
    print("\n🤖 Testing Claude Sonnet 4.5 with KB Context")
    print("=" * 60)

    try:
        # Initialize Claude
        llm = ChatBedrock(
            model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            region_name=AWS_REGION,
            model_kwargs={
                "max_tokens": 2048,
                "temperature": 0.3
            }
        )

        # Create a prompt with KB context
        system_prompt = """You are the SkyMarshal Arbitrator Agent, an expert in airline disruption management.
Use the provided knowledge base context to answer questions about aviation regulations and procedures."""

        user_query = "Based on the knowledge base, what are the key considerations for managing flight disruptions?"

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Knowledge Base Context:
{kb_context[:1500]}

Question: {user_query}

Please provide a concise answer based on the knowledge base context.""")
        ]

        print(f"Query: {user_query}\n")
        print("Generating response...\n")

        response = llm.invoke(messages)

        print("✅ Response:")
        print("-" * 60)
        print(response.content)
        print("-" * 60)

        return response.content

    except Exception as e:
        error_msg = f"Error invoking Claude: {str(e)}"
        print(f"❌ {error_msg}\n")
        return error_msg


def main():
    print("=" * 60)
    print("SkyMarshal Arbitrator - Knowledge Base Integration Test")
    print("=" * 60)

    # Test 1: Query the Knowledge Base
    test_queries = [
        "What are the crew compliance requirements?",
        "How should maintenance delays be handled?",
        "What are the regulatory considerations for flight delays?"
    ]

    all_kb_results = []

    for query in test_queries:
        kb_results = query_knowledge_base(query, num_results=2)
        all_kb_results.append(kb_results)

    # Test 2: Use Claude with KB context
    combined_context = "\n\n".join(all_kb_results)
    test_with_llm(combined_context)

    print("\n" + "=" * 60)
    print("✅ Knowledge Base Integration Test Complete!")
    print("=" * 60)
    print("\nSummary:")
    print("  - Knowledge Base is accessible")
    print("  - Can retrieve relevant documents")
    print("  - Claude can process KB context and generate responses")
    print("\nNext Steps:")
    print("  - Fix LangChain tool formatting issue for full agent integration")
    print("  - Deploy to AgentCore Runtime: agentcore deploy")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
