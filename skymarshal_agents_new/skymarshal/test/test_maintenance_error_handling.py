"""
Unit tests for Maintenance Agent error handling.

Tests verify that:
1. Agent handles tool failures gracefully
2. Agent returns proper error responses
3. Agent handles agent execution errors
4. Agent validates required fields
5. Agent handles extraction validation errors
6. Agent provides helpful error messages
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from agents.maintenance.agent import analyze_maintenance
from agents.schemas import FlightInfo


def create_mock_llm_with_flight_info(flight_info):
    """Helper to create properly mocked LLM with structured output"""
    mock_llm = AsyncMock()
    mock_structured_llm = AsyncMock()
    
    # Create a proper async mock that returns the flight_info
    async def mock_ainvoke(*args, **kwargs):
        return flight_info
    
    mock_structured_llm.ainvoke = mock_ainvoke
    mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)
    return mock_llm


class TestMaintenanceErrorHandling:
    """Test suite for maintenance agent error handling"""

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_agent_execution_error(self, mock_create_agent):
        """Test error handling when agent execution fails"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Mock agent that raises error
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=Exception("Agent execution failed"))
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify error response
        assert result["status"] == "error"
        assert result["agent_name"] == "maintenance"
        assert "Agent execution failed" in result["reasoning"]
        assert result["confidence"] == 0.0
        assert "error" in result
        assert "error_type" in result
        assert result["extracted_flight_info"]["flight_number"] == "EY123"

    @pytest.mark.asyncio
    async def test_empty_user_prompt(self):
        """Test error handling with empty user prompt"""
        # Mock LLM
        mock_llm = AsyncMock()

        # Test payload with empty prompt
        payload = {
            "user_prompt": "",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify error response
        assert result["status"] == "error"
        assert result["agent_name"] == "maintenance"
        assert "No user prompt provided" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_missing_phase(self):
        """Test that missing phase defaults to 'initial'"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Mock agent response
        with patch('agents.maintenance.agent.create_agent') as mock_create_agent:
            mock_agent = AsyncMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [Mock(content="Analysis complete")]
            })
            mock_create_agent.return_value = mock_agent

            # Test payload without phase
            payload = {
                "user_prompt": "Flight EY123 on January 20th had a mechanical failure"
            }

            # Execute
            result = await analyze_maintenance(payload, mock_llm, [])

            # Verify it defaults to initial phase
            assert result["status"] == "success"

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_response_has_required_fields(self, mock_create_agent):
        """Test that response always has required fields"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Mock agent response with minimal content
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [Mock(content="Minimal response")]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify required fields present
        assert "agent_name" in result
        assert result["agent_name"] == "maintenance"
        assert "extracted_flight_info" in result
        assert "timestamp" in result
        assert "status" in result
        assert "binding_constraints" in result  # Safety agent must have this

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_binding_constraints_always_present(self, mock_create_agent):
        """Test that binding_constraints field is always present for safety agent"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Mock agent response without binding_constraints
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                Mock(content={
                    "agent_name": "maintenance",
                    "recommendation": "Aircraft airworthy",
                    "confidence": 0.9
                    # Note: no binding_constraints field
                })
            ]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify binding_constraints added even if not in agent response
        assert "binding_constraints" in result
        assert isinstance(result["binding_constraints"], list)

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_tool_error_propagation(self, mock_create_agent):
        """Test that tool errors are handled by agent"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Mock agent response indicating tool failure
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                Mock(content={
                    "agent_name": "maintenance",
                    "recommendation": "CANNOT_PROCEED",
                    "confidence": 0.0,
                    "binding_constraints": [],
                    "reasoning": "Tool query_flight failed: DynamoDB error",
                    "data_sources": []
                })
            ]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify tool error reflected in response
        assert result["recommendation"] == "CANNOT_PROCEED"
        assert "Tool query_flight failed" in result["reasoning"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_structured_output_extraction_variations(self, mock_create_agent):
        """Test handling of different agent response formats"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Test Case 1: Dict content
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                Mock(content={
                    "agent_name": "maintenance",
                    "recommendation": "Aircraft airworthy",
                    "confidence": 0.9
                })
            ]
        })
        mock_create_agent.return_value = mock_agent

        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        result = await analyze_maintenance(payload, mock_llm, [])
        assert result["status"] == "success"
        assert result["recommendation"] == "Aircraft airworthy"

        # Test Case 2: String content
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [Mock(content="Aircraft requires inspection")]
        })

        result = await analyze_maintenance(payload, mock_llm, [])
        assert result["status"] == "success"
        assert "Aircraft requires inspection" in result["recommendation"]

    @pytest.mark.asyncio
    async def test_none_payload(self):
        """Test error handling with None payload"""
        # Mock LLM
        mock_llm = AsyncMock()

        # Execute with None payload - should return error response, not raise
        result = await analyze_maintenance(None, mock_llm, [])
        assert result["status"] == "error"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_extraction_validation_empty_flight_number(self):
        """Test error handling when extraction succeeds but flight_number is empty"""
        # Mock LLM structured output that returns FlightInfo with validation bypass
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        
        # Create FlightInfo with empty flight_number by bypassing validation
        flight_info = FlightInfo.model_construct(
            flight_number="",  # Empty flight number
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        
        # Create proper async mock
        async def mock_ainvoke(*args, **kwargs):
            return flight_info
        
        mock_structured_llm.ainvoke = mock_ainvoke
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Test payload
        payload = {
            "user_prompt": "Flight on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify error response
        assert result["status"] == "error"
        assert result["agent_name"] == "maintenance"
        assert "Could not extract flight number" in result["reasoning"]
        assert "EY123" in result["reasoning"]  # Should mention format
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_extraction_validation_empty_date(self):
        """Test error handling when extraction succeeds but date is empty"""
        # Mock LLM structured output that returns FlightInfo with validation bypass
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        
        # Create FlightInfo with empty date by bypassing validation
        flight_info = FlightInfo.model_construct(
            flight_number="EY123",
            date="",  # Empty date
            disruption_event="mechanical failure"
        )
        
        # Create proper async mock
        async def mock_ainvoke(*args, **kwargs):
            return flight_info
        
        mock_structured_llm.ainvoke = mock_ainvoke
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify error response
        assert result["status"] == "error"
        assert result["agent_name"] == "maintenance"
        assert "Could not extract date" in result["reasoning"]
        assert result["confidence"] == 0.0
        assert result["extracted_flight_info"]["flight_number"] == "EY123"

    @pytest.mark.asyncio
    async def test_extraction_error_types(self):
        """Test different extraction error types provide helpful messages"""
        # Test Case 1: Validation error
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        
        async def mock_ainvoke_validation_error(*args, **kwargs):
            raise Exception("Validation error: invalid format")
        
        mock_structured_llm.ainvoke = mock_ainvoke_validation_error
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        result = await analyze_maintenance(payload, mock_llm, [])
        assert result["status"] == "error"
        assert "validate" in result["reasoning"].lower()
        assert "flight number format" in result["reasoning"]

        # Test Case 2: Timeout error
        async def mock_ainvoke_timeout_error(*args, **kwargs):
            raise Exception("Timeout exceeded")
        
        mock_structured_llm.ainvoke = mock_ainvoke_timeout_error
        result = await analyze_maintenance(payload, mock_llm, [])
        assert result["status"] == "error"
        assert "timed out" in result["reasoning"].lower()

        # Test Case 3: Generic error
        async def mock_ainvoke_generic_error(*args, **kwargs):
            raise Exception("Unknown error")
        
        mock_structured_llm.ainvoke = mock_ainvoke_generic_error
        result = await analyze_maintenance(payload, mock_llm, [])
        assert result["status"] == "error"
        assert "Failed to extract flight information" in result["reasoning"]

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_agent_execution_timeout_error(self, mock_create_agent):
        """Test error handling when agent execution times out"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Mock agent that raises timeout error
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=Exception("Request timeout exceeded"))
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify timeout-specific error message
        assert result["status"] == "error"
        assert "timed out" in result["reasoning"].lower()
        assert "try again" in result["reasoning"].lower()

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_agent_execution_rate_limit_error(self, mock_create_agent):
        """Test error handling when rate limit is exceeded"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Mock agent that raises rate limit error
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=Exception("Rate limit exceeded"))
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify rate limit-specific error message
        assert result["status"] == "error"
        assert "rate limit" in result["reasoning"].lower()
        assert "wait" in result["reasoning"].lower()

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_agent_response_no_content_attribute(self, mock_create_agent):
        """Test handling when agent response has no content attribute"""
        # Mock LLM structured output
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm = create_mock_llm_with_flight_info(flight_info)

        # Mock agent response without content attribute
        mock_agent = AsyncMock()
        mock_message = Mock(spec=[])  # No content attribute
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [mock_message]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify default response created
        assert result["status"] == "success"
        assert result["agent_name"] == "maintenance"
        assert "recommendation" in result
        assert "binding_constraints" in result


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

if __name__ == '__main__':
    pytest.main([__file__, '-v'])

