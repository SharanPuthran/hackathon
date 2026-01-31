# Error-Specific Retry Strategies - Quick Reference

## Quick Lookup Table

| Error                      | Delay      | What It Means                 | What We Do                                 |
| -------------------------- | ---------- | ----------------------------- | ------------------------------------------ |
| **ResourceInUseException** | 5s         | Table is being updated        | Wait briefly for table to become available |
| **LimitExceededException** | 300s       | Hit DynamoDB service limit    | Wait 5 minutes for limit to reset          |
| **ValidationException**    | 0s         | Attribute definition conflict | Merge attributes and retry immediately     |
| **ThrottlingException**    | 30s → 480s | Too many requests             | Exponential backoff to reduce load         |
| **InternalServerError**    | 30s → 480s | AWS internal issue            | Exponential backoff while AWS recovers     |

## When You See These Errors

### ResourceInUseException

```
⚠ ResourceInUseException: Table bookings is being updated
ℹ Strategy: Waiting for table availability, retrying with 5s delay
⏳ Retrying in 5s (attempt 2/5)...
```

**What to do**: Nothing - the script will automatically retry after 5 seconds.

### LimitExceededException

```
⚠ LimitExceededException: DynamoDB service limit exceeded
ℹ Strategy: Wait 5 minutes for limit reset
⏳ Retrying in 300s (attempt 2/5)...
```

**What to do**: Wait - you've hit AWS limits. Consider creating GSIs sequentially instead of in parallel.

### ValidationException

```
⚠ ValidationException: Attribute definition conflict
ℹ Strategy: Merge attribute definitions, retry immediately
ℹ Adding new attribute definition: passenger_id (S)
⏳ Retrying in 0s (attempt 2/5)...
```

**What to do**: Nothing - attributes are automatically merged and retry happens immediately.

### ThrottlingException

```
⚠ ThrottlingException: Request throttled by DynamoDB
ℹ Strategy: Exponential backoff
⏳ Retrying in 30s (attempt 2/5)...
```

**What to do**: Wait - you're sending too many requests. The delay increases with each retry.

### InternalServerError

```
⚠ InternalServerError: AWS internal error
ℹ Strategy: Exponential backoff
⏳ Retrying in 60s (attempt 3/5)...
```

**What to do**: Wait - AWS is having issues. Check AWS Service Health Dashboard if it persists.

## Exponential Backoff Schedule

| Attempt | Delay        |
| ------- | ------------ |
| 1 → 2   | 30s          |
| 2 → 3   | 60s          |
| 3 → 4   | 120s (2 min) |
| 4 → 5   | 240s (4 min) |
| 5 → 6   | 480s (8 min) |

## Common Questions

**Q: Why does ResourceInUseException use 5s instead of 0s?**
A: A brief delay allows the table to actually become available. Immediate retry would likely hit the same error.

**Q: Why wait 5 minutes for LimitExceededException?**
A: AWS service limits reset on a per-minute basis. 5 minutes ensures the limit has definitely reset.

**Q: What if all 5 attempts fail?**
A: A detailed failure report is generated with recommended manual intervention steps.

**Q: Can I change the retry configuration?**
A: Yes, pass a custom `RetryConfig` object:

```python
custom_config = RetryConfig(max_attempts=3, backoff_delays=(15, 30, 60))
```

**Q: Will it continue with other GSIs if one fails?**
A: Yes, by default `continue_on_failure=True`. Failed GSIs are reported at the end.

## Testing

Run the test suite to verify all strategies work:

```bash
python3 scripts/test_error_specific_retry.py
```

Expected: All 6 test suites pass ✅

## Need More Details?

See `scripts/ERROR_SPECIFIC_RETRY_STRATEGIES.md` for complete documentation.
