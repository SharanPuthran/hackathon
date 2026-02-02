"""
Data models for API requests and responses.

This module defines Pydantic models for validating and serializing
API request and response payloads.
"""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class InvokeRequest(BaseModel):
    """
    Request model for agent invocation.
    
    Attributes:
        prompt: Disruption description in natural language
        session_id: Optional session ID for multi-turn conversations
        streaming: Enable streaming responses (SSE)
    """
    
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=10000,
        description="Disruption description in natural language"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID for multi-turn conversations"
    )
    streaming: bool = Field(
        False,
        description="Enable streaming responses (SSE)"
    )
    
    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session_id is a valid UUID v4."""
        if v is not None:
            try:
                uuid.UUID(v, version=4)
            except ValueError:
                raise ValueError('session_id must be a valid UUID v4')
        return v
    
    @field_validator('prompt')
    @classmethod
    def sanitize_prompt(cls, v: str) -> str:
        """Sanitize prompt by removing potentially dangerous characters."""
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>{}]', '', v)
        return sanitized.strip()


class AgentAssessment(BaseModel):
    """
    Individual agent assessment.
    
    Attributes:
        agent_name: Name of the agent
        status: Assessment status (approved, rejected, conditional)
        confidence: Confidence score between 0.0 and 1.0
        reasoning: Explanation of the assessment
        constraints: List of constraints identified
        recommendations: List of recommendations
    """
    
    agent_name: str
    status: str  # "approved" | "rejected" | "conditional"
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    constraints: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class InvokeResponse(BaseModel):
    """
    Response model for successful invocation.
    
    Attributes:
        status: Response status (always "success" for this model)
        request_id: Unique request identifier
        session_id: Session identifier if provided
        execution_time_ms: Execution duration in milliseconds
        assessment: Complete disruption assessment
        safety_phase: Safety agents results
        business_phase: Business agents results
        final_decision: Overall decision
        recommendations: Prioritized recovery recommendations
        metadata: Additional metadata
    """
    
    status: str = "success"
    request_id: str
    session_id: Optional[str] = None
    execution_time_ms: int
    
    assessment: Dict[str, Any] = Field(
        ...,
        description="Complete disruption assessment"
    )
    
    safety_phase: Dict[str, Any] = Field(
        default_factory=dict,
        description="Safety agents results (crew, maintenance, regulatory)"
    )
    
    business_phase: Dict[str, Any] = Field(
        default_factory=dict,
        description="Business agents results (network, guest, cargo, finance)"
    )
    
    final_decision: str = Field(
        ...,
        description="Overall decision: approved | rejected | conditional"
    )
    
    recommendations: List[str] = Field(
        default_factory=list,
        description="Prioritized recovery recommendations"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (timestamps, versions, etc.)"
    )


class ErrorResponse(BaseModel):
    """
    Response model for errors.
    
    Attributes:
        status: Response status (always "error" for this model)
        request_id: Unique request identifier
        error_code: Error code identifier
        error_message: Human-readable error message
        details: Optional additional error details
        timestamp: ISO 8601 timestamp of the error
    """
    
    status: str = "error"
    request_id: str
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class SessionInteraction(BaseModel):
    """
    Single interaction within a session.
    
    Attributes:
        session_id: Session identifier
        request_id: Request identifier
        timestamp: Unix timestamp in milliseconds
        prompt: User prompt
        response: Agent response
        status: Interaction status
        execution_time_ms: Execution duration
        error_message: Optional error message
    """
    
    session_id: str
    request_id: str
    timestamp: int  # Unix timestamp in milliseconds
    prompt: str
    response: Dict[str, Any]
    status: str
    execution_time_ms: int
    error_message: Optional[str] = None


class SessionHistory(BaseModel):
    """
    Complete session history.
    
    Attributes:
        session_id: Session identifier
        created_at: Unix timestamp when session was created
        last_interaction_at: Unix timestamp of last interaction
        interaction_count: Number of interactions in session
        interactions: List of interactions
    """
    
    session_id: str
    created_at: int
    last_interaction_at: int
    interaction_count: int
    interactions: List[SessionInteraction]


class HealthCheckResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    Attributes:
        status: Health status (healthy, degraded, unhealthy)
        version: API version
        timestamp: ISO 8601 timestamp
        dependencies: Status of dependencies
    """
    
    status: str  # "healthy" | "degraded" | "unhealthy"
    version: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of dependencies (agentcore, dynamodb, etc.)"
    )
