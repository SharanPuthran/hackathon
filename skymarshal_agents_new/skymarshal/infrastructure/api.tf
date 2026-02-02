# Terraform configuration for AgentCore REST API with Async Polling
# This creates API Gateway, Lambda functions, and DynamoDB tables for async processing

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "agentcore_runtime_arn" {
  description = "ARN of the AgentCore Runtime"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

# DynamoDB Table for Sessions
resource "aws_dynamodb_table" "sessions" {
  name           = "skymarshal-sessions-${var.environment}"
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
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "skymarshal-sessions"
    Environment = var.environment
  }
}

# DynamoDB Table for Async Requests
resource "aws_dynamodb_table" "requests" {
  name           = "skymarshal-requests-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "request_id"

  attribute {
    name = "request_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = "skymarshal-requests"
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "skymarshal-api-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "lambda_policy" {
  name = "skymarshal-api-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeRuntime",
          "bedrock-agentcore:InvokeAgentRuntime",
          "bedrock-agentcore:GetRuntime"
        ]
        Resource = "${var.agentcore_runtime_arn}*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem",
          "dynamodb:DescribeTable"
        ]
        Resource = [
          aws_dynamodb_table.sessions.arn,
          aws_dynamodb_table.requests.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:*:function:skymarshal-api-invoke-${var.environment}"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Lambda Function - Invoke Handler with Async Processing
resource "aws_lambda_function" "invoke_handler" {
  filename      = "../build/lambda_package.zip"
  function_name = "skymarshal-api-invoke-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "src.api.lambda_handler_async.lambda_handler"
  runtime       = "python3.11"
  timeout       = 900  # 15 minutes for async processing
  memory_size   = 1024

  environment {
    variables = {
      AGENTCORE_RUNTIME_ARN = var.agentcore_runtime_arn
      SKYMARSHAL_AWS_REGION = var.aws_region
      SESSION_TABLE_NAME    = aws_dynamodb_table.sessions.name
      REQUESTS_TABLE_NAME   = aws_dynamodb_table.requests.name
      LOG_LEVEL             = "INFO"
    }
  }

  reserved_concurrent_executions = 10

  tags = {
    Name        = "skymarshal-api-invoke"
    Environment = var.environment
  }
}

# Lambda Function - Health Check
resource "aws_lambda_function" "health_handler" {
  filename      = "../build/lambda_package.zip"
  function_name = "skymarshal-api-health-${var.environment}"
  role          = aws_iam_role.lambda_role.arn
  handler       = "src.api.health.health_check_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      AGENTCORE_RUNTIME_ARN = var.agentcore_runtime_arn
      SKYMARSHAL_AWS_REGION = var.aws_region
      SESSION_TABLE_NAME    = aws_dynamodb_table.sessions.name
    }
  }

  tags = {
    Name        = "skymarshal-api-health"
    Environment = var.environment
  }
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "api" {
  name        = "skymarshal-api-${var.environment}"
  description = "REST API for SkyMarshal AgentCore Runtime with Async Polling"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway Resource - /api
resource "aws_api_gateway_resource" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "api"
}

# API Gateway Resource - /api/v1
resource "aws_api_gateway_resource" "v1" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.api.id
  path_part   = "v1"
}

# API Gateway Resource - /api/v1/invoke
resource "aws_api_gateway_resource" "invoke" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "invoke"
}

# API Gateway Resource - /api/v1/status
resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "status"
}

# API Gateway Resource - /api/v1/status/{request_id}
resource "aws_api_gateway_resource" "status_request_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.status.id
  path_part   = "{request_id}"
}

# API Gateway Resource - /api/v1/health
resource "aws_api_gateway_resource" "health" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.v1.id
  path_part   = "health"
}

# API Gateway Method - POST /api/v1/invoke
resource "aws_api_gateway_method" "invoke_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.invoke.id
  http_method   = "POST"
  authorization = "NONE"
}

# API Gateway Method - OPTIONS /api/v1/invoke (CORS)
resource "aws_api_gateway_method" "invoke_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.invoke.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# API Gateway Method - GET /api/v1/status/{request_id}
resource "aws_api_gateway_method" "status_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.status_request_id.id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway Method - OPTIONS /api/v1/status/{request_id} (CORS)
resource "aws_api_gateway_method" "status_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.status_request_id.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# API Gateway Method - GET /api/v1/health
resource "aws_api_gateway_method" "health_get" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "GET"
  authorization = "NONE"
}

# API Gateway Method - OPTIONS /api/v1/health (CORS)
resource "aws_api_gateway_method" "health_options" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.health.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

# CORS Integration - OPTIONS /api/v1/invoke
resource "aws_api_gateway_integration" "invoke_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method = aws_api_gateway_method.invoke_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "invoke_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method = aws_api_gateway_method.invoke_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "invoke_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.invoke.id
  http_method = aws_api_gateway_method.invoke_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# CORS Integration - OPTIONS /api/v1/status/{request_id}
resource "aws_api_gateway_integration" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_request_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_request_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "status_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.status_request_id.id
  http_method = aws_api_gateway_method.status_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# CORS Integration - OPTIONS /api/v1/health
resource "aws_api_gateway_integration" "health_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options.http_method
  type        = "MOCK"
  
  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "health_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "health_options" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.health.id
  http_method = aws_api_gateway_method.health_options.http_method
  status_code = "200"
  
  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Lambda Integrations
resource "aws_api_gateway_integration" "invoke_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.invoke.id
  http_method             = aws_api_gateway_method.invoke_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.invoke_handler.invoke_arn
}

resource "aws_api_gateway_integration" "status_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.status_request_id.id
  http_method             = aws_api_gateway_method.status_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.invoke_handler.invoke_arn
}

resource "aws_api_gateway_integration" "health_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.health.id
  http_method             = aws_api_gateway_method.health_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.health_handler.invoke_arn
}

# Lambda Permissions
resource "aws_lambda_permission" "invoke_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.invoke_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "health_apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.health_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id

  depends_on = [
    aws_api_gateway_integration.invoke_lambda,
    aws_api_gateway_integration.status_lambda,
    aws_api_gateway_integration.health_lambda
  ]

  lifecycle {
    create_before_destroy = true
  }
}

# API Gateway Stage
resource "aws_api_gateway_stage" "api" {
  deployment_id = aws_api_gateway_deployment.api.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = var.environment
}

# Outputs
output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_stage.api.invoke_url}/api/v1"
}

output "invoke_url" {
  description = "Full invoke endpoint URL"
  value       = "${aws_api_gateway_stage.api.invoke_url}/api/v1/invoke"
}

output "status_url" {
  description = "Status check endpoint URL (append request_id)"
  value       = "${aws_api_gateway_stage.api.invoke_url}/api/v1/status"
}

output "health_url" {
  description = "Health check endpoint URL"
  value       = "${aws_api_gateway_stage.api.invoke_url}/api/v1/health"
}

output "dynamodb_sessions_table" {
  description = "DynamoDB table name for sessions"
  value       = aws_dynamodb_table.sessions.name
}

output "dynamodb_requests_table" {
  description = "DynamoDB table name for async requests"
  value       = aws_dynamodb_table.requests.name
}
