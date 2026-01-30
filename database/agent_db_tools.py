"""
SkyMarshal Agent Database Tools
Provides database access for agents that need operational data
"""

import asyncpg
import boto3
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

AWS_REGION = "us-east-1"
SECRET_NAME_PREFIX = "skymarshal/rds/password"

class AgentDatabaseTools:
    """Database access tools for SkyMarshal agents"""

    def __init__(self):
        self.pool = None
        self.db_config = None

    async def initialize(self):
        """Initialize database connection pool"""
        if self.pool:
            return  # Already initialized

        # Get credentials from Secrets Manager
        secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)

        # Find the latest secret
        response = secrets_client.list_secrets(
            Filters=[{'Key': 'name', 'Values': [SECRET_NAME_PREFIX]}]
        )

        if not response['SecretList']:
            raise ValueError(f"No secrets found with prefix: {SECRET_NAME_PREFIX}")

        secret = sorted(response['SecretList'],
                      key=lambda x: x['CreatedDate'],
                      reverse=True)[0]

        # Get secret value
        response = secrets_client.get_secret_value(SecretId=secret['ARN'])
        self.db_config = json.loads(response['SecretString'])

        # Create connection pool
        self.pool = await asyncpg.create_pool(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['dbname'],
            user=self.db_config['username'],
            password=self.db_config['password'],
            min_size=2,
            max_size=10,
            timeout=30
        )

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

    # ================================================================
    # CREW COMPLIANCE AGENT TOOLS
    # ================================================================

    async def get_crew_duty_hours(self, crew_id: int, date: str) -> Dict:
        """
        Get crew duty hours for FTL compliance checking.
        Used by: Crew Compliance Agent
        """
        async with self.pool.acquire() as conn:
            # Today's duty hours
            today = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(EXTRACT(EPOCH FROM (duty_end - duty_start))/3600), 0) as total_hours,
                    COUNT(*) as flights_today
                FROM crew_roster
                WHERE crew_id = $1
                  AND DATE(duty_start) = $2::date
                  AND roster_status IN ('Assigned', 'Confirmed')
            """, crew_id, date)

            # 7-day rolling duty hours
            week = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(EXTRACT(EPOCH FROM (duty_end - duty_start))/3600), 0) as total_hours_7day
                FROM crew_roster
                WHERE crew_id = $1
                  AND duty_start >= $2::date - INTERVAL '7 days'
                  AND roster_status IN ('Assigned', 'Confirmed', 'Completed')
            """, crew_id, date)

            # 28-day rolling duty hours
            month = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(EXTRACT(EPOCH FROM (duty_end - duty_start))/3600), 0) as total_hours_28day
                FROM crew_roster
                WHERE crew_id = $1
                  AND duty_start >= $2::date - INTERVAL '28 days'
                  AND roster_status IN ('Assigned', 'Confirmed', 'Completed')
            """, crew_id, date)

            return {
                "today_hours": float(today['total_hours']),
                "today_flights": int(today['flights_today']),
                "seven_day_hours": float(week['total_hours_7day']),
                "twenty_eight_day_hours": float(month['total_hours_28day'])
            }

    async def get_flight_crew_roster(self, flight_id: int) -> List[Dict]:
        """
        Get crew roster for a specific flight.
        Used by: Crew Compliance Agent
        """
        async with self.pool.acquire() as conn:
            crew = await conn.fetch("""
                SELECT
                    cm.crew_id, cm.employee_id, cm.first_name, cm.last_name,
                    cp.position_code, cp.position_name,
                    cr.duty_start, cr.duty_end, cr.roster_status
                FROM crew_roster cr
                JOIN crew_members cm ON cr.crew_id = cm.crew_id
                JOIN crew_positions cp ON cr.position_id = cp.position_id
                WHERE cr.flight_id = $1
                ORDER BY cp.position_code
            """, flight_id)

            return [dict(c) for c in crew]

    # ================================================================
    # MAINTENANCE AGENT TOOLS
    # ================================================================

    async def get_aircraft_maintenance_status(self, aircraft_type_code: str) -> Dict:
        """
        Get maintenance status for aircraft type.
        Used by: Maintenance Agent

        Note: This is a simplified query. In production, you'd have
        aircraft registration numbers and actual maintenance logs.
        """
        async with self.pool.acquire() as conn:
            aircraft = await conn.fetchrow("""
                SELECT
                    aircraft_type_id, aircraft_code, category,
                    passenger_capacity, cargo_capacity_kg
                FROM aircraft_types
                WHERE aircraft_code = $1
            """, aircraft_type_code)

            return dict(aircraft) if aircraft else {}

    # ================================================================
    # REGULATORY AGENT TOOLS
    # ================================================================

    async def get_airport_info(self, iata_code: str) -> Dict:
        """
        Get airport information for regulatory checks.
        Used by: Regulatory Agent
        """
        async with self.pool.acquire() as conn:
            airport = await conn.fetchrow("""
                SELECT
                    airport_id, iata_code, icao_code, airport_name,
                    city, country, timezone, is_hub
                FROM airports
                WHERE iata_code = $1
            """, iata_code.upper())

            return dict(airport) if airport else {}

    async def get_flight_route_info(self, flight_id: int) -> Dict:
        """
        Get flight route information for regulatory compliance.
        Used by: Regulatory Agent
        """
        async with self.pool.acquire() as conn:
            flight = await conn.fetchrow("""
                SELECT
                    f.flight_id, f.flight_number,
                    f.scheduled_departure, f.scheduled_arrival,
                    o.iata_code as origin_iata, o.airport_name as origin_name,
                    o.timezone as origin_timezone,
                    d.iata_code as dest_iata, d.airport_name as dest_name,
                    d.timezone as dest_timezone
                FROM flights f
                JOIN airports o ON f.origin_airport_id = o.airport_id
                JOIN airports d ON f.destination_airport_id = d.airport_id
                WHERE f.flight_id = $1
            """, flight_id)

            return dict(flight) if flight else {}

    # ================================================================
    # NETWORK AGENT TOOLS
    # ================================================================

    async def get_downstream_connections(self, flight_id: int) -> List[Dict]:
        """
        Get passengers with connections at risk.
        Used by: Network Agent
        """
        async with self.pool.acquire() as conn:
            connections = await conn.fetch("""
                SELECT
                    b.booking_id, b.pnr, b.seat_number,
                    b.is_connection, b.connection_at_risk,
                    p.first_name, p.last_name, p.frequent_flyer_number,
                    p.frequent_flyer_tier_id, p.is_vip,
                    cf.flight_number as connecting_flight
                FROM bookings b
                JOIN passengers p ON b.passenger_id = p.passenger_id
                LEFT JOIN flights cf ON b.connecting_flight_id = cf.flight_id
                WHERE b.flight_id = $1
                  AND b.is_connection = TRUE
                  AND b.booking_status = 'Confirmed'
                ORDER BY b.connection_at_risk DESC, p.frequent_flyer_tier_id ASC
            """, flight_id)

            return [dict(c) for c in connections]

    async def find_alternative_flights(
        self,
        origin_id: int,
        dest_id: int,
        after_time: str,
        hours_window: int = 24
    ) -> List[Dict]:
        """
        Find alternative flights for rebooking.
        Used by: Network Agent
        """
        async with self.pool.acquire() as conn:
            flights = await conn.fetch("""
                SELECT
                    f.flight_id, f.flight_number,
                    f.scheduled_departure, f.scheduled_arrival,
                    at.aircraft_code, at.passenger_capacity,
                    COUNT(b.booking_id) as booked_seats,
                    (at.passenger_capacity - COUNT(b.booking_id)) as available_seats
                FROM flights f
                JOIN aircraft_types at ON f.aircraft_type_id = at.aircraft_type_id
                LEFT JOIN bookings b ON f.flight_id = b.flight_id
                    AND b.booking_status IN ('Confirmed', 'CheckedIn')
                WHERE f.origin_airport_id = $1
                  AND f.destination_airport_id = $2
                  AND f.scheduled_departure > $3::timestamp
                  AND f.scheduled_departure < ($3::timestamp + ($4 || ' hours')::interval)
                  AND f.flight_status NOT IN ('Cancelled')
                GROUP BY f.flight_id, at.aircraft_type_id
                HAVING (at.passenger_capacity - COUNT(b.booking_id)) > 0
                ORDER BY f.scheduled_departure
            """, origin_id, dest_id, after_time, hours_window)

            return [dict(f) for f in flights]

    # ================================================================
    # GUEST EXPERIENCE AGENT TOOLS
    # ================================================================

    async def get_passenger_details(self, flight_id: int) -> Dict:
        """
        Get passenger statistics and high-value passenger details.
        Used by: Guest Experience Agent
        """
        async with self.pool.acquire() as conn:
            # Overall statistics
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_passengers,
                    SUM(CASE WHEN p.is_vip THEN 1 ELSE 0 END) as vip_count,
                    SUM(CASE WHEN p.frequent_flyer_tier_id = 1 THEN 1 ELSE 0 END) as platinum,
                    SUM(CASE WHEN p.frequent_flyer_tier_id = 2 THEN 1 ELSE 0 END) as gold,
                    SUM(CASE WHEN p.frequent_flyer_tier_id = 3 THEN 1 ELSE 0 END) as silver,
                    SUM(CASE WHEN p.has_medical_condition THEN 1 ELSE 0 END) as medical_assistance,
                    SUM(CASE WHEN b.booking_class = 'First' THEN 1 ELSE 0 END) as first_class,
                    SUM(CASE WHEN b.booking_class = 'Business' THEN 1 ELSE 0 END) as business_class,
                    SUM(CASE WHEN b.booking_class = 'Economy' THEN 1 ELSE 0 END) as economy_class
                FROM bookings b
                JOIN passengers p ON b.passenger_id = p.passenger_id
                WHERE b.flight_id = $1
                  AND b.booking_status IN ('Confirmed', 'CheckedIn', 'Boarded')
            """, flight_id)

            # High-value passengers
            vip_passengers = await conn.fetch("""
                SELECT
                    p.first_name, p.last_name, p.frequent_flyer_number,
                    fft.tier_name, b.booking_class, b.seat_number,
                    p.is_vip, p.has_medical_condition
                FROM bookings b
                JOIN passengers p ON b.passenger_id = p.passenger_id
                LEFT JOIN frequent_flyer_tiers fft ON p.frequent_flyer_tier_id = fft.tier_id
                WHERE b.flight_id = $1
                  AND (p.is_vip = TRUE OR p.frequent_flyer_tier_id IN (1, 2))
                  AND b.booking_status IN ('Confirmed', 'CheckedIn', 'Boarded')
                ORDER BY p.is_vip DESC, p.frequent_flyer_tier_id ASC
                LIMIT 20
            """, flight_id)

            return {
                "statistics": dict(stats) if stats else {},
                "high_value_passengers": [dict(vip) for vip in vip_passengers]
            }

    async def get_passenger_baggage(self, flight_id: int) -> Dict:
        """
        Get baggage statistics for the flight.
        Used by: Guest Experience Agent
        """
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_bags,
                    SUM(CASE WHEN baggage_type = 'CheckedIn' THEN 1 ELSE 0 END) as checked,
                    SUM(CASE WHEN is_priority THEN 1 ELSE 0 END) as priority,
                    ROUND(SUM(weight_kg)::numeric, 2) as total_weight
                FROM baggage bag
                JOIN bookings b ON bag.booking_id = b.booking_id
                WHERE b.flight_id = $1
            """, flight_id)

            return dict(stats) if stats else {}

    # ================================================================
    # CARGO AGENT TOOLS
    # ================================================================

    async def get_cargo_details(self, flight_id: int) -> Dict:
        """
        Get cargo shipment details for the flight.
        Used by: Cargo Agent
        """
        async with self.pool.acquire() as conn:
            # Overall cargo statistics
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(DISTINCT cs.shipment_id) as total_shipments,
                    SUM(cfa.pieces_on_flight) as total_pieces,
                    ROUND(SUM(cfa.weight_on_flight_kg)::numeric, 2) as total_weight_kg,
                    SUM(CASE WHEN ct.temperature_controlled THEN cfa.weight_on_flight_kg ELSE 0 END) as temp_controlled_weight,
                    SUM(CASE WHEN ct.requires_special_handling THEN 1 ELSE 0 END) as special_handling_count
                FROM cargo_flight_assignments cfa
                JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
                JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
                WHERE cfa.flight_id = $1
                  AND cfa.loading_status = 'Planned'
            """, flight_id)

            # Special cargo details
            special_cargo = await conn.fetch("""
                SELECT
                    cs.awb_number, ct.commodity_name, ct.commodity_code,
                    cfa.pieces_on_flight, cfa.weight_on_flight_kg,
                    ct.temperature_controlled, ct.requires_special_handling,
                    cs.shipper_name, cs.consignee_name
                FROM cargo_flight_assignments cfa
                JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
                JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
                WHERE cfa.flight_id = $1
                  AND cfa.loading_status = 'Planned'
                  AND (ct.temperature_controlled = TRUE OR ct.requires_special_handling = TRUE)
                ORDER BY ct.temperature_controlled DESC, cfa.weight_on_flight_kg DESC
            """, flight_id)

            return {
                "statistics": dict(stats) if stats else {},
                "special_cargo": [dict(cargo) for cargo in special_cargo]
            }

    # ================================================================
    # FINANCE AGENT TOOLS
    # ================================================================

    async def get_flight_revenue_data(self, flight_id: int) -> Dict:
        """
        Get flight data for revenue/cost calculations.
        Used by: Finance Agent
        """
        async with self.pool.acquire() as conn:
            # Flight details
            flight_info = await conn.fetchrow("""
                SELECT
                    f.flight_number, f.scheduled_departure, f.scheduled_arrival,
                    at.aircraft_code, at.passenger_capacity, at.cargo_capacity_kg,
                    o.iata_code as origin, d.iata_code as destination
                FROM flights f
                JOIN aircraft_types at ON f.aircraft_type_id = at.aircraft_type_id
                JOIN airports o ON f.origin_airport_id = o.airport_id
                JOIN airports d ON f.destination_airport_id = d.airport_id
                WHERE f.flight_id = $1
            """, flight_id)

            # Passenger revenue data
            pax_data = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_passengers,
                    SUM(CASE WHEN booking_class = 'First' THEN 1 ELSE 0 END) as first_class,
                    SUM(CASE WHEN booking_class = 'Business' THEN 1 ELSE 0 END) as business_class,
                    SUM(CASE WHEN booking_class = 'Economy' THEN 1 ELSE 0 END) as economy_class
                FROM bookings
                WHERE flight_id = $1
                  AND booking_status IN ('Confirmed', 'CheckedIn', 'Boarded')
            """, flight_id)

            # Cargo data
            cargo_data = await conn.fetchrow("""
                SELECT
                    COALESCE(SUM(cfa.weight_on_flight_kg), 0) as total_cargo_weight_kg
                FROM cargo_flight_assignments cfa
                WHERE cfa.flight_id = $1
                  AND cfa.loading_status = 'Planned'
            """, flight_id)

            return {
                "flight": dict(flight_info) if flight_info else {},
                "passengers": dict(pax_data) if pax_data else {},
                "cargo": dict(cargo_data) if cargo_data else {}
            }

    # ================================================================
    # COMMON TOOLS (All agents)
    # ================================================================

    async def get_flight_basic_info(self, flight_id: int) -> Dict:
        """
        Get basic flight information.
        Used by: All agents
        """
        async with self.pool.acquire() as conn:
            flight = await conn.fetchrow("""
                SELECT
                    f.flight_id, f.flight_number,
                    f.scheduled_departure, f.scheduled_arrival,
                    f.flight_status, f.gate, f.terminal,
                    at.aircraft_code, at.passenger_capacity, at.cargo_capacity_kg,
                    o.iata_code as origin_iata, o.airport_name as origin_name,
                    d.iata_code as dest_iata, d.airport_name as dest_name
                FROM flights f
                JOIN aircraft_types at ON f.aircraft_type_id = at.aircraft_type_id
                JOIN airports o ON f.origin_airport_id = o.airport_id
                JOIN airports d ON f.destination_airport_id = d.airport_id
                WHERE f.flight_id = $1
            """, flight_id)

            return dict(flight) if flight else {}
