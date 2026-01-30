#!/usr/bin/env python3
"""
Create OpenSearch Serverless index for Bedrock Knowledge Base using direct HTTP requests
"""
import boto3
import json
import requests
from requests_aws4auth import AWS4Auth

# Configuration
COLLECTION_ENDPOINT = "https://auu271l02wwqlmq6rcpa.us-east-1.aoss.amazonaws.com"
INDEX_NAME = "skymarshal-kb-index"
REGION = "us-east-1"

def create_index():
    """Create index with vector field mapping"""
    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()

    # Create AWS4Auth for signing requests
    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'aoss',
        session_token=credentials.token
    )

    # Index configuration
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
                "vector": {
                    "type": "knn_vector",
                    "dimension": 1024,  # Titan Embeddings v2 dimension
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {
                            "ef_construction": 512,
                            "m": 16
                        },
                        "space_type": "l2"
                    }
                },
                "text": {
                    "type": "text",
                    "index": True
                },
                "metadata": {
                    "type": "text",
                    "index": False
                }
            }
        }
    }

    # Create index
    url = f"{COLLECTION_ENDPOINT}/{INDEX_NAME}"
    headers = {'Content-Type': 'application/json'}

    print("=" * 60)
    print("Creating OpenSearch Index for Bedrock Knowledge Base")
    print("=" * 60)
    print(f"Collection: {COLLECTION_ENDPOINT}")
    print(f"Index: {INDEX_NAME}")
    print(f"Region: {REGION}")
    print()

    try:
        print(f"📝 Creating index '{INDEX_NAME}'...")
        response = requests.put(
            url,
            auth=awsauth,
            headers=headers,
            json=index_body,
            timeout=30
        )

        if response.status_code in [200, 201]:
            print(f"✅ Index '{INDEX_NAME}' created successfully!")
            print(json.dumps(response.json(), indent=2))
            return True
        elif response.status_code == 400 and 'resource_already_exists_exception' in response.text.lower():
            print(f"ℹ️  Index '{INDEX_NAME}' already exists")
            return True
        else:
            print(f"❌ Error creating index: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_index():
    """Verify index exists"""
    session = boto3.Session()
    credentials = session.get_credentials()

    awsauth = AWS4Auth(
        credentials.access_key,
        credentials.secret_key,
        REGION,
        'aoss',
        session_token=credentials.token
    )

    url = f"{COLLECTION_ENDPOINT}/{INDEX_NAME}"

    try:
        print(f"\n🔍 Verifying index '{INDEX_NAME}'...")
        response = requests.get(url, auth=awsauth, timeout=30)

        if response.status_code == 200:
            print(f"✅ Index verified successfully!")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"❌ Error verifying index: {response.status_code}")
            print(response.text)
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    if create_index():
        verify_index()
        print("\n✅ All done! Index is ready for Bedrock Knowledge Base.")
        print("\nNext step: Run 'terraform apply' again to create the Knowledge Base")
        return 0
    else:
        print("\n❌ Failed to create index")
        return 1

if __name__ == "__main__":
    exit(main())
