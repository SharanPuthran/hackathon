"""
Database Constants Module

Centralized configuration for DynamoDB table names, GSI names, and agent table access permissions.
This module provides type-safe constants to prevent runtime errors and simplifies configuration management.

Usage:
    from database.constants import FLIGHTS_TABLE, FLIGHT_NUMBER_DATE_INDEX, AGENT_TABLE_ACCESS
"""

from typing import Dict, List, Final

# ============================================================================
# Table Names
# ============================================================================

FLIGHTS_TABLE: Final[str] = "flights"
BOOKINGS_TABLE: Final[str] = "bookings"
PASSENGERS_TABLE: Final[str] = "passengers"
CREW_ROSTER_TABLE: Final[str] = "CrewRoster"
CREW_MEMBERS_TABLE: Final[str] = "CrewMembers"
MAINTENANCE_WORK_ORDERS_TABLE: Final[str] = "MaintenanceWorkOrders"
MAINTENANCE_STAFF_TABLE: Final[str] = "MaintenanceStaff"
MAINTENANCE_ROSTER_TABLE: Final[str] = "maintenance_roster"
AIRCRAFT_AVAILABILITY_TABLE: Final[str] = "AircraftAvailability"
CARGO_FLIGHT_ASSIGNMENTS_TABLE: Final[str] = "CargoFlightAssignments"
CARGO_SHIPMENTS_TABLE: Final[str] = "CargoShipments"
BAGGAGE_TABLE: Final[str] = "Baggage"
WEATHER_TABLE: Final[str] = "Weather"
DISRUPTED_PASSENGERS_TABLE: Final[str] = "disrupted_passengers_scenario"
AIRCRAFT_SWAP_OPTIONS_TABLE: Final[str] = "aircraft_swap_options"
INBOUND_FLIGHT_IMPACT_TABLE: Final[str] = "inbound_flight_impact"
RETURN_FLIGHT_IMPACT_TABLE: Final[str] = "return_flight_impact"

# ============================================================================
# GSI Names
# ============================================================================

# Flights table GSIs
FLIGHT_NUMBER_DATE_INDEX: Final[str] = "flight-number-date-index"
AIRCRAFT_REGISTRATION_INDEX: Final[str] = "aircraft-registration-index"

# Bookings table GSIs
FLIGHT_ID_INDEX: Final[str] = "flight-id-index"
PASSENGER_FLIGHT_INDEX: Final[str] = "passenger-flight-index"  # Priority 1
FLIGHT_STATUS_INDEX: Final[str] = "flight-status-index"  # Priority 1

# CrewRoster table GSIs
FLIGHT_POSITION_INDEX: Final[str] = "flight-position-index"
CREW_DUTY_DATE_INDEX: Final[str] = "crew-duty-date-index"  # Priority 1

# Flights table GSIs (additional)
AIRCRAFT_ROTATION_INDEX: Final[str] = "aircraft-rotation-index"  # Priority 1

# Passengers table GSIs
PASSENGER_ELITE_TIER_INDEX: Final[str] = "passenger-elite-tier-index"  # Priority 1

# CargoFlightAssignments table GSIs
FLIGHT_LOADING_INDEX: Final[str] = "flight-loading-index"
SHIPMENT_INDEX: Final[str] = "shipment-index"

# Baggage table GSIs
BOOKING_INDEX: Final[str] = "booking-index"
LOCATION_STATUS_INDEX: Final[str] = "location-status-index"

# MaintenanceRoster table GSIs
WORKORDER_SHIFT_INDEX: Final[str] = "workorder-shift-index"

# ============================================================================
# Agent Table Access Permissions
# ============================================================================

AGENT_TABLE_ACCESS: Final[Dict[str, List[str]]] = {
    "crew_compliance": [
        FLIGHTS_TABLE,
        CREW_ROSTER_TABLE,
        CREW_MEMBERS_TABLE
    ],
    "maintenance": [
        FLIGHTS_TABLE,
        MAINTENANCE_WORK_ORDERS_TABLE,
        MAINTENANCE_STAFF_TABLE,
        MAINTENANCE_ROSTER_TABLE,
        AIRCRAFT_AVAILABILITY_TABLE
    ],
    "regulatory": [
        FLIGHTS_TABLE,
        CREW_ROSTER_TABLE,
        MAINTENANCE_WORK_ORDERS_TABLE,
        WEATHER_TABLE
    ],
    "network": [
        FLIGHTS_TABLE,
        AIRCRAFT_AVAILABILITY_TABLE
    ],
    "guest_experience": [
        FLIGHTS_TABLE,
        BOOKINGS_TABLE,
        BAGGAGE_TABLE,
        PASSENGERS_TABLE  # For elite tier queries
    ],
    "cargo": [
        FLIGHTS_TABLE,
        CARGO_FLIGHT_ASSIGNMENTS_TABLE,
        CARGO_SHIPMENTS_TABLE
    ],
    "finance": [
        FLIGHTS_TABLE,
        BOOKINGS_TABLE,
        CARGO_FLIGHT_ASSIGNMENTS_TABLE,
        MAINTENANCE_WORK_ORDERS_TABLE
    ],
    "arbitrator": [
        # Arbitrator has read access to all tables for comprehensive analysis
        FLIGHTS_TABLE,
        BOOKINGS_TABLE,
        PASSENGERS_TABLE,
        CREW_ROSTER_TABLE,
        CREW_MEMBERS_TABLE,
        MAINTENANCE_WORK_ORDERS_TABLE,
        MAINTENANCE_STAFF_TABLE,
        MAINTENANCE_ROSTER_TABLE,
        AIRCRAFT_AVAILABILITY_TABLE,
        CARGO_FLIGHT_ASSIGNMENTS_TABLE,
        CARGO_SHIPMENTS_TABLE,
        BAGGAGE_TABLE,
        WEATHER_TABLE
    ]
}

# ============================================================================
# Agent GSI Access Permissions
# ============================================================================

AGENT_GSI_ACCESS: Final[Dict[str, List[str]]] = {
    "crew_compliance": [
        FLIGHT_NUMBER_DATE_INDEX,
        FLIGHT_POSITION_INDEX,
        CREW_DUTY_DATE_INDEX  # Priority 1
    ],
    "maintenance": [
        FLIGHT_NUMBER_DATE_INDEX,
        AIRCRAFT_REGISTRATION_INDEX,
        WORKORDER_SHIFT_INDEX
    ],
    "regulatory": [
        FLIGHT_NUMBER_DATE_INDEX,
        FLIGHT_POSITION_INDEX,
        AIRCRAFT_REGISTRATION_INDEX
    ],
    "network": [
        FLIGHT_NUMBER_DATE_INDEX,
        AIRCRAFT_REGISTRATION_INDEX,
        AIRCRAFT_ROTATION_INDEX  # Priority 1
    ],
    "guest_experience": [
        FLIGHT_NUMBER_DATE_INDEX,
        FLIGHT_ID_INDEX,
        BOOKING_INDEX,
        PASSENGER_FLIGHT_INDEX,  # Priority 1
        FLIGHT_STATUS_INDEX,  # Priority 1
        LOCATION_STATUS_INDEX,
        PASSENGER_ELITE_TIER_INDEX  # Priority 1
    ],
    "cargo": [
        FLIGHT_NUMBER_DATE_INDEX,
        FLIGHT_LOADING_INDEX,
        SHIPMENT_INDEX
    ],
    "finance": [
        FLIGHT_NUMBER_DATE_INDEX,
        FLIGHT_ID_INDEX,
        FLIGHT_LOADING_INDEX,
        AIRCRAFT_REGISTRATION_INDEX
    ],
    "arbitrator": [
        # Arbitrator has access to all GSIs
        FLIGHT_NUMBER_DATE_INDEX,
        AIRCRAFT_REGISTRATION_INDEX,
        AIRCRAFT_ROTATION_INDEX,  # Priority 1
        FLIGHT_ID_INDEX,
        PASSENGER_FLIGHT_INDEX,  # Priority 1
        FLIGHT_STATUS_INDEX,  # Priority 1
        FLIGHT_POSITION_INDEX,
        CREW_DUTY_DATE_INDEX,  # Priority 1
        FLIGHT_LOADING_INDEX,
        SHIPMENT_INDEX,
        BOOKING_INDEX,
        LOCATION_STATUS_INDEX,
        WORKORDER_SHIFT_INDEX,
        PASSENGER_ELITE_TIER_INDEX  # Priority 1
    ]
}

# ============================================================================
# All Tables List (for validation and orchestrator)
# ============================================================================

ALL_TABLES: Final[List[str]] = [
    FLIGHTS_TABLE,
    BOOKINGS_TABLE,
    PASSENGERS_TABLE,
    CREW_ROSTER_TABLE,
    CREW_MEMBERS_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    MAINTENANCE_STAFF_TABLE,
    MAINTENANCE_ROSTER_TABLE,
    AIRCRAFT_AVAILABILITY_TABLE,
    CARGO_FLIGHT_ASSIGNMENTS_TABLE,
    CARGO_SHIPMENTS_TABLE,
    BAGGAGE_TABLE,
    WEATHER_TABLE,
    DISRUPTED_PASSENGERS_TABLE,
    AIRCRAFT_SWAP_OPTIONS_TABLE,
    INBOUND_FLIGHT_IMPACT_TABLE,
    RETURN_FLIGHT_IMPACT_TABLE
]

# ============================================================================
# All GSIs List (for validation)
# ============================================================================

ALL_GSIS: Final[List[str]] = [
    FLIGHT_NUMBER_DATE_INDEX,
    AIRCRAFT_REGISTRATION_INDEX,
    AIRCRAFT_ROTATION_INDEX,  # Priority 1
    FLIGHT_ID_INDEX,
    PASSENGER_FLIGHT_INDEX,  # Priority 1
    FLIGHT_STATUS_INDEX,  # Priority 1
    FLIGHT_POSITION_INDEX,
    CREW_DUTY_DATE_INDEX,  # Priority 1
    FLIGHT_LOADING_INDEX,
    SHIPMENT_INDEX,
    BOOKING_INDEX,
    LOCATION_STATUS_INDEX,
    WORKORDER_SHIFT_INDEX,
    PASSENGER_ELITE_TIER_INDEX  # Priority 1
]

# ============================================================================
# Validation Functions
# ============================================================================

def validate_agent_name(agent_name: str) -> bool:
    """
    Validate that an agent name is recognized.

    Args:
        agent_name: Name of the agent to validate

    Returns:
        True if agent name is valid, False otherwise
    """
    return agent_name in AGENT_TABLE_ACCESS


def get_agent_tables(agent_name: str) -> List[str]:
    """
    Get the list of tables an agent is authorized to access.

    Args:
        agent_name: Name of the agent

    Returns:
        List of table names the agent can access

    Raises:
        ValueError: If agent name is not recognized
    """
    if not validate_agent_name(agent_name):
        raise ValueError(f"Unknown agent: {agent_name}. Valid agents: {list(AGENT_TABLE_ACCESS.keys())}")

    return AGENT_TABLE_ACCESS[agent_name]


def get_agent_gsis(agent_name: str) -> List[str]:
    """
    Get the list of GSIs an agent is authorized to use.

    Args:
        agent_name: Name of the agent

    Returns:
        List of GSI names the agent can use

    Raises:
        ValueError: If agent name is not recognized
    """
    if not validate_agent_name(agent_name):
        raise ValueError(f"Unknown agent: {agent_name}. Valid agents: {list(AGENT_GSI_ACCESS.keys())}")

    return AGENT_GSI_ACCESS[agent_name]


def can_agent_access_table(agent_name: str, table_name: str) -> bool:
    """
    Check if an agent is authorized to access a specific table.

    Args:
        agent_name: Name of the agent
        table_name: Name of the table

    Returns:
        True if agent can access table, False otherwise
    """
    if not validate_agent_name(agent_name):
        return False

    return table_name in AGENT_TABLE_ACCESS[agent_name]


def can_agent_use_gsi(agent_name: str, gsi_name: str) -> bool:
    """
    Check if an agent is authorized to use a specific GSI.

    Args:
        agent_name: Name of the agent
        gsi_name: Name of the GSI

    Returns:
        True if agent can use GSI, False otherwise
    """
    if not validate_agent_name(agent_name):
        return False

    return gsi_name in AGENT_GSI_ACCESS[agent_name]


# ============================================================================
# V2 Table Names (New tables with _v2 suffix)
# ============================================================================

# Enhanced tables (have V1 equivalent with additional columns)
FLIGHTS_V2_TABLE: Final[str] = "flights_v2"
PASSENGERS_V2_TABLE: Final[str] = "passengers_v2"
BAGGAGE_V2_TABLE: Final[str] = "baggage_v2"
CREW_ROSTER_V2_TABLE: Final[str] = "crew_roster_v2"
AIRCRAFT_V2_TABLE: Final[str] = "aircraft_v2"
CARGO_SHIPMENTS_V2_TABLE: Final[str] = "cargo_shipments_v2"
WEATHER_V2_TABLE: Final[str] = "weather_v2"
FINANCIAL_PARAMETERS_V2_TABLE: Final[str] = "financial_parameters_v2"
SAFETY_CONSTRAINTS_V2_TABLE: Final[str] = "safety_constraints_v2"
RECOVERY_COST_MATRIX_V2_TABLE: Final[str] = "recovery_cost_matrix_v2"
COST_BREAKDOWN_V2_TABLE: Final[str] = "cost_breakdown_v2"

# New V2-only tables (no V1 equivalent - new capabilities)
AIRCRAFT_ROTATIONS_V2_TABLE: Final[str] = "aircraft_rotations_v2"
OAL_FLIGHTS_V2_TABLE: Final[str] = "oal_flights_v2"
AIRPORT_CURFEWS_V2_TABLE: Final[str] = "airport_curfews_v2"
AIRPORT_SLOTS_V2_TABLE: Final[str] = "airport_slots_v2"
COLD_CHAIN_FACILITIES_V2_TABLE: Final[str] = "cold_chain_facilities_v2"
COMPENSATION_RULES_V2_TABLE: Final[str] = "compensation_rules_v2"
GROUND_EQUIPMENT_V2_TABLE: Final[str] = "ground_equipment_v2"
INTERLINE_AGREEMENTS_V2_TABLE: Final[str] = "interline_agreements_v2"
MAINTENANCE_CONSTRAINTS_V2_TABLE: Final[str] = "maintenance_constraints_v2"
MINIMUM_CONNECTION_TIMES_V2_TABLE: Final[str] = "minimum_connection_times_v2"
RESERVE_CREW_V2_TABLE: Final[str] = "reserve_crew_v2"
TURNAROUND_REQUIREMENTS_V2_TABLE: Final[str] = "turnaround_requirements_v2"

# ============================================================================
# V2 GSI Names
# ============================================================================

# passengers_v2 GSIs (new)
PNR_INDEX: Final[str] = "pnr-index"
FIRST_LEG_FLIGHT_INDEX: Final[str] = "first-leg-flight-index"

# baggage_v2 GSIs (new)
BAGGAGE_PASSENGER_INDEX: Final[str] = "passenger-index"
BAGGAGE_FLIGHT_INDEX: Final[str] = "flight-index"

# crew_roster_v2 GSIs (new)
EMPLOYEE_ID_INDEX: Final[str] = "employee-id-index"

# aircraft_v2 GSIs (new)
AIRCRAFT_STATUS_INDEX: Final[str] = "status-index"
AIRCRAFT_TYPE_INDEX: Final[str] = "aircraft-type-index"
MEL_STATUS_INDEX: Final[str] = "mel-status-index"

# cargo_shipments_v2 GSIs (new)
AWB_INDEX: Final[str] = "awb-index"
CARGO_FIRST_LEG_FLIGHT_INDEX: Final[str] = "cargo-first-leg-flight-index"
CARGO_TYPE_INDEX: Final[str] = "cargo-type-index"

# financial_parameters_v2, safety_constraints_v2, cost_breakdown_v2 GSIs
CATEGORY_INDEX: Final[str] = "category-index"

# recovery_cost_matrix_v2 GSIs
SCENARIO_TYPE_INDEX: Final[str] = "scenario-type-index"
RECOVERY_OPTION_INDEX: Final[str] = "recovery-option-index"

# aircraft_rotations_v2 GSIs
AIRCRAFT_SEQUENCE_INDEX: Final[str] = "aircraft-sequence-index"
ROTATION_FLIGHT_ID_INDEX: Final[str] = "rotation-flight-id-index"

# oal_flights_v2 GSIs
ROUTE_INDEX: Final[str] = "route-index"
AIRLINE_INDEX: Final[str] = "airline-index"

# airport_slots_v2 GSIs
SLOT_FLIGHT_INDEX: Final[str] = "slot-flight-index"
SLOT_AIRPORT_INDEX: Final[str] = "slot-airport-index"

# ground_equipment_v2 GSIs
EQUIPMENT_AIRPORT_TYPE_INDEX: Final[str] = "airport-type-index"

# interline_agreements_v2 GSIs
PARTNER_AIRLINE_INDEX: Final[str] = "partner-airline-index"

# maintenance_constraints_v2 GSIs
CONSTRAINT_AIRCRAFT_INDEX: Final[str] = "constraint-aircraft-index"

# minimum_connection_times_v2 GSIs
MCT_AIRPORT_CONNECTION_INDEX: Final[str] = "airport-connection-index"

# reserve_crew_v2 GSIs
RESERVE_BASE_STATUS_INDEX: Final[str] = "base-status-index"
RESERVE_ROLE_INDEX: Final[str] = "role-index"

# turnaround_requirements_v2 GSIs
TURNAROUND_FLIGHT_INDEX: Final[str] = "turnaround-flight-index"
TURNAROUND_AIRPORT_INDEX: Final[str] = "turnaround-airport-index"

# Common GSIs (used by multiple V2 tables)
AIRPORT_INDEX: Final[str] = "airport-index"
REGULATION_INDEX: Final[str] = "regulation-index"

# ============================================================================
# All V2 Tables List
# ============================================================================

ALL_V2_TABLES: Final[List[str]] = [
    # Enhanced tables
    FLIGHTS_V2_TABLE,
    PASSENGERS_V2_TABLE,
    BAGGAGE_V2_TABLE,
    CREW_ROSTER_V2_TABLE,
    AIRCRAFT_V2_TABLE,
    CARGO_SHIPMENTS_V2_TABLE,
    WEATHER_V2_TABLE,
    FINANCIAL_PARAMETERS_V2_TABLE,
    SAFETY_CONSTRAINTS_V2_TABLE,
    RECOVERY_COST_MATRIX_V2_TABLE,
    COST_BREAKDOWN_V2_TABLE,
    # New V2-only tables
    AIRCRAFT_ROTATIONS_V2_TABLE,
    OAL_FLIGHTS_V2_TABLE,
    AIRPORT_CURFEWS_V2_TABLE,
    AIRPORT_SLOTS_V2_TABLE,
    COLD_CHAIN_FACILITIES_V2_TABLE,
    COMPENSATION_RULES_V2_TABLE,
    GROUND_EQUIPMENT_V2_TABLE,
    INTERLINE_AGREEMENTS_V2_TABLE,
    MAINTENANCE_CONSTRAINTS_V2_TABLE,
    MINIMUM_CONNECTION_TIMES_V2_TABLE,
    RESERVE_CREW_V2_TABLE,
    TURNAROUND_REQUIREMENTS_V2_TABLE,
]

# ============================================================================
# AWS DynamoDB Configuration
# ============================================================================

# Default AWS region (can be overridden by environment variable)
DEFAULT_AWS_REGION: Final[str] = "us-east-1"

# DynamoDB billing mode
BILLING_MODE: Final[str] = "PAY_PER_REQUEST"

# Query limits
DEFAULT_QUERY_LIMIT: Final[int] = 100
MAX_BATCH_SIZE: Final[int] = 25  # DynamoDB batch write limit

# Timeout settings
QUERY_TIMEOUT_SECONDS: Final[int] = 60
GSI_ACTIVATION_TIMEOUT_SECONDS: Final[int] = 600  # 10 minutes
