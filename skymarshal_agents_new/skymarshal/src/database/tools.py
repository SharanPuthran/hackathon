"""Database tool factories for SkyMarshal agents"""

from langchain.tools import tool
from database.dynamodb import DynamoDBClient
from database.constants import (
    # Table names
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

    return [query_flight_crew_roster, query_crew_member_details]


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

    return [query_inbound_flight_impact, query_flight_network]


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

    return [
        query_passenger_bookings,
        query_flight_bookings,
        query_passenger_baggage,
        get_passenger_details,
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

    return [track_cargo_shipment, query_flight_cargo_manifest]


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
