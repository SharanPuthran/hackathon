"""Test all Bedrock model providers"""

import asyncio
import sys
from src.model_providers import create_bedrock_client, ModelFactory
from src.config import AGENT_MODEL_MAP

async def test_model(factory, agent_name, model_config):
    """Test a single model"""
    print(f"\n{'='*60}")
    print(f"Testing: {agent_name}")
    print(f"Model: {model_config['model_id']}")
    print(f"Reason: {model_config['reason']}")
    print('-'*60)

    try:
        provider = factory.get_provider(agent_name)

        # Simple test prompt
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Respond in one brief sentence."},
            {"role": "user", "content": "What is 2+2? Answer briefly."}
        ]

        response = await provider.invoke(messages, max_tokens=100, temperature=0.1)

        print(f"✓ SUCCESS")
        print(f"Response: {response[:100]}")
        return True

    except Exception as e:
        print(f"✗ FAILED: {str(e)[:200]}")
        return False

async def main():
    """Test all models"""
    print("="*60)
    print("SkyMarshal Model Provider Test")
    print("="*60)

    # Create Bedrock client
    try:
        bedrock_client = create_bedrock_client()
        print("✓ Bedrock client created successfully")
    except Exception as e:
        print(f"✗ Failed to create Bedrock client: {e}")
        sys.exit(1)

    # Create model factory
    factory = ModelFactory(bedrock_client)

    # Test each agent's model
    results = {}
    for agent_name, model_config in AGENT_MODEL_MAP.items():
        success = await test_model(factory, agent_name, model_config)
        results[agent_name] = success

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    successful = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nTotal agents: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")

    print("\nResults by agent:")
    for agent_name, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {agent_name}")

    if successful == total:
        print("\n🎉 All models are working!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - successful} models failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
