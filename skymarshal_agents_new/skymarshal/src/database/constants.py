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
