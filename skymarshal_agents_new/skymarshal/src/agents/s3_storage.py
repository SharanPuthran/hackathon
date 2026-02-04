"""
S3 Storage Module

This module provides functions for storing and retrieving decision records
to/from S3 buckets for historical learning and audit trails.

Key Features:
- Store decision records to multiple S3 buckets
- Date and time partitioned storage (YYYY/MM/DD/HH-MM-SS)
- Separate folders for agent decisions vs human overrides
- Metadata tagging for easy retrieval
- Error handling and retry logic

Folder Structure:
    s3://bucket/
    ├── agent-decisions/YYYY/MM/DD/HH-MM-SS/{flight}_{disruption_id}.json
    └── human-overrides/YYYY/MM/DD/HH-MM-SS/{flight}_{disruption_id}.json
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError

from agents.schemas import DecisionRecord

logger = logging.getLogger(__name__)

# S3 bucket names
KNOWLEDGE_BASE_BUCKET = "skymarshal-prod-knowledge-base-368613657554"
DECISIONS_BUCKET = "skymarshal-prod-decisions-368613657554"

# Folder prefixes for different record types
AGENT_DECISIONS_PREFIX = "agent-decisions"
HUMAN_OVERRIDES_PREFIX = "human-overrides"


def generate_s3_key(
    record_type: str,
    timestamp: str,
    flight_number: str,
    disruption_id: str
) -> str:
    """
    Generate S3 key with proper folder structure separating agent decisions from human overrides.

    Args:
        record_type: Either "agent_decision" or "human_override"
        timestamp: ISO 8601 timestamp
        flight_number: Flight number (e.g., EY123)
        disruption_id: Unique disruption identifier

    Returns:
        S3 key path: {folder}/YYYY/MM/DD/HH-MM-SS/{flight}_{disruption_id}.json

    Example:
        >>> key = generate_s3_key("agent_decision", "2026-02-04T10:30:45Z", "EY123", "DISR-001")
        >>> print(key)
        agent-decisions/2026/02/04/10-30-45/EY123_DISR-001.json
    """
    # Parse timestamp
    try:
        if timestamp.endswith('Z'):
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(timestamp)
    except ValueError:
        # Fallback to current time if parsing fails
        dt = datetime.now(timezone.utc)
        logger.warning(f"Failed to parse timestamp '{timestamp}', using current time")

    # Determine folder based on record type
    if record_type == "human_override":
        folder = HUMAN_OVERRIDES_PREFIX
    else:
        folder = AGENT_DECISIONS_PREFIX

    # Clean flight number (remove any special characters)
    clean_flight = flight_number.replace("/", "-").replace(" ", "_") if flight_number else "UNKNOWN"

    # Format: folder/YYYY/MM/DD/HH-MM-SS/flight_disruption.json
    return (
        f"{folder}/"
        f"{dt.year:04d}/{dt.month:02d}/{dt.day:02d}/"
        f"{dt.hour:02d}-{dt.minute:02d}-{dt.second:02d}/"
        f"{clean_flight}_{disruption_id}.json"
    )


async def store_decision_to_s3(
    decision_record: DecisionRecord,
    buckets: Optional[List[str]] = None
) -> Dict[str, bool]:
    """
    Store decision record to S3 buckets with proper folder structure.

    This function stores a decision record to one or more S3 buckets with
    date/time partitioning and separate folders for agent decisions vs human overrides.

    Folder Structure:
        - agent-decisions/YYYY/MM/DD/HH-MM-SS/{flight}_{disruption_id}.json
        - human-overrides/YYYY/MM/DD/HH-MM-SS/{flight}_{disruption_id}.json

    Args:
        decision_record: The decision record to store
        buckets: List of bucket names (defaults to decisions bucket only)

    Returns:
        Dict mapping bucket name to success status

    Example:
        >>> record = DecisionRecord(...)
        >>> result = await store_decision_to_s3(record)
        >>> print(result)
        {
            "skymarshal-prod-decisions-368613657554": True
        }
    """
    if buckets is None:
        buckets = [DECISIONS_BUCKET]

    s3_client = boto3.client('s3')
    results = {}

    # Determine record type based on human_override flag
    record_type = "human_override" if decision_record.human_override else "agent_decision"

    # Generate S3 key with new folder structure
    s3_key = generate_s3_key(
        record_type=record_type,
        timestamp=decision_record.timestamp,
        flight_number=decision_record.flight_number,
        disruption_id=decision_record.disruption_id
    )

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
                    'record_type': record_type,
                    'disruption_type': decision_record.disruption_type or 'unknown',
                    'flight_number': decision_record.flight_number or 'UNKNOWN',
                    'selected_solution': str(decision_record.selected_solution_id) if decision_record.selected_solution_id else 'none',
                    'human_override': str(decision_record.human_override)
                }
            )
            results[bucket] = True
            logger.info(f"Successfully stored {record_type} record to {bucket}/{s3_key}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(f"Failed to store to {bucket}: {error_code} - {e}")
            results[bucket] = False
        except Exception as e:
            logger.error(f"Failed to store to {bucket}: {e}", exc_info=True)
            results[bucket] = False

    return results


async def store_agent_decision(
    disruption_id: str,
    flight_number: str,
    disruption_type: str,
    selected_solution: Dict[str, Any],
    detailed_report: Dict[str, Any],
    session_id: Optional[str] = None,
    bucket: str = DECISIONS_BUCKET
) -> Dict[str, Any]:
    """
    Store an agent decision (AI solution selected by user) to S3.

    Args:
        disruption_id: Unique disruption identifier
        flight_number: Flight number (e.g., EY123)
        disruption_type: Type of disruption (mechanical, weather, crew, etc.)
        selected_solution: The solution object selected by the user
        detailed_report: Full report data including scores, impacts, recovery plan
        session_id: Optional session ID for context
        bucket: S3 bucket to store in

    Returns:
        Dict with storage result and S3 key
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build the record
    record = {
        "record_type": "agent_decision",
        "disruption_id": disruption_id,
        "timestamp": timestamp,
        "flight_number": flight_number,
        "disruption_type": disruption_type,
        "session_id": session_id,
        "selected_solution": selected_solution,
        "detailed_report": detailed_report,
        "recovery_executed": True,
        "execution_timestamp": timestamp
    }

    # Generate S3 key
    s3_key = generate_s3_key(
        record_type="agent_decision",
        timestamp=timestamp,
        flight_number=flight_number,
        disruption_id=disruption_id
    )

    s3_client = boto3.client('s3')

    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(record, indent=2, default=str),
            ContentType='application/json',
            Metadata={
                'record_type': 'agent_decision',
                'disruption_type': disruption_type,
                'flight_number': flight_number,
                'solution_id': str(selected_solution.get('solution_id', 'unknown'))
            }
        )
        logger.info(f"Successfully stored agent decision to {bucket}/{s3_key}")
        return {"success": True, "s3_key": s3_key, "bucket": bucket}
    except Exception as e:
        logger.error(f"Failed to store agent decision: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def store_human_override(
    disruption_id: str,
    flight_number: str,
    disruption_type: str,
    override_directive: str,
    rejected_solutions: Optional[List[Dict[str, Any]]] = None,
    session_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    bucket: str = DECISIONS_BUCKET
) -> Dict[str, Any]:
    """
    Store a human override directive to S3.

    Args:
        disruption_id: Unique disruption identifier
        flight_number: Flight number (e.g., EY123)
        disruption_type: Type of disruption (mechanical, weather, crew, etc.)
        override_directive: The human's override text/strategy
        rejected_solutions: List of solutions that were available but rejected
        session_id: Optional session ID for context
        context: Additional context (operator notes, etc.)
        bucket: S3 bucket to store in

    Returns:
        Dict with storage result and S3 key
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    # Build the record
    record = {
        "record_type": "human_override",
        "disruption_id": disruption_id,
        "timestamp": timestamp,
        "flight_number": flight_number,
        "disruption_type": disruption_type,
        "override_directive": override_directive,
        "rejected_solutions": rejected_solutions or [],
        "session_id": session_id,
        "context": context or {}
    }

    # Generate S3 key
    s3_key = generate_s3_key(
        record_type="human_override",
        timestamp=timestamp,
        flight_number=flight_number,
        disruption_id=disruption_id
    )

    s3_client = boto3.client('s3')

    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=json.dumps(record, indent=2, default=str),
            ContentType='application/json',
            Metadata={
                'record_type': 'human_override',
                'disruption_type': disruption_type,
                'flight_number': flight_number,
                'human_override': 'true'
            }
        )
        logger.info(f"Successfully stored human override to {bucket}/{s3_key}")
        return {"success": True, "s3_key": s3_key, "bucket": bucket}
    except Exception as e:
        logger.error(f"Failed to store human override: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def load_decision_from_s3(
    disruption_id: str,
    bucket: str = DECISIONS_BUCKET,
    date_hint: Optional[datetime] = None,
    record_type: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Load a decision record from S3.

    Searches for a decision record by disruption_id in both agent-decisions
    and human-overrides folders.

    Args:
        disruption_id: The disruption ID to search for
        bucket: The S3 bucket to search in
        date_hint: Optional datetime hint for faster lookup
        record_type: Optional filter: "agent_decision" or "human_override"

    Returns:
        Dict with record data if found, None otherwise

    Example:
        >>> record = await load_decision_from_s3("DISR-2026-001")
        >>> if record:
        ...     print(f"Found {record['record_type']} for {record['flight_number']}")
    """
    s3_client = boto3.client('s3')

    # Determine which prefixes to search
    prefixes = []
    if record_type == "agent_decision":
        prefixes = [AGENT_DECISIONS_PREFIX]
    elif record_type == "human_override":
        prefixes = [HUMAN_OVERRIDES_PREFIX]
    else:
        prefixes = [AGENT_DECISIONS_PREFIX, HUMAN_OVERRIDES_PREFIX]

    # Search in each prefix
    for prefix in prefixes:
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/")

            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    if disruption_id in obj['Key']:
                        response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                        record_json = response['Body'].read().decode('utf-8')
                        return json.loads(record_json)

        except Exception as e:
            logger.error(f"Error searching in {prefix}: {e}", exc_info=True)

    logger.warning(f"Decision record not found for disruption_id: {disruption_id}")
    return None


async def list_decisions_by_date(
    start_date: datetime,
    end_date: datetime,
    bucket: str = DECISIONS_BUCKET,
    record_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    List all decision records within a date range.

    Args:
        start_date: Start of date range (inclusive)
        end_date: End of date range (inclusive)
        bucket: The S3 bucket to search in
        record_type: Optional filter: "agent_decision" or "human_override"

    Returns:
        List of record dicts

    Example:
        >>> from datetime import datetime, timedelta
        >>> end = datetime.now()
        >>> start = end - timedelta(days=7)
        >>> records = await list_decisions_by_date(start, end)
        >>> print(f"Found {len(records)} decisions in the last week")
    """
    from datetime import timedelta

    s3_client = boto3.client('s3')
    records = []

    # Determine which prefixes to search
    prefixes = []
    if record_type == "agent_decision":
        prefixes = [AGENT_DECISIONS_PREFIX]
    elif record_type == "human_override":
        prefixes = [HUMAN_OVERRIDES_PREFIX]
    else:
        prefixes = [AGENT_DECISIONS_PREFIX, HUMAN_OVERRIDES_PREFIX]

    # Generate list of date partitions to search
    current_date = start_date
    while current_date <= end_date:
        for prefix in prefixes:
            search_prefix = f"{prefix}/{current_date.year}/{current_date.month:02d}/{current_date.day:02d}/"

            try:
                paginator = s3_client.get_paginator('list_objects_v2')
                pages = paginator.paginate(Bucket=bucket, Prefix=search_prefix)

                for page in pages:
                    if 'Contents' not in page:
                        continue

                    for obj in page['Contents']:
                        try:
                            response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                            record_json = response['Body'].read().decode('utf-8')
                            record_dict = json.loads(record_json)
                            records.append(record_dict)
                        except Exception as e:
                            logger.error(f"Error loading {obj['Key']}: {e}")
                            continue
            except Exception as e:
                logger.error(f"Error listing objects in {search_prefix}: {e}")

        current_date += timedelta(days=1)

    return records


async def query_decisions_by_metadata(
    disruption_type: Optional[str] = None,
    flight_number: Optional[str] = None,
    human_override: Optional[bool] = None,
    bucket: str = DECISIONS_BUCKET
) -> List[Dict[str, Any]]:
    """
    Query decision records by metadata filters.

    Note: This function lists all objects and filters in memory, which may be
    slow for large datasets. Consider using AWS Athena or similar for production.

    Args:
        disruption_type: Filter by disruption type
        flight_number: Filter by flight number
        human_override: Filter by human override flag (True = human-overrides folder)
        bucket: The S3 bucket to search in

    Returns:
        List of record dicts matching the filters

    Example:
        >>> records = await query_decisions_by_metadata(
        ...     disruption_type="crew",
        ...     human_override=True
        ... )
        >>> print(f"Found {len(records)} crew disruptions with human overrides")
    """
    s3_client = boto3.client('s3')
    records = []

    # Determine which prefixes to search based on human_override filter
    prefixes = []
    if human_override is True:
        prefixes = [HUMAN_OVERRIDES_PREFIX]
    elif human_override is False:
        prefixes = [AGENT_DECISIONS_PREFIX]
    else:
        prefixes = [AGENT_DECISIONS_PREFIX, HUMAN_OVERRIDES_PREFIX]

    for prefix in prefixes:
        try:
            paginator = s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=bucket, Prefix=f"{prefix}/")

            for page in pages:
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    try:
                        # Get object metadata for fast filtering
                        head_response = s3_client.head_object(Bucket=bucket, Key=obj['Key'])
                        metadata = head_response.get('Metadata', {})

                        # Apply filters
                        if disruption_type and metadata.get('disruption_type') != disruption_type:
                            continue
                        if flight_number and metadata.get('flight_number') != flight_number:
                            continue

                        # Load full record
                        response = s3_client.get_object(Bucket=bucket, Key=obj['Key'])
                        record_json = response['Body'].read().decode('utf-8')
                        record_dict = json.loads(record_json)
                        records.append(record_dict)

                    except Exception as e:
                        logger.error(f"Error processing {obj['Key']}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error querying in {prefix}: {e}", exc_info=True)

    return records
