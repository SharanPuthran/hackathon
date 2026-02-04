"""DynamoDB client singleton for SkyMarshal agents

This module provides a version-aware DynamoDB client that supports both
V1 (original) and V2 (new) table schemas. Use get_table() for version-aware access.

Usage:
    from database.dynamodb import DynamoDBClient
    from database.table_config import TableVersion

    client = DynamoDBClient()

    # Get table based on current version setting
    flights = client.get_table("flights")

    # Explicitly get V2 table
    flights_v2 = client.get_table("flights", TableVersion.V2)
"""

import boto3
import json
import time
from decimal import Decimal
from typing import Optional, Dict, List, Any
import logging
import sys

# Import table versioning configuration
try:
    from database.table_config import (
        get_table_name,
        TABLE_VERSION,
        TableVersion,
        is_v2_enabled,
        V2_TABLES,
    )
except ImportError:
    # Fallback for direct execution or import issues
    from table_config import (
        get_table_name,
        TABLE_VERSION,
        TableVersion,
        is_v2_enabled,
        V2_TABLES,
    )

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

        # Cache for dynamically loaded V2 tables
        self._table_cache: Dict[str, Any] = {}

        # Log current table version
        logger.info(f"   📊 Table version: {TABLE_VERSION.value} ({'V2 enabled' if is_v2_enabled() else 'V1 active'})")

    # ============================================================
    # VERSION-AWARE TABLE ACCESS
    # ============================================================

    def get_table(self, logical_name: str, version: Optional[TableVersion] = None):
        """
        Get DynamoDB table by logical name with version awareness.

        This method returns the appropriate table (V1 or V2) based on
        the current TABLE_VERSION setting or an explicit version override.

        Args:
            logical_name: Logical table name (e.g., "flights", "passengers")
            version: Override version (defaults to TABLE_VERSION from config)

        Returns:
            boto3 DynamoDB Table resource

        Example:
            # Get table based on current version setting
            flights = client.get_table("flights")

            # Explicitly get V2 table
            flights_v2 = client.get_table("flights", TableVersion.V2)
        """
        try:
            actual_table_name = get_table_name(logical_name, version)
        except KeyError as e:
            logger.error(f"Table not found: {e}")
            raise

        # Check cache first
        if actual_table_name in self._table_cache:
            return self._table_cache[actual_table_name]

        # Load table and cache it
        table = self.dynamodb.Table(actual_table_name)
        self._table_cache[actual_table_name] = table
        logger.debug(f"Loaded table: {actual_table_name} (logical: {logical_name})")

        return table

    def get_v2_table(self, logical_name: str):
        """
        Explicitly get a V2 table.

        Convenience method for accessing V2-only tables or explicitly
        requesting V2 version of enhanced tables.

        Args:
            logical_name: Logical table name

        Returns:
            boto3 DynamoDB Table resource for V2 table
        """
        return self.get_table(logical_name, TableVersion.V2)

    def get_current_table_version(self) -> str:
        """Get the current table version as a string."""
        return TABLE_VERSION.value

    def is_using_v2(self) -> bool:
        """Check if V2 tables are currently enabled."""
        return is_v2_enabled()

    # ============================================================
    # V2-ONLY TABLE ACCESS METHODS
    # ============================================================

    def get_aircraft_rotations(self, aircraft_registration: str) -> List[Dict[str, Any]]:
        """Query aircraft rotations (V2-only table)."""
        try:
            table = self.get_v2_table("aircraft_rotations")
            response = table.query(
                IndexName="aircraft-sequence-index",
                KeyConditionExpression="aircraft_registration = :reg",
                ExpressionAttributeValues={":reg": str(aircraft_registration)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying aircraft rotations for {aircraft_registration}: {e}")
            return []

    def get_airport_curfews(self, airport_code: str) -> List[Dict[str, Any]]:
        """Query airport curfews (V2-only table)."""
        try:
            table = self.get_v2_table("airport_curfews")
            response = table.query(
                IndexName="airport-index",
                KeyConditionExpression="airport_code = :code",
                ExpressionAttributeValues={":code": str(airport_code)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying airport curfews for {airport_code}: {e}")
            return []

    def get_airport_slots(self, flight_id: str) -> List[Dict[str, Any]]:
        """Query airport slots for a flight (V2-only table)."""
        try:
            table = self.get_v2_table("airport_slots")
            response = table.query(
                IndexName="flight-index",
                KeyConditionExpression="flight_id = :fid",
                ExpressionAttributeValues={":fid": str(flight_id)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying airport slots for flight {flight_id}: {e}")
            return []

    def get_oal_flights(self, origin: str, destination: str) -> List[Dict[str, Any]]:
        """Query Other Airline (OAL) rebooking options (V2-only table)."""
        try:
            table = self.get_v2_table("oal_flights")
            response = table.query(
                IndexName="route-index",
                KeyConditionExpression="origin = :orig AND destination = :dest",
                ExpressionAttributeValues={
                    ":orig": str(origin),
                    ":dest": str(destination),
                },
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying OAL flights for {origin}-{destination}: {e}")
            return []

    def get_cold_chain_facilities(self, airport_code: str) -> List[Dict[str, Any]]:
        """Query cold chain facilities at airport (V2-only table)."""
        try:
            table = self.get_v2_table("cold_chain_facilities")
            response = table.query(
                IndexName="airport-index",
                KeyConditionExpression="airport_code = :code",
                ExpressionAttributeValues={":code": str(airport_code)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying cold chain facilities for {airport_code}: {e}")
            return []

    def get_compensation_rules(self, regulation: str) -> List[Dict[str, Any]]:
        """Query compensation rules by regulation (V2-only table)."""
        try:
            table = self.get_v2_table("compensation_rules")
            response = table.query(
                IndexName="regulation-index",
                KeyConditionExpression="regulation = :reg",
                ExpressionAttributeValues={":reg": str(regulation)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying compensation rules for {regulation}: {e}")
            return []

    def get_ground_equipment(self, airport_code: str, equipment_type: str = None) -> List[Dict[str, Any]]:
        """Query ground equipment at airport (V2-only table)."""
        try:
            table = self.get_v2_table("ground_equipment")
            if equipment_type:
                response = table.query(
                    IndexName="airport-type-index",
                    KeyConditionExpression="airport_code = :code AND equipment_type = :type",
                    ExpressionAttributeValues={
                        ":code": str(airport_code),
                        ":type": str(equipment_type),
                    },
                )
            else:
                response = table.query(
                    IndexName="airport-type-index",
                    KeyConditionExpression="airport_code = :code",
                    ExpressionAttributeValues={":code": str(airport_code)},
                )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying ground equipment for {airport_code}: {e}")
            return []

    def get_reserve_crew(self, base: str, status: str = None) -> List[Dict[str, Any]]:
        """Query reserve crew at base (V2-only table)."""
        try:
            table = self.get_v2_table("reserve_crew")
            if status:
                response = table.query(
                    IndexName="base-status-index",
                    KeyConditionExpression="base = :base AND #status = :status",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":base": str(base),
                        ":status": str(status),
                    },
                )
            else:
                response = table.query(
                    IndexName="base-status-index",
                    KeyConditionExpression="base = :base",
                    ExpressionAttributeValues={":base": str(base)},
                )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying reserve crew for base {base}: {e}")
            return []

    def get_turnaround_requirements(self, flight_id: str) -> List[Dict[str, Any]]:
        """Query turnaround requirements for a flight (V2-only table)."""
        try:
            table = self.get_v2_table("turnaround_requirements")
            response = table.query(
                IndexName="flight-index",
                KeyConditionExpression="flight_id = :fid",
                ExpressionAttributeValues={":fid": str(flight_id)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying turnaround requirements for flight {flight_id}: {e}")
            return []

    def get_minimum_connection_times(self, airport_code: str, connection_type: str = None) -> List[Dict[str, Any]]:
        """Query minimum connection times at airport (V2-only table)."""
        try:
            table = self.get_v2_table("minimum_connection_times")
            if connection_type:
                response = table.query(
                    IndexName="airport-connection-index",
                    KeyConditionExpression="airport_code = :code AND connection_type = :type",
                    ExpressionAttributeValues={
                        ":code": str(airport_code),
                        ":type": str(connection_type),
                    },
                )
            else:
                response = table.query(
                    IndexName="airport-connection-index",
                    KeyConditionExpression="airport_code = :code",
                    ExpressionAttributeValues={":code": str(airport_code)},
                )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying MCT for {airport_code}: {e}")
            return []

    def get_interline_agreements(self, partner_airline_code: str = None) -> List[Dict[str, Any]]:
        """Query interline agreements (V2-only table)."""
        try:
            table = self.get_v2_table("interline_agreements")
            if partner_airline_code:
                response = table.query(
                    IndexName="partner-airline-index",
                    KeyConditionExpression="partner_airline_code = :code",
                    ExpressionAttributeValues={":code": str(partner_airline_code)},
                )
            else:
                response = table.scan()
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying interline agreements: {e}")
            return []

    def get_maintenance_constraints(self, aircraft_registration: str) -> List[Dict[str, Any]]:
        """Query maintenance constraints for aircraft (V2-only table)."""
        try:
            table = self.get_v2_table("maintenance_constraints")
            response = table.query(
                IndexName="aircraft-index",
                KeyConditionExpression="aircraft_registration = :reg",
                ExpressionAttributeValues={":reg": str(aircraft_registration)},
            )
            return response.get("Items", [])
        except Exception as e:
            logger.error(f"Error querying maintenance constraints for {aircraft_registration}: {e}")
            return []

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
                KeyConditionExpression="flight_number = :fn AND scheduled_departure_utc = :sd",
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
    # BATCH QUERY METHODS
    # ============================================================

    def batch_get_items(
        self,
        table_name: str,
        keys: List[Dict[str, Any]],
        max_batch_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Batch get items from DynamoDB table.

        Automatically splits requests into batches of max_batch_size.
        Handles unprocessed keys with exponential backoff retry.

        Args:
            table_name: DynamoDB table name
            keys: List of primary key dicts (e.g., [{"crew_id": "C001"}, {"crew_id": "C002"}])
            max_batch_size: Max items per batch (default 100, AWS limit)

        Returns:
            List of items retrieved

        Example:
            keys = [{"crew_id": "C001"}, {"crew_id": "C002"}]
            items = client.batch_get_items("CrewMembers", keys)
        """
        if not keys:
            return []

        # Split into batches of max_batch_size
        batches = [keys[i:i + max_batch_size] for i in range(0, len(keys), max_batch_size)]
        logger.debug(f"Batch get: {len(keys)} items split into {len(batches)} batches")

        all_items = []
        for batch_idx, batch in enumerate(batches):
            unprocessed = batch
            attempt_count = 0
            max_attempts = 4  # Initial attempt + 3 retries
            batch_items_collected = []

            while unprocessed and attempt_count < max_attempts:
                try:
                    response = self.client.batch_get_item(
                        RequestItems={
                            table_name: {'Keys': unprocessed}
                        }
                    )

                    # Collect successful items from this attempt
                    batch_items = response.get('Responses', {}).get(table_name, [])
                    batch_items_collected.extend(batch_items)
                    logger.debug(f"Batch {batch_idx + 1}/{len(batches)}: Retrieved {len(batch_items)} items")

                    # Handle unprocessed keys
                    unprocessed_response = response.get('UnprocessedKeys', {})
                    if table_name in unprocessed_response:
                        unprocessed = unprocessed_response[table_name].get('Keys', [])
                    else:
                        unprocessed = []

                    if unprocessed:
                        attempt_count += 1
                        if attempt_count < max_attempts:
                            # Exponential backoff
                            wait_time = (2 ** (attempt_count - 1)) * 0.1
                            logger.warning(
                                f"Batch {batch_idx + 1}/{len(batches)}: {len(unprocessed)} unprocessed keys, "
                                f"retrying after {wait_time}s (retry {attempt_count}/{max_attempts - 1})"
                            )
                            time.sleep(wait_time)
                    else:
                        # All items processed successfully
                        break

                except Exception as e:
                    logger.error(f"Error in batch get (batch {batch_idx + 1}/{len(batches)}): {e}")
                    attempt_count += 1
                    if attempt_count < max_attempts:
                        # Exponential backoff on error
                        wait_time = (2 ** (attempt_count - 1)) * 0.1
                        time.sleep(wait_time)

            # Add all items collected for this batch
            all_items.extend(batch_items_collected)

            if unprocessed:
                logger.warning(
                    f"Batch {batch_idx + 1}/{len(batches)}: Failed to process {len(unprocessed)} keys "
                    f"after {max_attempts} attempts"
                )

        logger.info(f"Batch get complete: Retrieved {len(all_items)}/{len(keys)} items")
        return all_items

    def batch_get_crew_members(
        self,
        crew_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Batch get crew member details.

        Optimized for crew compliance agent to retrieve multiple crew members
        in a single batch operation instead of N individual queries.

        Args:
            crew_ids: List of crew member IDs

        Returns:
            List of crew member records

        Example:
            crew_ids = ["C001", "C002", "C003"]
            members = client.batch_get_crew_members(crew_ids)
        """
        if not crew_ids:
            return []

        keys = [{"crew_id": str(crew_id)} for crew_id in crew_ids]
        return self.batch_get_items("CrewMembers", keys)

    def batch_get_flights(
        self,
        flight_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Batch get flight details.

        Optimized for network agent to retrieve multiple flights
        (e.g., connecting flights, affected flights) in a single batch operation.

        Args:
            flight_ids: List of flight IDs

        Returns:
            List of flight records

        Example:
            flight_ids = ["FL001", "FL002", "FL003"]
            flights = client.batch_get_flights(flight_ids)
        """
        if not flight_ids:
            return []

        keys = [{"flight_id": str(flight_id)} for flight_id in flight_ids]
        return self.batch_get_items("Flights", keys)

    def batch_get_passengers(
        self,
        passenger_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Batch get passenger details.

        Optimized for guest experience agent to retrieve multiple passengers
        affected by a disruption in a single batch operation.

        Args:
            passenger_ids: List of passenger IDs

        Returns:
            List of passenger records

        Example:
            passenger_ids = ["P001", "P002", "P003"]
            passengers = client.batch_get_passengers(passenger_ids)
        """
        if not passenger_ids:
            return []

        keys = [{"passenger_id": str(passenger_id)} for passenger_id in passenger_ids]
        return self.batch_get_items("Passengers", keys)

    def batch_get_cargo_shipments(
        self,
        shipment_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Batch get cargo shipment details.

        Optimized for cargo agent to retrieve multiple shipments
        affected by a disruption in a single batch operation.

        Args:
            shipment_ids: List of shipment IDs

        Returns:
            List of cargo shipment records

        Example:
            shipment_ids = ["SH001", "SH002", "SH003"]
            shipments = client.batch_get_cargo_shipments(shipment_ids)
        """
        if not shipment_ids:
            return []

        keys = [{"shipment_id": str(shipment_id)} for shipment_id in shipment_ids]
        return self.batch_get_items("CargoShipments", keys)

    # ============================================================
    # UTILITY METHODS
    # ============================================================

    def to_json(self, data: Any) -> str:
        """Convert DynamoDB data to JSON string"""
        return json.dumps(data, cls=DecimalEncoder, indent=2)
