"""
Unit Tests for Crew Compliance Agent Error Handling

Feature: skymarshal-multi-round-orchestration
Task: 10.3 Handle extraction and query errors gracefully
Validates: Requirements 2.1-2.7

Tests that the Crew Compliance agent handles errors gracefully:
- Pydantic validation errors during flight info extraction
- Missing flight records in database
- Missing crew roster data
- Missing crew member data
- Clear error messages for all failure scenarios
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from pydantic import ValidationError

from agents.crew_compliance.agent import (
    analyze_crew_compliance,
    query_flight,
    query_crew_roster,
    query_crew_members,
)
from agents.schemas import FlightInfo


class TestFlightInfoExtractionErrors:
    """Test error handling during flight information extraction."""

    @pytest.mark.asyncio
    async def test_missing_user_prompt(self):
        """Test handling of missing user prompt in payload."""
        payload = {}  # No user_prompt
        llm = Mock()
        mcp_tools = []
        
        result = await analyze_crew_compliance(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert result["agent_name"] == "crew_compliance"
        assert result["confidence"] == 0.0
        assert "user_prompt" in result["error"].lower()
        assert "prompt" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_empty_user_prompt(self):
        """Test handling of empty user prompt."""
        payload = {"user_prompt": "", "phase": "initial"}
        llm = Mock()
        mcp_tools = []
        
        result = await analyze_crew_compliance(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert result["agent_name"] == "crew_compliance"
        assert result["confidence"] == 0.0
        assert "user_prompt" in result["error"].lower() or "prompt" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_pydantic_validation_error(self):
        """Test handling of Pydantic validation errors."""
        payload = {
            "user_prompt": "Some invalid prompt",
            "phase": "initial"
        }
        
        # Mock LLM to raise ValidationError
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = ValueError("Invalid flight number format")
        llm.with_structured_output.return_value = structured_llm
        
        mcp_tools = []
        
        result = await analyze_crew_compliance(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert result["error_type"] == "ValidationError"
        assert "validated" in result["reasoning"].lower() or "validation" in result["error"].lower()
        assert "Invalid flight number format" in result["reasoning"]
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_missing_flight_number_in_extraction(self):
        """Test handling when flight number cannot be extracted."""
        payload = {
            "user_prompt": "There was a delay yesterday",
            "phase": "initial"
        }
        
        # Mock LLM to raise ValueError (simulating Pydantic validation failure)
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = ValueError("Invalid flight number format: . Expected format: EY followed by 3 or 4 digits")
        llm.with_structured_output.return_value = structured_llm
        
        mcp_tools = []
        
        result = await analyze_crew_compliance(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert "EY" in result["reasoning"]  # Should mention format
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_missing_date_in_extraction(self):
        """Test handling when date cannot be extracted."""
        payload = {
            "user_prompt": "Flight EY123 had a delay",
            "phase": "initial"
        }
        
        # Mock LLM to raise ValueError (simulating Pydantic validation failure for date)
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = ValueError("Invalid date format: . Expected ISO 8601 format (YYYY-MM-DD)")
        llm.with_structured_output.return_value = structured_llm
        
        mcp_tools = []
        
        result = await analyze_crew_compliance(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert "date" in result["reasoning"].lower() or "date" in result["error"].lower()
        assert result["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_generic_extraction_error(self):
        """Test handling of generic extraction errors."""
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th",
            "phase": "initial"
        }
        
        # Mock LLM to raise generic exception
        llm = Mock()
        structured_llm = AsyncMock()
        structured_llm.ainvoke.side_effect = RuntimeError("LLM service unavailable")
        llm.with_structured_output.return_value = structured_llm
        
        mcp_tools = []
        
        result = await analyze_crew_compliance(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert result["error_type"] == "RuntimeError"
        assert "LLM service unavailable" in result["error"]
        assert result["confidence"] == 0.0


class TestQueryFlightErrors:
    """Test error handling in query_flight tool."""

    @patch('agents.crew_compliance.agent.boto3')
    def test_flight_not_found(self, mock_boto3):
        """Test handling when flight is not found in database."""
        # Mock DynamoDB to return empty results
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})
        
        assert "error" in result
        assert result["error"] == "flight_not_found"
        assert "not found" in result["message"].lower()
        assert result["flight_number"] == "EY999"
        assert result["date"] == "2026-01-20"
        assert "suggestion" in result

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_flight_database_error(self, mock_boto3):
        """Test handling of database errors during flight query."""
        # Mock DynamoDB to raise exception
        mock_table = Mock()
        mock_table.query.side_effect = Exception("DynamoDB connection timeout")
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})
        
        assert "error" in result
        assert result["error"] == "query_failed"
        assert "connection timeout" in result["message"].lower()
        assert result["flight_number"] == "EY123"
        assert result["date"] == "2026-01-20"
        assert "error_type" in result
        assert "suggestion" in result

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_flight_success(self, mock_boto3):
        """Test successful flight query returns flight data."""
        # Mock DynamoDB to return flight data
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [{
                "flight_id": "1",
                "flight_number": "EY123",
                "scheduled_departure": "2026-01-20",
                "aircraft_registration": "A6-ABC"
            }]
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})
        
        assert "error" not in result
        assert result["flight_id"] == "1"
        assert result["flight_number"] == "EY123"


class TestQueryCrewRosterErrors:
    """Test error handling in query_crew_roster tool."""

    @patch('agents.crew_compliance.agent.boto3')
    def test_crew_roster_not_found(self, mock_boto3):
        """Test handling when crew roster is not found."""
        # Mock DynamoDB to return empty results
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_roster.invoke({"flight_id": "999"})
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0]
        assert result[0]["error"] == "crew_roster_not_found"
        assert "no crew roster found" in result[0]["message"].lower()
        assert result[0]["flight_id"] == "999"
        assert "suggestion" in result[0]

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_crew_roster_database_error(self, mock_boto3):
        """Test handling of database errors during crew roster query."""
        # Mock DynamoDB to raise exception
        mock_table = Mock()
        mock_table.query.side_effect = Exception("Table not accessible")
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_roster.invoke({"flight_id": "1"})
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert "error" in result[0]
        assert result[0]["error"] == "query_failed"
        assert "table not accessible" in result[0]["message"].lower()
        assert result[0]["flight_id"] == "1"
        assert "error_type" in result[0]
        assert "suggestion" in result[0]

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_crew_roster_success(self, mock_boto3):
        """Test successful crew roster query returns crew data."""
        # Mock DynamoDB to return crew roster
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"crew_id": "5", "position": "Captain"},
                {"crew_id": "6", "position": "First Officer"}
            ]
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_roster.invoke({"flight_id": "1"})
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert "error" not in result[0]
        assert result[0]["crew_id"] == "5"
        assert result[0]["position"] == "Captain"


class TestQueryCrewMembersErrors:
    """Test error handling in query_crew_members tool."""

    @patch('agents.crew_compliance.agent.boto3')
    def test_crew_member_not_found(self, mock_boto3):
        """Test handling when crew member is not found."""
        # Mock DynamoDB to return no item
        mock_table = Mock()
        mock_table.get_item.return_value = {}  # No Item key
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_members.invoke({"crew_id": "999"})
        
        assert "error" in result
        assert result["error"] == "crew_member_not_found"
        assert "not found" in result["message"].lower()
        assert result["crew_id"] == "999"
        assert "suggestion" in result

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_crew_members_database_error(self, mock_boto3):
        """Test handling of database errors during crew member query."""
        # Mock DynamoDB to raise exception
        mock_table = Mock()
        mock_table.get_item.side_effect = Exception("Access denied")
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_members.invoke({"crew_id": "5"})
        
        assert "error" in result
        assert result["error"] == "query_failed"
        assert "access denied" in result["message"].lower()
        assert result["crew_id"] == "5"
        assert "error_type" in result
        assert "suggestion" in result

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_crew_members_success(self, mock_boto3):
        """Test successful crew member query returns member data."""
        # Mock DynamoDB to return crew member
        mock_table = Mock()
        mock_table.get_item.return_value = {
            "Item": {
                "crew_id": "5",
                "crew_name": "John Smith",
                "type_ratings": ["A380"]
            }
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_members.invoke({"crew_id": "5"})
        
        assert "error" not in result
        assert result["crew_id"] == "5"
        assert result["crew_name"] == "John Smith"


class TestErrorMessageClarity:
    """Test that error messages are clear and actionable."""

    @patch('agents.crew_compliance.agent.boto3')
    def test_flight_not_found_message_clarity(self, mock_boto3):
        """Test that flight not found error message is clear."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})
        
        # Check message clarity
        assert "message" in result
        assert "EY999" in result["message"]
        assert "2026-01-20" in result["message"]
        assert "not found" in result["message"].lower()
        
        # Check suggestion is provided
        assert "suggestion" in result
        assert len(result["suggestion"]) > 20  # Meaningful suggestion

    @patch('agents.crew_compliance.agent.boto3')
    def test_crew_roster_not_found_message_clarity(self, mock_boto3):
        """Test that crew roster not found error message is clear."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_roster.invoke({"flight_id": "999"})
        
        # Check message clarity
        assert "message" in result[0]
        assert "999" in result[0]["message"]
        assert "no crew roster" in result[0]["message"].lower()
        
        # Check suggestion is provided
        assert "suggestion" in result[0]
        assert len(result[0]["suggestion"]) > 20

    @patch('agents.crew_compliance.agent.boto3')
    def test_crew_member_not_found_message_clarity(self, mock_boto3):
        """Test that crew member not found error message is clear."""
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_members.invoke({"crew_id": "999"})
        
        # Check message clarity
        assert "message" in result
        assert "999" in result["message"]
        assert "not found" in result["message"].lower()
        
        # Check suggestion is provided
        assert "suggestion" in result
        assert len(result["suggestion"]) > 20


class TestErrorResponseStructure:
    """Test that error responses have consistent structure."""

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_flight_error_structure(self, mock_boto3):
        """Test query_flight error response has required fields."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})
        
        # Required error fields
        assert "error" in result
        assert "message" in result
        assert "suggestion" in result
        assert "flight_number" in result
        assert "date" in result

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_crew_roster_error_structure(self, mock_boto3):
        """Test query_crew_roster error response has required fields."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_roster.invoke({"flight_id": "999"})
        
        # Required error fields
        assert "error" in result[0]
        assert "message" in result[0]
        assert "suggestion" in result[0]
        assert "flight_id" in result[0]

    @patch('agents.crew_compliance.agent.boto3')
    def test_query_crew_members_error_structure(self, mock_boto3):
        """Test query_crew_members error response has required fields."""
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        result = query_crew_members.invoke({"crew_id": "999"})
        
        # Required error fields
        assert "error" in result
        assert "message" in result
        assert "suggestion" in result
        assert "crew_id" in result

    @pytest.mark.asyncio
    async def test_agent_error_response_structure(self):
        """Test agent error response has required fields."""
        payload = {"user_prompt": "", "phase": "initial"}
        llm = Mock()
        mcp_tools = []
        
        result = await analyze_crew_compliance(payload, llm, mcp_tools)
        
        # Required agent error fields
        assert "agent_name" in result
        assert "recommendation" in result
        assert "confidence" in result
        assert "binding_constraints" in result
        assert "reasoning" in result
        assert "data_sources" in result
        assert "timestamp" in result
        assert "status" in result
        assert "error" in result
        assert result["status"] == "error"
        assert result["confidence"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
