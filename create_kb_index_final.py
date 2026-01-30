#!/usr/bin/env python3
"""
Create OpenSearch Serverless index for Bedrock Knowledge Base - Final Version
Uses standard Bedrock field names
"""
import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import urllib3
import time

http = urllib3.PoolManager()

# Configuration
COLLECTION_ENDPOINT = "https://auu271l02wwqlmq6rcpa.us-east-1.aoss.amazonaws.com"
INDEX_NAME = "bedrock-knowledge-base-default-index"
REGION = "us-east-1"

def create_index():
    """Create index with Bedrock-standard vector field mapping"""
    session = boto3.Session()
    credentials = session.get_credentials()

    # Bedrock Knowledge Base standard index configuration
    index_body = {
        "settings": {
            "index": {
                "knn": True,
                "number_of_shards": 2,
                "number_of_replicas": 0
            }
        },
        "mappings": {
            "properties": {
                "bedrock-knowledge-base-default-vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "space_type": "l2",
                        "parameters": {
                            "ef_construction": 512,
                            "m": 16
                        }
                    }
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {
                    "type": "text",
                    "index": True
                },
                "AMAZON_BEDROCK_METADATA": {
                    "type": "text",
                    "index": False
                }
            }
        }
    }

    url = f"{COLLECTION_ENDPOINT}/{INDEX_NAME}"
    body = json.dumps(index_body).encode('utf-8')

    request = AWSRequest(method='PUT', url=url, data=body, headers={'Content-Type': 'application/json'})
    SigV4Auth(credentials, 'aoss', REGION).add_auth(request)

    print("=" * 70)
    print("Creating OpenSearch Serverless Index for Bedrock Knowledge Base")
    print("=" * 70)
    print(f"Collection: {COLLECTION_ENDPOINT}")
    print(f"Index Name: {INDEX_NAME}")
    print(f"Region: {REGION}")
    print()
    print("Waiting 5 seconds for access policy propagation...")
    time.sleep(5)

    try:
        print(f"\n📝 Creating index '{INDEX_NAME}' with Bedrock-standard fields...")
        response = http.request(
            method=request.method,
            url=request.url,
            body=request.body,
            headers=dict(request.headers)
        )

        print(f"Response Status: {response.status}")
        response_data = json.loads(response.data.decode('utf-8'))
        print(json.dumps(response_data, indent=2))

        if response.status in [200, 201]:
            print(f"\n✅ SUCCESS! Index '{INDEX_NAME}' created!")
            print("\nIndex Configuration:")
            print(f"  - Vector Dimension: 1024 (Titan Embeddings v2)")
            print(f"  - Vector Field: bedrock-knowledge-base-default-vector")
            print(f"  - Text Field: AMAZON_BEDROCK_TEXT_CHUNK")
            print(f"  - Metadata Field: AMAZON_BEDROCK_METADATA")
            return True
        elif 'resource_already_exists' in str(response_data).lower():
            print(f"\nℹ️  Index '{INDEX_NAME}' already exists - this is fine!")
            return True
        else:
            print(f"\n❌ Unexpected status: {response.status}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if create_index():
        print("\n" + "=" * 70)
        print("✅ Index is ready! Now you can create the Bedrock Knowledge Base.")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Run: cd terraform && terraform apply tfplan-kb-retry")
        print("2. Wait for Knowledge Base creation (~2 minutes)")
        print("3. Upload documents to S3 and sync the data source")
        return 0
    else:
        print("\n❌ Failed to create index")
        print("If you see 403 Forbidden, wait 1-2 minutes and try again (policy propagation)")
        return 1

if __name__ == "__main__":
    exit(main())
