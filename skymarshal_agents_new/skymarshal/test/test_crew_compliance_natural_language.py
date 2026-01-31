"""
Natural Language Prompt Tests for Crew Compliance Agent

Feature: skymarshal-multi-round-orchestration
Task: 10.4 Test with sample natural language prompts
Validates: Requirements 1.1-1.15, 2.1-2.7

Tests that the Crew Compliance agent correctly handles various natural language
prompt phrasings, date formats, and error cases.

Test Categories:
1. Various prompt phrasings
2. Date formats (relative, named, numeric)
3. Error cases (missing info, invalid formats)
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from agents.crew_compliance.agent import analyze_crew_compliance
from agents.schemas import FlightInfo


class TestVariousPromptPhrasings:
    """Test agent handles different ways of expressing the same information."""

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_standard_phrasing(self, mock_boto3):
        """Test: 'Flight EY123 on January 20th had a mechanical failure'"""
        # Mock flight info extraction
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        # Mock agent execution
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [
                Mock(content="Flight EY123 crew is within FDP limits")
            ]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["agent_name"] == "crew_compliance"
            assert result["extracted_flight_info"]["flight_number"] == "EY123"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"
            assert result["extracted_flight_info"]["disruption_event"] == "mechanical failure"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_casual_phrasing(self, mock_boto3):
        """Test: 'EY456 yesterday was delayed 3 hours due to weather'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY456",
            date="2026-01-31",  # LLM resolves "yesterday"
            disruption_event="delayed 3 hours due to weather"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Crew within limits")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "EY456 yesterday was delayed 3 hours due to weather",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["flight_number"] == "EY456"
            assert result["extracted_flight_info"]["date"] == "2026-01-31"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_formal_phrasing(self, mock_boto3):
        """Test: 'Flight EY789 on 20/01/2026 needs crew assessment for 2-hour delay'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY789",
            date="2026-01-20",  # LLM converts 20/01/2026 to ISO format
            disruption_event="2-hour delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Assessment complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY789 on 20/01/2026 needs crew assessment for 2-hour delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["flight_number"] == "EY789"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_minimal_phrasing(self, mock_boto3):
        """Test: 'EY111 today delay'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY111",
            date="2026-02-01",  # LLM resolves "today"
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "EY111 today delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["flight_number"] == "EY111"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_verbose_phrasing(self, mock_boto3):
        """Test: Long descriptive prompt with embedded flight info"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY222",
            date="2026-01-25",
            disruption_event="mechanical issue with engine requiring inspection"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "We have a situation with Flight EY222 scheduled for January 25th. "
                              "There's a mechanical issue with the engine requiring inspection. "
                              "Need crew compliance assessment.",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["flight_number"] == "EY222"
            assert result["extracted_flight_info"]["date"] == "2026-01-25"


class TestDateFormats:
    """Test agent handles various date formats correctly."""

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_relative_date_yesterday(self, mock_boto3):
        """Test relative date: 'yesterday'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-31",  # Yesterday from 2026-02-01
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 yesterday had a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-01-31"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_relative_date_today(self, mock_boto3):
        """Test relative date: 'today'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-02-01",  # Today
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 today has a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-02-01"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_relative_date_tomorrow(self, mock_boto3):
        """Test relative date: 'tomorrow'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-02-02",  # Tomorrow from 2026-02-01
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 tomorrow will have a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-02-02"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_named_date_format_1(self, mock_boto3):
        """Test named date: 'January 20th'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on January 20th had a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_named_date_format_2(self, mock_boto3):
        """Test named date: '20 Jan'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on 20 Jan had a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_named_date_format_3(self, mock_boto3):
        """Test named date: '20th January 2026'"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on 20th January 2026 had a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_numeric_date_format_ddmmyyyy(self, mock_boto3):
        """Test numeric date: '20/01/2026' (European format)"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on 20/01/2026 had a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_numeric_date_format_ddmmyy(self, mock_boto3):
        """Test numeric date: '20-01-26' (short year)"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on 20-01-26 had a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_numeric_date_format_iso(self, mock_boto3):
        """Test numeric date: '2026-01-20' (ISO format)"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on 2026-01-20 had a delay",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"


class TestErrorCases:
    """Test agent handles error cases gracefully."""

    @pytest.mark.asyncio
    async def test_missing_flight_number(self):
        """Test error when flight number is missing from prompt"""
        llm = Mock()
        structured_llm = AsyncMock()
        # Simulate LLM unable to extract flight number
        structured_llm.ainvoke.side_effect = ValueError(
            "Invalid flight number format: . Expected format: EY followed by 3 or 4 digits"
        )
        llm.with_structured_output.return_value = structured_llm
        
        payload = {
            "user_prompt": "There was a delay yesterday",
            "phase": "initial"
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        assert result["status"] == "error"
        assert result["error_type"] == "ValidationError"
        assert "EY" in result["reasoning"]  # Should mention format
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_missing_date(self):
        """Test error when date is missing from prompt"""
        llm = Mock()
        structured_llm = AsyncMock()
        # Simulate LLM unable to extract date
        structured_llm.ainvoke.side_effect = ValueError(
            "Invalid date format: . Expected ISO 8601 format (YYYY-MM-DD)"
        )
        llm.with_structured_output.return_value = structured_llm
        
        payload = {
            "user_prompt": "Flight EY123 had a delay",
            "phase": "initial"
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        assert result["status"] == "error"
        assert "date" in result["reasoning"].lower()
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_invalid_flight_number_format(self):
        """Test error when flight number has invalid format"""
        llm = Mock()
        structured_llm = AsyncMock()
        # Simulate validation error for invalid format
        structured_llm.ainvoke.side_effect = ValueError(
            "Invalid flight number format: ABC123. Expected format: EY followed by 3 or 4 digits"
        )
        llm.with_structured_output.return_value = structured_llm
        
        payload = {
            "user_prompt": "Flight ABC123 on January 20th had a delay",
            "phase": "initial"
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        assert result["status"] == "error"
        assert result["error_type"] == "ValidationError"
        assert "EY" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_empty_prompt(self):
        """Test error when prompt is empty"""
        llm = Mock()
        
        payload = {
            "user_prompt": "",
            "phase": "initial"
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        assert result["status"] == "error"
        assert "user_prompt" in result["error"].lower() or "prompt" in result["error"].lower()
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_missing_prompt_field(self):
        """Test error when user_prompt field is missing"""
        llm = Mock()
        
        payload = {
            "phase": "initial"
            # No user_prompt field
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        assert result["status"] == "error"
        assert "user_prompt" in result["error"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_llm_service_unavailable(self):
        """Test error when LLM service is unavailable"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = RuntimeError("LLM service unavailable")
        llm.with_structured_output.return_value = structured_llm
        
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a delay",
            "phase": "initial"
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        assert result["status"] == "error"
        assert result["error_type"] == "RuntimeError"
        assert "LLM service unavailable" in result["error"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_ambiguous_date(self):
        """Test handling of ambiguous date that LLM cannot resolve"""
        llm = Mock()
        structured_llm = AsyncMock()
        # Simulate LLM unable to resolve ambiguous date
        structured_llm.ainvoke.side_effect = ValueError(
            "Ambiguous date: 'last week'. Please provide a specific date."
        )
        llm.with_structured_output.return_value = structured_llm
        
        payload = {
            "user_prompt": "Flight EY123 last week had a delay",
            "phase": "initial"
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        assert result["status"] == "error"
        assert "date" in result["reasoning"].lower() or "ambiguous" in result["error"].lower()
        assert result["confidence"] == 0.0


class TestRevisionPhase:
    """Test agent handles revision phase correctly."""

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_revision_phase_with_other_recommendations(self, mock_boto3):
        """Test agent receives and processes other agents' recommendations in revision phase"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Revised assessment based on other agents")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
                "phase": "revision",
                "other_recommendations": {
                    "maintenance": "Aircraft requires 4-hour inspection",
                    "network": "Delay will impact 3 downstream flights"
                }
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert result["status"] == "success"
            assert result["agent_name"] == "crew_compliance"
            # Verify agent was invoked with revision instructions
            call_args = agent_mock.ainvoke.call_args
            assert "revision" in str(call_args).lower() or "other agents" in str(call_args).lower()


class TestExtractedFlightInfoInResponse:
    """Test that extracted flight info is included in all responses."""

    @pytest.mark.asyncio
    @patch('agents.crew_compliance.agent.boto3')
    async def test_extracted_info_in_success_response(self, mock_boto3):
        """Test extracted flight info is included in successful response"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.return_value = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        )
        llm.with_structured_output.return_value = structured_llm
        
        agent_mock = AsyncMock()
        agent_mock.ainvoke.return_value = {
            "messages": [Mock(content="Analysis complete")]
        }
        
        with patch('agents.crew_compliance.agent.create_agent', return_value=agent_mock):
            payload = {
                "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
                "phase": "initial"
            }
            
            result = await analyze_crew_compliance(payload, llm, [])
            
            assert "extracted_flight_info" in result
            assert result["extracted_flight_info"]["flight_number"] == "EY123"
            assert result["extracted_flight_info"]["date"] == "2026-01-20"
            assert result["extracted_flight_info"]["disruption_event"] == "mechanical failure"

    @pytest.mark.asyncio
    async def test_extracted_info_null_on_extraction_failure(self):
        """Test extracted flight info is None when extraction fails"""
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = RuntimeError("Extraction failed")
        llm.with_structured_output.return_value = structured_llm
        
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a delay",
            "phase": "initial"
        }
        
        result = await analyze_crew_compliance(payload, llm, [])
        
        assert result["status"] == "error"
        assert result["extracted_flight_info"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
