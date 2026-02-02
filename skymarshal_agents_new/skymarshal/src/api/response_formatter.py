"""
Response formatting module for API endpoints.
"""

import json
from datetime import datetime
from typing import Any, Dict


class ResponseFormatter:
    """Formats agent responses for API Gateway."""
    
    @staticmethod
    def format_success_response(
        data: Dict[str, Any],
        request_id: str,
        execution_time_ms: int,
        session_id: str = None
    ) -> dict:
        """Format successful response for API Gateway."""
        body = {
            "status": "success",
            "request_id": request_id,
            "execution_time_ms": execution_time_ms,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **data
        }
        
        if session_id:
            body["session_id"] = session_id
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
            },
            "body": json.dumps(body)
        }
    
    @staticmethod
    def format_error_response(
        error_code: str,
        error_message: str,
        request_id: str,
        status_code: int = 500,
        details: Dict[str, Any] = None
    ) -> dict:
        """Format error response for API Gateway."""
        body = {
            "status": "error",
            "request_id": request_id,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if details:
            body["details"] = details
        
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
            },
            "body": json.dumps(body)
        }
    
    @staticmethod
    def format_streaming_chunk(chunk: dict) -> str:
        """Format streaming response chunk as SSE."""
        data = json.dumps(chunk)
        return f"data: {data}\n\n"
