#!/usr/bin/env python3
"""
Enhanced GSI creation with comprehensive error-specific retry strategies.

This module provides an improved create_gsi_async function that implements
all error-specific retry strategies as specified in Task 1.15:

1. ResourceInUseException: Wait for table availability, retry immediately (5s delay)
2. LimitExceededException: Wait 5 minutes, retry
3. ValidationException (attribute conflicts): Merge attribute definitions, retry immediately
4. ThrottlingException: Exponential backoff, retry
5. InternalServerError: Exponential backoff, retry

State file support (Task 1.18):
- Tracks GSI creation progress in .gsi_creation_state.json
- Supports resume from last successful GSI
- Cleans up state file on successful completion
"""

import boto3
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from gsi_retry_utils import (
    RetryConfig,
    ErrorSpecificRetryHandler,
    extract_error_type,
    is_validation_attribute_conflict,
    get_error_description,
    log_retry_attempt,
    generate_failure_report,
    validate_gsi_query,
    log_validation_results
)
from gsi_state_manager import GSIStateManager

# Initialize DynamoDB client
dynamodb_client = boto3.client('dynamodb')


def get_existing_gsis(table_name: str) -> Dict[str, str]:
    """
    Get existing GSIs for a table.
    
    Args:
        table_name: Name of the table
    
    Returns:
        Dictionary mapping GSI name to status
    """
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        gsis = response['Table'].get('GlobalSecondaryIndexes', [])
        return {gsi['IndexName']: gsi['IndexStatus'] for gsi in gsis}
    except Exception as e:
        print(f"Error getting existing GSIs: {e}")
        return {}


def get_attribute_definitions(table_name: str) -> List[Dict]:
    """
    Get existing attribute definitions for a table.
    
    Args:
        table_name: Name of the table
    
    Returns:
        List of attribute definition dictionaries
    """
    try:
        response = dynamodb_client.describe_table(TableName=table_name)
        return response['Table'].get('AttributeDefinitions', [])
    except Exception as e:
        print(f"Error getting attribute definitions: {e}")
        return []


def merge_attribute_definitions(existing_attrs: List[Dict], new_attrs: List[Dict]) -> List[Dict]:
    """
    Merge new attribute definitions with existing ones, avoiding duplicates.
    
    This is used for ValidationException handling when attribute conflicts occur.
    
    Args:
        existing_attrs: Existing attribute definitions
        new_attrs: New attribute definitions to add
    
    Returns:
        Merged list of attribute definitions
    """
    existing_attr_names = {attr['AttributeName'] for attr in existing_attrs}
    merged_attrs = existing_attrs.copy()
    
    for attr in new_attrs:
        if attr['AttributeName'] not in existing_attr_names:
            merged_attrs.append(attr)
            print(f"    ℹ Adding new attribute definition: {attr['AttributeName']} ({attr['AttributeType']})")
        else:
            # Verify type matches
            existing_attr = next(a for a in existing_attrs if a['AttributeName'] == attr['AttributeName'])
            if existing_attr['AttributeType'] != attr['AttributeType']:
                print(f"    ⚠ Warning: Attribute {attr['AttributeName']} type mismatch: "
                      f"existing={existing_attr['AttributeType']}, new={attr['AttributeType']}")
    
    return merged_attrs


async def create_gsi_with_error_specific_retry(
    table_name: str,
    gsi_config: Dict,
    wait: bool = True,
    validate: bool = False,
    retry_config: Optional[RetryConfig] = None,
    state_manager: Optional[GSIStateManager] = None
) -> Tuple[bool, str, dict]:
    """
    Create a Global Secondary Index with comprehensive error-specific retry strategies.
    
    This function implements all error-specific retry strategies as specified in Task 1.15:
    
    1. ResourceInUseException: Wait for table availability, retry with 5s delay
    2. LimitExceededException: Wait 5 minutes, retry
    3. ValidationException (attribute conflicts): Merge attribute definitions, retry immediately
    4. ThrottlingException: Exponential backoff, retry
    5. InternalServerError: Exponential backoff, retry
    
    State management (Task 1.18):
    - Updates state file after each status change
    - Tracks retry count and errors
    - Supports resume capability
    
    Args:
        table_name: Name of the table
        gsi_config: GSI configuration dictionary with keys:
            - IndexName: Name of the GSI
            - KeySchema: List of key schema elements
            - Projection: Projection configuration
            - AttributeDefinitions: List of attribute definitions
            - Description: (optional) Description of the GSI
        wait: Whether to wait for GSI to become ACTIVE
        validate: Whether to validate GSI performance after creation
        retry_config: Retry configuration (uses default if None)
        state_manager: State manager for tracking progress (optional)
    
    Returns:
        Tuple of (success: bool, message: str, metadata: dict)
        metadata includes: attempts, retry_history, error_type (if failed)
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    index_name = gsi_config['IndexName']
    description = gsi_config.get('Description', '')
    
    print(f"  Creating {index_name}...")
    if description:
        print(f"    Use case: {description}")
    
    # Update state to in_progress
    if state_manager:
        state_manager.update_gsi_status(table_name, index_name, "in_progress")
    
    # Initialize error handler
    error_handler = ErrorSpecificRetryHandler(retry_config)
    
    for attempt in range(retry_config.max_attempts):
        try:
            # Check if GSI already exists
            existing_gsis = get_existing_gsis(table_name)
            if index_name in existing_gsis:
                status = existing_gsis[index_name]
                if status == 'ACTIVE':
                    print(f"    ✓ Already exists and is ACTIVE")
                    
                    # Update state to active
                    if state_manager:
                        state_manager.update_gsi_status(table_name, index_name, "active", retry_count=attempt + 1)
                    
                    metadata = {
                        'attempts': 1,
                        'retry_history': [],
                        'status': 'already_exists'
                    }
                    return (True, "Already exists and is ACTIVE", metadata)
                else:
                    print(f"    ⏳ Already exists with status: {status}")
                    metadata = {
                        'attempts': 1,
                        'retry_history': [],
                        'status': status
                    }
                    return (True, f"Already exists with status: {status}", metadata)
            
            # Get existing attribute definitions and merge with new ones
            existing_attrs = get_attribute_definitions(table_name)
            merged_attrs = merge_attribute_definitions(existing_attrs, gsi_config['AttributeDefinitions'])
            
            # Create GSI
            dynamodb_client.update_table(
                TableName=table_name,
                AttributeDefinitions=merged_attrs,
                GlobalSecondaryIndexUpdates=[{
                    'Create': {
                        'IndexName': gsi_config['IndexName'],
                        'KeySchema': gsi_config['KeySchema'],
                        'Projection': gsi_config['Projection']
                    }
                }]
            )
            
            print(f"    ✓ GSI creation initiated")
            
            # Wait for GSI to become active if requested
            if wait:
                print(f"    ⏳ Waiting for GSI to become ACTIVE...")
                if await wait_for_gsi_active(table_name, index_name):
                    print(f"    ✓ GSI is now ACTIVE")
                    
                    # Validate performance if requested
                    if validate:
                        print(f"    ⏳ Validating GSI performance...")
                        is_functional, status, validation_details = validate_gsi_query(
                            dynamodb_client,
                            table_name,
                            index_name,
                            gsi_config
                        )
                        
                        # Log validation results
                        log_validation_results(
                            index_name,
                            table_name,
                            is_functional,
                            status,
                            validation_details
                        )
                        
                        # Update state to active
                        if state_manager:
                            state_manager.update_gsi_status(table_name, index_name, "active", retry_count=attempt + 1)
                        
                        # Update metadata with validation results
                        metadata = {
                            'attempts': attempt + 1,
                            'retry_history': error_handler.get_retry_history(),
                            'status': 'active',
                            'validation': {
                                'is_functional': is_functional,
                                'status': status,
                                'details': validation_details
                            }
                        }
                        
                        if status == "non-functional":
                            print(f"    ⚠ GSI is ACTIVE but non-functional")
                            return (True, "ACTIVE but non-functional", metadata)
                        elif status == "not-used":
                            print(f"    ⚠ GSI is ACTIVE but not being used by queries")
                            return (True, "ACTIVE but not used", metadata)
                        elif status == "validation-error":
                            print(f"    ⚠ GSI is ACTIVE but validation failed")
                            return (True, "ACTIVE but validation failed", metadata)
                        else:
                            print(f"    ✓ GSI validation passed")
                            return (True, "Created, ACTIVE, and functional", metadata)
                    else:
                        # Update state to active
                        if state_manager:
                            state_manager.update_gsi_status(table_name, index_name, "active", retry_count=attempt + 1)
                        
                        metadata = {
                            'attempts': attempt + 1,
                            'retry_history': error_handler.get_retry_history(),
                            'status': 'active'
                        }
                        return (True, "Created and ACTIVE", metadata)
                else:
                    error_msg = "GSI failed to become ACTIVE within timeout"
                    print(f"    ✗ {error_msg}")
                    
                    # Record timeout as error
                    error_handler.retry_history.append({
                        'attempt': attempt + 1,
                        'timestamp': datetime.now().isoformat(),
                        'error': error_msg,
                        'error_type': 'ActivationTimeout'
                    })
                    
                    if attempt < retry_config.max_attempts - 1:
                        delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
                        
                        # Update state with retry count
                        if state_manager:
                            state_manager.update_gsi_status(
                                table_name, 
                                index_name, 
                                "in_progress", 
                                retry_count=attempt + 1,
                                error=error_msg
                            )
                        
                        print(f"    ⏳ Retrying in {delay}s (attempt {attempt + 2}/{retry_config.max_attempts})...")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # Update state to failed
                        if state_manager:
                            state_manager.update_gsi_status(
                                table_name, 
                                index_name, 
                                "failed", 
                                retry_count=retry_config.max_attempts,
                                error=error_msg
                            )
                        
                        metadata = {
                            'attempts': retry_config.max_attempts,
                            'retry_history': error_handler.get_retry_history(),
                            'error_type': 'ActivationTimeout'
                        }
                        return (False, error_msg, metadata)
            else:
                print(f"    ℹ GSI created, not waiting for backfill")
                metadata = {
                    'attempts': attempt + 1,
                    'retry_history': error_handler.get_retry_history(),
                    'status': 'creating'
                }
                return (True, "Created, not waiting", metadata)
        
        except dynamodb_client.exceptions.ResourceInUseException as e:
            # Error-specific strategy: Wait for table availability, retry with minimal delay
            error_msg = f"Table {table_name} is being updated"
            error_type = 'ResourceInUseException'
            
            print(f"    ⚠ {error_type}: {error_msg}")
            print(f"    ℹ Strategy: Waiting for table availability, retrying with 5s delay")
            
            error_handler.retry_history.append({
                'attempt': attempt + 1,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'error_type': error_type,
                'strategy': 'Wait for table availability, retry immediately'
            })
            
            if attempt < retry_config.max_attempts - 1:
                delay = 5  # 5 seconds to let table become available
                log_retry_attempt(index_name, table_name, attempt + 1, retry_config.max_attempts, 
                                error_msg, len(error_handler.retry_history), delay)
                
                # Update state with retry count
                if state_manager:
                    state_manager.update_gsi_status(
                        table_name, 
                        index_name, 
                        "in_progress", 
                        retry_count=attempt + 1,
                        error=error_msg
                    )
                
                print(f"    ⏳ Retrying in {delay}s (attempt {attempt + 2}/{retry_config.max_attempts})...")
                await asyncio.sleep(delay)
                continue
            else:
                print(f"    ✗ Failed after {retry_config.max_attempts} attempts")
                failure_report = generate_failure_report(index_name, table_name, error_handler.retry_history)
                
                # Update state to failed
                if state_manager:
                    state_manager.update_gsi_status(
                        table_name, 
                        index_name, 
                        "failed", 
                        retry_count=retry_config.max_attempts,
                        error=error_msg
                    )
                
                metadata = {
                    'attempts': retry_config.max_attempts,
                    'retry_history': error_handler.get_retry_history(),
                    'error_type': error_type,
                    'failure_report': failure_report
                }
                return (False, error_msg, metadata)
        
        except Exception as e:
            error_msg = str(e)
            error_type = extract_error_type(error_msg) or type(e).__name__
            
            # Determine error-specific strategy
            if 'LimitExceededException' in error_msg or error_type == 'LimitExceededException':
                # Error-specific strategy: Wait 5 minutes for limit reset
                error_type = 'LimitExceededException'
                delay = 300  # 5 minutes
                strategy = 'Wait 5 minutes for limit reset'
                print(f"    ⚠ {error_type}: DynamoDB service limit exceeded")
                print(f"    ℹ Strategy: {strategy}")
                
            elif is_validation_attribute_conflict(error_msg):
                # Error-specific strategy: Merge attribute definitions, retry immediately
                error_type = 'ValidationException'
                delay = 0  # Retry immediately (attribute merge already done)
                strategy = 'Merge attribute definitions, retry immediately'
                print(f"    ⚠ {error_type}: Attribute definition conflict")
                print(f"    ℹ Strategy: {strategy}")
                print(f"    ℹ Attribute definitions have been merged, retrying...")
                
            elif 'ThrottlingException' in error_msg or error_type == 'ThrottlingException':
                # Error-specific strategy: Exponential backoff
                error_type = 'ThrottlingException'
                delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
                strategy = 'Exponential backoff'
                print(f"    ⚠ {error_type}: Request throttled by DynamoDB")
                print(f"    ℹ Strategy: {strategy}")
                
            elif 'InternalServerError' in error_msg or error_type == 'InternalServerError':
                # Error-specific strategy: Exponential backoff
                error_type = 'InternalServerError'
                delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
                strategy = 'Exponential backoff'
                print(f"    ⚠ {error_type}: AWS internal error")
                print(f"    ℹ Strategy: {strategy}")
                
            elif 'already exists' in error_msg.lower():
                # GSI already exists
                print(f"    ℹ GSI {index_name} already exists")
                metadata = {
                    'attempts': attempt + 1,
                    'retry_history': error_handler.get_retry_history(),
                    'status': 'already_exists'
                }
                return (True, "Already exists", metadata)
                
            else:
                # Unknown error - use default exponential backoff
                delay = retry_config.backoff_delays[min(attempt, len(retry_config.backoff_delays) - 1)]
                strategy = 'Default exponential backoff'
                print(f"    ⚠ {error_type}: {error_msg}")
                print(f"    ℹ Strategy: {strategy}")
            
            # Record retry attempt
            error_handler.retry_history.append({
                'attempt': attempt + 1,
                'timestamp': datetime.now().isoformat(),
                'error': error_msg,
                'error_type': error_type,
                'strategy': strategy,
                'next_retry_delay': delay
            })
            
            if attempt < retry_config.max_attempts - 1:
                log_retry_attempt(index_name, table_name, attempt + 1, retry_config.max_attempts,
                                error_msg, len(error_handler.retry_history), delay)
                
                # Update state with retry count
                if state_manager:
                    state_manager.update_gsi_status(
                        table_name, 
                        index_name, 
                        "in_progress", 
                        retry_count=attempt + 1,
                        error=error_msg
                    )
                
                print(f"    ⏳ Retrying in {delay}s (attempt {attempt + 2}/{retry_config.max_attempts})...")
                await asyncio.sleep(delay)
                continue
            else:
                print(f"    ✗ Failed after {retry_config.max_attempts} attempts")
                failure_report = generate_failure_report(index_name, table_name, error_handler.retry_history)
                
                # Update state to failed
                if state_manager:
                    state_manager.update_gsi_status(
                        table_name, 
                        index_name, 
                        "failed", 
                        retry_count=retry_config.max_attempts,
                        error=error_msg
                    )
                
                metadata = {
                    'attempts': retry_config.max_attempts,
                    'retry_history': error_handler.get_retry_history(),
                    'error_type': error_type,
                    'failure_report': failure_report
                }
                return (False, error_msg, metadata)
    
    # Should not reach here, but just in case
    metadata = {
        'attempts': retry_config.max_attempts,
        'retry_history': error_handler.get_retry_history(),
        'error_type': 'MaxAttemptsExhausted'
    }
    return (False, f"Failed after {retry_config.max_attempts} attempts", metadata)


async def wait_for_gsi_active(table_name: str, index_name: str, timeout: int = 900) -> bool:
    """
    Wait for a GSI to become ACTIVE.
    
    Args:
        table_name: Name of the table
        index_name: Name of the GSI
        timeout: Maximum wait time in seconds (default: 15 minutes)
    
    Returns:
        True if GSI is ACTIVE, False if timeout or error
    """
    start_time = asyncio.get_event_loop().time()
    poll_interval = 10  # Poll every 10 seconds
    
    while True:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            gsis = response['Table'].get('GlobalSecondaryIndexes', [])
            
            for gsi in gsis:
                if gsi['IndexName'] == index_name:
                    status = gsi['IndexStatus']
                    if status == 'ACTIVE':
                        return True
                    elif status in ['CREATING', 'UPDATING']:
                        # Still in progress
                        elapsed = asyncio.get_event_loop().time() - start_time
                        if elapsed >= timeout:
                            print(f"    ✗ Timeout waiting for GSI to become ACTIVE (elapsed: {elapsed:.0f}s)")
                            return False
                        await asyncio.sleep(poll_interval)
                        break
                    else:
                        # Failed or other status
                        print(f"    ✗ GSI has unexpected status: {status}")
                        return False
            else:
                # GSI not found
                print(f"    ✗ GSI {index_name} not found in table")
                return False
                
        except Exception as e:
            print(f"    ✗ Error checking GSI status: {e}")
            return False
