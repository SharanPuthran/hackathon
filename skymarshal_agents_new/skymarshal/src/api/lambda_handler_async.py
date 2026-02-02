"""
Lambda handler with async processing to avoid API Gateway timeouts.

This handler supports two modes:
1. Async invocation: Returns immediately with request_id, processes in background
2. Status check: Returns current status of a request

This completely solves the API Gateway 29-second timeout issue.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from decimal import Decimal
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from api.response_formatter import ResponseFormatter
from api.session_manager import SessionManager
from api.validation import RequestValidator
from api.websocket_client import AgentCoreWebSocketClient

# Configure logging
logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(__name__)

# Environment variables
AGENTCORE_RUNTIME_ARN = os.getenv('AGENTCORE_RUNTIME_ARN')
AWS_REGION = os.getenv('SKYMARSHAL_AWS_REGION') or os.getenv('AWS_REGION', 'us-east-1')
SESSION_TABLE_NAME = os.getenv('SESSION_TABLE_NAME', 'skymarshal-sessions')
REQUESTS_TABLE_NAME = os.getenv('REQUESTS_TABLE_NAME', 'skymarshal-requests')

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
lambda_client = boto3.client('lambda', region_name=AWS_REGION)


def convert_floats_to_decimal(obj: Any) -> Any:
    """
    Recursively convert float values to Decimal for DynamoDB compatibility.
    DynamoDB doesn't support Python float types directly.
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    return obj


def convert_decimal_to_float(obj: Any) -> Any:
    """
    Recursively convert Decimal values back to float for JSON serialization.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    return obj


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler with async processing support.
    
    Routes:
    - POST /invoke: Start async processing, return request_id immediately
    - GET /status/{request_id}: Check status of async request
    - Internal: Process request in background (invoked by itself)
    
    Args:
        event: Lambda event (API Gateway or direct invocation)
        context: Lambda context object
        
    Returns:
        API Gateway response or processing result
    """
    # Check if this is an internal processing invocation
    if event.get('action') == 'process':
        return process_request_async(event, context)
    
    # Handle API Gateway requests
    path = event.get('path', '')
    http_method = event.get('httpMethod', '')
    
    if path == '/api/v1/invoke' and http_method == 'POST':
        return handle_invoke_async(event, context)
    elif path.startswith('/api/v1/status/') and http_method == 'GET':
        request_id = path.split('/')[-1]
        return handle_status_check(request_id)
    else:
        return {
            'statusCode': 404,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Not found'})
        }


def handle_invoke_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle async invocation request.
    
    Returns immediately with request_id. Actual processing happens in background.
    
    Args:
        event: API Gateway event
        context: Lambda context
        
    Returns:
        202 Accepted response with request_id
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Parse and validate request
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return ResponseFormatter.format_error_response(
                error_code="INVALID_JSON",
                error_message="Request body must be valid JSON",
                request_id=request_id,
                status_code=400
            )
        
        is_valid, error_msg = RequestValidator.validate_invoke_request(body)
        if not is_valid:
            return ResponseFormatter.format_error_response(
                error_code="INVALID_REQUEST",
                error_message=error_msg,
                request_id=request_id,
                status_code=400
            )
        
        prompt = RequestValidator.sanitize_prompt(body['prompt'])
        session_id = body.get('session_id')
        
        # Store request in DynamoDB
        requests_table = dynamodb.Table(REQUESTS_TABLE_NAME)
        requests_table.put_item(
            Item={
                'request_id': request_id,
                'status': 'processing',
                'prompt': prompt,
                'session_id': session_id or '',
                'created_at': int(time.time()),
                'updated_at': int(time.time()),
                'ttl': int(time.time()) + 3600,  # 1 hour TTL
            }
        )
        
        # Invoke Lambda asynchronously to process in background
        lambda_client.invoke(
            FunctionName=context.function_name,
            InvocationType='Event',  # Async invocation
            Payload=json.dumps({
                'action': 'process',
                'request_id': request_id,
                'prompt': prompt,
                'session_id': session_id
            })
        )
        
        logger.info(f"Started async processing for request {request_id}")
        
        # Return immediately
        return {
            'statusCode': 202,  # Accepted
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'POST,OPTIONS'
            },
            'body': json.dumps({
                'status': 'accepted',
                'request_id': request_id,
                'message': 'Request accepted for processing. Poll /status/{request_id} for results.',
                'poll_url': f'/api/v1/status/{request_id}'
            })
        }
    
    except Exception as e:
        logger.exception("Error starting async processing")
        return ResponseFormatter.format_error_response(
            error_code="INTERNAL_ERROR",
            error_message="Failed to start processing",
            request_id=request_id,
            status_code=500,
            details={"error": str(e)}
        )


def handle_status_check(request_id: str) -> Dict[str, Any]:
    """
    Check status of an async request.
    
    Args:
        request_id: Request ID to check
        
    Returns:
        Current status and result (if complete)
    """
    try:
        requests_table = dynamodb.Table(REQUESTS_TABLE_NAME)
        response = requests_table.get_item(Key={'request_id': request_id})
        
        item = response.get('Item')
        if not item:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Request not found',
                    'request_id': request_id
                })
            }
        
        # Return current status
        status_response = {
            'request_id': request_id,
            'status': item['status'],
            'created_at': item.get('created_at'),
            'updated_at': item.get('updated_at')
        }
        
        # Include result if complete
        if item['status'] == 'complete':
            # Convert Decimals back to floats for JSON serialization
            assessment = item.get('assessment')
            if assessment:
                assessment = convert_decimal_to_float(assessment)
            status_response['assessment'] = assessment
            status_response['session_id'] = item.get('session_id')
            status_response['execution_time_ms'] = item.get('execution_time_ms')
        
        # Include error if failed
        if item['status'] == 'error':
            status_response['error'] = item.get('error', '')
            status_response['error_code'] = item.get('error_code', '')
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(status_response, default=str)
        }
    
    except Exception as e:
        logger.exception(f"Error checking status for {request_id}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Failed to check status',
                'request_id': request_id,
                'details': str(e)
            })
        }


def process_request_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process request asynchronously in background.
    
    This function is invoked by Lambda itself (async invocation).
    It can run for up to 15 minutes without timeout issues.
    
    Args:
        event: Processing event with request_id, prompt, session_id
        context: Lambda context
        
    Returns:
        Processing result (not returned to user, stored in DynamoDB)
    """
    request_id = event['request_id']
    prompt = event['prompt']
    session_id = event.get('session_id')
    start_time = time.time()
    
    ws_client = None
    requests_table = dynamodb.Table(REQUESTS_TABLE_NAME)
    
    try:
        logger.info(f"Processing request {request_id} in background")
        
        # Initialize WebSocket client
        ws_client = AgentCoreWebSocketClient(AGENTCORE_RUNTIME_ARN, AWS_REGION)
        
        # Invoke AgentCore Runtime (can take 2-5 minutes, no problem!)
        response = asyncio.run(
            ws_client.invoke_with_retry(
                prompt=prompt,
                session_id=session_id,
                timeout=600,  # 10 minutes - plenty of time!
                max_retries=2
            )
        )
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Save to session history
        try:
            session_manager = SessionManager(SESSION_TABLE_NAME, AWS_REGION)
            if not session_id:
                session_id = session_manager.create_session()
            
            session_manager.save_interaction(
                session_id=session_id,
                request_id=request_id,
                prompt=prompt,
                response=response,
                execution_time_ms=execution_time_ms,
                status="success"
            )
        except Exception as e:
            logger.warning(f"Failed to save session: {str(e)}")
        
        # Update request status to complete
        # Convert floats to Decimal for DynamoDB compatibility
        assessment_for_dynamo = convert_floats_to_decimal(response)
        
        requests_table.update_item(
            Key={'request_id': request_id},
            UpdateExpression='SET #status = :status, assessment = :assessment, session_id = :session_id, execution_time_ms = :exec_time, updated_at = :updated',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'complete',
                ':assessment': assessment_for_dynamo,
                ':session_id': session_id or '',
                ':exec_time': execution_time_ms,
                ':updated': int(time.time())
            }
        )
        
        logger.info(f"Request {request_id} completed in {execution_time_ms}ms")
        
        return {'status': 'success', 'request_id': request_id}
    
    except TimeoutError:
        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Request {request_id} timed out after {execution_time_ms}ms")
        
        # Update request status to error
        requests_table.update_item(
            Key={'request_id': request_id},
            UpdateExpression='SET #status = :status, #err = :err, error_code = :code, updated_at = :updated',
            ExpressionAttributeNames={'#status': 'status', '#err': 'error'},
            ExpressionAttributeValues={
                ':status': 'error',
                ':err': 'Agent execution exceeded timeout',
                ':code': 'TIMEOUT',
                ':updated': int(time.time())
            }
        )
        
        return {'status': 'error', 'request_id': request_id}
    
    except Exception as e:
        logger.exception(f"Error processing request {request_id}")
        
        # Update request status to error
        requests_table.update_item(
            Key={'request_id': request_id},
            UpdateExpression='SET #status = :status, #err = :err, error_code = :code, updated_at = :updated',
            ExpressionAttributeNames={'#status': 'status', '#err': 'error'},
            ExpressionAttributeValues={
                ':status': 'error',
                ':err': str(e),
                ':code': 'PROCESSING_ERROR',
                ':updated': int(time.time())
            }
        )
        
        return {'status': 'error', 'request_id': request_id}
    
    finally:
        if ws_client:
            asyncio.run(ws_client.close())
