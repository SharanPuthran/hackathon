"""
Table Version Configuration Module

Provides feature flag control for switching between V1 (original) and V2 (new) DynamoDB tables.
This enables seamless rollback capability without code changes - just change the TABLE_VERSION variable.

Usage:
    from database.table_config import get_table_name, TABLE_VERSION, TableVersion

    # Get table name based on current version
    table_name = get_table_name("flights")  # Returns "flights" (V1) or "flights_v2" (V2)

    # Override version for specific query
    table_name = get_table_name("flights", TableVersion.V2)  # Always returns "flights_v2"

Rollback Procedure:
    1. Change TABLE_VERSION below from TableVersion.V2 to TableVersion.V1
    2. Restart agents/redeploy Lambda
    3. V2 tables remain intact but unused
"""

from enum import Enum
from typing import Dict, Optional, List
from dataclasses import dataclass


class TableVersion(Enum):
    """Table version enum for switching between V1 and V2 tables."""
    V1 = "v1"
    V2 = "v2"


# =============================================================================
# FEATURE FLAG - CHANGE THIS TO SWITCH BETWEEN V1 AND V2 TABLES
# =============================================================================
# Set to TableVersion.V1 for original tables (rollback)
# Set to TableVersion.V2 for new V2 tables with enhanced data
TABLE_VERSION: TableVersion = TableVersion.V2  # <-- CHANGE THIS FOR ROLLBACK
# =============================================================================


@dataclass
class TableSchema:
    """Schema definition for a DynamoDB table."""
    partition_key: str
    partition_key_type: str = "S"  # S=String, N=Number
    sort_key: Optional[str] = None
    sort_key_type: Optional[str] = None
    gsis: Optional[List[Dict]] = None


# =============================================================================
# V1 Table Names (Original - 23 tables)
# =============================================================================
V1_TABLES: Dict[str, str] = {
    # Core operational tables
    "flights": "flights",
    "passengers": "passengers",
    "bookings": "bookings",
    "baggage": "Baggage",
    "crew_roster": "CrewRoster",
    "crew_members": "CrewMembers",
    "aircraft": "AircraftAvailability",
    "cargo_shipments": "CargoShipments",
    "cargo_assignments": "CargoFlightAssignments",
    "weather": "Weather",
    "maintenance_work_orders": "MaintenanceWorkOrders",
    "maintenance_staff": "MaintenanceStaff",
    # Analysis and impact tables
    "disrupted_passengers": "disrupted_passengers_scenario",
    "aircraft_swap_options": "aircraft_swap_options",
    "inbound_flight_impact": "inbound_flight_impact",
    "recovery_scenarios": "recovery_scenarios",
    "recovery_actions": "recovery_actions",
    "disruption_events": "disruption_events",
    "disruption_costs": "disruption_costs",
    "financial_parameters": "financial_parameters",
    "financial_transactions": "financial_transactions",
    "business_impact": "business_impact_assessment",
    "safety_constraints": "safety_constraints",
}

# =============================================================================
# V2 Table Names (New - with _v2 suffix)
# =============================================================================
V2_TABLES: Dict[str, str] = {
    # Enhanced tables (have V1 equivalent with additional columns)
    "flights": "flights_v2",
    "passengers": "passengers_v2",
    "baggage": "baggage_v2",
    "crew_roster": "crew_roster_v2",
    "aircraft": "aircraft_v2",
    "cargo_shipments": "cargo_shipments_v2",
    "weather": "weather_v2",
    "financial_parameters": "financial_parameters_v2",
    "safety_constraints": "safety_constraints_v2",
    "recovery_cost_matrix": "recovery_cost_matrix_v2",
    "cost_breakdown": "cost_breakdown_v2",
    # Tables without V2 version - fall back to V1 names
    "bookings": "bookings",
    "crew_members": "CrewMembers",
    "cargo_assignments": "CargoFlightAssignments",
    "maintenance_work_orders": "MaintenanceWorkOrders",
    "maintenance_staff": "MaintenanceStaff",
    "maintenance_roster": "maintenance_roster",
    "disrupted_passengers": "disrupted_passengers_scenario",
    "aircraft_swap_options": "aircraft_swap_options",
    "inbound_flight_impact": "inbound_flight_impact",
    "recovery_scenarios": "recovery_scenarios",
    "recovery_actions": "recovery_actions",
    "disruption_events": "disruption_events",
    "disruption_costs": "disruption_costs",
    "financial_transactions": "financial_transactions",
    "business_impact": "business_impact_assessment",
    # New V2-only tables (no V1 equivalent - new capabilities)
    "aircraft_rotations": "aircraft_rotations_v2",
    "oal_flights": "oal_flights_v2",
    "airport_curfews": "airport_curfews_v2",
    "airport_slots": "airport_slots_v2",
    "cold_chain_facilities": "cold_chain_facilities_v2",
    "compensation_rules": "compensation_rules_v2",
    "ground_equipment": "ground_equipment_v2",
    "interline_agreements": "interline_agreements_v2",
    "maintenance_constraints": "maintenance_constraints_v2",
    "minimum_connection_times": "minimum_connection_times_v2",
    "reserve_crew": "reserve_crew_v2",
    "turnaround_requirements": "turnaround_requirements_v2",
}

# =============================================================================
# V2 Table Schemas (Primary Key, Sort Key, GSIs)
# =============================================================================
V2_TABLE_SCHEMAS: Dict[str, TableSchema] = {
    # Enhanced tables
    "flights_v2": TableSchema(
        partition_key="flight_id",
        partition_key_type="S",
        gsis=[
            {"name": "flight-number-date-index", "pk": "flight_number", "sk": "scheduled_departure_utc"},
            {"name": "aircraft-rotation-index", "pk": "aircraft_registration", "sk": "scheduled_departure_utc"},
            {"name": "airport-curfew-index", "pk": "destination", "sk": "scheduled_arrival_utc"},
            {"name": "aircraft-registration-index", "pk": "aircraft_registration"},
        ]
    ),
    "passengers_v2": TableSchema(
        partition_key="passenger_id",
        partition_key_type="S",
        gsis=[
            {"name": "passenger-elite-tier-index", "pk": "frequent_flyer_tier", "sk": "passenger_id"},
            {"name": "pnr-index", "pk": "pnr"},
            {"name": "first-leg-flight-index", "pk": "first_leg_flight_id"},
        ]
    ),
    "baggage_v2": TableSchema(
        partition_key="baggage_id",
        partition_key_type="S",
        gsis=[
            {"name": "passenger-index", "pk": "passenger_id"},
            {"name": "flight-index", "pk": "flight_id"},
            {"name": "pnr-index", "pk": "pnr"},
        ]
    ),
    "crew_roster_v2": TableSchema(
        partition_key="roster_id",
        partition_key_type="S",
        gsis=[
            {"name": "flight-position-index", "pk": "flight_id", "sk": "role"},
            {"name": "crew-duty-date-index", "pk": "crew_id", "sk": "duty_start_utc"},
            {"name": "employee-id-index", "pk": "employee_id"},
        ]
    ),
    "aircraft_v2": TableSchema(
        partition_key="aircraft_registration",
        partition_key_type="S",
        gsis=[
            {"name": "status-index", "pk": "status"},
            {"name": "aircraft-type-index", "pk": "aircraft_type"},
            {"name": "mel-status-index", "pk": "mel_status"},
        ]
    ),
    "cargo_shipments_v2": TableSchema(
        partition_key="shipment_id",
        partition_key_type="S",
        gsis=[
            {"name": "awb-index", "pk": "awb_number"},
            {"name": "first-leg-flight-index", "pk": "first_leg_flight_id"},
            {"name": "cargo-type-index", "pk": "cargo_type"},
        ]
    ),
    "weather_v2": TableSchema(
        partition_key="airport_code",
        partition_key_type="S",
        sort_key="forecast_time_utc",
        sort_key_type="S",
    ),
    "financial_parameters_v2": TableSchema(
        partition_key="parameter_id",
        partition_key_type="S",
        gsis=[
            {"name": "category-index", "pk": "category"},
        ]
    ),
    "safety_constraints_v2": TableSchema(
        partition_key="constraint_id",
        partition_key_type="S",
        gsis=[
            {"name": "category-index", "pk": "category"},
        ]
    ),
    "recovery_cost_matrix_v2": TableSchema(
        partition_key="matrix_id",
        partition_key_type="S",
        gsis=[
            {"name": "scenario-type-index", "pk": "scenario_type"},
            {"name": "recovery-option-index", "pk": "recovery_option"},
        ]
    ),
    "cost_breakdown_v2": TableSchema(
        partition_key="cost_id",
        partition_key_type="S",
        gsis=[
            {"name": "category-index", "pk": "cost_category"},
        ]
    ),
    # New V2-only tables
    "aircraft_rotations_v2": TableSchema(
        partition_key="rotation_id",
        partition_key_type="S",
        gsis=[
            {"name": "aircraft-sequence-index", "pk": "aircraft_registration", "sk": "sequence_number"},
            {"name": "flight-id-index", "pk": "flight_id"},
        ]
    ),
    "oal_flights_v2": TableSchema(
        partition_key="alt_flight_id",
        partition_key_type="S",
        gsis=[
            {"name": "route-index", "pk": "origin", "sk": "destination"},
            {"name": "airline-index", "pk": "airline_code"},
        ]
    ),
    "airport_curfews_v2": TableSchema(
        partition_key="curfew_id",
        partition_key_type="S",
        gsis=[
            {"name": "airport-index", "pk": "airport_code"},
        ]
    ),
    "airport_slots_v2": TableSchema(
        partition_key="slot_id",
        partition_key_type="S",
        gsis=[
            {"name": "flight-index", "pk": "flight_id"},
            {"name": "airport-index", "pk": "airport_code"},
        ]
    ),
    "cold_chain_facilities_v2": TableSchema(
        partition_key="facility_id",
        partition_key_type="S",
        gsis=[
            {"name": "airport-index", "pk": "airport_code"},
        ]
    ),
    "compensation_rules_v2": TableSchema(
        partition_key="rule_id",
        partition_key_type="S",
        gsis=[
            {"name": "regulation-index", "pk": "regulation"},
        ]
    ),
    "ground_equipment_v2": TableSchema(
        partition_key="equipment_id",
        partition_key_type="S",
        gsis=[
            {"name": "airport-type-index", "pk": "airport_code", "sk": "equipment_type"},
        ]
    ),
    "interline_agreements_v2": TableSchema(
        partition_key="agreement_id",
        partition_key_type="S",
        gsis=[
            {"name": "partner-airline-index", "pk": "partner_airline_code"},
        ]
    ),
    "maintenance_constraints_v2": TableSchema(
        partition_key="constraint_id",
        partition_key_type="S",
        gsis=[
            {"name": "aircraft-index", "pk": "aircraft_registration"},
        ]
    ),
    "minimum_connection_times_v2": TableSchema(
        partition_key="mct_id",
        partition_key_type="S",
        gsis=[
            {"name": "airport-connection-index", "pk": "airport_code", "sk": "connection_type"},
        ]
    ),
    "reserve_crew_v2": TableSchema(
        partition_key="reserve_id",
        partition_key_type="S",
        gsis=[
            {"name": "base-status-index", "pk": "base", "sk": "status"},
            {"name": "role-index", "pk": "role"},
        ]
    ),
    "turnaround_requirements_v2": TableSchema(
        partition_key="turnaround_id",
        partition_key_type="S",
        gsis=[
            {"name": "flight-index", "pk": "flight_id"},
            {"name": "airport-index", "pk": "airport_code"},
        ]
    ),
}

# =============================================================================
# CSV to Table Mapping (for import script)
# =============================================================================
CSV_TO_TABLE_MAPPING: Dict[str, str] = {
    "flights.csv": "flights_v2",
    "passengers.csv": "passengers_v2",
    "baggage.csv": "baggage_v2",
    "crew_roster.csv": "crew_roster_v2",
    "aircraft.csv": "aircraft_v2",
    "cargo.csv": "cargo_shipments_v2",
    "weather.csv": "weather_v2",
    "financial_parameters.csv": "financial_parameters_v2",
    "safety_constraints.csv": "safety_constraints_v2",
    "recovery_cost_matrix.csv": "recovery_cost_matrix_v2",
    "cost_breakdown.csv": "cost_breakdown_v2",
    "aircraft_rotations.csv": "aircraft_rotations_v2",
    "OAL_flights.csv": "oal_flights_v2",
    "airport_curfews.csv": "airport_curfews_v2",
    "airport_slots.csv": "airport_slots_v2",
    "cold_chain_facilities.csv": "cold_chain_facilities_v2",
    "compensation_rules.csv": "compensation_rules_v2",
    "ground_equipment.csv": "ground_equipment_v2",
    "interline_agreements.csv": "interline_agreements_v2",
    "maintenance_constraints.csv": "maintenance_constraints_v2",
    "minimum_connection_times.csv": "minimum_connection_times_v2",
    "reserve_crew.csv": "reserve_crew_v2",
    "turnaround_requirements.csv": "turnaround_requirements_v2",
}


# =============================================================================
# Table Access Functions
# =============================================================================

def get_table_name(logical_name: str, version: Optional[TableVersion] = None) -> str:
    """
    Get actual DynamoDB table name for logical name based on version.

    Args:
        logical_name: The logical table name (e.g., "flights", "passengers")
        version: Override version (defaults to TABLE_VERSION)

    Returns:
        The actual DynamoDB table name

    Raises:
        KeyError: If table not found for the specified version

    Examples:
        >>> get_table_name("flights")  # Uses current TABLE_VERSION
        'flights'  # or 'flights_v2' depending on TABLE_VERSION
        >>> get_table_name("flights", TableVersion.V2)
        'flights_v2'
    """
    version = version or TABLE_VERSION
    tables = V2_TABLES if version == TableVersion.V2 else V1_TABLES

    if logical_name not in tables:
        raise KeyError(
            f"Table '{logical_name}' not found for version {version.value}. "
            f"Available tables: {list(tables.keys())}"
        )

    return tables[logical_name]


def is_v2_only_table(logical_name: str) -> bool:
    """
    Check if a table exists only in V2 (no V1 equivalent).

    Args:
        logical_name: The logical table name

    Returns:
        True if table only exists in V2, False otherwise

    Examples:
        >>> is_v2_only_table("aircraft_rotations")
        True
        >>> is_v2_only_table("flights")
        False
    """
    return logical_name in V2_TABLES and logical_name not in V1_TABLES


def get_all_v2_table_names() -> List[str]:
    """Get list of all V2 table names (actual DynamoDB names)."""
    return list(V2_TABLES.values())


def get_all_v2_logical_names() -> List[str]:
    """Get list of all V2 logical table names."""
    return list(V2_TABLES.keys())


def get_v2_only_tables() -> List[str]:
    """Get list of tables that only exist in V2 (new capabilities)."""
    return [name for name in V2_TABLES.keys() if name not in V1_TABLES]


def get_enhanced_tables() -> List[str]:
    """Get list of tables that exist in both V1 and V2 (enhanced with new columns)."""
    return [name for name in V2_TABLES.keys() if name in V1_TABLES]


def get_table_schema(table_name: str) -> Optional[TableSchema]:
    """
    Get schema definition for a V2 table.

    Args:
        table_name: The actual DynamoDB table name (e.g., "flights_v2")

    Returns:
        TableSchema object or None if not found
    """
    return V2_TABLE_SCHEMAS.get(table_name)


def get_current_version() -> str:
    """Get the current table version as a string."""
    return TABLE_VERSION.value


def is_v2_enabled() -> bool:
    """Check if V2 tables are currently enabled."""
    return TABLE_VERSION == TableVersion.V2


# =============================================================================
# Logging helper for debugging
# =============================================================================

def log_table_config():
    """Print current table configuration for debugging."""
    print(f"Current Table Version: {TABLE_VERSION.value}")
    print(f"V2 Enabled: {is_v2_enabled()}")
    print(f"\nV2-Only Tables ({len(get_v2_only_tables())}):")
    for name in get_v2_only_tables():
        print(f"  - {name} -> {V2_TABLES[name]}")
    print(f"\nEnhanced Tables ({len(get_enhanced_tables())}):")
    for name in get_enhanced_tables():
        v1_name = V1_TABLES.get(name, "N/A")
        v2_name = V2_TABLES.get(name, "N/A")
        print(f"  - {name}: V1={v1_name}, V2={v2_name}")


if __name__ == "__main__":
    log_table_config()
