"""Unit tests for crew compliance agent tools"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from database.tools import get_crew_compliance_tools


class TestCrewComplianceTools:
    """Test crew compliance agent database tools"""

    @pytest.fixture
    def mock_db_client(self):
        """Create a mock DynamoDB client"""
        with patch('database.tools.DynamoDBClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            yield mock_instance

    def test_query_crew_roster_and_members_uses_batch(self, mock_db_client):
        """
        Test that query_crew_roster_and_members uses batch_get_crew_members
        instead of individual queries.
        
        Validates: Requirements 3.7 - Agents use batch query methods when multiple items needed
        """
        # Setup mock data
        mock_roster = [
            {"crew_id": "C001", "position_id": "CAPT", "duty_start": "2024-01-15T06:00:00Z"},
            {"crew_id": "C002", "position_id": "FO", "duty_start": "2024-01-15T06:00:00Z"},
            {"crew_id": "C003", "position_id": "FA1", "duty_start": "2024-01-15T06:00:00Z"},
            {"crew_id": "C004", "position_id": "FA2", "duty_start": "2024-01-15T06:00:00Z"},
        ]
        
        mock_crew_members = [
            {"crew_id": "C001", "name": "John Smith", "qualifications": ["A380", "B777"]},
            {"crew_id": "C002", "name": "Jane Doe", "qualifications": ["A380"]},
            {"crew_id": "C003", "name": "Bob Johnson", "qualifications": ["FA"]},
            {"crew_id": "C004", "name": "Alice Williams", "qualifications": ["FA"]},
        ]
        
        # Configure mock
        mock_db_client.query_crew_roster_by_flight.return_value = mock_roster
        mock_db_client.batch_get_crew_members.return_value = mock_crew_members
        mock_db_client.to_json = lambda x: json.dumps(x)
        
        # Get tools and execute
        tools = get_crew_compliance_tools()
        query_crew_roster_and_members = tools[2]  # Third tool in the list
        
        result_json = query_crew_roster_and_members.invoke({"flight_id": "EY123"})
        result = json.loads(result_json)
        
        # Verify batch method was called
        mock_db_client.batch_get_crew_members.assert_called_once()
        
        # Verify it was called with the correct crew IDs
        call_args = mock_db_client.batch_get_crew_members.call_args[0][0]
        assert set(call_args) == {"C001", "C002", "C003", "C004"}
        
        # Verify only 2 queries were made (roster + batch)
        assert result["query_count"] == 2
        assert "Batch" in result["query_method"]
        
        # Verify optimization message
        assert "Reduced from 5 queries to 2 queries" in result["optimization"]

    def test_query_crew_roster_and_members_empty_roster(self, mock_db_client):
        """
        Test that query_crew_roster_and_members handles empty roster correctly.
        """
        # Configure mock for empty roster
        mock_db_client.query_crew_roster_by_flight.return_value = []
        mock_db_client.to_json = lambda x: json.dumps(x)
        
        # Get tools and execute
        tools = get_crew_compliance_tools()
        query_crew_roster_and_members = tools[2]
        
        result_json = query_crew_roster_and_members.invoke({"flight_id": "EY123"})
        result = json.loads(result_json)
        
        # Verify batch method was NOT called for empty roster
        mock_db_client.batch_get_crew_members.assert_not_called()
        
        # Verify response structure
        assert result["crew_count"] == 0
        assert result["roster"] == []
        assert result["crew_members"] == []
        assert result["query_count"] == 1  # Only roster query

    def test_query_crew_roster_and_members_enriches_data(self, mock_db_client):
        """
        Test that query_crew_roster_and_members enriches roster with crew details.
        """
        # Setup mock data
        mock_roster = [
            {"crew_id": "C001", "position_id": "CAPT"},
            {"crew_id": "C002", "position_id": "FO"},
        ]
        
        mock_crew_members = [
            {"crew_id": "C001", "name": "John Smith"},
            {"crew_id": "C002", "name": "Jane Doe"},
        ]
        
        # Configure mock
        mock_db_client.query_crew_roster_by_flight.return_value = mock_roster
        mock_db_client.batch_get_crew_members.return_value = mock_crew_members
        mock_db_client.to_json = lambda x: json.dumps(x)
        
        # Get tools and execute
        tools = get_crew_compliance_tools()
        query_crew_roster_and_members = tools[2]
        
        result_json = query_crew_roster_and_members.invoke({"flight_id": "EY123"})
        result = json.loads(result_json)
        
        # Verify roster is enriched with crew member details
        assert len(result["roster"]) == 2
        assert result["roster"][0]["crew_member_details"]["name"] == "John Smith"
        assert result["roster"][1]["crew_member_details"]["name"] == "Jane Doe"

    def test_batch_method_is_synchronous(self, mock_db_client):
        """
        Test that batch_get_crew_members is called synchronously (no await).
        
        This test verifies that the implementation correctly uses the synchronous
        batch method as specified in the task requirements.
        """
        # Setup mock data
        mock_roster = [{"crew_id": "C001", "position_id": "CAPT"}]
        mock_crew_members = [{"crew_id": "C001", "name": "John Smith"}]
        
        # Configure mock
        mock_db_client.query_crew_roster_by_flight.return_value = mock_roster
        mock_db_client.batch_get_crew_members.return_value = mock_crew_members
        mock_db_client.to_json = lambda x: json.dumps(x)
        
        # Get tools and execute
        tools = get_crew_compliance_tools()
        query_crew_roster_and_members = tools[2]
        
        # This should execute without any async/await issues
        result_json = query_crew_roster_and_members.invoke({"flight_id": "EY123"})
        result = json.loads(result_json)
        
        # Verify successful execution
        assert result["crew_count"] == 1
        assert mock_db_client.batch_get_crew_members.called

    def test_query_crew_roster_and_members_handles_missing_crew_ids(self, mock_db_client):
        """
        Test that query_crew_roster_and_members handles roster entries without crew_id.
        """
        # Setup mock data with some missing crew_ids
        mock_roster = [
            {"crew_id": "C001", "position_id": "CAPT"},
            {"position_id": "FO"},  # Missing crew_id
            {"crew_id": "C003", "position_id": "FA1"},
        ]
        
        mock_crew_members = [
            {"crew_id": "C001", "name": "John Smith"},
            {"crew_id": "C003", "name": "Bob Johnson"},
        ]
        
        # Configure mock
        mock_db_client.query_crew_roster_by_flight.return_value = mock_roster
        mock_db_client.batch_get_crew_members.return_value = mock_crew_members
        mock_db_client.to_json = lambda x: json.dumps(x)
        
        # Get tools and execute
        tools = get_crew_compliance_tools()
        query_crew_roster_and_members = tools[2]
        
        result_json = query_crew_roster_and_members.invoke({"flight_id": "EY123"})
        result = json.loads(result_json)
        
        # Verify batch method was called with only valid crew IDs
        call_args = mock_db_client.batch_get_crew_members.call_args[0][0]
        assert set(call_args) == {"C001", "C003"}
        
        # Verify roster still contains all entries
        assert len(result["roster"]) == 3
