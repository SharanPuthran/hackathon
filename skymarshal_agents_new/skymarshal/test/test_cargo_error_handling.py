"""
Unit tests for Cargo Agent error handling.

Tests verify that:
1. Agent handles database query failures gracefully
2. Agent returns structured failure responses
3. Agent provides helpful error messages
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents.cargo.agent import analyze_cargo, query_flight, query_cargo_manifest
from agents.schemas import FlightInfo


class TestCargoErrorHandling:
    """Test suite for Cargo Agent error handling."""

    @pytest.mark.asyncio
    async def test_agent_execution_error(self):
        """Test handling of agent execution error."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent to raise exception
        with patch("agents.cargo.agent.create_agent", side_effect=Exception("Agent creation failed")):
            # Execute
            payload = {
                "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify failure response
            assert result["status"] == "FAILURE"
            assert result["assessment"] == "CANNOT_PROCEED"
            assert "Agent execution error" in result["failure_reason"]
            assert result["error_type"] == "Exception"

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_flight_database_error(self, mock_boto3):
        """Test handling of database error in query_flight."""
        # Setup mock to raise exception
        mock_table = Mock()
        mock_table.query.side_effect = Exception("DynamoDB connection failed")
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Verify returns None on error
        assert result is None

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_cargo_manifest_database_error(self, mock_boto3):
        """Test handling of database error in query_cargo_manifest."""
        # Setup mock to raise exception
        mock_table = Mock()
        mock_table.query.side_effect = Exception("DynamoDB connection failed")
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_cargo_manifest.invoke({"flight_id": "EY123-20260120"})

        # Verify returns empty list on error
        assert result == []

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_flight_not_found(self, mock_boto3):
        """Test handling when flight is not found in database."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY999",
            date="2026-01-20",
            disruption_event="delay"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent to return flight not found
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "assessment": "CANNOT_PROCEED",
                    "status": "FAILURE",
                    "failure_reason": "Flight EY999 on 2026-01-20 not found in database",
                    "missing_data": ["flight_record"],
                    "recommendations": ["Verify flight number and date are correct"]
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY999 on January 20th was delayed",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify appropriate failure response
            assert result["status"] == "FAILURE"
            assert "not found" in result["failure_reason"]

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_no_cargo_on_flight(self, mock_boto3):
        """Test handling when flight has no cargo."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent to return no cargo found
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "cargo_risk_score": 0,
                    "total_cargo_value_usd": 0,
                    "recommendations": ["No cargo on this flight - no cargo impact"],
                    "status": "success"
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY123 on January 20th was delayed",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify successful response with zero cargo
            assert result["status"] == "success"
            assert result["cargo_risk_score"] == 0

    @pytest.mark.asyncio
    async def test_invalid_payload_structure(self):
        """Test handling of invalid payload structure."""
        # Setup
        mock_llm = Mock()

        # Execute with invalid payload
        payload = None
        
        # Should handle gracefully
        try:
            result = await analyze_cargo(payload, mock_llm, [])
            # If it doesn't raise, verify it returns failure
            assert result["status"] == "FAILURE"
        except Exception as e:
            # If it raises, that's also acceptable error handling
            assert isinstance(e, (TypeError, AttributeError))

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_database_timeout(self, mock_boto3):
        """Test handling of database timeout."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent to return timeout error
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "assessment": "CANNOT_PROCEED",
                    "status": "FAILURE",
                    "failure_reason": "Database query timeout after 30 seconds",
                    "attempted_tools": ["query_flight", "query_cargo_manifest"],
                    "recommendations": ["Retry the request", "Check database connectivity"]
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY123 on January 20th was delayed",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify timeout is handled
            assert result["status"] == "FAILURE"
            assert "timeout" in result["failure_reason"].lower()

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_partial_data_available(self, mock_boto3):
        """Test handling when only partial cargo data is available."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent to return partial data warning
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "cargo_risk_score": 50,
                    "total_cargo_value_usd": 85000,
                    "recommendations": [
                        "WARNING: Some shipment details unavailable",
                        "Risk assessment based on partial data"
                    ],
                    "status": "success",
                    "data_completeness": "partial"
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY123 on January 20th was delayed",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify partial data is handled
            assert result["status"] == "success"
            assert any("partial" in str(rec).lower() or "unavailable" in str(rec).lower() 
                      for rec in result.get("recommendations", []))

    @pytest.mark.asyncio
    async def test_llm_structured_output_failure(self):
        """Test handling when LLM structured output fails."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.side_effect = ValueError("Invalid output format")
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Execute
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }
        result = await analyze_cargo(payload, mock_llm, [])

        # Verify extraction failure is handled
        assert result["status"] == "FAILURE"
        assert result["assessment"] == "CANNOT_PROCEED"
        assert "Could not extract flight information" in result["failure_reason"]
