"""
Unit tests for Maintenance Agent DynamoDB query tools.

Tests verify that:
1. Tools are properly defined with correct signatures
2. Tools use correct GSIs and table names
3. Tools handle errors gracefully
4. Tools return expected data structures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from agents.maintenance.agent import (
    query_flight,
    query_maintenance_work_orders,
    query_maintenance_staff,
    query_maintenance_roster,
    query_aircraft_availability
)


class TestMaintenanceTools:
    """Test suite for maintenance agent DynamoDB query tools"""

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_flight_success(self, mock_boto3):
        """Test query_flight returns flight data successfully"""
        # Mock DynamoDB response
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [{
                'flight_id': 'FL-12345',
                'flight_number': 'EY123',
                'scheduled_departure': '2026-01-20',
                'aircraft_registration': 'A6-APX',
                'origin_airport_id': 'AUH',
                'destination_airport_id': 'LHR'
            }]
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Verify
        assert result is not None
        assert result['flight_id'] == 'FL-12345'
        assert result['flight_number'] == 'EY123'
        assert result['aircraft_registration'] == 'A6-APX'
        
        # Verify correct GSI used
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs['IndexName'] == 'flight-number-date-index'

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_flight_not_found(self, mock_boto3):
        """Test query_flight returns error dict when flight not found"""
        # Mock empty response
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_flight.invoke({"flight_number": "EY999", "date": "2026-01-20"})

        # Verify error response
        assert isinstance(result, dict)
        assert result['error'] == 'FLIGHT_NOT_FOUND'
        assert result['flight_number'] == 'EY999'
        assert result['date'] == '2026-01-20'

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_flight_error_handling(self, mock_boto3):
        """Test query_flight handles errors gracefully"""
        # Mock error
        mock_table = MagicMock()
        mock_table.query.side_effect = Exception("DynamoDB error")
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_flight.invoke({"flight_number": "EY123", "date": "2026-01-20"})

        # Verify error response
        assert isinstance(result, dict)
        assert 'error' in result
        assert result['flight_number'] == 'EY123'

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_maintenance_work_orders_success(self, mock_boto3):
        """Test query_maintenance_work_orders returns work orders"""
        # Mock DynamoDB response
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [
                {
                    'workorder_id': 'WO-10193',
                    'aircraftRegistration': 'A6-APX',
                    'status': 'OPEN',
                    'mel_item': 'Weather Radar Inoperative'
                },
                {
                    'workorder_id': 'WO-10194',
                    'aircraftRegistration': 'A6-APX',
                    'status': 'IN_PROGRESS',
                    'mel_item': 'APU Inoperative'
                }
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_maintenance_work_orders.invoke({"aircraft_registration": "A6-APX"})

        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['workorder_id'] == 'WO-10193'
        assert result[1]['status'] == 'IN_PROGRESS'
        
        # Verify correct GSI used
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs['IndexName'] == 'aircraft-registration-index'

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_maintenance_work_orders_empty(self, mock_boto3):
        """Test query_maintenance_work_orders returns empty list when no work orders"""
        # Mock empty response
        mock_table = MagicMock()
        mock_table.query.return_value = {'Items': []}
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_maintenance_work_orders.invoke({"aircraft_registration": "A6-APY"})

        # Verify
        assert isinstance(result, list)
        assert len(result) == 0

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_maintenance_staff_success(self, mock_boto3):
        """Test query_maintenance_staff returns staff details"""
        # Mock DynamoDB response
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'staff_id': 'MAINT-001',
                'name': 'John Smith',
                'qualifications': ['A380', 'B787'],
                'certifications': ['AME License'],
                'available': True
            }
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_maintenance_staff.invoke({"staff_id": "MAINT-001"})

        # Verify
        assert result is not None
        assert result['staff_id'] == 'MAINT-001'
        assert result['name'] == 'John Smith'
        assert 'A380' in result['qualifications']

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_maintenance_staff_not_found(self, mock_boto3):
        """Test query_maintenance_staff returns error dict when staff not found"""
        # Mock empty response
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_maintenance_staff.invoke({"staff_id": "MAINT-999"})

        # Verify error response
        assert isinstance(result, dict)
        assert result['error'] == 'STAFF_NOT_FOUND'
        assert result['staff_id'] == 'MAINT-999'

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_maintenance_roster_success(self, mock_boto3):
        """Test query_maintenance_roster returns staff assignments"""
        # Mock DynamoDB response
        mock_table = MagicMock()
        mock_table.query.return_value = {
            'Items': [
                {
                    'workorder_id': 'WO-10193',
                    'staff_id': 'MAINT-001',
                    'shift_start': '2026-01-20T08:00:00Z',
                    'shift_end': '2026-01-20T16:00:00Z'
                },
                {
                    'workorder_id': 'WO-10193',
                    'staff_id': 'MAINT-002',
                    'shift_start': '2026-01-20T08:00:00Z',
                    'shift_end': '2026-01-20T16:00:00Z'
                }
            ]
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_maintenance_roster.invoke({"workorder_id": "WO-10193"})

        # Verify
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['staff_id'] == 'MAINT-001'
        
        # Verify correct GSI used
        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args[1]
        assert call_kwargs['IndexName'] == 'workorder-shift-index'

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_aircraft_availability_success(self, mock_boto3):
        """Test query_aircraft_availability returns MEL status"""
        # Mock DynamoDB response
        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            'Item': {
                'aircraft_registration': 'A6-APX',
                'valid_from': '2026-01-20T00:00:00Z',
                'mel_items': [
                    {
                        'mel_reference': 'MEL-34-412',
                        'category': 'B',
                        'defect': 'Weather Radar Inoperative',
                        'expiry_date': '2026-01-23T00:00:00Z'
                    }
                ],
                'airworthiness_status': 'AIRWORTHY_WITH_MEL'
            }
        }
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_aircraft_availability.invoke({
            "aircraft_registration": "A6-APX",
            "valid_from": "2026-01-20T00:00:00Z"
        })

        # Verify
        assert result is not None
        assert result['aircraft_registration'] == 'A6-APX'
        assert result['airworthiness_status'] == 'AIRWORTHY_WITH_MEL'
        assert len(result['mel_items']) == 1

    @patch('agents.maintenance.agent.boto3.resource')
    def test_query_aircraft_availability_not_found(self, mock_boto3):
        """Test query_aircraft_availability returns error dict when not found"""
        # Mock empty response
        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_boto3.return_value.Table.return_value = mock_table

        # Execute tool
        result = query_aircraft_availability.invoke({
            "aircraft_registration": "A6-APY",
            "valid_from": "2026-01-20T00:00:00Z"
        })

        # Verify error response
        assert isinstance(result, dict)
        assert result['error'] == 'AVAILABILITY_NOT_FOUND'
        assert result['aircraft_registration'] == 'A6-APY'

    def test_tool_metadata(self):
        """Test that all tools have proper metadata for LangChain"""
        tools = [
            query_flight,
            query_maintenance_work_orders,
            query_maintenance_staff,
            query_maintenance_roster,
            query_aircraft_availability
        ]
        
        for tool in tools:
            # Verify tool has name
            assert hasattr(tool, 'name')
            assert tool.name is not None
            
            # Verify tool has description
            assert hasattr(tool, 'description')
            assert tool.description is not None
            
            # Verify tool has args_schema
            assert hasattr(tool, 'args_schema')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
