"""
Unit tests for Guest Experience Agent DynamoDB query tools.

Tests verify that:
1. Tools are properly defined with @tool decorator
2. Tools use correct GSIs from constants module
3. Tools only access authorized tables
4. Tools handle errors gracefully
5. Tools return expected data structures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from agents.guest_experience.agent import (
    query_flight,
    query_bookings_by_flight,
    query_bookings_by_passenger,
    query_bookings_by_status,
    query_baggage_by_booking,
    query_baggage_by_location,
    query_passenger,
    query_elite_passengers,
    _convert_decimals,
)
from database.constants import (
    FLIGHTS_TABLE,
    BOOKINGS_TABLE,
    BAGGAGE_TABLE,
    PASSENGERS_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_ID_INDEX,
    BOOKING_INDEX,
    PASSENGER_FLIGHT_INDEX,
    FLIGHT_STATUS_INDEX,
    LOCATION_STATUS_INDEX,
    PASSENGER_ELITE_TIER_INDEX,
)


class TestDecimalConversion:
    """Test Decimal to float conversion utility."""

    def test_convert_decimal_to_float(self):
        """Test converting Decimal to float."""
        result = _convert_decimals(Decimal("123.45"))
        assert result == 123.45
        assert isinstance(result, float)

    def test_convert_dict_with_decimals(self):
        """Test converting dict containing Decimals."""
        data = {"price": Decimal("99.99"), "quantity": Decimal("5")}
        result = _convert_decimals(data)
        assert result == {"price": 99.99, "quantity": 5.0}
        assert isinstance(result["price"], float)

    def test_convert_list_with_decimals(self):
        """Test converting list containing Decimals."""
        data = [Decimal("1.1"), Decimal("2.2"), Decimal("3.3")]
        result = _convert_decimals(data)
        assert result == [1.1, 2.2, 3.3]
        assert all(isinstance(x, float) for x in result)

    def test_convert_nested_structures(self):
        """Test converting nested structures with Decimals."""
        data = {
            "items": [
                {"price": Decimal("10.50"), "count": Decimal("2")},
                {"price": Decimal("20.75"), "count": Decimal("1")},
            ]
        }
        result = _convert_decimals(data)
        assert result["items"][0]["price"] == 10.50
        assert isinstance(result["items"][0]["price"], float)


class TestQueryFlight:
    """Test query_flight tool."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_flight_success(self, mock_dynamodb):
        """Test successful flight query."""
        # Mock DynamoDB response
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "flight_id": "EY123-20260120",
                    "flight_number": "EY123",
                    "scheduled_departure": "2026-01-20",
                    "aircraft_registration": "A6-ABC",
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        # Call tool
        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Verify
        assert result is not None
        assert result["flight_id"] == "EY123-20260120"
        assert result["flight_number"] == "EY123"
        mock_table.query.assert_called_once()
        
        # Verify correct GSI used
        call_args = mock_table.query.call_args
        assert call_args[1]["IndexName"] == FLIGHT_NUMBER_DATE_INDEX

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_flight_not_found(self, mock_dynamodb):
        """Test flight not found."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table

        result = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})

        assert result is None

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_flight_error_handling(self, mock_dynamodb):
        """Test error handling in flight query."""
        mock_table = Mock()
        mock_table.query.side_effect = Exception("DynamoDB error")
        mock_dynamodb.Table.return_value = mock_table

        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        assert result is None


class TestQueryBookingsByFlight:
    """Test query_bookings_by_flight tool."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_bookings_success(self, mock_dynamodb):
        """Test successful bookings query."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "booking_id": "BKG001",
                    "flight_id": "EY123-20260120",
                    "passenger_id": "PAX001",
                    "booking_status": "confirmed",
                },
                {
                    "booking_id": "BKG002",
                    "flight_id": "EY123-20260120",
                    "passenger_id": "PAX002",
                    "booking_status": "confirmed",
                },
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_bookings_by_flight.invoke({"flight_id": "EY123-20260120"})

        assert len(result) == 2
        assert result[0]["booking_id"] == "BKG001"
        
        # Verify correct GSI used
        call_args = mock_table.query.call_args
        assert call_args[1]["IndexName"] == FLIGHT_ID_INDEX

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_bookings_empty(self, mock_dynamodb):
        """Test bookings query with no results."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb.Table.return_value = mock_table

        result = query_bookings_by_flight.invoke({"flight_id": "EY999-20260120"})

        assert result == []


class TestQueryBookingsByPassenger:
    """Test query_bookings_by_passenger tool (Priority 1 GSI)."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_bookings_by_passenger_success(self, mock_dynamodb):
        """Test successful passenger bookings query."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "booking_id": "BKG001",
                    "passenger_id": "PAX001",
                    "flight_id": "EY123-20260120",
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_bookings_by_passenger.invoke({"passenger_id": "PAX001"})

        assert len(result) == 1
        assert result[0]["passenger_id"] == "PAX001"
        
        # Verify correct GSI used (Priority 1)
        call_args = mock_table.query.call_args
        assert call_args[1]["IndexName"] == PASSENGER_FLIGHT_INDEX

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_bookings_by_passenger_with_flight(self, mock_dynamodb):
        """Test passenger bookings query filtered by flight."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": [{"booking_id": "BKG001"}]}
        mock_dynamodb.Table.return_value = mock_table

        result = query_bookings_by_passenger.invoke({
            "passenger_id": "PAX001",
            "flight_id": "EY123-20260120"
        })

        assert len(result) == 1
        
        # Verify both passenger_id and flight_id in query
        call_args = mock_table.query.call_args
        assert ":pid" in call_args[1]["ExpressionAttributeValues"]
        assert ":fid" in call_args[1]["ExpressionAttributeValues"]


class TestQueryBookingsByStatus:
    """Test query_bookings_by_status tool (Priority 1 GSI)."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_bookings_by_status_success(self, mock_dynamodb):
        """Test successful bookings by status query."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"booking_id": "BKG001", "booking_status": "confirmed"},
                {"booking_id": "BKG002", "booking_status": "confirmed"},
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_bookings_by_status.invoke({
            "flight_id": "EY123-20260120",
            "booking_status": "confirmed"
        })

        assert len(result) == 2
        
        # Verify correct GSI used (Priority 1)
        call_args = mock_table.query.call_args
        assert call_args[1]["IndexName"] == FLIGHT_STATUS_INDEX


class TestQueryBaggageByBooking:
    """Test query_baggage_by_booking tool."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_baggage_success(self, mock_dynamodb):
        """Test successful baggage query."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "baggage_tag": "EY123456",
                    "booking_id": "BKG001",
                    "baggage_status": "checked",
                }
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_baggage_by_booking.invoke({"booking_id": "BKG001"})

        assert len(result) == 1
        assert result[0]["baggage_tag"] == "EY123456"
        
        # Verify correct GSI used
        call_args = mock_table.query.call_args
        assert call_args[1]["IndexName"] == BOOKING_INDEX


class TestQueryBaggageByLocation:
    """Test query_baggage_by_location tool."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_baggage_by_location_success(self, mock_dynamodb):
        """Test successful baggage by location query."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"baggage_tag": "EY123456", "current_location": "LHR"},
                {"baggage_tag": "EY123457", "current_location": "LHR"},
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_baggage_by_location.invoke({"current_location": "LHR"})

        assert len(result) == 2
        
        # Verify correct GSI used
        call_args = mock_table.query.call_args
        assert call_args[1]["IndexName"] == LOCATION_STATUS_INDEX

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_baggage_by_location_with_status(self, mock_dynamodb):
        """Test baggage by location with status filter."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [{"baggage_tag": "EY123456", "baggage_status": "mishandled"}]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_baggage_by_location.invoke({
            "current_location": "LHR",
            "baggage_status": "mishandled"
        })

        assert len(result) == 1
        
        # Verify status filter in query
        call_args = mock_table.query.call_args
        assert ":status" in call_args[1]["ExpressionAttributeValues"]


class TestQueryPassenger:
    """Test query_passenger tool."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_passenger_success(self, mock_dynamodb):
        """Test successful passenger query."""
        mock_table = Mock()
        mock_table.get_item.return_value = {
            "Item": {
                "passenger_id": "PAX001",
                "passenger_name": "John Doe",
                "frequent_flyer_tier": "PLATINUM",
            }
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_passenger.invoke({"passenger_id": "PAX001"})

        assert result is not None
        assert result["passenger_id"] == "PAX001"
        assert result["frequent_flyer_tier"] == "PLATINUM"

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_passenger_not_found(self, mock_dynamodb):
        """Test passenger not found."""
        mock_table = Mock()
        mock_table.get_item.return_value = {}
        mock_dynamodb.Table.return_value = mock_table

        result = query_passenger.invoke({"passenger_id": "PAX999"})

        assert result is None


class TestQueryElitePassengers:
    """Test query_elite_passengers tool (Priority 1 GSI)."""

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_elite_passengers_success(self, mock_dynamodb):
        """Test successful elite passengers query."""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"passenger_id": "PAX001", "frequent_flyer_tier_id": "PLATINUM"},
                {"passenger_id": "PAX002", "frequent_flyer_tier_id": "PLATINUM"},
            ]
        }
        mock_dynamodb.Table.return_value = mock_table

        result = query_elite_passengers.invoke({"frequent_flyer_tier_id": "PLATINUM"})

        assert len(result) == 2
        
        # Verify correct GSI used (Priority 1)
        call_args = mock_table.query.call_args
        assert call_args[1]["IndexName"] == PASSENGER_ELITE_TIER_INDEX

    @patch("agents.guest_experience.agent.dynamodb")
    def test_query_elite_passengers_with_date_filter(self, mock_dynamodb):
        """Test elite passengers query with booking date filter."""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": [{"passenger_id": "PAX001"}]}
        mock_dynamodb.Table.return_value = mock_table

        result = query_elite_passengers.invoke({
            "frequent_flyer_tier_id": "DIAMOND",
            "booking_date_from": "2026-01-01"
        })

        assert len(result) == 1
        
        # Verify date filter in query
        call_args = mock_table.query.call_args
        assert ":date" in call_args[1]["ExpressionAttributeValues"]


class TestTableAccessRestrictions:
    """Test that Guest Experience Agent only accesses authorized tables."""

    def test_authorized_tables(self):
        """Verify agent only uses authorized tables."""
        from database.constants import AGENT_TABLE_ACCESS

        authorized_tables = AGENT_TABLE_ACCESS["guest_experience"]

        # Guest Experience Agent should access these tables
        assert FLIGHTS_TABLE in authorized_tables
        assert BOOKINGS_TABLE in authorized_tables
        assert BAGGAGE_TABLE in authorized_tables
        assert PASSENGERS_TABLE in authorized_tables

        # Guest Experience Agent should NOT access these tables
        from database.constants import (
            CREW_ROSTER_TABLE,
            MAINTENANCE_WORK_ORDERS_TABLE,
            CARGO_SHIPMENTS_TABLE,
        )
        assert CREW_ROSTER_TABLE not in authorized_tables
        assert MAINTENANCE_WORK_ORDERS_TABLE not in authorized_tables
        assert CARGO_SHIPMENTS_TABLE not in authorized_tables

    def test_authorized_gsis(self):
        """Verify agent uses correct GSIs."""
        from database.constants import AGENT_GSI_ACCESS

        authorized_gsis = AGENT_GSI_ACCESS["guest_experience"]

        # Guest Experience Agent should use these GSIs
        assert FLIGHT_NUMBER_DATE_INDEX in authorized_gsis
        assert FLIGHT_ID_INDEX in authorized_gsis
        assert BOOKING_INDEX in authorized_gsis
        assert PASSENGER_FLIGHT_INDEX in authorized_gsis  # Priority 1
        assert FLIGHT_STATUS_INDEX in authorized_gsis  # Priority 1
        assert LOCATION_STATUS_INDEX in authorized_gsis
        assert PASSENGER_ELITE_TIER_INDEX in authorized_gsis  # Priority 1


class TestToolDefinitions:
    """Test that tools are properly defined with @tool decorator."""

    def test_tools_are_langchain_tools(self):
        """Verify tools are LangChain Tool objects."""
        from langchain_core.tools import BaseTool

        tools = [
            query_flight,
            query_bookings_by_flight,
            query_bookings_by_passenger,
            query_bookings_by_status,
            query_baggage_by_booking,
            query_baggage_by_location,
            query_passenger,
            query_elite_passengers,
        ]

        for tool in tools:
            assert isinstance(tool, BaseTool), f"{tool.name} is not a LangChain Tool"

    def test_tools_have_descriptions(self):
        """Verify all tools have descriptions."""
        tools = [
            query_flight,
            query_bookings_by_flight,
            query_bookings_by_passenger,
            query_bookings_by_status,
            query_baggage_by_booking,
            query_baggage_by_location,
            query_passenger,
            query_elite_passengers,
        ]

        for tool in tools:
            assert tool.description, f"{tool.name} missing description"
            assert len(tool.description) > 20, f"{tool.name} description too short"

    def test_tools_have_correct_names(self):
        """Verify tools have expected names."""
        expected_names = [
            "query_flight",
            "query_bookings_by_flight",
            "query_bookings_by_passenger",
            "query_bookings_by_status",
            "query_baggage_by_booking",
            "query_baggage_by_location",
            "query_passenger",
            "query_elite_passengers",
        ]

        tools = [
            query_flight,
            query_bookings_by_flight,
            query_bookings_by_passenger,
            query_bookings_by_status,
            query_baggage_by_booking,
            query_baggage_by_location,
            query_passenger,
            query_elite_passengers,
        ]

        for tool, expected_name in zip(tools, expected_names):
            assert tool.name == expected_name, f"Tool name mismatch: {tool.name} != {expected_name}"
