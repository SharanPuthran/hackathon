# GSI State File - Quick Reference

## Quick Start

### Run GSI Creation Script

```bash
python3 create_priority1_gsis.py
```

State file automatically created at `.gsi_creation_state.json`

### Resume After Interruption

```bash
python3 create_priority1_gsis.py
```

Same command - automatically detects and loads existing state

### View Current Status

```bash
python3 -c "from gsi_state_manager import GSIStateManager; GSIStateManager('create_priority1_gsis.py', '.').print_status()"
```

### Retry Failed GSIs Only

```bash
python3 create_priority1_gsis.py --retry-failed
```

## State File Location

```
scripts/.gsi_creation_state.json
```

## Status Values

| Status        | Meaning                  |
| ------------- | ------------------------ |
| `pending`     | Not yet attempted        |
| `in_progress` | Currently being created  |
| `active`      | Successfully created     |
| `failed`      | Failed after all retries |

## Common Scenarios

### Scenario 1: Normal Execution

```bash
$ python3 create_priority1_gsis.py
# Creates all GSIs
# Archives state file on completion
```

### Scenario 2: Interrupted (Ctrl+C)

```bash
$ python3 create_priority1_gsis.py
# Creates some GSIs
^C Interrupted!

$ python3 create_priority1_gsis.py
# Resumes from where it left off
# Skips already-active GSIs
```

### Scenario 3: Some GSIs Failed

```bash
$ python3 create_priority1_gsis.py
# Some GSIs succeed, some fail

$ python3 create_priority1_gsis.py --retry-failed
# Retries only failed GSIs
```

## State File Format

```json
{
  "version": "1.0",
  "created_at": "2026-02-01T10:30:00Z",
  "updated_at": "2026-02-01T10:35:00Z",
  "script_name": "create_priority1_gsis.py",
  "gsis": {
    "table.index": {
      "table_name": "table",
      "index_name": "index",
      "status": "active|failed|pending|in_progress",
      "creation_time": "2026-02-01T10:31:00Z",
      "retry_count": 2,
      "last_error": "error message or null"
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

## Troubleshooting

### State File Corrupted

```bash
rm .gsi_creation_state.json
python3 create_priority1_gsis.py
# Script will detect existing GSIs and skip them
```

### Force Fresh Start

```bash
rm .gsi_creation_state.json
python3 create_priority1_gsis.py
```

### View Archived State Files

```bash
ls -la .gsi_creation_state_*.json
```

## Integration Code

```python
from gsi_state_manager import GSIStateManager

# Initialize
state_manager = GSIStateManager(
    script_name="my_script.py",
    state_dir="."
)

# Initialize GSIs
state_manager.initialize_gsis(gsi_definitions)

# Check if should skip
if state_manager.should_skip_gsi(table_name, index_name):
    continue

# Create GSI with state tracking
success, message, metadata = await create_gsi_with_error_specific_retry(
    table_name=table_name,
    gsi_config=gsi_config,
    state_manager=state_manager
)

# Cleanup on completion
if state_manager.is_complete():
    state_manager.cleanup()
```

## Key Benefits

✅ **Resilience**: Resume after interruption  
✅ **Efficiency**: Skip already-active GSIs  
✅ **Visibility**: Real-time status tracking  
✅ **Auditability**: Complete history with timestamps

## See Also

- [Full Documentation](STATE_FILE_DOCUMENTATION.md)
- [GSI Retry Logic Guide](GSI_RETRY_LOGIC_IMPLEMENTATION_GUIDE.md)
- [Error-Specific Retry Strategies](ERROR_SPECIFIC_RETRY_STRATEGIES.md)
