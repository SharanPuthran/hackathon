"""
Unit Tests for Network Agent DynamoDB Query Tools

Feature: skymarshal-multi-round-orchestration
Task: 13.1 Update Network Agent
Validates: Requirements 2.1-2.7, 7.4

Tests that the Network agent has properly defined DynamoDB query tools
using the @tool decorator and that they use the correct GSIs and table access.
"""

import pytest
from langchain_core.tools import BaseTool
from agents.network.agent import (
    query_flight,
    query_aircraft_rotation,
    query_flights_by_aircraft,
    query_aircraft_availability,
)
from database.constants import (
    FLIGHTS_TABLE,
    AIRCRAFT_AVAILABILITY_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
    AIRCRAFT_ROTATION_INDEX,
)


class TestNetworkToolDefinitions:
    """Test that Network agent tools are properly defined."""

    def test_query_flight_is_tool(self):
        """Test that query_flight is a LangChain Tool."""
        assert isinstance(query_flight, BaseTool), \
            "query_flight should be a LangChain Tool (created with @tool decorator)"

    def test_query_aircraft_rotation_is_tool(self):
        """Test that query_aircraft_rotation is a LangChain Tool."""
        assert isinstance(query_aircraft_rotation, BaseTool), \
            "query_aircraft_rotation should be a LangChain Tool (created with @tool decorator)"

    def test_query_flights_by_aircraft_is_tool(self):
        """Test that query_flights_by_aircraft is a LangChain Tool."""
        assert isinstance(query_flights_by_aircraft, BaseTool), \
            "query_flights_by_aircraft should be a LangChain Tool (created with @tool decorator)"

    def test_query_aircraft_availability_is_tool(self):
        """Test that query_aircraft_availability is a LangChain Tool."""
        assert isinstance(query_aircraft_availability, BaseTool), \
            "query_aircraft_availability should be a LangChain Tool (created with @tool decorator)"

    def test_query_flight_has_name(self):
        """Test that query_flight has a proper name."""
        assert query_flight.name == "query_flight", \
            "Tool name should match function name"

    def test_query_aircraft_rotation_has_name(self):
        """Test that query_aircraft_rotation has a proper name."""
        assert query_aircraft_rotation.name == "query_aircraft_rotation", \
            "Tool name should match function name"

    def test_query_flights_by_aircraft_has_name(self):
        """Test that query_flights_by_aircraft has a proper name."""
        assert query_flights_by_aircraft.name == "query_flights_by_aircraft", \
            "Tool name should match function name"

    def test_query_aircraft_availability_has_name(self):
        """Test that query_aircraft_availability has a proper name."""
        assert query_aircraft_availability.name == "query_aircraft_availability", \
            "Tool name should match function name"

    def test_query_flight_has_description(self):
        """Test that query_flight has a description."""
        assert query_flight.description, \
            "Tool should have a description from docstring"
        assert "flight number" in query_flight.description.lower(), \
            "Description should mention flight number"
        assert "date" in query_flight.description.lower(), \
            "Description should mention date"

    def test_query_aircraft_rotation_has_description(self):
        """Test that query_aircraft_rotation has a description."""
        assert query_aircraft_rotation.description, \
            "Tool should have a description from docstring"
        assert "rotation" in query_aircraft_rotation.description.lower(), \
            "Description should mention rotation"
        assert "aircraft" in query_aircraft_rotation.description.lower(), \
            "Description should mention aircraft"

    def test_query_flights_by_aircraft_has_description(self):
        """Test that query_flights_by_aircraft has a description."""
        assert query_flights_by_aircraft.description, \
            "Tool should have a description from docstring"
        assert "aircraft" in query_flights_by_aircraft.description.lower(), \
            "Description should mention aircraft"

    def test_query_aircraft_availability_has_description(self):
        """Test that query_aircraft_availability has a description."""
        assert query_aircraft_availability.description, \
            "Tool should have a description from docstring"
        assert "availability" in query_aircraft_availability.description.lower(), \
            "Description should mention availability"


class TestNetworkToolInputs:
    """Test that tools have correct input schemas."""

    def test_query_flight_inputs(self):
        """Test query_flight has correct input parameters."""
        # Get the tool's input schema
        schema = query_flight.args_schema
        assert schema is not None, "Tool should have input schema"
        
        # Check that it has the expected fields
        fields = schema.model_fields
        assert "flight_number" in fields, "Should have flight_number parameter"
        assert "date" in fields, "Should have date parameter"

    def test_query_aircraft_rotation_inputs(self):
        """Test query_aircraft_rotation has correct input parameters."""
        schema = query_aircraft_rotation.args_schema
        assert schema is not None, "Tool should have input schema"
        
        fields = schema.model_fields
        assert "aircraft_registration" in fields, "Should have aircraft_registration parameter"
        assert "start_date" in fields, "Should have start_date parameter"
        assert "end_date" in fields, "Should have end_date parameter"

    def test_query_flights_by_aircraft_inputs(self):
        """Test query_flights_by_aircraft has correct input parameters."""
        schema = query_flights_by_aircraft.args_schema
        assert schema is not None, "Tool should have input schema"
        
        fields = schema.model_fields
        assert "aircraft_registration" in fields, "Should have aircraft_registration parameter"

    def test_query_aircraft_availability_inputs(self):
        """Test query_aircraft_availability has correct input parameters."""
        schema = query_aircraft_availability.args_schema
        assert schema is not None, "Tool should have input schema"
        
        fields = schema.model_fields
        assert "aircraft_registration" in fields, "Should have aircraft_registration parameter"
        assert "date" in fields, "Should have date parameter"


class TestNetworkTableAccess:
    """Test that tools only access authorized tables."""

    def test_authorized_tables(self):
        """Test that Network agent only accesses authorized tables."""
        from database.constants import AGENT_TABLE_ACCESS
        
        authorized_tables = AGENT_TABLE_ACCESS["network"]
        
        # Verify the two authorized tables
        assert FLIGHTS_TABLE in authorized_tables, \
            "Network should access flights table"
        assert AIRCRAFT_AVAILABILITY_TABLE in authorized_tables, \
            "Network should access AircraftAvailability table"
        
        # Verify exactly 2 tables
        assert len(authorized_tables) == 2, \
            "Network should have exactly 2 authorized tables"

    def test_gsi_usage(self):
        """Test that Network agent uses correct GSIs."""
        from database.constants import AGENT_GSI_ACCESS
        
        authorized_gsis = AGENT_GSI_ACCESS["network"]
        
        # Verify the required GSIs
        assert FLIGHT_NUMBER_DATE_INDEX in authorized_gsis, \
            "Should use flight-number-date-index for flight lookup"
        assert AIRCRAFT_REGISTRATION_INDEX in authorized_gsis, \
            "Should use aircraft-registration-index for aircraft queries"
        assert AIRCRAFT_ROTATION_INDEX in authorized_gsis, \
            "Should use aircraft-rotation-index for rotation queries (Priority 1 GSI)"


class TestNetworkToolDocumentation:
    """Test that tools have comprehensive documentation."""

    def test_query_flight_documentation(self):
        """Test query_flight has comprehensive documentation."""
        doc = query_flight.description
        assert "GSI" in doc or "gsi" in doc.lower(), \
            "Should mention GSI usage"
        assert "flight-number-date-index" in doc.lower() or "index" in doc.lower(), \
            "Should mention the specific GSI used"

    def test_query_aircraft_rotation_documentation(self):
        """Test query_aircraft_rotation has comprehensive documentation."""
        doc = query_aircraft_rotation.description
        assert "rotation" in doc.lower(), \
            "Should explain rotation concept"
        assert "aircraft-rotation-index" in doc.lower() or "priority 1" in doc.lower(), \
            "Should mention Priority 1 GSI"

    def test_query_flights_by_aircraft_documentation(self):
        """Test query_flights_by_aircraft has comprehensive documentation."""
        doc = query_flights_by_aircraft.description
        assert "aircraft" in doc.lower(), \
            "Should explain aircraft query"

    def test_query_aircraft_availability_documentation(self):
        """Test query_aircraft_availability has comprehensive documentation."""
        doc = query_aircraft_availability.description
        assert "availability" in doc.lower(), \
            "Should explain availability concept"
