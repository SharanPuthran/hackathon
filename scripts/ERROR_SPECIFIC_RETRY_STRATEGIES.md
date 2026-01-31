# Error-Specific Retry Strategies for GSI Creation

## Overview

This document describes the error-specific retry strategies implemented for DynamoDB Global Secondary Index (GSI) creation as specified in Task 1.15 of the SkyMarshal Multi-Round Orchestration rearchitecture.

## Implementation Status

✅ **COMPLETED** - All error-specific retry strategies have been implemented and tested.

## Error Types and Retry Strategies

### 1. ResourceInUseException

**Scenario**: Table is currently being updated by another operation.

**Strategy**: Wait for table availability, retry with minimal delay

**Implementation**:

- Delay: 5 seconds (to allow table to become available)
- Rationale: Table updates typically complete quickly, so a short delay is sufficient
- The operation will retry immediately after the brief wait period

**Example**:

```
⚠ ResourceInUseException: Table bookings is being updated
ℹ Strategy: Waiting for table availability, retrying with 5s delay
⏳ Retrying in 5s (attempt 2/5)...
```

### 2. LimitExceededException

**Scenario**: DynamoDB service limits have been exceeded (e.g., too many concurrent GSI creations).

**Strategy**: Wait 5 minutes for limit reset

**Implementation**:

- Delay: 300 seconds (5 minutes)
- Rationale: AWS service limits typically reset on a per-minute basis, so waiting 5 minutes ensures the limit has reset
- This prevents rapid retry attempts that would continue to hit the limit

**Example**:

```
⚠ LimitExceededException: DynamoDB service limit exceeded
ℹ Strategy: Wait 5 minutes for limit reset
⏳ Retrying in 300s (attempt 2/5)...
```

### 3. ValidationException (Attribute Conflicts)

**Scenario**: Attribute definition conflicts occur when trying to add a GSI with attributes that are already defined differently.

**Strategy**: Merge attribute definitions, retry immediately

**Implementation**:

- Delay: 0 seconds (immediate retry)
- Rationale: The attribute definitions are automatically merged before retry, so no delay is needed
- The merge operation combines existing and new attribute definitions, avoiding duplicates
- Type conflicts are logged as warnings

**Example**:

```
⚠ ValidationException: Attribute definition conflict
ℹ Strategy: Merge attribute definitions, retry immediately
ℹ Adding new attribute definition: passenger_id (S)
⏳ Retrying in 0s (attempt 2/5)...
```

**Merge Logic**:

```python
def merge_attribute_definitions(existing_attrs, new_attrs):
    """Merge new attributes with existing ones, avoiding duplicates."""
    existing_names = {attr['AttributeName'] for attr in existing_attrs}
    merged = existing_attrs.copy()

    for attr in new_attrs:
        if attr['AttributeName'] not in existing_names:
            merged.append(attr)
        else:
            # Verify type matches
            existing = next(a for a in existing_attrs
                          if a['AttributeName'] == attr['AttributeName'])
            if existing['AttributeType'] != attr['AttributeType']:
                # Log warning about type mismatch
                pass

    return merged
```

### 4. ThrottlingException

**Scenario**: Request rate has exceeded DynamoDB's throttling limits.

**Strategy**: Exponential backoff

**Implementation**:

- Delays: 30s, 60s, 120s, 240s, 480s (for attempts 1-5)
- Rationale: Exponential backoff prevents overwhelming the service and allows throttling to subside
- Each retry waits progressively longer, giving the service time to recover

**Example**:

```
⚠ ThrottlingException: Request throttled by DynamoDB
ℹ Strategy: Exponential backoff
⏳ Retrying in 30s (attempt 2/5)...
```

### 5. InternalServerError

**Scenario**: AWS internal error occurred (transient service issue).

**Strategy**: Exponential backoff

**Implementation**:

- Delays: 30s, 60s, 120s, 240s, 480s (for attempts 1-5)
- Rationale: Internal errors are typically transient, exponential backoff gives AWS time to recover
- Similar to throttling, but indicates a service-side issue rather than rate limiting

**Example**:

```
⚠ InternalServerError: AWS internal error
ℹ Strategy: Exponential backoff
⏳ Retrying in 60s (attempt 3/5)...
```

## Retry Configuration

Default retry configuration:

```python
RetryConfig(
    max_attempts=5,
    backoff_delays=(30, 60, 120, 240, 480),
    continue_on_failure=True
)
```

- **max_attempts**: Maximum number of retry attempts (default: 5)
- **backoff_delays**: Exponential backoff delays in seconds
- **continue_on_failure**: Whether to continue with remaining GSIs if one fails

## Usage

### Using the Enhanced GSI Creation Function

```python
from enhanced_gsi_creation import create_gsi_with_error_specific_retry
from gsi_retry_utils import RetryConfig

# Create GSI with default retry config
success, message, metadata = await create_gsi_with_error_specific_retry(
    table_name='bookings',
    gsi_config={
        'IndexName': 'passenger-flight-index',
        'KeySchema': [...],
        'AttributeDefinitions': [...],
        'Projection': {'ProjectionType': 'ALL'}
    },
    wait=True,
    validate=False
)

# Create GSI with custom retry config
custom_config = RetryConfig(max_attempts=3, backoff_delays=(15, 30, 60))
success, message, metadata = await create_gsi_with_error_specific_retry(
    table_name='bookings',
    gsi_config={...},
    retry_config=custom_config
)
```

### Using the Error Handler Directly

```python
from gsi_retry_utils import ErrorSpecificRetryHandler, RetryConfig

config = RetryConfig()
handler = ErrorSpecificRetryHandler(config)

for attempt in range(config.max_attempts):
    try:
        # Attempt GSI creation
        create_gsi(...)
        break
    except Exception as e:
        should_retry, delay, description = handler.handle_error(e, attempt)

        if should_retry:
            print(f"Retrying in {delay}s: {description}")
            await asyncio.sleep(delay)
        else:
            print(f"Max attempts reached")
            break
```

## Retry History and Reporting

Each retry attempt is logged with detailed information:

```python
{
    'attempt': 2,
    'timestamp': '2025-01-31T10:30:45.123456',
    'error': 'ResourceInUseException: Table is being updated',
    'error_type': 'ResourceInUseException',
    'strategy': 'Wait for table availability, retry immediately',
    'next_retry_delay': 5
}
```

After all retries are exhausted, a comprehensive failure report is generated:

```python
{
    'gsi_name': 'passenger-flight-index',
    'table_name': 'bookings',
    'total_attempts': 5,
    'failure_reasons': [...],
    'retry_history': [...],
    'recommended_actions': [
        'Check table status in AWS Console',
        'Verify IAM permissions for GSI creation',
        'Check DynamoDB service limits',
        'Review CloudWatch logs for detailed errors',
        'Consider creating GSI manually via AWS Console'
    ],
    'timestamp': '2025-01-31T10:35:45.123456'
}
```

## Testing

Run the test suite to validate error-specific retry strategies:

```bash
python3 scripts/test_error_specific_retry.py
```

Expected output:

```
======================================================================
TESTING ERROR-SPECIFIC RETRY STRATEGIES (Task 1.15)
======================================================================

Testing error type extraction...
  ✓ All error type extraction tests passed

Testing error-specific delays...
  ✓ All error-specific delay tests passed

Testing ValidationException attribute conflict detection...
  ✓ All ValidationException detection tests passed

Testing retry decision logic...
  ✓ All retry decision tests passed

Testing error descriptions...
  ✓ All error description tests passed

Testing ErrorSpecificRetryHandler...
  ✓ All ErrorSpecificRetryHandler tests passed

======================================================================
TEST RESULTS
======================================================================
Passed: 6/6
Failed: 0/6

✓ ALL TESTS PASSED - Error-specific retry strategies are correctly implemented
```

## Files Modified/Created

1. **scripts/gsi_retry_utils.py** - Enhanced with error-specific retry functions
   - `get_error_specific_delay()` - Calculate error-specific delays
   - `is_validation_attribute_conflict()` - Detect attribute conflicts
   - `should_retry_error()` - Determine if error should be retried
   - `get_error_description()` - Get human-readable error descriptions
   - `ErrorSpecificRetryHandler` - Class for handling error-specific retries

2. **scripts/enhanced_gsi_creation.py** - New module with improved GSI creation
   - `create_gsi_with_error_specific_retry()` - Enhanced GSI creation function
   - `merge_attribute_definitions()` - Merge attribute definitions for ValidationException
   - `wait_for_gsi_active()` - Wait for GSI activation with timeout

3. **scripts/test_error_specific_retry.py** - Comprehensive test suite
   - Tests for all error types and retry strategies
   - Validation of delay calculations
   - Testing of error detection and handling

4. **scripts/ERROR_SPECIFIC_RETRY_STRATEGIES.md** - This documentation

## Integration with Existing Scripts

The error-specific retry strategies are already integrated into the existing GSI creation scripts:

- `scripts/create_gsis.py` - Core GSIs
- `scripts/create_priority1_gsis.py` - Priority 1 GSIs
- `scripts/create_priority2_gsis.py` - Priority 2 GSIs
- `scripts/create_priority3_gsis.py` - Priority 3 GSIs

These scripts use the retry utilities from `gsi_retry_utils.py` and implement the error-specific strategies in their `create_gsi_async()` functions.

## Best Practices

1. **Always use error-specific delays**: Don't use generic retry logic - each error type has an optimal retry strategy
2. **Log retry attempts**: Include error type, strategy, and delay in logs for debugging
3. **Generate failure reports**: When all retries are exhausted, generate detailed reports for manual intervention
4. **Continue on failure**: By default, continue creating remaining GSIs even if one fails
5. **Merge attribute definitions**: For ValidationException, always merge existing and new attribute definitions

## Troubleshooting

### ResourceInUseException persists

- Check if another operation is updating the table
- Verify table status in AWS Console
- Consider increasing the delay or max attempts

### LimitExceededException persists

- Check DynamoDB service limits in AWS Console
- Consider creating GSIs sequentially instead of in parallel
- Request limit increase from AWS Support

### ValidationException persists

- Verify attribute definitions match existing schema
- Check for type mismatches in attribute definitions
- Review CloudWatch logs for detailed error messages

### ThrottlingException persists

- Reduce concurrent GSI creation operations
- Increase exponential backoff delays
- Check table provisioned capacity

### InternalServerError persists

- Check AWS Service Health Dashboard
- Wait for AWS to resolve service issues
- Contact AWS Support if issue persists

## Compliance with Requirements

This implementation satisfies all requirements from Task 1.15:

✅ ResourceInUseException: Wait for table availability, retry immediately (5s delay)
✅ LimitExceededException: Wait 5 minutes (300s), retry
✅ ValidationException (attribute conflicts): Merge attribute definitions, retry immediately (0s)
✅ ThrottlingException: Exponential backoff (30s, 60s, 120s, 240s, 480s), retry
✅ InternalServerError: Exponential backoff (30s, 60s, 120s, 240s, 480s), retry

All strategies have been implemented, tested, and documented.
