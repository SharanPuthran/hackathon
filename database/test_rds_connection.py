#!/usr/bin/env python3
"""
Test AWS RDS PostgreSQL connection for SkyMarshal
"""

import asyncio
import asyncpg
import boto3
import json
import sys
from datetime import datetime

AWS_REGION = "us-east-1"
SECRET_NAME_PREFIX = "skymarshal/rds/password"


async def test_rds_connection():
    """Test connection to RDS and run sample queries"""

    print("=" * 60)
    print("SkyMarshal RDS PostgreSQL Connection Test")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    try:
        # Step 1: Get credentials from Secrets Manager
        print("🔐 Retrieving credentials from Secrets Manager...")
        secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)

        # Find the latest secret
        response = secrets_client.list_secrets(
            Filters=[{'Key': 'name', 'Values': [SECRET_NAME_PREFIX]}]
        )

        if not response['SecretList']:
            print(f"   ❌ No secrets found with prefix: {SECRET_NAME_PREFIX}")
            sys.exit(1)

        secret = sorted(response['SecretList'],
                      key=lambda x: x['CreatedDate'],
                      reverse=True)[0]

        print(f"   Found: {secret['Name']}")

        # Get secret value
        response = secrets_client.get_secret_value(SecretId=secret['ARN'])
        creds = json.loads(response['SecretString'])
        print(f"   ✅ Retrieved credentials for: {creds['host']}\n")

        # Step 2: Connect to RDS
        print("🔌 Connecting to RDS PostgreSQL...")
        conn = await asyncpg.connect(
            host=creds['host'],
            port=creds['port'],
            database=creds['dbname'],
            user=creds['username'],
            password=creds['password'],
            timeout=30
        )
        print(f"   ✅ Connected successfully!\n")

        # Step 3: Test database version
        print("📊 Database Information:")
        version = await conn.fetchval('SELECT version()')
        print(f"   PostgreSQL Version: {version[:50]}...\n")

        # Step 4: Check table counts
        print("📋 Table Statistics:")
        print("   " + "-" * 50)
        print(f"   {'Table':<27} | {'Row Count':>10}")
        print("   " + "-" * 50)

        tables = [
            'aircraft_types', 'airports', 'frequent_flyer_tiers',
            'crew_positions', 'commodity_types', 'flights',
            'passengers', 'bookings', 'baggage', 'cargo_shipments',
            'cargo_flight_assignments', 'crew_members',
            'crew_type_ratings', 'crew_roster'
        ]

        total_rows = 0
        for table in tables:
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM {table}')
                print(f"   {table:<27} | {count:>10,}")
                total_rows += count
            except Exception as e:
                print(f"   {table:<27} | {'ERROR':>10}")

        print("   " + "-" * 50)
        print(f"   {'TOTAL':<27} | {total_rows:>10,}\n")

        # Step 5: Test sample queries
        print("🔍 Sample Queries:")
        print("   " + "-" * 50)

        # Query 1: Flight statistics
        result = await conn.fetchrow("""
            SELECT COUNT(*) as total_flights,
                   COUNT(DISTINCT origin_airport_id) as origins,
                   COUNT(DISTINCT destination_airport_id) as destinations
            FROM flights
        """)
        print(f"   Flights: {result['total_flights']}, "
              f"Origins: {result['origins']}, "
              f"Destinations: {result['destinations']}")

        # Query 2: Passenger statistics
        result = await conn.fetchrow("""
            SELECT COUNT(*) as total_passengers,
                   COUNT(CASE WHEN is_vip THEN 1 END) as vip_count,
                   COUNT(CASE WHEN frequent_flyer_tier_id = 1 THEN 1 END) as platinum
            FROM passengers
        """)
        print(f"   Passengers: {result['total_passengers']:,}, "
              f"VIP: {result['vip_count']}, "
              f"Platinum: {result['platinum']}")

        # Query 3: Cargo statistics
        result = await conn.fetchrow("""
            SELECT COUNT(*) as total_shipments,
                   ROUND(SUM(total_weight_kg)::numeric, 2) as total_weight
            FROM cargo_shipments
            WHERE shipment_status = 'Confirmed'
        """)
        print(f"   Cargo Shipments: {result['total_shipments']}, "
              f"Weight: {result['total_weight']:,} kg")

        # Query 4: Crew statistics
        result = await conn.fetchrow("""
            SELECT COUNT(DISTINCT crew_id) as total_crew,
                   COUNT(*) as total_assignments
            FROM crew_roster
            WHERE roster_status = 'Assigned'
        """)
        print(f"   Crew: {result['total_crew']}, "
              f"Assignments: {result['total_assignments']}\n")

        # Step 6: Test complex join query
        print("🔗 Complex Query Test:")
        result = await conn.fetchrow("""
            SELECT f.flight_number,
                   o.iata_code as origin,
                   d.iata_code as destination,
                   COUNT(DISTINCT b.booking_id) as passengers,
                   COUNT(DISTINCT cfa.shipment_id) as cargo_shipments
            FROM flights f
            JOIN airports o ON f.origin_airport_id = o.airport_id
            JOIN airports d ON f.destination_airport_id = d.airport_id
            LEFT JOIN bookings b ON f.flight_id = b.flight_id
                AND b.booking_status = 'Confirmed'
            LEFT JOIN cargo_flight_assignments cfa ON f.flight_id = cfa.flight_id
            WHERE f.flight_number = 'EY123'
            GROUP BY f.flight_id, f.flight_number, o.iata_code, d.iata_code
        """)

        if result:
            print(f"   Flight: {result['flight_number']} "
                  f"({result['origin']} → {result['destination']})")
            print(f"   Passengers: {result['passengers']}, "
                  f"Cargo: {result['cargo_shipments']}\n")
        else:
            print("   No data found for EY123\n")

        # Step 7: Test performance
        print("⚡ Performance Test:")
        import time
        start = time.time()
        await conn.execute("SELECT 1")
        elapsed = (time.time() - start) * 1000
        print(f"   Simple query latency: {elapsed:.2f}ms\n")

        # Close connection
        await conn.close()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print(f"\nRDS Details:")
        print(f"   Endpoint: {creds['endpoint']}")
        print(f"   Database: {creds['dbname']}")
        print(f"   Username: {creds['username']}")
        print(f"\nConnection String:")
        print(f"   postgresql://{creds['username']}:****@"
              f"{creds['host']}:{creds['port']}/{creds['dbname']}")
        print()

    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_rds_connection())
