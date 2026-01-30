#!/usr/bin/env python3
"""
Create OpenSearch Serverless index using boto3 SigV4 signing
"""
import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import urllib3

http = urllib3.PoolManager()

# Configuration
COLLECTION_ENDPOINT = "https://auu271l02wwqlmq6rcpa.us-east-1.aoss.amazonaws.com"
INDEX_NAME = "skymarshal-kb-index"
REGION = "us-east-1"

def create_index():
    """Create index with vector field mapping"""
    # Get credentials
    session = boto3.Session()
    credentials = session.get_credentials()

    # Index configuration
    index_body = {
        "settings": {
            "index": {
                "knn": True
            }
        },
        "mappings": {
            "properties": {
                "vector": {
                    "type": "knn_vector",
                    "dimension": 1024,
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "space_type": "l2"
                    }
                },
                "text": {
                    "type": "text"
                },
                "metadata": {
                    "type": "text",
                    "index": False
                }
            }
        }
    }

    # Create AWS request
    url = f"{COLLECTION_ENDPOINT}/{INDEX_NAME}"
    body = json.dumps(index_body).encode('utf-8')

    request = AWSRequest(method='PUT', url=url, data=body, headers={'Content-Type': 'application/json'})
    SigV4Auth(credentials, 'aoss', REGION).add_auth(request)

    print("=" * 60)
    print("Creating OpenSearch Index for Bedrock Knowledge Base")
    print("=" * 60)
    print(f"Collection: {COLLECTION_ENDPOINT}")
    print(f"Index: {INDEX_NAME}")
    print()

    try:
        print(f"📝 Creating index '{INDEX_NAME}'...")
        response = http.request(
            method=request.method,
            url=request.url,
            body=request.body,
            headers=dict(request.headers)
        )

        print(f"Status: {response.status}")
        response_data = json.loads(response.data.decode('utf-8'))
        print(json.dumps(response_data, indent=2))

        if response.status in [200, 201]:
            print(f"\n✅ Index '{INDEX_NAME}' created successfully!")
            return True
        elif 'resource_already_exists' in str(response_data):
            print(f"\nℹ️  Index '{INDEX_NAME}' already exists")
            return True
        else:
            print(f"\n⚠️  Unexpected status: {response.status}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if create_index():
        print("\n✅ Index is ready for Bedrock Knowledge Base!")
        print("\nNext: Run 'terraform apply' to create the Knowledge Base")
        return 0
    else:
        return 1

if __name__ == "__main__":
    exit(main())
