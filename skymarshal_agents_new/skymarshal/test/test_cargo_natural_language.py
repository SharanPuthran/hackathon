"""
Unit tests for Cargo Agent natural language processing.

Tests verify that:
1. Agent extracts flight information from natural language prompts
2. Agent handles various date formats
3. Agent handles missing or invalid information gracefully
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents.cargo.agent import analyze_cargo
from agents.schemas import FlightInfo


class TestCargoNaturalLanguage:
    """Test suite for Cargo Agent natural language processing."""

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_extract_flight_info_standard_format(self, mock_boto3):
        """Test extraction of flight info from standard format prompt."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "cargo_risk_score": 65,
                    "recommendations": ["Monitor cold chain cargo"]
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY123 on January 20th, 2026 had a mechanical failure",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify extraction was called
            mock_llm.with_structured_output.assert_called_once()
            mock_structured_llm.invoke.assert_called_once()

            # Verify extracted info in result
            assert result["extracted_flight_info"]["flight_number"] == "EY123"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_extract_flight_info_relative_date(self, mock_boto3):
        """Test extraction with relative date (yesterday, today, tomorrow)."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY456",
            date="2026-01-19",
            disruption_event="weather delay"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "cargo_risk_score": 45,
                    "recommendations": ["Standard cargo handling"]
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY456 yesterday was delayed due to weather",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify
            assert result["extracted_flight_info"]["flight_number"] == "EY456"
            assert result["extracted_flight_info"]["date"] == "2026-01-19"

    @pytest.mark.asyncio
    async def test_missing_prompt(self):
        """Test handling of missing user prompt."""
        # Setup
        mock_llm = Mock()

        # Execute
        payload = {}
        result = await analyze_cargo(payload, mock_llm, [])

        # Verify failure response
        assert result["status"] == "FAILURE"
        assert result["assessment"] == "CANNOT_PROCEED"
        assert "No user prompt provided" in result["failure_reason"]

    @pytest.mark.asyncio
    async def test_extraction_failure(self):
        """Test handling of extraction failure."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.side_effect = Exception("Extraction failed")
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Execute
        payload = {
            "user_prompt": "Some invalid prompt without flight info",
            "phase": "initial"
        }
        result = await analyze_cargo(payload, mock_llm, [])

        # Verify failure response
        assert result["status"] == "FAILURE"
        assert result["assessment"] == "CANNOT_PROCEED"
        assert "Could not extract flight information" in result["failure_reason"]
        assert "flight_number" in result["missing_data"]
        assert "date" in result["missing_data"]

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_extract_flight_info_numeric_date(self, mock_boto3):
        """Test extraction with numeric date format."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY789",
            date="2026-01-20",
            disruption_event="technical issue"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "cargo_risk_score": 55,
                    "recommendations": ["Check perishable cargo"]
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY789 on 20/01/2026 had a technical issue",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify
            assert result["extracted_flight_info"]["flight_number"] == "EY789"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_revision_phase_with_other_recommendations(self, mock_boto3):
        """Test cargo agent in revision phase with other agents' recommendations."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "cargo_risk_score": 70,
                    "recommendations": ["Revised: Prioritize cold chain cargo based on maintenance timeline"]
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
                "phase": "revision",
                "other_recommendations": {
                    "maintenance": {
                        "recommendation": "Aircraft requires 4-hour repair",
                        "confidence": 0.9
                    },
                    "network": {
                        "recommendation": "Swap aircraft available in 2 hours",
                        "confidence": 0.85
                    }
                }
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify revision phase was processed
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["flight_number"] == "EY123"

            # Verify agent was invoked with revision instructions
            call_args = mock_agent.ainvoke.call_args[0][0]
            system_message = call_args["messages"][0]["content"]
            assert "REVISION ROUND" in system_message
            assert "OTHER AGENTS' RECOMMENDATIONS" in system_message

    @pytest.mark.asyncio
    @patch("agents.cargo.agent.boto3.resource")
    async def test_extract_disruption_event(self, mock_boto3):
        """Test extraction of disruption event description."""
        # Setup mocks
        mock_llm = Mock()
        mock_structured_llm = Mock()
        mock_structured_llm.invoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure requiring engine replacement"
        )
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(content={
                    "agent": "cargo",
                    "cargo_risk_score": 75,
                    "recommendations": ["Extended delay - prioritize perishables"]
                })
            ]
        }

        with patch("agents.cargo.agent.create_agent", return_value=mock_agent):
            # Execute
            payload = {
                "user_prompt": "Flight EY123 on Jan 20 had a mechanical failure requiring engine replacement",
                "phase": "initial"
            }
            result = await analyze_cargo(payload, mock_llm, [])

            # Verify disruption event captured
            assert "mechanical failure" in result["extracted_flight_info"]["disruption_event"]
