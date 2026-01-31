#!/usr/bin/env python3
"""
Analyze CSV data for issues and prepare for re-upload
"""

import os
import pandas as pd
import numpy as np

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')

def analyze_csv(file_path, key_field):
    """Analyze CSV file for data quality issues"""
    print(f"\n{'='*80}")
    print(f"Analyzing: {os.path.basename(file_path)}")
    print(f"Key field: {key_field}")
    print(f"{'='*80}")
    
    # Read CSV
    df = pd.read_csv(file_path)
    total_rows = len(df)
    print(f"Total rows: {total_rows:,}")
    
    # Check if key field exists
    if key_field not in df.columns:
        print(f"❌ ERROR: Key field '{key_field}' not found in columns!")
        print(f"Available columns: {list(df.columns)[:10]}")
        return None
    
    # Analyze key field
    print(f"\nKey field analysis:")
    print(f"  Data type: {df[key_field].dtype}")
    
    # Check for null/empty values
    null_count = df[key_field].isna().sum()
    empty_count = (df[key_field] == '').sum()
    
    print(f"  Null values: {null_count}")
    print(f"  Empty strings: {empty_count}")
    print(f"  Valid values: {total_rows - null_count - empty_count}")
    
    # Check for duplicates
    duplicate_count = df[key_field].duplicated().sum()
    print(f"  Duplicate keys: {duplicate_count}")
    
    # Show sample values
    print(f"\nSample key values:")
    print(f"  First 5: {df[key_field].head().tolist()}")
    print(f"  Last 5: {df[key_field].tail().tolist()}")
    
    # Check data types of all columns
    print(f"\nColumn data types:")
    for col in df.columns[:10]:  # First 10 columns
        dtype = df[col].dtype
        null_pct = (df[col].isna().sum() / total_rows * 100)
        print(f"  {col:30} {str(dtype):15} ({null_pct:.1f}% null)")
    
    # Identify problematic rows
    problematic_mask = df[key_field].isna() | (df[key_field] == '')
    problematic_rows = df[problematic_mask]
    
    if len(problematic_rows) > 0:
        print(f"\n⚠️  Found {len(problematic_rows)} problematic rows:")
        print(problematic_rows.head())
    
    return df, problematic_rows


def main():
    """Main analysis"""
    print("\n" + "="*80)
    print("CSV DATA ANALYSIS FOR DYNAMODB UPLOAD")
    print("="*80)
    
    files_to_check = [
        ('financial_transactions.csv', 'transaction_id'),
        ('disruption_costs.csv', 'cost_id')
    ]
    
    results = {}
    
    for filename, key_field in files_to_check:
        file_path = os.path.join(OUTPUT_DIR, filename)
        
        if not os.path.exists(file_path):
            print(f"\n❌ File not found: {file_path}")
            continue
        
        result = analyze_csv(file_path, key_field)
        if result:
            df, problematic_rows = result
            results[filename] = {
                'df': df,
                'problematic_rows': problematic_rows,
                'key_field': key_field
            }
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    for filename, data in results.items():
        df = data['df']
        problematic = data['problematic_rows']
        key_field = data['key_field']
        
        total = len(df)
        bad = len(problematic)
        good = total - bad
        
        status = "✅" if bad == 0 else "⚠️"
        print(f"{status} {filename:40} {good:>8}/{total:<8} valid rows")
        
        if bad > 0:
            print(f"   Action needed: {bad} rows have null/empty {key_field}")


if __name__ == '__main__':
    main()
