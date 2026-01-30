#!/usr/bin/env python3
"""
SkyMarshal Database Migration to AWS RDS PostgreSQL
Loads schema and all CSV data into RDS instance
"""

import asyncpg
import boto3
import json
import csv
import sys
from pathlib import Path
from typing import Dict, List
import asyncio
from datetime import datetime

# Configuration
AWS_REGION = "us-east-1"
SECRET_NAME_PREFIX = "skymarshal/rds/password"

# Table load order (respecting foreign keys)
TABLE_LOAD_ORDER = [
    # Reference tables first
    ("aircraft_types", "aircraft_types.csv", None),
    ("airports", "airports.csv", None),
    ("frequent_flyer_tiers", "frequent_flyer_tiers.csv", None),
    ("crew_positions", "crew_positions.csv", None),
    ("commodity_types", "commodity_types.csv", None),

    # Core tables
    ("flights", "flights.csv", "output/flights.csv"),
    ("passengers", "passengers.csv", "output/passengers.csv"),
    ("crew_members", "crew_members.csv", "output/crew_members.csv"),
    ("cargo_shipments", "cargo_shipments.csv", "output/cargo_shipments.csv"),

    # Dependent tables
    ("bookings", "bookings.csv", "output/bookings.csv"),
    ("baggage", "baggage.csv", "output/baggage.csv"),
    ("crew_type_ratings", "crew_type_ratings.csv", None),
    ("crew_roster", "crew_roster.csv", "output/crew_roster.csv"),
    ("cargo_flight_assignments", "cargo_flight_assignments.csv", "output/cargo_flight_assignments.csv"),
]


class RDSMigration:
    """Handles migration to AWS RDS PostgreSQL"""

    def __init__(self, db_secret_arn: str = None):
        self.db_secret_arn = db_secret_arn
        self.secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)
        self.pool = None
        self.db_config = None

    async def get_db_credentials(self) -> Dict:
        """Retrieve database credentials from AWS Secrets Manager"""
        print("🔐 Retrieving RDS credentials from Secrets Manager...")

        try:
            # If no ARN provided, find the latest skymarshal secret
            if not self.db_secret_arn:
                print("   Finding latest SkyMarshal RDS secret...")
                response = self.secrets_client.list_secrets(
                    Filters=[
                        {'Key': 'name', 'Values': [SECRET_NAME_PREFIX]}
                    ]
                )

                if not response['SecretList']:
                    raise ValueError(f"No secrets found with prefix: {SECRET_NAME_PREFIX}")

                # Get the most recent secret
                secret = sorted(response['SecretList'],
                              key=lambda x: x['CreatedDate'],
                              reverse=True)[0]
                self.db_secret_arn = secret['ARN']
                print(f"   Found secret: {secret['Name']}")

            # Retrieve secret value
            response = self.secrets_client.get_secret_value(SecretId=self.db_secret_arn)
            secret_data = json.loads(response['SecretString'])

            print(f"   ✅ Retrieved credentials for: {secret_data['host']}")
            return secret_data

        except Exception as e:
            print(f"   ❌ Error retrieving credentials: {str(e)}")
            raise

    async def initialize_connection(self):
        """Initialize database connection pool"""
        print("\n🔌 Connecting to RDS PostgreSQL...")

        self.db_config = await self.get_db_credentials()

        try:
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
            print(f"   ✅ Connected to: {self.db_config['endpoint']}")

        except Exception as e:
            print(f"   ❌ Connection failed: {str(e)}")
            raise

    async def load_schema(self, schema_file: Path):
        """Load database schema from SQL file"""
        print(f"\n📄 Loading database schema...")
        print(f"   Schema file: {schema_file}")

        try:
            # Read schema file
            with open(schema_file, 'r') as f:
                schema_sql = f.read()

            # Execute schema
            async with self.pool.acquire() as conn:
                await conn.execute(schema_sql)

            print("   ✅ Schema loaded successfully")

        except Exception as e:
            print(f"   ❌ Schema load failed: {str(e)}")
            raise

    async def load_csv_data(self, table_name: str, csv_path: Path):
        """Load CSV data into a table"""

        if not csv_path.exists():
            print(f"   ⏭️  Skipping {table_name} - CSV not found: {csv_path}")
            return

        print(f"\n📊 Loading data into: {table_name}")
        print(f"   CSV file: {csv_path}")

        try:
            # Read CSV file
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                print(f"   ⚠️  No data in CSV file")
                return

            print(f"   Found {len(rows)} rows")

            # Get column names from CSV header
            columns = list(rows[0].keys())

            # Build INSERT query
            placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
            query = f"""
                INSERT INTO {table_name} ({', '.join(columns)})
                VALUES ({placeholders})
            """

            # Insert data in batches
            batch_size = 100
            total_inserted = 0

            async with self.pool.acquire() as conn:
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]

                    # Convert each row to a tuple of values
                    for row in batch:
                        values = [
                            None if v == '' or v == 'NULL' else v
                            for v in row.values()
                        ]
                        await conn.execute(query, *values)
                        total_inserted += 1

                    if (i + batch_size) % 500 == 0:
                        print(f"   Progress: {total_inserted}/{len(rows)} rows inserted...")

            print(f"   ✅ Inserted {total_inserted} rows into {table_name}")

        except Exception as e:
            print(f"   ❌ Data load failed for {table_name}: {str(e)}")
            raise

    async def verify_data(self):
        """Verify data was loaded correctly"""
        print("\n✅ Verifying data load...")

        try:
            async with self.pool.acquire() as conn:
                # Check each table
                tables = [
                    "aircraft_types", "airports", "flights", "passengers",
                    "bookings", "baggage", "cargo_shipments", "cargo_flight_assignments",
                    "crew_members", "crew_roster", "crew_positions", "commodity_types",
                    "frequent_flyer_tiers", "crew_type_ratings"
                ]

                print("\n   Table                       | Row Count")
                print("   " + "-" * 50)

                total_rows = 0
                for table in tables:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    print(f"   {table:27} | {count:,}")
                    total_rows += count

                print("   " + "-" * 50)
                print(f"   {'TOTAL':27} | {total_rows:,}")
                print()

                # Test a complex query
                print("   Testing complex query...")
                result = await conn.fetchrow("""
                    SELECT COUNT(DISTINCT f.flight_id) as flights,
                           COUNT(DISTINCT b.booking_id) as bookings,
                           COUNT(DISTINCT p.passenger_id) as passengers
                    FROM flights f
                    LEFT JOIN bookings b ON f.flight_id = b.flight_id
                    LEFT JOIN passengers p ON b.passenger_id = p.passenger_id
                """)

                print(f"   ✅ Flights: {result['flights']}, "
                      f"Bookings: {result['bookings']}, "
                      f"Passengers: {result['passengers']}")

        except Exception as e:
            print(f"   ❌ Verification failed: {str(e)}")
            raise

    async def close(self):
        """Close database connection"""
        if self.pool:
            await self.pool.close()


async def main():
    """Main migration process"""
    print("=" * 60)
    print("SkyMarshal Database Migration to AWS RDS PostgreSQL")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize migration
    migration = RDSMigration()

    try:
        # Step 1: Connect to RDS
        await migration.initialize_connection()

        # Step 2: Load schema
        schema_file = Path(__file__).parent / "schema" / "database_schema.sql"
        await migration.load_schema(schema_file)

        # Step 3: Load data from CSVs
        print("\n" + "=" * 60)
        print("Loading data from CSV files...")
        print("=" * 60)

        base_dir = Path(__file__).parent

        for table_name, csv_name, csv_path_override in TABLE_LOAD_ORDER:
            # Determine CSV path
            if csv_path_override:
                csv_path = base_dir / csv_path_override
            else:
                # Check if it's in output directory
                csv_path = base_dir / "output" / csv_name
                if not csv_path.exists():
                    # Try without output directory
                    csv_path = base_dir / csv_name

            if csv_path.exists():
                await migration.load_csv_data(table_name, csv_path)

        # Step 4: Verify data
        await migration.verify_data()

        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print(f"\nDatabase endpoint: {migration.db_config['endpoint']}")
        print(f"Database name: {migration.db_config['dbname']}")
        print(f"Username: {migration.db_config['username']}")
        print("\nConnection string for agents:")
        print(f"postgresql://{migration.db_config['username']}:****@"
              f"{migration.db_config['host']}:{migration.db_config['port']}"
              f"/{migration.db_config['dbname']}")
        print()

        # Save connection info
        config_file = base_dir.parent / ".env.rds"
        with open(config_file, 'w') as f:
            f.write(f"# AWS RDS PostgreSQL Configuration\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            f.write(f"RDS_HOST={migration.db_config['host']}\n")
            f.write(f"RDS_PORT={migration.db_config['port']}\n")
            f.write(f"RDS_DATABASE={migration.db_config['dbname']}\n")
            f.write(f"RDS_USERNAME={migration.db_config['username']}\n")
            f.write(f"RDS_SECRET_ARN={migration.db_secret_arn}\n")
            f.write(f"\n# To get password, run:\n")
            f.write(f"# aws secretsmanager get-secret-value --secret-id {migration.db_secret_arn}\n")

        print(f"Configuration saved to: {config_file}")

    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        sys.exit(1)

    finally:
        await migration.close()

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
