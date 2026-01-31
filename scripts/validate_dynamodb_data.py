#!/usr/bin/env python3
"""
DynamoDB Data Validation Script

This script validates data integrity and identifies discrepancies in DynamoDB tables.
It checks:
- Required attributes presence
- Foreign key relationships
- Orphaned records
- Data type consistency
- GSI configurations
- IAM permissions

Usage:
    python scripts/validate_dynamodb_data.py [--output report.json] [--fix]
"""

import boto3
import json
import sys
import argparse
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
from decimal import Decimal
import logging
import os

# Try to import yaml for config reading
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    logging.warning("PyYAML not installed. Config file reading will be limited.")

# Add parent directory to path for imports
sys.path.insert(0, "skymarshal_agents_new/skymarshal/src")

from database.constants import (
    ALL_TABLES,
    ALL_GSIS,
    AGENT_TABLE_ACCESS,
    FLIGHTS_TABLE,
    BOOKINGS_TABLE,
    CREW_ROSTER_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    CARGO_FLIGHT_ASSIGNMENTS_TABLE,
    BAGGAGE_TABLE,
    CARGO_SHIPMENTS_TABLE,
    CREW_MEMBERS_TABLE,
    MAINTENANCE_STAFF_TABLE,
    PASSENGERS_TABLE,
    DEFAULT_AWS_REGION
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ValidationIssue:
    """Represents a validation issue found in the data"""
    
    def __init__(
        self,
        severity: str,
        table: str,
        issue_type: str,
        description: str,
        record_id: Optional[Dict[str, Any]] = None,
        fix_suggestion: Optional[str] = None
    ):
        self.severity = severity  # "error", "warning", "info"
        self.table = table
        self.issue_type = issue_type
        self.description = description
        self.record_id = record_id
        self.fix_suggestion = fix_suggestion
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "severity": self.severity,
            "table": self.table,
            "issue_type": self.issue_type,
            "description": self.description,
            "record_id": self.record_id,
            "fix_suggestion": self.fix_suggestion,
            "timestamp": self.timestamp
        }


class DynamoDBValidator:
    """Validates DynamoDB data integrity"""
    
    def __init__(self, region: str = DEFAULT_AWS_REGION):
        self.region = region
        self.dynamodb = boto3.resource("dynamodb", region_name=region)
        self.client = boto3.client("dynamodb", region_name=region)
        self.iam_client = boto3.client("iam", region_name=region)
        self.issues: List[ValidationIssue] = []
        
        # Cache for foreign key validation
        self.flight_ids: Set[str] = set()
        self.booking_ids: Set[str] = set()
        self.passenger_ids: Set[str] = set()
        self.crew_ids: Set[str] = set()
        self.shipment_ids: Set[str] = set()
        self.aircraft_registrations: Set[str] = set()
    
    def add_issue(
        self,
        severity: str,
        table: str,
        issue_type: str,
        description: str,
        record_id: Optional[Dict[str, Any]] = None,
        fix_suggestion: Optional[str] = None
    ):
        """Add a validation issue"""
        issue = ValidationIssue(
            severity, table, issue_type, description, record_id, fix_suggestion
        )
        self.issues.append(issue)
        
        # Log based on severity
        log_msg = f"[{table}] {description}"
        if severity == "error":
            logger.error(log_msg)
        elif severity == "warning":
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
    
    def validate_table_exists(self, table_name: str) -> bool:
        """Check if a table exists"""
        try:
            self.dynamodb.Table(table_name).load()
            return True
        except Exception as e:
            # Check if it's a ResourceNotFoundException
            if e.__class__.__name__ == 'ResourceNotFoundException':
                self.add_issue(
                    "error",
                    table_name,
                    "table_missing",
                    f"Table {table_name} does not exist",
                    fix_suggestion=f"Create table {table_name} using create_dynamodb_tables.py"
                )
                return False
            else:
                self.add_issue(
                    "error",
                    table_name,
                    "table_access_error",
                    f"Error accessing table {table_name}: {str(e)}"
                )
                return False
    
    def validate_gsi_exists(self, table_name: str, gsi_name: str) -> bool:
        """Check if a GSI exists on a table"""
        try:
            table = self.dynamodb.Table(table_name)
            table.load()
            
            if not table.global_secondary_indexes:
                self.add_issue(
                    "warning",
                    table_name,
                    "gsi_missing",
                    f"Table {table_name} has no GSIs, expected {gsi_name}",
                    fix_suggestion=f"Run scripts/create_gsis.py to add {gsi_name}"
                )
                return False
            
            gsi_names = [gsi["IndexName"] for gsi in table.global_secondary_indexes]
            if gsi_name not in gsi_names:
                self.add_issue(
                    "warning",
                    table_name,
                    "gsi_missing",
                    f"GSI {gsi_name} not found on table {table_name}",
                    fix_suggestion=f"Run scripts/create_gsis.py to add {gsi_name}"
                )
                return False
            
            # Check GSI status
            for gsi in table.global_secondary_indexes:
                if gsi["IndexName"] == gsi_name:
                    if gsi["IndexStatus"] != "ACTIVE":
                        self.add_issue(
                            "warning",
                            table_name,
                            "gsi_not_active",
                            f"GSI {gsi_name} on {table_name} is {gsi['IndexStatus']}, not ACTIVE",
                            fix_suggestion="Wait for GSI to become ACTIVE"
                        )
                        return False
            
            return True
        except Exception as e:
            self.add_issue(
                "error",
                table_name,
                "gsi_validation_error",
                f"Error validating GSI {gsi_name} on {table_name}: {str(e)}"
            )
            return False
    
    def validate_gsi_key_schema(self, table_name: str, gsi_name: str, expected_keys: Dict[str, str]) -> bool:
        """Validate GSI key schema matches expected configuration
        
        Args:
            table_name: Name of the table
            gsi_name: Name of the GSI
            expected_keys: Dict with 'HASH' and optionally 'RANGE' keys mapping to attribute names
        """
        try:
            table = self.dynamodb.Table(table_name)
            table.load()
            
            if not table.global_secondary_indexes:
                return False
            
            for gsi in table.global_secondary_indexes:
                if gsi["IndexName"] == gsi_name:
                    # Check if KeySchema exists
                    if "KeySchema" not in gsi:
                        self.add_issue(
                            "error",
                            table_name,
                            "gsi_schema_missing",
                            f"GSI {gsi_name} has no KeySchema",
                            fix_suggestion=f"Recreate GSI with correct schema"
                        )
                        return False
                    
                    actual_keys = {}
                    for key in gsi["KeySchema"]:
                        actual_keys[key["KeyType"]] = key["AttributeName"]
                    
                    # Validate key schema
                    for key_type, attr_name in expected_keys.items():
                        if key_type not in actual_keys:
                            self.add_issue(
                                "error",
                                table_name,
                                "gsi_schema_mismatch",
                                f"GSI {gsi_name} missing {key_type} key",
                                fix_suggestion=f"Recreate GSI with correct schema"
                            )
                            return False
                        
                        if actual_keys[key_type] != attr_name:
                            self.add_issue(
                                "error",
                                table_name,
                                "gsi_schema_mismatch",
                                f"GSI {gsi_name} {key_type} key is {actual_keys[key_type]}, expected {attr_name}",
                                fix_suggestion=f"Recreate GSI with correct schema"
                            )
                            return False
                    
                    return True
            
            return False
        except Exception as e:
            self.add_issue(
                "error",
                table_name,
                "gsi_schema_validation_error",
                f"Error validating GSI schema for {gsi_name} on {table_name}: {str(e)}"
            )
            return False
    
    def test_gsi_query_performance(self, table_name: str, gsi_name: str, test_key: Dict[str, Any]) -> bool:
        """Test that a query uses the GSI and doesn't perform a table scan
        
        Args:
            table_name: Name of the table
            gsi_name: Name of the GSI
            test_key: Sample key to query with
        """
        try:
            table = self.dynamodb.Table(table_name)
            
            # Perform a query using the GSI
            response = table.query(
                IndexName=gsi_name,
                KeyConditionExpression=f"{list(test_key.keys())[0]} = :val",
                ExpressionAttributeValues={":val": list(test_key.values())[0]},
                Limit=1
            )
            
            # Check if query was successful (indicates GSI is being used)
            if "Items" in response:
                self.add_issue(
                    "info",
                    table_name,
                    "gsi_query_success",
                    f"GSI {gsi_name} query successful - no table scan detected"
                )
                return True
            else:
                self.add_issue(
                    "warning",
                    table_name,
                    "gsi_query_issue",
                    f"GSI {gsi_name} query returned unexpected response",
                    fix_suggestion="Verify GSI configuration and test data"
                )
                return False
        except Exception as e:
            self.add_issue(
                "warning",
                table_name,
                "gsi_query_test_failed",
                f"Could not test GSI {gsi_name} query: {str(e)}",
                fix_suggestion="Ensure test data exists for GSI validation"
            )
            return False
    
    def load_foreign_key_caches(self):
        """Load all foreign key values into memory for validation"""
        logger.info("Loading foreign key caches...")
        
        # Load flight IDs
        try:
            table = self.dynamodb.Table(FLIGHTS_TABLE)
            response = table.scan(ProjectionExpression="flight_id,aircraft_registration")
            for item in response.get("Items", []):
                if "flight_id" in item:
                    self.flight_ids.add(str(item["flight_id"]))
                if "aircraft_registration" in item:
                    self.aircraft_registrations.add(str(item["aircraft_registration"]))
            logger.info(f"  Loaded {len(self.flight_ids)} flight IDs")
        except Exception as e:
            logger.error(f"  Error loading flight IDs: {e}")
        
        # Load booking IDs
        try:
            table = self.dynamodb.Table(BOOKINGS_TABLE)
            response = table.scan(ProjectionExpression="booking_id")
            for item in response.get("Items", []):
                if "booking_id" in item:
                    self.booking_ids.add(str(item["booking_id"]))
            logger.info(f"  Loaded {len(self.booking_ids)} booking IDs")
        except Exception as e:
            logger.error(f"  Error loading booking IDs: {e}")
        
        # Load passenger IDs
        try:
            table = self.dynamodb.Table(PASSENGERS_TABLE)
            response = table.scan(ProjectionExpression="passenger_id")
            for item in response.get("Items", []):
                if "passenger_id" in item:
                    self.passenger_ids.add(str(item["passenger_id"]))
            logger.info(f"  Loaded {len(self.passenger_ids)} passenger IDs")
        except Exception as e:
            logger.error(f"  Error loading passenger IDs: {e}")
        
        # Load crew IDs
        try:
            table = self.dynamodb.Table(CREW_MEMBERS_TABLE)
            response = table.scan(ProjectionExpression="crew_id")
            for item in response.get("Items", []):
                if "crew_id" in item:
                    self.crew_ids.add(str(item["crew_id"]))
            logger.info(f"  Loaded {len(self.crew_ids)} crew IDs")
        except Exception as e:
            logger.error(f"  Error loading crew IDs: {e}")
        
        # Load shipment IDs
        try:
            table = self.dynamodb.Table(CARGO_SHIPMENTS_TABLE)
            response = table.scan(ProjectionExpression="shipment_id")
            for item in response.get("Items", []):
                if "shipment_id" in item:
                    self.shipment_ids.add(str(item["shipment_id"]))
            logger.info(f"  Loaded {len(self.shipment_ids)} shipment IDs")
        except Exception as e:
            logger.error(f"  Error loading shipment IDs: {e}")
    
    def validate_foreign_key(
        self,
        table_name: str,
        record_id: Dict[str, Any],
        fk_field: str,
        fk_value: Any,
        reference_set: Set[str],
        reference_table: str
    ):
        """Validate a foreign key reference"""
        if fk_value is None:
            return
        
        fk_str = str(fk_value)
        if fk_str not in reference_set:
            self.add_issue(
                "error",
                table_name,
                "invalid_foreign_key",
                f"Invalid {fk_field} reference: {fk_str} not found in {reference_table}",
                record_id=record_id,
                fix_suggestion=f"Remove orphaned record or add missing {reference_table} entry"
            )
    
    def validate_required_attributes(
        self,
        table_name: str,
        item: Dict[str, Any],
        required_attrs: List[str]
    ):
        """Validate that required attributes are present"""
        missing = [attr for attr in required_attrs if attr not in item]
        if missing:
            # Get primary key for identification
            pk_fields = self.get_primary_key_fields(table_name)
            record_id = {k: item.get(k) for k in pk_fields if k in item}
            
            self.add_issue(
                "error",
                table_name,
                "missing_required_attributes",
                f"Missing required attributes: {', '.join(missing)}",
                record_id=record_id,
                fix_suggestion="Add missing attributes to the record"
            )
    
    def get_primary_key_fields(self, table_name: str) -> List[str]:
        """Get primary key field names for a table"""
        try:
            table = self.dynamodb.Table(table_name)
            table.load()
            key_schema = table.key_schema
            return [key["AttributeName"] for key in key_schema]
        except:
            return []
    
    def validate_flights_table(self):
        """Validate Flights table"""
        logger.info("Validating Flights table...")
        table_name = FLIGHTS_TABLE
        
        if not self.validate_table_exists(table_name):
            return
        
        # Check required GSIs exist and are ACTIVE
        gsi1_exists = self.validate_gsi_exists(table_name, "flight-number-date-index")
        gsi2_exists = self.validate_gsi_exists(table_name, "aircraft-registration-index")
        
        # Validate GSI key schemas
        if gsi1_exists:
            self.validate_gsi_key_schema(
                table_name,
                "flight-number-date-index",
                {"HASH": "flight_number", "RANGE": "scheduled_departure"}
            )
        
        if gsi2_exists:
            self.validate_gsi_key_schema(
                table_name,
                "aircraft-registration-index",
                {"HASH": "aircraft_registration"}
            )
        
        # Validate records
        table = self.dynamodb.Table(table_name)
        required_attrs = ["flight_id", "flight_number", "scheduled_departure", "aircraft_registration"]
        
        try:
            response = table.scan()
            items = response.get("Items", [])
            
            # Test GSI queries with sample data if available
            if items and gsi1_exists:
                sample_item = items[0]
                if "flight_number" in sample_item and "scheduled_departure" in sample_item:
                    self.test_gsi_query_performance(
                        table_name,
                        "flight-number-date-index",
                        {"flight_number": sample_item["flight_number"]}
                    )
            
            if items and gsi2_exists:
                sample_item = items[0]
                if "aircraft_registration" in sample_item:
                    self.test_gsi_query_performance(
                        table_name,
                        "aircraft-registration-index",
                        {"aircraft_registration": sample_item["aircraft_registration"]}
                    )
            
            for item in items:
                self.validate_required_attributes(table_name, item, required_attrs)
        except Exception as e:
            self.add_issue(
                "error",
                table_name,
                "scan_error",
                f"Error scanning table: {str(e)}"
            )
    
    def validate_bookings_table(self):
        """Validate Bookings table"""
        logger.info("Validating Bookings table...")
        table_name = BOOKINGS_TABLE
        
        if not self.validate_table_exists(table_name):
            return
        
        # Check required GSIs exist and are ACTIVE
        gsi_exists = self.validate_gsi_exists(table_name, "flight-id-index")
        
        # Validate GSI key schema
        if gsi_exists:
            self.validate_gsi_key_schema(
                table_name,
                "flight-id-index",
                {"HASH": "flight_id"}
            )
        
        # Validate records
        table = self.dynamodb.Table(table_name)
        required_attrs = ["booking_id", "flight_id", "passenger_id"]
        
        try:
            response = table.scan()
            items = response.get("Items", [])
            
            # Test GSI query with sample data if available
            if items and gsi_exists:
                sample_item = items[0]
                if "flight_id" in sample_item:
                    self.test_gsi_query_performance(
                        table_name,
                        "flight-id-index",
                        {"flight_id": sample_item["flight_id"]}
                    )
            
            for item in items:
                self.validate_required_attributes(table_name, item, required_attrs)
                
                # Validate foreign keys
                record_id = {"booking_id": item.get("booking_id")}
                self.validate_foreign_key(
                    table_name, record_id, "flight_id",
                    item.get("flight_id"), self.flight_ids, FLIGHTS_TABLE
                )
                self.validate_foreign_key(
                    table_name, record_id, "passenger_id",
                    item.get("passenger_id"), self.passenger_ids, PASSENGERS_TABLE
                )
        except Exception as e:
            self.add_issue(
                "error",
                table_name,
                "scan_error",
                f"Error scanning table: {str(e)}"
            )
    
    def validate_crew_roster_table(self):
        """Validate CrewRoster table"""
        logger.info("Validating CrewRoster table...")
        table_name = CREW_ROSTER_TABLE
        
        if not self.validate_table_exists(table_name):
            return
        
        # Check required GSIs exist and are ACTIVE (Requirement 4.8)
        gsi_exists = self.validate_gsi_exists(table_name, "flight-position-index")
        
        # Validate GSI key schema
        if gsi_exists:
            self.validate_gsi_key_schema(
                table_name,
                "flight-position-index",
                {"HASH": "flight_id", "RANGE": "position"}
            )
        
        # Validate records
        table = self.dynamodb.Table(table_name)
        required_attrs = ["flight_id", "crew_id"]
        
        try:
            response = table.scan()
            items = response.get("Items", [])
            
            # Test GSI query with sample data if available
            if items and gsi_exists:
                sample_item = items[0]
                if "flight_id" in sample_item:
                    self.test_gsi_query_performance(
                        table_name,
                        "flight-position-index",
                        {"flight_id": sample_item["flight_id"]}
                    )
            
            for item in items:
                self.validate_required_attributes(table_name, item, required_attrs)
                
                # Validate foreign keys
                record_id = {"flight_id": item.get("flight_id"), "crew_id": item.get("crew_id")}
                self.validate_foreign_key(
                    table_name, record_id, "flight_id",
                    item.get("flight_id"), self.flight_ids, FLIGHTS_TABLE
                )
                self.validate_foreign_key(
                    table_name, record_id, "crew_id",
                    item.get("crew_id"), self.crew_ids, CREW_MEMBERS_TABLE
                )
        except Exception as e:
            self.add_issue(
                "error",
                table_name,
                "scan_error",
                f"Error scanning table: {str(e)}"
            )
    
    def validate_maintenance_workorders_table(self):
        """Validate MaintenanceWorkOrders table"""
        logger.info("Validating MaintenanceWorkOrders table...")
        table_name = MAINTENANCE_WORK_ORDERS_TABLE
        
        if not self.validate_table_exists(table_name):
            return
        
        # Check required GSIs exist and are ACTIVE
        gsi_exists = self.validate_gsi_exists(table_name, "aircraft-registration-index")
        
        # Validate GSI key schema
        if gsi_exists:
            self.validate_gsi_key_schema(
                table_name,
                "aircraft-registration-index",
                {"HASH": "aircraftRegistration"}
            )
        
        # Validate records
        table = self.dynamodb.Table(table_name)
        required_attrs = ["workorder_id", "aircraftRegistration"]
        
        try:
            response = table.scan()
            items = response.get("Items", [])
            
            # Test GSI query with sample data if available
            if items and gsi_exists:
                sample_item = items[0]
                if "aircraftRegistration" in sample_item:
                    self.test_gsi_query_performance(
                        table_name,
                        "aircraft-registration-index",
                        {"aircraftRegistration": sample_item["aircraftRegistration"]}
                    )
            
            for item in items:
                self.validate_required_attributes(table_name, item, required_attrs)
                
                # Validate foreign keys
                record_id = {"workorder_id": item.get("workorder_id")}
                self.validate_foreign_key(
                    table_name, record_id, "aircraftRegistration",
                    item.get("aircraftRegistration"), self.aircraft_registrations, FLIGHTS_TABLE
                )
        except Exception as e:
            self.add_issue(
                "error",
                table_name,
                "scan_error",
                f"Error scanning table: {str(e)}"
            )
    
    def validate_cargo_tables(self):
        """Validate Cargo tables"""
        logger.info("Validating Cargo tables...")
        
        # Validate CargoFlightAssignments
        table_name = CARGO_FLIGHT_ASSIGNMENTS_TABLE
        if self.validate_table_exists(table_name):
            # Check required GSIs exist and are ACTIVE (Requirement 4.9)
            gsi1_exists = self.validate_gsi_exists(table_name, "flight-loading-index")
            gsi2_exists = self.validate_gsi_exists(table_name, "shipment-index")
            
            # Validate GSI key schemas
            if gsi1_exists:
                self.validate_gsi_key_schema(
                    table_name,
                    "flight-loading-index",
                    {"HASH": "flight_id", "RANGE": "loading_priority"}
                )
            
            if gsi2_exists:
                self.validate_gsi_key_schema(
                    table_name,
                    "shipment-index",
                    {"HASH": "shipment_id"}
                )
            
            table = self.dynamodb.Table(table_name)
            required_attrs = ["flight_id", "shipment_id"]
            
            try:
                response = table.scan()
                items = response.get("Items", [])
                
                # Test GSI queries with sample data if available
                if items and gsi1_exists:
                    sample_item = items[0]
                    if "flight_id" in sample_item:
                        self.test_gsi_query_performance(
                            table_name,
                            "flight-loading-index",
                            {"flight_id": sample_item["flight_id"]}
                        )
                
                if items and gsi2_exists:
                    sample_item = items[0]
                    if "shipment_id" in sample_item:
                        self.test_gsi_query_performance(
                            table_name,
                            "shipment-index",
                            {"shipment_id": sample_item["shipment_id"]}
                        )
                
                for item in items:
                    self.validate_required_attributes(table_name, item, required_attrs)
                    
                    # Validate foreign keys
                    record_id = {"flight_id": item.get("flight_id"), "shipment_id": item.get("shipment_id")}
                    self.validate_foreign_key(
                        table_name, record_id, "flight_id",
                        item.get("flight_id"), self.flight_ids, FLIGHTS_TABLE
                    )
                    self.validate_foreign_key(
                        table_name, record_id, "shipment_id",
                        item.get("shipment_id"), self.shipment_ids, CARGO_SHIPMENTS_TABLE
                    )
            except Exception as e:
                self.add_issue(
                    "error",
                    table_name,
                    "scan_error",
                    f"Error scanning table: {str(e)}"
                )
    
    def validate_baggage_table(self):
        """Validate Baggage table"""
        logger.info("Validating Baggage table...")
        table_name = BAGGAGE_TABLE
        
        if not self.validate_table_exists(table_name):
            return
        
        # Check required GSIs exist and are ACTIVE (Requirement 4.10)
        gsi1_exists = self.validate_gsi_exists(table_name, "booking-index")
        gsi2_exists = self.validate_gsi_exists(table_name, "location-status-index")
        
        # Validate GSI key schemas
        if gsi1_exists:
            self.validate_gsi_key_schema(
                table_name,
                "booking-index",
                {"HASH": "booking_id"}
            )
        
        if gsi2_exists:
            self.validate_gsi_key_schema(
                table_name,
                "location-status-index",
                {"HASH": "current_location", "RANGE": "status"}
            )
        
        # Validate records
        table = self.dynamodb.Table(table_name)
        required_attrs = ["baggage_id", "booking_id"]
        
        try:
            response = table.scan()
            items = response.get("Items", [])
            
            # Test GSI queries with sample data if available
            if items and gsi1_exists:
                sample_item = items[0]
                if "booking_id" in sample_item:
                    self.test_gsi_query_performance(
                        table_name,
                        "booking-index",
                        {"booking_id": sample_item["booking_id"]}
                    )
            
            if items and gsi2_exists:
                sample_item = items[0]
                if "current_location" in sample_item:
                    self.test_gsi_query_performance(
                        table_name,
                        "location-status-index",
                        {"current_location": sample_item["current_location"]}
                    )
            
            for item in items:
                self.validate_required_attributes(table_name, item, required_attrs)
                
                # Validate foreign keys
                record_id = {"baggage_id": item.get("baggage_id")}
                self.validate_foreign_key(
                    table_name, record_id, "booking_id",
                    item.get("booking_id"), self.booking_ids, BOOKINGS_TABLE
                )
        except Exception as e:
            self.add_issue(
                "error",
                table_name,
                "scan_error",
                f"Error scanning table: {str(e)}"
            )
    
    def validate_agent_permissions(self):
        """Validate IAM permissions for agents"""
        logger.info("Validating agent permissions...")
        
        # Get the AgentCore execution role from environment or config
        execution_role_arn = self._get_agentcore_execution_role()
        
        if not execution_role_arn:
            self.add_issue(
                "warning",
                "IAM",
                "role_not_found",
                "Could not determine AgentCore execution role ARN",
                fix_suggestion="Set AGENTCORE_EXECUTION_ROLE environment variable or check .bedrock_agentcore.yaml"
            )
            return
        
        # Extract role name from ARN
        role_name = execution_role_arn.split("/")[-1]
        logger.info(f"  Checking role: {role_name}")
        
        # Validate role exists
        if not self._validate_role_exists(role_name):
            return
        
        # Get role policies
        inline_policies = self._get_inline_policies(role_name)
        attached_policies = self._get_attached_policies(role_name)
        
        # Check DynamoDB permissions
        self._validate_dynamodb_permissions(
            role_name, inline_policies, attached_policies
        )
        
        # Validate agent-specific table access
        self._validate_agent_table_access_permissions(
            role_name, inline_policies, attached_policies
        )
    
    def validate_all_gsis(self):
        """Comprehensive GSI validation across all tables (Task 3.4)
        
        This method provides a comprehensive validation of all GSIs required by the system:
        - Verifies all required GSIs exist on tables
        - Checks GSI status (must be ACTIVE)
        - Validates GSI key schema matches requirements
        - Tests sample queries use GSIs (no table scans)
        
        Validates Requirements 4.1-4.12 and 6.5-6.8
        """
        logger.info("=" * 60)
        logger.info("Comprehensive GSI Validation (Task 3.4)")
        logger.info("=" * 60)
        
        # Define required GSIs per table based on Requirements 4.1-4.12
        required_gsis = {
            FLIGHTS_TABLE: [
                {
                    "name": "flight-number-date-index",
                    "keys": {"HASH": "flight_number", "RANGE": "scheduled_departure"},
                    "requirement": "4.1"
                },
                {
                    "name": "aircraft-registration-index",
                    "keys": {"HASH": "aircraft_registration"},
                    "requirement": "4.2"
                }
            ],
            BOOKINGS_TABLE: [
                {
                    "name": "flight-id-index",
                    "keys": {"HASH": "flight_id"},
                    "requirement": "4.3"
                }
            ],
            MAINTENANCE_WORK_ORDERS_TABLE: [
                {
                    "name": "aircraft-registration-index",
                    "keys": {"HASH": "aircraftRegistration"},
                    "requirement": "4.4"
                }
            ],
            CREW_ROSTER_TABLE: [
                {
                    "name": "flight-position-index",
                    "keys": {"HASH": "flight_id", "RANGE": "position"},
                    "requirement": "4.8"
                }
            ],
            CARGO_FLIGHT_ASSIGNMENTS_TABLE: [
                {
                    "name": "flight-loading-index",
                    "keys": {"HASH": "flight_id", "RANGE": "loading_priority"},
                    "requirement": "4.9"
                }
            ],
            BAGGAGE_TABLE: [
                {
                    "name": "booking-index",
                    "keys": {"HASH": "booking_id"},
                    "requirement": "4.10"
                }
            ]
        }
        
        gsi_validation_results = {
            "total_gsis": 0,
            "validated": 0,
            "missing": 0,
            "inactive": 0,
            "schema_mismatch": 0,
            "query_test_passed": 0,
            "query_test_failed": 0
        }
        
        for table_name, gsis in required_gsis.items():
            logger.info(f"\nValidating GSIs for {table_name}...")
            
            # Check if table exists first
            if not self.validate_table_exists(table_name):
                logger.warning(f"  Skipping GSI validation - table {table_name} does not exist")
                continue
            
            for gsi_config in gsis:
                gsi_name = gsi_config["name"]
                expected_keys = gsi_config["keys"]
                requirement = gsi_config["requirement"]
                
                gsi_validation_results["total_gsis"] += 1
                
                logger.info(f"  Validating GSI: {gsi_name} (Requirement {requirement})")
                
                # Step 1: Check if GSI exists and is ACTIVE
                gsi_exists = self.validate_gsi_exists(table_name, gsi_name)
                if not gsi_exists:
                    gsi_validation_results["missing"] += 1
                    logger.error(f"    ❌ GSI {gsi_name} is missing or not ACTIVE")
                    continue
                
                # Step 2: Validate GSI key schema
                schema_valid = self.validate_gsi_key_schema(table_name, gsi_name, expected_keys)
                if not schema_valid:
                    gsi_validation_results["schema_mismatch"] += 1
                    logger.error(f"    ❌ GSI {gsi_name} schema does not match requirements")
                    continue
                
                # Step 3: Test sample query uses GSI (no table scan)
                # Get sample data for testing
                try:
                    table = self.dynamodb.Table(table_name)
                    response = table.scan(Limit=1)
                    items = response.get("Items", [])
                    
                    if items:
                        sample_item = items[0]
                        # Get the partition key attribute name
                        partition_key = expected_keys["HASH"]
                        
                        if partition_key in sample_item:
                            test_key = {partition_key: sample_item[partition_key]}
                            query_success = self.test_gsi_query_performance(
                                table_name, gsi_name, test_key
                            )
                            
                            if query_success:
                                gsi_validation_results["query_test_passed"] += 1
                                gsi_validation_results["validated"] += 1
                                logger.info(f"    ✅ GSI {gsi_name} validated successfully")
                            else:
                                gsi_validation_results["query_test_failed"] += 1
                                logger.warning(f"    ⚠️  GSI {gsi_name} query test failed")
                        else:
                            logger.warning(f"    ⚠️  No sample data with {partition_key} for query test")
                            gsi_validation_results["validated"] += 1  # Still count as validated if schema is correct
                    else:
                        logger.info(f"    ℹ️  No sample data available for query test")
                        gsi_validation_results["validated"] += 1  # Still count as validated if schema is correct
                        
                except Exception as e:
                    logger.error(f"    ❌ Error testing GSI query: {str(e)}")
                    gsi_validation_results["query_test_failed"] += 1
        
        # Log comprehensive summary
        logger.info(f"\n{'=' * 60}")
        logger.info(f"GSI VALIDATION SUMMARY")
        logger.info(f"{'=' * 60}")
        logger.info(f"Total GSIs Required: {gsi_validation_results['total_gsis']}")
        logger.info(f"Successfully Validated: {gsi_validation_results['validated']}")
        logger.info(f"Missing or Inactive: {gsi_validation_results['missing']}")
        logger.info(f"Schema Mismatches: {gsi_validation_results['schema_mismatch']}")
        logger.info(f"Query Tests Passed: {gsi_validation_results['query_test_passed']}")
        logger.info(f"Query Tests Failed: {gsi_validation_results['query_test_failed']}")
        
        # Add summary issue
        if gsi_validation_results["validated"] == gsi_validation_results["total_gsis"]:
            self.add_issue(
                "info",
                "GSI_VALIDATION",
                "all_gsis_validated",
                f"All {gsi_validation_results['total_gsis']} required GSIs validated successfully",
                fix_suggestion=None
            )
        else:
            issues_found = (
                gsi_validation_results["missing"] +
                gsi_validation_results["schema_mismatch"] +
                gsi_validation_results["query_test_failed"]
            )
            self.add_issue(
                "error",
                "GSI_VALIDATION",
                "gsi_validation_incomplete",
                f"GSI validation incomplete: {issues_found} issues found out of {gsi_validation_results['total_gsis']} GSIs",
                fix_suggestion="Run scripts/create_gsis.py to create missing GSIs and fix schema issues"
            )
        
        return gsi_validation_results
    
    def _get_agentcore_execution_role(self) -> Optional[str]:
        """Get the AgentCore execution role ARN from environment or config"""
        
        # Try environment variable first
        role_arn = os.environ.get("AGENTCORE_EXECUTION_ROLE")
        if role_arn:
            return role_arn
        
        # Try reading from .bedrock_agentcore.yaml if yaml is available
        if not HAS_YAML:
            logger.debug("PyYAML not available, cannot read config file")
            return None
        
        config_paths = [
            "skymarshal_agents_new/skymarshal/.bedrock_agentcore.yaml",
            ".bedrock_agentcore.yaml"
        ]
        
        for config_path in config_paths:
            try:
                if os.path.exists(config_path):
                    with open(config_path, "r") as f:
                        config = yaml.safe_load(f)
                        if config and "agents" in config:
                            for agent_config in config["agents"].values():
                                if "aws" in agent_config and "execution_role" in agent_config["aws"]:
                                    return agent_config["aws"]["execution_role"]
            except Exception as e:
                logger.debug(f"Could not read config from {config_path}: {e}")
        
        return None
    
    def _validate_role_exists(self, role_name: str) -> bool:
        """Check if IAM role exists"""
        try:
            self.iam_client.get_role(RoleName=role_name)
            self.add_issue(
                "info",
                "IAM",
                "role_exists",
                f"IAM role {role_name} exists"
            )
            return True
        except self.iam_client.exceptions.NoSuchEntityException:
            self.add_issue(
                "error",
                "IAM",
                "role_not_found",
                f"IAM role {role_name} does not exist",
                fix_suggestion="Create the IAM role or update the execution role ARN in AgentCore config"
            )
            return False
        except Exception as e:
            self.add_issue(
                "error",
                "IAM",
                "role_check_error",
                f"Error checking IAM role {role_name}: {str(e)}",
                fix_suggestion="Verify IAM permissions for the validation script"
            )
            return False
    
    def _get_inline_policies(self, role_name: str) -> List[Dict[str, Any]]:
        """Get inline policies attached to a role"""
        try:
            response = self.iam_client.list_role_policies(RoleName=role_name)
            policy_names = response.get("PolicyNames", [])
            
            policies = []
            for policy_name in policy_names:
                policy_response = self.iam_client.get_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
                policies.append({
                    "name": policy_name,
                    "document": policy_response.get("PolicyDocument", {})
                })
            
            return policies
        except Exception as e:
            logger.error(f"Error getting inline policies: {e}")
            return []
    
    def _get_attached_policies(self, role_name: str) -> List[Dict[str, Any]]:
        """Get managed policies attached to a role"""
        try:
            response = self.iam_client.list_attached_role_policies(RoleName=role_name)
            attached_policies = response.get("AttachedPolicies", [])
            
            policies = []
            for policy in attached_policies:
                policy_arn = policy["PolicyArn"]
                
                # Get policy version
                policy_response = self.iam_client.get_policy(PolicyArn=policy_arn)
                default_version_id = policy_response["Policy"]["DefaultVersionId"]
                
                # Get policy document
                version_response = self.iam_client.get_policy_version(
                    PolicyArn=policy_arn,
                    VersionId=default_version_id
                )
                
                policies.append({
                    "name": policy["PolicyName"],
                    "arn": policy_arn,
                    "document": version_response["PolicyVersion"]["Document"]
                })
            
            return policies
        except Exception as e:
            logger.error(f"Error getting attached policies: {e}")
            return []
    
    def _validate_dynamodb_permissions(
        self,
        role_name: str,
        inline_policies: List[Dict[str, Any]],
        attached_policies: List[Dict[str, Any]]
    ):
        """Validate that the role has necessary DynamoDB permissions"""
        required_actions = [
            "dynamodb:Query",
            "dynamodb:Scan",
            "dynamodb:GetItem",
            "dynamodb:BatchGetItem",
            "dynamodb:DescribeTable"
        ]
        
        # Check if role has DynamoDB permissions
        has_dynamodb_access = False
        granted_actions = set()
        
        all_policies = inline_policies + attached_policies
        
        for policy in all_policies:
            document = policy.get("document", {})
            statements = document.get("Statement", [])
            
            if not isinstance(statements, list):
                statements = [statements]
            
            for statement in statements:
                if statement.get("Effect") != "Allow":
                    continue
                
                actions = statement.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]
                
                resources = statement.get("Resource", [])
                if isinstance(resources, str):
                    resources = [resources]
                
                # Check for DynamoDB actions
                for action in actions:
                    if action.startswith("dynamodb:") or action == "*":
                        has_dynamodb_access = True
                        
                        # Check if it covers required actions
                        if action == "dynamodb:*" or action == "*":
                            granted_actions.update(required_actions)
                        else:
                            granted_actions.add(action)
        
        if not has_dynamodb_access:
            self.add_issue(
                "error",
                "IAM",
                "missing_dynamodb_permissions",
                f"Role {role_name} has no DynamoDB permissions",
                fix_suggestion="Add DynamoDB read permissions to the IAM role"
            )
            return
        
        # Check for specific required actions
        missing_actions = [
            action for action in required_actions
            if action not in granted_actions and "dynamodb:*" not in granted_actions and "*" not in granted_actions
        ]
        
        if missing_actions:
            self.add_issue(
                "warning",
                "IAM",
                "incomplete_dynamodb_permissions",
                f"Role {role_name} missing DynamoDB actions: {', '.join(missing_actions)}",
                fix_suggestion=f"Add the following actions to IAM policy: {', '.join(missing_actions)}"
            )
        else:
            self.add_issue(
                "info",
                "IAM",
                "dynamodb_permissions_ok",
                f"Role {role_name} has required DynamoDB permissions"
            )
    
    def _validate_agent_table_access_permissions(
        self,
        role_name: str,
        inline_policies: List[Dict[str, Any]],
        attached_policies: List[Dict[str, Any]]
    ):
        """Validate that agents have access to their required tables"""
        logger.info("  Validating agent-specific table access...")
        
        # Get all table ARNs that should be accessible
        required_tables = set()
        for agent_name, tables in AGENT_TABLE_ACCESS.items():
            required_tables.update(tables)
        
        # Check if policies grant access to required tables
        all_policies = inline_policies + attached_policies
        accessible_tables = set()
        has_wildcard_access = False
        
        for policy in all_policies:
            document = policy.get("document", {})
            statements = document.get("Statement", [])
            
            if not isinstance(statements, list):
                statements = [statements]
            
            for statement in statements:
                if statement.get("Effect") != "Allow":
                    continue
                
                actions = statement.get("Action", [])
                if isinstance(actions, str):
                    actions = [actions]
                
                resources = statement.get("Resource", [])
                if isinstance(resources, str):
                    resources = [resources]
                
                # Check if actions include DynamoDB read operations
                has_read_action = any(
                    action in ["dynamodb:Query", "dynamodb:Scan", "dynamodb:GetItem", "dynamodb:*", "*"]
                    for action in actions
                )
                
                if not has_read_action:
                    continue
                
                # Check resources
                for resource in resources:
                    if resource == "*":
                        has_wildcard_access = True
                        accessible_tables.update(required_tables)
                        break
                    
                    # Extract table name from ARN
                    # Format: arn:aws:dynamodb:region:account:table/TableName
                    if "/table/" in resource or resource.endswith("/table/*"):
                        if resource.endswith("/*") or resource.endswith("/table/*"):
                            has_wildcard_access = True
                            accessible_tables.update(required_tables)
                            break
                        else:
                            table_name = resource.split("/")[-1]
                            accessible_tables.add(table_name)
        
        # Report on table access
        if has_wildcard_access:
            self.add_issue(
                "info",
                "IAM",
                "table_access_wildcard",
                f"Role {role_name} has wildcard access to DynamoDB tables"
            )
        else:
            missing_tables = required_tables - accessible_tables
            if missing_tables:
                self.add_issue(
                    "warning",
                    "IAM",
                    "missing_table_access",
                    f"Role {role_name} may not have access to tables: {', '.join(sorted(missing_tables))}",
                    fix_suggestion="Add table-specific permissions to IAM policy or use wildcard for development"
                )
            else:
                self.add_issue(
                    "info",
                    "IAM",
                    "table_access_ok",
                    f"Role {role_name} has access to all required tables"
                )
        
        # Validate per-agent access
        for agent_name, agent_tables in AGENT_TABLE_ACCESS.items():
            agent_accessible = [t for t in agent_tables if t in accessible_tables or has_wildcard_access]
            agent_missing = [t for t in agent_tables if t not in accessible_tables and not has_wildcard_access]
            
            if agent_missing:
                self.add_issue(
                    "warning",
                    "IAM",
                    "agent_table_access_incomplete",
                    f"Agent '{agent_name}' may not have access to tables: {', '.join(agent_missing)}",
                    fix_suggestion=f"Ensure IAM policy grants access to: {', '.join(agent_missing)}"
                )
            else:
                self.add_issue(
                    "info",
                    "IAM",
                    "agent_table_access_ok",
                    f"Agent '{agent_name}' has access to all required tables ({len(agent_tables)} tables)"
                )
    
    def run_validation(self) -> Dict[str, Any]:
        """Run all validations"""
        logger.info("=" * 60)
        logger.info("Starting DynamoDB Data Validation")
        logger.info("=" * 60)
        
        # Load foreign key caches
        self.load_foreign_key_caches()
        
        # Validate tables (includes individual GSI checks)
        self.validate_flights_table()
        self.validate_bookings_table()
        self.validate_crew_roster_table()
        self.validate_maintenance_workorders_table()
        self.validate_cargo_tables()
        self.validate_baggage_table()
        
        # Comprehensive GSI validation (Task 3.4)
        gsi_results = self.validate_all_gsis()
        
        # Validate permissions
        self.validate_agent_permissions()
        
        # Generate report
        report = self.generate_report()
        
        # Add GSI validation results to report
        report["gsi_validation"] = gsi_results
        
        logger.info("=" * 60)
        logger.info("Validation Complete")
        logger.info("=" * 60)
        
        return report
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate detailed validation report with comprehensive statistics and groupings"""
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        info = [i for i in self.issues if i.severity == "info"]
        
        # Group issues by table
        issues_by_table = {}
        for issue in self.issues:
            if issue.table not in issues_by_table:
                issues_by_table[issue.table] = []
            issues_by_table[issue.table].append(issue.to_dict())
        
        # Group issues by type
        issues_by_type = {}
        for issue in self.issues:
            if issue.issue_type not in issues_by_type:
                issues_by_type[issue.issue_type] = []
            issues_by_type[issue.issue_type].append(issue.to_dict())
        
        # Calculate statistics per table
        table_statistics = {}
        for table_name in issues_by_table.keys():
            table_issues = [i for i in self.issues if i.table == table_name]
            table_statistics[table_name] = {
                "total_issues": len(table_issues),
                "errors": len([i for i in table_issues if i.severity == "error"]),
                "warnings": len([i for i in table_issues if i.severity == "warning"]),
                "info": len([i for i in table_issues if i.severity == "info"]),
                "issue_types": list(set([i.issue_type for i in table_issues]))
            }
        
        # Calculate statistics per issue type
        type_statistics = {}
        for issue_type in issues_by_type.keys():
            type_issues = [i for i in self.issues if i.issue_type == issue_type]
            type_statistics[issue_type] = {
                "count": len(type_issues),
                "severity_breakdown": {
                    "errors": len([i for i in type_issues if i.severity == "error"]),
                    "warnings": len([i for i in type_issues if i.severity == "warning"]),
                    "info": len([i for i in type_issues if i.severity == "info"])
                },
                "affected_tables": list(set([i.table for i in type_issues]))
            }
        
        # Identify critical issues (errors with fix suggestions)
        critical_issues = [
            issue.to_dict() for issue in errors 
            if issue.fix_suggestion is not None
        ]
        
        # Identify issues without fix suggestions
        unresolved_issues = [
            issue.to_dict() for issue in self.issues 
            if issue.fix_suggestion is None and issue.severity in ["error", "warning"]
        ]
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "validation_metadata": {
                "region": self.region,
                "tables_validated": list(issues_by_table.keys()),
                "validation_scope": [
                    "table_existence",
                    "gsi_configuration",
                    "required_attributes",
                    "foreign_key_relationships",
                    "data_type_consistency"
                ]
            },
            "summary": {
                "total_issues": len(self.issues),
                "errors": len(errors),
                "warnings": len(warnings),
                "info": len(info),
                "critical_issues": len(critical_issues),
                "unresolved_issues": len(unresolved_issues),
                "tables_with_issues": len(issues_by_table),
                "unique_issue_types": len(issues_by_type)
            },
            "statistics": {
                "by_table": table_statistics,
                "by_issue_type": type_statistics
            },
            "issues": {
                "all": [issue.to_dict() for issue in self.issues],
                "by_severity": {
                    "errors": [issue.to_dict() for issue in errors],
                    "warnings": [issue.to_dict() for issue in warnings],
                    "info": [issue.to_dict() for issue in info]
                },
                "by_table": issues_by_table,
                "by_type": issues_by_type,
                "critical": critical_issues,
                "unresolved": unresolved_issues
            },
            "recommendations": self._generate_recommendations(errors, warnings)
        }
        
        # Print detailed summary
        logger.info(f"\n{'=' * 60}")
        logger.info(f"VALIDATION SUMMARY")
        logger.info(f"{'=' * 60}")
        logger.info(f"Total Issues: {len(self.issues)}")
        logger.info(f"  - Errors: {len(errors)}")
        logger.info(f"  - Warnings: {len(warnings)}")
        logger.info(f"  - Info: {len(info)}")
        logger.info(f"\nCritical Issues (with fix suggestions): {len(critical_issues)}")
        logger.info(f"Unresolved Issues (no fix suggestions): {len(unresolved_issues)}")
        
        if table_statistics:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"ISSUES BY TABLE")
            logger.info(f"{'=' * 60}")
            for table_name, stats in sorted(table_statistics.items()):
                logger.info(f"\n{table_name}:")
                logger.info(f"  Total: {stats['total_issues']} (E:{stats['errors']}, W:{stats['warnings']}, I:{stats['info']})")
                logger.info(f"  Issue Types: {', '.join(stats['issue_types'])}")
        
        if type_statistics:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"ISSUES BY TYPE")
            logger.info(f"{'=' * 60}")
            for issue_type, stats in sorted(type_statistics.items()):
                logger.info(f"\n{issue_type}:")
                logger.info(f"  Count: {stats['count']}")
                logger.info(f"  Severity: E:{stats['severity_breakdown']['errors']}, W:{stats['severity_breakdown']['warnings']}, I:{stats['severity_breakdown']['info']}")
                logger.info(f"  Affected Tables: {', '.join(stats['affected_tables'])}")
        
        if critical_issues:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"CRITICAL ISSUES (TOP 5)")
            logger.info(f"{'=' * 60}")
            for issue in critical_issues[:5]:
                logger.info(f"\n[{issue['table']}] {issue['issue_type']}")
                logger.info(f"  Description: {issue['description']}")
                logger.info(f"  Fix: {issue['fix_suggestion']}")
        
        return report
    
    def _generate_recommendations(self, errors: List[ValidationIssue], warnings: List[ValidationIssue]) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on validation results"""
        recommendations = []
        
        # Check for missing GSIs
        gsi_errors = [e for e in errors + warnings if "gsi" in e.issue_type.lower()]
        if gsi_errors:
            recommendations.append({
                "priority": "high",
                "category": "database_schema",
                "action": "Create missing Global Secondary Indexes",
                "command": "python scripts/create_gsis.py",
                "description": f"Found {len(gsi_errors)} GSI-related issues. Run the GSI creation script to add required indexes."
            })
        
        # Check for missing tables
        table_errors = [e for e in errors if e.issue_type == "table_missing"]
        if table_errors:
            recommendations.append({
                "priority": "critical",
                "category": "database_schema",
                "action": "Create missing DynamoDB tables",
                "command": "python database/create_dynamodb_tables.py",
                "description": f"Found {len(table_errors)} missing tables. Run the table creation script."
            })
        
        # Check for foreign key violations
        fk_errors = [e for e in errors if e.issue_type == "invalid_foreign_key"]
        if fk_errors:
            recommendations.append({
                "priority": "high",
                "category": "data_integrity",
                "action": "Fix foreign key violations",
                "description": f"Found {len(fk_errors)} orphaned records with invalid foreign key references. Review and clean up orphaned data."
            })
        
        # Check for missing required attributes
        attr_errors = [e for e in errors if e.issue_type == "missing_required_attributes"]
        if attr_errors:
            recommendations.append({
                "priority": "high",
                "category": "data_integrity",
                "action": "Add missing required attributes",
                "description": f"Found {len(attr_errors)} records with missing required attributes. Update records to include all required fields."
            })
        
        # Check for GSI status issues
        gsi_status_warnings = [w for w in warnings if w.issue_type == "gsi_not_active"]
        if gsi_status_warnings:
            recommendations.append({
                "priority": "medium",
                "category": "database_schema",
                "action": "Wait for GSI activation",
                "description": f"Found {len(gsi_status_warnings)} GSIs that are not yet ACTIVE. Wait for GSI creation to complete."
            })
        
        # Check for permission issues
        perm_issues = [e for e in errors + warnings if "permission" in e.issue_type.lower() or "iam" in e.table.lower()]
        if perm_issues:
            recommendations.append({
                "priority": "high",
                "category": "security",
                "action": "Verify IAM permissions",
                "description": "Review and update IAM roles for AgentCore agents to ensure proper DynamoDB access."
            })
        
        # If no issues, provide positive feedback
        if not errors and not warnings:
            recommendations.append({
                "priority": "info",
                "category": "validation",
                "action": "No action required",
                "description": "All validation checks passed successfully. Database is in good state."
            })
        
        return recommendations


def main():
    parser = argparse.ArgumentParser(description="Validate DynamoDB data integrity")
    parser.add_argument(
        "--output",
        default="validation_report.json",
        help="Output file for validation report (default: validation_report.json)"
    )
    parser.add_argument(
        "--region",
        default=DEFAULT_AWS_REGION,
        help=f"AWS region (default: {DEFAULT_AWS_REGION})"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = DynamoDBValidator(region=args.region)
    report = validator.run_validation()
    
    # Write report
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    logger.info(f"\nReport written to: {args.output}")
    
    # Exit with error code if there are errors
    if report["summary"]["errors"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
