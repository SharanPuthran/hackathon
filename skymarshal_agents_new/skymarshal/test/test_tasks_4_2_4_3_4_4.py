"""
Test suite for tasks 4.2, 4.3, and 4.4: Batch query tools for network, guest experience, and cargo agents
"""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal
import json

from database.dynamodb import DynamoDBClient
from database.tools import get_network_tools, get_guest_experience_tools, get_cargo_tools


class TestTask42NetworkBatchTools:
    """Test Task 4.2: Network agent batch query tools"""
    
    def test_network_tools_include_batch_query(self):
        """Verify network tools include the batch query tool"""
        tools = get_network_tools()
        tool_names = [tool.name for tool in tools]
        
        assert "query_multiple_flights_network" in tool_names, \
            "Network tools should include query_multiple_flights_network"
    
    @patch('database.tools.DynamoDBClient')
    def test_query_multiple_flights_network_uses_batch_get_flights(self, mock_db_class):
        """Verify query_multiple_flights_network uses batch_get_flights method"""
        # Setup mock
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        # Mock batch_get_flights to return test data
        mock_db.batch_get_flights.return_value = [
            {'flight_id': 'FL001', 'flight_number': 'EY123', 'origin': 'AUH'},
            {'flight_id': 'FL002', 'flight_number': 'EY456', 'origin': 'DXB'}
        ]
        
        # Mock to_json
        def mock_to_json(data):
            return json.dumps(data)
        mock_db.to_json = mock_to_json
        
        # Get tools and invoke
        tools = get_network_tools()
        batch_tool = next(t for t in tools if t.name == "query_multiple_flights_network")
        
        result_json = batch_tool.invoke({'flight_ids': 'FL001,FL002'})
        result = json.loads(result_json)
        
        # Verify batch_get_flights was called
        mock_db.batch_get_flights.assert_called_once_with(['FL001', 'FL002'])
        
        # Verify result structure
        assert result['flight_count'] == 2
        assert result['query_method'] == 'Batch: Flights'
        assert 'optimization' in result
        assert 'Reduced from 2 queries to 1 batch query' in result['optimization']


class TestTask43GuestExperienceBatchTools:
    """Test Task 4.3: Guest experience agent batch query tools"""
    
    def test_guest_experience_tools_include_batch_query(self):
        """Verify guest experience tools include the batch query tool"""
        tools = get_guest_experience_tools()
        tool_names = [tool.name for tool in tools]
        
        assert "query_flight_bookings_with_passengers" in tool_names, \
            "Guest experience tools should include query_flight_bookings_with_passengers"
    
    @patch('database.tools.DynamoDBClient')
    def test_query_flight_bookings_with_passengers_uses_batch_get_passengers(self, mock_db_class):
        """Verify query_flight_bookings_with_passengers uses batch_get_passengers method"""
        # Setup mock
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        # Mock query_bookings_by_flight to return test bookings
        mock_db.query_bookings_by_flight.return_value = [
            {'booking_id': 'B001', 'passenger_id': 'P001', 'flight_id': 'FL001'},
            {'booking_id': 'B002', 'passenger_id': 'P002', 'flight_id': 'FL001'}
        ]
        
        # Mock batch_get_passengers to return test passengers
        mock_db.batch_get_passengers.return_value = [
            {'passenger_id': 'P001', 'name': 'Alice Brown', 'tier': 'Gold'},
            {'passenger_id': 'P002', 'name': 'Bob Wilson', 'tier': 'Silver'}
        ]
        
        # Mock to_json
        def mock_to_json(data):
            return json.dumps(data, default=str)
        mock_db.to_json = mock_to_json
        
        # Get tools and invoke
        tools = get_guest_experience_tools()
        batch_tool = next(t for t in tools if t.name == "query_flight_bookings_with_passengers")
        
        result_json = batch_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        # Verify batch_get_passengers was called
        mock_db.batch_get_passengers.assert_called_once_with(['P001', 'P002'])
        
        # Verify result structure
        assert result['booking_count'] == 2
        assert result['query_count'] == 2
        assert 'GSI: flight-status-index + Batch: Passengers' in result['query_method']
        assert 'optimization' in result
        assert 'Reduced from 3 queries to 2 queries' in result['optimization']


class TestTask44CargoBatchTools:
    """Test Task 4.4: Cargo agent batch query tools"""
    
    def test_cargo_tools_include_batch_query(self):
        """Verify cargo tools include the batch query tool"""
        tools = get_cargo_tools()
        tool_names = [tool.name for tool in tools]
        
        assert "query_flight_cargo_manifest_with_shipments" in tool_names, \
            "Cargo tools should include query_flight_cargo_manifest_with_shipments"
    
    @patch('database.tools.DynamoDBClient')
    def test_query_flight_cargo_manifest_with_shipments_uses_batch_get_cargo_shipments(self, mock_db_class):
        """Verify query_flight_cargo_manifest_with_shipments uses batch_get_cargo_shipments method"""
        # Setup mock
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        
        # Mock query_cargo_by_flight to return test cargo assignments
        mock_db.query_cargo_by_flight.return_value = [
            {'shipment_id': 'SH001', 'flight_id': 'FL001', 'weight_on_flight_kg': '150.5'},
            {'shipment_id': 'SH002', 'flight_id': 'FL001', 'weight_on_flight_kg': '200.0'}
        ]
        
        # Mock batch_get_cargo_shipments to return test shipments
        mock_db.batch_get_cargo_shipments.return_value = [
            {'shipment_id': 'SH001', 'priority': 'high', 'contents': 'Electronics'},
            {'shipment_id': 'SH002', 'priority': 'medium', 'contents': 'Textiles'}
        ]
        
        # Mock to_json
        def mock_to_json(data):
            return json.dumps(data, default=str)
        mock_db.to_json = mock_to_json
        
        # Get tools and invoke
        tools = get_cargo_tools()
        batch_tool = next(t for t in tools if t.name == "query_flight_cargo_manifest_with_shipments")
        
        result_json = batch_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        # Verify batch_get_cargo_shipments was called
        mock_db.batch_get_cargo_shipments.assert_called_once_with(['SH001', 'SH002'])
        
        # Verify result structure
        assert result['cargo_count'] == 2
        assert result['query_count'] == 2
        assert 'GSI: flight-loading-index + Batch: CargoShipments' in result['query_method']
        assert 'optimization' in result
        assert 'Reduced from 3 queries to 2 queries' in result['optimization']


class TestBatchToolsIntegration:
    """Integration tests for all batch query tools"""
    
    def test_all_batch_tools_follow_same_pattern(self):
        """Verify all batch tools follow the same implementation pattern"""
        network_tools = get_network_tools()
        guest_tools = get_guest_experience_tools()
        cargo_tools = get_cargo_tools()
        
        # Get batch tools
        network_batch = next(t for t in network_tools if 'multiple' in t.name or 'batch' in t.name.lower())
        guest_batch = next(t for t in guest_tools if 'with_passengers' in t.name)
        cargo_batch = next(t for t in cargo_tools if 'with_shipments' in t.name)
        
        # Verify all have descriptions mentioning optimization
        assert 'batch' in network_batch.description.lower() or 'optimized' in network_batch.description.lower()
        assert 'batch' in guest_batch.description.lower() or 'optimized' in guest_batch.description.lower()
        assert 'batch' in cargo_batch.description.lower() or 'optimized' in cargo_batch.description.lower()
    
    def test_batch_tools_reduce_query_count(self):
        """Verify batch tools document query count reduction"""
        # This is a documentation test - verify the tools explain the optimization
        network_tools = get_network_tools()
        guest_tools = get_guest_experience_tools()
        cargo_tools = get_cargo_tools()
        
        network_batch = next(t for t in network_tools if 'multiple' in t.name)
        guest_batch = next(t for t in guest_tools if 'with_passengers' in t.name)
        cargo_batch = next(t for t in cargo_tools if 'with_shipments' in t.name)
        
        # All should mention reducing queries
        assert 'reduces' in network_batch.description.lower() or 'reduced' in network_batch.description.lower()
        assert 'reduces' in guest_batch.description.lower() or 'reduced' in guest_batch.description.lower()
        assert 'reduces' in cargo_batch.description.lower() or 'reduced' in cargo_batch.description.lower()
