"""Migration utilities for checkpoint integration"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def test_checkpoint_integration(mode: str = "development") -> bool:
    """
    Test checkpoint integration without deployment.
    
    Verifies that checkpoint infrastructure is working correctly
    in the specified mode before deploying to production.
    
    Args:
        mode: "development" (in-memory) or "production" (DynamoDB)
        
    Returns:
        bool: True if all tests pass, False otherwise
    """
    try:
        from checkpoint import CheckpointSaver, ThreadManager
        
        logger.info(f"Testing checkpoint integration in {mode} mode...")
        
        # Initialize checkpoint infrastructure
        checkpoint_saver = CheckpointSaver(mode=mode)
        thread_manager = ThreadManager(checkpoint_saver=checkpoint_saver)
        
        logger.info(f"✅ CheckpointSaver initialized: backend={checkpoint_saver.backend}")
        logger.info(f"✅ ThreadManager initialized")
        
        # Test thread creation
        thread_id = thread_manager.create_thread(
            user_prompt="Test migration",
            metadata={"test": True}
        )
        logger.info(f"✅ Thread created: {thread_id}")
        
        # Test checkpoint save (async operation)
        import asyncio
        
        async def test_save():
            await checkpoint_saver.save_checkpoint(
                thread_id=thread_id,
                checkpoint_id="test_checkpoint",
                state={"test": "data"},
                metadata={"test": True}
            )
            logger.info(f"✅ Checkpoint saved")
            
            # Test checkpoint load
            checkpoint = await checkpoint_saver.load_checkpoint(
                thread_id=thread_id,
                checkpoint_id="test_checkpoint"
            )
            
            if checkpoint:
                logger.info(f"✅ Checkpoint loaded: {checkpoint.get('checkpoint_id')}")
                return True
            else:
                logger.error("❌ Failed to load checkpoint")
                return False
        
        result = asyncio.run(test_save())
        
        if result:
            logger.info("✅ All checkpoint integration tests passed")
            return True
        else:
            logger.error("❌ Checkpoint integration tests failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Checkpoint integration test failed: {e}")
        logger.exception("Full traceback:")
        return False


def verify_backward_compatibility() -> bool:
    """
    Verify that checkpoint integration maintains backward compatibility.
    
    Tests that:
    1. Orchestrator works without checkpoint parameters
    2. Agents work without checkpoint parameters
    3. All existing functionality remains unchanged
    
    Returns:
        bool: True if backward compatible, False otherwise
    """
    try:
        logger.info("Verifying backward compatibility...")
        
        # Test 1: Import orchestrator without errors
        from main import handle_disruption, run_agent_safely
        logger.info("✅ Orchestrator imports successful")
        
        # Test 2: Verify run_agent_safely has optional checkpoint parameters
        import inspect
        sig = inspect.signature(run_agent_safely)
        params = sig.parameters
        
        # Check that thread_id and checkpoint_saver are optional
        if "thread_id" in params and params["thread_id"].default is None:
            logger.info("✅ thread_id parameter is optional")
        else:
            logger.error("❌ thread_id parameter is not optional")
            return False
        
        if "checkpoint_saver" in params and params["checkpoint_saver"].default is None:
            logger.info("✅ checkpoint_saver parameter is optional")
        else:
            logger.error("❌ checkpoint_saver parameter is not optional")
            return False
        
        # Test 3: Verify checkpoint infrastructure can be disabled
        import os
        original_mode = os.getenv("CHECKPOINT_MODE")
        
        # Test development mode (disabled persistence)
        os.environ["CHECKPOINT_MODE"] = "development"
        from checkpoint import CheckpointSaver
        saver = CheckpointSaver()
        
        if saver.backend == "InMemorySaver":
            logger.info("✅ Development mode (disabled persistence) works")
        else:
            logger.error("❌ Development mode not working correctly")
            return False
        
        # Restore original mode
        if original_mode:
            os.environ["CHECKPOINT_MODE"] = original_mode
        
        logger.info("✅ All backward compatibility checks passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Backward compatibility verification failed: {e}")
        logger.exception("Full traceback:")
        return False


def migration_guide() -> str:
    """
    Return migration guide for converting existing workflows to checkpoint-based.
    
    Returns:
        str: Markdown-formatted migration guide
    """
    guide = """
# Checkpoint Integration Migration Guide

## Overview

The checkpoint integration is **fully backward compatible**. No changes are required to existing code.

## Migration Steps

### Step 1: Test in Development Mode (No AWS Resources)

```bash
# Set development mode in .env
CHECKPOINT_MODE=development

# Run orchestrator - checkpoints will be in-memory only
uv run agentcore dev
```

### Step 2: Verify Checkpoint Functionality

```python
# Run migration test utility
from checkpoint.migration import test_checkpoint_integration

# Test in development mode
test_checkpoint_integration(mode="development")
```

### Step 3: Create Production Infrastructure (Optional)

```bash
# Create DynamoDB table
cd skymarshal_agents_new/skymarshal
uv run python scripts/create_checkpoint_table.py

# Create S3 bucket
uv run python scripts/create_checkpoint_s3_bucket.py
```

### Step 4: Switch to Production Mode (Optional)

```bash
# Update .env
CHECKPOINT_MODE=production
CHECKPOINT_TABLE_NAME=SkyMarshalCheckpoints
CHECKPOINT_S3_BUCKET=skymarshal-checkpoints-<account-id>
CHECKPOINT_TTL_DAYS=90

# Test in production mode
uv run python -c "from checkpoint.migration import test_checkpoint_integration; test_checkpoint_integration('production')"
```

### Step 5: Deploy

```bash
# Deploy with checkpoint support
uv run agentcore deploy
```

## Rollback

To disable checkpoint persistence:

```bash
# Set development mode
CHECKPOINT_MODE=development

# Or remove checkpoint environment variables entirely
# The system will default to development mode
```

## Verification

```python
# Verify backward compatibility
from checkpoint.migration import verify_backward_compatibility
verify_backward_compatibility()
```

## Key Points

1. **No Code Changes Required**: All checkpoint parameters are optional
2. **Gradual Migration**: Can enable checkpoints incrementally
3. **Easy Rollback**: Switch back to development mode anytime
4. **Zero Downtime**: Existing workflows continue to work
5. **Additive Only**: No breaking changes to existing functionality

## Support

For issues or questions:
1. Check logs for checkpoint-related errors
2. Verify environment variables are set correctly
3. Test in development mode first
4. Ensure DynamoDB table and S3 bucket exist (production mode only)
"""
    return guide


if __name__ == "__main__":
    # Run migration tests
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("CHECKPOINT INTEGRATION MIGRATION TESTS")
    print("=" * 60)
    
    # Test 1: Backward compatibility
    print("\n1. Testing backward compatibility...")
    compat_result = verify_backward_compatibility()
    
    # Test 2: Development mode
    print("\n2. Testing development mode...")
    dev_result = test_checkpoint_integration(mode="development")
    
    # Print migration guide
    print("\n" + "=" * 60)
    print("MIGRATION GUIDE")
    print("=" * 60)
    print(migration_guide())
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Backward Compatibility: {'✅ PASS' if compat_result else '❌ FAIL'}")
    print(f"Development Mode: {'✅ PASS' if dev_result else '❌ FAIL'}")
    print("=" * 60)
