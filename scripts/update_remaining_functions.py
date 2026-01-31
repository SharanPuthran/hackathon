#!/usr/bin/env python3
"""
Script to update process_table_gsis, create_all_gsis_async, and add --max-attempts argument.
"""

import re
import sys

def update_file(filename):
    """Update a single file with remaining retry logic changes."""
    print(f"\nProcessing {filename}...")
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # 1. Update process_table_gsis function signature and body
    old_process_sig = r'async def process_table_gsis\(table_name: str, gsis: List\[Dict\], wait: bool = True, validate: bool = False\) -> Tuple\[int, int\]:'
    new_process_sig = 'async def process_table_gsis(table_name: str, gsis: List[Dict], wait: bool = True, validate: bool = False, retry_config: Optional[RetryConfig] = None) -> Tuple[int, int]:'
    
    if re.search(old_process_sig, content):
        content = re.sub(old_process_sig, new_process_sig, content)
        print("  ✓ Updated process_table_gsis signature")
    
    # Add retry_config default at start of process_table_gsis
    process_body_pattern = r'(async def process_table_gsis.*?\n.*?""")\n(\s+print\(f"\{table_name\}"\))'
    process_body_replacement = r'\1\n    if retry_config is None:\n        retry_config = DEFAULT_RETRY_CONFIG\n    \n\2'
    
    if re.search(process_body_pattern, content, re.DOTALL):
        content = re.sub(process_body_pattern, process_body_replacement, content, flags=re.DOTALL)
        print("  ✓ Added retry_config default to process_table_gsis")
    
    # Update process_table_gsis to pass retry_config to create_gsi_async
    old_tasks = r'tasks = \[create_gsi_async\(table_name, gsi_config, wait, validate\) for gsi_config in gsis\]'
    new_tasks = 'tasks = [create_gsi_async(table_name, gsi_config, wait, validate, retry_config) for gsi_config in gsis]'
    
    if old_tasks in content:
        content = content.replace(old_tasks, new_tasks)
        print("  ✓ Updated process_table_gsis to pass retry_config")
    
    # Add continue_on_failure logic to process_table_gsis
    old_for_loop = r'    for result in results:\n        if isinstance\(result, Exception\):\n            print\(f"  ✗ Exception: \{result\}"\)\n            failed_count \+= 1\n        else:\n            success, message = result\n            if success:\n                created_count \+= 1\n            else:\n                failed_count \+= 1'
    
    new_for_loop = '''    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"  ✗ Exception: {result}")
            failed_count += 1
            
            # Log that we're continuing with remaining GSIs
            if retry_config.continue_on_failure and i < len(gsis) - 1:
                print(f"  ℹ Continuing with remaining GSIs...")
        else:
            success, message = result
            if success:
                created_count += 1
            else:
                failed_count += 1
                
                # Log that we're continuing with remaining GSIs
                if retry_config.continue_on_failure and i < len(gsis) - 1:
                    print(f"  ℹ Continuing with remaining GSIs...")'''
    
    if re.search(old_for_loop, content):
        content = re.sub(old_for_loop, new_for_loop, content)
        print("  ✓ Added continue_on_failure logic to process_table_gsis")
    
    # 2. Update create_all_gsis_async function signature
    old_create_all_sig = r'async def create_all_gsis_async\(tables_to_process: Dict\[str, List\[Dict\]\], wait: bool = True, validate: bool = False\) -> Tuple\[int, int\]:'
    new_create_all_sig = 'async def create_all_gsis_async(tables_to_process: Dict[str, List[Dict]], wait: bool = True, validate: bool = False, retry_config: Optional[RetryConfig] = None) -> Tuple[int, int]:'
    
    if re.search(old_create_all_sig, content):
        content = re.sub(old_create_all_sig, new_create_all_sig, content)
        print("  ✓ Updated create_all_gsis_async signature")
    
    # Add retry_config default at start of create_all_gsis_async
    create_all_body_pattern = r'(async def create_all_gsis_async.*?\n.*?""")\n(\s+# Process all tables)'
    create_all_body_replacement = r'\1\n    if retry_config is None:\n        retry_config = DEFAULT_RETRY_CONFIG\n    \n\2'
    
    if re.search(create_all_body_pattern, content, re.DOTALL):
        content = re.sub(create_all_body_pattern, create_all_body_replacement, content, flags=re.DOTALL)
        print("  ✓ Added retry_config default to create_all_gsis_async")
    
    # Update create_all_gsis_async to pass retry_config to process_table_gsis
    old_all_tasks = r'process_table_gsis\(table_name, gsis, wait, validate\)'
    new_all_tasks = 'process_table_gsis(table_name, gsis, wait, validate, retry_config)'
    
    if old_all_tasks in content:
        content = content.replace(old_all_tasks, new_all_tasks)
        print("  ✓ Updated create_all_gsis_async to pass retry_config")
    
    # 3. Add --max-attempts argument if not present
    if '--max-attempts' not in content:
        old_args = r"    parser\.add_argument\(\n        '--validate',\n        action='store_true',\n        help='Validate GSI performance with sample queries'\n    \)\n\n    args = parser\.parse_args\(\)"
        
        new_args = """    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate GSI performance with sample queries'
    )

    parser.add_argument(
        '--max-attempts',
        type=int,
        default=5,
        help='Maximum number of retry attempts (default: 5)'
    )

    args = parser.parse_args()"""
        
        if re.search(old_args, content):
            content = re.sub(old_args, new_args, content)
            print("  ✓ Added --max-attempts argument")
    
    # 4. Update main function to create retry_config and pass it
    # Find the section where we create GSIs
    old_main_create = r'    print\(f"Creating \{total_gsis\}.*?for \{len\(tables_to_process\)\} tables \(async\)\.\.\."\)\n    print\(\)\n\n    start_time = datetime\.now\(\)\n\n    # Run async GSI creation\n    created_count, failed_count = asyncio\.run\(create_all_gsis_async\(\n        tables_to_process,\n        wait=not args\.no_wait,\n        validate=args\.validate\n    \)\)'
    
    new_main_create = '''    print(f"Creating {total_gsis} Priority GSIs for {len(tables_to_process)} tables (async)...")
    print(f"Retry configuration: max {args.max_attempts} attempts with exponential backoff")
    print()

    start_time = datetime.now()

    # Create retry configuration
    retry_config = RetryConfig(
        max_attempts=args.max_attempts,
        backoff_delays=(30, 60, 120, 240, 480),
        continue_on_failure=True
    )

    # Run async GSI creation
    created_count, failed_count = asyncio.run(create_all_gsis_async(
        tables_to_process,
        wait=not args.no_wait,
        validate=args.validate,
        retry_config=retry_config
    ))'''
    
    # This pattern is complex, so let's do a simpler replacement
    if 'retry_config = RetryConfig(' not in content:
        # Find the line with "Run async GSI creation"
        pattern = r'(\s+# Run async GSI creation\n\s+created_count, failed_count = asyncio\.run\(create_all_gsis_async\(\n\s+tables_to_process,\n\s+wait=not args\.no_wait,\n\s+validate=args\.validate)\n(\s+\)\))'
        
        replacement = r'\1,\n        retry_config=RetryConfig(\n            max_attempts=args.max_attempts,\n            backoff_delays=(30, 60, 120, 240, 480),\n            continue_on_failure=True\n        )\n\2'
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            print("  ✓ Updated main function to create and pass retry_config")
        
        # Also add the retry config message
        pattern2 = r'(print\(f"Creating \{total_gsis\}.*?tables \(async\)\.\.\."\)\n)(\s+print\(\))'
        replacement2 = r'\1    print(f"Retry configuration: max {args.max_attempts} attempts with exponential backoff")\n\2'
        
        if re.search(pattern2, content):
            content = re.sub(pattern2, replacement2, content)
            print("  ✓ Added retry configuration message to output")
    
    # Write back
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"  ✓ Completed {filename}")

def main():
    files = [
        'scripts/create_priority1_gsis.py',
        'scripts/create_priority2_gsis.py',
        'scripts/create_priority3_gsis.py'
    ]
    
    for filename in files:
        try:
            update_file(filename)
        except Exception as e:
            print(f"  ✗ Error updating {filename}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n✓ All files updated!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
