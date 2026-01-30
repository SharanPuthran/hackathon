"""Database manager for SkyMarshal"""

import asyncpg
from typing import Dict, List, Optional
import logging
from src.config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                min_size=5,
                max_size=20
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def get_flight_details(self, flight_id: int) -> Dict:
        """Get complete flight details including aircraft, route, crew, pax, cargo"""
        
        async with self.pool.acquire() as conn:
            # Get flight info
            flight = await conn.fetchrow("""
                SELECT f.*,
                       at.aircraft_code, at.passenger_capacity, at.cargo_capacity_kg,
                       o.iata_code as origin_iata, o.airport_name as origin_name,
                       d.iata_code as dest_iata, d.airport_name as dest_name
                FROM flights f
                JOIN aircraft_types at ON f.aircraft_type_id = at.aircraft_type_id
                JOIN airports o ON f.origin_airport_id = o.airport_id
                JOIN airports d ON f.destination_airport_id = d.airport_id
                WHERE f.flight_id = $1
            """, flight_id)
            
            if not flight:
                return None
            
            # Get passenger count and breakdown
            pax_stats = await conn.fetchrow("""
                SELECT COUNT(*) as total_pax,
                       SUM(CASE WHEN is_connection THEN 1 ELSE 0 END) as connections,
                       SUM(CASE WHEN connection_at_risk THEN 1 ELSE 0 END) as at_risk,
                       SUM(CASE WHEN p.is_vip THEN 1 ELSE 0 END) as vip_count,
                       SUM(CASE WHEN p.frequent_flyer_tier_id = 1 THEN 1 ELSE 0 END) as platinum,
                       SUM(CASE WHEN booking_class = 'First' THEN 1 ELSE 0 END) as first_class,
                       SUM(CASE WHEN booking_class = 'Business' THEN 1 ELSE 0 END) as business_class
                FROM bookings b
                JOIN passengers p ON b.passenger_id = p.passenger_id
                WHERE b.flight_id = $1 AND b.booking_status != 'Cancelled'
            """, flight_id)
            
            # Get cargo summary
            cargo_stats = await conn.fetchrow("""
                SELECT COUNT(DISTINCT cs.shipment_id) as total_shipments,
                       SUM(cfa.weight_on_flight_kg) as total_cargo_weight,
                       SUM(CASE WHEN ct.temperature_controlled THEN cfa.weight_on_flight_kg ELSE 0 END) as temp_controlled_weight,
                       SUM(CASE WHEN ct.requires_special_handling THEN 1 ELSE 0 END) as special_handling_count
                FROM cargo_flight_assignments cfa
                JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
                JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
                WHERE cfa.flight_id = $1 AND cfa.loading_status = 'Planned'
            """, flight_id)
            
            # Get crew assignments
            crew = await conn.fetch("""
                SELECT cm.crew_id, cm.first_name, cm.last_name, cp.position_code, cp.position_name,
                       cr.duty_start, cr.duty_end
                FROM crew_roster cr
                JOIN crew_members cm ON cr.crew_id = cm.crew_id
                JOIN crew_positions cp ON cr.position_id = cp.position_id
                WHERE cr.flight_id = $1 AND cr.roster_status = 'Assigned'
            """, flight_id)
            
            return {
                "flight": dict(flight),
                "passengers": dict(pax_stats) if pax_stats else {},
                "cargo": dict(cargo_stats) if cargo_stats else {},
                "crew": [dict(c) for c in crew]
            }
    
    async def get_crew_duty_hours(self, crew_id: int, date: str) -> Dict:
        """Calculate crew duty hours for FTL compliance"""
        
        async with self.pool.acquire() as conn:
            duty_summary = await conn.fetchrow("""
                SELECT
                    SUM(EXTRACT(EPOCH FROM (duty_end - duty_start))/3600) as total_hours_today,
                    COUNT(*) as flights_today
                FROM crew_roster
                WHERE crew_id = $1
                  AND DATE(duty_start) = $2
                  AND roster_status IN ('Assigned', 'Confirmed')
            """, crew_id, date)
            
            # Get last 7 days duty time
            duty_7day = await conn.fetchrow("""
                SELECT
                    SUM(EXTRACT(EPOCH FROM (duty_end - duty_start))/3600) as total_hours_7day
                FROM crew_roster
                WHERE crew_id = $1
                  AND duty_start >= $2::date - INTERVAL '7 days'
                  AND roster_status IN ('Assigned', 'Confirmed', 'Completed')
            """, crew_id, date)
            
            return {
                "today_hours": float(duty_summary['total_hours_today'] or 0),
                "today_flights": int(duty_summary['flights_today'] or 0),
                "seven_day_hours": float(duty_7day['total_hours_7day'] or 0)
            }
    
    async def find_alternative_flights(
        self,
        origin_id: int,
        dest_id: int,
        after_time: str,
        hours_window: int = 24
    ) -> List[Dict]:
        """Find alternative flights for rebooking"""
        
        async with self.pool.acquire() as conn:
            flights = await conn.fetch("""
                SELECT f.flight_id, f.flight_number,
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
                  AND f.flight_status = 'Scheduled'
                GROUP BY f.flight_id, at.aircraft_type_id
                HAVING (at.passenger_capacity - COUNT(b.booking_id)) > 0
                ORDER BY f.scheduled_departure
            """, origin_id, dest_id, after_time, hours_window)
            
            return [dict(f) for f in flights]
    
    async def get_all_flights(self) -> List[Dict]:
        """Get all flights for demo selection"""
        async with self.pool.acquire() as conn:
            flights = await conn.fetch("""
                SELECT f.flight_id, f.flight_number, f.scheduled_departure,
                       o.iata_code as origin, d.iata_code as destination,
                       at.aircraft_code
                FROM flights f
                JOIN airports o ON f.origin_airport_id = o.airport_id
                JOIN airports d ON f.destination_airport_id = d.airport_id
                JOIN aircraft_types at ON f.aircraft_type_id = at.aircraft_type_id
                ORDER BY f.scheduled_departure
                LIMIT 50
            """)
            return [dict(f) for f in flights]
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
