"""Test direct invocation of Claude Opus 4.5"""

import boto3
import json

REGION = "us-east-1"
MODEL_ID = "us.anthropic.claude-opus-4-5-20251101-v1:0"

bedrock_runtime = boto3.client('bedrock-runtime', region_name=REGION)

print(f"Testing direct invocation of {MODEL_ID}...")

try:
    response = bedrock_runtime.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": "Hello, can you respond with 'working'?"}]
            }
        ],
        inferenceConfig={
            "maxTokens": 100,
            "temperature": 0.3
        }
    )

    output_text = response['output']['message']['content'][0]['text']
    print(f"✅ Success! Model responded: {output_text}")

except Exception as e:
    print(f"❌ Error: {e}")
    print(f"\nThis might mean Claude Opus 4.5 requires model access approval.")
    print("Check: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess")
