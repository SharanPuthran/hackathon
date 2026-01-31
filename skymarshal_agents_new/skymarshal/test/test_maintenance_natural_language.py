"""
Unit tests for Maintenance Agent natural language processing.

Tests verify that:
1. Agent extracts flight information from natural language prompts
2. Agent handles various date formats
3. Agent handles missing or invalid prompts
4. Agent uses structured output correctly
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from agents.maintenance.agent import analyze_maintenance
from agents.schemas import FlightInfo


class TestMaintenanceNaturalLanguage:
    """Test suite for maintenance agent natural language processing"""

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
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
                    "agent_name": "maintenance",
                    "recommendation": "Aircraft requires inspection",
                    "confidence": 0.9,
                    "binding_constraints": ["Aircraft grounded until inspection complete"],
                    "reasoning": "Mechanical failure requires thorough inspection",
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
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify extraction was called
        mock_llm.with_structured_output.assert_called_once_with(FlightInfo)
        mock_structured_llm.ainvoke.assert_called_once()

        # Verify extracted info in response
        assert result["extracted_flight_info"]["flight_number"] == "EY123"
        assert result["extracted_flight_info"]["date"] == "2026-01-20"
        assert result["extracted_flight_info"]["disruption_event"] == "mechanical failure"

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_extract_flight_info_numeric_date(self, mock_create_agent):
        """Test extraction with numeric date format"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY456",
            date="2026-01-20",
            disruption_event="hydraulic issue"
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
            "user_prompt": "EY456 on 20/01/2026 has hydraulic issue",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify
        assert result["extracted_flight_info"]["flight_number"] == "EY456"
        assert result["extracted_flight_info"]["date"] == "2026-01-20"

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_extract_flight_info_relative_date(self, mock_create_agent):
        """Test extraction with relative date (yesterday, today, tomorrow)"""
        # Mock LLM structured output
        mock_llm = AsyncMock()
        mock_structured_llm = AsyncMock()
        mock_structured_llm.ainvoke = AsyncMock(return_value=FlightInfo(
            flight_number="EY789",
            date="2026-01-19",  # Yesterday
            disruption_event="weather radar inoperative"
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
            "user_prompt": "Flight EY789 yesterday had weather radar inoperative",
            "phase": "initial"
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

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
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify error response
        assert result["status"] == "error"
        assert result["agent_name"] == "maintenance"
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
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify error response
        assert result["status"] == "error"
        assert result["agent_name"] == "maintenance"
        assert "Failed to extract flight information" in result["reasoning"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
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
                    "agent_name": "maintenance",
                    "recommendation": "Revised: Aircraft swap recommended",
                    "confidence": 0.95,
                    "binding_constraints": ["Aircraft grounded"],
                    "reasoning": "After reviewing crew compliance concerns, aircraft swap is best option",
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
                "crew_compliance": {
                    "recommendation": "Crew approaching FDP limits",
                    "confidence": 0.9
                },
                "network": {
                    "recommendation": "Delay would cascade to 3 downstream flights",
                    "confidence": 0.85
                }
            }
        }

        # Execute
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify agent was invoked with revision context
        assert mock_agent.ainvoke.called
        call_args = mock_agent.ainvoke.call_args[0][0]
        system_message = call_args["messages"][0]["content"]
        
        # Verify revision instructions included
        assert "revision phase" in system_message.lower()
        assert "other agents" in system_message.lower()

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
    async def test_tools_passed_to_agent(self, mock_create_agent):
        """Test that maintenance tools are passed to agent"""
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
        result = await analyze_maintenance(payload, mock_llm, mock_mcp_tools)

        # Verify create_agent was called with tools
        assert mock_create_agent.called
        call_kwargs = mock_create_agent.call_args[1]
        tools = call_kwargs["tools"]
        
        # Verify maintenance tools included (5 tools)
        assert len(tools) >= 5  # At least 5 maintenance tools
        
        # Verify MCP tools included
        assert any(tool.name == "mcp_tool_1" for tool in tools)

    @pytest.mark.asyncio
    @patch('agents.maintenance.agent.create_agent')
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
        result = await analyze_maintenance(payload, mock_llm, [])

        # Verify timestamp
        assert "timestamp" in result
        # Verify it's ISO 8601 format
        datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
