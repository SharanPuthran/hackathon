"""
Unit tests for Pydantic schemas in src/agents/schemas.py

Tests focus on:
1. Model validation with valid inputs
2. Model validation with invalid inputs
3. Field validators (flight_number, date, disruption_event)
4. Various natural language input formats
5. Edge cases and error handling
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from hypothesis import given, strategies as st, settings

from agents.schemas import (
    FlightInfo,
    DisruptionPayload,
    AgentResponse,
    Collation,
    CrewMember,
    Violation,
    AlternativeCrew,
    CrewComplianceOutput,
    MaintenanceOutput,
    RegulatoryOutput,
    NetworkOutput,
    GuestExperienceOutput,
    CargoOutput,
    FinanceOutput,
    OrchestratorValidation,
    OrchestratorOutput,
)


# ============================================================================
# FlightInfo Model Tests
# ============================================================================


class TestFlightInfoValidation:
    """Test FlightInfo model validation"""

    def test_valid_flight_info(self):
        """Test FlightInfo with valid inputs"""
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure",
        )

        assert flight_info.flight_number == "EY123"
        assert flight_info.date == "2026-01-20"
        assert flight_info.disruption_event == "mechanical failure"

    def test_valid_flight_number_formats(self):
        """Test various valid flight number formats"""
        valid_numbers = ["EY123", "EY1234", "ey456", "Ey789", "EY0001"]

        for flight_num in valid_numbers:
            flight_info = FlightInfo(
                flight_number=flight_num,
                date="2026-01-20",
                disruption_event="delay",
            )
            # Should be converted to uppercase
            assert flight_info.flight_number.startswith("EY")
            assert flight_info.flight_number.isupper()

    def test_invalid_flight_number_formats(self):
        """Test invalid flight number formats raise ValidationError"""
        invalid_numbers = [
            "EY12",  # Too short (only 2 digits)
            "EY12345",  # Too long (5 digits)
            "EY",  # No digits
            "123",  # No EY prefix
            "AB123",  # Wrong prefix
            "EY12A",  # Contains letter in digits
            "E Y123",  # Space in number
            "",  # Empty string
        ]

        for flight_num in invalid_numbers:
            with pytest.raises(ValidationError) as exc_info:
                FlightInfo(
                    flight_number=flight_num,
                    date="2026-01-20",
                    disruption_event="delay",
                )
            assert "Invalid flight number format" in str(exc_info.value)

    def test_valid_date_formats(self):
        """Test valid ISO 8601 date formats"""
        valid_dates = [
            "2026-01-20",
            "2025-12-31",
            "2026-02-28",
            "2024-02-29",  # Leap year
        ]

        for date in valid_dates:
            flight_info = FlightInfo(
                flight_number="EY123", date=date, disruption_event="delay"
            )
            assert flight_info.date == date

    def test_invalid_date_formats(self):
        """Test invalid date formats raise ValidationError"""
        invalid_dates = [
            "20/01/2026",  # dd/mm/yyyy format
            "01-20-2026",  # mm-dd-yyyy format
            "20 Jan 2026",  # Named format
            "yesterday",  # Relative date
            "2026-13-01",  # Invalid month
            "2026-01-32",  # Invalid day
            "not-a-date",  # Invalid format
            "",  # Empty string
        ]

        for date in invalid_dates:
            with pytest.raises(ValidationError) as exc_info:
                FlightInfo(
                    flight_number="EY123", date=date, disruption_event="delay"
                )
            assert "Invalid date format" in str(exc_info.value)

    def test_valid_disruption_events(self):
        """Test various valid disruption event descriptions"""
        valid_events = [
            "mechanical failure",
            "weather delay",
            "crew shortage",
            "maintenance issue",
            "rerouted plane",
            "weather diversion",
            "passenger medical emergency",
            "bird strike",
            "technical fault in landing gear",
        ]

        for event in valid_events:
            flight_info = FlightInfo(
                flight_number="EY123", date="2026-01-20", disruption_event=event
            )
            assert flight_info.disruption_event == event

    def test_invalid_disruption_events(self):
        """Test invalid disruption events raise ValidationError"""
        invalid_events = [
            "",  # Empty string
            "   ",  # Whitespace only
            "\n",  # Newline only
            "\t",  # Tab only
        ]

        for event in invalid_events:
            with pytest.raises(ValidationError) as exc_info:
                FlightInfo(
                    flight_number="EY123", date="2026-01-20", disruption_event=event
                )
            assert "Disruption event description cannot be empty" in str(exc_info.value)

    def test_flight_info_whitespace_handling(self):
        """Test that whitespace is properly stripped"""
        flight_info = FlightInfo(
            flight_number="  EY123  ",
            date="2026-01-20",
            disruption_event="  mechanical failure  ",
        )

        assert flight_info.flight_number == "EY123"
        assert flight_info.disruption_event == "mechanical failure"

    def test_flight_info_case_insensitive_flight_number(self):
        """Test that flight numbers are converted to uppercase"""
        flight_info = FlightInfo(
            flight_number="ey123", date="2026-01-20", disruption_event="delay"
        )

        assert flight_info.flight_number == "EY123"


# ============================================================================
# DisruptionPayload Model Tests
# ============================================================================


class TestDisruptionPayload:
    """Test DisruptionPayload model"""

    def test_valid_initial_phase_payload(self):
        """Test DisruptionPayload for initial phase"""
        payload = DisruptionPayload(
            user_prompt="Flight EY123 on January 20th had a mechanical failure",
            phase="initial",
        )

        assert payload.user_prompt == "Flight EY123 on January 20th had a mechanical failure"
        assert payload.phase == "initial"
        assert payload.other_recommendations is None

    def test_valid_revision_phase_payload(self):
        """Test DisruptionPayload for revision phase"""
        recommendations = {
            "crew_compliance": {"recommendation": "Approved", "confidence": 0.95}
        }

        payload = DisruptionPayload(
            user_prompt="Flight EY123 on January 20th had a mechanical failure",
            phase="revision",
            other_recommendations=recommendations,
        )

        assert payload.phase == "revision"
        assert payload.other_recommendations == recommendations

    def test_invalid_phase_value(self):
        """Test that invalid phase values raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            DisruptionPayload(
                user_prompt="Flight EY123 on January 20th had a mechanical failure",
                phase="invalid_phase",
            )
        assert "phase" in str(exc_info.value).lower()

    def test_empty_user_prompt(self):
        """Test that empty user prompt raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            DisruptionPayload(
                user_prompt="",
                phase="initial",
            )
        assert "User prompt cannot be empty" in str(exc_info.value)

    def test_whitespace_only_user_prompt(self):
        """Test that whitespace-only user prompt raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            DisruptionPayload(
                user_prompt="   ",
                phase="initial",
            )
        assert "User prompt cannot be empty" in str(exc_info.value)

    def test_too_short_user_prompt(self):
        """Test that too short user prompt raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            DisruptionPayload(
                user_prompt="EY123",
                phase="initial",
            )
        assert "User prompt too short" in str(exc_info.value)

    def test_revision_phase_without_recommendations(self):
        """Test that revision phase without other_recommendations raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            DisruptionPayload(
                user_prompt="Flight EY123 on January 20th had a mechanical failure",
                phase="revision",
                other_recommendations=None,
            )
        assert "other_recommendations is required in revision phase" in str(exc_info.value)

    def test_initial_phase_with_recommendations(self):
        """Test that initial phase with other_recommendations raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            DisruptionPayload(
                user_prompt="Flight EY123 on January 20th had a mechanical failure",
                phase="initial",
                other_recommendations={"agent": "test"},
            )
        assert "other_recommendations should not be provided in initial phase" in str(exc_info.value)

    def test_user_prompt_whitespace_stripping(self):
        """Test that user prompt whitespace is properly stripped"""
        payload = DisruptionPayload(
            user_prompt="  Flight EY123 on January 20th had a mechanical failure  ",
            phase="initial",
        )
        assert payload.user_prompt == "Flight EY123 on January 20th had a mechanical failure"


# ============================================================================
# AgentResponse Model Tests
# ============================================================================


class TestAgentResponse:
    """Test AgentResponse model"""

    def test_valid_agent_response(self):
        """Test AgentResponse with valid inputs"""
        response = AgentResponse(
            agent_name="crew_compliance",
            recommendation="Flight can proceed with current crew",
            confidence=0.95,
            reasoning="All crew members meet regulatory requirements",
            data_sources=["CrewRoster", "CrewMembers"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        assert response.agent_name == "crew_compliance"
        assert response.confidence == 0.95
        assert response.status == "success"  # Default value
        assert len(response.binding_constraints) == 0  # Default empty list

    def test_agent_response_with_binding_constraints(self):
        """Test AgentResponse with binding constraints (safety agents)"""
        response = AgentResponse(
            agent_name="regulatory",
            recommendation="Flight must be delayed",
            confidence=1.0,
            binding_constraints=[
                "Curfew violation: Cannot depart after 23:00",
                "Slot availability: No slots available before curfew",
            ],
            reasoning="Regulatory constraints prevent departure",
            data_sources=["Weather", "Slots"],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        assert len(response.binding_constraints) == 2
        assert response.confidence == 1.0

    def test_agent_response_confidence_validation(self):
        """Test that confidence must be between 0.0 and 1.0"""
        # Valid confidence values
        for conf in [0.0, 0.5, 1.0]:
            response = AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=conf,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            assert response.confidence == conf

        # Invalid confidence values
        for conf in [-0.1, 1.1, 2.0]:
            with pytest.raises(ValidationError):
                AgentResponse(
                    agent_name="crew_compliance",
                    recommendation="Test",
                    confidence=conf,
                    reasoning="Test",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )

    def test_agent_response_with_error(self):
        """Test AgentResponse with error status"""
        response = AgentResponse(
            agent_name="maintenance",
            recommendation="Unable to complete analysis",
            confidence=0.0,
            reasoning="Database connection timeout",
            timestamp=datetime.now(timezone.utc).isoformat(),
            status="error",
            error="Database connection timeout",
        )

        assert response.status == "error"
        assert response.error == "Database connection timeout"

    def test_agent_response_with_extracted_flight_info(self):
        """Test AgentResponse with extracted flight information"""
        flight_info = {
            "flight_number": "EY123",
            "date": "2026-01-20",
            "disruption_event": "mechanical failure",
        }

        response = AgentResponse(
            agent_name="crew_compliance",
            recommendation="Approved",
            confidence=0.95,
            reasoning="Test",
            timestamp=datetime.now(timezone.utc).isoformat(),
            extracted_flight_info=flight_info,
        )

        assert response.extracted_flight_info == flight_info

    def test_invalid_agent_name(self):
        """Test that invalid agent name raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                agent_name="invalid_agent",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        assert "Invalid agent name" in str(exc_info.value)

    def test_valid_agent_names(self):
        """Test all valid agent names"""
        valid_agents = [
            "crew_compliance",
            "maintenance",
            "regulatory",
            "network",
            "guest_experience",
            "cargo",
            "finance",
            "arbitrator",
        ]

        for agent_name in valid_agents:
            response = AgentResponse(
                agent_name=agent_name,
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            assert response.agent_name == agent_name

    def test_empty_recommendation(self):
        """Test that empty recommendation raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                agent_name="crew_compliance",
                recommendation="",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        assert "Recommendation cannot be empty" in str(exc_info.value)

    def test_empty_reasoning(self):
        """Test that empty reasoning raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="",
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        assert "Reasoning cannot be empty" in str(exc_info.value)

    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp format raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp="not-a-timestamp",
            )
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_valid_timestamp_formats(self):
        """Test various valid timestamp formats"""
        valid_timestamps = [
            datetime.now(timezone.utc).isoformat(),
            "2026-02-01T12:00:00Z",
            "2026-02-01T12:00:00+00:00",
            "2026-02-01T12:00:00.123456Z",
        ]

        for timestamp in valid_timestamps:
            response = AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=timestamp,
            )
            assert response.timestamp == timestamp

    def test_invalid_status(self):
        """Test that invalid status raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="invalid_status",
            )
        assert "Invalid status" in str(exc_info.value)

    def test_valid_statuses(self):
        """Test all valid status values"""
        valid_statuses = ["success", "timeout", "error"]

        for status in valid_statuses:
            response = AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status=status,
            )
            assert response.status == status

    def test_negative_duration(self):
        """Test that negative duration raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=-1.0,
            )
        assert "Duration cannot be negative" in str(exc_info.value)

    def test_valid_durations(self):
        """Test valid duration values"""
        valid_durations = [0.0, 1.5, 10.0, 30.0]

        for duration in valid_durations:
            response = AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=duration,
            )
            assert response.duration_seconds == duration

    def test_business_agent_with_binding_constraints(self):
        """Test that business agents cannot provide binding constraints"""
        business_agents = ["network", "guest_experience", "cargo", "finance"]

        for agent_name in business_agents:
            with pytest.raises(ValidationError) as exc_info:
                AgentResponse(
                    agent_name=agent_name,
                    recommendation="Test",
                    confidence=0.9,
                    reasoning="Test",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    binding_constraints=["Some constraint"],
                )
            assert "Only safety agents can provide binding constraints" in str(exc_info.value)

    def test_safety_agent_with_binding_constraints(self):
        """Test that safety agents can provide binding constraints"""
        safety_agents = ["crew_compliance", "maintenance", "regulatory"]

        for agent_name in safety_agents:
            response = AgentResponse(
                agent_name=agent_name,
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                binding_constraints=["Safety constraint"],
            )
            assert len(response.binding_constraints) == 1
            assert response.binding_constraints[0] == "Safety constraint"


# ============================================================================
# Collation Model Tests
# ============================================================================


class TestCollation:
    """Test Collation model"""

    def test_valid_collation(self):
        """Test Collation with valid responses"""
        responses = {
            "crew_compliance": AgentResponse(
                agent_name="crew_compliance",
                recommendation="Approved",
                confidence=0.95,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            "maintenance": AgentResponse(
                agent_name="maintenance",
                recommendation="Requires inspection",
                confidence=0.85,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        }

        collation = Collation(
            phase="initial",
            responses=responses,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=5.2,
        )

        assert collation.phase == "initial"
        assert len(collation.responses) == 2
        assert collation.duration_seconds == 5.2

    def test_collation_get_successful_responses(self):
        """Test get_successful_responses method"""
        responses = {
            "crew_compliance": AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="success",
            ),
            "maintenance": AgentResponse(
                agent_name="maintenance",
                recommendation="Test",
                confidence=0.8,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="timeout",
            ),
            "regulatory": AgentResponse(
                agent_name="regulatory",
                recommendation="Test",
                confidence=0.7,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="error",
                error="Test error",
            ),
        }

        collation = Collation(
            phase="initial",
            responses=responses,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=10.0,
        )

        successful = collation.get_successful_responses()
        assert len(successful) == 1
        assert "crew_compliance" in successful

    def test_collation_get_failed_responses(self):
        """Test get_failed_responses method"""
        responses = {
            "network": AgentResponse(
                agent_name="network",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="success",
            ),
            "guest_experience": AgentResponse(
                agent_name="guest_experience",
                recommendation="Test",
                confidence=0.8,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="timeout",
            ),
            "cargo": AgentResponse(
                agent_name="cargo",
                recommendation="Test",
                confidence=0.7,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="error",
                error="Test error",
            ),
        }

        collation = Collation(
            phase="revision",
            responses=responses,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=10.0,
        )

        failed = collation.get_failed_responses()
        assert len(failed) == 2
        assert "guest_experience" in failed
        assert "cargo" in failed

    def test_collation_get_agent_count(self):
        """Test get_agent_count method"""
        responses = {
            "crew_compliance": AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="success",
            ),
            "maintenance": AgentResponse(
                agent_name="maintenance",
                recommendation="Test",
                confidence=0.8,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="success",
            ),
            "regulatory": AgentResponse(
                agent_name="regulatory",
                recommendation="Test",
                confidence=0.7,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="timeout",
            ),
            "network": AgentResponse(
                agent_name="network",
                recommendation="Test",
                confidence=0.6,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="error",
                error="Test error",
            ),
        }

        collation = Collation(
            phase="initial",
            responses=responses,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=15.0,
        )

        counts = collation.get_agent_count()
        assert counts["success"] == 2
        assert counts["timeout"] == 1
        assert counts["error"] == 1

    def test_empty_responses(self):
        """Test that empty responses dict raises ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Collation(
                phase="initial",
                responses={},
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=0.0,
            )
        assert "Responses cannot be empty" in str(exc_info.value)

    def test_mismatched_response_keys(self):
        """Test that mismatched response keys raise ValidationError"""
        responses = {
            "wrong_key": AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        }

        with pytest.raises(ValidationError) as exc_info:
            Collation(
                phase="initial",
                responses=responses,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=5.0,
            )
        assert "does not match agent_name" in str(exc_info.value)

    def test_invalid_timestamp_format(self):
        """Test that invalid timestamp format raises ValidationError"""
        responses = {
            "crew_compliance": AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        }

        with pytest.raises(ValidationError) as exc_info:
            Collation(
                phase="initial",
                responses=responses,
                timestamp="not-a-timestamp",
                duration_seconds=5.0,
            )
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_negative_duration(self):
        """Test that negative duration raises ValidationError"""
        responses = {
            "crew_compliance": AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        }

        with pytest.raises(ValidationError) as exc_info:
            Collation(
                phase="initial",
                responses=responses,
                timestamp=datetime.now(timezone.utc).isoformat(),
                duration_seconds=-1.0,
            )
        assert "Duration cannot be negative" in str(exc_info.value)

    def test_valid_timestamp_formats(self):
        """Test various valid timestamp formats"""
        responses = {
            "crew_compliance": AgentResponse(
                agent_name="crew_compliance",
                recommendation="Test",
                confidence=0.9,
                reasoning="Test",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        }

        valid_timestamps = [
            datetime.now(timezone.utc).isoformat(),
            "2026-02-01T12:00:00Z",
            "2026-02-01T12:00:00+00:00",
            "2026-02-01T12:00:00.123456Z",
        ]

        for timestamp in valid_timestamps:
            collation = Collation(
                phase="initial",
                responses=responses,
                timestamp=timestamp,
                duration_seconds=5.0,
            )
            assert collation.timestamp == timestamp


# ============================================================================
# Property-Based Tests for FlightInfo Extraction Consistency
# ============================================================================


class TestProperty3FlightLookupConsistency:
    """
    Property-Based Tests for Property 3: Flight Lookup Consistency
    
    Feature: skymarshal-multi-round-orchestration
    Property 3: Flight Lookup Consistency
    Validates: Requirements 1.1-1.15, 2.1
    
    For all flight information (flight_number, date, event), when expressed in 
    different natural language phrasings, the structured output extraction SHALL 
    produce consistent results:
    
    ∀ flight_info f, ∀ phrasings p1, p2 where content(p1) == content(p2):
      extract(p1) == extract(p2) ∧
      extract(p1).flight_number == f.flight_number ∧
      extract(p1).date == normalize(f.date) ∧
      extract(p1).disruption_event == f.event
    
    Test Strategy: Generate prompts with the same flight information in different
    phrasings and verify that FlightInfo model validation produces consistent results.
    
    Note: This test validates the Pydantic model validation, not LLM extraction.
    The actual LLM extraction consistency is tested in integration tests.
    """
    
    @given(
        flight_number=st.from_regex(r'EY[0-9]{3,4}', fullmatch=True),
        date=st.dates(min_value=datetime(2024, 1, 1).date(), max_value=datetime(2027, 12, 31).date()),
        event=st.sampled_from([
            "mechanical failure",
            "weather delay",
            "crew shortage",
            "maintenance issue",
            "engine failure",
            "technical fault",
            "bird strike",
            "weather diversion",
        ])
    )
    @settings(max_examples=100, deadline=None)
    def test_flight_info_validation_consistency_across_formats(self, flight_number, date, event):
        """
        Property 3.1: FlightInfo validation produces consistent results
        
        For the same flight information, the Pydantic model should validate
        consistently regardless of how the data is provided (assuming it's
        already in the correct format).
        
        Validates: Requirements 1.1, 1.3, 2.1
        """
        # Convert date to ISO format
        date_iso = date.isoformat()
        
        # Create FlightInfo with the same data multiple times
        flight_info_1 = FlightInfo(
            flight_number=flight_number,
            date=date_iso,
            disruption_event=event
        )
        
        flight_info_2 = FlightInfo(
            flight_number=flight_number.lower(),  # Test case insensitivity
            date=date_iso,
            disruption_event=event
        )
        
        flight_info_3 = FlightInfo(
            flight_number=f"  {flight_number}  ",  # Test whitespace handling
            date=date_iso,
            disruption_event=f"  {event}  "
        )
        
        # Property: All should produce the same normalized output
        assert flight_info_1.flight_number == flight_info_2.flight_number, \
            "Flight number should be normalized consistently"
        assert flight_info_1.flight_number == flight_info_3.flight_number, \
            "Flight number should be normalized consistently with whitespace"
        
        assert flight_info_1.date == flight_info_2.date, \
            "Date should be consistent"
        assert flight_info_1.date == flight_info_3.date, \
            "Date should be consistent"
        
        assert flight_info_1.disruption_event == flight_info_2.disruption_event, \
            "Disruption event should be consistent"
        assert flight_info_1.disruption_event == flight_info_3.disruption_event, \
            "Disruption event should be normalized consistently"
    
    @given(
        flight_number=st.from_regex(r'EY[0-9]{3,4}', fullmatch=True),
        date=st.dates(min_value=datetime(2024, 1, 1).date(), max_value=datetime(2027, 12, 31).date()),
    )
    @settings(max_examples=50, deadline=None)
    def test_flight_number_normalization_consistency(self, flight_number, date):
        """
        Property 3.2: Flight number normalization is consistent
        
        For any valid flight number, the model should normalize it consistently
        to uppercase format regardless of input case.
        
        Validates: Requirements 1.3, 2.1
        """
        date_iso = date.isoformat()
        event = "test event"
        
        # Test various case combinations
        variations = [
            flight_number.upper(),
            flight_number.lower(),
            flight_number.capitalize(),
            f"  {flight_number.upper()}  ",
            f"  {flight_number.lower()}  ",
        ]
        
        normalized_values = []
        for variation in variations:
            flight_info = FlightInfo(
                flight_number=variation,
                date=date_iso,
                disruption_event=event
            )
            normalized_values.append(flight_info.flight_number)
        
        # Property: All variations should normalize to the same value
        assert len(set(normalized_values)) == 1, \
            f"All flight number variations should normalize consistently: {normalized_values}"
        
        # Property: Normalized value should be uppercase
        assert normalized_values[0].isupper(), \
            "Normalized flight number should be uppercase"
        
        # Property: Normalized value should match expected format
        assert normalized_values[0] == flight_number.upper(), \
            "Normalized flight number should match uppercase input"
    
    @given(
        date=st.dates(min_value=datetime(2024, 1, 1).date(), max_value=datetime(2027, 12, 31).date()),
    )
    @settings(max_examples=50, deadline=None)
    def test_date_validation_consistency(self, date):
        """
        Property 3.3: Date validation is consistent for ISO format
        
        For any valid date in ISO format, the model should validate it
        consistently and preserve the exact format.
        
        Validates: Requirements 1.4, 1.10, 2.1
        """
        date_iso = date.isoformat()
        flight_number = "EY123"
        event = "test event"
        
        # Create multiple FlightInfo instances with the same date
        flight_info_1 = FlightInfo(
            flight_number=flight_number,
            date=date_iso,
            disruption_event=event
        )
        
        flight_info_2 = FlightInfo(
            flight_number=flight_number,
            date=date_iso,
            disruption_event=event
        )
        
        # Property: Date should be preserved exactly
        assert flight_info_1.date == date_iso, \
            "Date should be preserved in ISO format"
        assert flight_info_2.date == date_iso, \
            "Date should be preserved consistently"
        assert flight_info_1.date == flight_info_2.date, \
            "Date should be identical across instances"
    
    @given(
        event=st.text(min_size=5, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'),
            whitelist_characters=',-.'
        ))
    )
    @settings(max_examples=50, deadline=None)
    def test_disruption_event_normalization_consistency(self, event):
        """
        Property 3.4: Disruption event normalization is consistent
        
        For any valid disruption event, the model should normalize it
        consistently by stripping whitespace.
        
        Validates: Requirements 1.5, 2.1
        """
        # Skip empty or whitespace-only events
        if not event.strip():
            return
        
        flight_number = "EY123"
        date_iso = "2026-01-20"
        
        # Test various whitespace combinations
        variations = [
            event,
            f"  {event}",
            f"{event}  ",
            f"  {event}  ",
            f"\t{event}\t",
            f"\n{event}\n",
        ]
        
        normalized_values = []
        for variation in variations:
            flight_info = FlightInfo(
                flight_number=flight_number,
                date=date_iso,
                disruption_event=variation
            )
            normalized_values.append(flight_info.disruption_event)
        
        # Property: All variations should normalize to the same value
        assert len(set(normalized_values)) == 1, \
            f"All event variations should normalize consistently: {normalized_values}"
        
        # Property: Normalized value should be stripped
        assert normalized_values[0] == event.strip(), \
            "Normalized event should have whitespace stripped"
    
    @given(
        flight_number=st.from_regex(r'EY[0-9]{3,4}', fullmatch=True),
        date=st.dates(min_value=datetime(2024, 1, 1).date(), max_value=datetime(2027, 12, 31).date()),
        event=st.sampled_from([
            "mechanical failure",
            "weather delay",
            "crew shortage",
        ])
    )
    @settings(max_examples=50, deadline=None)
    def test_complete_flight_info_extraction_consistency(self, flight_number, date, event):
        """
        Property 3.5: Complete FlightInfo extraction is consistent
        
        For the same flight information provided in different formats,
        the model should produce identical normalized output.
        
        Validates: Requirements 1.1-1.15, 2.1
        """
        date_iso = date.isoformat()
        
        # Create FlightInfo with various input formats
        variations = [
            # Standard format
            FlightInfo(
                flight_number=flight_number,
                date=date_iso,
                disruption_event=event
            ),
            # Lowercase flight number
            FlightInfo(
                flight_number=flight_number.lower(),
                date=date_iso,
                disruption_event=event
            ),
            # With whitespace
            FlightInfo(
                flight_number=f"  {flight_number}  ",
                date=date_iso,
                disruption_event=f"  {event}  "
            ),
            # Mixed case
            FlightInfo(
                flight_number=flight_number.capitalize(),
                date=date_iso,
                disruption_event=event
            ),
        ]
        
        # Property: All variations should produce identical normalized output
        normalized_flight_numbers = [v.flight_number for v in variations]
        normalized_dates = [v.date for v in variations]
        normalized_events = [v.disruption_event for v in variations]
        
        assert len(set(normalized_flight_numbers)) == 1, \
            f"Flight numbers should normalize consistently: {normalized_flight_numbers}"
        assert len(set(normalized_dates)) == 1, \
            f"Dates should be consistent: {normalized_dates}"
        assert len(set(normalized_events)) == 1, \
            f"Events should normalize consistently: {normalized_events}"
        
        # Property: Normalized values should match expected format
        assert normalized_flight_numbers[0] == flight_number.upper(), \
            "Flight number should be uppercase"
        assert normalized_dates[0] == date_iso, \
            "Date should be in ISO format"
        assert normalized_events[0] == event.strip(), \
            "Event should be stripped"
    
    @given(
        flight_number=st.from_regex(r'EY[0-9]{3,4}', fullmatch=True),
    )
    @settings(max_examples=30, deadline=None)
    def test_flight_info_serialization_consistency(self, flight_number):
        """
        Property 3.6: FlightInfo serialization is consistent
        
        For the same flight information, serialization to dict should
        produce identical results.
        
        Validates: Requirements 2.1
        """
        date_iso = "2026-01-20"
        event = "mechanical failure"
        
        # Create two identical FlightInfo instances
        flight_info_1 = FlightInfo(
            flight_number=flight_number,
            date=date_iso,
            disruption_event=event
        )
        
        flight_info_2 = FlightInfo(
            flight_number=flight_number.lower(),  # Different case
            date=date_iso,
            disruption_event=event
        )
        
        # Serialize to dict
        dict_1 = flight_info_1.model_dump()
        dict_2 = flight_info_2.model_dump()
        
        # Property: Serialized dicts should be identical
        assert dict_1 == dict_2, \
            f"Serialized FlightInfo should be identical: {dict_1} vs {dict_2}"
        
        # Property: Serialized dict should contain normalized values
        assert dict_1["flight_number"] == flight_number.upper(), \
            "Serialized flight number should be uppercase"
        assert dict_1["date"] == date_iso, \
            "Serialized date should be in ISO format"
        assert dict_1["disruption_event"] == event, \
            "Serialized event should be normalized"


# ============================================================================
# Other Schema Model Tests
# ============================================================================


class TestCrewMember:
    """Test CrewMember model"""

    def test_valid_crew_member(self):
        """Test CrewMember with valid inputs"""
        crew = CrewMember(
            crew_id="C001",
            crew_name="John Doe",
            duty_hours_used=8.5,
            fdp_remaining=3.5,
            fdp_margin_percentage=29.2,
            location="AUH",
            roster_status="available",
            qualifications_valid=True,
        )

        assert crew.crew_id == "C001"
        assert crew.duty_hours_used == 8.5
        assert crew.qualifications_valid is True


class TestViolation:
    """Test Violation model"""

    def test_valid_violation(self):
        """Test Violation with valid inputs"""
        violation = Violation(
            violation_id="V001",
            type="FDP_EXCEEDED",
            severity="blocking",
            affected_crew=["C001", "C002"],
            description="Flight duty period exceeded",
            actual_value="12.5 hours",
            limit_value="12.0 hours",
            deficit="0.5 hours",
            regulation="EASA FTL",
            mitigation="Replace crew members",
        )

        assert violation.severity == "blocking"
        assert len(violation.affected_crew) == 2


class TestCrewComplianceOutput:
    """Test CrewComplianceOutput model"""

    def test_valid_crew_compliance_output(self):
        """Test CrewComplianceOutput with valid inputs"""
        output = CrewComplianceOutput(
            assessment="APPROVED",
            flight_id="FL123",
            regulatory_framework="EASA FTL",
            timestamp=datetime.now(timezone.utc).isoformat(),
            crew_roster={},
            violations=[],
            recommendations=["Proceed with current crew"],
            reasoning="All crew members meet requirements",
        )

        assert output.agent == "crew_compliance"
        assert output.assessment == "APPROVED"
        assert output.data_source == "database_tools"


class TestMaintenanceOutput:
    """Test MaintenanceOutput model"""

    def test_valid_maintenance_output(self):
        """Test MaintenanceOutput with valid inputs"""
        output = MaintenanceOutput(
            assessment="REQUIRES_MAINTENANCE",
            aircraft_id="A320-001",
            mel_status="ACTIVE",
            maintenance_constraints=[],
            recommendations=["Schedule inspection"],
            reasoning="MEL item requires attention",
        )

        assert output.agent == "maintenance"
        assert output.assessment == "REQUIRES_MAINTENANCE"


class TestRegulatoryOutput:
    """Test RegulatoryOutput model"""

    def test_valid_regulatory_output(self):
        """Test RegulatoryOutput with valid inputs"""
        output = RegulatoryOutput(
            assessment="APPROVED",
            regulatory_constraints=[],
            curfew_status="COMPLIANT",
            slot_status="AVAILABLE",
            recommendations=["Proceed as planned"],
            reasoning="All regulatory requirements met",
        )

        assert output.agent == "regulatory"
        assert output.curfew_status == "COMPLIANT"


class TestOrchestratorValidation:
    """Test OrchestratorValidation model"""

    def test_valid_orchestrator_validation(self):
        """Test OrchestratorValidation with valid inputs"""
        validation = OrchestratorValidation(
            is_valid=True,
            missing_fields=[],
            validation_errors=[],
            required_fields=["flight_number", "date", "disruption_event"],
        )

        assert validation.is_valid is True
        assert len(validation.missing_fields) == 0

    def test_invalid_orchestrator_validation(self):
        """Test OrchestratorValidation with validation errors"""
        validation = OrchestratorValidation(
            is_valid=False,
            missing_fields=["date"],
            validation_errors=["Invalid flight number format"],
            required_fields=["flight_number", "date", "disruption_event"],
        )

        assert validation.is_valid is False
        assert "date" in validation.missing_fields
        assert len(validation.validation_errors) == 1


class TestOrchestratorOutput:
    """Test OrchestratorOutput model"""

    def test_valid_orchestrator_output(self):
        """Test OrchestratorOutput with valid inputs"""
        validation = OrchestratorValidation(
            is_valid=True, required_fields=["flight_number", "date", "disruption_event"]
        )

        output = OrchestratorOutput(
            status="success",
            validation=validation,
            safety_assessments=[],
            business_assessments=[],
            aggregated_recommendations=["Proceed with caution"],
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_duration_seconds=25.5,
        )

        assert output.status == "success"
        assert output.total_duration_seconds == 25.5
