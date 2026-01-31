"""
Unit tests for Guest Experience Agent natural language prompt handling.

Tests verify that:
1. Agent accepts natural language prompts
2. Agent uses LangChain structured output for extraction
3. Agent handles various date formats
4. Agent handles various prompt phrasings
5. Agent extracts flight info correctly
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from agents.guest_experience.agent import analyze_guest_experience
from agents.schemas import FlightInfo


class TestNaturalLanguagePrompts:
    """Test natural language prompt handling."""

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_basic_natural_language_prompt(self, mock_dynamodb, mock_create_agent):
        """Test basic natural language prompt."""
        # Mock agent response
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "HIGH_IMPACT",
                        "passenger_impact": {"total_affected": 615},
                        "recommendations": ["Proactive rebooking for elite passengers"],
                        "reasoning": "Analysis complete",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        # Test with natural language prompt
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Verify agent was invoked with user prompt
        assert mock_agent.ainvoke.called
        call_args = mock_agent.ainvoke.call_args[0][0]
        assert "messages" in call_args
        assert any(
            "Flight EY123 on January 20th" in str(msg.get("content", ""))
            for msg in call_args["messages"]
        )

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_various_date_formats(self, mock_dynamodb, mock_create_agent):
        """Test various date format handling."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "MEDIUM_IMPACT",
                        "recommendations": ["Standard rebooking"],
                        "reasoning": "Analysis complete",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        # Test different date formats
        date_formats = [
            "Flight EY123 on 20/01/2026 was delayed",
            "Flight EY123 on 20-01-26 was delayed",
            "Flight EY123 on 2026-01-20 was delayed",
            "Flight EY123 on 20 Jan was delayed",
            "Flight EY123 on 20th January was delayed",
            "Flight EY123 on January 20th 2026 was delayed",
            "Flight EY123 yesterday was delayed",
            "Flight EY123 today was delayed",
            "Flight EY123 tomorrow was delayed",
        ]

        for prompt in date_formats:
            payload = {"user_prompt": prompt, "phase": "initial"}
            result = await analyze_guest_experience(payload, Mock(), [])
            assert result["agent"] == "guest_experience"

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_various_disruption_descriptions(self, mock_dynamodb, mock_create_agent):
        """Test various disruption description handling."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "HIGH_IMPACT",
                        "recommendations": ["Immediate action required"],
                        "reasoning": "Analysis complete",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        # Test different disruption descriptions
        disruptions = [
            "Flight EY123 on Jan 20th had a mechanical failure",
            "Flight EY123 on Jan 20th was delayed due to weather",
            "Flight EY123 on Jan 20th experienced a rerouted plane",
            "Flight EY123 on Jan 20th had a weather diversion",
            "Flight EY123 on Jan 20th suffered crew shortage",
            "Flight EY123 on Jan 20th had maintenance issue",
            "Flight EY123 on Jan 20th was cancelled",
        ]

        for prompt in disruptions:
            payload = {"user_prompt": prompt, "phase": "initial"}
            result = await analyze_guest_experience(payload, Mock(), [])
            assert result["agent"] == "guest_experience"


class TestFlightInfoExtraction:
    """Test FlightInfo extraction from natural language."""

    def test_flight_info_validation(self):
        """Test FlightInfo model validation."""
        # Valid flight info
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure",
        )
        assert flight_info.flight_number == "EY123"
        assert flight_info.date == "2026-01-20"
        assert flight_info.disruption_event == "mechanical failure"

    def test_flight_number_validation(self):
        """Test flight number format validation."""
        # Valid formats
        valid_numbers = ["EY123", "EY1234", "ey123", "ey1234"]
        for num in valid_numbers:
            flight_info = FlightInfo(
                flight_number=num, date="2026-01-20", disruption_event="delay"
            )
            assert flight_info.flight_number.startswith("EY")

        # Invalid formats
        invalid_numbers = ["EY12", "EY12345", "AB123", "123", "EY"]
        for num in invalid_numbers:
            with pytest.raises(ValueError):
                FlightInfo(
                    flight_number=num, date="2026-01-20", disruption_event="delay"
                )

    def test_date_validation(self):
        """Test date format validation."""
        # Valid ISO format
        flight_info = FlightInfo(
            flight_number="EY123", date="2026-01-20", disruption_event="delay"
        )
        assert flight_info.date == "2026-01-20"

        # Invalid formats (should be converted by LLM before validation)
        invalid_dates = ["20/01/2026", "20-01-26", "Jan 20", "yesterday"]
        for date in invalid_dates:
            with pytest.raises(ValueError):
                FlightInfo(
                    flight_number="EY123", date=date, disruption_event="delay"
                )

    def test_disruption_event_validation(self):
        """Test disruption event validation."""
        # Valid disruption events
        valid_events = [
            "mechanical failure",
            "weather delay",
            "crew shortage",
            "maintenance issue",
        ]
        for event in valid_events:
            flight_info = FlightInfo(
                flight_number="EY123", date="2026-01-20", disruption_event=event
            )
            assert flight_info.disruption_event == event

        # Empty disruption event should fail
        with pytest.raises(ValueError):
            FlightInfo(
                flight_number="EY123", date="2026-01-20", disruption_event=""
            )


class TestPhaseHandling:
    """Test phase-specific behavior."""

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_initial_phase(self, mock_dynamodb, mock_create_agent):
        """Test initial phase handling."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "HIGH_IMPACT",
                        "recommendations": ["Proactive rebooking"],
                        "reasoning": "Initial analysis",
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

        # Verify initial phase instructions in system message
        call_args = mock_agent.ainvoke.call_args[0][0]
        system_message = call_args["messages"][0]["content"]
        assert "INITIAL RECOMMENDATIONS" in system_message
        assert "independent assessment" in system_message

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_revision_phase(self, mock_dynamodb, mock_create_agent):
        """Test revision phase handling."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "HIGH_IMPACT",
                        "recommendations": ["Revised: Enhanced rebooking"],
                        "reasoning": "Revised after reviewing other agents",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        other_recommendations = {
            "crew_compliance": {"recommendation": "Crew change required"},
            "maintenance": {"recommendation": "Aircraft inspection needed"},
        }

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "revision",
            "other_recommendations": other_recommendations,
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Verify revision phase instructions in system message
        call_args = mock_agent.ainvoke.call_args[0][0]
        system_message = call_args["messages"][0]["content"]
        assert "REVISION ROUND" in system_message
        assert "Other Agents' Recommendations" in system_message
        assert "crew_compliance" in system_message


class TestErrorHandling:
    """Test error handling in natural language processing."""

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    async def test_agent_execution_error(self, mock_create_agent):
        """Test handling of agent execution errors."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.side_effect = Exception("Agent execution failed")
        mock_create_agent.return_value = mock_agent

        payload = {
            "user_prompt": "Flight EY123 on Jan 20th had mechanical failure",
            "phase": "initial",
        }

        result = await analyze_guest_experience(payload, Mock(), [])

        # Verify error response
        assert result["status"] == "FAILURE"
        assert result["agent"] == "guest_experience"
        assert "error" in result
        assert "Agent execution failed" in result["error"]

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_missing_user_prompt(self, mock_dynamodb, mock_create_agent):
        """Test handling of missing user prompt."""
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {
            "messages": [
                Mock(
                    content={
                        "agent": "guest_experience",
                        "assessment": "CANNOT_PROCEED",
                        "recommendations": ["Provide flight details"],
                        "reasoning": "Missing information",
                    }
                )
            ]
        }
        mock_create_agent.return_value = mock_agent

        # Empty prompt
        payload = {"user_prompt": "", "phase": "initial"}

        result = await analyze_guest_experience(payload, Mock(), [])

        # Agent should still be invoked (validation happens in agent logic)
        assert mock_agent.ainvoke.called


class TestToolIntegration:
    """Test integration with DynamoDB query tools."""

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_tools_passed_to_agent(self, mock_dynamodb, mock_create_agent):
        """Test that DynamoDB tools are passed to agent."""
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
            "phase": "initial",
        }

        mcp_tools = [Mock(name="mcp_tool_1")]

        await analyze_guest_experience(payload, Mock(), mcp_tools)

        # Verify create_agent was called with tools
        assert mock_create_agent.called
        call_kwargs = mock_create_agent.call_args[1]
        assert "tools" in call_kwargs
        
        # Verify both MCP tools and DB tools are included
        tools = call_kwargs["tools"]
        assert len(tools) > len(mcp_tools)  # Should have MCP + DB tools

    @pytest.mark.asyncio
    @patch("agents.guest_experience.agent.create_agent")
    @patch("agents.guest_experience.agent.dynamodb")
    async def test_structured_output_format(self, mock_dynamodb, mock_create_agent):
        """Test that agent uses structured output format."""
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
            "phase": "initial",
        }

        await analyze_guest_experience(payload, Mock(), [])

        # Verify create_agent was called with response_format
        call_kwargs = mock_create_agent.call_args[1]
        assert "response_format" in call_kwargs
        from agents.schemas import GuestExperienceOutput
        assert call_kwargs["response_format"] == GuestExperienceOutput
