# GSI Creation State File Documentation

## Overview

The GSI creation scripts now support state file tracking and resume capability. This allows you to:

1. **Track Progress**: Monitor GSI creation status in real-time
2. **Resume After Interruption**: Continue from where you left off if the script is interrupted
3. **Retry Failed GSIs**: Easily identify and retry GSIs that failed
4. **Audit Trail**: Maintain a complete record of all GSI creation attempts

## State File Format

The state file (`.gsi_creation_state.json`) is stored in the same directory as the script and contains:

```json
{
  "version": "1.0",
  "created_at": "2026-02-01T10:30:00Z",
  "updated_at": "2026-02-01T10:35:00Z",
  "script_name": "create_priority1_gsis.py",
  "gsis": {
    "bookings.passenger-flight-index": {
      "table_name": "bookings",
      "index_name": "passenger-flight-index",
      "status": "active",
      "creation_time": "2026-02-01T10:31:00Z",
      "retry_count": 2,
      "last_error": null
    },
    "bookings.flight-status-index": {
      "table_name": "bookings",
      "index_name": "flight-status-index",
      "status": "failed",
      "creation_time": "2026-02-01T10:33:00Z",
      "retry_count": 5,
      "last_error": "LimitExceededException: Too many GSIs"
    }
  },
  "summary": {
    "total": 6,
    "pending": 2,
    "in_progress": 0,
    "active": 3,
    "failed": 1
  }
}
```

### Status Values

- **pending**: GSI creation not yet attempted
- **in_progress**: GSI creation currently in progress
- **active**: GSI successfully created and is ACTIVE
- **failed**: GSI creation failed after all retries

## Usage

### Basic Usage

The state file is automatically created and updated when you run any GSI creation script:

```bash
python3 create_priority1_gsis.py
```

The script will:

1. Create `.gsi_creation_state.json` on first run
2. Update the state after each GSI operation
3. Skip GSIs that are already active
4. Continue with remaining GSIs if one fails

### Resume After Interruption

If the script is interrupted (Ctrl+C, network failure, etc.), you can resume by running the same command:

```bash
python3 create_priority1_gsis.py
```

The script will:

1. Load the existing state file
2. Skip GSIs that are already active
3. Continue from the first pending GSI
4. Retry failed GSIs if requested

### Retry Failed GSIs

To retry only the GSIs that failed:

```bash
python3 create_priority1_gsis.py --retry-failed
```

This will:

1. Load the state file
2. Skip active GSIs
3. Skip pending GSIs
4. Retry only failed GSIs

### View Current Status

To view the current status without making changes:

```bash
python3 -c "
from gsi_state_manager import GSIStateManager
state = GSIStateManager('create_priority1_gsis.py', '.')
state.print_status()
"
```

### Clean Up State File

The state file is automatically archived when all GSIs are successfully created. You can also manually clean up:

```bash
python3 -c "
from gsi_state_manager import GSIStateManager
state = GSIStateManager('create_priority1_gsis.py', '.')
state.cleanup()
"
```

This will rename the state file to `.gsi_creation_state_YYYYMMDD_HHMMSS.json` for archival.

## Integration with GSI Creation Scripts

### Using State Manager in Your Script

```python
from gsi_state_manager import GSIStateManager
from enhanced_gsi_creation import create_gsi_with_error_specific_retry

# Initialize state manager
state_manager = GSIStateManager(
    script_name="my_gsi_script.py",
    state_dir="."
)

# Initialize GSI definitions
state_manager.initialize_gsis(gsi_definitions)

# Create GSIs with state tracking
for table_name, gsi_configs in gsi_definitions.items():
    for gsi_config in gsi_configs:
        index_name = gsi_config['IndexName']

        # Skip if already active
        if state_manager.should_skip_gsi(table_name, index_name):
            print(f"Skipping {table_name}.{index_name} (already active)")
            continue

        # Create GSI with state tracking
        success, message, metadata = await create_gsi_with_error_specific_retry(
            table_name=table_name,
            gsi_config=gsi_config,
            wait=True,
            validate=True,
            retry_config=retry_config,
            state_manager=state_manager  # Pass state manager
        )

# Clean up on completion
if state_manager.is_complete():
    state_manager.cleanup()
```

### State Updates

The state manager automatically updates the state file:

1. **Before GSI creation**: Status set to `in_progress`
2. **After each retry**: Retry count incremented, error recorded
3. **On success**: Status set to `active`
4. **On failure**: Status set to `failed`, error recorded

## Benefits

### 1. Resilience

- Script can be interrupted and resumed without losing progress
- Network failures don't require starting over
- Failed GSIs can be retried without recreating successful ones

### 2. Visibility

- Real-time status of all GSIs
- Clear indication of which GSIs succeeded, failed, or are pending
- Detailed error messages for failures

### 3. Efficiency

- Skip GSIs that are already active
- Avoid redundant API calls
- Focus retry efforts on failed GSIs only

### 4. Auditability

- Complete record of all GSI creation attempts
- Timestamps for each operation
- Retry counts and error messages
- Archived state files for historical reference

## State File Location

The state file is stored in the same directory as the script:

```
scripts/
├── create_priority1_gsis.py
├── .gsi_creation_state.json          # Active state file
└── .gsi_creation_state_20260201_103000.json  # Archived state file
```

## Troubleshooting

### State File Corrupted

If the state file becomes corrupted, delete it and start fresh:

```bash
rm .gsi_creation_state.json
python3 create_priority1_gsis.py
```

The script will detect existing GSIs and skip them automatically.

### State File Out of Sync

If the state file is out of sync with actual DynamoDB state:

1. Delete the state file
2. Run the script
3. The script will query DynamoDB and skip existing GSIs

### Resume Not Working

If resume doesn't work as expected:

1. Check that the state file exists: `ls -la .gsi_creation_state.json`
2. Verify the state file is valid JSON: `python3 -m json.tool .gsi_creation_state.json`
3. Check the script name matches: The state file records which script created it

## Examples

### Example 1: Normal Execution

```bash
$ python3 create_priority1_gsis.py

================================================================================
GSI Creation Status
================================================================================

Summary:
  Total: 6
  Active: 0
  Failed: 0
  Pending: 6
  In Progress: 0

Creating GSI: bookings.passenger-flight-index
  ✓ GSI created successfully

Creating GSI: bookings.flight-status-index
  ✓ GSI created successfully

...

All GSIs created successfully!
State file archived to .gsi_creation_state_20260201_103000.json
```

### Example 2: Interrupted and Resumed

```bash
$ python3 create_priority1_gsis.py

Creating GSI: bookings.passenger-flight-index
  ✓ GSI created successfully

Creating GSI: bookings.flight-status-index
^C
Interrupted by user!
State has been saved.

$ python3 create_priority1_gsis.py

Loaded state from .gsi_creation_state.json
  Created: 2026-02-01T10:30:00Z
  Updated: 2026-02-01T10:31:00Z
  Summary: 1 active, 0 failed, 5 pending, 0 in progress

Skipping bookings.passenger-flight-index (already active)

Creating GSI: bookings.flight-status-index
  ✓ GSI created successfully

...
```

### Example 3: Retry Failed GSIs

```bash
$ python3 create_priority1_gsis.py

...
Creating GSI: bookings.flight-status-index
  ✗ Failed after 5 attempts: LimitExceededException

$ python3 create_priority1_gsis.py --retry-failed

Loaded state from .gsi_creation_state.json

Retrying failed GSIs:
  - bookings.flight-status-index

Creating GSI: bookings.flight-status-index
  ✓ GSI created successfully
```

## API Reference

### GSIStateManager

```python
class GSIStateManager:
    """Manages GSI creation state with resume capability."""

    def __init__(self, script_name: str, state_dir: str = "."):
        """Initialize state manager."""

    def initialize_gsis(self, gsi_definitions: Dict[str, List[dict]]) -> None:
        """Initialize GSI states from definitions."""

    def update_gsi_status(
        self,
        table_name: str,
        index_name: str,
        status: str,
        retry_count: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Update the status of a GSI."""

    def get_gsi_status(self, table_name: str, index_name: str) -> Optional[str]:
        """Get the status of a GSI."""

    def should_skip_gsi(self, table_name: str, index_name: str) -> bool:
        """Check if a GSI should be skipped (already active)."""

    def get_pending_gsis(self) -> List[Tuple[str, str]]:
        """Get list of GSIs that are pending."""

    def get_failed_gsis(self) -> List[Tuple[str, str, str]]:
        """Get list of GSIs that failed."""

    def get_resume_point(self) -> Optional[Tuple[str, str]]:
        """Get the resume point (first pending GSI)."""

    def is_complete(self) -> bool:
        """Check if all GSIs are complete."""

    def cleanup(self) -> None:
        """Clean up state file on successful completion."""

    def print_status(self) -> None:
        """Print current status of all GSIs."""
```

## See Also

- [GSI Retry Logic Implementation Guide](GSI_RETRY_LOGIC_IMPLEMENTATION_GUIDE.md)
- [Error-Specific Retry Strategies](ERROR_SPECIFIC_RETRY_STRATEGIES.md)
- [Priority 1 GSIs README](PRIORITY1_GSIS_README.md)
