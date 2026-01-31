"""
Unit Tests for Finance Agent DynamoDB Query Tools

Feature: skymarshal-multi-round-orchestration
Task: 13.4 Update Finance Agent
Validates: Requirements 7.7, 7.1

Tests that the Finance agent's DynamoDB query tools are correctly defined
and use appropriate GSIs for efficient querying.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents.finance.agent import (
    query_flight,
    query_passenger_bookings,
    query_cargo_revenue,
    query_maintenance_costs,
    get_current_datetime_tool,
)
from database.constants import (
    FLIGHTS_TABLE,
    BOOKINGS_TABLE,
    CARGO_FLIGHT_ASSIGNMENTS_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_ID_INDEX,
    FLIGHT_LOADING_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
)


class TestFinanceAgentTools:
    """Test Finance agent tool definitions."""

    def test_query_flight_tool_exists(self):
        """Test that query_flight tool is defined."""
        assert callable(query_flight.func)
        assert query_flight.name == "query_flight"
        assert "flight_number" in query_flight.description.lower()

    def test_query_passenger_bookings_tool_exists(self):
        """Test that query_passenger_bookings tool is defined."""
        assert callable(query_passenger_bookings.func)
        assert query_passenger_bookings.name == "query_passenger_bookings"
        assert "booking" in query_passenger_bookings.description.lower()

    def test_query_cargo_revenue_tool_exists(self):
        """Test that query_cargo_revenue tool is defined."""
        assert callable(query_cargo_revenue.func)
        assert query_cargo_revenue.name == "query_cargo_revenue"
        assert "cargo" in query_cargo_revenue.description.lower()

    def test_query_maintenance_costs_tool_exists(self):
        """Test that query_maintenance_costs tool is defined."""
        assert callable(query_maintenance_costs.func)
        assert query_maintenance_costs.name == "query_maintenance_costs"
        assert "maintenance" in query_maintenance_costs.description.lower()

    def test_get_current_datetime_tool_exists(self):
        """Test that get_current_datetime_tool is defined."""
        assert callable(get_current_datetime_tool.func)
        assert query_flight.name == "query_flight"


class TestQueryFlightTool:
    """Test query_flight tool implementation."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_flight_uses_gsi(self, mock_boto3):
        """Test that query_flight uses flight-number-date-index GSI."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [{
                "flight_id": "EY123-20260120",
                "flight_number": "EY123",
                "scheduled_departure": "2026-01-20"
            }]
        }
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_flight.func("EY123", "2026-01-20")

        # Verify GSI usage
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == FLIGHT_NUMBER_DATE_INDEX
        assert result is not None
        assert result["flight_id"] == "EY123-20260120"

    @patch("agents.finance.agent.boto3.resource")
    def test_query_flight_not_found(self, mock_boto3):
        """Test query_flight returns None when flight not found."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_flight.func("EY999", "2026-01-20")

        # Verify
        assert result is None

    @patch("agents.finance.agent.boto3.resource")
    def test_query_flight_handles_errors(self, mock_boto3):
        """Test query_flight handles DynamoDB errors gracefully."""
        # Setup mock to raise exception
        mock_boto3.side_effect = Exception("DynamoDB error")

        # Execute
        result = query_flight.func("EY123", "2026-01-20")

        # Verify error handling
        assert result is None


class TestQueryPassengerBookingsTool:
    """Test query_passenger_bookings tool implementation."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_passenger_bookings_uses_gsi(self, mock_boto3):
        """Test that query_passenger_bookings uses flight-id-index GSI."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"booking_id": "B001", "flight_id": "EY123-20260120", "fare_paid": 650},
                {"booking_id": "B002", "flight_id": "EY123-20260120", "fare_paid": 1200}
            ]
        }
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_passenger_bookings.func("EY123-20260120")

        # Verify GSI usage
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == FLIGHT_ID_INDEX
        assert len(result) == 2
        assert result[0]["booking_id"] == "B001"

    @patch("agents.finance.agent.boto3.resource")
    def test_query_passenger_bookings_empty(self, mock_boto3):
        """Test query_passenger_bookings returns empty list when no bookings."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_passenger_bookings.func("EY999-20260120")

        # Verify
        assert result == []


class TestQueryCargoRevenueTool:
    """Test query_cargo_revenue tool implementation."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_cargo_revenue_uses_gsi(self, mock_boto3):
        """Test that query_cargo_revenue uses flight-loading-index GSI."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"assignment_id": "CA001", "flight_id": "EY123-20260120", "revenue_usd": 15000},
                {"assignment_id": "CA002", "flight_id": "EY123-20260120", "revenue_usd": 30000}
            ]
        }
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_cargo_revenue.func("EY123-20260120")

        # Verify GSI usage
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == FLIGHT_LOADING_INDEX
        assert len(result) == 2
        assert result[0]["revenue_usd"] == 15000


class TestQueryMaintenanceCostsTool:
    """Test query_maintenance_costs tool implementation."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_maintenance_costs_uses_gsi(self, mock_boto3):
        """Test that query_maintenance_costs uses aircraft-registration-index GSI."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"workorder_id": "WO001", "aircraft_registration": "A6-APX", "estimated_cost": 25000},
                {"workorder_id": "WO002", "aircraft_registration": "A6-APX", "actual_cost": 30000}
            ]
        }
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_maintenance_costs.func("A6-APX")

        # Verify GSI usage
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == AIRCRAFT_REGISTRATION_INDEX
        assert len(result) == 2
        assert result[0]["estimated_cost"] == 25000


class TestGetCurrentDatetimeTool:
    """Test get_current_datetime_tool implementation."""

    def test_get_current_datetime_returns_iso_format(self):
        """Test that get_current_datetime_tool returns ISO format datetime."""
        result = get_current_datetime_tool.func()
        
        # Verify ISO format (YYYY-MM-DDTHH:MM:SS)
        assert isinstance(result, str)
        assert "T" in result
        assert len(result) >= 19  # Minimum length for ISO datetime


class TestFinanceAgentTableAccess:
    """Test Finance agent table access restrictions."""

    def test_finance_agent_authorized_tables(self):
        """Test that Finance agent only accesses authorized tables."""
        from database.constants import AGENT_TABLE_ACCESS
        
        authorized_tables = AGENT_TABLE_ACCESS.get("finance", [])
        
        # Finance agent should have access to these tables
        assert FLIGHTS_TABLE in authorized_tables
        assert BOOKINGS_TABLE in authorized_tables
        assert CARGO_FLIGHT_ASSIGNMENTS_TABLE in authorized_tables
        assert MAINTENANCE_WORK_ORDERS_TABLE in authorized_tables

    def test_finance_agent_unauthorized_tables(self):
        """Test that Finance agent does NOT access unauthorized tables."""
        from database.constants import (
            AGENT_TABLE_ACCESS,
            CREW_ROSTER_TABLE,
            CREW_MEMBERS_TABLE,
            WEATHER_TABLE,
        )
        
        authorized_tables = AGENT_TABLE_ACCESS.get("finance", [])
        
        # Finance agent should NOT have access to these tables
        assert CREW_ROSTER_TABLE not in authorized_tables
        assert CREW_MEMBERS_TABLE not in authorized_tables
        assert WEATHER_TABLE not in authorized_tables
