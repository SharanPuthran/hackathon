#!/usr/bin/env python3
"""
Basic test for checkpoint persistence
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, 'src')

from checkpoint import CheckpointSaver, ThreadManager
from datetime import datetime


async def test_development_mode():
    """Test checkpoint persistence in development mode (in-memory)"""
    print("\n" + "="*60)
    print("TEST 1: Development Mode (In-Memory)")
    print("="*60)
    
    # Initialize in development mode
    saver = CheckpointSaver(mode="development")
    manager = ThreadManager(checkpoint_saver=saver)
    
    print(f"✅ CheckpointSaver initialized: {saver.mode} mode")
    print(f"✅ Backend: {saver.backend.__class__.__name__}")
    
    # Create thread
    thread_id = manager.create_thread(
        user_prompt="Test disruption",
        metadata={"test": True}
    )
    print(f"✅ Thread created: {thread_id}")
    
    # Save checkpoint
    await saver.save_checkpoint(
        thread_id=thread_id,
        checkpoint_id="test_checkpoint",
        state={"data": "test_value", "count": 42},
        metadata={"phase": "test", "timestamp": datetime.now().isoformat()}
    )
    print(f"✅ Checkpoint saved: test_checkpoint")
    
    # Load checkpoint
    loaded = await saver.load_checkpoint(
        thread_id=thread_id,
        checkpoint_id="test_checkpoint"
    )
    print(f"✅ Checkpoint loaded: {loaded is not None}")
    
    # List checkpoints
    checkpoints = await saver.list_checkpoints(thread_id=thread_id)
    print(f"✅ Checkpoints listed: {len(checkpoints)} found")
    
    # Mark thread complete
    manager.mark_thread_complete(thread_id=thread_id)
    status = manager.get_thread_status(thread_id)
    print(f"✅ Thread status: {status}")
    
    print("\n✅ Development mode test PASSED")
    return True


async def test_production_mode():
    """Test checkpoint persistence in production mode (DynamoDB)"""
    print("\n" + "="*60)
    print("TEST 2: Production Mode (DynamoDB)")
    print("="*60)
    
    # Initialize in production mode
    os.environ["CHECKPOINT_MODE"] = "production"
    os.environ["CHECKPOINT_TABLE_NAME"] = "SkyMarshalCheckpoints"
    os.environ["CHECKPOINT_S3_BUCKET"] = "skymarshal-checkpoints-368613657554"
    
    saver = CheckpointSaver(mode="production")
    manager = ThreadManager(checkpoint_saver=saver)
    
    print(f"✅ CheckpointSaver initialized: {saver.mode} mode")
    print(f"✅ Backend: {saver.backend.__class__.__name__}")
    
    # Create thread
    thread_id = manager.create_thread(
        user_prompt="Test disruption in production",
        metadata={"test": True, "mode": "production"}
    )
    print(f"✅ Thread created: {thread_id}")
    
    # Save checkpoint
    await saver.save_checkpoint(
        thread_id=thread_id,
        checkpoint_id="prod_test_checkpoint",
        state={
            "data": "production_test_value",
            "count": 100,
            "nested": {"key": "value"}
        },
        metadata={
            "phase": "test",
            "timestamp": datetime.now().isoformat(),
            "mode": "production"
        }
    )
    print(f"✅ Checkpoint saved to DynamoDB: prod_test_checkpoint")
    
    # Load checkpoint
    loaded = await saver.load_checkpoint(
        thread_id=thread_id,
        checkpoint_id="prod_test_checkpoint"
    )
    print(f"✅ Checkpoint loaded from DynamoDB: {loaded is not None}")
    
    if loaded:
        print(f"   Loaded data: {loaded.get('data', 'N/A')}")
    
    # List checkpoints
    checkpoints = await saver.list_checkpoints(thread_id=thread_id)
    print(f"✅ Checkpoints listed: {len(checkpoints)} found")
    
    # Mark thread complete
    manager.mark_thread_complete(thread_id=thread_id)
    status = manager.get_thread_status(thread_id)
    print(f"✅ Thread status: {status}")
    
    print("\n✅ Production mode test PASSED")
    return True


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("CHECKPOINT PERSISTENCE BASIC TESTS")
    print("="*60)
    
    try:
        # Test 1: Development mode
        result1 = await test_development_mode()
        
        # Test 2: Production mode
        result2 = await test_production_mode()
        
        if result1 and result2:
            print("\n" + "="*60)
            print("✅ ALL TESTS PASSED")
            print("="*60)
            return 0
        else:
            print("\n" + "="*60)
            print("❌ SOME TESTS FAILED")
            print("="*60)
            return 1
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
