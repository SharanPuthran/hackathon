#!/usr/bin/env python3
"""
Verify upload success by scanning tables
"""

import os
import boto3
import time

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)

TABLES = ['financial_transactions', 'disruption_costs']

def count_items_by_scan(table_name):
    """Count items by scanning the entire table"""
    table = dynamodb.Table(table_name)
    
    print(f"\nScanning {table_name}...", end=" ")
    
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
    
    print(f"✅ {count:,} items")
    return count


def get_sample_items(table_name, limit=5):
    """Get sample items from table"""
    table = dynamodb.Table(table_name)
    
    response = table.scan(Limit=limit)
    items = response.get('Items', [])
    
    if items:
        print(f"\nSample items from {table_name}:")
        key_schema = table.key_schema
        key_name = key_schema[0]['AttributeName']
        
        for i, item in enumerate(items[:3], 1):
            key_value = item.get(key_name, 'N/A')
            # Show a few other fields
            other_fields = {k: v for k, v in list(item.items())[:5] if k != key_name}
            print(f"  {i}. {key_name}={key_value}")
            for k, v in other_fields.items():
                print(f"     {k}={v}")


def main():
    print("\n" + "="*80)
    print("VERIFY DYNAMODB UPLOAD SUCCESS")
    print("="*80)
    
    expected_counts = {
        'financial_transactions': 15391,
        'disruption_costs': 100
    }
    
    results = {}
    
    for table_name in TABLES:
        try:
            actual_count = count_items_by_scan(table_name)
            expected_count = expected_counts.get(table_name, 0)
            
            results[table_name] = {
                'actual': actual_count,
                'expected': expected_count,
                'success': actual_count == expected_count
            }
            
            # Get sample items
            get_sample_items(table_name)
            
        except Exception as e:
            print(f"\n❌ Error scanning {table_name}: {e}")
            results[table_name] = {
                'actual': 0,
                'expected': expected_counts.get(table_name, 0),
                'success': False,
                'error': str(e)
            }
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    all_success = True
    
    for table_name, result in results.items():
        actual = result['actual']
        expected = result['expected']
        success = result['success']
        
        if success:
            print(f"✅ {table_name:35} {actual:>8}/{expected:<8} items (100%)")
        else:
            all_success = False
            error_msg = result.get('error', '')
            if error_msg:
                print(f"❌ {table_name:35} Error: {error_msg}")
            else:
                pct = (actual / expected * 100) if expected > 0 else 0
                print(f"⚠️  {table_name:35} {actual:>8}/{expected:<8} items ({pct:.1f}%)")
    
    if all_success:
        print("\n✅ ALL TABLES VERIFIED SUCCESSFULLY!")
        print("   - 15,391 financial_transactions uploaded")
        print("   - 100 disruption_costs uploaded")
        print("   - 0 errors")
        return 0
    else:
        print("\n⚠️  VERIFICATION INCOMPLETE")
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
