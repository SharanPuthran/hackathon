"""
Unit tests for API validation module.
"""

import pytest
from src.api.validation import RequestValidator


class TestRequestValidator:
    """Test suite for RequestValidator class."""
    
    def test_validate_invoke_request_valid(self):
        """Test that valid requests pass validation."""
        body = {
            "prompt": "Flight AA123 delayed 3 hours due to weather"
        }
        is_valid, error = RequestValidator.validate_invoke_request(body)
        assert is_valid is True
        assert error is None
    
    def test_validate_invoke_request_missing_prompt(self):
        """Test that requests without prompt are rejected."""
        body = {"session_id": "550e8400-e29b-41d4-a716-446655440000"}
        is_valid, error = RequestValidator.validate_invoke_request(body)
        assert is_valid is False
        assert "prompt" in error.lower()
    
    def test_validate_invoke_request_prompt_too_short(self):
        """Test that prompts below minimum length are rejected."""
        body = {"prompt": "Short"}
        is_valid, error = RequestValidator.validate_invoke_request(body)
        assert is_valid is False
        assert "at least" in error.lower()
    
    def test_validate_invoke_request_prompt_too_long(self):
        """Test that prompts exceeding maximum length are rejected."""
        body = {"prompt": "x" * 10001}
        is_valid, error = RequestValidator.validate_invoke_request(body)
        assert is_valid is False
        assert "exceed" in error.lower()
    
    def test_validate_invoke_request_invalid_session_id(self):
        """Test that invalid session IDs are rejected."""
        body = {
            "prompt": "Flight delayed",
            "session_id": "invalid-uuid"
        }
        is_valid, error = RequestValidator.validate_invoke_request(body)
        assert is_valid is False
        assert "uuid" in error.lower()
    
    def test_sanitize_prompt_removes_special_chars(self):
        """Test that special characters are removed from prompts."""
        prompt = "Flight <script>alert('xss')</script> delayed"
        sanitized = RequestValidator.sanitize_prompt(prompt)
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert "Flight" in sanitized
        assert "delayed" in sanitized
    
    def test_sanitize_prompt_removes_braces(self):
        """Test that braces are removed from prompts."""
        prompt = "Flight {injection} delayed"
        sanitized = RequestValidator.sanitize_prompt(prompt)
        assert "{" not in sanitized
        assert "}" not in sanitized
    
    def test_validate_session_id_valid_uuid(self):
        """Test that valid UUID v4 is accepted."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        assert RequestValidator.validate_session_id(session_id) is True
    
    def test_validate_session_id_invalid_uuid(self):
        """Test that invalid UUID is rejected."""
        session_id = "invalid-uuid"
        assert RequestValidator.validate_session_id(session_id) is False
    
    def test_validate_session_id_empty_string(self):
        """Test that empty string is rejected."""
        session_id = ""
        assert RequestValidator.validate_session_id(session_id) is False
