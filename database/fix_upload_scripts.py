#!/usr/bin/env python3
"""
Fix Upload Scripts

This script fixes key schema mismatches in:
1. cleanup_and_upload_dynamodb.py
2. async_import_dynamodb.py

Usage:
    python3 database/fix_upload_scripts.py
"""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def fix_cleanup_and_upload():
    """Fix cleanup_and_upload_dynamodb.py"""
    print("\n" + "=" * 60)
    print("Fixing cleanup_and_upload_dynamodb.py")
    print("=" * 60)
    
    file_path = os.path.join(SCRIPT_DIR, 'cleanup_and_upload_dynamodb.py')
    
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Fix 1: MaintenanceWorkOrders key schema
        if "'work_order_id'" in content:
            content = content.replace(
                "{'AttributeName': 'work_order_id', 'KeyType': 'HASH'}",
                "{'AttributeName': 'workorder_id', 'KeyType': 'HASH'}"
            )
            content = content.replace(
                "{'AttributeName': 'work_order_id', 'AttributeType': 'S'}",
                "{'AttributeName': 'workorder_id', 'AttributeType': 'S'}"
            )
            changes.append("Fixed MaintenanceWorkOrders key: work_order_id → workorder_id")
        
        # Fix 2: MaintenanceStaff file path
        if "'file': os.path.join(OUTPUT_DIR, 'maintenance_roster.csv')" in content:
            content = content.replace(
                "'file': os.path.join(OUTPUT_DIR, 'maintenance_roster.csv')",
                "'file': os.path.join(OUTPUT_DIR, 'maintenance_staff.csv')"
            )
            changes.append("Fixed MaintenanceStaff file: maintenance_roster.csv → maintenance_staff.csv")
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"  ✓ Applied {len(changes)} fixes:")
            for change in changes:
                print(f"    - {change}")
            return True
        else:
            print("  ℹ No changes needed (already fixed or different structure)")
            return True
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def fix_async_import():
    """Fix async_import_dynamodb.py"""
    print("\n" + "=" * 60)
    print("Fixing async_import_dynamodb.py")
    print("=" * 60)
    
    file_path = os.path.join(SCRIPT_DIR, 'async_import_dynamodb.py')
    
    if not os.path.exists(file_path):
        print(f"✗ File not found: {file_path}")
        return False
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_content = content
        changes = []
        
        # Fix 1: MaintenanceWorkOrders key schema
        if "'workorder_id'" not in content and "'work_order_id'" in content:
            content = content.replace(
                "{'AttributeName': 'work_order_id', 'KeyType': 'HASH'}",
                "{'AttributeName': 'workorder_id', 'KeyType': 'HASH'}"
            )
            content = content.replace(
                "{'AttributeName': 'work_order_id', 'AttributeType': 'S'}",
                "{'AttributeName': 'workorder_id', 'AttributeType': 'S'}"
            )
            content = content.replace(
                "'key_field': 'work_order_id'",
                "'key_field': 'workorder_id'"
            )
            changes.append("Fixed MaintenanceWorkOrders key: work_order_id → workorder_id")
        
        # Fix 2: MaintenanceStaff file path and key
        if "'file': 'maintenance_roster.csv'" in content:
            content = content.replace(
                "'file': 'maintenance_roster.csv'",
                "'file': 'maintenance_staff.csv'"
            )
            changes.append("Fixed MaintenanceStaff file: maintenance_roster.csv → maintenance_staff.csv")
        
        if content != original_content:
            with open(file_path, 'w') as f:
                f.write(content)
            
            print(f"  ✓ Applied {len(changes)} fixes:")
            for change in changes:
                print(f"    - {change}")
            return True
        else:
            print("  ℹ No changes needed (already fixed or different structure)")
            return True
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def verify_fixes():
    """Verify fixes were applied"""
    print("\n" + "=" * 60)
    print("Verifying Fixes")
    print("=" * 60)
    
    checks = []
    
    # Check cleanup_and_upload_dynamodb.py
    try:
        with open(os.path.join(SCRIPT_DIR, 'cleanup_and_upload_dynamodb.py'), 'r') as f:
            content = f.read()
        
        has_correct_key = "'workorder_id'" in content or "'work_order_id'" not in content
        checks.append(('cleanup_and_upload_dynamodb.py', has_correct_key))
        print(f"  {'✓' if has_correct_key else '✗'} cleanup_and_upload_dynamodb.py has correct key schema")
    except Exception as e:
        checks.append(('cleanup_and_upload_dynamodb.py', False))
        print(f"  ✗ cleanup_and_upload_dynamodb.py: {e}")
    
    # Check async_import_dynamodb.py
    try:
        with open(os.path.join(SCRIPT_DIR, 'async_import_dynamodb.py'), 'r') as f:
            content = f.read()
        
        has_correct_key = "'workorder_id'" in content or "'work_order_id'" not in content
        checks.append(('async_import_dynamodb.py', has_correct_key))
        print(f"  {'✓' if has_correct_key else '✗'} async_import_dynamodb.py has correct key schema")
    except Exception as e:
        checks.append(('async_import_dynamodb.py', False))
        print(f"  ✗ async_import_dynamodb.py: {e}")
    
    all_passed = all(check[1] for check in checks)
    
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
    print("Upload Scripts Fix Script")
    print("=" * 60)
    
    # Run fixes
    results = []
    results.append(('cleanup_and_upload_dynamodb.py', fix_cleanup_and_upload()))
    results.append(('async_import_dynamodb.py', fix_async_import()))
    
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
        print("\n✅ All upload scripts fixed successfully!")
        print("\nNext step:")
        print("  Re-upload data: python3 database/async_import_dynamodb.py")
        return 0
    else:
        print("\n❌ Some fixes failed - review errors above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
