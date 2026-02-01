"""
S3 Storage Module

This module provides functions for storing and retrieving decision records
to/from S3 buckets for historical learning and audit trails.

Key Features:
- Store decision records to multiple S3 buckets
- Date-partitioned storage (YYYY/MM/DD)
- Metadata tagging for easy retrieval
- Error handling and retry logic
"""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError

from agents.schemas import DecisionRecord

logger = logging.getLogger(__name__)

# S3 bucket names
KNOWLEDGE_BASE_BUCKET = "skymarshal-prod-knowledge-base-368613657554"
DECISIONS_BUCKET = "skymarshal-prod-decisions-368613657554"


async def store_decision_to_s3(
    decision_record: DecisionRecord,
    buckets: Optional[List[str]] = None
) -> Dict[str, bool]:
    """
    Store decision record to S3 buckets.
    
    This function stores a decision record to one or more S3 buckets with
    date partitioning and metadata tagging for easy retrieval and analysis.
    
    Args:
        decision_record: The decision record to store
        buckets: List of bucket names (defaults to both KB and decisions buckets)
        
    Returns:
        Dict mapping bucket name to success status
        
    Example:
        >>> record = DecisionRecord(...)
        >>> result = await store_decision_to_s3(record)
        >>> print(result)
        {
            "skymarshal-prod-knowledge-base-368613657554": True,
            "skymarshal-prod-decisions-368613657554": True
        }
    """
    if buckets is None:
        buckets = [KNOWLEDGE_BASE_BUCKET, DECISIONS_BUCKET]
    
    s3_client = boto3.client('s3')
    results = {}
    
    # Generate S3 key with date partitioning
    dt = datetime.fromisoformat(decision_record.timestamp)
    s3_key = f"decisions/{dt.year}/{dt.month:02d}/{dt.day:02d}/{decision_record.disruption_id}.json"
    
    # Convert to JSON
    record_json = json.dumps(decision_record.model_dump(), indent=2, default=str)
    
    # Upload to each bucket
    for bucket in buckets:
        try:
            s3_client.put_object(
                Bucket=bucket,
                Key=s3_key,
                Body=record_json,
                ContentType='application/json',
                Metadata={
                    'disruption_type': decision_record.disruption_type,
                    'flight_number': decision_record.flight_number,
                    'selected_solution': str(decision_record.selected_solution_id),
                    'human_override': str(decision_record.human_override)
                }
            )
            results[bucket] = True
            logger.info(f"Successfully stored decision record to {bucket}/{s3_key}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to store to {bucket}: {error_code} - {e}")
            results[bucket] = False
        except Exception as e:
            logger.error(f"Failed to store to {bucket}: {e}", exc_info=True)
            results[bucket] = False
    
    return results


async def load_decision_from_s3(
    disruption_id: str,
    bucket: str = DECISIONS_BUCKET,
    date_hint: Optional[datetime] = None
) -> Optional[DecisionRecord]:
    """
    Load a decision record from S3.
    
    Searches for a decision record by disruption_id. If date_hint is provided,
    searches that specific date partition first, otherwise searches all partitions.
    
    Args:
        disruption_id: The disruption ID to search for
        bucket: The S3 bucket to search in
        date_hint: Optional datetime hint for faster lookup
        
    Returns:
        DecisionRecord if found, None otherwise
        
    Example:
        >>> record = await load_decision_from_s3("DISR-2026-001")
        >>> if record:
        ...     print(f"Found decision for {record.flight_number}")
    """
    s3_client = boto3.client('s3')
    
    # If date hint provided, try that specific partition first
    if date_hint:
        s3_key = f"decisions/{date_hint.year}/{date_hint.month:02d}/{date_hint.day:02d}/{disruption_id}.json"
        try:
            response = s3_client.get_object(Bucket=bucket, Key=s3_key)
            record_json = response['Body'].read().decode('utf-8')
            record_dict = json.loads(record_json)
            return DecisionRecord(**record_dict)
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchKey':
                logger.error(f"Error loading from {bucket}/{s3_key}: {e}")
            # Fall through to search all partitions
    
    # Search all partitions (this could be slow for large datasets)
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix='decisions/')
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                if disruption_id in obj['Key']:
                    response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                    record_json = response['Body'].read().decode('utf-8')
                    record_dict = json.loads(record_json)
                    return DecisionRecord(**record_dict)
        
        logger.warning(f"Decision record not found for disruption_id: {disruption_id}")
        return None
        
    except Exception as e:
        logger.error(f"Error searching for decision record: {e}", exc_info=True)
        return None


async def list_decisions_by_date(
    start_date: datetime,
    end_date: datetime,
    bucket: str = DECISIONS_BUCKET
) -> List[DecisionRecord]:
    """
    List all decision records within a date range.
    
    Args:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        bucket: The S3 bucket to search in
        
    Returns:
        List of DecisionRecord objects
        
    Example:
        >>> from datetime import datetime, timedelta
        >>> end = datetime.now()
        >>> start = end - timedelta(days=7)
        >>> records = await list_decisions_by_date(start, end)
        >>> print(f"Found {len(records)} decisions in the last week")
    """
    s3_client = boto3.client('s3')
    records = []
    
    # Generate list of date partitions to search
    current_date = start_date
    while current_date <= end_date:
        prefix = f"decisions/{current_date.year}/{current_date.month:02d}/{current_date.day:02d}/"
        
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    try:
                        response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                        record_json = response['Body'].read().decode('utf-8')
                        record_dict = json.loads(record_json)
                        records.append(DecisionRecord(**record_dict))
                    except Exception as e:
                        logger.error(f"Error loading {obj['Key']}: {e}")
                        continue
        except Exception as e:
            logger.error(f"Error listing objects in {prefix}: {e}")
        
        # Move to next day
        from datetime import timedelta
        current_date += timedelta(days=1)
    
    return records


async def query_decisions_by_metadata(
    disruption_type: Optional[str] = None,
    flight_number: Optional[str] = None,
    human_override: Optional[bool] = None,
    bucket: str = DECISIONS_BUCKET
) -> List[DecisionRecord]:
    """
    Query decision records by metadata filters.
    
    Note: This function lists all objects and filters in memory, which may be
    slow for large datasets. Consider using AWS Athena or similar for production.
    
    Args:
        disruption_type: Filter by disruption type
        flight_number: Filter by flight number
        human_override: Filter by human override flag
        bucket: The S3 bucket to search in
        
    Returns:
        List of DecisionRecord objects matching the filters
        
    Example:
        >>> records = await query_decisions_by_metadata(
        ...     disruption_type="crew",
        ...     human_override=True
        ... )
        >>> print(f"Found {len(records)} crew disruptions with human overrides")
    """
    s3_client = boto3.client('s3')
    records = []
    
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket, Prefix='decisions/')
        
        for page in pages:
            if 'Contents' not in page:
                continue
                
            for obj in page['Contents']:
                try:
                    # Get object metadata
                    head_response = s3_client.head_object(Bucket=bucket, Key=obj['Key'])
                    metadata = head_response.get('Metadata', {})
                    
                    # Apply filters
                    if disruption_type and metadata.get('disruption_type') != disruption_type:
                        continue
                    if flight_number and metadata.get('flight_number') != flight_number:
                        continue
                    if human_override is not None:
                        override_str = str(human_override).lower()
                        if metadata.get('human_override', '').lower() != override_str:
                            continue
                    
                    # Load full record
                    response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                    record_json = response['Body'].read().decode('utf-8')
                    record_dict = json.loads(record_json)
                    records.append(DecisionRecord(**record_dict))
                    
                except Exception as e:
                    logger.error(f"Error processing {obj['Key']}: {e}")
                    continue
        
    except Exception as e:
        logger.error(f"Error querying decision records: {e}", exc_info=True)
    
    return records
