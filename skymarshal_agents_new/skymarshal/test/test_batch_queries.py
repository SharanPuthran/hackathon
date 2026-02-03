"""Unit tests for DynamoDB batch query operations"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Import the DynamoDB client
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from database.dynamodb import DynamoDBClient


class TestBatchGetItems:
    """Test suite for batch_get_items() method"""

    @pytest.fixture
    def mock_client(self):
        """Create a mock DynamoDB client"""
        with patch('database.dynamodb.boto3') as mock_boto3:
            # Mock the resource and client
            mock_resource = Mock()
            mock_client = Mock()
            mock_boto3.resource.return_value = mock_resource
            mock_boto3.client.return_value = mock_client
            
            # Reset singleton
            DynamoDBClient._instance = None
            
            # Create client instance
            client = DynamoDBClient()
            
            yield client, mock_client

    @pytest.mark.asyncio
    async def test_batch_get_empty_keys(self, mock_client):
        """Test batch_get_items with empty keys list"""
        client, _ = mock_client
        
        result = await client.batch_get_items("TestTable", [])
        
        assert result == []

    @pytest.mark.asyncio
    async def test_batch_get_single_item(self, mock_client):
        """Test batch_get_items with single item"""
        client, mock_boto_client = mock_client
        
        # Mock response
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'TestTable': [
                    {'id': 'item1', 'name': 'Test Item 1'}
                ]
            },
            'UnprocessedKeys': {}
        }
        
        keys = [{'id': 'item1'}]
        result = await client.batch_get_items("TestTable", keys)
        
        assert len(result) == 1
        assert result[0]['id'] == 'item1'
        assert result[0]['name'] == 'Test Item 1'
        
        # Verify batch_get_item was called once
        mock_boto_client.batch_get_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_get_100_items(self, mock_client):
        """Test batch_get_items with exactly 100 items (AWS limit)"""
        client, mock_boto_client = mock_client
        
        # Create 100 items
        items = [{'id': f'item{i}', 'value': i} for i in range(100)]
        
        # Mock response
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'TestTable': items
            },
            'UnprocessedKeys': {}
        }
        
        keys = [{'id': f'item{i}'} for i in range(100)]
        result = await client.batch_get_items("TestTable", keys)
        
        assert len(result) == 100
        # Should be called once (single batch)
        assert mock_boto_client.batch_get_item.call_count == 1

    @pytest.mark.asyncio
    async def test_batch_get_101_items_splits(self, mock_client):
        """Test batch_get_items with 101 items (requires splitting)"""
        client, mock_boto_client = mock_client
        
        # Mock responses for two batches
        def batch_get_side_effect(*args, **kwargs):
            request_items = kwargs['RequestItems']['TestTable']['Keys']
            num_items = len(request_items)
            return {
                'Responses': {
                    'TestTable': [{'id': key['id'], 'value': int(key['id'].replace('item', ''))} 
                                  for key in request_items]
                },
                'UnprocessedKeys': {}
            }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        keys = [{'id': f'item{i}'} for i in range(101)]
        result = await client.batch_get_items("TestTable", keys)
        
        assert len(result) == 101
        # Should be called twice (two batches: 100 + 1)
        assert mock_boto_client.batch_get_item.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_get_250_items_splits(self, mock_client):
        """Test batch_get_items with 250 items (requires 3 batches)"""
        client, mock_boto_client = mock_client
        
        # Mock responses
        def batch_get_side_effect(*args, **kwargs):
            request_items = kwargs['RequestItems']['TestTable']['Keys']
            return {
                'Responses': {
                    'TestTable': [{'id': key['id']} for key in request_items]
                },
                'UnprocessedKeys': {}
            }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        keys = [{'id': f'item{i}'} for i in range(250)]
        result = await client.batch_get_items("TestTable", keys)
        
        assert len(result) == 250
        # Should be called 3 times (batches: 100 + 100 + 50)
        assert mock_boto_client.batch_get_item.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_get_with_unprocessed_keys_retry(self, mock_client):
        """Test batch_get_items handles unprocessed keys with retry"""
        client, mock_boto_client = mock_client
        
        # First call returns unprocessed keys, second call succeeds
        call_count = 0
        def batch_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call: some items succeed, some unprocessed
                return {
                    'Responses': {
                        'TestTable': [
                            {'id': 'item0'},
                            {'id': 'item1'}
                        ]
                    },
                    'UnprocessedKeys': {
                        'TestTable': {
                            'Keys': [
                                {'id': 'item2'},
                                {'id': 'item3'}
                            ]
                        }
                    }
                }
            else:
                # Second call: unprocessed keys succeed
                return {
                    'Responses': {
                        'TestTable': [
                            {'id': 'item2'},
                            {'id': 'item3'}
                        ]
                    },
                    'UnprocessedKeys': {}
                }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        keys = [{'id': f'item{i}'} for i in range(4)]
        result = await client.batch_get_items("TestTable", keys)
        
        assert len(result) == 4
        # Should be called twice (initial + retry)
        assert mock_boto_client.batch_get_item.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_get_exponential_backoff(self, mock_client):
        """Test batch_get_items uses exponential backoff for retries"""
        client, mock_boto_client = mock_client
        
        retry_times = []
        
        # Track retry attempts
        call_count = 0
        def batch_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count <= 2:
                # First two calls return unprocessed keys
                return {
                    'Responses': {
                        'TestTable': []
                    },
                    'UnprocessedKeys': {
                        'TestTable': {
                            'Keys': [{'id': 'item0'}]
                        }
                    }
                }
            else:
                # Third call succeeds
                return {
                    'Responses': {
                        'TestTable': [{'id': 'item0'}]
                    },
                    'UnprocessedKeys': {}
                }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        # Patch asyncio.sleep to track wait times
        original_sleep = asyncio.sleep
        sleep_times = []
        
        async def mock_sleep(duration):
            sleep_times.append(duration)
            # Don't actually sleep in tests
            await original_sleep(0)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            keys = [{'id': 'item0'}]
            result = await client.batch_get_items("TestTable", keys)
        
        assert len(result) == 1
        # Verify exponential backoff: 0.1, 0.2
        assert len(sleep_times) == 2
        assert sleep_times[0] == 0.1  # 2^0 * 0.1
        assert sleep_times[1] == 0.2  # 2^1 * 0.1

    @pytest.mark.asyncio
    async def test_batch_get_max_retries_exhausted(self, mock_client):
        """Test batch_get_items stops after max retries"""
        client, mock_boto_client = mock_client
        
        call_count = 0
        def batch_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            request_keys = kwargs['RequestItems']['TestTable']['Keys']
            
            # First call: both keys requested, item0 succeeds, item1 unprocessed
            if call_count == 1:
                return {
                    'Responses': {
                        'TestTable': [{'id': 'item0'}]
                    },
                    'UnprocessedKeys': {
                        'TestTable': {
                            'Keys': [{'id': 'item1'}]
                        }
                    }
                }
            # Subsequent calls: only item1 requested, always fails
            else:
                return {
                    'Responses': {
                        'TestTable': []
                    },
                    'UnprocessedKeys': {
                        'TestTable': {
                            'Keys': [{'id': 'item1'}]
                        }
                    }
                }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        with patch('asyncio.sleep', return_value=asyncio.sleep(0)):
            keys = [{'id': 'item0'}, {'id': 'item1'}]
            result = await client.batch_get_items("TestTable", keys)
        
        # Should get only item0 (item1 never succeeded)
        assert len(result) == 1
        assert result[0]['id'] == 'item0'
        
        # Should be called 4 times (initial + 3 retries)
        assert mock_boto_client.batch_get_item.call_count == 4

    @pytest.mark.asyncio
    async def test_batch_get_partial_failure(self, mock_client):
        """Test batch_get_items returns successful items even with partial failures"""
        client, mock_boto_client = mock_client
        
        call_count = 0
        def batch_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            request_keys = kwargs['RequestItems']['TestTable']['Keys']
            
            # First call: all 5 keys requested, 3 succeed, 2 unprocessed
            if call_count == 1:
                return {
                    'Responses': {
                        'TestTable': [
                            {'id': 'item0'},
                            {'id': 'item1'},
                            {'id': 'item2'}
                        ]
                    },
                    'UnprocessedKeys': {
                        'TestTable': {
                            'Keys': [
                                {'id': 'item3'},
                                {'id': 'item4'}
                            ]
                        }
                    }
                }
            # Subsequent calls: only item3 and item4 requested, always fail
            else:
                return {
                    'Responses': {
                        'TestTable': []
                    },
                    'UnprocessedKeys': {
                        'TestTable': {
                            'Keys': [
                                {'id': 'item3'},
                                {'id': 'item4'}
                            ]
                        }
                    }
                }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        with patch('asyncio.sleep', return_value=asyncio.sleep(0)):
            keys = [{'id': f'item{i}'} for i in range(5)]
            result = await client.batch_get_items("TestTable", keys)
        
        # Should return the 3 successful items only
        assert len(result) == 3
        assert all(item['id'] in ['item0', 'item1', 'item2'] for item in result)

    @pytest.mark.asyncio
    async def test_batch_get_exception_handling(self, mock_client):
        """Test batch_get_items handles exceptions gracefully"""
        client, mock_boto_client = mock_client
        
        call_count = 0
        def batch_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                # First call raises exception
                raise Exception("DynamoDB throttling error")
            else:
                # Second call succeeds
                return {
                    'Responses': {
                        'TestTable': [{'id': 'item0'}]
                    },
                    'UnprocessedKeys': {}
                }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        with patch('asyncio.sleep', return_value=asyncio.sleep(0)):
            keys = [{'id': 'item0'}]
            result = await client.batch_get_items("TestTable", keys)
        
        # Should succeed after retry
        assert len(result) == 1
        assert result[0]['id'] == 'item0'
        assert mock_boto_client.batch_get_item.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_get_custom_batch_size(self, mock_client):
        """Test batch_get_items with custom max_batch_size"""
        client, mock_boto_client = mock_client
        
        def batch_get_side_effect(*args, **kwargs):
            request_items = kwargs['RequestItems']['TestTable']['Keys']
            return {
                'Responses': {
                    'TestTable': [{'id': key['id']} for key in request_items]
                },
                'UnprocessedKeys': {}
            }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        # Use custom batch size of 50
        keys = [{'id': f'item{i}'} for i in range(150)]
        result = await client.batch_get_items("TestTable", keys, max_batch_size=50)
        
        assert len(result) == 150
        # Should be called 3 times (batches: 50 + 50 + 50)
        assert mock_boto_client.batch_get_item.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_get_with_decimal_values(self, mock_client):
        """Test batch_get_items handles Decimal values from DynamoDB"""
        client, mock_boto_client = mock_client
        
        # DynamoDB returns Decimal for numeric values
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'TestTable': [
                    {'id': 'item0', 'price': Decimal('19.99')},
                    {'id': 'item1', 'price': Decimal('29.99')}
                ]
            },
            'UnprocessedKeys': {}
        }
        
        keys = [{'id': 'item0'}, {'id': 'item1'}]
        result = await client.batch_get_items("TestTable", keys)
        
        assert len(result) == 2
        assert isinstance(result[0]['price'], Decimal)
        assert result[0]['price'] == Decimal('19.99')


class TestBatchConvenienceMethods:
    """Test suite for batch convenience methods"""

    @pytest.fixture
    def mock_client(self):
        """Create a mock DynamoDB client"""
        with patch('database.dynamodb.boto3') as mock_boto3:
            # Mock the resource and client
            mock_resource = Mock()
            mock_client = Mock()
            mock_boto3.resource.return_value = mock_resource
            mock_boto3.client.return_value = mock_client
            
            # Reset singleton
            DynamoDBClient._instance = None
            
            # Create client instance
            client = DynamoDBClient()
            
            yield client, mock_client

    @pytest.mark.asyncio
    async def test_batch_get_crew_members_empty(self, mock_client):
        """Test batch_get_crew_members with empty list"""
        client, _ = mock_client
        
        result = await client.batch_get_crew_members([])
        
        assert result == []

    @pytest.mark.asyncio
    async def test_batch_get_crew_members_single(self, mock_client):
        """Test batch_get_crew_members with single crew member"""
        client, mock_boto_client = mock_client
        
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CrewMembers': [
                    {
                        'crew_id': 'C001',
                        'name': 'John Doe',
                        'position': 'Captain',
                        'qualifications': ['A320', 'A380']
                    }
                ]
            },
            'UnprocessedKeys': {}
        }
        
        result = await client.batch_get_crew_members(['C001'])
        
        assert len(result) == 1
        assert result[0]['crew_id'] == 'C001'
        assert result[0]['name'] == 'John Doe'
        assert result[0]['position'] == 'Captain'

    @pytest.mark.asyncio
    async def test_batch_get_crew_members_multiple(self, mock_client):
        """Test batch_get_crew_members with multiple crew members"""
        client, mock_boto_client = mock_client
        
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CrewMembers': [
                    {'crew_id': 'C001', 'name': 'John Doe', 'position': 'Captain'},
                    {'crew_id': 'C002', 'name': 'Jane Smith', 'position': 'First Officer'},
                    {'crew_id': 'C003', 'name': 'Bob Johnson', 'position': 'Flight Attendant'}
                ]
            },
            'UnprocessedKeys': {}
        }
        
        result = await client.batch_get_crew_members(['C001', 'C002', 'C003'])
        
        assert len(result) == 3
        assert all('crew_id' in member for member in result)
        assert all('name' in member for member in result)

    def test_batch_get_flights_empty(self, mock_client):
        """Test batch_get_flights with empty list"""
        client, _ = mock_client
        
        result = client.batch_get_flights([])
        
        assert result == []

    def test_batch_get_flights_single(self, mock_client):
        """Test batch_get_flights with single flight"""
        client, mock_boto_client = mock_client
        
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'Flights': [
                    {
                        'flight_id': 'FL001',
                        'flight_number': 'EY123',
                        'origin': 'AUH',
                        'destination': 'LHR',
                        'status': 'scheduled'
                    }
                ]
            },
            'UnprocessedKeys': {}
        }
        
        result = client.batch_get_flights(['FL001'])
        
        assert len(result) == 1
        assert result[0]['flight_id'] == 'FL001'
        assert result[0]['flight_number'] == 'EY123'

    def test_batch_get_flights_multiple(self, mock_client):
        """Test batch_get_flights with multiple flights"""
        client, mock_boto_client = mock_client
        
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'Flights': [
                    {'flight_id': 'FL001', 'flight_number': 'EY123', 'origin': 'AUH'},
                    {'flight_id': 'FL002', 'flight_number': 'EY456', 'origin': 'DXB'},
                    {'flight_id': 'FL003', 'flight_number': 'EY789', 'origin': 'LHR'}
                ]
            },
            'UnprocessedKeys': {}
        }
        
        result = client.batch_get_flights(['FL001', 'FL002', 'FL003'])
        
        assert len(result) == 3
        assert all('flight_id' in flight for flight in result)

    @pytest.mark.asyncio
    async def test_batch_get_passengers_empty(self, mock_client):
        """Test batch_get_passengers with empty list"""
        client, _ = mock_client
        
        result = await client.batch_get_passengers([])
        
        assert result == []

    @pytest.mark.asyncio
    async def test_batch_get_passengers_single(self, mock_client):
        """Test batch_get_passengers with single passenger"""
        client, mock_boto_client = mock_client
        
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'Passengers': [
                    {
                        'passenger_id': 'P001',
                        'name': 'Alice Brown',
                        'tier': 'Gold',
                        'email': 'alice@example.com'
                    }
                ]
            },
            'UnprocessedKeys': {}
        }
        
        result = await client.batch_get_passengers(['P001'])
        
        assert len(result) == 1
        assert result[0]['passenger_id'] == 'P001'
        assert result[0]['name'] == 'Alice Brown'

    @pytest.mark.asyncio
    async def test_batch_get_passengers_multiple(self, mock_client):
        """Test batch_get_passengers with multiple passengers"""
        client, mock_boto_client = mock_client
        
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'Passengers': [
                    {'passenger_id': 'P001', 'name': 'Alice Brown', 'tier': 'Gold'},
                    {'passenger_id': 'P002', 'name': 'Bob Wilson', 'tier': 'Silver'},
                    {'passenger_id': 'P003', 'name': 'Carol Davis', 'tier': 'Platinum'}
                ]
            },
            'UnprocessedKeys': {}
        }
        
        result = await client.batch_get_passengers(['P001', 'P002', 'P003'])
        
        assert len(result) == 3
        assert all('passenger_id' in passenger for passenger in result)

    @pytest.mark.asyncio
    async def test_batch_get_cargo_shipments_empty(self, mock_client):
        """Test batch_get_cargo_shipments with empty list"""
        client, _ = mock_client
        
        result = await client.batch_get_cargo_shipments([])
        
        assert result == []

    @pytest.mark.asyncio
    async def test_batch_get_cargo_shipments_single(self, mock_client):
        """Test batch_get_cargo_shipments with single shipment"""
        client, mock_boto_client = mock_client
        
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CargoShipments': [
                    {
                        'shipment_id': 'SH001',
                        'weight_kg': Decimal('150.5'),
                        'priority': 'high',
                        'contents': 'Electronics'
                    }
                ]
            },
            'UnprocessedKeys': {}
        }
        
        result = await client.batch_get_cargo_shipments(['SH001'])
        
        assert len(result) == 1
        assert result[0]['shipment_id'] == 'SH001'
        assert result[0]['priority'] == 'high'

    @pytest.mark.asyncio
    async def test_batch_get_cargo_shipments_multiple(self, mock_client):
        """Test batch_get_cargo_shipments with multiple shipments"""
        client, mock_boto_client = mock_client
        
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CargoShipments': [
                    {'shipment_id': 'SH001', 'weight_kg': Decimal('150.5'), 'priority': 'high'},
                    {'shipment_id': 'SH002', 'weight_kg': Decimal('200.0'), 'priority': 'medium'},
                    {'shipment_id': 'SH003', 'weight_kg': Decimal('75.3'), 'priority': 'low'}
                ]
            },
            'UnprocessedKeys': {}
        }
        
        result = await client.batch_get_cargo_shipments(['SH001', 'SH002', 'SH003'])
        
        assert len(result) == 3
        assert all('shipment_id' in shipment for shipment in result)

    @pytest.mark.asyncio
    async def test_batch_convenience_methods_use_correct_table(self, mock_client):
        """Test that convenience methods call batch_get_items with correct table names"""
        client, mock_boto_client = mock_client
        
        # Mock response for any table
        def batch_get_side_effect(*args, **kwargs):
            table_name = list(kwargs['RequestItems'].keys())[0]
            keys = kwargs['RequestItems'][table_name]['Keys']
            return {
                'Responses': {
                    table_name: [key for key in keys]
                },
                'UnprocessedKeys': {}
            }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        # Test crew members
        await client.batch_get_crew_members(['C001'])
        call_args = mock_boto_client.batch_get_item.call_args
        assert 'CrewMembers' in call_args[1]['RequestItems']
        
        # Test flights
        await client.batch_get_flights(['FL001'])
        call_args = mock_boto_client.batch_get_item.call_args
        assert 'Flights' in call_args[1]['RequestItems']
        
        # Test passengers
        await client.batch_get_passengers(['P001'])
        call_args = mock_boto_client.batch_get_item.call_args
        assert 'Passengers' in call_args[1]['RequestItems']
        
        # Test cargo shipments
        await client.batch_get_cargo_shipments(['SH001'])
        call_args = mock_boto_client.batch_get_item.call_args
        assert 'CargoShipments' in call_args[1]['RequestItems']

    @pytest.mark.asyncio
    async def test_batch_convenience_methods_use_correct_keys(self, mock_client):
        """Test that convenience methods construct correct primary keys"""
        client, mock_boto_client = mock_client
        
        # Mock response
        def batch_get_side_effect(*args, **kwargs):
            table_name = list(kwargs['RequestItems'].keys())[0]
            return {
                'Responses': {table_name: []},
                'UnprocessedKeys': {}
            }
        
        mock_boto_client.batch_get_item.side_effect = batch_get_side_effect
        
        # Test crew members - should use crew_id
        await client.batch_get_crew_members(['C001', 'C002'])
        call_args = mock_boto_client.batch_get_item.call_args
        keys = call_args[1]['RequestItems']['CrewMembers']['Keys']
        assert keys == [{'crew_id': 'C001'}, {'crew_id': 'C002'}]
        
        # Test flights - should use flight_id
        await client.batch_get_flights(['FL001', 'FL002'])
        call_args = mock_boto_client.batch_get_item.call_args
        keys = call_args[1]['RequestItems']['Flights']['Keys']
        assert keys == [{'flight_id': 'FL001'}, {'flight_id': 'FL002'}]
        
        # Test passengers - should use passenger_id
        await client.batch_get_passengers(['P001', 'P002'])
        call_args = mock_boto_client.batch_get_item.call_args
        keys = call_args[1]['RequestItems']['Passengers']['Keys']
        assert keys == [{'passenger_id': 'P001'}, {'passenger_id': 'P002'}]
        
        # Test cargo shipments - should use shipment_id
        await client.batch_get_cargo_shipments(['SH001', 'SH002'])
        call_args = mock_boto_client.batch_get_item.call_args
        keys = call_args[1]['RequestItems']['CargoShipments']['Keys']
        assert keys == [{'shipment_id': 'SH001'}, {'shipment_id': 'SH002'}]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])


class TestCrewComplianceTools:
    """Test suite for crew compliance tools using batch queries"""

    @pytest.fixture
    def mock_client(self):
        """Create a mock DynamoDB client"""
        with patch('database.dynamodb.boto3') as mock_boto3:
            # Mock the resource and client
            mock_resource = Mock()
            mock_client = Mock()
            mock_boto3.resource.return_value = mock_resource
            mock_boto3.client.return_value = mock_client
            
            # Mock table objects
            mock_crew_roster_table = Mock()
            mock_crew_members_table = Mock()
            mock_resource.Table.side_effect = lambda name: {
                'CrewRoster': mock_crew_roster_table,
                'CrewMembers': mock_crew_members_table,
            }.get(name, Mock())
            
            # Reset singleton
            DynamoDBClient._instance = None
            
            # Create client instance
            client = DynamoDBClient()
            
            yield client, mock_client, mock_crew_roster_table, mock_crew_members_table

    @pytest.mark.asyncio
    async def test_query_crew_roster_and_members_empty_roster(self, mock_client):
        """Test query_crew_roster_and_members with empty roster"""
        from database.tools import get_crew_compliance_tools
        
        client, mock_boto_client, mock_roster_table, mock_members_table = mock_client
        
        # Mock empty roster
        mock_roster_table.query.return_value = {
            'Items': []
        }
        
        tools = get_crew_compliance_tools()
        query_tool = tools[2]  # query_crew_roster_and_members is the third tool
        
        result_json = query_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        assert result['flight_id'] == 'FL001'
        assert result['crew_count'] == 0
        assert result['roster'] == []
        assert result['crew_members'] == []
        assert result['query_count'] == 1

    @pytest.mark.asyncio
    async def test_query_crew_roster_and_members_single_crew(self, mock_client):
        """Test query_crew_roster_and_members with single crew member"""
        from database.tools import get_crew_compliance_tools
        
        client, mock_boto_client, mock_roster_table, mock_members_table = mock_client
        
        # Mock roster with one crew member
        mock_roster_table.query.return_value = {
            'Items': [
                {
                    'flight_id': 'FL001',
                    'crew_id': 'C001',
                    'position_id': 'Captain',
                    'duty_start': '2024-01-15T08:00:00Z',
                    'duty_end': '2024-01-15T16:00:00Z'
                }
            ]
        }
        
        # Mock batch get crew members
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CrewMembers': [
                    {
                        'crew_id': 'C001',
                        'name': 'John Doe',
                        'position': 'Captain',
                        'qualifications': ['A320', 'A380'],
                        'max_fdp_hours': Decimal('13')
                    }
                ]
            },
            'UnprocessedKeys': {}
        }
        
        tools = get_crew_compliance_tools()
        query_tool = tools[2]  # query_crew_roster_and_members
        
        result_json = query_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        assert result['flight_id'] == 'FL001'
        assert result['crew_count'] == 1
        assert result['query_count'] == 2
        assert len(result['roster']) == 1
        assert len(result['crew_members']) == 1
        
        # Verify roster is enriched with crew member details
        enriched_assignment = result['roster'][0]
        assert enriched_assignment['crew_id'] == 'C001'
        assert enriched_assignment['position_id'] == 'Captain'
        assert enriched_assignment['crew_member_details'] is not None
        assert enriched_assignment['crew_member_details']['name'] == 'John Doe'

    @pytest.mark.asyncio
    async def test_query_crew_roster_and_members_multiple_crew(self, mock_client):
        """Test query_crew_roster_and_members with multiple crew members"""
        from database.tools import get_crew_compliance_tools
        
        client, mock_boto_client, mock_roster_table, mock_members_table = mock_client
        
        # Mock roster with 4 crew members (typical flight crew)
        mock_roster_table.query.return_value = {
            'Items': [
                {'flight_id': 'FL001', 'crew_id': 'C001', 'position_id': 'Captain'},
                {'flight_id': 'FL001', 'crew_id': 'C002', 'position_id': 'First Officer'},
                {'flight_id': 'FL001', 'crew_id': 'C003', 'position_id': 'Flight Attendant'},
                {'flight_id': 'FL001', 'crew_id': 'C004', 'position_id': 'Flight Attendant'}
            ]
        }
        
        # Mock batch get crew members
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CrewMembers': [
                    {'crew_id': 'C001', 'name': 'John Doe', 'position': 'Captain'},
                    {'crew_id': 'C002', 'name': 'Jane Smith', 'position': 'First Officer'},
                    {'crew_id': 'C003', 'name': 'Bob Johnson', 'position': 'Flight Attendant'},
                    {'crew_id': 'C004', 'name': 'Alice Brown', 'position': 'Flight Attendant'}
                ]
            },
            'UnprocessedKeys': {}
        }
        
        tools = get_crew_compliance_tools()
        query_tool = tools[2]  # query_crew_roster_and_members
        
        result_json = query_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        assert result['flight_id'] == 'FL001'
        assert result['crew_count'] == 4
        assert result['query_count'] == 2
        assert len(result['roster']) == 4
        assert len(result['crew_members']) == 4
        
        # Verify optimization message
        assert 'optimization' in result
        assert '5 queries to 2 queries' in result['optimization']
        
        # Verify all roster entries are enriched
        for assignment in result['roster']:
            assert 'crew_member_details' in assignment
            assert assignment['crew_member_details'] is not None

    @pytest.mark.asyncio
    async def test_query_crew_roster_and_members_batch_call(self, mock_client):
        """Test that query_crew_roster_and_members uses batch_get_item correctly"""
        from database.tools import get_crew_compliance_tools
        
        client, mock_boto_client, mock_roster_table, mock_members_table = mock_client
        
        # Mock roster with 3 crew members
        mock_roster_table.query.return_value = {
            'Items': [
                {'flight_id': 'FL001', 'crew_id': 'C001', 'position_id': 'Captain'},
                {'flight_id': 'FL001', 'crew_id': 'C002', 'position_id': 'First Officer'},
                {'flight_id': 'FL001', 'crew_id': 'C003', 'position_id': 'Flight Attendant'}
            ]
        }
        
        # Mock batch get crew members
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CrewMembers': [
                    {'crew_id': 'C001', 'name': 'John Doe'},
                    {'crew_id': 'C002', 'name': 'Jane Smith'},
                    {'crew_id': 'C003', 'name': 'Bob Johnson'}
                ]
            },
            'UnprocessedKeys': {}
        }
        
        tools = get_crew_compliance_tools()
        query_tool = tools[2]  # query_crew_roster_and_members
        
        query_tool.invoke({'flight_id': 'FL001'})
        
        # Verify batch_get_item was called once
        mock_boto_client.batch_get_item.assert_called_once()
        
        # Verify correct keys were passed
        call_args = mock_boto_client.batch_get_item.call_args
        keys = call_args[1]['RequestItems']['CrewMembers']['Keys']
        assert len(keys) == 3
        assert keys == [
            {'crew_id': 'C001'},
            {'crew_id': 'C002'},
            {'crew_id': 'C003'}
        ]

    @pytest.mark.asyncio
    async def test_query_crew_roster_and_members_missing_crew_member(self, mock_client):
        """Test query_crew_roster_and_members when some crew members are not found"""
        from database.tools import get_crew_compliance_tools
        
        client, mock_boto_client, mock_roster_table, mock_members_table = mock_client
        
        # Mock roster with 3 crew members
        mock_roster_table.query.return_value = {
            'Items': [
                {'flight_id': 'FL001', 'crew_id': 'C001', 'position_id': 'Captain'},
                {'flight_id': 'FL001', 'crew_id': 'C002', 'position_id': 'First Officer'},
                {'flight_id': 'FL001', 'crew_id': 'C003', 'position_id': 'Flight Attendant'}
            ]
        }
        
        # Mock batch get - only 2 crew members found
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CrewMembers': [
                    {'crew_id': 'C001', 'name': 'John Doe'},
                    {'crew_id': 'C002', 'name': 'Jane Smith'}
                    # C003 not found
                ]
            },
            'UnprocessedKeys': {}
        }
        
        tools = get_crew_compliance_tools()
        query_tool = tools[2]  # query_crew_roster_and_members
        
        result_json = query_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        assert result['crew_count'] == 3
        assert len(result['crew_members']) == 2
        
        # Verify roster entries - C003 should have None for crew_member_details
        c003_assignment = [a for a in result['roster'] if a['crew_id'] == 'C003'][0]
        assert c003_assignment['crew_member_details'] is None

    @pytest.mark.asyncio
    async def test_query_crew_roster_and_members_performance_improvement(self, mock_client):
        """Test that query_crew_roster_and_members reduces query count"""
        from database.tools import get_crew_compliance_tools
        
        client, mock_boto_client, mock_roster_table, mock_members_table = mock_client
        
        # Mock roster with 6 crew members (large crew)
        crew_count = 6
        mock_roster_table.query.return_value = {
            'Items': [
                {'flight_id': 'FL001', 'crew_id': f'C{i:03d}', 'position_id': 'Crew'}
                for i in range(1, crew_count + 1)
            ]
        }
        
        # Mock batch get crew members
        mock_boto_client.batch_get_item.return_value = {
            'Responses': {
                'CrewMembers': [
                    {'crew_id': f'C{i:03d}', 'name': f'Crew Member {i}'}
                    for i in range(1, crew_count + 1)
                ]
            },
            'UnprocessedKeys': {}
        }
        
        tools = get_crew_compliance_tools()
        query_tool = tools[2]  # query_crew_roster_and_members
        
        result_json = query_tool.invoke({'flight_id': 'FL001'})
        result = json.loads(result_json)
        
        # Verify query count is 2 (roster + batch) instead of 7 (roster + 6 individual)
        assert result['query_count'] == 2
        
        # Verify optimization message shows the improvement
        assert 'optimization' in result
        assert f'{1 + crew_count} queries to 2 queries' in result['optimization']
        
        # Old approach would have been: 1 roster query + 6 individual crew queries = 7 total
        # New approach: 1 roster query + 1 batch query = 2 total
        # Improvement: 71% reduction in queries (5 fewer queries)
