"""
Unit Tests for Finance Agent Error Handling

Feature: skymarshal-multi-round-orchestration
Task: 13.4 Update Finance Agent
Validates: Requirements 1.13-1.15, 2.5

Tests that the Finance agent handles errors gracefully when data extraction
fails or database queries return no results.
"""

import pytest
from unittest.mock import Mock, patch
from agents.finance.agent import (
    query_flight,
    query_passenger_bookings,
    query_cargo_revenue,
    query_maintenance_costs,
)


class TestFlightNotFoundHandling:
    """Test Finance agent handles missing flight records."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_flight_returns_none_when_not_found(self, mock_boto3):
        """Test that query_flight returns None when flight not found."""
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
    def test_query_flight_handles_invalid_flight_number(self, mock_boto3):
        """Test that query_flight handles invalid flight numbers."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute with invalid flight number
        result = query_flight.func("INVALID", "2026-01-20")

        # Verify - should return None, not raise exception
        assert result is None


class TestDatabaseErrorHandling:
    """Test Finance agent handles database errors gracefully."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_flight_handles_dynamodb_exception(self, mock_boto3):
        """Test that query_flight handles DynamoDB exceptions."""
        # Setup mock to raise exception
        mock_boto3.side_effect = Exception("DynamoDB connection error")

        # Execute
        result = query_flight.func("EY123", "2026-01-20")

        # Verify - should return None, not propagate exception
        assert result is None

    @patch("agents.finance.agent.boto3.resource")
    def test_query_passenger_bookings_handles_exception(self, mock_boto3):
        """Test that query_passenger_bookings handles exceptions."""
        # Setup mock to raise exception
        mock_boto3.side_effect = Exception("DynamoDB error")

        # Execute
        result = query_passenger_bookings.func("EY123-20260120")

        # Verify - should return empty list, not propagate exception
        assert result == []

    @patch("agents.finance.agent.boto3.resource")
    def test_query_cargo_revenue_handles_exception(self, mock_boto3):
        """Test that query_cargo_revenue handles exceptions."""
        # Setup mock to raise exception
        mock_boto3.side_effect = Exception("DynamoDB error")

        # Execute
        result = query_cargo_revenue.func("EY123-20260120")

        # Verify - should return empty list, not propagate exception
        assert result == []

    @patch("agents.finance.agent.boto3.resource")
    def test_query_maintenance_costs_handles_exception(self, mock_boto3):
        """Test that query_maintenance_costs handles exceptions."""
        # Setup mock to raise exception
        mock_boto3.side_effect = Exception("DynamoDB error")

        # Execute
        result = query_maintenance_costs.func("A6-APX")

        # Verify - should return empty list, not propagate exception
        assert result == []


class TestEmptyDataHandling:
    """Test Finance agent handles empty query results."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_passenger_bookings_empty_result(self, mock_boto3):
        """Test that query_passenger_bookings handles empty results."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_passenger_bookings.func("EY123-20260120")

        # Verify
        assert result == []
        assert isinstance(result, list)

    @patch("agents.finance.agent.boto3.resource")
    def test_query_cargo_revenue_empty_result(self, mock_boto3):
        """Test that query_cargo_revenue handles empty results."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_cargo_revenue.func("EY123-20260120")

        # Verify
        assert result == []
        assert isinstance(result, list)

    @patch("agents.finance.agent.boto3.resource")
    def test_query_maintenance_costs_empty_result(self, mock_boto3):
        """Test that query_maintenance_costs handles empty results."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_maintenance_costs.func("A6-APX")

        # Verify
        assert result == []
        assert isinstance(result, list)


class TestMissingFieldHandling:
    """Test Finance agent handles missing fields in query results."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_passenger_bookings_missing_fare_field(self, mock_boto3):
        """Test that query_passenger_bookings handles missing fare_paid field."""
        # Setup mock with incomplete data
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"booking_id": "B001", "flight_id": "EY123-20260120"},  # Missing fare_paid
                {"booking_id": "B002", "flight_id": "EY123-20260120", "fare_paid": 1200}
            ]
        }
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_passenger_bookings.func("EY123-20260120")

        # Verify - should return all items, agent handles missing fields
        assert len(result) == 2
        assert result[0]["booking_id"] == "B001"
        assert "fare_paid" not in result[0]

    @patch("agents.finance.agent.boto3.resource")
    def test_query_cargo_revenue_missing_revenue_field(self, mock_boto3):
        """Test that query_cargo_revenue handles missing revenue_usd field."""
        # Setup mock with incomplete data
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"assignment_id": "CA001", "flight_id": "EY123-20260120"},  # Missing revenue_usd
                {"assignment_id": "CA002", "flight_id": "EY123-20260120", "revenue_usd": 30000}
            ]
        }
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_cargo_revenue.func("EY123-20260120")

        # Verify - should return all items
        assert len(result) == 2
        assert result[0]["assignment_id"] == "CA001"


class TestInvalidInputHandling:
    """Test Finance agent handles invalid inputs."""

    @patch("agents.finance.agent.boto3.resource")
    def test_query_flight_with_empty_flight_number(self, mock_boto3):
        """Test that query_flight handles empty flight number."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute with empty flight number
        result = query_flight.func("", "2026-01-20")

        # Verify - should handle gracefully
        assert result is None or result == []

    @patch("agents.finance.agent.boto3.resource")
    def test_query_flight_with_empty_date(self, mock_boto3):
        """Test that query_flight handles empty date."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute with empty date
        result = query_flight.func("EY123", "")

        # Verify - should handle gracefully
        assert result is None or result == []

    @patch("agents.finance.agent.boto3.resource")
    def test_query_passenger_bookings_with_invalid_flight_id(self, mock_boto3):
        """Test that query_passenger_bookings handles invalid flight_id."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute with invalid flight_id
        result = query_passenger_bookings.func("INVALID-ID")

        # Verify - should return empty list
        assert result == []


class TestPartialDataHandling:
    """Test Finance agent handles partial data scenarios."""

    @patch("agents.finance.agent.boto3.resource")
    def test_flight_found_but_no_bookings(self, mock_boto3):
        """Test scenario where flight exists but has no bookings."""
        # This tests the agent's ability to handle flights with no passengers
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_passenger_bookings.func("EY123-20260120")

        # Verify - empty list is valid (ferry flight, cargo-only, etc.)
        assert result == []

    @patch("agents.finance.agent.boto3.resource")
    def test_flight_found_but_no_cargo(self, mock_boto3):
        """Test scenario where flight exists but has no cargo."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_cargo_revenue.func("EY123-20260120")

        # Verify - empty list is valid (passenger-only flight)
        assert result == []

    @patch("agents.finance.agent.boto3.resource")
    def test_aircraft_with_no_maintenance(self, mock_boto3):
        """Test scenario where aircraft has no maintenance work orders."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute
        result = query_maintenance_costs.func("A6-APX")

        # Verify - empty list is valid (new aircraft, no issues)
        assert result == []


class TestConcurrentQueryHandling:
    """Test Finance agent handles concurrent query scenarios."""

    @patch("agents.finance.agent.boto3.resource")
    def test_multiple_queries_in_sequence(self, mock_boto3):
        """Test that multiple queries can be executed in sequence."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.side_effect = [
            {"Items": [{"flight_id": "EY123-20260120"}]},
            {"Items": [{"booking_id": "B001"}]},
            {"Items": [{"assignment_id": "CA001"}]}
        ]
        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.return_value = mock_dynamodb

        # Execute multiple queries
        flight = query_flight.func("EY123", "2026-01-20")
        bookings = query_passenger_bookings.func("EY123-20260120")
        cargo = query_cargo_revenue.func("EY123-20260120")

        # Verify all queries succeeded
        assert flight is not None
        assert len(bookings) > 0
        assert len(cargo) > 0
