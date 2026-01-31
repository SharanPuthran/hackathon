"""
Unit Tests for Network Agent Error Handling

Feature: skymarshal-multi-round-orchestration
Task: 13.1 Update Network Agent
Validates: Requirements 2.3, 2.7

Tests that the Network agent handles errors gracefully and returns
appropriate failure responses when tools fail or data is missing.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone


class TestNetworkAgentErrorHandling:
    """Test Network agent error handling."""

    @pytest.mark.asyncio
    async def test_missing_user_prompt(self):
        """Test that agent handles missing user prompt gracefully."""
        from agents.network.agent import analyze_network
        
        # Create mock LLM
        mock_llm = Mock()
        
        # Payload without user_prompt
        payload = {}
        
        result = await analyze_network(payload, mock_llm, [])
        
        assert result["agent_name"] == "network"
        assert result["status"] == "error"
        assert "user_prompt" in result["error"].lower() or "prompt" in result["error"].lower()
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_empty_user_prompt(self):
        """Test that agent handles empty user prompt gracefully."""
        from agents.network.agent import analyze_network
        
        mock_llm = Mock()
        
        payload = {
            "user_prompt": "",
            "phase": "initial"
        }
        
        result = await analyze_network(payload, mock_llm, [])
        
        assert result["agent_name"] == "network"
        assert result["status"] == "error"
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_agent_execution_exception(self):
        """Test that agent handles execution exceptions gracefully."""
        from agents.network.agent import analyze_network
        
        # Create mock LLM that raises exception
        mock_llm = Mock()
        mock_llm.with_structured_output = Mock(side_effect=Exception("LLM error"))
        
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }
        
        result = await analyze_network(payload, mock_llm, [])
        
        assert result["agent_name"] == "network"
        assert result["status"] == "error"
        assert "error" in result
        assert result["confidence"] == 0.0
        assert "LLM error" in result["error"] or "error" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_timeout_response_format(self):
        """Test that timeout responses have correct format."""
        from agents.schemas import AgentResponse
        
        # Simulate timeout response
        response = AgentResponse(
            agent_name="network",
            recommendation="Unable to complete analysis",
            confidence=0.0,
            reasoning="Agent execution timed out after 30 seconds",
            data_sources=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="timeout",
            duration_seconds=30.0,
            error="Execution exceeded 30 second timeout"
        )
        
        assert response.agent_name == "network"
        assert response.status == "timeout"
        assert response.confidence == 0.0
        assert response.duration_seconds == 30.0
        assert "timeout" in response.error.lower()

    @pytest.mark.asyncio
    async def test_error_response_format(self):
        """Test that error responses have correct format."""
        from agents.schemas import AgentResponse
        
        # Simulate error response
        response = AgentResponse(
            agent_name="network",
            recommendation="Unable to complete analysis",
            confidence=0.0,
            reasoning="Failed to query flight data",
            data_sources=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="error",
            duration_seconds=1.5,
            error="DynamoDB query failed: Flight not found"
        )
        
        assert response.agent_name == "network"
        assert response.status == "error"
        assert response.confidence == 0.0
        assert "DynamoDB" in response.error or "query" in response.error.lower()


class TestNetworkToolErrorHandling:
    """Test Network agent tool error handling."""

    def test_query_flight_handles_boto3_error(self):
        """Test that query_flight handles boto3 errors gracefully."""
        from agents.network.agent import query_flight
        
        # Mock boto3 to raise exception
        with patch('agents.network.agent.boto3') as mock_boto3:
            mock_boto3.resource.side_effect = Exception("AWS connection error")
            
            result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})
            
            # Should return None on error, not raise exception
            assert result is None

    def test_query_aircraft_rotation_handles_boto3_error(self):
        """Test that query_aircraft_rotation handles boto3 errors gracefully."""
        from agents.network.agent import query_aircraft_rotation
        
        with patch('agents.network.agent.boto3') as mock_boto3:
            mock_boto3.resource.side_effect = Exception("AWS connection error")
            
            result = query_aircraft_rotation.invoke({
                "aircraft_registration": "A6-APX",
                "start_date": "2026-01-20",
                "end_date": "2026-01-21"
            })
            
            # Should return empty list on error, not raise exception
            assert result == []

    def test_query_flights_by_aircraft_handles_boto3_error(self):
        """Test that query_flights_by_aircraft handles boto3 errors gracefully."""
        from agents.network.agent import query_flights_by_aircraft
        
        with patch('agents.network.agent.boto3') as mock_boto3:
            mock_boto3.resource.side_effect = Exception("AWS connection error")
            
            result = query_flights_by_aircraft.invoke({"aircraft_registration": "A6-APX"})
            
            # Should return empty list on error, not raise exception
            assert result == []

    def test_query_aircraft_availability_handles_boto3_error(self):
        """Test that query_aircraft_availability handles boto3 errors gracefully."""
        from agents.network.agent import query_aircraft_availability
        
        with patch('agents.network.agent.boto3') as mock_boto3:
            mock_boto3.resource.side_effect = Exception("AWS connection error")
            
            result = query_aircraft_availability.invoke({
                "aircraft_registration": "A6-APX",
                "date": "2026-01-20"
            })
            
            # Should return None on error, not raise exception
            assert result is None

    def test_query_flight_not_found(self):
        """Test that query_flight returns None when flight not found."""
        from agents.network.agent import query_flight
        
        # Mock boto3 to return empty results
        with patch('agents.network.agent.boto3') as mock_boto3:
            mock_table = Mock()
            mock_table.query.return_value = {"Items": []}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})
            
            assert result is None

    def test_query_aircraft_rotation_empty(self):
        """Test that query_aircraft_rotation returns empty list when no flights found."""
        from agents.network.agent import query_aircraft_rotation
        
        with patch('agents.network.agent.boto3') as mock_boto3:
            mock_table = Mock()
            mock_table.query.return_value = {"Items": []}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result = query_aircraft_rotation.invoke({
                "aircraft_registration": "A6-XXX",
                "start_date": "2026-01-20",
                "end_date": "2026-01-21"
            })
            
            assert result == []


class TestNetworkAgentResponseValidation:
    """Test Network agent response validation."""

    def test_response_has_required_fields(self):
        """Test that agent response has all required fields."""
        from agents.schemas import AgentResponse
        
        response = AgentResponse(
            agent_name="network",
            recommendation="Network impact assessment",
            confidence=0.9,
            reasoning="Analysis complete",
            data_sources=["flights", "AircraftAvailability"],
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Verify all required fields are present
        assert hasattr(response, "agent_name")
        assert hasattr(response, "recommendation")
        assert hasattr(response, "confidence")
        assert hasattr(response, "reasoning")
        assert hasattr(response, "data_sources")
        assert hasattr(response, "timestamp")

    def test_response_confidence_range(self):
        """Test that confidence is within valid range."""
        from agents.schemas import AgentResponse
        from pydantic import ValidationError
        
        # Valid confidence values
        for conf in [0.0, 0.5, 1.0]:
            response = AgentResponse(
                agent_name="network",
                recommendation="Test",
                confidence=conf,
                reasoning="Test",
                data_sources=[],
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            assert response.confidence == conf
        
        # Invalid confidence values
        for conf in [-0.1, 1.1, 2.0]:
            with pytest.raises(ValidationError):
                AgentResponse(
                    agent_name="network",
                    recommendation="Test",
                    confidence=conf,
                    reasoning="Test",
                    data_sources=[],
                    timestamp=datetime.now(timezone.utc).isoformat()
                )

    def test_response_includes_duration(self):
        """Test that response can include duration_seconds."""
        from agents.schemas import AgentResponse
        
        response = AgentResponse(
            agent_name="network",
            recommendation="Network impact assessment",
            confidence=0.9,
            reasoning="Analysis complete",
            data_sources=["flights"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=3.5
        )
        
        assert response.duration_seconds == 3.5

    def test_response_includes_error_field(self):
        """Test that error responses include error field."""
        from agents.schemas import AgentResponse
        
        response = AgentResponse(
            agent_name="network",
            recommendation="Unable to complete analysis",
            confidence=0.0,
            reasoning="Tool failure",
            data_sources=[],
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="error",
            error="DynamoDB connection failed"
        )
        
        assert response.status == "error"
        assert response.error == "DynamoDB connection failed"
