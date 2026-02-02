"""
Request validation module for API endpoints.

This module provides validation and sanitization for incoming API requests
to ensure data integrity and security before processing.
"""

import re
import uuid
from typing import Optional, Tuple


class RequestValidator:
    """
    Validates API requests before processing.
    
    This class provides static methods for validating request payloads,
    sanitizing user inputs, and ensuring data meets security requirements.
    """
    
    MAX_PROMPT_LENGTH = 10000
    MIN_PROMPT_LENGTH = 10
    
    @staticmethod
    def validate_invoke_request(body: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate invocation request.
        
        Checks that the request body contains all required fields with valid
        values according to the API specification.
        
        Args:
            body: Request body dictionary containing prompt and optional parameters
            
        Returns:
            Tuple of (is_valid, error_message) where is_valid is True if the
            request is valid, False otherwise. error_message contains details
            if validation fails, None if validation succeeds.
            
        Examples:
            >>> RequestValidator.validate_invoke_request({"prompt": "Flight delayed"})
            (True, None)
            
            >>> RequestValidator.validate_invoke_request({})
            (False, "Missing required field: prompt")
        """
        # Check for required prompt field
        if "prompt" not in body:
            return False, "Missing required field: prompt"
        
        prompt = body.get("prompt")
        
        # Validate prompt is a string
        if not isinstance(prompt, str):
            return False, "Field 'prompt' must be a string"
        
        # Validate prompt length
        if len(prompt) < RequestValidator.MIN_PROMPT_LENGTH:
            return False, f"Prompt must be at least {RequestValidator.MIN_PROMPT_LENGTH} characters"
        
        if len(prompt) > RequestValidator.MAX_PROMPT_LENGTH:
            return False, f"Prompt must not exceed {RequestValidator.MAX_PROMPT_LENGTH} characters"
        
        # Validate optional session_id if provided
        if "session_id" in body and body["session_id"] is not None:
            session_id = body["session_id"]
            if not isinstance(session_id, str):
                return False, "Field 'session_id' must be a string"
            
            if not RequestValidator.validate_session_id(session_id):
                return False, "Field 'session_id' must be a valid UUID v4"
        
        # Validate optional streaming flag if provided
        if "streaming" in body:
            streaming = body["streaming"]
            if not isinstance(streaming, bool):
                return False, "Field 'streaming' must be a boolean"
        
        return True, None
    
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        """
        Sanitize prompt to prevent injection attacks.
        
        Removes potentially dangerous characters that could be used for
        injection attacks or XSS vulnerabilities.
        
        Args:
            prompt: Raw prompt string from user input
            
        Returns:
            Sanitized prompt with dangerous characters removed
            
        Examples:
            >>> RequestValidator.sanitize_prompt("Flight <script>alert('xss')</script> delayed")
            'Flight scriptalert(xss)/script delayed'
            
            >>> RequestValidator.sanitize_prompt("Normal prompt text")
            'Normal prompt text'
        """
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>{}]', '', prompt)
        
        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()
        
        return sanitized
    
    @staticmethod
    def validate_session_id(session_id: str) -> bool:
        """
        Validate session ID format (UUID v4).
        
        Ensures the session ID is a properly formatted UUID version 4 string.
        
        Args:
            session_id: Session identifier to validate
            
        Returns:
            True if session_id is a valid UUID v4, False otherwise
            
        Examples:
            >>> RequestValidator.validate_session_id("550e8400-e29b-41d4-a716-446655440000")
            True
            
            >>> RequestValidator.validate_session_id("invalid-uuid")
            False
        """
        try:
            parsed_uuid = uuid.UUID(session_id, version=4)
            # Ensure the string representation matches (handles case sensitivity)
            return str(parsed_uuid) == session_id.lower()
        except (ValueError, AttributeError):
            return False
