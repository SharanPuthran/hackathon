#!/usr/bin/env python3
"""
Simple test script to verify Knowledge Base integration
"""
import boto3
import sys

KNOWLEDGE_BASE_ID = "UDONMVCXEW"
AWS_REGION = "us-east-1"

def test_knowledge_base_connection():
    """Test basic knowledge base connectivity"""
    print("=" * 60)
    print("Testing SkyMarshal Knowledge Base Connection")
    print("=" * 60)
    print(f"Knowledge Base ID: {KNOWLEDGE_BASE_ID}")
    print(f"Region: {AWS_REGION}")
    print()

    try:
        # Initialize client
        print("Initializing Bedrock Agent Runtime client...")
        bedrock = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
        print("✅ Client initialized")
        print()

        # Test query
        test_query = "What is SkyMarshal?"
        print(f"Test Query: '{test_query}'")
        print()

        response = bedrock.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': test_query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 3
                }
            }
        )

        results = response.get('retrievalResults', [])
        print(f"✅ Knowledge Base is accessible!")
        print(f"Found {len(results)} results")
        print()

        # Display results
        for i, result in enumerate(results[:3], 1):
            score = result.get('score', 0)
            content = result.get('content', {}).get('text', '')
            print(f"Result {i} (Score: {score:.2f}):")
            print(f"{content[:300]}...")
            print()

        print("=" * 60)
        print("✅ Knowledge Base Test PASSED")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print()
        print("=" * 60)
        print("❌ Knowledge Base Test FAILED")
        print("=" * 60)
        return False

if __name__ == "__main__":
    success = test_knowledge_base_connection()
    sys.exit(0 if success else 1)
