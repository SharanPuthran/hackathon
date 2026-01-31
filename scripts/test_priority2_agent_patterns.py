#!/usr/bin/env python3
"""
Test Priority 2 GSIs with Agent-Specific Query Patterns

This script validates Priority 2 GSIs by testing actual agent query patterns:
- Regulatory Agent: Curfew compliance queries
- Cargo Agent: Cold chain identification queries  
- Maintenance Agent: Conflict detection queries

It measures query latency improvements and validates that queries use GSIs.
"""

import boto3
import json
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from decimal import Decimal

# Initialize DynamoDB resources
dynamodb = boto3.resource('dynamodb')
dynamodb_client = boto3.client('dynamodb')


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder for Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def get_sample_data_for_queries() -> Dict:
    """
    Get sample data from tables to use in test queries.
    
    Returns:
        Dictionary with sample data for each agent's queries
    """
    sample_data = {
        'airports': [],
        'commodity_types': [],
        'aircraft_registrations': []
    }
    
    try:
        # Get sample airports from flights table
        # Note: destination_airport_id is stored as Decimal (number)
        flights_table = dynamodb.Table('flights')
        response = flights_table.scan(Limit=20)
        airports = set()
        for item in response.get('Items', []):
            if 'destination_airport_id' in item:
                # Convert Decimal to int for consistency
                airports.add(int(item['destination_airport_id']))
        sample_data['airports'] = list(airports)[:3]
        
        # Get sample commodity types from CargoShipments
        # Note: commodity_type_id is stored as Decimal (number)
        cargo_table = dynamodb.Table('CargoShipments')
        response = cargo_table.scan(Limit=20)
        commodity_types = set()
        for item in response.get('Items', []):
            if 'commodity_type_id' in item:
                # Convert Decimal to int for consistency
                commodity_types.add(int(item['commodity_type_id']))
        sample_data['commodity_types'] = list(commodity_types)[:3]
        
        # Get sample aircraft registrations from MaintenanceWorkOrders
        maint_table = dynamodb.Table('MaintenanceWorkOrders')
        response = maint_table.scan(Limit=10)
        aircraft = set()
        for item in response.get('Items', []):
            if 'aircraft_registration' in item:
                aircraft.add(item['aircraft_registration'])
        sample_data['aircraft_registrations'] = list(aircraft)[:3]
        
    except Exception as e:
        print(f"  ⚠ Error getting sample data: {str(e)}")
    
    return sample_data


def test_regulatory_agent_curfew_queries(sample_data: Dict) -> Dict:
    """
    Test Regulatory Agent curfew compliance queries.
    
    Query Pattern: Find all flights arriving at airport near curfew time
    GSI: airport-curfew-index (PK: destination_airport_id, SK: scheduled_arrival)
    
    Returns:
        Test results dictionary
    """
    print("\n" + "="*80)
    print("Regulatory Agent: Curfew Compliance Queries")
    print("="*80)
    
    results = {
        'agent': 'Regulatory Agent',
        'use_case': 'Curfew compliance checks',
        'gsi': 'airport-curfew-index',
        'queries': []
    }
    
    flights_table = dynamodb.Table('flights')
    airports = sample_data.get('airports', [])
    
    if not airports:
        print("  ⚠ No sample airports found, using default")
        airports = ['AUH', 'DXB', 'JFK']
    
    print(f"\nTesting curfew queries for {len(airports)} airports...")
    
    for airport in airports:
        print(f"\n  Airport: {airport}")
        
        # Query 1: Find flights arriving at airport (using GSI)
        print(f"    [1/2] Query with GSI (airport-curfew-index)...", end=' ')
        
        try:
            start_time = time.time()
            
            response = flights_table.query(
                IndexName='airport-curfew-index',
                KeyConditionExpression='destination_airport_id = :airport',
                ExpressionAttributeValues={
                    ':airport': airport
                },
                Limit=50
            )
            
            gsi_latency = (time.time() - start_time) * 1000
            gsi_count = len(response.get('Items', []))
            
            print(f"✓ {gsi_count} flights, {gsi_latency:.2f}ms")
            
            # Query 2: Same query without GSI (table scan) for comparison
            print(f"    [2/2] Query without GSI (table scan)...", end=' ')
            
            start_time = time.time()
            
            response = flights_table.scan(
                FilterExpression='destination_airport_id = :airport',
                ExpressionAttributeValues={
                    ':airport': airport
                },
                Limit=50
            )
            
            scan_latency = (time.time() - start_time) * 1000
            scan_count = len(response.get('Items', []))
            
            print(f"✓ {scan_count} flights, {scan_latency:.2f}ms")
            
            # Calculate improvement
            if scan_latency > 0:
                improvement = scan_latency / gsi_latency if gsi_latency > 0 else 0
                print(f"    📊 Performance improvement: {improvement:.1f}x faster with GSI")
            
            results['queries'].append({
                'airport': airport,
                'gsi_latency_ms': gsi_latency,
                'scan_latency_ms': scan_latency,
                'improvement_factor': improvement if scan_latency > 0 else 0,
                'items_found': gsi_count,
                'status': 'PASSED' if gsi_latency < 100 else 'WARNING'
            })
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            results['queries'].append({
                'airport': airport,
                'error': str(e),
                'status': 'FAILED'
            })
    
    # Calculate average metrics
    successful_queries = [q for q in results['queries'] if 'gsi_latency_ms' in q]
    if successful_queries:
        avg_gsi_latency = sum(q['gsi_latency_ms'] for q in successful_queries) / len(successful_queries)
        avg_improvement = sum(q['improvement_factor'] for q in successful_queries) / len(successful_queries)
        
        results['summary'] = {
            'total_queries': len(results['queries']),
            'successful': len(successful_queries),
            'avg_gsi_latency_ms': avg_gsi_latency,
            'avg_improvement_factor': avg_improvement,
            'meets_target': avg_gsi_latency < 100
        }
        
        print(f"\n  Summary:")
        print(f"    Average GSI latency: {avg_gsi_latency:.2f}ms")
        print(f"    Average improvement: {avg_improvement:.1f}x")
        print(f"    Target (<100ms): {'✓ PASS' if avg_gsi_latency < 100 else '⚠ WARNING'}")
    
    return results


def test_cargo_agent_cold_chain_queries(sample_data: Dict) -> Dict:
    """
    Test Cargo Agent cold chain identification queries.
    
    Query Pattern: Find temperature-sensitive cargo for special handling
    GSI: cargo-temperature-index (PK: commodity_type_id, SK: temperature_requirement)
    
    Returns:
        Test results dictionary
    """
    print("\n" + "="*80)
    print("Cargo Agent: Cold Chain Identification Queries")
    print("="*80)
    
    results = {
        'agent': 'Cargo Agent',
        'use_case': 'Cold chain identification',
        'gsi': 'cargo-temperature-index',
        'queries': []
    }
    
    cargo_table = dynamodb.Table('CargoShipments')
    commodity_types = sample_data.get('commodity_types', [])
    
    if not commodity_types:
        print("  ⚠ No sample commodity types found, using defaults")
        commodity_types = [1, 2, 3]  # Perishables, Pharmaceuticals, etc.
    
    print(f"\nTesting cold chain queries for {len(commodity_types)} commodity types...")
    
    for commodity_type in commodity_types:
        print(f"\n  Commodity Type: {commodity_type}")
        
        # Query 1: Find shipments by commodity type (using GSI)
        print(f"    [1/2] Query with GSI (cargo-temperature-index)...", end=' ')
        
        try:
            start_time = time.time()
            
            response = cargo_table.query(
                IndexName='cargo-temperature-index',
                KeyConditionExpression='commodity_type_id = :commodity',
                ExpressionAttributeValues={
                    ':commodity': commodity_type
                },
                Limit=50
            )
            
            gsi_latency = (time.time() - start_time) * 1000
            gsi_count = len(response.get('Items', []))
            
            # Count temperature-sensitive items
            temp_sensitive = sum(1 for item in response.get('Items', []) 
                               if item.get('temperature_requirement'))
            
            print(f"✓ {gsi_count} shipments ({temp_sensitive} temp-sensitive), {gsi_latency:.2f}ms")
            
            # Query 2: Same query without GSI (table scan) for comparison
            print(f"    [2/2] Query without GSI (table scan)...", end=' ')
            
            start_time = time.time()
            
            response = cargo_table.scan(
                FilterExpression='commodity_type_id = :commodity',
                ExpressionAttributeValues={
                    ':commodity': commodity_type
                },
                Limit=50
            )
            
            scan_latency = (time.time() - start_time) * 1000
            scan_count = len(response.get('Items', []))
            
            print(f"✓ {scan_count} shipments, {scan_latency:.2f}ms")
            
            # Calculate improvement
            if scan_latency > 0:
                improvement = scan_latency / gsi_latency if gsi_latency > 0 else 0
                print(f"    📊 Performance improvement: {improvement:.1f}x faster with GSI")
            
            results['queries'].append({
                'commodity_type': commodity_type,
                'gsi_latency_ms': gsi_latency,
                'scan_latency_ms': scan_latency,
                'improvement_factor': improvement if scan_latency > 0 else 0,
                'items_found': gsi_count,
                'temp_sensitive_count': temp_sensitive,
                'status': 'PASSED' if gsi_latency < 100 else 'WARNING'
            })
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            results['queries'].append({
                'commodity_type': commodity_type,
                'error': str(e),
                'status': 'FAILED'
            })
    
    # Calculate average metrics
    successful_queries = [q for q in results['queries'] if 'gsi_latency_ms' in q]
    if successful_queries:
        avg_gsi_latency = sum(q['gsi_latency_ms'] for q in successful_queries) / len(successful_queries)
        avg_improvement = sum(q['improvement_factor'] for q in successful_queries) / len(successful_queries)
        
        results['summary'] = {
            'total_queries': len(results['queries']),
            'successful': len(successful_queries),
            'avg_gsi_latency_ms': avg_gsi_latency,
            'avg_improvement_factor': avg_improvement,
            'meets_target': avg_gsi_latency < 100
        }
        
        print(f"\n  Summary:")
        print(f"    Average GSI latency: {avg_gsi_latency:.2f}ms")
        print(f"    Average improvement: {avg_improvement:.1f}x")
        print(f"    Target (<100ms): {'✓ PASS' if avg_gsi_latency < 100 else '⚠ WARNING'}")
    
    return results


def test_maintenance_agent_conflict_queries(sample_data: Dict) -> Dict:
    """
    Test Maintenance Agent conflict detection queries.
    
    Query Pattern: Find scheduled maintenance for aircraft within date range
    GSI: aircraft-maintenance-date-index (PK: aircraft_registration, SK: scheduled_date)
    
    Returns:
        Test results dictionary
    """
    print("\n" + "="*80)
    print("Maintenance Agent: Conflict Detection Queries")
    print("="*80)
    
    results = {
        'agent': 'Maintenance Agent',
        'use_case': 'Maintenance conflict detection',
        'gsi': 'aircraft-maintenance-date-index',
        'queries': []
    }
    
    maint_table = dynamodb.Table('MaintenanceWorkOrders')
    aircraft = sample_data.get('aircraft_registrations', [])
    
    if not aircraft:
        print("  ⚠ No sample aircraft found, using defaults")
        aircraft = ['A6-EYA', 'A6-EYB', 'A6-EYC']
    
    print(f"\nTesting conflict detection queries for {len(aircraft)} aircraft...")
    
    for aircraft_reg in aircraft:
        print(f"\n  Aircraft: {aircraft_reg}")
        
        # Query 1: Find maintenance for aircraft (using GSI)
        print(f"    [1/2] Query with GSI (aircraft-maintenance-date-index)...", end=' ')
        
        try:
            start_time = time.time()
            
            response = maint_table.query(
                IndexName='aircraft-maintenance-date-index',
                KeyConditionExpression='aircraft_registration = :reg',
                ExpressionAttributeValues={
                    ':reg': aircraft_reg
                },
                Limit=50
            )
            
            gsi_latency = (time.time() - start_time) * 1000
            gsi_count = len(response.get('Items', []))
            
            print(f"✓ {gsi_count} work orders, {gsi_latency:.2f}ms")
            
            # Query 2: Same query without GSI (table scan) for comparison
            print(f"    [2/2] Query without GSI (table scan)...", end=' ')
            
            start_time = time.time()
            
            response = maint_table.scan(
                FilterExpression='aircraft_registration = :reg',
                ExpressionAttributeValues={
                    ':reg': aircraft_reg
                },
                Limit=50
            )
            
            scan_latency = (time.time() - start_time) * 1000
            scan_count = len(response.get('Items', []))
            
            print(f"✓ {scan_count} work orders, {scan_latency:.2f}ms")
            
            # Calculate improvement
            if scan_latency > 0:
                improvement = scan_latency / gsi_latency if gsi_latency > 0 else 0
                print(f"    📊 Performance improvement: {improvement:.1f}x faster with GSI")
            
            results['queries'].append({
                'aircraft_registration': aircraft_reg,
                'gsi_latency_ms': gsi_latency,
                'scan_latency_ms': scan_latency,
                'improvement_factor': improvement if scan_latency > 0 else 0,
                'items_found': gsi_count,
                'status': 'PASSED' if gsi_latency < 100 else 'WARNING'
            })
            
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            results['queries'].append({
                'aircraft_registration': aircraft_reg,
                'error': str(e),
                'status': 'FAILED'
            })
    
    # Calculate average metrics
    successful_queries = [q for q in results['queries'] if 'gsi_latency_ms' in q]
    if successful_queries:
        avg_gsi_latency = sum(q['gsi_latency_ms'] for q in successful_queries) / len(successful_queries)
        avg_improvement = sum(q['improvement_factor'] for q in successful_queries) / len(successful_queries)
        
        results['summary'] = {
            'total_queries': len(results['queries']),
            'successful': len(successful_queries),
            'avg_gsi_latency_ms': avg_gsi_latency,
            'avg_improvement_factor': avg_improvement,
            'meets_target': avg_gsi_latency < 100
        }
        
        print(f"\n  Summary:")
        print(f"    Average GSI latency: {avg_gsi_latency:.2f}ms")
        print(f"    Average improvement: {avg_improvement:.1f}x")
        print(f"    Target (<100ms): {'✓ PASS' if avg_gsi_latency < 100 else '⚠ WARNING'}")
    
    return results


def print_overall_summary(all_results: List[Dict]) -> None:
    """Print overall test summary."""
    print("\n" + "="*80)
    print("Overall Test Summary")
    print("="*80)
    
    for result in all_results:
        agent = result['agent']
        use_case = result['use_case']
        summary = result.get('summary', {})
        
        print(f"\n{agent} - {use_case}:")
        
        if summary:
            avg_latency = summary.get('avg_gsi_latency_ms', 0)
            avg_improvement = summary.get('avg_improvement_factor', 0)
            meets_target = summary.get('meets_target', False)
            
            print(f"  Average GSI Latency: {avg_latency:.2f}ms")
            print(f"  Average Improvement: {avg_improvement:.1f}x")
            print(f"  Meets Target (<100ms): {'✓ YES' if meets_target else '⚠ NO'}")
        else:
            print(f"  ⚠ No successful queries")
    
    print("\n" + "="*80)
    print("Validation Complete")
    print("="*80)
    
    # Check if all agents meet targets
    all_pass = all(
        result.get('summary', {}).get('meets_target', False) 
        for result in all_results
    )
    
    if all_pass:
        print("\n✓ All Priority 2 GSIs meet performance targets!")
        print("\nExpected Benefits Validated:")
        print("  • Regulatory Agent: Faster curfew compliance checks")
        print("  • Cargo Agent: Faster cold chain identification")
        print("  • Maintenance Agent: Faster conflict detection")
    else:
        print("\n⚠ Some GSIs exceed latency target")
        print("\nNote: Initial queries may have higher latency due to cold start.")
        print("Run the test multiple times to see improved performance.")


def save_results(all_results: List[Dict], filename: str = 'priority2_agent_pattern_test_results.json') -> None:
    """Save test results to JSON file."""
    output = {
        'timestamp': datetime.now().isoformat(),
        'test_type': 'Priority 2 GSI Agent Pattern Validation',
        'results': all_results
    }
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2, cls=DecimalEncoder)
    
    print(f"\nResults saved to {filename}")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("Priority 2 GSI Agent Pattern Validation")
    print("="*80)
    print("\nTesting agent-specific query patterns with performance measurement")
    print()
    
    # Check AWS credentials
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"AWS Account: {identity['Account']}")
        print(f"User: {identity['Arn'].split('/')[-1]}")
    except Exception as e:
        print(f"Error: AWS credentials not configured: {e}")
        print("Please run: aws configure")
        return 1
    
    # Get AWS region
    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    print(f"Region: {region}")
    
    # Get sample data for queries
    print("\nGathering sample data for test queries...")
    sample_data = get_sample_data_for_queries()
    print(f"  Airports: {len(sample_data['airports'])}")
    print(f"  Commodity Types: {len(sample_data['commodity_types'])}")
    print(f"  Aircraft: {len(sample_data['aircraft_registrations'])}")
    
    # Run agent-specific tests
    all_results = []
    
    # Test 1: Regulatory Agent
    regulatory_results = test_regulatory_agent_curfew_queries(sample_data)
    all_results.append(regulatory_results)
    
    # Test 2: Cargo Agent
    cargo_results = test_cargo_agent_cold_chain_queries(sample_data)
    all_results.append(cargo_results)
    
    # Test 3: Maintenance Agent
    maintenance_results = test_maintenance_agent_conflict_queries(sample_data)
    all_results.append(maintenance_results)
    
    # Print overall summary
    print_overall_summary(all_results)
    
    # Save results
    save_results(all_results)
    
    # Return exit code based on whether all tests meet targets
    all_pass = all(
        result.get('summary', {}).get('meets_target', False) 
        for result in all_results
    )
    
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
