"""
Unit Tests for Crew Compliance Agent DynamoDB Query Tools

Feature: skymarshal-multi-round-orchestration
Task: 10.2 Implement DynamoDB query tools
Validates: Requirements 2.1-2.7, 7.1

Tests that the Crew Compliance agent has properly defined DynamoDB query tools
using the @tool decorator and that they use the correct GSIs and table access.
"""

import pytest
from langchain_core.tools import BaseTool
from agents.crew_compliance.agent import (
    query_flight,
    query_crew_roster,
    query_crew_members,
)
from database.constants import (
    FLIGHTS_TABLE,
    CREW_ROSTER_TABLE,
    CREW_MEMBERS_TABLE,
    FLIGHT_NUMBER_DATE_INDEX,
    FLIGHT_POSITION_INDEX,
)


class TestCrewComplianceToolDefinitions:
    """Test that Crew Compliance agent tools are properly defined."""

    def test_query_flight_is_tool(self):
        """Test that query_flight is a LangChain Tool."""
        assert isinstance(query_flight, BaseTool), \
            "query_flight should be a LangChain Tool (created with @tool decorator)"

    def test_query_crew_roster_is_tool(self):
        """Test that query_crew_roster is a LangChain Tool."""
        assert isinstance(query_crew_roster, BaseTool), \
            "query_crew_roster should be a LangChain Tool (created with @tool decorator)"

    def test_query_crew_members_is_tool(self):
        """Test that query_crew_members is a LangChain Tool."""
        assert isinstance(query_crew_members, BaseTool), \
            "query_crew_members should be a LangChain Tool (created with @tool decorator)"

    def test_query_flight_has_name(self):
        """Test that query_flight has a proper name."""
        assert query_flight.name == "query_flight", \
            "Tool name should match function name"

    def test_query_crew_roster_has_name(self):
        """Test that query_crew_roster has a proper name."""
        assert query_crew_roster.name == "query_crew_roster", \
            "Tool name should match function name"

    def test_query_crew_members_has_name(self):
        """Test that query_crew_members has a proper name."""
        assert query_crew_members.name == "query_crew_members", \
            "Tool name should match function name"

    def test_query_flight_has_description(self):
        """Test that query_flight has a description."""
        assert query_flight.description, \
            "Tool should have a description from docstring"
        assert "flight number" in query_flight.description.lower(), \
            "Description should mention flight number"
        assert "date" in query_flight.description.lower(), \
            "Description should mention date"

    def test_query_crew_roster_has_description(self):
        """Test that query_crew_roster has a description."""
        assert query_crew_roster.description, \
            "Tool should have a description from docstring"
        assert "crew roster" in query_crew_roster.description.lower(), \
            "Description should mention crew roster"
        assert "flight" in query_crew_roster.description.lower(), \
            "Description should mention flight"

    def test_query_crew_members_has_description(self):
        """Test that query_crew_members has a description."""
        assert query_crew_members.description, \
            "Tool should have a description from docstring"
        assert "crew member" in query_crew_members.description.lower(), \
            "Description should mention crew member"


class TestCrewComplianceToolInputs:
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

    def test_query_crew_roster_inputs(self):
        """Test query_crew_roster has correct input parameters."""
        schema = query_crew_roster.args_schema
        assert schema is not None, "Tool should have input schema"
        
        fields = schema.model_fields
        assert "flight_id" in fields, "Should have flight_id parameter"

    def test_query_crew_members_inputs(self):
        """Test query_crew_members has correct input parameters."""
        schema = query_crew_members.args_schema
        assert schema is not None, "Tool should have input schema"
        
        fields = schema.model_fields
        assert "crew_id" in fields, "Should have crew_id parameter"


class TestCrewComplianceTableAccess:
    """Test that tools only access authorized tables."""

    def test_authorized_tables(self):
        """Test that Crew Compliance agent only accesses authorized tables."""
        from database.constants import AGENT_TABLE_ACCESS
        
        authorized_tables = AGENT_TABLE_ACCESS["crew_compliance"]
        
        # Verify the three authorized tables
        assert FLIGHTS_TABLE in authorized_tables, \
            "Crew Compliance should access flights table"
        assert CREW_ROSTER_TABLE in authorized_tables, \
            "Crew Compliance should access CrewRoster table"
        assert CREW_MEMBERS_TABLE in authorized_tables, \
            "Crew Compliance should access CrewMembers table"
        
        # Verify exactly 3 tables
        assert len(authorized_tables) == 3, \
            "Crew Compliance should have exactly 3 authorized tables"

    def test_gsi_usage(self):
        """Test that Crew Compliance agent uses correct GSIs."""
        from database.constants import AGENT_GSI_ACCESS
        
        authorized_gsis = AGENT_GSI_ACCESS["crew_compliance"]
        
        # Verify the required GSIs
        assert FLIGHT_NUMBER_DATE_INDEX in authorized_gsis, \
            "Should use flight-number-date-index for flight lookup"
        assert FLIGHT_POSITION_INDEX in authorized_gsis, \
            "Should use flight-position-index for crew roster queries"


class TestCrewComplianceToolIntegration:
    """Integration tests for tool usage in agent."""

    def test_agent_has_tools_available(self):
        """Test that the agent can access its tools."""
        from agents.crew_compliance.agent import analyze_crew_compliance
        import inspect
        
        # Verify the agent function exists
        assert callable(analyze_crew_compliance)
        
        # Verify it's async
        assert inspect.iscoroutinefunction(analyze_crew_compliance)
        
        # Verify it has the expected parameters
        sig = inspect.signature(analyze_crew_compliance)
        params = list(sig.parameters.keys())
        assert "payload" in params
        assert "llm" in params
        assert "mcp_tools" in params

    def test_tools_list_creation(self):
        """Test that tools can be collected into a list."""
        tools = [query_flight, query_crew_roster, query_crew_members]
        
        assert len(tools) == 3, "Should have 3 DynamoDB query tools"
        
        # Verify all are BaseTool instances
        for tool in tools:
            assert isinstance(tool, BaseTool), \
                f"Tool {tool.name} should be a LangChain BaseTool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
