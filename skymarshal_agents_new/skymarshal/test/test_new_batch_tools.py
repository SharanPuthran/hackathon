"""Test new batch tools for network, guest experience, and cargo agents"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import json


class TestNetworkBatchTools:
    """Test network agent batch tools"""

    @pytest.fixture
    def mock_db_client(self):
        """Mock DynamoDB client"""
        with patch('database.tools.DynamoDBClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Mock batch_get_flights
            mock_instance.batch_get_flights.return_value = [
                {'flight_id': 'FL001', 'flight_number': 'EY123', 'origin': 'AUH'},
                {'flight_id': 'FL002', 'flight_number': 'EY456', 'origin': 'DXB'}
            ]
            
            # Mock to_json
            mock_instance.to_json.side_effect = lambda x: json.dumps(x, default=str)
            
            yield mock_instance

    def test_query_multiple_flights_network_success(self, mock_db_client):
        """Test query_multiple_flights_network with multiple flights"""
        from database.tools import get_network_tools
        
        tools = get_network_tools()
        query_tool = tools[2]  # query_multiple_flights_network is the third tool
        
        result_json = query_tool.invoke({'flight_ids': 'FL001,FL002'})
        result = json.loads(result_json)
        
        assert result['flight_count'] == 2
        assert result['found_count'] == 2
        assert result['requested_count'] == 2
        assert len(result['missing_ids']) == 0
        assert 'optimization' in result
        
        # Verify batch method was called
        mock_db_client.batch_get_flights.assert_called_once_with(['FL001', 'FL002'])

    def test_query_multiple_flights_network_empty(self, mock_db_client):
        """Test query_multiple_flights_network with empty input"""
        from database.tools import get_network_tools
        
        tools = get_network_tools()
        query_tool = tools[2]
        
        result_json = query_tool.invoke({'flight_ids': ''})
        result = json.loads(result_json)
        
        assert 'error' in result
        assert result['error'] == 'No flight IDs provided'


class TestGuestExperienceBatchTools:
    """Test guest experience agent batch tools"""

    @pytest.fixture
    def mock_db_client(self):
        """Mock DynamoDB client"""
        with patch('database.tools.DynamoDBClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Mock query_bookings_by_flight
            mock_instance.query_bookings_by_flight.return_value = [
                {'booking_id': 'B001', 'passenger_id': 'P001', 'seat': '12A'},
                {'booking_id': 'B002', 'passenger_id': 'P002', 'seat': '12B'}
            ]
            
            # Mock batch_get_passengers
            mock_instance.batch_get_passengers.return_value = [
                {'passenger_id': 'P001', 'name': 'Alice Brown', 'tier': 'Gold'},
                {'passenger_id': 'P002', 'name': 'Bob Wilson', 'tier': 'Silver'}
            ]
            
            # Mock to_json
            mock_instance.to_json.side_effect = lambda x: json.dumps(x, default=str)
            
            yield mock_instance

    def test_query_flight_bookings_with_passengers_success(self, mock_db_client):
        """Test query_flight_bookings_with_passengers with multiple passengers"""
        from database.tools import get_guest_experience_tools
        
        tools = get_guest_experience_tools()
        query_tool = tools[4]  # query_flight_bookings_with_passengers is the fifth tool
        
        result_json = query_tool.invoke({'flight_id': 'FL001', 'booking_status': 'Confirmed'})
        result = json.loads(result_json)
        
        assert result['booking_count'] == 2
        assert result['query_count'] == 2
        assert len(result['passengers']) == 2
        assert 'optimization' in result
        
        # Verify methods were called
        mock_db_client.query_bookings_by_flight.assert_called_once_with('FL001', 'Confirmed')
        mock_db_client.batch_get_passengers.assert_called_once_with(['P001', 'P002'])

    def test_query_flight_bookings_with_passengers_empty(self, mock_db_client):
        """Test query_flight_bookings_with_passengers with no bookings"""
        from database.tools import get_guest_experience_tools
        
        # Mock empty bookings
        mock_db_client.query_bookings_by_flight.return_value = []
        
        tools = get_guest_experience_tools()
        query_tool = tools[4]
        
        result_json = query_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        assert result['booking_count'] == 0
        assert result['query_count'] == 1
        assert len(result['passengers']) == 0


class TestCargoBatchTools:
    """Test cargo agent batch tools"""

    @pytest.fixture
    def mock_db_client(self):
        """Mock DynamoDB client"""
        with patch('database.tools.DynamoDBClient') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Mock query_cargo_by_flight
            mock_instance.query_cargo_by_flight.return_value = [
                {'shipment_id': 'SH001', 'weight_on_flight_kg': Decimal('150.5')},
                {'shipment_id': 'SH002', 'weight_on_flight_kg': Decimal('200.0')}
            ]
            
            # Mock batch_get_cargo_shipments
            mock_instance.batch_get_cargo_shipments.return_value = [
                {'shipment_id': 'SH001', 'priority': 'high', 'contents': 'Electronics'},
                {'shipment_id': 'SH002', 'priority': 'medium', 'contents': 'Textiles'}
            ]
            
            # Mock to_json
            mock_instance.to_json.side_effect = lambda x: json.dumps(x, default=str)
            
            yield mock_instance

    def test_query_flight_cargo_manifest_with_shipments_success(self, mock_db_client):
        """Test query_flight_cargo_manifest_with_shipments with multiple shipments"""
        from database.tools import get_cargo_tools
        
        tools = get_cargo_tools()
        query_tool = tools[2]  # query_flight_cargo_manifest_with_shipments is the third tool
        
        result_json = query_tool.invoke({'flight_id': 'FL001', 'loading_status': 'LOADED'})
        result = json.loads(result_json)
        
        assert result['cargo_count'] == 2
        assert result['query_count'] == 2
        assert result['total_weight_kg'] == 350.5
        assert len(result['shipments']) == 2
        assert 'optimization' in result
        
        # Verify methods were called
        mock_db_client.query_cargo_by_flight.assert_called_once_with('FL001', 'LOADED')
        mock_db_client.batch_get_cargo_shipments.assert_called_once_with(['SH001', 'SH002'])

    def test_query_flight_cargo_manifest_with_shipments_empty(self, mock_db_client):
        """Test query_flight_cargo_manifest_with_shipments with no cargo"""
        from database.tools import get_cargo_tools
        
        # Mock empty cargo
        mock_db_client.query_cargo_by_flight.return_value = []
        
        tools = get_cargo_tools()
        query_tool = tools[2]
        
        result_json = query_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        assert result['cargo_count'] == 0
        assert result['query_count'] == 1
        assert result['total_weight_kg'] == 0
        assert len(result['shipments']) == 0
