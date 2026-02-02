"""
Lambda handler for AgentCore Runtime invocation with streaming support.

This handler uses Lambda response streaming to send agent responses
as they arrive, avoiding API Gateway timeout issues.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict
from awslambdaric.lambda_context import LambdaContext

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


def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Lambda handler with streaming support for AgentCore Runtime invocation.
    
    This handler streams responses using Server-Sent Events (SSE) format,
    allowing the frontend to receive agent responses as they complete.
    
    Args:
        event: Lambda Function URL event
        context: Lambda context object
        
    Returns:
        Streaming response with SSE format
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Check if streaming is supported (Lambda Function URL)
    is_streaming = hasattr(context, 'response_stream')
    
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
        
        # Use streaming if available, otherwise fall back to buffered
        if is_streaming:
            return _handle_streaming_request(
                prompt, session_id, request_id, start_time, context
            )
        else:
            return _handle_buffered_request(
                prompt, session_id, request_id, start_time
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


def _handle_buffered_request(
    prompt: str,
    session_id: str,
    request_id: str,
    start_time: float
) -> Dict[str, Any]:
    """
    Handle buffered (non-streaming) request.
    
    Returns complete response after all agents finish.
    """
    ws_client = None
    
    try:
        # Initialize WebSocket client
        ws_client = AgentCoreWebSocketClient(AGENTCORE_RUNTIME_ARN, AWS_REGION)
        
        # Invoke AgentCore Runtime
        logger.info(f"Invoking AgentCore Runtime for request {request_id}")
        response = asyncio.run(
            ws_client.invoke_with_retry(
                prompt=prompt,
                session_id=session_id,
                timeout=300,  # Full timeout for buffered mode
                max_retries=2
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
            error_message="Agent analysis exceeded timeout",
            request_id=request_id,
            status_code=504,
            details={"execution_time_ms": execution_time_ms}
        )
    
    except ConnectionError as e:
        return ResponseFormatter.format_error_response(
            error_code="CONNECTION_FAILED",
            error_message=f"Failed to connect to AgentCore Runtime: {str(e)}",
            request_id=request_id,
            status_code=502
        )
    
    finally:
        if ws_client:
            asyncio.run(ws_client.close())


def _handle_streaming_request(
    prompt: str,
    session_id: str,
    request_id: str,
    start_time: float,
    context: LambdaContext
) -> None:
    """
    Handle streaming request using Lambda response streaming.
    
    Streams agent responses as they arrive using SSE format.
    """
    ws_client = None
    chunks = []
    
    try:
        # Get the response stream
        response_stream = context.response_stream
        
        # Send headers
        response_stream.write({
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "POST,OPTIONS"
            }
        })
        
        # Initialize WebSocket client
        ws_client = AgentCoreWebSocketClient(AGENTCORE_RUNTIME_ARN, AWS_REGION)
        
        # Create session if needed
        if not session_id:
            session_manager = SessionManager(SESSION_TABLE_NAME, AWS_REGION)
            session_id = session_manager.create_session()
        
        # Send initial metadata
        metadata = {
            "type": "metadata",
            "request_id": request_id,
            "session_id": session_id,
            "timestamp": time.time()
        }
        _write_sse_event(response_stream, metadata)
        
        # Stream agent responses
        async def stream_responses():
            async for chunk in ws_client.invoke(prompt, session_id, timeout=300):
                chunks.append(chunk)
                chunk_data = {
                    "type": "chunk",
                    "data": chunk
                }
                _write_sse_event(response_stream, chunk_data)
        
        # Run streaming
        asyncio.run(stream_responses())
        
        # Send completion message
        execution_time_ms = int((time.time() - start_time) * 1000)
        completion = {
            "type": "complete",
            "execution_time_ms": execution_time_ms,
            "chunk_count": len(chunks)
        }
        _write_sse_event(response_stream, completion)
        
        # Save to session history
        try:
            session_manager = SessionManager(SESSION_TABLE_NAME, AWS_REGION)
            session_manager.save_interaction(
                session_id=session_id,
                request_id=request_id,
                prompt=prompt,
                response={"chunks": chunks},
                execution_time_ms=execution_time_ms,
                status="success"
            )
        except Exception as e:
            logger.warning(f"Failed to save session: {str(e)}")
    
    except Exception as e:
        logger.exception("Error during streaming")
        error_data = {
            "type": "error",
            "error_code": "STREAMING_ERROR",
            "error_message": str(e)
        }
        _write_sse_event(response_stream, error_data)
    
    finally:
        if ws_client:
            asyncio.run(ws_client.close())


def _write_sse_event(stream, data: Dict[str, Any]) -> None:
    """
    Write a Server-Sent Event to the response stream.
    
    Args:
        stream: Lambda response stream
        data: Data to send as JSON
    """
    event_data = f"data: {json.dumps(data)}\n\n"
    stream.write(event_data.encode('utf-8'))
