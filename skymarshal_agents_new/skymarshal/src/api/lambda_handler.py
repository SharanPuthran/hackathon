"""
Lambda handler for AgentCore Runtime invocation.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict

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
RESPONSE_MODE = os.getenv('RESPONSE_MODE', 'buffered')


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for AgentCore Runtime invocation.
    
    Args:
        event: API Gateway proxy event
        context: Lambda context object
        
    Returns:
        API Gateway proxy response
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    ws_client = None
    
    try:
        # Parse request body
        try:
            body = json.loads(event.get('body', '{}'))
        except json.JSONDecodeError:
            return ResponseFormatter.format_error_response(
                error_code="INVALID_JSON",
                error_message="Request body must be valid JSON",
                request_id=request_id,
                status_code=400
            )
        
        # Validate request
        is_valid, error_msg = RequestValidator.validate_invoke_request(body)
        if not is_valid:
            return ResponseFormatter.format_error_response(
                error_code="INVALID_REQUEST",
                error_message=error_msg,
                request_id=request_id,
                status_code=400
            )
        
        # Extract parameters
        prompt = RequestValidator.sanitize_prompt(body['prompt'])
        session_id = body.get('session_id')
        
        # Initialize WebSocket client
        ws_client = AgentCoreWebSocketClient(AGENTCORE_RUNTIME_ARN, AWS_REGION)
        
        # Invoke AgentCore Runtime
        logger.info(f"Invoking AgentCore Runtime for request {request_id}")
        
        # Use shorter timeout to stay under API Gateway 29-second limit
        # This gives us 25 seconds for agent execution + 4 seconds for overhead
        response = asyncio.run(
            ws_client.invoke_with_retry(
                prompt=prompt,
                session_id=session_id,
                timeout=25,  # 25 seconds to avoid API Gateway timeout
                max_retries=0  # No retries to save time
            )
        )
        
        # Calculate execution time
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
        
        # Format and return response
        return ResponseFormatter.format_success_response(
            data=response,
            request_id=request_id,
            execution_time_ms=execution_time_ms,
            session_id=session_id
        )
    
    except TimeoutError:
        execution_time_ms = int((time.time() - start_time) * 1000)
        return ResponseFormatter.format_error_response(
            error_code="TIMEOUT",
            error_message="Agent analysis is taking longer than expected. This is normal for complex disruptions. Please try again - the system will be faster on subsequent requests.",
            request_id=request_id,
            status_code=504,
            details={
                "execution_time_ms": execution_time_ms,
                "note": "First-time analysis can take 30-90 seconds. Subsequent requests with the same session_id will be faster."
            }
        )
    
    except ConnectionError as e:
        return ResponseFormatter.format_error_response(
            error_code="CONNECTION_FAILED",
            error_message=f"Failed to connect to AgentCore Runtime: {str(e)}",
            request_id=request_id,
            status_code=502
        )
    
    except Exception as e:
        logger.exception("Unexpected error during invocation")
        return ResponseFormatter.format_error_response(
            error_code="INTERNAL_ERROR",
            error_message="An unexpected error occurred",
            request_id=request_id,
            status_code=500,
            details={"error": str(e)}
        )
    
    finally:
        # Ensure WebSocket cleanup
        if ws_client:
            asyncio.run(ws_client.close())
