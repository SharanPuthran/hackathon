"""
Unit tests for API data models.
"""

import pytest
from pydantic import ValidationError
from src.api.models import (
    InvokeRequest,
    InvokeResponse,
    ErrorResponse,
    SessionInteraction,
    SessionHistory,
    HealthCheckResponse
)


class TestInvokeRequest:
    """Test suite for InvokeRequest model."""
    
    def test_valid_request(self):
        """Test that valid request data is accepted."""
        data = {
            "prompt": "Flight AA123 delayed 3 hours due to weather"
        }
        request = InvokeRequest(**data)
        assert request.prompt == data["prompt"]
        assert request.session_id is None
        assert request.streaming is False
    
    def test_request_with_session_id(self):
        """Test request with valid session ID."""
        data = {
            "prompt": "Flight delayed",
            "session_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        request = InvokeRequest(**data)
        assert request.session_id == data["session_id"]
    
    def test_request_with_invalid_session_id(self):
        """Test that invalid session ID raises validation error."""
        data = {
            "prompt": "Flight delayed",
            "session_id": "invalid-uuid"
        }
        with pytest.raises(ValidationError) as exc_info:
            InvokeRequest(**data)
        assert "uuid" in str(exc_info.value).lower()
    
    def test_prompt_too_short(self):
        """Test that short prompts are rejected."""
        data = {"prompt": "Short"}
        with pytest.raises(ValidationError):
            InvokeRequest(**data)
    
    def test_prompt_sanitization(self):
        """Test that prompts are sanitized."""
        data = {"prompt": "Flight <script>alert('xss')</script> delayed"}
        request = InvokeRequest(**data)
        assert "<" not in request.prompt
        assert ">" not in request.prompt


class TestInvokeResponse:
    """Test suite for InvokeResponse model."""
    
    def test_valid_response(self):
        """Test that valid response data is accepted."""
        data = {
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "execution_time_ms": 5000,
            "assessment": {"result": "approved"},
            "final_decision": "approved"
        }
        response = InvokeResponse(**data)
        assert response.status == "success"
        assert response.request_id == data["request_id"]
        assert response.execution_time_ms == data["execution_time_ms"]


class TestErrorResponse:
    """Test suite for ErrorResponse model."""
    
    def test_valid_error_response(self):
        """Test that valid error response is created."""
        data = {
            "request_id": "550e8400-e29b-41d4-a716-446655440000",
            "error_code": "TIMEOUT",
            "error_message": "Request timed out"
        }
        response = ErrorResponse(**data)
        assert response.status == "error"
        assert response.error_code == data["error_code"]
        assert response.timestamp is not None


class TestHealthCheckResponse:
    """Test suite for HealthCheckResponse model."""
    
    def test_valid_health_response(self):
        """Test that valid health check response is created."""
        data = {
            "status": "healthy",
            "version": "0.1.0"
        }
        response = HealthCheckResponse(**data)
        assert response.status == data["status"]
        assert response.version == data["version"]
        assert response.timestamp is not None
