#!/usr/bin/env python3
"""
Fix CSV Data Issues for DynamoDB Upload

This script fixes the following issues:
1. Adds loading_priority to cargo_flight_assignments.csv
2. Adds position to crew_roster_enriched.csv
3. Adds status to baggage.csv

Usage:
    python3 database/fix_csv_data.py
"""

import pandas as pd
import os
import sys

# Get script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')

def fix_cargo_flight_assignments():
    """Add loading_priority column to cargo_flight_assignments.csv"""
    print("\n" + "=" * 60)
    print("Fixing cargo_flight_assignments.csv")
    print("=" * 60)
    
    csv_path = os.path.join(OUTPUT_DIR, 'cargo_flight_assignments.csv')
    
    if not os.path.exists(csv_path):
        print(f"✗ File not found: {csv_path}")
        return False
    
    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"  Loaded {len(df)} rows")
        
        # Check if loading_priority already exists
        if 'loading_priority' in df.columns:
            print("  ℹ loading_priority column already exists")
            print(f"  Sample values: {df['loading_priority'].head(3).tolist()}")
            return True
        
        # Add loading_priority based on sequence_number
        if 'sequence_number' in df.columns:
            df['loading_priority'] = df['sequence_number']
            print("  ✓ Added loading_priority from sequence_number")
        else:
            # If no sequence_number, use row index + 1
            df['loading_priority'] = range(1, len(df) + 1)
            print("  ✓ Added loading_priority as sequential numbers")
        
        # Save
        df.to_csv(csv_path, index=False)
        print(f"  ✓ Saved {len(df)} rows")
        print(f"  Sample loading_priority values: {df['loading_priority'].head(3).tolist()}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def fix_crew_roster():
    """Add position column to crew_roster_enriched.csv"""
    print("\n" + "=" * 60)
    print("Fixing crew_roster_enriched.csv")
    print("=" * 60)
    
    csv_path = os.path.join(OUTPUT_DIR, 'crew_roster_enriched.csv')
    
    if not os.path.exists(csv_path):
        print(f"✗ File not found: {csv_path}")
        return False
    
    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"  Loaded {len(df)} rows")
        
        # Check if position already exists
        if 'position' in df.columns:
            print("  ℹ position column already exists")
            print(f"  Sample values: {df['position'].head(3).tolist()}")
            return True
        
        # Map position_id to position names
        position_map = {
            1: 'Captain',
            2: 'First Officer',
            3: 'Cabin Manager',
            4: 'Senior FA',
            5: 'Flight Attendant',
            6: 'Purser',
            7: 'Relief Pilot',
            8: 'Check Captain'
        }
        
        if 'position_id' in df.columns:
            df['position'] = df['position_id'].map(position_map).fillna('Unknown')
            print("  ✓ Added position from position_id mapping")
            print(f"  Position distribution:")
            print(df['position'].value_counts().to_string())
        else:
            # Fallback: use crew_rank if available
            if 'crew_rank' in df.columns:
                df['position'] = df['crew_rank']
                print("  ✓ Added position from crew_rank")
            else:
                df['position'] = 'Unknown'
                print("  ⚠ Added position as 'Unknown' (no position_id or crew_rank)")
        
        # Save
        df.to_csv(csv_path, index=False)
        print(f"  ✓ Saved {len(df)} rows")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def fix_baggage():
    """Add status column to baggage.csv"""
    print("\n" + "=" * 60)
    print("Fixing baggage.csv")
    print("=" * 60)
    
    csv_path = os.path.join(OUTPUT_DIR, 'baggage.csv')
    
    if not os.path.exists(csv_path):
        print(f"✗ File not found: {csv_path}")
        return False
    
    try:
        # Read CSV
        df = pd.read_csv(csv_path)
        print(f"  Loaded {len(df)} rows")
        
        # Check if status already exists
        if 'status' in df.columns:
            print("  ℹ status column already exists")
            print(f"  Sample values: {df['status'].head(3).tolist()}")
            return True
        
        # Add status column (copy from baggage_status)
        if 'baggage_status' in df.columns:
            df['status'] = df['baggage_status']
            print("  ✓ Added status from baggage_status")
            print(f"  Status distribution:")
            print(df['status'].value_counts().to_string())
        else:
            df['status'] = 'Unknown'
            print("  ⚠ Added status as 'Unknown' (no baggage_status column)")
        
        # Save
        df.to_csv(csv_path, index=False)
        print(f"  ✓ Saved {len(df)} rows")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def verify_fixes():
    """Verify all fixes were applied correctly"""
    print("\n" + "=" * 60)
    print("Verifying Fixes")
    print("=" * 60)
    
    checks = []
    
    # Check cargo_flight_assignments
    try:
        df = pd.read_csv(os.path.join(OUTPUT_DIR, 'cargo_flight_assignments.csv'))
        has_loading_priority = 'loading_priority' in df.columns
        checks.append(('cargo_flight_assignments.csv', 'loading_priority', has_loading_priority))
        print(f"  {'✓' if has_loading_priority else '✗'} cargo_flight_assignments.csv has loading_priority")
    except Exception as e:
        checks.append(('cargo_flight_assignments.csv', 'loading_priority', False))
        print(f"  ✗ cargo_flight_assignments.csv: {e}")
    
    # Check crew_roster_enriched
    try:
        df = pd.read_csv(os.path.join(OUTPUT_DIR, 'crew_roster_enriched.csv'))
        has_position = 'position' in df.columns
        checks.append(('crew_roster_enriched.csv', 'position', has_position))
        print(f"  {'✓' if has_position else '✗'} crew_roster_enriched.csv has position")
    except Exception as e:
        checks.append(('crew_roster_enriched.csv', 'position', False))
        print(f"  ✗ crew_roster_enriched.csv: {e}")
    
    # Check baggage
    try:
        df = pd.read_csv(os.path.join(OUTPUT_DIR, 'baggage.csv'))
        has_status = 'status' in df.columns
        checks.append(('baggage.csv', 'status', has_status))
        print(f"  {'✓' if has_status else '✗'} baggage.csv has status")
    except Exception as e:
        checks.append(('baggage.csv', 'status', False))
        print(f"  ✗ baggage.csv: {e}")
    
    all_passed = all(check[2] for check in checks)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All fixes verified successfully!")
    else:
        print("⚠️  Some fixes failed - review errors above")
    print("=" * 60)
    
    return all_passed


def main():
    """Main execution"""
    print("=" * 60)
    print("CSV Data Fix Script")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    
    # Run fixes
    results = []
    results.append(('cargo_flight_assignments', fix_cargo_flight_assignments()))
    results.append(('crew_roster', fix_crew_roster()))
    results.append(('baggage', fix_baggage()))
    
    # Verify
    verified = verify_fixes()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    print(f"\nVerification: {'✅ PASSED' if verified else '❌ FAILED'}")
    
    if verified:
        print("\n✅ All CSV files fixed successfully!")
        print("\nNext steps:")
        print("  1. Update upload scripts: python3 database/fix_upload_scripts.py")
        print("  2. Re-upload data: python3 database/async_import_dynamodb.py")
        print("  3. Create GSIs: python3 scripts/create_gsis.py")
        print("  4. Validate: python3 scripts/validate_dynamodb_data.py")
        return 0
    else:
        print("\n❌ Some fixes failed - review errors above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
