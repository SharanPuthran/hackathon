#!/usr/bin/env python3
"""
Verify all DynamoDB tables have data
"""

import os
import boto3

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
client = boto3.client('dynamodb', region_name=AWS_REGION)

# Expected counts based on CSV files
EXPECTED_COUNTS = {
    'flights': 100,
    'aircraft': 50,
    'crew_members': 500,
    'crew_assignments': 1000,
    'passengers': 5000,
    'bookings': 5000,
    'cargo_shipments': 500,
    'disruptions': 20,
    'financial_transactions': 15391,
    'disruption_costs': 100,
    'financial_parameters': 50,
    'disrupted_passengers_scenario': 300,
    'aircraft_swap_options': 10,
    'inbound_flight_impact': 5
}

def scan_table_count(table_name):
    """Get accurate count by scanning"""
    table = dynamodb.Table(table_name)
    
    count = 0
    last_evaluated_key = None
    
    while True:
        if last_evaluated_key:
            response = table.scan(
                Select='COUNT',
                ExclusiveStartKey=last_evaluated_key
            )
        else:
            response = table.scan(Select='COUNT')
        
        count += response['Count']
        
        last_evaluated_key = response.get('LastEvaluatedKey')
        if not last_evaluated_key:
            break
    
    return count


def main():
    print("\n" + "="*80)
    print("COMPLETE DYNAMODB VERIFICATION")
    print("="*80)
    
    # List all tables
    try:
        response = client.list_tables()
        all_tables = response.get('TableNames', [])
        print(f"\nFound {len(all_tables)} tables in DynamoDB")
    except Exception as e:
        print(f"❌ Error listing tables: {e}")
        return 1
    
    # Check each expected table
    print("\n" + "-"*80)
    print(f"{'Table Name':<40} {'Actual':<10} {'Expected':<10} {'Status'}")
    print("-"*80)
    
    results = {}
    total_items = 0
    all_good = True
    
    for table_name in sorted(EXPECTED_COUNTS.keys()):
        expected = EXPECTED_COUNTS[table_name]
        
        if table_name not in all_tables:
            print(f"{table_name:<40} {'N/A':<10} {expected:<10} ❌ MISSING")
            results[table_name] = {'status': 'missing', 'actual': 0, 'expected': expected}
            all_good = False
            continue
        
        try:
            actual = scan_table_count(table_name)
            total_items += actual
            
            if actual == expected:
                status = "✅"
                results[table_name] = {'status': 'ok', 'actual': actual, 'expected': expected}
            elif actual == 0:
                status = "❌ EMPTY"
                results[table_name] = {'status': 'empty', 'actual': actual, 'expected': expected}
                all_good = False
            else:
                pct = (actual / expected * 100) if expected > 0 else 0
                status = f"⚠️  {pct:.1f}%"
                results[table_name] = {'status': 'partial', 'actual': actual, 'expected': expected}
                if pct < 95:
                    all_good = False
            
            print(f"{table_name:<40} {actual:<10} {expected:<10} {status}")
            
        except Exception as e:
            print(f"{table_name:<40} {'ERROR':<10} {expected:<10} ❌ {str(e)[:20]}")
            results[table_name] = {'status': 'error', 'actual': 0, 'expected': expected}
            all_good = False
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    ok_count = sum(1 for r in results.values() if r['status'] == 'ok')
    partial_count = sum(1 for r in results.values() if r['status'] == 'partial')
    empty_count = sum(1 for r in results.values() if r['status'] == 'empty')
    missing_count = sum(1 for r in results.values() if r['status'] == 'missing')
    error_count = sum(1 for r in results.values() if r['status'] == 'error')
    
    print(f"✅ Complete:  {ok_count}/{len(EXPECTED_COUNTS)} tables")
    if partial_count > 0:
        print(f"⚠️  Partial:   {partial_count} tables")
    if empty_count > 0:
        print(f"❌ Empty:     {empty_count} tables")
    if missing_count > 0:
        print(f"❌ Missing:   {missing_count} tables")
    if error_count > 0:
        print(f"❌ Errors:    {error_count} tables")
    
    print(f"\n📊 Total items in database: {total_items:,}")
    
    if all_good:
        print("\n✅ ALL TABLES VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("\n⚠️  SOME TABLES NEED ATTENTION")
        
        # Show which tables need work
        problem_tables = [name for name, r in results.items() 
                         if r['status'] in ['empty', 'missing', 'error']]
        if problem_tables:
            print("\nTables needing attention:")
            for table in problem_tables:
                print(f"  - {table}")
        
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
