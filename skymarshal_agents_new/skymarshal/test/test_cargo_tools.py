"""
Unit tests for Cargo Agent DynamoDB query tools.

Tests verify that:
1. Tools are properly defined with correct signatures
2. Tools use correct GSIs for queries
3. Tools handle missing data gracefully
4. Tools only access authorized tables
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents.cargo.agent import (
    query_flight,
    query_cargo_manifest,
    query_shipment_details,
    query_shipment_by_awb,
)


class TestCargoTools:
    """Test suite for Cargo Agent DynamoDB query tools."""

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_flight_success(self, mock_boto3):
        """Test successful flight query using flight-number-date-index GSI."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "flight_id": "EY123-20260120",
                    "flight_number": "EY123",
                    "aircraft_registration": "A6-APX",
                    "origin_airport_id": "AUH",
                    "destination_airport_id": "LHR",
                    "scheduled_departure": "2026-01-20T10:00:00Z",
                    "scheduled_arrival": "2026-01-20T14:30:00Z",
                    "status": "scheduled",
                }
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Verify
        assert result is not None
        assert result["flight_id"] == "EY123-20260120"
        assert result["flight_number"] == "EY123"
        assert result["aircraft_registration"] == "A6-APX"

        # Verify correct GSI used
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == "flight-number-date-index"

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_flight_not_found(self, mock_boto3):
        """Test flight query when flight doesn't exist."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})

        # Verify
        assert result is None

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_cargo_manifest_success(self, mock_boto3):
        """Test successful cargo manifest query using flight-loading-index GSI."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "assignment_id": "ASSIGN-001",
                    "flight_id": "EY123-20260120",
                    "shipment_id": "SHP-12345",
                    "loading_status": "loaded",
                    "weight_kg": 850,
                    "priority": "high",
                },
                {
                    "assignment_id": "ASSIGN-002",
                    "flight_id": "EY123-20260120",
                    "shipment_id": "SHP-12346",
                    "loading_status": "loaded",
                    "weight_kg": 1200,
                    "priority": "standard",
                },
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_cargo_manifest.invoke({"flight_id": "EY123-20260120"})

        # Verify
        assert len(result) == 2
        assert result[0]["shipment_id"] == "SHP-12345"
        assert result[1]["weight_kg"] == 1200

        # Verify correct GSI used
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs["IndexName"] == "flight-loading-index"

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_cargo_manifest_empty(self, mock_boto3):
        """Test cargo manifest query when no cargo exists."""
        # Setup mock
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_cargo_manifest.invoke({"flight_id": "EY123-20260120"})

        # Verify
        assert result == []

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_shipment_details_success(self, mock_boto3):
        """Test successful shipment details query."""
        # Setup mock
        mock_table = Mock()
        mock_table.get_item.return_value = {
            "Item": {
                "shipment_id": "SHP-12345",
                "awb_number": "607-12345678",
                "commodity_type_id": "PHARMA",
                "weight_kg": 850,
                "value_usd": 125000,
                "temperature_requirement": "2-8C",
                "special_handling_codes": ["RRW", "PER"],
                "shipper_id": "SHIP-001",
                "consignee_id": "CONS-001",
                "origin_airport": "AUH",
                "destination_airport": "LHR",
            }
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_shipment_details.invoke({"shipment_id": "SHP-12345"})

        # Verify
        assert result is not None
        assert result["shipment_id"] == "SHP-12345"
        assert result["awb_number"] == "607-12345678"
        assert result["value_usd"] == 125000
        assert "RRW" in result["special_handling_codes"]

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_shipment_details_not_found(self, mock_boto3):
        """Test shipment details query when shipment doesn't exist."""
        # Setup mock
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_shipment_details.invoke({"shipment_id": "SHP-99999"})

        # Verify
        assert result is None

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_shipment_by_awb_success(self, mock_boto3):
        """Test successful shipment query by AWB number."""
        # Setup mock
        mock_table = Mock()
        mock_table.scan.return_value = {
            "Items": [
                {
                    "shipment_id": "SHP-12345",
                    "awb_number": "607-12345678",
                    "commodity_type_id": "PHARMA",
                    "weight_kg": 850,
                    "value_usd": 125000,
                }
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_shipment_by_awb.invoke({"awb_number": "607-12345678"})

        # Verify
        assert result is not None
        assert result["shipment_id"] == "SHP-12345"
        assert result["awb_number"] == "607-12345678"

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_shipment_by_awb_not_found(self, mock_boto3):
        """Test shipment query by AWB when shipment doesn't exist."""
        # Setup mock
        mock_table = Mock()
        mock_table.scan.return_value = {"Items": []}
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute
        result = query_shipment_by_awb.invoke({"awb_number": "607-99999999"})

        # Verify
        assert result is None

    def test_tool_table_access_restrictions(self):
        """Test that cargo agent only accesses authorized tables."""
        from database.constants import AGENT_TABLE_ACCESS

        authorized_tables = AGENT_TABLE_ACCESS["cargo"]

        # Verify cargo agent has access to correct tables
        assert "flights" in authorized_tables
        assert "CargoFlightAssignments" in authorized_tables
        assert "CargoShipments" in authorized_tables

        # Verify cargo agent does NOT have access to unauthorized tables
        assert "bookings" not in authorized_tables
        assert "CrewRoster" not in authorized_tables
        assert "MaintenanceWorkOrders" not in authorized_tables

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_flight_uses_correct_table(self, mock_boto3):
        """Test that query_flight uses the flights table."""
        # Setup mock
        mock_dynamodb = Mock()
        mock_boto3.return_value = mock_dynamodb
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table

        # Execute
        query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Verify correct table accessed
        mock_dynamodb.Table.assert_called_once_with("flights")

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_cargo_manifest_uses_correct_table(self, mock_boto3):
        """Test that query_cargo_manifest uses CargoFlightAssignments table."""
        # Setup mock
        mock_dynamodb = Mock()
        mock_boto3.return_value = mock_dynamodb
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table

        # Execute
        query_cargo_manifest.invoke({"flight_id": "EY123-20260120"})

        # Verify correct table accessed
        mock_dynamodb.Table.assert_called_once_with("CargoFlightAssignments")

    @patch("agents.cargo.agent.boto3.resource")
    def test_query_shipment_details_uses_correct_table(self, mock_boto3):
        """Test that query_shipment_details uses CargoShipments table."""
        # Setup mock
        mock_dynamodb = Mock()
        mock_boto3.return_value = mock_dynamodb
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_dynamodb.Table.return_value = mock_table

        # Execute
        query_shipment_details.invoke({"shipment_id": "SHP-12345"})

        # Verify correct table accessed
        mock_dynamodb.Table.assert_called_once_with("CargoShipments")
