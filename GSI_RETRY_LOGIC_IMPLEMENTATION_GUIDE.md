# GSI Creation Retry Logic - Implementation Guide

**Date:** January 31, 2026  
**Purpose:** Comprehensive guide for implementing robust retry logic in GSI creation scripts  
**Spec Reference:** Requirements 4.31-4.52

---

## Overview

This guide provides detailed implementation specifications for retry logic in DynamoDB GSI creation scripts. The retry logic ensures GSI creation succeeds even in the face of transient failures, resource conflicts, and rate limiting.

## Retry Strategy

### Exponential Backoff Configuration

```python
MAX_RETRIES = 5
BACKOFF_DELAYS = [30, 60, 120, 240, 480]  # seconds
STATUS_POLL_INTERVAL = 10  # seconds
STATUS_POLL_TIMEOUT = 900  # 15 minutes
STATUS_POLL_RETRIES = 3
DELETE_RETRIES = 3
DELETE_RETRY_DELAY = 30  # seconds
```

### Error-Specific Retry Strategies

| Error Type             | Strategy              | Delay     | Max Retries |
| ---------------------- | --------------------- | --------- | ----------- |
| ResourceInUseException | Wait for availability | Immediate | 5           |
| LimitExceededException | Wait for quota reset  | 300s      | 5           |
| ValidationException    | Merge attributes      | 30s       | 5           |
| ThrottlingException    | Exponential backoff   | 30-480s   | 5           |
| InternalServerError    | Exponential backoff   | 30-480s   | 5           |

## State File Format

```json
{
  "version": "1.0",
  "started_at": "2026-01-31T10:00:00Z",
  "last_updated": "2026-01-31T10:15:00Z",
  "gsis": {
    "passenger-flight-index": {
      "table": "bookings",
      "status": "active",
      "created_at": "2026-01-31T10:05:00Z",
      "retry_count": 0,
      "last_error": null
    },
    "crew-duty-date-index": {
      "table": "CrewRoster",
      "status": "failed",
      "created_at": null,
      "retry_count": 5,
      "last_error": "LimitExceededException: Too many GSIs"
    }
  }
}
```

## Implementation Checklist

### Core Retry Logic

- [ ] Implement retry decorator with exponential backoff
- [ ] Implement error-specific retry strategies
- [ ] Log each retry attempt with details
- [ ] Continue with remaining GSIs on failure

### State Management

- [ ] Create state file on script start
- [ ] Update state after each GSI operation
- [ ] Support --resume flag
- [ ] Support --retry-failed flag
- [ ] Clean up state file on success

### Validation

- [ ] Poll GSI status with retry
- [ ] Perform validation query
- [ ] Mark non-functional GSIs
- [ ] Generate validation report

### Reporting

- [ ] Generate detailed failure reports
- [ ] Generate summary report
- [ ] Save reports with timestamps
- [ ] Include retry history

### Rollback

- [ ] Implement delete with retry
- [ ] Handle ResourceInUseException
- [ ] Generate rollback report

## Success Criteria

- All GSI creation scripts include retry logic
- State file enables resume capability
- Validation confirms GSI functionality
- Reports provide actionable information
- Rollback works reliably

---

**Next Steps:** Implement retry logic in all GSI creation scripts
