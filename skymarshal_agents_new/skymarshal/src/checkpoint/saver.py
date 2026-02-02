"""CheckpointSaver abstraction layer for checkpoint persistence"""

import os
import sys
import json
import logging
import asyncio
import boto3
from typing import Any, Optional, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Size threshold for routing to S3 (350KB)
S3_THRESHOLD_BYTES = 350 * 1024

# Exponential backoff configuration
MAX_RETRIES = 5
BASE_DELAY_MS = 100
MAX_DELAY_MS = 1600


class CheckpointSaver:
    """
    Abstraction layer for checkpoint persistence.
    
    Provides unified interface for checkpoint persistence with automatic
    mode detection (production vs development) and size-based routing
    (DynamoDB vs S3 for large checkpoints).
    """

    def __init__(self, mode: Optional[str] = None):
        """
        Initialize checkpoint saver with mode detection.
        
        Args:
            mode: "production" (DynamoDB) or "development" (in-memory).
                  If None, reads from CHECKPOINT_MODE environment variable.
                  Defaults to "development" if not specified.
        """
        # Detect mode from environment or parameter
        self.mode = mode or os.getenv("CHECKPOINT_MODE", "development")
        
        # Initialize appropriate backend
        if self.mode == "production":
            self._init_production_backend()
        else:
            self._init_development_backend()
        
        logger.info(f"CheckpointSaver initialized in {self.mode} mode")

    def _init_production_backend(self):
        """Initialize DynamoDB backend for production"""
        table_name = os.getenv("CHECKPOINT_TABLE_NAME", "SkyMarshalCheckpoints")
        region = os.getenv("AWS_REGION", "us-east-1")
        self.s3_bucket = os.getenv("CHECKPOINT_S3_BUCKET")
        
        try:
            # Initialize DynamoDB
            self.dynamodb = boto3.resource('dynamodb', region_name=region)
            self.table = self.dynamodb.Table(table_name)
            self.backend = "DynamoDB"
            logger.info(f"DynamoDB backend initialized: table={table_name}, region={region}")
            
            # Initialize S3 client if bucket configured
            if self.s3_bucket:
                self.s3_client = boto3.client('s3', region_name=region)
                logger.info(f"S3 client initialized: bucket={self.s3_bucket}")
            else:
                self.s3_client = None
                logger.warning("S3 bucket not configured - large checkpoints may fail")
                
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB backend: {e}")
            logger.warning("Falling back to in-memory backend")
            self._init_development_backend()

    def _init_development_backend(self):
        """Initialize in-memory backend for development"""
        self.backend = "InMemorySaver"
        self.memory_store = {}  # Simple in-memory dict
        self.s3_client = None
        self.s3_bucket = None
        logger.info("In-memory backend initialized for development")

    def _calculate_size(self, data: Any) -> int:
        """Calculate approximate size of data in bytes"""
        try:
            return sys.getsizeof(json.dumps(data))
        except Exception:
            # Fallback to rough estimate
            return len(str(data))

    async def _retry_with_backoff(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                
                # Calculate delay with exponential backoff and jitter
                delay_ms = min(BASE_DELAY_MS * (2 ** attempt), MAX_DELAY_MS)
                jitter_ms = delay_ms * 0.1  # 10% jitter
                import random
                total_delay = (delay_ms + random.uniform(-jitter_ms, jitter_ms)) / 1000
                
                logger.warning(f"Operation failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                logger.info(f"Retrying in {total_delay:.2f}s...")
                await asyncio.sleep(total_delay)

    async def _save_to_s3(self, thread_id: str, checkpoint_id: str, data: Dict[str, Any]) -> str:
        """Save large checkpoint to S3 and return reference"""
        if not self.s3_client or not self.s3_bucket:
            raise ValueError("S3 not configured for large checkpoint storage")
        
        s3_key = f"checkpoints/{thread_id}/{checkpoint_id}.json"
        
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=json.dumps(data),
                ContentType='application/json'
            )
            
            logger.info(f"Large checkpoint saved to S3: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint to S3: {e}")
            raise

    async def _load_from_s3(self, s3_key: str) -> Dict[str, Any]:
        """Load checkpoint from S3"""
        if not self.s3_client or not self.s3_bucket:
            raise ValueError("S3 not configured")
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=s3_key
            )
            
            data = json.loads(response['Body'].read())
            logger.debug(f"Checkpoint loaded from S3: s3://{self.s3_bucket}/{s3_key}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint from S3: {e}")
            raise

    async def save_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
        state: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save checkpoint to persistence layer with size-based routing.
        
        Small checkpoints (<350KB) go to DynamoDB.
        Large checkpoints (≥350KB) go to S3 with DynamoDB reference.
        
        Args:
            thread_id: Unique thread identifier
            checkpoint_id: Unique checkpoint identifier within thread
            state: Checkpoint state data
            metadata: Optional metadata (agent name, phase, confidence, etc.)
        """
        try:
            # Prepare checkpoint data
            timestamp = datetime.utcnow().isoformat()
            checkpoint_data = {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "state": state,
                "metadata": metadata or {},
                "timestamp": timestamp
            }
            
            if self.mode == "development":
                # In-memory storage
                key = f"{thread_id}#{checkpoint_id}"
                self.memory_store[key] = checkpoint_data
                logger.debug(f"Checkpoint saved to memory: {key}")
                return
            
            # Production mode - DynamoDB
            # Calculate size
            size_bytes = self._calculate_size(checkpoint_data)
            
            # Prepare DynamoDB item
            pk = f"THREAD#{thread_id}"
            sk = f"CHECKPOINT#{checkpoint_id}#{timestamp}"
            
            ttl_days = int(os.getenv("CHECKPOINT_TTL_DAYS", "90"))
            ttl = int((datetime.utcnow() + timedelta(days=ttl_days)).timestamp())
            
            # Generate version for optimistic locking
            import uuid
            version = str(uuid.uuid4())
            
            item = {
                "PK": pk,
                "SK": sk,
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "timestamp": timestamp,
                "ttl": ttl,
                "version": version  # For optimistic locking
            }
            
            # Route based on size
            if size_bytes >= S3_THRESHOLD_BYTES and self.s3_client:
                # Large checkpoint - save to S3
                logger.info(f"Checkpoint size {size_bytes} bytes exceeds threshold, routing to S3")
                
                try:
                    s3_key = await self._save_to_s3(thread_id, checkpoint_id, checkpoint_data)
                    
                    # Save reference in DynamoDB
                    item["s3_reference"] = s3_key
                    item["size_bytes"] = size_bytes
                    item["metadata"] = metadata or {}
                    
                except Exception as e:
                    logger.error(f"Failed to save large checkpoint to S3: {e}")
                    logger.warning("Falling back to in-memory storage for this checkpoint")
                    # Fallback to in-memory
                    key = f"{thread_id}#{checkpoint_id}"
                    self.memory_store[key] = checkpoint_data
                    return
            else:
                # Small checkpoint - save to DynamoDB
                item["state"] = state
                item["metadata"] = metadata or {}
            
            # Save to DynamoDB with conditional write to prevent overwrites
            # Use attribute_not_exists to ensure we don't overwrite existing checkpoints
            try:
                self.table.put_item(
                    Item=item,
                    ConditionExpression="attribute_not_exists(PK) AND attribute_not_exists(SK)"
                )
                logger.debug(f"Checkpoint saved: thread={thread_id}, checkpoint={checkpoint_id}, size={size_bytes}")
            except self.dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
                # Checkpoint already exists - this is expected for concurrent writes
                # Generate new timestamp to create unique checkpoint
                logger.warning(f"Checkpoint {checkpoint_id} already exists, creating new version")
                timestamp = datetime.utcnow().isoformat()
                sk = f"CHECKPOINT#{checkpoint_id}#{timestamp}"
                item["SK"] = sk
                item["timestamp"] = timestamp
                self.table.put_item(Item=item)
                logger.debug(f"Checkpoint saved with new timestamp: thread={thread_id}, checkpoint={checkpoint_id}")
            
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            # Fallback to in-memory
            if self.mode == "production":
                logger.warning("Falling back to in-memory storage")
                key = f"{thread_id}#{checkpoint_id}"
                self.memory_store[key] = checkpoint_data

    async def load_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint from persistence layer with transparent S3 retrieval.
        
        Automatically detects if checkpoint is stored in S3 and retrieves it.
        
        Args:
            thread_id: Unique thread identifier
            checkpoint_id: Optional specific checkpoint ID. If None, loads latest.
        
        Returns:
            Checkpoint data or None if not found
        """
        try:
            if self.mode == "development":
                # In-memory retrieval
                if checkpoint_id:
                    key = f"{thread_id}#{checkpoint_id}"
                    return self.memory_store.get(key)
                else:
                    # Get latest checkpoint for thread
                    matching = [v for k, v in self.memory_store.items() if k.startswith(f"{thread_id}#")]
                    if matching:
                        return sorted(matching, key=lambda x: x.get("timestamp", ""), reverse=True)[0]
                    return None
            
            # Production mode - DynamoDB
            pk = f"THREAD#{thread_id}"
            
            if checkpoint_id:
                # Query specific checkpoint
                response = self.table.query(
                    KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                    ExpressionAttributeValues={
                        ":pk": pk,
                        ":sk_prefix": f"CHECKPOINT#{checkpoint_id}#"
                    },
                    ScanIndexForward=False,
                    Limit=1
                )
            else:
                # Get latest checkpoint
                response = self.table.query(
                    KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                    ExpressionAttributeValues={
                        ":pk": pk,
                        ":sk_prefix": "CHECKPOINT#"
                    },
                    ScanIndexForward=False,
                    Limit=1
                )
            
            items = response.get('Items', [])
            if not items:
                logger.debug(f"No checkpoint found: thread={thread_id}, checkpoint={checkpoint_id}")
                return None
            
            item = items[0]
            
            # Check if this is an S3 reference
            if "s3_reference" in item:
                s3_key = item["s3_reference"]
                logger.debug(f"Loading checkpoint from S3: {s3_key}")
                
                try:
                    # Load actual data from S3
                    checkpoint_data = await self._load_from_s3(s3_key)
                    logger.debug(f"Checkpoint loaded from S3: thread={thread_id}, checkpoint={checkpoint_id}")
                    return checkpoint_data
                    
                except Exception as e:
                    logger.error(f"Failed to load checkpoint from S3: {e}")
                    return None
            
            # Regular DynamoDB checkpoint
            checkpoint_data = {
                "thread_id": item.get("thread_id"),
                "checkpoint_id": item.get("checkpoint_id"),
                "state": item.get("state", {}),
                "metadata": item.get("metadata", {}),
                "timestamp": item.get("timestamp")
            }
            
            logger.debug(f"Checkpoint loaded: thread={thread_id}, checkpoint={checkpoint_id}")
            return checkpoint_data
            
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    async def list_checkpoints(
        self,
        thread_id: str,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all checkpoints for a thread in chronological order.
        
        Args:
            thread_id: Unique thread identifier
            status_filter: Optional filter by thread status (active, completed, failed)
        
        Returns:
            List of checkpoint metadata dictionaries sorted by timestamp
        """
        try:
            if self.mode == "development":
                # In-memory retrieval
                checkpoints = [v for k, v in self.memory_store.items() if k.startswith(f"{thread_id}#")]
                
                # Apply status filter if specified
                if status_filter:
                    checkpoints = [c for c in checkpoints if c.get("metadata", {}).get("status") == status_filter]
                
                # Sort by timestamp
                checkpoints.sort(key=lambda x: x.get("timestamp", ""))
                
                logger.debug(f"Listed {len(checkpoints)} checkpoints for thread={thread_id}")
                return checkpoints
            
            # Production mode - DynamoDB
            pk = f"THREAD#{thread_id}"
            
            response = self.table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": pk,
                    ":sk_prefix": "CHECKPOINT#"
                },
                ScanIndexForward=True  # Chronological order
            )
            
            items = response.get('Items', [])
            
            # Convert to checkpoint metadata
            checkpoints = []
            for item in items:
                checkpoint = {
                    "thread_id": item.get("thread_id"),
                    "checkpoint_id": item.get("checkpoint_id"),
                    "timestamp": item.get("timestamp"),
                    "metadata": item.get("metadata", {}),
                    "has_s3_reference": "s3_reference" in item
                }
                
                # Apply status filter if specified
                if status_filter and checkpoint.get("metadata", {}).get("status") != status_filter:
                    continue
                
                checkpoints.append(checkpoint)
            
            logger.debug(f"Listed {len(checkpoints)} checkpoints for thread={thread_id}")
            return checkpoints
            
        except Exception as e:
            logger.error(f"Failed to list checkpoints: {e}")
            return []

    async def get_thread_history(
        self,
        thread_id: str,
        phase_filter: Optional[str] = None,
        agent_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get complete audit trail for a thread with full checkpoint data.
        
        Supports filtering by phase or agent for focused analysis.
        
        Args:
            thread_id: Unique thread identifier
            phase_filter: Optional filter by phase (phase1, phase2, phase3)
            agent_filter: Optional filter by agent name
        
        Returns:
            List of complete checkpoint records with state and metadata
        """
        try:
            checkpoints = await self.list_checkpoints(thread_id)
            
            # Load full data for each checkpoint
            history = []
            for checkpoint_meta in checkpoints:
                # Apply filters
                metadata = checkpoint_meta.get("metadata", {})
                
                if phase_filter and metadata.get("phase") != phase_filter:
                    continue
                
                if agent_filter and metadata.get("agent") != agent_filter:
                    continue
                
                checkpoint_id = checkpoint_meta.get("checkpoint_id")
                full_checkpoint = await self.load_checkpoint(thread_id, checkpoint_id)
                if full_checkpoint:
                    history.append(full_checkpoint)
            
            logger.debug(f"Retrieved history with {len(history)} checkpoints for thread={thread_id}")
            return history
            
        except Exception as e:
            logger.error(f"Failed to get thread history: {e}")
            return []
