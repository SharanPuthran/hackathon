"""Database tool factories for SkyMarshal agents

This module provides version-aware database tools that support both V1 (original)
and V2 (new) table schemas. The active table version is controlled by the
TABLE_VERSION setting in table_config.py.

Usage:
    from database.tools import get_crew_compliance_tools, get_v2_tools

    # Get standard tools (uses current version)
    crew_tools = get_crew_compliance_tools()

    # Get V2-specific tools (requires V2 tables)
    v2_tools = get_v2_tools()
"""

from langchain.tools import tool
from database.dynamodb import DynamoDBClient
from database.constants import (
    # Table names (V1)
    FLIGHTS_TABLE,
    BOOKINGS_TABLE,
    CREW_ROSTER_TABLE,
    CREW_MEMBERS_TABLE,
    MAINTENANCE_WORK_ORDERS_TABLE,
    AIRCRAFT_AVAILABILITY_TABLE,
    CARGO_SHIPMENTS_TABLE,
    CARGO_FLIGHT_ASSIGNMENTS_TABLE,
    BAGGAGE_TABLE,
    WEATHER_TABLE,
    PASSENGERS_TABLE,
    # V2 Table names
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
    # GSI names
    FLIGHT_POSITION_INDEX,
    PASSENGER_FLIGHT_INDEX,
    FLIGHT_STATUS_INDEX,
    BOOKING_INDEX,
    SHIPMENT_INDEX,
    FLIGHT_LOADING_INDEX,
    WORKORDER_SHIFT_INDEX,
    # Agent access validation
    get_agent_tables,
    can_agent_access_table
)
from database.table_config import TABLE_VERSION, TableVersion, is_v2_enabled
import logging

logger = logging.getLogger(__name__)


# ============================================================
# CREW COMPLIANCE TOOLS
# ============================================================


def get_crew_compliance_tools():
    """Get database tools for crew compliance agent"""
    db = DynamoDBClient()
    
    # Validate agent has access to required tables
    agent_name = "crew_compliance"
    required_tables = get_agent_tables(agent_name)
    logger.info(f"Crew compliance agent authorized for tables: {required_tables}")

    @tool
    def query_flight_crew_roster(flight_id: str) -> str:
        """
        Query crew roster for a flight from DynamoDB.

        Args:
            flight_id: The flight ID to query crew roster for

        Returns:
            JSON string containing crew roster with crew_id, position_id, duty times, status
        """
        try:
            # Validate table access
            if not can_agent_access_table(agent_name, CREW_ROSTER_TABLE):
                return db.to_json({
                    "error": f"Agent {agent_name} not authorized to access {CREW_ROSTER_TABLE}"
                })
            
            roster = db.query_crew_roster_by_flight(flight_id)
            result = {
                "flight_id": flight_id,
                "crew_count": len(roster),
                "roster": roster,
                "query_method": f"GSI: {FLIGHT_POSITION_INDEX}",
                "table": CREW_ROSTER_TABLE
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_flight_crew_roster: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    @tool
    def query_crew_member_details(crew_id: str) -> str:
        """
        Query crew member details from DynamoDB.

        Args:
            crew_id: The crew member ID to query

        Returns:
            JSON string containing crew member details including qualifications, type ratings, etc.
        """
        try:
            # Validate table access
            if not can_agent_access_table(agent_name, CREW_MEMBERS_TABLE):
                return db.to_json({
                    "error": f"Agent {agent_name} not authorized to access {CREW_MEMBERS_TABLE}"
                })
            
            crew_member = db.get_crew_member(crew_id)
            if not crew_member:
                return db.to_json({"error": f"Crew member {crew_id} not found"})

            result = {
                "crew_id": crew_id,
                "crew_details": crew_member,
                "query_method": "Direct key lookup",
                "table": CREW_MEMBERS_TABLE
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_crew_member_details: {e}")
            return db.to_json({"error": str(e), "crew_id": crew_id})

    @tool
    def query_crew_roster_and_members(flight_id: str) -> str:
        """
        Query crew roster and all crew member details for a flight using batch operations.
        
        This is an optimized tool that reduces query count from 1+N to just 2 queries:
        - 1 query for the crew roster (using GSI)
        - 1 batch query for all crew member details
        
        Args:
            flight_id: The flight ID to query crew roster and members for
            
        Returns:
            JSON string containing crew roster and full crew member details
        """
        try:
            # Validate table access
            if not can_agent_access_table(agent_name, CREW_ROSTER_TABLE):
                return db.to_json({
                    "error": f"Agent {agent_name} not authorized to access {CREW_ROSTER_TABLE}"
                })
            if not can_agent_access_table(agent_name, CREW_MEMBERS_TABLE):
                return db.to_json({
                    "error": f"Agent {agent_name} not authorized to access {CREW_MEMBERS_TABLE}"
                })
            
            # Query 1: Get crew roster for the flight
            roster = db.query_crew_roster_by_flight(flight_id)
            
            if not roster:
                return db.to_json({
                    "flight_id": flight_id,
                    "crew_count": 0,
                    "roster": [],
                    "crew_members": [],
                    "query_method": "GSI + Batch",
                    "query_count": 1
                })
            
            # Extract crew IDs from roster
            crew_ids = [assignment.get("crew_id") for assignment in roster if assignment.get("crew_id")]
            
            # Query 2: Batch get all crew member details
            crew_members = db.batch_get_crew_members(crew_ids)
            
            # Create a lookup map for easy access
            crew_member_map = {member.get("crew_id"): member for member in crew_members}
            
            # Enrich roster with crew member details
            enriched_roster = []
            for assignment in roster:
                crew_id = assignment.get("crew_id")
                enriched_assignment = {
                    **assignment,
                    "crew_member_details": crew_member_map.get(crew_id, None)
                }
                enriched_roster.append(enriched_assignment)
            
            return db.to_json({
                "flight_id": flight_id,
                "crew_count": len(roster),
                "roster": enriched_roster,
                "crew_members": crew_members,
                "query_method": f"GSI: {FLIGHT_POSITION_INDEX} + Batch: CrewMembers",
                "query_count": 2,
                "optimization": f"Reduced from {1 + len(crew_ids)} queries to 2 queries"
            })
        except Exception as e:
            logger.error(f"Error in query_crew_roster_and_members: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    return [query_flight_crew_roster, query_crew_member_details, query_crew_roster_and_members]


# ============================================================
# MAINTENANCE TOOLS
# ============================================================


def get_maintenance_tools():
    """Get database tools for maintenance agent"""
    db = DynamoDBClient()

    @tool
    def check_aircraft_availability(aircraft_registration: str, valid_from: str) -> str:
        """
        Check aircraft availability and MEL status from DynamoDB.

        Args:
            aircraft_registration: Aircraft registration (e.g., "A6-APX")
            valid_from: Valid from timestamp in ISO format

        Returns:
            JSON string containing aircraft MEL status, deferred items, airworthiness
        """
        try:
            availability = db.get_aircraft_availability(
                aircraft_registration, valid_from
            )
            if not availability:
                return db.to_json(
                    {
                        "error": f"Aircraft {aircraft_registration} not found",
                        "aircraft_registration": aircraft_registration,
                    }
                )

            result = {
                "aircraft_registration": aircraft_registration,
                "availability": availability,
                "query_method": "Composite key lookup",
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in check_aircraft_availability: {e}")
            return db.to_json(
                {"error": str(e), "aircraft_registration": aircraft_registration}
            )

    @tool
    def query_maintenance_workorders(aircraft_registration: str) -> str:
        """
        Query maintenance work orders for an aircraft from DynamoDB.

        Args:
            aircraft_registration: Aircraft registration (e.g., "A6-APX")

        Returns:
            JSON string containing maintenance work orders, status, technicians assigned
        """
        try:
            workorders = db.query_maintenance_workorders(aircraft_registration)
            result = {
                "aircraft_registration": aircraft_registration,
                "workorder_count": len(workorders),
                "workorders": workorders,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_maintenance_workorders: {e}")
            return db.to_json(
                {"error": str(e), "aircraft_registration": aircraft_registration}
            )

    @tool
    def query_maintenance_roster(workorder_id: str) -> str:
        """
        Query maintenance staff assigned to a work order from DynamoDB.

        Args:
            workorder_id: Work order ID (e.g., "WO-10193")

        Returns:
            JSON string containing staff assignments, shift times
        """
        try:
            roster = db.query_maintenance_roster_by_workorder(workorder_id)
            result = {
                "workorder_id": workorder_id,
                "staff_count": len(roster),
                "roster": roster,
                "query_method": "GSI: workorder-shift-index",
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_maintenance_roster: {e}")
            return db.to_json({"error": str(e), "workorder_id": workorder_id})

    return [
        check_aircraft_availability,
        query_maintenance_workorders,
        query_maintenance_roster,
    ]


# ============================================================
# REGULATORY TOOLS
# ============================================================


def get_regulatory_tools():
    """Get database tools for regulatory agent"""
    db = DynamoDBClient()

    @tool
    def query_weather_forecast(airport_code: str, forecast_time: str) -> str:
        """
        Query weather forecast for an airport from DynamoDB.

        Args:
            airport_code: Airport IATA code (e.g., "AUH", "LHR")
            forecast_time: Forecast timestamp in ISO format

        Returns:
            JSON string containing weather forecast data
        """
        try:
            weather = db.get_weather(airport_code, forecast_time)
            if not weather:
                return db.to_json(
                    {
                        "error": f"Weather data not found for {airport_code}",
                        "airport_code": airport_code,
                    }
                )

            result = {
                "airport_code": airport_code,
                "forecast_time": forecast_time,
                "weather": weather,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_weather_forecast: {e}")
            return db.to_json({"error": str(e), "airport_code": airport_code})

    @tool
    def query_flight_details(flight_id: str) -> str:
        """
        Query flight details for regulatory checks (NOTAMs, curfews, etc.) from DynamoDB.

        Args:
            flight_id: Flight ID

        Returns:
            JSON string containing flight route, schedule, aircraft type
        """
        try:
            flight = db.get_flight(flight_id)
            if not flight:
                return db.to_json(
                    {"error": f"Flight {flight_id} not found", "flight_id": flight_id}
                )

            result = {"flight_id": flight_id, "flight_details": flight}
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_flight_details: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    return [query_weather_forecast, query_flight_details]


# ============================================================
# NETWORK TOOLS
# ============================================================


def get_network_tools():
    """Get database tools for network agent"""
    db = DynamoDBClient()

    @tool
    def query_inbound_flight_impact(scenario: str) -> str:
        """
        Query inbound flight impact analysis from DynamoDB.

        Args:
            scenario: Scenario identifier

        Returns:
            JSON string containing inbound flight impact data
        """
        try:
            impact = db.get_inbound_flight_impact(scenario)
            if not impact:
                return db.to_json(
                    {
                        "error": f"Impact data not found for scenario {scenario}",
                        "scenario": scenario,
                    }
                )

            result = {"scenario": scenario, "impact": impact}
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_inbound_flight_impact: {e}")
            return db.to_json({"error": str(e), "scenario": scenario})

    @tool
    def query_flight_network(flight_id: str) -> str:
        """
        Query flight details for network analysis (rotation, connections, etc.) from DynamoDB.

        Args:
            flight_id: Flight ID

        Returns:
            JSON string containing flight network data
        """
        try:
            flight = db.get_flight(flight_id)
            if not flight:
                return db.to_json(
                    {"error": f"Flight {flight_id} not found", "flight_id": flight_id}
                )

            result = {"flight_id": flight_id, "flight_details": flight}
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_flight_network: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    @tool
    def query_multiple_flights_network(flight_ids: str) -> str:
        """
        Query multiple flight details for network analysis using batch operations.
        
        This is an optimized tool that reduces query count from N to just 1 batch query
        when analyzing multiple flights (e.g., connecting flights, rotation flights,
        affected flights in a propagation chain).
        
        Args:
            flight_ids: Comma-separated list of flight IDs (e.g., "FL001,FL002,FL003")
            
        Returns:
            JSON string containing flight details for all requested flights
        """
        try:
            # Parse comma-separated flight IDs
            flight_id_list = [fid.strip() for fid in flight_ids.split(",") if fid.strip()]
            
            if not flight_id_list:
                return db.to_json({
                    "error": "No flight IDs provided",
                    "flight_ids": flight_ids
                })
            
            # Batch get all flight details
            flights = db.batch_get_flights(flight_id_list)
            
            # Create a lookup map for easy access
            flight_map = {flight.get("flight_id"): flight for flight in flights}
            
            # Identify any missing flights
            found_ids = set(flight_map.keys())
            requested_ids = set(flight_id_list)
            missing_ids = requested_ids - found_ids
            
            return db.to_json({
                "flight_count": len(flights),
                "flights": flights,
                "flight_map": flight_map,
                "requested_count": len(flight_id_list),
                "found_count": len(flights),
                "missing_ids": list(missing_ids) if missing_ids else [],
                "query_method": "Batch: Flights",
                "optimization": f"Reduced from {len(flight_id_list)} queries to 1 batch query"
            })
        except Exception as e:
            logger.error(f"Error in query_multiple_flights_network: {e}")
            return db.to_json({"error": str(e), "flight_ids": flight_ids})

    return [query_inbound_flight_impact, query_flight_network, query_multiple_flights_network]


# ============================================================
# GUEST EXPERIENCE TOOLS
# ============================================================


def get_guest_experience_tools():
    """Get database tools for guest experience agent"""
    db = DynamoDBClient()

    @tool
    def query_passenger_bookings(passenger_id: str) -> str:
        """
        Query all bookings for a passenger from DynamoDB.

        Args:
            passenger_id: Passenger ID

        Returns:
            JSON string containing passenger booking history
        """
        try:
            bookings = db.query_bookings_by_passenger(passenger_id)
            result = {
                "passenger_id": passenger_id,
                "booking_count": len(bookings),
                "bookings": bookings,
                "query_method": "GSI: passenger-flight-index",
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_passenger_bookings: {e}")
            return db.to_json({"error": str(e), "passenger_id": passenger_id})

    @tool
    def query_flight_bookings(flight_id: str, booking_status: str = None) -> str:
        """
        Query bookings for a flight from DynamoDB.

        Args:
            flight_id: Flight ID
            booking_status: Optional booking status filter (e.g., "Confirmed")

        Returns:
            JSON string containing flight bookings and passenger manifest
        """
        try:
            bookings = db.query_bookings_by_flight(flight_id, booking_status)
            result = {
                "flight_id": flight_id,
                "booking_status_filter": booking_status,
                "booking_count": len(bookings),
                "bookings": bookings,
                "query_method": "GSI: flight-status-index",
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_flight_bookings: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    @tool
    def query_passenger_baggage(booking_id: str) -> str:
        """
        Query baggage for a booking from DynamoDB.

        Args:
            booking_id: Booking ID

        Returns:
            JSON string containing baggage tracking information
        """
        try:
            baggage = db.query_baggage_by_booking(booking_id)
            result = {
                "booking_id": booking_id,
                "baggage_count": len(baggage),
                "baggage": baggage,
                "query_method": "GSI: booking-index",
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_passenger_baggage: {e}")
            return db.to_json({"error": str(e), "booking_id": booking_id})

    @tool
    def get_passenger_details(passenger_id: str) -> str:
        """
        Get passenger details from DynamoDB.

        Args:
            passenger_id: Passenger ID

        Returns:
            JSON string containing passenger profile, loyalty status, special needs
        """
        try:
            passenger = db.get_passenger(passenger_id)
            if not passenger:
                return db.to_json(
                    {
                        "error": f"Passenger {passenger_id} not found",
                        "passenger_id": passenger_id,
                    }
                )

            result = {"passenger_id": passenger_id, "passenger_details": passenger}
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in get_passenger_details: {e}")
            return db.to_json({"error": str(e), "passenger_id": passenger_id})

    @tool
    def query_flight_bookings_with_passengers(flight_id: str, booking_status: str = None) -> str:
        """
        Query bookings for a flight and get all passenger details using batch operations.
        
        This is an optimized tool that reduces query count from 1+N to just 2 queries:
        - 1 query for the flight bookings (using GSI)
        - 1 batch query for all passenger details
        
        Args:
            flight_id: Flight ID
            booking_status: Optional booking status filter (e.g., "Confirmed")
            
        Returns:
            JSON string containing flight bookings and full passenger details
        """
        try:
            # Query 1: Get bookings for the flight
            bookings = db.query_bookings_by_flight(flight_id, booking_status)
            
            if not bookings:
                return db.to_json({
                    "flight_id": flight_id,
                    "booking_status_filter": booking_status,
                    "booking_count": 0,
                    "bookings": [],
                    "passengers": [],
                    "query_method": "GSI + Batch",
                    "query_count": 1
                })
            
            # Extract passenger IDs from bookings
            passenger_ids = [booking.get("passenger_id") for booking in bookings if booking.get("passenger_id")]
            
            # Query 2: Batch get all passenger details
            passengers = db.batch_get_passengers(passenger_ids)
            
            # Create a lookup map for easy access
            passenger_map = {passenger.get("passenger_id"): passenger for passenger in passengers}
            
            # Enrich bookings with passenger details
            enriched_bookings = []
            for booking in bookings:
                passenger_id = booking.get("passenger_id")
                enriched_booking = {
                    **booking,
                    "passenger_details": passenger_map.get(passenger_id, None)
                }
                enriched_bookings.append(enriched_booking)
            
            return db.to_json({
                "flight_id": flight_id,
                "booking_status_filter": booking_status,
                "booking_count": len(bookings),
                "bookings": enriched_bookings,
                "passengers": passengers,
                "query_method": f"GSI: flight-status-index + Batch: Passengers",
                "query_count": 2,
                "optimization": f"Reduced from {1 + len(passenger_ids)} queries to 2 queries"
            })
        except Exception as e:
            logger.error(f"Error in query_flight_bookings_with_passengers: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    return [
        query_passenger_bookings,
        query_flight_bookings,
        query_passenger_baggage,
        get_passenger_details,
        query_flight_bookings_with_passengers,
    ]


# ============================================================
# CARGO TOOLS
# ============================================================


def get_cargo_tools():
    """Get database tools for cargo agent"""
    db = DynamoDBClient()

    @tool
    def track_cargo_shipment(shipment_id: str) -> str:
        """
        Track cargo shipment across all flights from DynamoDB.

        Args:
            shipment_id: Cargo shipment ID

        Returns:
            JSON string containing shipment routing, flight assignments, loading status
        """
        try:
            assignments = db.query_cargo_by_shipment(shipment_id)
            shipment = db.get_cargo_shipment(shipment_id)

            result = {
                "shipment_id": shipment_id,
                "shipment_details": shipment,
                "flight_assignment_count": len(assignments),
                "flight_assignments": assignments,
                "query_method": "GSI: shipment-index",
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in track_cargo_shipment: {e}")
            return db.to_json({"error": str(e), "shipment_id": shipment_id})

    @tool
    def query_flight_cargo_manifest(flight_id: str, loading_status: str = None) -> str:
        """
        Query cargo manifest for a flight from DynamoDB.

        Args:
            flight_id: Flight ID
            loading_status: Optional loading status filter (e.g., "LOADED")

        Returns:
            JSON string containing cargo manifest, weight, special handling
        """
        try:
            cargo = db.query_cargo_by_flight(flight_id, loading_status)

            # Calculate total weight
            total_weight = sum(
                float(item.get("weight_on_flight_kg", 0)) for item in cargo
            )

            result = {
                "flight_id": flight_id,
                "loading_status_filter": loading_status,
                "cargo_count": len(cargo),
                "total_weight_kg": total_weight,
                "cargo": cargo,
                "query_method": "GSI: flight-loading-index",
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_flight_cargo_manifest: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    @tool
    def query_flight_cargo_manifest_with_shipments(flight_id: str, loading_status: str = None) -> str:
        """
        Query cargo manifest for a flight and get all shipment details using batch operations.
        
        This is an optimized tool that reduces query count from 1+N to just 2 queries:
        - 1 query for the cargo manifest (using GSI)
        - 1 batch query for all shipment details
        
        Args:
            flight_id: Flight ID
            loading_status: Optional loading status filter (e.g., "LOADED")
            
        Returns:
            JSON string containing cargo manifest and full shipment details
        """
        try:
            # Query 1: Get cargo assignments for the flight
            cargo = db.query_cargo_by_flight(flight_id, loading_status)
            
            if not cargo:
                return db.to_json({
                    "flight_id": flight_id,
                    "loading_status_filter": loading_status,
                    "cargo_count": 0,
                    "total_weight_kg": 0,
                    "cargo": [],
                    "shipments": [],
                    "query_method": "GSI + Batch",
                    "query_count": 1
                })
            
            # Calculate total weight
            total_weight = sum(
                float(item.get("weight_on_flight_kg", 0)) for item in cargo
            )
            
            # Extract shipment IDs from cargo assignments
            shipment_ids = [assignment.get("shipment_id") for assignment in cargo if assignment.get("shipment_id")]
            
            # Query 2: Batch get all shipment details
            shipments = db.batch_get_cargo_shipments(shipment_ids)
            
            # Create a lookup map for easy access
            shipment_map = {shipment.get("shipment_id"): shipment for shipment in shipments}
            
            # Enrich cargo assignments with shipment details
            enriched_cargo = []
            for assignment in cargo:
                shipment_id = assignment.get("shipment_id")
                enriched_assignment = {
                    **assignment,
                    "shipment_details": shipment_map.get(shipment_id, None)
                }
                enriched_cargo.append(enriched_assignment)
            
            return db.to_json({
                "flight_id": flight_id,
                "loading_status_filter": loading_status,
                "cargo_count": len(cargo),
                "total_weight_kg": total_weight,
                "cargo": enriched_cargo,
                "shipments": shipments,
                "query_method": f"GSI: flight-loading-index + Batch: CargoShipments",
                "query_count": 2,
                "optimization": f"Reduced from {1 + len(shipment_ids)} queries to 2 queries"
            })
        except Exception as e:
            logger.error(f"Error in query_flight_cargo_manifest_with_shipments: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    return [track_cargo_shipment, query_flight_cargo_manifest, query_flight_cargo_manifest_with_shipments]


# ============================================================
# FINANCE TOOLS
# ============================================================


def get_finance_tools():
    """Get database tools for finance agent (minimal, mostly calculation-based)"""
    db = DynamoDBClient()

    @tool
    def query_flight_for_cost_analysis(flight_id: str) -> str:
        """
        Query flight details for cost analysis from DynamoDB.

        Args:
            flight_id: Flight ID

        Returns:
            JSON string containing flight details needed for cost calculations
        """
        try:
            flight = db.get_flight(flight_id)
            if not flight:
                return db.to_json(
                    {"error": f"Flight {flight_id} not found", "flight_id": flight_id}
                )

            result = {"flight_id": flight_id, "flight_details": flight}
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_flight_for_cost_analysis: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    return [query_flight_for_cost_analysis]


# ============================================================
# V2 TOOLS (NEW CAPABILITIES)
# ============================================================


def get_v2_tools():
    """
    Get V2-specific database tools for enhanced capabilities.

    These tools access V2-only tables that provide new functionality:
    - Aircraft rotations for cascade analysis
    - Airport curfews and slots for regulatory compliance
    - OAL flights for rebooking options
    - Cold chain facilities for cargo handling
    - Compensation rules for EU261 compliance
    - Ground equipment availability
    - Reserve crew pool
    - Turnaround requirements
    - Minimum connection times
    - Interline agreements
    - Maintenance constraints

    Returns:
        List of tools if V2 is enabled, empty list otherwise
    """
    if not is_v2_enabled():
        logger.warning("V2 tools requested but V2 is not enabled. Set TABLE_VERSION=V2 in table_config.py")
        return []

    db = DynamoDBClient()

    @tool
    def query_aircraft_rotations(aircraft_registration: str) -> str:
        """
        Query aircraft rotation sequence (V2-only).

        Shows the complete flight chain for an aircraft, useful for
        cascade impact analysis when a flight is delayed or canceled.

        Args:
            aircraft_registration: Aircraft registration (e.g., "A6-BNC")

        Returns:
            JSON string containing rotation sequence with flight chain
        """
        try:
            rotations = db.get_aircraft_rotations(aircraft_registration)
            result = {
                "aircraft_registration": aircraft_registration,
                "rotation_count": len(rotations),
                "rotations": rotations,
                "table": AIRCRAFT_ROTATIONS_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_aircraft_rotations: {e}")
            return db.to_json({"error": str(e), "aircraft_registration": aircraft_registration})

    @tool
    def query_airport_curfews(airport_code: str) -> str:
        """
        Query airport curfew restrictions (V2-only).

        Returns night curfew times, exceptions, and special restrictions
        for regulatory compliance checking.

        Args:
            airport_code: IATA airport code (e.g., "LHR")

        Returns:
            JSON string containing curfew details
        """
        try:
            curfews = db.get_airport_curfews(airport_code)
            result = {
                "airport_code": airport_code,
                "curfew_count": len(curfews),
                "curfews": curfews,
                "table": AIRPORT_CURFEWS_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_airport_curfews: {e}")
            return db.to_json({"error": str(e), "airport_code": airport_code})

    @tool
    def query_airport_slots(flight_id: str) -> str:
        """
        Query airport slot allocations for a flight (V2-only).

        Returns slot times, windows, criticality, and penalties for
        slot management and compliance.

        Args:
            flight_id: Flight ID

        Returns:
            JSON string containing slot details
        """
        try:
            slots = db.get_airport_slots(flight_id)
            result = {
                "flight_id": flight_id,
                "slot_count": len(slots),
                "slots": slots,
                "table": AIRPORT_SLOTS_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_airport_slots: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    @tool
    def query_oal_rebooking_options(origin: str, destination: str) -> str:
        """
        Query Other Airline (OAL) rebooking options (V2-only).

        Returns available partner airline flights for passenger rebooking
        during disruptions.

        Args:
            origin: Origin airport code
            destination: Destination airport code

        Returns:
            JSON string containing OAL flight options
        """
        try:
            oal_flights = db.get_oal_flights(origin, destination)
            result = {
                "origin": origin,
                "destination": destination,
                "option_count": len(oal_flights),
                "oal_flights": oal_flights,
                "table": OAL_FLIGHTS_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_oal_rebooking_options: {e}")
            return db.to_json({"error": str(e), "origin": origin, "destination": destination})

    @tool
    def query_cold_chain_facilities(airport_code: str) -> str:
        """
        Query cold chain storage facilities at airport (V2-only).

        Returns temperature-controlled facilities for pharma, perishables,
        and other temperature-sensitive cargo.

        Args:
            airport_code: IATA airport code

        Returns:
            JSON string containing cold chain facility details
        """
        try:
            facilities = db.get_cold_chain_facilities(airport_code)
            result = {
                "airport_code": airport_code,
                "facility_count": len(facilities),
                "facilities": facilities,
                "table": COLD_CHAIN_FACILITIES_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_cold_chain_facilities: {e}")
            return db.to_json({"error": str(e), "airport_code": airport_code})

    @tool
    def query_compensation_rules(regulation: str) -> str:
        """
        Query compensation rules by regulation (V2-only).

        Returns EU261 or other regulatory compensation requirements
        based on delay duration, distance, and cancellation conditions.

        Args:
            regulation: Regulation code (e.g., "EU261")

        Returns:
            JSON string containing compensation rules
        """
        try:
            rules = db.get_compensation_rules(regulation)
            result = {
                "regulation": regulation,
                "rule_count": len(rules),
                "rules": rules,
                "table": COMPENSATION_RULES_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_compensation_rules: {e}")
            return db.to_json({"error": str(e), "regulation": regulation})

    @tool
    def query_ground_equipment(airport_code: str, equipment_type: str = None) -> str:
        """
        Query ground equipment availability at airport (V2-only).

        Returns GPU, ASU, cold chain trucks, and other ground equipment
        status for turnaround planning.

        Args:
            airport_code: IATA airport code
            equipment_type: Optional equipment type filter (e.g., "GPU")

        Returns:
            JSON string containing ground equipment details
        """
        try:
            equipment = db.get_ground_equipment(airport_code, equipment_type)
            result = {
                "airport_code": airport_code,
                "equipment_type_filter": equipment_type,
                "equipment_count": len(equipment),
                "equipment": equipment,
                "table": GROUND_EQUIPMENT_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_ground_equipment: {e}")
            return db.to_json({"error": str(e), "airport_code": airport_code})

    @tool
    def query_reserve_crew(base: str, status: str = None) -> str:
        """
        Query reserve crew availability at base (V2-only).

        Returns available reserve crew members for disruption callout,
        including qualifications and availability times.

        Args:
            base: Crew base location (e.g., "AUH", "BKK")
            status: Optional status filter (e.g., "AVAILABLE")

        Returns:
            JSON string containing reserve crew details
        """
        try:
            reserve = db.get_reserve_crew(base, status)
            result = {
                "base": base,
                "status_filter": status,
                "reserve_count": len(reserve),
                "reserve_crew": reserve,
                "table": RESERVE_CREW_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_reserve_crew: {e}")
            return db.to_json({"error": str(e), "base": base})

    @tool
    def query_turnaround_requirements(flight_id: str) -> str:
        """
        Query turnaround requirements for a flight (V2-only).

        Returns detailed turn requirements including minimum turn time,
        compression options, GPU requirements, and critical path items.

        Args:
            flight_id: Flight ID

        Returns:
            JSON string containing turnaround requirements
        """
        try:
            requirements = db.get_turnaround_requirements(flight_id)
            result = {
                "flight_id": flight_id,
                "requirement_count": len(requirements),
                "turnaround_requirements": requirements,
                "table": TURNAROUND_REQUIREMENTS_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_turnaround_requirements: {e}")
            return db.to_json({"error": str(e), "flight_id": flight_id})

    @tool
    def query_minimum_connection_times(airport_code: str, connection_type: str = None) -> str:
        """
        Query minimum connection times at airport (V2-only).

        Returns MCT requirements by connection type (domestic, international,
        premium, wheelchair) for passenger rebooking validation.

        Args:
            airport_code: IATA airport code
            connection_type: Optional connection type filter (e.g., "INT-INT")

        Returns:
            JSON string containing MCT details
        """
        try:
            mcts = db.get_minimum_connection_times(airport_code, connection_type)
            result = {
                "airport_code": airport_code,
                "connection_type_filter": connection_type,
                "mct_count": len(mcts),
                "minimum_connection_times": mcts,
                "table": MINIMUM_CONNECTION_TIMES_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_minimum_connection_times: {e}")
            return db.to_json({"error": str(e), "airport_code": airport_code})

    @tool
    def query_interline_agreements(partner_airline_code: str = None) -> str:
        """
        Query interline agreements with partner airlines (V2-only).

        Returns rebooking permissions, cost multipliers, baggage handling,
        and settlement terms for OAL rebooking.

        Args:
            partner_airline_code: Optional partner airline code filter (e.g., "QR")

        Returns:
            JSON string containing interline agreement details
        """
        try:
            agreements = db.get_interline_agreements(partner_airline_code)
            result = {
                "partner_airline_filter": partner_airline_code,
                "agreement_count": len(agreements),
                "interline_agreements": agreements,
                "table": INTERLINE_AGREEMENTS_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_interline_agreements: {e}")
            return db.to_json({"error": str(e), "partner_airline_code": partner_airline_code})

    @tool
    def query_maintenance_constraints(aircraft_registration: str) -> str:
        """
        Query maintenance constraints for aircraft (V2-only).

        Returns MEL items, dispatch restrictions, operational impact,
        and ground equipment requirements for aircraft.

        Args:
            aircraft_registration: Aircraft registration (e.g., "A6-BNC")

        Returns:
            JSON string containing maintenance constraint details
        """
        try:
            constraints = db.get_maintenance_constraints(aircraft_registration)
            result = {
                "aircraft_registration": aircraft_registration,
                "constraint_count": len(constraints),
                "maintenance_constraints": constraints,
                "table": MAINTENANCE_CONSTRAINTS_V2_TABLE,
            }
            return db.to_json(result)
        except Exception as e:
            logger.error(f"Error in query_maintenance_constraints: {e}")
            return db.to_json({"error": str(e), "aircraft_registration": aircraft_registration})

    return [
        query_aircraft_rotations,
        query_airport_curfews,
        query_airport_slots,
        query_oal_rebooking_options,
        query_cold_chain_facilities,
        query_compensation_rules,
        query_ground_equipment,
        query_reserve_crew,
        query_turnaround_requirements,
        query_minimum_connection_times,
        query_interline_agreements,
        query_maintenance_constraints,
    ]


def get_table_version_info() -> dict:
    """
    Get information about the current table version configuration.

    Returns:
        Dictionary with version info
    """
    return {
        "current_version": TABLE_VERSION.value,
        "is_v2_enabled": is_v2_enabled(),
        "v2_tables_available": 23 if is_v2_enabled() else 0,
    }
