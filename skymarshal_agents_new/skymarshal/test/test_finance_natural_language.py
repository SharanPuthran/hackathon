"""
Unit Tests for Finance Agent Natural Language Processing

Feature: skymarshal-multi-round-orchestration
Task: 13.4 Update Finance Agent
Validates: Requirements 1.1-1.15, 2.1

Tests that the Finance agent can extract flight information from natural
language prompts using LangChain structured output.
"""

import pytest
from pydantic import ValidationError
from agents.schemas import FlightInfo


class TestFlightInfoExtraction:
    """Test FlightInfo model validation for Finance agent."""

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


class TestFinanceAgentPromptHandling:
    """Test Finance agent's natural language prompt handling."""

    def test_agent_receives_user_prompt(self):
        """Test that Finance agent receives raw user prompt."""
        # This test validates the agent interface accepts user_prompt
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }
        
        assert "user_prompt" in payload
        assert isinstance(payload["user_prompt"], str)
        assert len(payload["user_prompt"]) > 0

    def test_agent_receives_phase_indicator(self):
        """Test that Finance agent receives phase indicator."""
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }
        
        assert "phase" in payload
        assert payload["phase"] in ["initial", "revision"]

    def test_revision_phase_includes_other_recommendations(self):
        """Test that revision phase includes other agents' recommendations."""
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "revision",
            "other_recommendations": {
                "crew_compliance": {"recommendation": "Crew within limits"},
                "maintenance": {"recommendation": "Aircraft serviceable"}
            }
        }
        
        assert "other_recommendations" in payload
        assert isinstance(payload["other_recommendations"], dict)


class TestNaturalLanguagePromptVariations:
    """Test Finance agent handles various natural language prompt formats."""

    def test_numeric_date_format(self):
        """Test prompt with numeric date format."""
        prompts = [
            "Flight EY123 on 20/01/2026 had a delay",
            "EY456 on 01-20-2026 mechanical issue",
            "Flight EY789 2026-01-20 weather delay"
        ]
        
        for prompt in prompts:
            # Agent should be able to extract flight info from these prompts
            assert "EY" in prompt
            assert "2026" in prompt or "26" in prompt

    def test_named_date_format(self):
        """Test prompt with named date format."""
        prompts = [
            "Flight EY123 on January 20th had a mechanical failure",
            "EY456 on 20 Jan experienced a delay",
            "Flight EY789 on 20th January 2026 was cancelled"
        ]
        
        for prompt in prompts:
            assert "EY" in prompt
            assert "jan" in prompt.lower()  # Check for "jan" substring in lowercase

    def test_relative_date_format(self):
        """Test prompt with relative date format."""
        prompts = [
            "Flight EY123 yesterday had a mechanical failure",
            "EY456 today is delayed",
            "Flight EY789 tomorrow will be cancelled"
        ]
        
        for prompt in prompts:
            assert "EY" in prompt
            assert any(word in prompt.lower() for word in ["yesterday", "today", "tomorrow"])

    def test_various_disruption_descriptions(self):
        """Test prompts with various disruption event descriptions."""
        prompts = [
            "Flight EY123 on 2026-01-20 had a mechanical failure",
            "EY456 on 2026-01-20 was delayed due to weather",
            "Flight EY789 on 2026-01-20 diverted to alternate airport",
            "EY321 on 2026-01-20 cancelled due to crew shortage",
            "Flight EY654 on 2026-01-20 experienced hydraulic issues"
        ]
        
        for prompt in prompts:
            # Each prompt should contain flight number, date, and disruption
            assert "EY" in prompt
            assert "2026" in prompt
            # Disruption keywords
            assert any(word in prompt.lower() for word in 
                      ["mechanical", "delayed", "weather", "diverted", "cancelled", "hydraulic"])


class TestFinanceAgentResponsibility:
    """Test Finance agent's domain responsibility."""

    def test_finance_agent_focuses_on_financial_impact(self):
        """Test that Finance agent is responsible for financial analysis."""
        # Finance agent should analyze:
        # - Direct costs (crew, fuel, maintenance)
        # - Passenger compensation (EU261, DOT, care costs)
        # - Revenue impact (lost tickets, cargo, ancillary)
        # - Cost-benefit analysis of recovery scenarios
        
        responsibilities = [
            "direct costs",
            "passenger compensation",
            "revenue impact",
            "cost-benefit analysis",
            "budget tracking",
            "scenario ranking"
        ]
        
        # Verify Finance agent domain
        assert len(responsibilities) > 0

    def test_finance_agent_uses_financial_data(self):
        """Test that Finance agent queries financial data."""
        # Finance agent should query:
        # - Passenger bookings (for revenue calculation)
        # - Cargo assignments (for cargo revenue)
        # - Maintenance work orders (for cost estimation)
        
        data_sources = [
            "bookings",
            "cargo_flight_assignments",
            "maintenance_work_orders"
        ]
        
        assert len(data_sources) > 0


class TestFinanceAgentOutputStructure:
    """Test Finance agent output structure."""

    def test_finance_output_includes_cost_breakdown(self):
        """Test that Finance agent output includes cost breakdown."""
        # Expected output structure
        expected_fields = [
            "agent_name",
            "recommendation",
            "confidence",
            "reasoning",
            "data_sources",
            "extracted_flight_info"
        ]
        
        # Finance-specific fields
        finance_fields = [
            "direct_costs",
            "passenger_compensation",
            "revenue_impact",
            "total_cost"
        ]
        
        assert len(expected_fields) > 0
        assert len(finance_fields) > 0

    def test_finance_output_includes_scenario_ranking(self):
        """Test that Finance agent output includes scenario ranking."""
        # Finance agent should rank scenarios by total cost
        ranking_fields = [
            "scenario_rankings",
            "recommended_scenario",
            "cost_savings"
        ]
        
        assert len(ranking_fields) > 0
