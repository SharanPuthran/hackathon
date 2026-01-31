#!/usr/bin/env python3
"""
Script to copy retry logic from create_gsis.py to other GSI creation scripts.
"""

import re
import sys

def main():
    # Read the template from create_gsis.py
    with open('scripts/create_gsis.py', 'r') as f:
        template_content = f.read()

    # Extract the retry-enabled create_gsi_async function
    # Find from function definition to the end return statement
    match = re.search(
        r'(async def create_gsi_async\(table_name: str.*?'
        r'return \(False, f"Failed after \{retry_config\.max_attempts\} attempts"\))',
        template_content,
        re.DOTALL
    )

    if not match:
        print("✗ Failed to extract create_gsi_async function from template")
        return 1

    retry_create_gsi_async = match.group(1)
    print("✓ Extracted retry-enabled create_gsi_async function")
    print(f"  Length: {len(retry_create_gsi_async)} characters")

    # Files to update
    files = [
        'scripts/create_priority1_gsis.py',
        'scripts/create_priority2_gsis.py',
        'scripts/create_priority3_gsis.py'
    ]

    for filename in files:
        print(f"\nProcessing {filename}...")
        
        try:
            with open(filename, 'r') as f:
                content = f.read()
            
            # Find and replace the old create_gsi_async function
            # Match from async def to the next async def or end of file
            pattern = r'async def create_gsi_async\(table_name: str.*?(?=\n\nasync def process_table_gsis)'
            
            old_match = re.search(pattern, content, re.DOTALL)
            if old_match:
                old_func = old_match.group(0)
                content = content.replace(old_func, retry_create_gsi_async)
                print(f"  ✓ Replaced create_gsi_async function")
                
                with open(filename, 'w') as f:
                    f.write(content)
                
                print(f"  ✓ Updated {filename}")
            else:
                print(f"  ✗ Could not find create_gsi_async function to replace")
                
        except Exception as e:
            print(f"  ✗ Error processing {filename}: {e}")
            continue

    print("\n✓ All files processed!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
