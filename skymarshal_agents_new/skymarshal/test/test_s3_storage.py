"""
Unit tests for S3 storage module.

Tests the S3 storage functionality for decision records including:
- Storing decision records to S3 buckets
- S3 key generation with date partitioning
- Metadata tagging
- Error handling for bucket failures
- Loading decision records from S3
- Querying decisions by date range and metadata

Uses moto library to mock AWS S3 service for testing.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_aws

from agents.schemas import DecisionRecord, RecoverySolution, RecoveryPlan, RecoveryStep
from agents.s3_storage import (
    store_decision_to_s3,
    load_decision_from_s3,
    list_decisions_by_date,
    query_decisions_by_metadata,
    KNOWLEDGE_BASE_BUCKET,
    DECISIONS_BUCKET
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_decision_record():
    """Create a sample decision record for testing."""
    recovery_step = RecoveryStep(
        step_number=1,
        step_name="Notify Crew",
        description="Notify crew of schedule change",
        responsible_agent="crew_scheduling",
        dependencies=[],
        estimated_duration="15 minutes",
        automation_possible=True,
        action_type="notify",
        parameters={"crew_ids": ["C001", "C002"]},
        success_criteria="Crew acknowledged notification"
    )
    
    recovery_plan = RecoveryPlan(
        solution_id=1,
        total_steps=1,
        estimated_total_duration="15 minutes",
        steps=[recovery_step],
        critical_path=[1],
        contingency_plans=[]
    )
    
    solution = RecoverySolution(
        solution_id=1,
        title="Conservative Safety-First Approach",
        description="Delay flight to allow full crew rest",
        recommendations=["Delay flight 10 hours", "Arrange crew rest facilities"],
        safety_compliance="Full compliance with FDP regulations",
        passenger_impact={"affected_count": 180, "delay_hours": 10, "cancellation_flag": False},
        financial_impact={"total_cost": 180000, "breakdown": {"crew": 50000, "passenger": 130000}},
        network_impact={"downstream_flights": 3, "connection_misses": 12},
        safety_score=100.0,
        cost_score=40.0,
        passenger_score=55.0,
        network_score=50.0,
        composite_score=69.0,  # 100*0.4 + 40*0.2 + 55*0.2 + 50*0.2 = 69.0
        pros=["Full regulatory compliance", "Zero safety risk"],
        cons=["High cost", "Significant passenger impact"],
        risks=["Potential customer dissatisfaction"],
        confidence=0.95,
        estimated_duration="10 hours",
        recovery_plan=recovery_plan
    )
    
    return DecisionRecord(
        disruption_id="DISR-2026-001",
        timestamp=datetime(2026, 1, 20, 10, 30, 0, tzinfo=timezone.utc).isoformat(),
        flight_number="EY123",
        disruption_type="crew",
        disruption_severity="high",
        agent_responses={
            "crew_compliance": {"recommendation": "Delay required"},
            "maintenance": {"recommendation": "Aircraft serviceable"}
        },
        solution_options=[solution],
        recommended_solution_id=1,
        conflicts_identified=[],
        conflict_resolutions=[],
        selected_solution_id=1,
        selection_rationale="Best balance of safety and cost",
        human_override=False
    )


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client with moto."""
    with mock_aws():
        # Create S3 client
        s3 = boto3.client('s3', region_name='us-east-1')
        
        # Create test buckets
        s3.create_bucket(Bucket=KNOWLEDGE_BASE_BUCKET)
        s3.create_bucket(Bucket=DECISIONS_BUCKET)
        
        yield s3


# ============================================================================
# S3 Key Generation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_s3_key_format(sample_decision_record, mock_s3_client):
    """
    Test S3 key generation follows correct format with date partitioning.
    
    Validates: Requirements 4.4
    """
    # Store decision record
    result = await store_decision_to_s3(sample_decision_record)
    
    # Verify storage succeeded
    assert result[KNOWLEDGE_BASE_BUCKET] is True
    assert result[DECISIONS_BUCKET] is True
    
    # Verify S3 key format: decisions/YYYY/MM/DD/disruption_id.json
    expected_key = "decisions/2026/01/20/DISR-2026-001.json"
    
    # Check object exists in both buckets
    for bucket in [KNOWLEDGE_BASE_BUCKET, DECISIONS_BUCKET]:
        response = mock_s3_client.head_object(Bucket=bucket, Key=expected_key)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200


@pytest.mark.asyncio
async def test_s3_key_date_partitioning(sample_decision_record, mock_s3_client):
    """
    Test S3 keys are correctly partitioned by date.
    
    Validates: Requirements 4.4
    """
    # Create records for different dates
    records = []
    for day in range(1, 4):
        record = sample_decision_record.model_copy()
        record.disruption_id = f"DISR-2026-00{day}"
        record.timestamp = datetime(2026, 1, day, 10, 0, 0, tzinfo=timezone.utc).isoformat()
        records.append(record)
    
    # Store all records
    for record in records:
        await store_decision_to_s3(record)
    
    # Verify each record is in correct date partition
    for day, record in enumerate(records, start=1):
        expected_key = f"decisions/2026/01/{day:02d}/DISR-2026-00{day}.json"
        response = mock_s3_client.head_object(Bucket=DECISIONS_BUCKET, Key=expected_key)
        assert response['ResponseMetadata']['HTTPStatusCode'] == 200


# ============================================================================
# Metadata Tagging Tests
# ============================================================================

@pytest.mark.asyncio
async def test_metadata_tagging(sample_decision_record, mock_s3_client):
    """
    Test S3 objects are tagged with correct metadata.
    
    Validates: Requirements 4.5
    """
    # Store decision record
    await store_decision_to_s3(sample_decision_record)
    
    # Retrieve object metadata
    key = "decisions/2026/01/20/DISR-2026-001.json"
    response = mock_s3_client.head_object(Bucket=DECISIONS_BUCKET, Key=key)
    
    # Verify metadata
    metadata = response['Metadata']
    assert metadata['disruption_type'] == "crew"
    assert metadata['flight_number'] == "EY123"
    assert metadata['selected_solution'] == "1"
    assert metadata['human_override'] == "False"


@pytest.mark.asyncio
async def test_human_override_flag_consistency(sample_decision_record, mock_s3_client):
    """
    Test human_override flag is correctly set in metadata.
    
    Validates: Requirements 4.6 (Property 19)
    """
    # Test case 1: No override (selected = recommended)
    record1 = sample_decision_record.model_copy()
    record1.disruption_id = "DISR-2026-001"
    record1.recommended_solution_id = 1
    record1.selected_solution_id = 1
    record1.human_override = False
    
    await store_decision_to_s3(record1)
    
    key1 = "decisions/2026/01/20/DISR-2026-001.json"
    response1 = mock_s3_client.head_object(Bucket=DECISIONS_BUCKET, Key=key1)
    assert response1['Metadata']['human_override'] == "False"
    
    # Test case 2: Override (selected != recommended)
    record2 = sample_decision_record.model_copy()
    record2.disruption_id = "DISR-2026-002"
    record2.timestamp = datetime(2026, 1, 21, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    record2.recommended_solution_id = 1
    record2.selected_solution_id = 2
    record2.human_override = True
    
    # Add second solution
    solution2 = record2.solution_options[0].model_copy()
    solution2.solution_id = 2
    solution2.title = "Alternative Solution"
    record2.solution_options.append(solution2)
    
    await store_decision_to_s3(record2)
    
    key2 = "decisions/2026/01/21/DISR-2026-002.json"
    response2 = mock_s3_client.head_object(Bucket=DECISIONS_BUCKET, Key=key2)
    assert response2['Metadata']['human_override'] == "True"


# ============================================================================
# Storage Error Handling Tests
# ============================================================================

@pytest.mark.asyncio
async def test_storage_error_handling_bucket_not_found(sample_decision_record):
    """
    Test error handling when S3 bucket doesn't exist.
    
    Validates: Requirements 4.7
    """
    # Don't use mock - let it fail naturally
    with patch('agents.s3_storage.boto3.client') as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        
        # Simulate NoSuchBucket error
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}}
        mock_s3.put_object.side_effect = ClientError(error_response, 'PutObject')
        
        # Store should handle error gracefully
        result = await store_decision_to_s3(sample_decision_record)
        
        # Verify both buckets failed
        assert result[KNOWLEDGE_BASE_BUCKET] is False
        assert result[DECISIONS_BUCKET] is False


@pytest.mark.asyncio
async def test_storage_partial_failure(sample_decision_record):
    """
    Test handling of partial storage failure (one bucket succeeds, one fails).
    
    Validates: Requirements 4.7
    """
    with patch('agents.s3_storage.boto3.client') as mock_boto:
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        
        # First call succeeds, second fails
        from botocore.exceptions import ClientError
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}}
        mock_s3.put_object.side_effect = [
            None,  # First bucket succeeds
            ClientError(error_response, 'PutObject')  # Second bucket fails
        ]
        
        # Store should handle partial failure
        result = await store_decision_to_s3(sample_decision_record)
        
        # Verify one succeeded, one failed
        assert len([v for v in result.values() if v is True]) == 1
        assert len([v for v in result.values() if v is False]) == 1


# ============================================================================
# Loading and Querying Tests
# ============================================================================

@pytest.mark.asyncio
async def test_load_decision_from_s3(sample_decision_record, mock_s3_client):
    """
    Test loading a decision record from S3.
    
    Validates: Requirements 5.1-5.3
    """
    # Store decision record
    await store_decision_to_s3(sample_decision_record)
    
    # Load it back
    loaded_record = await load_decision_from_s3(
        "DISR-2026-001",
        date_hint=datetime(2026, 1, 20, tzinfo=timezone.utc)
    )
    
    # Verify loaded record matches original
    assert loaded_record is not None
    assert loaded_record.disruption_id == sample_decision_record.disruption_id
    assert loaded_record.flight_number == sample_decision_record.flight_number
    assert loaded_record.disruption_type == sample_decision_record.disruption_type


@pytest.mark.asyncio
async def test_load_decision_not_found(mock_s3_client):
    """
    Test loading a non-existent decision record returns None.
    
    Validates: Requirements 5.4
    """
    loaded_record = await load_decision_from_s3("NONEXISTENT-ID")
    assert loaded_record is None


@pytest.mark.asyncio
async def test_list_decisions_by_date(sample_decision_record, mock_s3_client):
    """
    Test listing decisions within a date range.
    
    Validates: Requirements 5.5-5.7
    """
    # Create records for multiple days
    for day in range(18, 23):
        record = sample_decision_record.model_copy()
        record.disruption_id = f"DISR-2026-{day:03d}"
        record.timestamp = datetime(2026, 1, day, 10, 0, 0, tzinfo=timezone.utc).isoformat()
        await store_decision_to_s3(record)
    
    # Query date range
    start_date = datetime(2026, 1, 19, tzinfo=timezone.utc)
    end_date = datetime(2026, 1, 21, tzinfo=timezone.utc)
    
    records = await list_decisions_by_date(start_date, end_date)
    
    # Should return 3 records (19, 20, 21)
    assert len(records) == 3
    assert all(r.disruption_id in ["DISR-2026-019", "DISR-2026-020", "DISR-2026-021"] for r in records)


@pytest.mark.asyncio
async def test_query_decisions_by_metadata(sample_decision_record, mock_s3_client):
    """
    Test querying decisions by metadata filters.
    
    Validates: Requirements 5.8-5.9
    """
    # Create records with different metadata
    records_data = [
        ("DISR-2026-001", "crew", "EY123", False),
        ("DISR-2026-002", "crew", "EY456", True),
        ("DISR-2026-003", "maintenance", "EY123", False),
        ("DISR-2026-004", "weather", "EY789", False),
    ]
    
    for disruption_id, disruption_type, flight_number, human_override in records_data:
        record = sample_decision_record.model_copy()
        record.disruption_id = disruption_id
        record.disruption_type = disruption_type
        record.flight_number = flight_number
        record.human_override = human_override
        await store_decision_to_s3(record)
    
    # Query by disruption type
    crew_records = await query_decisions_by_metadata(disruption_type="crew")
    assert len(crew_records) == 2
    assert all(r.disruption_type == "crew" for r in crew_records)
    
    # Query by flight number
    ey123_records = await query_decisions_by_metadata(flight_number="EY123")
    assert len(ey123_records) == 2
    assert all(r.flight_number == "EY123" for r in ey123_records)
    
    # Query by human override
    override_records = await query_decisions_by_metadata(human_override=True)
    assert len(override_records) == 1
    assert override_records[0].human_override is True
    
    # Query with multiple filters
    crew_ey123_records = await query_decisions_by_metadata(
        disruption_type="crew",
        flight_number="EY123"
    )
    assert len(crew_ey123_records) == 1
    assert crew_ey123_records[0].disruption_id == "DISR-2026-001"


# ============================================================================
# Content Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_stored_content_is_valid_json(sample_decision_record, mock_s3_client):
    """
    Test stored content is valid JSON and can be deserialized.
    
    Validates: Requirements 4.1-4.3
    """
    # Store decision record
    await store_decision_to_s3(sample_decision_record)
    
    # Retrieve raw content
    key = "decisions/2026/01/20/DISR-2026-001.json"
    response = mock_s3_client.get_object(Bucket=DECISIONS_BUCKET, Key=key)
    content = response['Body'].read().decode('utf-8')
    
    # Verify it's valid JSON
    data = json.loads(content)
    assert isinstance(data, dict)
    assert data['disruption_id'] == "DISR-2026-001"
    assert data['flight_number'] == "EY123"
    
    # Verify it can be deserialized to DecisionRecord
    record = DecisionRecord(**data)
    assert record.disruption_id == sample_decision_record.disruption_id


@pytest.mark.asyncio
async def test_stored_content_preserves_all_fields(sample_decision_record, mock_s3_client):
    """
    Test all fields are preserved when storing and loading.
    
    Validates: Requirements 4.1-4.3
    """
    # Store decision record
    await store_decision_to_s3(sample_decision_record)
    
    # Load it back
    loaded_record = await load_decision_from_s3(
        "DISR-2026-001",
        date_hint=datetime(2026, 1, 20, tzinfo=timezone.utc)
    )
    
    # Verify all fields match
    assert loaded_record.disruption_id == sample_decision_record.disruption_id
    assert loaded_record.timestamp == sample_decision_record.timestamp
    assert loaded_record.flight_number == sample_decision_record.flight_number
    assert loaded_record.disruption_type == sample_decision_record.disruption_type
    assert loaded_record.disruption_severity == sample_decision_record.disruption_severity
    assert loaded_record.recommended_solution_id == sample_decision_record.recommended_solution_id
    assert loaded_record.selected_solution_id == sample_decision_record.selected_solution_id
    assert loaded_record.human_override == sample_decision_record.human_override
    assert len(loaded_record.solution_options) == len(sample_decision_record.solution_options)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
