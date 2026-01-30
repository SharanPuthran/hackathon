# SkyMarshal - Simplified Initial Deployment
# Phase 1: Core infrastructure (VPC, S3, basics)
# Updated: 2026-01-30 - Migrated to AWS Bedrock AgentCore

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "skymarshal-terraform-state-368613657554"
    key            = "skymarshal/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "skymarshal-terraform-locks"
  }
}

provider "aws" {
  region = "us-east-1"

  default_tags {
    tags = {
      Project     = "SkyMarshal"
      Environment = "prod"
      ManagedBy   = "Terraform"
      CostCenter  = "Etihad-Innovation"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# S3 Buckets
resource "aws_s3_bucket" "disruptions" {
  bucket = "skymarshal-prod-disruptions-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "SkyMarshal Disruption Scenarios"
    Environment = "prod"
  }
}

resource "aws_s3_bucket_versioning" "disruptions" {
  bucket = aws_s3_bucket.disruptions.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "disruptions" {
  bucket = aws_s3_bucket.disruptions.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "knowledge_base" {
  bucket = "skymarshal-prod-knowledge-base-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "SkyMarshal Knowledge Base"
    Environment = "prod"
  }
}

resource "aws_s3_bucket_versioning" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "agent_logs" {
  bucket = "skymarshal-prod-agent-logs-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "SkyMarshal Agent Logs"
    Environment = "prod"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "agent_logs" {
  bucket = aws_s3_bucket.agent_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "agent_logs" {
  bucket = aws_s3_bucket.agent_logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket" "decisions" {
  bucket = "skymarshal-prod-decisions-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "SkyMarshal Decisions"
    Environment = "prod"
  }
}

resource "aws_s3_bucket_versioning" "decisions" {
  bucket = aws_s3_bucket.decisions.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "decisions" {
  bucket = aws_s3_bucket.decisions.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# IAM Role for Bedrock AgentCore Runtime
# Also supports legacy Bedrock Agents for backward compatibility
resource "aws_iam_role" "bedrock_agent" {
  name = "skymarshal-bedrock-agentcore-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockAgentCoreAssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "bedrock.amazonaws.com",
            "bedrock-agentcore.amazonaws.com"
          ]
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid    = "CodeBuildAssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "SkyMarshal Bedrock AgentCore Role"
    Description = "IAM role for AgentCore Runtime and deployment"
  }
}

resource "aws_iam_role_policy" "bedrock_agentcore_policy" {
  name = "skymarshal-bedrock-agentcore-policy"
  role = aws_iam_role.bedrock_agent.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "BedrockModelAccess"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:us-east-1::foundation-model/us.amazon.nova-premier-v1:0",
          "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-pro-v1:0",
          "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-opus-4-5-20251101-v1:0",
          "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-opus-4-5-20251101-v1:0"
        ]
      },
      {
        Sid    = "AgentCoreManagement"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:CreateAgent",
          "bedrock-agentcore:UpdateAgent",
          "bedrock-agentcore:DeleteAgent",
          "bedrock-agentcore:DescribeAgent",
          "bedrock-agentcore:ListAgents",
          "bedrock-agentcore:InvokeAgentRuntime"
        ]
        Resource = "arn:aws:bedrock-agentcore:us-east-1:${data.aws_caller_identity.current.account_id}:agent/*"
      },
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.disruptions.arn,
          "${aws_s3_bucket.disruptions.arn}/*",
          aws_s3_bucket.knowledge_base.arn,
          "${aws_s3_bucket.knowledge_base.arn}/*",
          aws_s3_bucket.agent_logs.arn,
          "${aws_s3_bucket.agent_logs.arn}/*",
          aws_s3_bucket.decisions.arn,
          "${aws_s3_bucket.decisions.arn}/*"
        ]
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock/*",
          "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/*"
        ]
      },
      {
        Sid    = "ECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        Sid    = "DynamoDBMemory"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "arn:aws:dynamodb:us-east-1:${data.aws_caller_identity.current.account_id}:table/skymarshal-agentcore-memory"
      }
    ]
  })
}

# CloudWatch Log Groups
# AgentCore Runtime logs (primary)
resource "aws_cloudwatch_log_group" "agentcore_runtime" {
  name              = "/aws/bedrock-agentcore/runtime/skymarshal"
  retention_in_days = 30

  tags = {
    Name        = "SkyMarshal AgentCore Runtime Logs"
    Environment = "prod"
    Runtime     = "AgentCore"
  }
}

# Legacy Bedrock Agents logs (for backward compatibility)
resource "aws_cloudwatch_log_group" "bedrock_agents_legacy" {
  name              = "/aws/bedrock/agents/skymarshal"
  retention_in_days = 30

  tags = {
    Name        = "SkyMarshal Bedrock Agent Logs (Legacy)"
    Environment = "prod"
    Status      = "Deprecated"
  }
}

# DynamoDB Table for AgentCore Memory
resource "aws_dynamodb_table" "agentcore_memory" {
  name           = "skymarshal-agentcore-memory"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "session_id"
  range_key      = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "expiration_time"
    enabled        = true
  }

  tags = {
    Name        = "SkyMarshal AgentCore Memory Store"
    Environment = "prod"
    Purpose     = "Agent conversation history and context"
  }
}

# Outputs
output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    disruptions   = aws_s3_bucket.disruptions.id
    knowledge_base = aws_s3_bucket.knowledge_base.id
    agent_logs    = aws_s3_bucket.agent_logs.id
    decisions     = aws_s3_bucket.decisions.id
  }
}

output "agentcore_role_arn" {
  description = "Bedrock AgentCore IAM Role ARN"
  value       = aws_iam_role.bedrock_agent.arn
}

output "bedrock_agent_role_arn" {
  description = "Bedrock AgentCore IAM Role ARN (alias for backward compatibility)"
  value       = aws_iam_role.bedrock_agent.arn
}

output "agentcore_memory_table" {
  description = "DynamoDB table for AgentCore Memory"
  value       = aws_dynamodb_table.agentcore_memory.name
}

output "agentcore_log_group" {
  description = "CloudWatch Log Group for AgentCore Runtime"
  value       = aws_cloudwatch_log_group.agentcore_runtime.name
}

output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "deployment_region" {
  description = "AWS Region"
  value       = "us-east-1"
}
