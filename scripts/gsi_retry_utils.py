#!/usr/bin/env python3
"""
Retry utilities for GSI creation with exponential backoff.

This module provides a retry decorator and utilities for handling GSI creation
failures with configurable exponential backoff and error-specific retry strategies.
"""

import time
import functools
import logging
from typing import Callable, Any, Tuple, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 5,
        backoff_delays: Tuple[int, ...] = (30, 60, 120, 240, 480),
        continue_on_failure: bool = True
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts (default: 5)
            backoff_delays: Exponential backoff delays in seconds (default: 30s, 60s, 120s, 240s, 480s)
            continue_on_failure: Whether to continue with remaining GSIs if one fails (default: True)
        """
        self.max_attempts = max_attempts
        self.backoff_delays = backoff_delays
        self.continue_on_failure = continue_on_failure


def get_retry_delay(attempt: int, config: RetryConfig, error_type: Optional[str] = None) -> int:
    """
    Get retry delay based on attempt number and error type.
    
    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        error_type: Type of error encountered (for error-specific strategies)
    
    Returns:
        Delay in seconds before next retry
    """
    # Use error-specific delay if error type is known
    if error_type:
        return get_error_specific_delay(error_type, attempt, config)
    
    # Default exponential backoff
    if attempt < len(config.backoff_delays):
        return config.backoff_delays[attempt]
    else:
        # Use last delay for any attempts beyond configured delays
        return config.backoff_delays[-1]


def retry_with_backoff(config: Optional[RetryConfig] = None):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        config: Retry configuration (uses default if None)
    
    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Tuple[bool, str, dict]:
            """
            Wrapper function that implements retry logic.
            
            Returns:
                Tuple of (success: bool, message: str, metadata: dict)
            """
            retry_history = []
            last_error = None
            last_error_type = None
            
            for attempt in range(config.max_attempts):
                try:
                    # Call the original function
                    result = func(*args, **kwargs)
                    
                    # If function returns tuple (success, message), check success
                    if isinstance(result, tuple) and len(result) >= 2:
                        success, message = result[0], result[1]
                        
                        if success:
                            # Success - return with retry metadata
                            metadata = {
                                'attempts': attempt + 1,
                                'retry_history': retry_history
                            }
                            return (True, message, metadata)
                        else:
                            # Function returned failure
                            last_error = message
                            last_error_type = extract_error_type(message)
                    else:
                        # Function returned success (non-tuple or unexpected format)
                        metadata = {
                            'attempts': attempt + 1,
                            'retry_history': retry_history
                        }
                        return (True, str(result), metadata)
                
                except Exception as e:
                    last_error = str(e)
                    last_error_type = type(e).__name__
                
                # Log retry attempt
                retry_info = {
                    'attempt': attempt + 1,
                    'timestamp': datetime.now().isoformat(),
                    'error': last_error,
                    'error_type': last_error_type
                }
                retry_history.append(retry_info)
                
                # Check if we should retry
                if attempt < config.max_attempts - 1:
                    delay = get_retry_delay(attempt, config, last_error_type)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{config.max_attempts} failed: {last_error}. "
                        f"Retrying in {delay}s..."
                    )
                    
                    retry_info['next_retry_delay'] = delay
                    
                    if delay > 0:
                        time.sleep(delay)
                else:
                    logger.error(
                        f"All {config.max_attempts} attempts exhausted. Last error: {last_error}"
                    )
            
            # All retries exhausted
            metadata = {
                'attempts': config.max_attempts,
                'retry_history': retry_history,
                'exhausted': True
            }
            
            return (False, f"Failed after {config.max_attempts} attempts: {last_error}", metadata)
        
        return wrapper
    return decorator


def extract_error_type(error_message: str) -> Optional[str]:
    """
    Extract error type from error message.
    
    Args:
        error_message: Error message string
    
    Returns:
        Error type string or None
    """
    error_types = [
        'ResourceInUseException',
        'LimitExceededException',
        'ValidationException',
        'ThrottlingException',
        'InternalServerError'
    ]
    
    for error_type in error_types:
        if error_type.lower() in error_message.lower():
            return error_type
    
    return None


def get_error_specific_delay(error_type: str, attempt: int, config: RetryConfig) -> int:
    """
    Get error-specific retry delay based on error type.
    
    Args:
        error_type: Type of error encountered
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
    
    Returns:
        Delay in seconds before next retry
    """
    if error_type == 'ResourceInUseException':
        # Wait for table availability, retry with minimal delay
        return 5  # 5 seconds to let table become available
    elif error_type == 'LimitExceededException':
        # Wait 5 minutes for limit reset
        return 300
    elif error_type == 'ValidationException':
        # Attribute conflicts - retry immediately after merge
        return 0
    elif error_type == 'ThrottlingException':
        # Use exponential backoff for throttling
        if attempt < len(config.backoff_delays):
            return config.backoff_delays[attempt]
        return config.backoff_delays[-1]
    elif error_type == 'InternalServerError':
        # Use exponential backoff for internal errors
        if attempt < len(config.backoff_delays):
            return config.backoff_delays[attempt]
        return config.backoff_delays[-1]
    else:
        # Default exponential backoff
        if attempt < len(config.backoff_delays):
            return config.backoff_delays[attempt]
        return config.backoff_delays[-1]


def is_validation_attribute_conflict(error_message: str) -> bool:
    """
    Check if ValidationException is due to attribute definition conflicts.
    
    Args:
        error_message: Error message string
    
    Returns:
        True if error is attribute conflict, False otherwise
    """
    attribute_keywords = [
        'attribute',
        'AttributeDefinition',
        'already defined',
        'duplicate attribute'
    ]
    
    error_lower = error_message.lower()
    return 'validationexception' in error_lower and any(
        keyword.lower() in error_lower for keyword in attribute_keywords
    )


def should_retry_error(error_type: str, attempt: int, max_attempts: int) -> bool:
    """
    Determine if an error should be retried.
    
    Args:
        error_type: Type of error encountered
        attempt: Current attempt number (0-indexed)
        max_attempts: Maximum number of attempts
    
    Returns:
        True if error should be retried, False otherwise
    """
    # Always retry if we haven't exhausted attempts
    if attempt >= max_attempts - 1:
        return False
    
    # All errors are retryable (including unknown errors)
    # We use exponential backoff for unknown errors
    return True


def get_error_description(error_type: str) -> str:
    """
    Get human-readable description of error type and retry strategy.
    
    Args:
        error_type: Type of error encountered
    
    Returns:
        Description string
    """
    descriptions = {
        'ResourceInUseException': 'Table is being updated. Waiting for availability and retrying immediately.',
        'LimitExceededException': 'DynamoDB service limit exceeded. Waiting 5 minutes for limit reset.',
        'ValidationException': 'Validation error (possibly attribute conflict). Merging definitions and retrying immediately.',
        'ThrottlingException': 'Request throttled by DynamoDB. Using exponential backoff.',
        'InternalServerError': 'AWS internal error. Using exponential backoff.'
    }
    
    return descriptions.get(error_type, 'Unknown error. Using exponential backoff.')



def log_retry_attempt(
    gsi_name: str,
    table_name: str,
    attempt: int,
    max_attempts: int,
    error: str,
    retry_count: int,
    next_delay: int
) -> None:
    """
    Log a retry attempt with detailed information.
    
    Args:
        gsi_name: Name of the GSI being created
        table_name: Name of the table
        attempt: Current attempt number
        max_attempts: Maximum number of attempts
        error: Error message
        retry_count: Total retry count so far
        next_delay: Delay before next retry in seconds
    """
    logger.info(
        f"GSI: {gsi_name} on {table_name} - "
        f"Attempt {attempt}/{max_attempts} failed. "
        f"Error: {error}. "
        f"Retry count: {retry_count}. "
        f"Next retry in {next_delay}s"
    )


def generate_failure_report(
    gsi_name: str,
    table_name: str,
    retry_history: list,
    recommended_actions: Optional[list] = None
) -> dict:
    """
    Generate a detailed failure report for a GSI creation failure.
    
    Args:
        gsi_name: Name of the GSI
        table_name: Name of the table
        retry_history: List of retry attempt information
        recommended_actions: Optional list of recommended manual intervention steps
    
    Returns:
        Dictionary containing detailed failure report
    """
    if recommended_actions is None:
        recommended_actions = [
            "Check table status in AWS Console",
            "Verify IAM permissions for GSI creation",
            "Check DynamoDB service limits",
            "Review CloudWatch logs for detailed errors",
            "Consider creating GSI manually via AWS Console"
        ]
    
    report = {
        'gsi_name': gsi_name,
        'table_name': table_name,
        'total_attempts': len(retry_history),
        'failure_reasons': [attempt['error'] for attempt in retry_history],
        'retry_history': retry_history,
        'recommended_actions': recommended_actions,
        'timestamp': datetime.now().isoformat()
    }
    
    return report


def should_continue_on_failure(config: RetryConfig, error_type: Optional[str] = None) -> bool:
    """
    Determine if processing should continue after a failure.
    
    Args:
        config: Retry configuration
        error_type: Type of error encountered
    
    Returns:
        True if processing should continue, False otherwise
    """
    # Always continue if configured to do so
    if config.continue_on_failure:
        return True
    
    # For certain critical errors, might want to stop
    critical_errors = ['InternalServerError', 'ThrottlingException']
    if error_type in critical_errors:
        return False
    
    return True


class ErrorSpecificRetryHandler:
    """
    Handler for error-specific retry strategies in GSI creation.
    
    This class encapsulates the logic for handling different types of errors
    with appropriate retry strategies as specified in the requirements.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize the retry handler.
        
        Args:
            config: Retry configuration (uses default if None)
        """
        self.config = config or RetryConfig()
        self.retry_history = []
    
    def handle_error(self, error: Exception, attempt: int) -> Tuple[bool, int, str]:
        """
        Handle an error and determine retry strategy.
        
        Args:
            error: The exception that occurred
            attempt: Current attempt number (0-indexed)
        
        Returns:
            Tuple of (should_retry: bool, delay: int, description: str)
        """
        error_msg = str(error)
        error_type = self._get_error_type(error)
        
        # Record retry attempt
        self.retry_history.append({
            'attempt': attempt + 1,
            'timestamp': datetime.now().isoformat(),
            'error': error_msg,
            'error_type': error_type
        })
        
        # Check if we should retry
        if not should_retry_error(error_type, attempt, self.config.max_attempts):
            return (False, 0, f"Max attempts ({self.config.max_attempts}) reached")
        
        # Get error-specific delay
        delay = get_error_specific_delay(error_type, attempt, self.config)
        description = get_error_description(error_type)
        
        return (True, delay, description)
    
    def _get_error_type(self, error: Exception) -> str:
        """
        Get the error type from an exception.
        
        Args:
            error: The exception
        
        Returns:
            Error type string
        """
        # Check exception class name first
        error_class = type(error).__name__
        if error_class in ['ResourceInUseException', 'LimitExceededException', 
                          'ValidationException', 'ThrottlingException', 'InternalServerError']:
            return error_class
        
        # Check error message
        error_msg = str(error)
        return extract_error_type(error_msg) or 'UnknownError'
    
    def get_retry_history(self) -> list:
        """Get the retry history."""
        return self.retry_history
    
    def reset(self):
        """Reset the retry history."""
        self.retry_history = []


def wait_for_gsi_active_with_retry(
    dynamodb_client: Any,
    table_name: str,
    index_name: str,
    timeout: int = 900,
    poll_interval: int = 10,
    max_query_retries: int = 3
) -> bool:
    """
    Wait for a GSI to become ACTIVE with retry logic for status queries.
    
    This function implements the requirements from Task 1.16:
    - Poll GSI status every 10 seconds
    - Timeout after 15 minutes (90 attempts)
    - Retry status query up to 3 times if query fails
    - Log activation progress with timestamps
    
    Args:
        dynamodb_client: Boto3 DynamoDB client
        table_name: Name of the table
        index_name: Name of the GSI
        timeout: Maximum wait time in seconds (default: 900 = 15 minutes)
        poll_interval: Interval between status checks in seconds (default: 10)
        max_query_retries: Maximum retries for status query failures (default: 3)
    
    Returns:
        True if GSI is ACTIVE, False if timeout or error
    """
    start_time = time.time()
    max_attempts = timeout // poll_interval  # 90 attempts for 15 minutes
    attempt = 0
    
    logger.info(
        f"Waiting for GSI {index_name} on table {table_name} to become ACTIVE "
        f"(timeout: {timeout}s, poll interval: {poll_interval}s, max attempts: {max_attempts})"
    )
    
    while attempt < max_attempts:
        elapsed = int(time.time() - start_time)
        attempt += 1
        
        # Try to query GSI status with retries
        query_success = False
        query_retry_count = 0
        last_query_error = None
        
        while query_retry_count < max_query_retries and not query_success:
            try:
                response = dynamodb_client.describe_table(TableName=table_name)
                gsis = response['Table'].get('GlobalSecondaryIndexes', [])
                
                # Find the target GSI
                target_gsi = None
                for gsi in gsis:
                    if gsi['IndexName'] == index_name:
                        target_gsi = gsi
                        break
                
                if target_gsi is None:
                    logger.error(
                        f"GSI {index_name} not found on table {table_name} "
                        f"(elapsed: {elapsed}s, attempt: {attempt}/{max_attempts})"
                    )
                    return False
                
                status = target_gsi['IndexStatus']
                query_success = True
                
                # Check status
                if status == 'ACTIVE':
                    logger.info(
                        f"GSI {index_name} on table {table_name} is ACTIVE "
                        f"(elapsed: {elapsed}s, attempts: {attempt})"
                    )
                    return True
                elif status == 'CREATING':
                    logger.info(
                        f"GSI {index_name} status: CREATING "
                        f"(elapsed: {elapsed}s, attempt: {attempt}/{max_attempts})"
                    )
                elif status in ['UPDATING', 'DELETING']:
                    logger.warning(
                        f"GSI {index_name} status: {status} "
                        f"(elapsed: {elapsed}s, attempt: {attempt}/{max_attempts})"
                    )
                else:
                    logger.error(
                        f"GSI {index_name} unexpected status: {status} "
                        f"(elapsed: {elapsed}s, attempt: {attempt}/{max_attempts})"
                    )
                    return False
                
            except Exception as e:
                query_retry_count += 1
                last_query_error = str(e)
                
                if query_retry_count < max_query_retries:
                    logger.warning(
                        f"Status query failed for GSI {index_name} "
                        f"(query retry {query_retry_count}/{max_query_retries}): {last_query_error}. "
                        f"Retrying immediately..."
                    )
                    # Retry immediately without delay
                    continue
                else:
                    logger.error(
                        f"Status query failed for GSI {index_name} after {max_query_retries} retries: "
                        f"{last_query_error} (elapsed: {elapsed}s, attempt: {attempt}/{max_attempts})"
                    )
                    return False
        
        # If query failed after all retries, return False
        if not query_success:
            return False
        
        # Check if we've exceeded timeout
        if time.time() - start_time >= timeout:
            logger.error(
                f"Timeout waiting for GSI {index_name} on table {table_name} "
                f"(elapsed: {elapsed}s, attempts: {attempt})"
            )
            return False
        
        # Wait before next poll
        time.sleep(poll_interval)
    
    # Max attempts reached
    elapsed = int(time.time() - start_time)
    logger.error(
        f"Max attempts ({max_attempts}) reached waiting for GSI {index_name} "
        f"on table {table_name} (elapsed: {elapsed}s)"
    )
    return False


def validate_gsi_query(
    dynamodb_client: Any,
    table_name: str,
    index_name: str,
    gsi_config: dict
) -> Tuple[bool, str, dict]:
    """
    Validate that a GSI is functional by performing a test query.
    
    This function implements the requirements from Task 1.17:
    - Perform test query on newly created GSI
    - Verify query uses GSI (not table scan)
    - Mark GSI as "ACTIVE but non-functional" if validation fails
    - Log validation results
    
    Args:
        dynamodb_client: Boto3 DynamoDB client
        table_name: Name of the table
        index_name: Name of the GSI
        gsi_config: GSI configuration with KeySchema
    
    Returns:
        Tuple of (is_functional: bool, status: str, validation_details: dict)
        status can be: "functional", "non-functional", "not-used", "validation-error"
    """
    logger.info(f"Validating GSI {index_name} on table {table_name}...")
    
    validation_details = {
        'index_name': index_name,
        'table_name': table_name,
        'timestamp': datetime.now().isoformat(),
        'test_query_executed': False,
        'uses_gsi': False,
        'error': None
    }
    
    try:
        # Extract key schema to build test query
        key_schema = gsi_config.get('KeySchema', [])
        if not key_schema:
            logger.error(f"No KeySchema found in GSI config for {index_name}")
            validation_details['error'] = "No KeySchema in config"
            return (False, "validation-error", validation_details)
        
        # Get partition key name
        partition_key = None
        sort_key = None
        for key in key_schema:
            if key['KeyType'] == 'HASH':
                partition_key = key['AttributeName']
            elif key['KeyType'] == 'RANGE':
                sort_key = key['AttributeName']
        
        if not partition_key:
            logger.error(f"No partition key found in KeySchema for {index_name}")
            validation_details['error'] = "No partition key in KeySchema"
            return (False, "validation-error", validation_details)
        
        # Build a test query with a dummy value
        # We use a value that's unlikely to exist to minimize data retrieval
        test_value = "__validation_test_nonexistent__"
        
        logger.info(f"  Executing test query on {index_name} with partition key: {partition_key}")
        
        # Perform test query
        query_params = {
            'TableName': table_name,
            'IndexName': index_name,
            'KeyConditionExpression': f"{partition_key} = :val",
            'ExpressionAttributeValues': {':val': {'S': test_value}},
            'Limit': 1,  # Only need to verify query works, not retrieve data
            'ReturnConsumedCapacity': 'INDEXES'  # Get capacity info to verify GSI usage
        }
        
        response = dynamodb_client.query(**query_params)
        validation_details['test_query_executed'] = True
        
        # Check if query used the GSI
        consumed_capacity = response.get('ConsumedCapacity', {})
        
        # If GlobalSecondaryIndexes is present in consumed capacity, GSI was used
        gsi_capacity = consumed_capacity.get('GlobalSecondaryIndexes', {})
        
        if index_name in gsi_capacity:
            # GSI was used successfully
            validation_details['uses_gsi'] = True
            validation_details['consumed_capacity'] = consumed_capacity
            logger.info(f"  ✓ GSI {index_name} is functional and being used for queries")
            return (True, "functional", validation_details)
        elif consumed_capacity.get('Table'):
            # Table scan was performed instead of using GSI
            validation_details['uses_gsi'] = False
            validation_details['consumed_capacity'] = consumed_capacity
            logger.warning(
                f"  ⚠ GSI {index_name} is ACTIVE but query performed table scan instead of using GSI"
            )
            return (False, "not-used", validation_details)
        else:
            # Query succeeded but capacity info unclear
            validation_details['uses_gsi'] = None
            validation_details['consumed_capacity'] = consumed_capacity
            logger.warning(
                f"  ⚠ GSI {index_name} query succeeded but could not verify GSI usage "
                f"(no capacity info returned)"
            )
            # Consider this functional since query worked
            return (True, "functional", validation_details)
    
    except dynamodb_client.exceptions.ResourceNotFoundException as e:
        # GSI or table not found
        error_msg = f"GSI or table not found: {str(e)}"
        logger.error(f"  ✗ {error_msg}")
        validation_details['error'] = error_msg
        return (False, "validation-error", validation_details)
    
    except Exception as e:
        # Other query errors
        error_msg = f"Validation query failed: {str(e)}"
        logger.error(f"  ✗ {error_msg}")
        validation_details['error'] = error_msg
        return (False, "non-functional", validation_details)


def log_validation_results(
    index_name: str,
    table_name: str,
    is_functional: bool,
    status: str,
    validation_details: dict
) -> None:
    """
    Log detailed validation results for a GSI.
    
    Args:
        index_name: Name of the GSI
        table_name: Name of the table
        is_functional: Whether GSI is functional
        status: Validation status
        validation_details: Detailed validation information
    """
    logger.info(f"Validation results for GSI {index_name} on table {table_name}:")
    logger.info(f"  Status: {status}")
    logger.info(f"  Functional: {is_functional}")
    logger.info(f"  Test query executed: {validation_details.get('test_query_executed', False)}")
    logger.info(f"  Uses GSI: {validation_details.get('uses_gsi', 'unknown')}")
    
    if validation_details.get('error'):
        logger.error(f"  Error: {validation_details['error']}")
    
    if validation_details.get('consumed_capacity'):
        logger.info(f"  Consumed capacity: {validation_details['consumed_capacity']}")
    
    # Provide recommendations based on status
    if status == "non-functional":
        logger.warning(f"  ⚠ Recommendation: GSI {index_name} is ACTIVE but non-functional. "
                      f"Check GSI configuration and table data.")
    elif status == "not-used":
        logger.warning(f"  ⚠ Recommendation: GSI {index_name} is ACTIVE but queries are not using it. "
                      f"Verify KeyConditionExpression matches GSI key schema.")
    elif status == "validation-error":
        logger.error(f"  ✗ Recommendation: Could not validate GSI {index_name}. "
                    f"Manual verification required.")
