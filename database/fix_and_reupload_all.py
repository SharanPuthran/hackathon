#!/usr/bin/env python3
"""
Master Script: Fix and Re-upload All DynamoDB Data

This script orchestrates the complete fix and re-upload process:
1. Fix CSV data files
2. Fix upload scripts
3. Re-upload data to DynamoDB
4. Create GSIs
5. Validate everything

Usage:
    python3 database/fix_and_reupload_all.py [--skip-upload] [--skip-gsi] [--skip-validation]
"""

import subprocess
import sys
import os
import argparse
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

def run_command(cmd, cwd=None, description=None):
    """Run a command and return success status"""
    if description:
        print(f"\n{'=' * 60}")
        print(description)
        print('=' * 60)
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or SCRIPT_DIR,
            check=True,
            capture_output=False,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Command failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def phase_1_fix_csv_data():
    """Phase 1: Fix CSV data files"""
    print("\n" + "=" * 80)
    print("PHASE 1: FIX CSV DATA FILES")
    print("=" * 80)
    
    return run_command(
        ['python3', 'fix_csv_data.py'],
        cwd=SCRIPT_DIR,
        description="Fixing CSV data files (loading_priority, position, status)"
    )


def phase_2_fix_upload_scripts():
    """Phase 2: Fix upload scripts"""
    print("\n" + "=" * 80)
    print("PHASE 2: FIX UPLOAD SCRIPTS")
    print("=" * 80)
    
    return run_command(
        ['python3', 'fix_upload_scripts.py'],
        cwd=SCRIPT_DIR,
        description="Fixing upload scripts (key schema mismatches)"
    )


def phase_3_reupload_data():
    """Phase 3: Re-upload data to DynamoDB"""
    print("\n" + "=" * 80)
    print("PHASE 3: RE-UPLOAD DATA TO DYNAMODB")
    print("=" * 80)
    
    print("\n⚠️  WARNING: This will delete all existing tables and re-create them!")
    print("All data will be replaced with fresh uploads from CSV files.")
    print()
    
    response = input("Continue with re-upload? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Re-upload cancelled by user")
        return False
    
    return run_command(
        ['python3', 'async_import_dynamodb.py'],
        cwd=SCRIPT_DIR,
        description="Re-uploading all data to DynamoDB (async)"
    )


def phase_4_create_gsis():
    """Phase 4: Create GSIs"""
    print("\n" + "=" * 80)
    print("PHASE 4: CREATE GLOBAL SECONDARY INDEXES")
    print("=" * 80)
    
    scripts_dir = os.path.join(PROJECT_ROOT, 'scripts')
    
    success = run_command(
        ['python3', 'create_gsis.py'],
        cwd=scripts_dir,
        description="Creating all required GSIs"
    )
    
    if success:
        print("\n⏳ Waiting 10 seconds for GSIs to start activating...")
        time.sleep(10)
        
        print("\n" + "=" * 60)
        print("Checking GSI Status")
        print("=" * 60)
        
        run_command(
            ['python3', 'create_gsis.py', '--check-status'],
            cwd=scripts_dir
        )
    
    return success


def phase_5_validate():
    """Phase 5: Validate everything"""
    print("\n" + "=" * 80)
    print("PHASE 5: VALIDATE DATA AND GSIS")
    print("=" * 80)
    
    scripts_dir = os.path.join(PROJECT_ROOT, 'scripts')
    output_file = os.path.join(SCRIPT_DIR, 'validation_report.json')
    
    return run_command(
        ['python3', 'validate_dynamodb_data.py', '--output', output_file],
        cwd=scripts_dir,
        description="Running comprehensive validation"
    )


def print_summary(results):
    """Print execution summary"""
    print("\n" + "=" * 80)
    print("EXECUTION SUMMARY")
    print("=" * 80)
    
    for phase, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{phase}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL PHASES COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nYour DynamoDB database is now:")
        print("  ✓ Populated with corrected data")
        print("  ✓ Configured with all required GSIs")
        print("  ✓ Validated and ready for use")
        print("\nNext steps:")
        print("  1. Test agent queries")
        print("  2. Deploy agents to AgentCore")
        print("  3. Run end-to-end tests")
    else:
        print("⚠️  SOME PHASES FAILED")
        print("=" * 80)
        print("\nReview the errors above and:")
        print("  1. Fix any issues")
        print("  2. Re-run this script")
        print("  3. Or run individual phase scripts manually")
    
    return all_passed


def main():
    """Main execution"""
    parser = argparse.ArgumentParser(
        description='Fix and re-upload all DynamoDB data',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--skip-upload',
        action='store_true',
        help='Skip data re-upload (use if data is already correct)'
    )
    
    parser.add_argument(
        '--skip-gsi',
        action='store_true',
        help='Skip GSI creation (use if GSIs already exist)'
    )
    
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation phase'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("DYNAMODB FIX AND RE-UPLOAD - MASTER SCRIPT")
    print("=" * 80)
    print()
    print("This script will:")
    print("  1. Fix CSV data files (add missing columns)")
    print("  2. Fix upload scripts (correct key schemas)")
    if not args.skip_upload:
        print("  3. Re-upload all data to DynamoDB")
    if not args.skip_gsi:
        print("  4. Create all required GSIs")
    if not args.skip_validation:
        print("  5. Validate data and GSIs")
    print()
    
    results = {}
    
    # Phase 1: Fix CSV data
    results['Phase 1: Fix CSV Data'] = phase_1_fix_csv_data()
    if not results['Phase 1: Fix CSV Data']:
        print("\n❌ Phase 1 failed - stopping execution")
        return 1
    
    # Phase 2: Fix upload scripts
    results['Phase 2: Fix Upload Scripts'] = phase_2_fix_upload_scripts()
    if not results['Phase 2: Fix Upload Scripts']:
        print("\n❌ Phase 2 failed - stopping execution")
        return 1
    
    # Phase 3: Re-upload data
    if not args.skip_upload:
        results['Phase 3: Re-upload Data'] = phase_3_reupload_data()
        if not results['Phase 3: Re-upload Data']:
            print("\n❌ Phase 3 failed - stopping execution")
            return 1
    else:
        print("\n⏭️  Skipping Phase 3: Re-upload Data")
        results['Phase 3: Re-upload Data'] = True
    
    # Phase 4: Create GSIs
    if not args.skip_gsi:
        results['Phase 4: Create GSIs'] = phase_4_create_gsis()
        if not results['Phase 4: Create GSIs']:
            print("\n⚠️  Phase 4 failed - GSI creation had issues")
            print("You may need to:")
            print("  1. Wait for existing GSIs to finish creating")
            print("  2. Run: python3 scripts/create_gsis.py --check-status")
            print("  3. Re-run GSI creation if needed")
    else:
        print("\n⏭️  Skipping Phase 4: Create GSIs")
        results['Phase 4: Create GSIs'] = True
    
    # Phase 5: Validate
    if not args.skip_validation:
        results['Phase 5: Validate'] = phase_5_validate()
    else:
        print("\n⏭️  Skipping Phase 5: Validate")
        results['Phase 5: Validate'] = True
    
    # Print summary
    all_passed = print_summary(results)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
