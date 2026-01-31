"""
Unit tests for Regulatory Agent DynamoDB query tools.

Tests verify that:
1. Tools are properly defined with correct signatures
2. Tools use correct GSIs from constants module
3. Tools only access authorized tables
4. Error handling works correctly
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from agents.regulatory.agent import (
    query_flight,
    query_crew_roster,
    query_maintenance_work_orders,
    query_weather
)
from database.constants import (
    FLIGHTS_TABLE,
    CREW_ROSTER_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    WEATHER_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
    AGENT_TABLE_ACCESS
)


class TestRegulatoryAgentTools:
    """Test suite for Regulatory Agent DynamoDB query tools."""

    def test_regulatory_agent_table_access_permissions(self):
        """Verify regulatory agent has correct table access permissions."""
        authorized_tables = AGENT_TABLE_ACCESS["regulatory"]
        
        assert FLIGHTS_TABLE in authorized_tables
        assert CREW_ROSTER_TABLE in authorized_tables
        assert MAINTENANCE_WORK_ORDERS_TABLE in authorized_tables
        assert WEATHER_TABLE in authorized_tables
        
        # Verify it doesn't have access to unauthorized tables
        assert "bookings" not in authorized_tables
        assert "Baggage" not in authorized_tables

    @patch('agents.regulatory.agent.boto3')
    def test_query_flight_uses_correct_gsi(self, mock_boto3):
        """Test that query_flight uses the correct GSI."""
        # Setup mock
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [{
                "flight_id": "FL123",
                "flight_number": "EY123",
                "scheduled_departure": "2026-01-20"
            }]
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Execute
        result_json = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})
        result = json.loads(result_json)
        
        # Verify
        mock_boto3.resource.assert_called_with("dynamodb", region_name="us-east-1")
        mock_boto3.resource.return_value.Table.assert_called_with(FLIGHTS_TABLE)
        
        # Verify GSI usage
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == FLIGHT_NUMBER_DATE_INDEX
        
        # Verify result
        assert result["flight_id"] == "FL123"
        assert result["query_method"] == f"GSI: {FLIGHT_NUMBER_DATE_INDEX}"

    @patch('agents.regulatory.agent.boto3')
    def test_query_flight_handles_not_found(self, mock_boto3):
        """Test that query_flight handles flight not found gracefully."""
        # Setup mock - no items returned
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Execute
        result_json = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})
        result = json.loads(result_json)
        
        # Verify error handling
        assert "error" in result
        assert "not found" in result["error"].lower()
        assert result["flight_number"] == "EY999"

    @patch('agents.regulatory.agent.boto3')
    def test_query_crew_roster_uses_correct_gsi(self, mock_boto3):
        """Test that query_crew_roster uses the correct GSI."""
        # Setup mock
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {"crew_id": "C001", "position": "Captain"},
                {"crew_id": "C002", "position": "First Officer"}
            ]
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Execute
        result_json = query_crew_roster.invoke({"flight_id": "FL123"})
        result = json.loads(result_json)
        
        # Verify
        mock_boto3.resource.return_value.Table.assert_called_with(CREW_ROSTER_TABLE)
        
        # Verify GSI usage
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == "flight-position-index"
        
        # Verify result
        assert result["crew_count"] == 2
        assert result["query_method"] == "GSI: flight-position-index"

    @patch('agents.regulatory.agent.boto3')
    def test_query_maintenance_work_orders_uses_correct_gsi(self, mock_boto3):
        """Test that query_maintenance_work_orders uses the correct GSI."""
        # Setup mock
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {"workorder_id": "WO001", "status": "scheduled"}
            ]
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Execute
        result_json = query_maintenance_work_orders.invoke({"aircraft_registration": "A6-APX"})
        result = json.loads(result_json)
        
        # Verify
        mock_boto3.resource.return_value.Table.assert_called_with(MAINTENANCE_WORK_ORDERS_TABLE)
        
        # Verify GSI usage
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == AIRCRAFT_REGISTRATION_INDEX
        
        # Verify result
        assert result["workorder_count"] == 1
        assert result["query_method"] == f"GSI: {AIRCRAFT_REGISTRATION_INDEX}"

    @patch('agents.regulatory.agent.boto3')
    def test_query_weather_uses_direct_key_lookup(self, mock_boto3):
        """Test that query_weather uses direct key lookup."""
        # Setup mock
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "airport_code": "LHR",
                "forecast_time": "2026-01-20T12:00:00Z",
                "temperature": 15,
                "conditions": "Cloudy"
            }
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Execute
        result_json = query_weather.invoke({
            "airport_code": "LHR",
            "forecast_time": "2026-01-20T12:00:00Z"
        })
        result = json.loads(result_json)
        
        # Verify
        mock_boto3.resource.return_value.Table.assert_called_with(WEATHER_TABLE)
        
        # Verify direct key lookup
        mock_table.get_item.assert_called_once()
        call_kwargs = mock_table.get_item.call_args[1]
        assert call_kwargs["Key"]["airport_code"] == "LHR"
        
        # Verify result
        assert result["query_method"] == "Direct key lookup"
        assert result["weather"]["temperature"] == 15

    @patch('agents.regulatory.agent.boto3')
    def test_query_weather_handles_not_found(self, mock_boto3):
        """Test that query_weather handles weather data not found gracefully."""
        # Setup mock - no item returned
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Execute
        result_json = query_weather.invoke({
            "airport_code": "XXX",
            "forecast_time": "2026-01-20T12:00:00Z"
        })
        result = json.loads(result_json)
        
        # Verify error handling
        assert "error" in result
        assert "not found" in result["error"].lower()

    @patch('agents.regulatory.agent.boto3')
    def test_tools_handle_boto3_exceptions(self, mock_boto3):
        """Test that tools handle boto3 exceptions gracefully."""
        # Setup mock to raise exception
        mock_boto3.resource.side_effect = Exception("DynamoDB connection error")
        
        # Test query_flight
        result_json = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})
        result = json.loads(result_json)
        assert "error" in result
        assert "DynamoDB connection error" in result["error"]

    def test_tools_are_langchain_tools(self):
        """Verify that all tools are proper LangChain Tool objects."""
        from langchain_core.tools import BaseTool
        
        # All tools should be LangChain tools
        assert hasattr(query_flight, 'name')
        assert hasattr(query_flight, 'description')
        assert hasattr(query_flight, 'invoke')
        
        assert hasattr(query_crew_roster, 'name')
        assert hasattr(query_maintenance_work_orders, 'name')
        assert hasattr(query_weather, 'name')

    def test_tool_descriptions_are_clear(self):
        """Verify that tool descriptions are clear for LLM understanding."""
        # Check that descriptions exist and are meaningful
        assert len(query_flight.description) > 50
        assert "flight number" in query_flight.description.lower()
        assert "date" in query_flight.description.lower()
        
        assert len(query_crew_roster.description) > 30
        assert "crew" in query_crew_roster.description.lower()
        
        assert len(query_maintenance_work_orders.description) > 30
        assert "maintenance" in query_maintenance_work_orders.description.lower()
        
        assert len(query_weather.description) > 30
        assert "weather" in query_weather.description.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
