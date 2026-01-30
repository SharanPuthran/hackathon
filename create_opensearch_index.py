#!/usr/bin/env python3
"""
Create OpenSearch Serverless index for Bedrock Knowledge Base
"""
import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# Configuration
COLLECTION_ENDPOINT = "auu271l02wwqlmq6rcpa.us-east-1.aoss.amazonaws.com"
INDEX_NAME = "skymarshal-kb-index"
REGION = "us-east-1"

def create_opensearch_client():
    """Create OpenSearch client with AWS authentication"""
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, REGION, 'aoss')

    client = OpenSearch(
        hosts=[{'host': COLLECTION_ENDPOINT, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )
    return client

def create_index(client):
    """Create index with vector field mapping"""
    index_body = {
        "settings": {
            "index": {
                "number_of_shards": 2,
                "number_of_replicas": 0,
                "knn": True,
                "knn.algo_param.ef_search": 512
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
                    "type": "object",
                    "enabled": True
                }
            }
        }
    }

    try:
        response = client.indices.create(index=INDEX_NAME, body=index_body)
        print(f"✅ Index '{INDEX_NAME}' created successfully!")
        print(json.dumps(response, indent=2))
        return True
    except Exception as e:
        if 'resource_already_exists_exception' in str(e).lower():
            print(f"ℹ️  Index '{INDEX_NAME}' already exists")
            return True
        else:
            print(f"❌ Error creating index: {e}")
            return False

def verify_index(client):
    """Verify index exists and get info"""
    try:
        response = client.indices.get(index=INDEX_NAME)
        print(f"\n✅ Index verification successful!")
        print(f"Index settings:")
        print(json.dumps(response, indent=2))
        return True
    except Exception as e:
        print(f"❌ Error verifying index: {e}")
        return False

def main():
    print("=" * 60)
    print("Creating OpenSearch Index for Bedrock Knowledge Base")
    print("=" * 60)
    print(f"Collection: {COLLECTION_ENDPOINT}")
    print(f"Index: {INDEX_NAME}")
    print(f"Region: {REGION}")
    print()

    try:
        # Create OpenSearch client
        print("🔗 Connecting to OpenSearch Serverless...")
        client = create_opensearch_client()
        print("✅ Connected successfully!")

        # Create index
        print(f"\n📝 Creating index '{INDEX_NAME}'...")
        if create_index(client):
            print("\n🔍 Verifying index...")
            verify_index(client)
            print("\n✅ All done! Index is ready for Bedrock Knowledge Base.")
            return 0
        else:
            print("\n❌ Failed to create index")
            return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
