"""
Unit tests for Regulatory Agent natural language processing.

Tests verify that:
1. Agent extracts flight information from natural language prompts
2. Agent handles various date formats
3. Agent handles missing or invalid prompts
4. Agent uses structured output correctly
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from agents.regulatory.agent import analyze_regulatory
from agents.schemas import FlightInfo


class TestRegulatoryNaturalLanguage:
    """Test suite for regulatory agent natural language processing"""

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_extract_flight_info_standard_format(self, mock_create_agent):
        """Test extraction of flight info from standard format prompt"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                Mock(content={
                    "agent": "regulatory",
                    "assessment": "COMPLIANT",
                    "recommendations": ["Flight cleared for dispatch"],
                    "confidence": 0.9,
                    "binding_constraints": [],
                    "reasoning": "No regulatory violations detected",
                    "data_sources": ["DynamoDB queries"]
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
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify extraction was called
        mock_llm.with_structured_output.assert_called_once_with(FlightInfo)
        mock_structured_llm.ainvoke.assert_called_once()

        # Verify extracted info in response
        assert result["extracted_flight_info"]["flight_number"] == "EY123"
        assert result["extracted_flight_info"]["date"] == "2026-01-20"
        assert result["extracted_flight_info"]["disruption_event"] == "mechanical failure"

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_extract_flight_info_numeric_date(self, mock_create_agent):
        """Test extraction with numeric date format"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY456",
            date="2026-01-20",
            disruption_event="weather delay"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response with proper content structure
        mock_final_message = Mock()
        mock_final_message.content = {
            "agent": "regulatory",
            "assessment": "COMPLIANT",
            "recommendations": ["Analysis complete"],
            "confidence": 0.9,
            "binding_constraints": [],
            "reasoning": "Test",
            "data_sources": []
        }
        mock_final_message.tool_calls = []
        
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [mock_final_message]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "EY456 on 20/01/2026 has weather delay",
            "phase": "initial"
        }

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify
        assert result["extracted_flight_info"]["flight_number"] == "EY456"
        assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_extract_flight_info_relative_date(self, mock_create_agent):
        """Test extraction with relative date (yesterday, today, tomorrow)"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY789",
            date="2026-01-19",  # Yesterday
            disruption_event="curfew risk"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response with proper content structure
        mock_final_message = Mock()
        mock_final_message.content = {
            "agent": "regulatory",
            "assessment": "COMPLIANT",
            "recommendations": ["Analysis complete"],
            "confidence": 0.9,
            "binding_constraints": [],
            "reasoning": "Test",
            "data_sources": []
        }
        mock_final_message.tool_calls = []
        
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [mock_final_message]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY789 yesterday had curfew risk",
            "phase": "initial"
        }

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify
        assert result["extracted_flight_info"]["flight_number"] == "EY789"
        assert result["extracted_flight_info"]["date"] == "2026-01-19"

    @pytest.mark.asyncio
    async def test_missing_user_prompt(self):
        """Test error handling when user_prompt is missing"""
        # Mock LLM
        mock_llm = AsyncMock()

        # Test payload without user_prompt
        payload = {"phase": "initial"}

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify error response
        assert result["status"] == "error"
        assert result["agent_name"] == "regulatory"
        assert "No user prompt provided" in result["reasoning"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_extraction_failure(self):
        """Test error handling when extraction fails"""
        # Mock LLM that fails extraction
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke.side_effect = Exception("Extraction failed")
        mock_llm.with_structured_output.return_value = mock_structured_llm

        # Test payload
        payload = {
            "user_prompt": "Invalid prompt without flight info",
            "phase": "initial"
        }

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify error response
        assert result["status"] == "error"
        assert result["agent_name"] == "regulatory"
        assert "Failed to extract flight information" in result["reasoning"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_curfew_violation_prompt(self, mock_create_agent):
        """Test extraction and analysis of curfew violation scenario"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY123",
            date="2026-01-30",
            disruption_event="2 hour delay causing curfew risk at LHR"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response with curfew violation
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                Mock(content={
                    "agent": "regulatory",
                    "assessment": "VIOLATIONS_DETECTED",
                    "recommendations": ["Cannot delay - would violate LHR curfew"],
                    "confidence": 0.95,
                    "binding_constraints": ["Arrival must be before 23:00 GMT"],
                    "reasoning": "2 hour delay would cause arrival after curfew",
                    "data_sources": ["DynamoDB queries", "Curfew database"]
                })
            ]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 30th has 2 hour delay causing curfew risk at LHR",
            "phase": "initial"
        }

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify
        assert result["extracted_flight_info"]["flight_number"] == "EY123"
        assert "curfew" in result["extracted_flight_info"]["disruption_event"].lower()
        assert result["assessment"] == "VIOLATIONS_DETECTED"

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_notam_scenario_prompt(self, mock_create_agent):
        """Test extraction and analysis of NOTAM scenario"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY456",
            date="2026-01-30",
            disruption_event="runway closure at destination"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response with NOTAM impact
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                Mock(content={
                    "agent": "regulatory",
                    "assessment": "VIOLATIONS_DETECTED",
                    "recommendations": ["Use alternate runway", "Expect delays"],
                    "confidence": 0.9,
                    "binding_constraints": [],
                    "reasoning": "NOTAM indicates runway closure, alternate available",
                    "data_sources": ["DynamoDB queries", "NOTAM database"]
                })
            ]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "EY456 on 30/01/2026 affected by runway closure at destination",
            "phase": "initial"
        }

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify
        assert result["extracted_flight_info"]["flight_number"] == "EY456"
        assert "runway closure" in result["extracted_flight_info"]["disruption_event"].lower()

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_revision_phase_with_other_recommendations(self, mock_create_agent):
        """Test agent behavior in revision phase with other agents' recommendations"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                Mock(content={
                    "agent": "regulatory",
                    "assessment": "COMPLIANT",
                    "recommendations": ["Revised: Approve delay with curfew buffer"],
                    "confidence": 0.95,
                    "binding_constraints": ["Depart before 15:30 UTC"],
                    "reasoning": "After reviewing network impact, delay acceptable with early departure",
                    "data_sources": ["DynamoDB queries"]
                })
            ]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload with other recommendations
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "revision",
            "other_recommendations": {
                "maintenance": {
                    "recommendation": "Aircraft requires 2 hour inspection",
                    "confidence": 0.9
                },
                "network": {
                    "recommendation": "Delay would cascade to 3 downstream flights",
                    "confidence": 0.85
                }
            }
        }

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify agent was invoked
        assert mock_agent.ainvoke.called
        
        # Verify extracted flight info is present
        assert "extracted_flight_info" in result
        assert result["extracted_flight_info"]["flight_number"] == "EY123"

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_tools_passed_to_agent(self, mock_create_agent):
        """Test that regulatory tools are passed to agent"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [Mock(content="Analysis complete")]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Mock MCP tools with proper name attribute
        mock_mcp_tool = Mock()
        mock_mcp_tool.name = "mcp_tool_1"
        mock_mcp_tools = [mock_mcp_tool]

        # Execute
        result = await analyze_regulatory(payload, mock_llm, mock_mcp_tools)

        # Verify create_agent was called with tools
        assert mock_create_agent.called
        call_kwargs = mock_create_agent.call_args[1]
        tools = call_kwargs["tools"]
        
        # Verify regulatory tools included (4 tools: query_flight, query_crew_roster, query_maintenance_work_orders, query_weather)
        assert len(tools) >= 4  # At least 4 regulatory tools
        
        # Verify MCP tools included
        assert any(tool.name == "mcp_tool_1" for tool in tools)

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_response_includes_timestamp(self, mock_create_agent):
        """Test that response includes ISO 8601 timestamp"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="mechanical failure"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [Mock(content="Analysis complete")]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY123 on January 20th had a mechanical failure",
            "phase": "initial"
        }

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify timestamp
        assert "timestamp" in result
        # Verify it's ISO 8601 format
        datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_atc_restriction_prompt(self, mock_create_agent):
        """Test extraction and analysis of ATC restriction scenario"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY789",
            date="2026-01-30",
            disruption_event="ground stop at destination"
        ))
        mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

        # Mock agent response with ATC restriction
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [
                Mock(content={
                    "agent": "regulatory",
                    "assessment": "CANNOT_DISPATCH",
                    "recommendations": ["Wait for ground stop to clear"],
                    "confidence": 1.0,
                    "binding_constraints": ["Ground stop active until 16:00 UTC"],
                    "reasoning": "ATC ground stop prevents departure",
                    "data_sources": ["DynamoDB queries", "ATC database"]
                })
            ]
        })
        mock_create_agent.return_value = mock_agent

        # Test payload
        payload = {
            "user_prompt": "Flight EY789 on January 30th affected by ground stop at destination",
            "phase": "initial"
        }

        # Execute
        result = await analyze_regulatory(payload, mock_llm, [])

        # Verify
        assert result["extracted_flight_info"]["flight_number"] == "EY789"
        assert "ground stop" in result["extracted_flight_info"]["disruption_event"].lower()
        assert result["assessment"] == "CANNOT_DISPATCH"

    @pytest.mark.asyncio
    @patch('agents.regulatory.agent.create_agent')
    async def test_multiple_date_formats(self, mock_create_agent):
        """Test extraction with various date formats"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        
        test_cases = [
            ("Flight EY123 on 20th January 2026", "2026-01-20"),
            ("EY456 on Jan 20", "2026-01-20"),
            ("Flight EY789 tomorrow", "2026-02-02"),  # Assuming today is 2026-02-01
        ]

        for prompt, expected_date in test_cases:
            mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
                flight_number="EY123",
                date=expected_date,
                disruption_event="test"
            ))
            mock_llm.with_structured_output = Mock(return_value=mock_structured_llm)

            # Mock agent response with proper content structure
            mock_final_message = Mock()
            mock_final_message.content = {
                "agent": "regulatory",
                "assessment": "COMPLIANT",
                "recommendations": ["Analysis complete"],
                "confidence": 0.9,
                "binding_constraints": [],
                "reasoning": "Test",
                "data_sources": []
            }
            mock_final_message.tool_calls = []
            
            mock_agent = AsyncMock()
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [mock_final_message]
            })
            mock_create_agent.return_value = mock_agent

            # Test payload
            payload = {
                "user_prompt": prompt,
                "phase": "initial"
            }

            # Execute
            result = await analyze_regulatory(payload, mock_llm, [])

            # Verify date was extracted (format may vary based on LLM)
            assert "date" in result["extracted_flight_info"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
