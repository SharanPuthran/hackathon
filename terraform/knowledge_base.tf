# Amazon Bedrock Knowledge Base for SkyMarshal
# This creates a knowledge base with vector embeddings for semantic search

# OpenSearch Serverless Collection for vector storage
resource "aws_opensearchserverless_security_policy" "kb_encryption" {
  name = "skymarshal-kb-encryption"
  type = "encryption"
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/skymarshal-kb-vectors"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "kb_network" {
  name = "skymarshal-kb-network"
  type = "network"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/skymarshal-kb-vectors"
          ]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

resource "aws_opensearchserverless_collection" "kb_vectors" {
  name = "skymarshal-kb-vectors"
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.kb_encryption,
    aws_opensearchserverless_security_policy.kb_network
  ]

  tags = {
    Name        = "SkyMarshal Knowledge Base Vectors"
    Environment = "prod"
    Purpose     = "Vector embeddings for RAG"
  }
}

resource "aws_opensearchserverless_access_policy" "kb_access" {
  name = "skymarshal-kb-access"
  type = "data"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource = [
            "collection/skymarshal-kb-vectors"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        },
        {
          ResourceType = "index"
          Resource = [
            "index/skymarshal-kb-vectors/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        }
      ]
      Principal = [
        aws_iam_role.bedrock_kb_role.arn,
        aws_iam_role.bedrock_agent.arn,
        "arn:aws:iam::368613657554:role/AWSReservedSSO_AWSAdministratorAccess_aa081849542deab6"
      ]
    }
  ])
}

# IAM Role for Bedrock Knowledge Base
resource "aws_iam_role" "bedrock_kb_role" {
  name = "skymarshal-bedrock-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockKnowledgeBaseAssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:aws:bedrock:us-east-1:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
          }
        }
      }
    ]
  })

  tags = {
    Name        = "SkyMarshal Bedrock Knowledge Base Role"
    Environment = "prod"
  }
}

resource "aws_iam_role_policy" "bedrock_kb_policy" {
  name = "skymarshal-bedrock-kb-policy"
  role = aws_iam_role.bedrock_kb_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockEmbeddingsAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0",
          "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v1"
        ]
      },
      {
        Sid    = "S3DataSourceAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.knowledge_base.arn,
          "${aws_s3_bucket.knowledge_base.arn}/*"
        ]
      },
      {
        Sid    = "OpenSearchAccess"
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = aws_opensearchserverless_collection.kb_vectors.arn
      }
    ]
  })
}

# Bedrock Knowledge Base
# Note: Bedrock will automatically create the vector index in OpenSearch Serverless
resource "aws_bedrockagent_knowledge_base" "skymarshal_kb" {
  name     = "skymarshal-knowledge-base"
  role_arn = aws_iam_role.bedrock_kb_role.arn

  description = "SkyMarshal knowledge base for airline regulations, disruption management, and decision-making context"

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.kb_vectors.arn
      vector_index_name = "bedrock-knowledge-base-default-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  depends_on = [
    aws_opensearchserverless_collection.kb_vectors,
    aws_opensearchserverless_access_policy.kb_access,
    aws_iam_role_policy.bedrock_kb_policy
  ]

  tags = {
    Name        = "SkyMarshal Knowledge Base"
    Environment = "prod"
    Purpose     = "RAG for arbitrator agent"
  }
}

# Data Source for Knowledge Base (S3)
resource "aws_bedrockagent_data_source" "skymarshal_docs" {
  name              = "skymarshal-documents"
  knowledge_base_id = aws_bedrockagent_knowledge_base.skymarshal_kb.id

  description = "Airline regulations, disruption management procedures, and reference documents"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.knowledge_base.arn
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 512
        overlap_percentage = 20
      }
    }
  }

  depends_on = [
    aws_bedrockagent_knowledge_base.skymarshal_kb
  ]
}

# Outputs
output "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID"
  value       = aws_bedrockagent_knowledge_base.skymarshal_kb.id
}

output "knowledge_base_arn" {
  description = "Bedrock Knowledge Base ARN"
  value       = aws_bedrockagent_knowledge_base.skymarshal_kb.arn
}

output "opensearch_collection_endpoint" {
  description = "OpenSearch Serverless Collection Endpoint"
  value       = aws_opensearchserverless_collection.kb_vectors.collection_endpoint
}

output "data_source_id" {
  description = "Knowledge Base Data Source ID"
  value       = aws_bedrockagent_data_source.skymarshal_docs.id
}
