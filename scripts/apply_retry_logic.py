#!/usr/bin/env python3
"""
Helper script to apply retry logic updates to all GSI creation scripts.
This script updates create_priority1_gsis.py, create_priority2_gsis.py, and create_priority3_gsis.py
"""

import re

# Files to update
files_to_update = [
    'scripts/create_priority1_gsis.py',
    'scripts/create_priority2_gsis.py',
    'scripts/create_priority3_gsis.py'
]

# Import statement to add
import_addition = """from gsi_retry_utils import RetryConfig, log_retry_attempt, generate_failure_report

# Initialize DynamoDB client
dynamodb_client = boto3.client('dynamodb')

# Default retry configuration
DEFAULT_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    backoff_delays=(30, 60, 120, 240, 480),
    continue_on_failure=True
)"""

# Function signature updates
def update_function_signatures(content):
    """Update function signatures to include retry_config parameter."""
    
    # Update create_gsi_async signature
    content = re.sub(
        r'async def create_gsi_async\(table_name: str, gsi_config: Dict, wait: bool = True, validate: bool = False\) -> Tuple\[bool, str\]:',
        'async def create_gsi_async(table_name: str, gsi_config: Dict, wait: bool = True, validate: bool = False, retry_config: Optional[RetryConfig] = None) -> Tuple[bool, str]:',
        content
    )
    
    # Update process_table_gsis signature
    content = re.sub(
        r'async def process_table_gsis\(table_name: str, gsis: List\[Dict\], wait: bool = True, validate: bool = False\) -> Tuple\[int, int\]:',
        'async def process_table_gsis(table_name: str, gsis: List[Dict], wait: bool = True, validate: bool = False, retry_config: Optional[RetryConfig] = None) -> Tuple[int, int]:',
        content
    )
    
    # Update create_all_gsis_async signature
    content = re.sub(
        r'async def create_all_gsis_async\(tables_to_process: Dict\[str, List\[Dict\]\], wait: bool = True, validate: bool = False\) -> Tuple\[int, int\]:',
        'async def create_all_gsis_async(tables_to_process: Dict[str, List[Dict]], wait: bool = True, validate: bool = False, retry_config: Optional[RetryConfig] = None) -> Tuple[int, int]:',
        content
    )
    
    return content

def main():
    print("Applying retry logic to GSI creation scripts...")
    
    for filepath in files_to_update:
        print(f"\nProcessing {filepath}...")
        
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Add imports
            content = content.replace(
                '# Initialize DynamoDB client\ndynamodb_client = boto3.client(\'dynamodb\')',
                import_addition
            )
            
            # Update function signatures
            content = update_function_signatures(content)
            
            # Add --max-attempts argument
            if '--max-attempts' not in content:
                content = content.replace(
                    "    parser.add_argument(\n        '--validate',\n        action='store_true',\n        help='Validate GSI performance with sample queries'\n    )\n\n    args = parser.parse_args()",
                    "    parser.add_argument(\n        '--validate',\n        action='store_true',\n        help='Validate GSI performance with sample queries'\n    )\n\n    parser.add_argument(\n        '--max-attempts',\n        type=int,\n        default=5,\n        help='Maximum number of retry attempts (default: 5)'\n    )\n\n    args = parser.parse_args()"
                )
            
            # Write back
            with open(filepath, 'w') as f:
                f.write(content)
            
            print(f"  ✓ Updated {filepath}")
            
        except Exception as e:
            print(f"  ✗ Error updating {filepath}: {e}")
    
    print("\n✓ Retry logic application complete!")
    print("\nNote: Manual review recommended for:")
    print("  - create_gsi_async function body (retry loop logic)")
    print("  - process_table_gsis function body (retry_config passing)")
    print("  - create_all_gsis_async function body (retry_config passing)")
    print("  - main function (retry_config creation)")

if __name__ == '__main__':
    main()
