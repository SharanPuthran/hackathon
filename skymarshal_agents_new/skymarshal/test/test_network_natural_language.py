"""
Unit Tests for Network Agent Natural Language Processing

Feature: skymarshal-multi-round-orchestration
Task: 13.1 Update Network Agent
Validates: Requirements 1.1-1.15, 2.1

Tests that the Network agent can extract flight information from natural
language prompts using LangChain structured output.
"""

import pytest
from pydantic import ValidationError
from agents.schemas import FlightInfo


class TestFlightInfoExtraction:
    """Test FlightInfo model validation for Network agent."""

    def test_valid_flight_info(self):
        """Test that valid flight info is accepted."""
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        
        assert flight_info.flight_number == "EY123"
        assert flight_info.date == "2026-01-20"
        assert flight_info.disruption_event == "mechanical failure"

    def test_flight_number_validation(self):
        """Test flight number format validation."""
        # Valid formats
        valid_numbers = ["EY123", "EY1234", "ey456", "Ey789"]
        for num in valid_numbers:
            flight_info = FlightInfo(
                flight_number=num,
                date="2026-01-20",
                disruption_event="delay"
            )
            assert flight_info.flight_number.startswith("EY")

    def test_invalid_flight_number(self):
        """Test that invalid flight numbers are rejected."""
        invalid_numbers = ["EY12", "EY12345", "AA123", "123", "EY"]
        
        for num in invalid_numbers:
            with pytest.raises(ValidationError):
                FlightInfo(
                    flight_number=num,
                    date="2026-01-20",
                    disruption_event="delay"
                )

    def test_date_format_validation(self):
        """Test that date must be in ISO format."""
        # Valid ISO format
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        assert flight_info.date == "2026-01-20"

    def test_invalid_date_format(self):
        """Test that non-ISO date formats are rejected."""
        invalid_dates = ["20/01/2026", "Jan 20", "yesterday", "20-01-2026"]
        
        for date in invalid_dates:
            with pytest.raises(ValidationError):
                FlightInfo(
                    flight_number="EY123",
                    date=date,
                    disruption_event="delay"
                )

    def test_empty_disruption_event(self):
        """Test that empty disruption event is rejected."""
        with pytest.raises(ValidationError):
            FlightInfo(
                flight_number="EY123",
                date="2026-01-20",
                disruption_event=""
            )

    def test_whitespace_disruption_event(self):
        """Test that whitespace-only disruption event is rejected."""
        with pytest.raises(ValidationError):
            FlightInfo(
                flight_number="EY123",
                date="2026-01-20",
                disruption_event="   "
            )


class TestNetworkAgentPromptHandling:
    """Test Network agent's natural language prompt handling."""

    def test_agent_receives_user_prompt(self):
        """Test that agent receives raw user prompt in payload."""
        from agents.schemas import DisruptionPayload
        
        payload = DisruptionPayload(
            user_prompt="Flight EY123 on January 20th had a mechanical failure",
            phase="initial"
        )
        
        assert payload.user_prompt == "Flight EY123 on January 20th had a mechanical failure"
        assert payload.phase == "initial"
        assert payload.other_recommendations is None

    def test_agent_receives_revision_payload(self):
        """Test that agent receives other recommendations in revision phase."""
        from agents.schemas import DisruptionPayload
        
        other_recs = {
            "crew_compliance": {"recommendation": "Approve with crew change"},
            "maintenance": {"recommendation": "Requires inspection"}
        }
        
        payload = DisruptionPayload(
            user_prompt="Flight EY123 on January 20th had a mechanical failure",
            phase="revision",
            other_recommendations=other_recs
        )
        
        assert payload.phase == "revision"
        assert payload.other_recommendations is not None
        assert len(payload.other_recommendations) == 2

    def test_short_prompt_rejected(self):
        """Test that very short prompts are rejected."""
        from agents.schemas import DisruptionPayload
        
        with pytest.raises(ValidationError):
            DisruptionPayload(
                user_prompt="EY123",
                phase="initial"
            )

    def test_empty_prompt_rejected(self):
        """Test that empty prompts are rejected."""
        from agents.schemas import DisruptionPayload
        
        with pytest.raises(ValidationError):
            DisruptionPayload(
                user_prompt="",
                phase="initial"
            )


class TestNetworkAgentResponse:
    """Test Network agent response format."""

    def test_agent_response_structure(self):
        """Test that agent response has required fields."""
        from agents.schemas import AgentResponse
        from datetime import datetime, timezone
        
        response = AgentResponse(
            agent_name="network",
            recommendation="Delay propagates to 2 downstream flights",
            confidence=0.85,
            binding_constraints=[],  # Network is business agent, no binding constraints
            reasoning="Aircraft rotation analysis shows 2 downstream flights affected",
            data_sources=["flights", "AircraftAvailability"],
            extracted_flight_info={
                "flight_number": "EY123",
                "date": "2026-01-20",
                "disruption_event": "mechanical failure"
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="success"
        )
        
        assert response.agent_name == "network"
        assert response.confidence == 0.85
        assert response.binding_constraints == []  # Business agent
        assert "flights" in response.data_sources
        assert "AircraftAvailability" in response.data_sources

    def test_network_no_binding_constraints(self):
        """Test that Network agent (business) does not provide binding constraints."""
        from agents.schemas import AgentResponse
        from datetime import datetime, timezone
        
        # Network is a business agent and should not have binding constraints
        response = AgentResponse(
            agent_name="network",
            recommendation="Network impact assessment",
            confidence=0.9,
            binding_constraints=[],  # Should be empty for business agents
            reasoning="Network analysis complete",
            data_sources=["flights"],
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        assert response.binding_constraints == []

    def test_extracted_flight_info_in_response(self):
        """Test that agent response includes extracted flight info."""
        from agents.schemas import AgentResponse
        from datetime import datetime, timezone
        
        response = AgentResponse(
            agent_name="network",
            recommendation="Network impact assessment",
            confidence=0.9,
            reasoning="Analysis complete",
            data_sources=["flights"],
            extracted_flight_info={
                "flight_number": "EY123",
                "date": "2026-01-20",
                "disruption_event": "mechanical failure"
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        assert response.extracted_flight_info is not None
        assert response.extracted_flight_info["flight_number"] == "EY123"
        assert response.extracted_flight_info["date"] == "2026-01-20"


class TestNetworkAgentSystemPrompt:
    """Test Network agent system prompt configuration."""

    def test_system_prompt_mentions_extraction(self):
        """Test that system prompt mentions natural language extraction."""
        from agents.network.agent import SYSTEM_PROMPT
        
        assert "natural language" in SYSTEM_PROMPT.lower(), \
            "System prompt should mention natural language processing"
        assert "extract" in SYSTEM_PROMPT.lower(), \
            "System prompt should mention extraction"
        assert "FlightInfo" in SYSTEM_PROMPT, \
            "System prompt should mention FlightInfo model"

    def test_system_prompt_mentions_tools(self):
        """Test that system prompt mentions available tools."""
        from agents.network.agent import SYSTEM_PROMPT
        
        assert "query_flight" in SYSTEM_PROMPT, \
            "System prompt should mention query_flight tool"
        assert "query_aircraft_rotation" in SYSTEM_PROMPT, \
            "System prompt should mention query_aircraft_rotation tool"
        assert "database tools" in SYSTEM_PROMPT.lower(), \
            "System prompt should mention database tools"

    def test_system_prompt_mentions_gsis(self):
        """Test that system prompt mentions GSI usage."""
        from agents.network.agent import SYSTEM_PROMPT
        
        assert "GSI" in SYSTEM_PROMPT or "index" in SYSTEM_PROMPT.lower(), \
            "System prompt should mention GSI usage"
        assert "aircraft-rotation-index" in SYSTEM_PROMPT.lower() or "rotation" in SYSTEM_PROMPT.lower(), \
            "System prompt should mention rotation queries"

    def test_system_prompt_has_failure_format(self):
        """Test that system prompt includes failure response format."""
        from agents.network.agent import SYSTEM_PROMPT
        
        assert "FAILURE" in SYSTEM_PROMPT or "CANNOT_PROCEED" in SYSTEM_PROMPT, \
            "System prompt should include failure response format"
        assert "error" in SYSTEM_PROMPT.lower(), \
            "System prompt should mention error handling"
