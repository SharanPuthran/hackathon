"""DynamoDB client singleton for SkyMarshal agents"""

import boto3
import json
from decimal import Decimal
from typing import Optional, Dict, List, Any
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

AWS_REGION = "us-east-1"


class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal types"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class DynamoDBClient:
    """Singleton DynamoDB client with connection pooling"""

    _instance: Optional["DynamoDBClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        logger.info("🔧 Initializing DynamoDB client...")
        self._initialized = True

        try:
            self.dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
            self.client = boto3.client("dynamodb", region_name=AWS_REGION)
            logger.info(f"   ✅ Connected to DynamoDB in {AWS_REGION}")
        except Exception as e:
            logger.error(f"   ❌ Failed to connect to DynamoDB: {e}")
            raise

        # Initialize all table references
        logger.debug("   Loading table references...")
        self.passengers = self.dynamodb.Table("Passengers")
        self.flights = self.dynamodb.Table("Flights")
        self.aircraft_availability = self.dynamodb.Table("AircraftAvailability")
        self.maintenance_workorders = self.dynamodb.Table("MaintenanceWorkOrders")
        self.weather = self.dynamodb.Table("Weather")
        self.disrupted_passengers = self.dynamodb.Table("DisruptedPassengers")
        self.aircraft_swap_options = self.dynamodb.Table("AircraftSwapOptions")
        self.inbound_flight_impact = self.dynamodb.Table("InboundFlightImpact")
        self.bookings = self.dynamodb.Table("Bookings")
        self.baggage = self.dynamodb.Table("Baggage")
        self.crew_members = self.dynamodb.Table("CrewMembers")
        self.crew_roster = self.dynamodb.Table("CrewRoster")
        self.cargo_shipments = self.dynamodb.Table("CargoShipments")
        self.cargo_flight_assignments = self.dynamodb.Table("CargoFlightAssignments")
        self.maintenance_staff = self.dynamodb.Table("MaintenanceStaff")
        self.maintenance_roster = self.dynamodb.Table("MaintenanceRoster")

        logger.info("   ✅ DynamoDB client initialized with 16 operational tables")

    # ============================================================
    # CREW COMPLIANCE QUERIES
    # ============================================================

    def query_crew_roster_by_flight(self, flight_id: str) -> List[Dict[str, Any]]:
        """Query crew roster for a flight using GSI"""
        try:
            response = self.crew_roster.query(
                IndexName="flight-position-index",
                KeyConditionExpression="flight_id = :fid",
                ExpressionAttributeValues={":fid": str(flight_id)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying crew roster for flight {flight_id}: {e}")
            return []

    def get_crew_member(self, crew_id: str) -> Optional[Dict[str, Any]]:
        """Get crew member details by ID"""
        try:
            response = self.crew_members.get_item(Key={"crew_id": str(crew_id)})
            return response.get("Item")
        except Exception as e:
            logger.error(f"Error getting crew member {crew_id}: {e}")
            return None

    # ============================================================
    # MAINTENANCE QUERIES
    # ============================================================

    def get_aircraft_availability(
        self, aircraft_registration: str, valid_from: str
    ) -> Optional[Dict[str, Any]]:
        """Get aircraft availability and MEL status"""
        try:
            response = self.aircraft_availability.get_item(
                Key={
                    "aircraftRegistration": str(aircraft_registration),
                    "valid_from_zulu": str(valid_from),
                }
            )
            return response.get("Item")
        except Exception as e:
            logger.error(
                f"Error getting aircraft availability for {aircraft_registration}: {e}"
            )
            return None

    def query_maintenance_workorders(
        self, aircraft_registration: str
    ) -> List[Dict[str, Any]]:
        """Query maintenance work orders for an aircraft using GSI"""
        try:
            response = self.maintenance_workorders.query(
                IndexName="aircraft-registration-index",
                KeyConditionExpression="aircraftRegistration = :reg",
                ExpressionAttributeValues={":reg": str(aircraft_registration)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(
                f"Error querying maintenance workorders for {aircraft_registration}: {e}"
            )
            return []

    def query_maintenance_roster_by_workorder(
        self, workorder_id: str
    ) -> List[Dict[str, Any]]:
        """Query maintenance staff assigned to work order using GSI"""
        try:
            response = self.maintenance_roster.query(
                IndexName="workorder-shift-index",
                KeyConditionExpression="workorder_id = :wid",
                ExpressionAttributeValues={":wid": str(workorder_id)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(
                f"Error querying maintenance roster for workorder {workorder_id}: {e}"
            )
            return []

    # ============================================================
    # REGULATORY QUERIES
    # ============================================================

    def get_weather(
        self, airport_code: str, forecast_time: str
    ) -> Optional[Dict[str, Any]]:
        """Get weather forecast for airport"""
        try:
            response = self.weather.get_item(
                Key={
                    "airport_code": str(airport_code),
                    "forecast_time_zulu": str(forecast_time),
                }
            )
            return response.get("Item")
        except Exception as e:
            logger.error(f"Error getting weather for {airport_code}: {e}")
            return None

    def get_flight(self, flight_id: str) -> Optional[Dict[str, Any]]:
        """Get flight details"""
        try:
            response = self.flights.get_item(Key={"flight_id": str(flight_id)})
            return response.get("Item")
        except Exception as e:
            logger.error(f"Error getting flight {flight_id}: {e}")
            return None

    # ============================================================
    # NETWORK QUERIES
    # ============================================================

    def get_inbound_flight_impact(self, scenario: str) -> Optional[Dict[str, Any]]:
        """Get inbound flight impact analysis"""
        try:
            response = self.inbound_flight_impact.get_item(
                Key={"scenario": str(scenario)}
            )
            return response.get("Item")
        except Exception as e:
            logger.error(
                f"Error getting inbound flight impact for scenario {scenario}: {e}"
            )
            return None

    def query_flight_by_number_and_date(
        self, flight_number: str, scheduled_departure: str
    ) -> Optional[Dict[str, Any]]:
        """
        Query flight by flight number and scheduled departure date using GSI.
        
        Args:
            flight_number: Flight number (e.g., "EY123")
            scheduled_departure: Scheduled departure date in YYYY-MM-DD format
            
        Returns:
            Flight record if found, None otherwise
        """
        try:
            response = self.flights.query(
                IndexName="flight-number-date-index",
                KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
                ExpressionAttributeValues={
                    ":fn": str(flight_number),
                    ":sd": str(scheduled_departure),
                },
            )
            items = response.get("Items", [])
            return items[0] if items else None
        except Exception as e:
            logger.error(
                f"Error querying flight {flight_number} on {scheduled_departure}: {e}"
            )
            return None

    def query_flights_by_aircraft(
        self, aircraft_registration: str
    ) -> List[Dict[str, Any]]:
        """
        Query flights by aircraft registration using GSI.
        
        Args:
            aircraft_registration: Aircraft registration (e.g., "A6-APX")
            
        Returns:
            List of flight records for the aircraft
        """
        try:
            response = self.flights.query(
                IndexName="aircraft-registration-index",
                KeyConditionExpression="aircraft_registration = :reg",
                ExpressionAttributeValues={":reg": str(aircraft_registration)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(
                f"Error querying flights for aircraft {aircraft_registration}: {e}"
            )
            return []

    def query_flights(self, **kwargs) -> List[Dict[str, Any]]:
        """
        DEPRECATED: Generic query method that uses table scan.
        Use query_flight_by_number_and_date() or query_flights_by_aircraft() instead.
        
        This method is kept for backward compatibility with test scripts only.
        """
        logger.warning(
            "query_flights() uses table scan and is deprecated. "
            "Use query_flight_by_number_and_date() or query_flights_by_aircraft() instead."
        )
        try:
            response = self.flights.scan(**kwargs)
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying flights: {e}")
            return []

    # ============================================================
    # GUEST EXPERIENCE QUERIES
    # ============================================================

    def query_bookings_by_passenger(self, passenger_id: str) -> List[Dict[str, Any]]:
        """Query bookings for a passenger using GSI"""
        try:
            response = self.bookings.query(
                IndexName="passenger-flight-index",
                KeyConditionExpression="passenger_id = :pid",
                ExpressionAttributeValues={":pid": str(passenger_id)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying bookings for passenger {passenger_id}: {e}")
            return []

    def query_bookings_by_flight(
        self, flight_id: str, booking_status: str = None
    ) -> List[Dict[str, Any]]:
        """Query bookings for a flight using GSI"""
        try:
            if booking_status:
                response = self.bookings.query(
                    IndexName="flight-status-index",
                    KeyConditionExpression="flight_id = :fid AND booking_status = :status",
                    ExpressionAttributeValues={
                        ":fid": str(flight_id),
                        ":status": str(booking_status),
                    },
                )
            else:
                response = self.bookings.query(
                    IndexName="flight-status-index",
                    KeyConditionExpression="flight_id = :fid",
                    ExpressionAttributeValues={":fid": str(flight_id)},
                )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying bookings for flight {flight_id}: {e}")
            return []

    def query_baggage_by_booking(self, booking_id: str) -> List[Dict[str, Any]]:
        """Query baggage for a booking using GSI"""
        try:
            response = self.baggage.query(
                IndexName="booking-index",
                KeyConditionExpression="booking_id = :bid",
                ExpressionAttributeValues={":bid": str(booking_id)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying baggage for booking {booking_id}: {e}")
            return []

    def get_passenger(self, passenger_id: str) -> Optional[Dict[str, Any]]:
        """Get passenger details"""
        try:
            response = self.passengers.get_item(Key={"passenger_id": str(passenger_id)})
            return response.get("Item")
        except Exception as e:
            logger.error(f"Error getting passenger {passenger_id}: {e}")
            return None

    # ============================================================
    # CARGO QUERIES
    # ============================================================

    def query_cargo_by_shipment(self, shipment_id: str) -> List[Dict[str, Any]]:
        """Track cargo shipment across flights using GSI"""
        try:
            response = self.cargo_flight_assignments.query(
                IndexName="shipment-index",
                KeyConditionExpression="shipment_id = :sid",
                ExpressionAttributeValues={":sid": str(shipment_id)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying cargo for shipment {shipment_id}: {e}")
            return []

    def query_cargo_by_flight(
        self, flight_id: str, loading_status: str = None
    ) -> List[Dict[str, Any]]:
        """Query cargo for a flight using GSI"""
        try:
            if loading_status:
                response = self.cargo_flight_assignments.query(
                    IndexName="flight-loading-index",
                    KeyConditionExpression="flight_id = :fid AND loading_status = :status",
                    ExpressionAttributeValues={
                        ":fid": str(flight_id),
                        ":status": str(loading_status),
                    },
                )
            else:
                response = self.cargo_flight_assignments.query(
                    IndexName="flight-loading-index",
                    KeyConditionExpression="flight_id = :fid",
                    ExpressionAttributeValues={":fid": str(flight_id)},
                )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying cargo for flight {flight_id}: {e}")
            return []

    def get_cargo_shipment(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """Get cargo shipment details"""
        try:
            response = self.cargo_shipments.get_item(
                Key={"shipment_id": str(shipment_id)}
            )
            return response.get("Item")
        except Exception as e:
            logger.error(f"Error getting cargo shipment {shipment_id}: {e}")
            return None

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    def to_json(self, data: Any) -> str:
        """Convert DynamoDB data to JSON string"""
        return json.dumps(data, cls=DecimalEncoder, indent=2)
