"""
Unit tests for Guest Experience Agent error handling.

Tests verify that:
1. Agent handles DynamoDB query failures gracefully
2. Agent handles missing data appropriately
3. Agent returns proper error responses
4. Agent logs errors for debugging
5. Agent continues execution when possible
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents.guest_experience.agent import (
    analyze_guest_experience,
    query_flight,
    query_bookings_by_flight,
    query_passenger,
)


class TestDynamoDBErrorHandling:
    """Test DynamoDB query error handling."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_flight_dynamodb_error(self, mock_dynamodb):
        """Test handling of DynamoDB errors in flight query."""
        mock_table = Mock()
        mock_table.query.side_effect = Exception("DynamoDB connection failed")
        mock_dynamodb.Table.return_value = mock_table

        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Should return None instead of raising exception
        assert result is None

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_bookings_dynamodb_error(self, mock_dynamodb):
        """Test handling of DynamoDB errors in bookings query."""
        mock_table = Mock()
        mock_table.query.side_effect = Exception("Table not found")
        mock_dynamodb.Table.return_value = mock_table

        result = query_bookings_by_flight.invoke({"flight_id": "EY123-20260120"})

        # Should return empty list instead of raising exception
        assert result == []

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_passenger_dynamodb_error(self, mock_dynamodb):
        """Test handling of DynamoDB errors in passenger query."""
        mock_table = Mock()
        mock_table.get_item.side_effect = Exception("Access denied")
        mock_dynamodb.Table.return_value = mock_table

        result = query_passenger.invoke({"passenger_id": "PAX001"})

        # Should return None instead of raising exception
        assert result is None


class TestMissingDataHandling:
    """Test handling of missing data scenarios."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_flight_not_found(self, mock_dynamodb):
        """Test handling when flight is not found."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table

        result = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})

        assert result is None

    @patch("agents.guest_experience.agent.dynamodb")
    def test_no_bookings_for_flight(self, mock_dynamodb):
        """Test handling when no bookings exist for flight."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table

        result = query_bookings_by_flight.invoke({"flight_id": "EY123-20260120"})

        assert result == []
        assert isinstance(result, list)

    @patch("agents.guest_experience.agent.dynamodb")
    def test_passenger_not_found(self, mock_dynamodb):
        """Test handling when passenger is not found."""
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_dynamodb.Table.return_value = mock_table

        result = query_passenger.invoke({"passenger_id": "PAX999"})

        assert result is None


class TestAgentErrorHandling:
    """Test agent-level error handling."""

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_agent_creation_error(self, mock_create_agent):
        """Test handling of agent creation errors."""
        mock_create_agent.side_effect = Exception("Failed to create agent")

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Should return error response
        assert result["status"] == "FAILURE"
        assert result["agent"] == "guest_experience"
        assert "error" in result
        assert "Failed to create agent" in result["error"]

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_agent_invocation_error(self, mock_create_agent):
        """Test handling of agent invocation errors."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("Agent invocation failed")
        mock_create_agent.return_value = mock_agent

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Should return error response
        assert result["status"] == "FAILURE"
        assert result["agent"] == "guest_experience"
        assert "Agent invocation failed" in result["error"]

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_agent_timeout_handling(self, mock_create_agent):
        """Test handling of agent timeout."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = TimeoutError("Agent execution timed out")
        mock_create_agent.return_value = mock_agent

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Should return error response
        assert result["status"] == "FAILURE"
        assert "error" in result


class TestErrorResponseFormat:
    """Test error response format consistency."""

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_error_response_structure(self, mock_create_agent):
        """Test that error responses have consistent structure."""
        mock_create_agent.side_effect = Exception("Test error")

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Verify required fields in error response
        assert "agent" in result
        assert result["agent"] == "guest_experience"
        assert "category" in result
        assert result["category"] == "business"
        assert "status" in result
        assert result["status"] == "FAILURE"
        assert "assessment" in result
        assert result["assessment"] == "CANNOT_PROCEED"
        assert "failure_reason" in result
        assert "error" in result
        assert "error_type" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_error_includes_exception_type(self, mock_create_agent):
        """Test that error response includes exception type."""
        mock_create_agent.side_effect = ValueError("Invalid input")

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        assert result["error_type"] == "ValueError"
        assert "Invalid input" in result["error"]


class TestLogging:
    """Test error logging."""

    @patch("agents.guest_experience.agent.logger")
    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_error_logging(self, mock_dynamodb, mock_logger):
        """Test that query errors are logged."""
        mock_table = Mock()
        mock_table.query.side_effect = Exception("Query failed")
        mock_dynamodb.Table.return_value = mock_table

        query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Verify error was logged
        assert mock_logger.error.called
        error_message = mock_logger.error.call_args[0][0]
        assert "EY123" in error_message
        assert "2026-01-20" in error_message

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.logger")
    @patch("agents.guest_experience.agent.create_agent")
    async def test_agent_error_logging(self, mock_create_agent, mock_logger):
        """Test that agent errors are logged."""
        mock_create_agent.side_effect = Exception("Agent creation failed")

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        await analyze_guest_experience(payload, Mock(), [])

        # Verify error was logged
        assert mock_logger.error.called
        assert mock_logger.exception.called


class TestPartialDataHandling:
    """Test handling of partial or incomplete data."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_incomplete_flight_data(self, mock_dynamodb):
        """Test handling of incomplete flight data."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "flight_id": "EY123-20260120",
                    "flight_number": "EY123",
                    # Missing scheduled_departure and other fields
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Should still return the partial data
        assert result is not None
        assert result["flight_id"] == "EY123-20260120"

    @patch("agents.guest_experience.agent.dynamodb")
    def test_incomplete_booking_data(self, mock_dynamodb):
        """Test handling of incomplete booking data."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "booking_id": "BKG001",
                    # Missing passenger_id and other fields
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_bookings_by_flight.invoke({"flight_id": "EY123-20260120"})

        # Should still return the partial data
        assert len(result) == 1
        assert result[0]["booking_id"] == "BKG001"


class TestRecoveryStrategies:
    """Test error recovery strategies."""

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_continues_with_available_data(self, mock_dynamodb, mock_create_agent):
        """Test that agent continues with available data when some queries fail."""
        # Mock successful agent execution despite some tool failures
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "PARTIAL_DATA",
                        "recommendations": ["Limited analysis due to missing data"],
                        "reasoning": "Some data unavailable",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Agent should complete despite partial data
        assert result["agent"] == "guest_experience"
        assert "assessment" in result

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_graceful_degradation(self, mock_create_agent):
        """Test graceful degradation when tools are unavailable."""
        # Mock agent that handles tool unavailability
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "CANNOT_PROCEED",
                        "status": "FAILURE",
                        "failure_reason": "Required data unavailable",
                        "recommendations": ["Manual review required"],
                        "reasoning": "Database tools failed",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Should return structured failure response
        assert result["agent"] == "guest_experience"
        assert "assessment" in result


class TestInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_empty_payload(self, mock_create_agent):
        """Test handling of empty payload."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "CANNOT_PROCEED",
                        "recommendations": ["Provide flight details"],
                        "reasoning": "No input provided",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        payload = {}

        result = await analyze_guest_experience(payload, Mock(), [])

        # Should handle empty payload gracefully
        assert result["agent"] == "guest_experience"

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_invalid_phase(self, mock_create_agent):
        """Test handling of invalid phase value."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "HIGH_IMPACT",
                        "recommendations": ["Action required"],
                        "reasoning": "Analysis complete",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "invalid_phase",  # Invalid phase
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Should handle invalid phase (defaults to initial)
        assert result["agent"] == "guest_experience"
