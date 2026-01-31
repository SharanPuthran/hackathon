"""
Unit Tests for Regulatory Agent Error Handling

Feature: skymarshal-multi-round-orchestration
Task: 12.3 Handle extraction and query errors gracefully
Validates: Requirements 2.1-2.7

Tests that the Regulatory agent handles errors gracefully:
- Pydantic validation errors during flight info extraction
- Missing flight records in database
- Missing crew roster data
- Missing maintenance work orders
- Missing weather data
- Clear error messages for all failure scenarios
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from pydantic import ValidationError

from agents.regulatory.agent import (
    analyze_regulatory,
    query_flight,
    query_crew_roster,
    query_maintenance_work_orders,
    query_weather,
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
        
        result = await analyze_regulatory(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert result["agent_name"] == "regulatory"
        assert result["confidence"] == 0.0
        assert "user_prompt" in result["error"].lower() or "prompt" in result["error"].lower()
        assert "prompt" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_empty_user_prompt(self):
        """Test handling of empty user prompt."""
        payload = {"user_prompt": "", "phase": "initial"}
        llm = Mock()
        mcp_tools = []
        
        result = await analyze_regulatory(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert result["agent_name"] == "regulatory"
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
        
        result = await analyze_regulatory(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
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
        
        result = await analyze_regulatory(payload, llm, mcp_tools)
        
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
        
        result = await analyze_regulatory(payload, llm, mcp_tools)
        
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
        
        result = await analyze_regulatory(payload, llm, mcp_tools)
        
        assert result["status"] == "error"
        assert "LLM service unavailable" in result["error"]
        assert result["confidence"] == 0.0


class TestQueryFlightErrors:
    """Test error handling in query_flight tool."""

    def test_flight_not_found(self):
        """Test handling when flight is not found in database."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to return empty results
            mock_table = Mock()
            mock_table.query.return_value = {"Items": []}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" in result
            assert "EY999" in result["error"]
            assert "not found" in result["error"].lower()
            assert result["flight_number"] == "EY999"
            assert result["date"] == "2026-01-20"

    def test_query_flight_database_error(self):
        """Test handling of database errors during flight query."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to raise exception
            mock_table = Mock()
            mock_table.query.side_effect = Exception("DynamoDB connection timeout")
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" in result
            assert "connection timeout" in result["error"].lower()
            assert result["flight_number"] == "EY123"
            assert result["date"] == "2026-01-20"

    def test_query_flight_success(self):
        """Test successful flight query returns flight data."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
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
            
            result_str = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" not in result
            assert result["flight_id"] == "1"
            assert result["flight_details"]["flight_number"] == "EY123"


class TestQueryCrewRosterErrors:
    """Test error handling in query_crew_roster tool."""

    def test_crew_roster_empty_results(self):
        """Test handling when crew roster returns empty results."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to return empty results
            mock_table = Mock()
            mock_table.query.return_value = {"Items": []}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_crew_roster.invoke({"flight_id": "999"})
            
            import json
            result = json.loads(result_str)
            
            # Empty roster is valid - just returns 0 crew count
            assert result["flight_id"] == "999"
            assert result["crew_count"] == 0
            assert result["roster"] == []

    def test_query_crew_roster_database_error(self):
        """Test handling of database errors during crew roster query."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to raise exception
            mock_table = Mock()
            mock_table.query.side_effect = Exception("Table not accessible")
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_crew_roster.invoke({"flight_id": "1"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" in result
            assert "table not accessible" in result["error"].lower()
            assert result["flight_id"] == "1"

    def test_query_crew_roster_success(self):
        """Test successful crew roster query returns crew data."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to return crew roster
            mock_table = Mock()
            mock_table.query.return_value = {
                "Items": [
                    {"crew_id": "5", "position": "Captain"},
                    {"crew_id": "6", "position": "First Officer"}
                ]
            }
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_crew_roster.invoke({"flight_id": "1"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" not in result
            assert result["crew_count"] == 2
            assert result["roster"][0]["crew_id"] == "5"
            assert result["roster"][0]["position"] == "Captain"


class TestQueryMaintenanceWorkOrdersErrors:
    """Test error handling in query_maintenance_work_orders tool."""

    def test_maintenance_work_orders_empty_results(self):
        """Test handling when maintenance work orders returns empty results."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to return empty results
            mock_table = Mock()
            mock_table.query.return_value = {"Items": []}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_maintenance_work_orders.invoke({"aircraft_registration": "A6-XYZ"})
            
            import json
            result = json.loads(result_str)
            
            # Empty work orders is valid - just returns 0 count
            assert result["aircraft_registration"] == "A6-XYZ"
            assert result["workorder_count"] == 0
            assert result["workorders"] == []

    def test_query_maintenance_work_orders_database_error(self):
        """Test handling of database errors during maintenance work orders query."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to raise exception
            mock_table = Mock()
            mock_table.query.side_effect = Exception("Access denied")
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_maintenance_work_orders.invoke({"aircraft_registration": "A6-ABC"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" in result
            assert "access denied" in result["error"].lower()
            assert result["aircraft_registration"] == "A6-ABC"

    def test_query_maintenance_work_orders_success(self):
        """Test successful maintenance work orders query returns data."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to return work orders
            mock_table = Mock()
            mock_table.query.return_value = {
                "Items": [
                    {"workorder_id": "WO123", "status": "scheduled"},
                    {"workorder_id": "WO124", "status": "in_progress"}
                ]
            }
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_maintenance_work_orders.invoke({"aircraft_registration": "A6-ABC"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" not in result
            assert result["workorder_count"] == 2
            assert result["workorders"][0]["workorder_id"] == "WO123"


class TestQueryWeatherErrors:
    """Test error handling in query_weather tool."""

    def test_weather_not_found(self):
        """Test handling when weather data is not found."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to return no item
            mock_table = Mock()
            mock_table.get_item.return_value = {}  # No Item key
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_weather.invoke({"airport_code": "XYZ", "forecast_time": "2026-01-20T12:00:00Z"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" in result
            assert "not found" in result["error"].lower()
            assert result["airport_code"] == "XYZ"
            assert result["forecast_time"] == "2026-01-20T12:00:00Z"

    def test_query_weather_database_error(self):
        """Test handling of database errors during weather query."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to raise exception
            mock_table = Mock()
            mock_table.get_item.side_effect = Exception("Network error")
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_weather.invoke({"airport_code": "AUH", "forecast_time": "2026-01-20T12:00:00Z"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" in result
            assert "network error" in result["error"].lower()
            assert result["airport_code"] == "AUH"

    def test_query_weather_success(self):
        """Test successful weather query returns weather data."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            # Mock DynamoDB to return weather data
            mock_table = Mock()
            mock_table.get_item.return_value = {
                "Item": {
                    "airport_code": "AUH",
                    "forecast_time": "2026-01-20T12:00:00Z",
                    "temperature": 25,
                    "visibility": 10000
                }
            }
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_weather.invoke({"airport_code": "AUH", "forecast_time": "2026-01-20T12:00:00Z"})
            
            import json
            result = json.loads(result_str)
            
            assert "error" not in result
            assert result["weather"]["airport_code"] == "AUH"
            assert result["weather"]["temperature"] == 25


class TestErrorMessageClarity:
    """Test that error messages are clear and actionable."""

    def test_flight_not_found_message_clarity(self):
        """Test that flight not found error message is clear."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            mock_table = Mock()
            mock_table.query.return_value = {"Items": []}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})
            
            import json
            result = json.loads(result_str)
            
            # Check message clarity
            assert "error" in result
            assert "EY999" in result["error"]
            assert "2026-01-20" in result["error"]
            assert "not found" in result["error"].lower()

    def test_weather_not_found_message_clarity(self):
        """Test that weather not found error message is clear."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            mock_table = Mock()
            mock_table.get_item.return_value = {}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_weather.invoke({"airport_code": "XYZ", "forecast_time": "2026-01-20T12:00:00Z"})
            
            import json
            result = json.loads(result_str)
            
            # Check message clarity
            assert "error" in result
            assert "XYZ" in result["error"]
            assert "not found" in result["error"].lower()


class TestErrorResponseStructure:
    """Test that error responses have consistent structure."""

    def test_query_flight_error_structure(self):
        """Test query_flight error response has required fields."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            mock_table = Mock()
            mock_table.query.return_value = {"Items": []}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})
            
            import json
            result = json.loads(result_str)
            
            # Required error fields
            assert "error" in result
            assert "flight_number" in result
            assert "date" in result

    def test_query_weather_error_structure(self):
        """Test query_weather error response has required fields."""
        with patch('agents.regulatory.agent.boto3') as mock_boto3:
            mock_table = Mock()
            mock_table.get_item.return_value = {}
            mock_boto3.resource.return_value.Table.return_value = mock_table
            
            result_str = query_weather.invoke({"airport_code": "XYZ", "forecast_time": "2026-01-20T12:00:00Z"})
            
            import json
            result = json.loads(result_str)
            
            # Required error fields
            assert "error" in result
            assert "airport_code" in result
            assert "forecast_time" in result

    @pytest.mark.asyncio
    async def test_agent_error_response_structure(self):
        """Test agent error response has required fields."""
        payload = {"user_prompt": "", "phase": "initial"}
        llm = Mock()
        mcp_tools = []
        
        result = await analyze_regulatory(payload, llm, mcp_tools)
        
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


class TestAgentExecutionErrors:
    """Test error handling during agent execution."""

    @pytest.mark.asyncio
    async def test_agent_execution_exception(self):
        """Test handling of exceptions during agent execution."""
        payload = {
            "user_prompt": "Flight EY123 on Jan 20th",
            "phase": "initial"
        }
        
        # Mock LLM to succeed extraction but fail during agent execution
        llm = Mock()
        structured_llm = AsyncMock()
        
        # Mock successful extraction
        from agents.schemas import FlightInfo
        flight_info = FlightInfo(
            flight_number="EY123",
            date="2026-01-20",
            disruption_event="delay"
        )
        structured_llm.ainvoke.return_value = flight_info
        llm.with_structured_output.return_value = structured_llm
        
        # Mock agent creation to raise exception
        with patch('agents.regulatory.agent.create_agent') as mock_create_agent:
            mock_create_agent.side_effect = RuntimeError("Agent creation failed")
            
            mcp_tools = []
            
            result = await analyze_regulatory(payload, llm, mcp_tools)
            
            assert result["status"] == "error"
            assert result["agent_name"] == "regulatory"
            assert "Agent creation failed" in result["error"]
            assert result["confidence"] == 0.0
            assert "error_type" in result
            assert result["error_type"] == "RuntimeError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
