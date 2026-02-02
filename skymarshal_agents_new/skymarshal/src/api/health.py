"""
Health check endpoint handler.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Environment variables
AWS_REGION = os.getenv('SKYMARSHAL_AWS_REGION') or os.getenv('AWS_REGION', 'us-east-1')
SESSION_TABLE_NAME = os.getenv('SESSION_TABLE_NAME', 'skymarshal-sessions')
AGENTCORE_RUNTIME_ARN = os.getenv('AGENTCORE_RUNTIME_ARN')


def health_check_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Health check endpoint handler.
    
    Returns system health status without requiring authentication.
    
    Args:
        event: API Gateway proxy event
        context: Lambda context object
        
    Returns:
        API Gateway proxy response with health status
    """
    health_status = "healthy"
    dependencies = {}
    
    # Check DynamoDB connectivity
    try:
        dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
        table = dynamodb.Table(SESSION_TABLE_NAME)
        table.load()
        dependencies["dynamodb"] = "healthy"
    except ClientError as e:
        logger.error(f"DynamoDB health check failed: {str(e)}")
        dependencies["dynamodb"] = "unhealthy"
        health_status = "degraded"
    except Exception as e:
        logger.error(f"DynamoDB health check error: {str(e)}")
        dependencies["dynamodb"] = "unknown"
        health_status = "degraded"
    
    # Check AgentCore Runtime connectivity (basic check)
    try:
        if AGENTCORE_RUNTIME_ARN:
            client = boto3.client('bedrock-agentcore', region_name=AWS_REGION)
            # Just verify we can create a client
            dependencies["agentcore"] = "healthy"
        else:
            dependencies["agentcore"] = "not_configured"
            health_status = "degraded"
    except Exception as e:
        logger.error(f"AgentCore health check error: {str(e)}")
        dependencies["agentcore"] = "unknown"
        health_status = "degraded"
    
    # Determine overall status code
    status_code = 200 if health_status == "healthy" else 503
    
    # Build response
    body = {
        "status": health_status,
        "version": "0.1.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": dependencies
    }
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }
