# SkyMarshal AWS RDS PostgreSQL Deployment Guide

**Complete guide for deploying the SkyMarshal database to AWS RDS**

---

## 📊 Overview

This guide will deploy:
- **RDS PostgreSQL 16.3** instance (db.t4g.micro)
- **14 tables** with complete aviation data
- **~10,000 records** from CSV files
- **7.2MB** of synthetic aviation data
- **Automated backups** and monitoring
- **Secrets Manager** integration for credentials

---

## 🎯 Quick Start (5 Steps)

### Prerequisites

```bash
# 1. AWS CLI configured
aws sts get-caller-identity

# 2. Terraform installed
terraform version

# 3. Python 3.9+ with required packages
pip install asyncpg boto3
```

### Step-by-Step Deployment

```bash
# Step 1: Deploy RDS infrastructure (5-10 minutes)
cd terraform
terraform init
terraform plan -target=aws_db_instance.skymarshal_postgres
terraform apply -target=aws_db_instance.skymarshal_postgres

# Step 2: Wait for RDS to be available
aws rds wait db-instance-available --db-instance-identifier skymarshal-aviation-db

# Step 3: Run migration script
cd ../database
python3 migrate_to_rds.py

# Step 4: Verify deployment
python3 test_rds_connection.py

# Step 5: Update agent configurations
python3 update_agent_configs.py
```

---

## 📋 Detailed Steps

### 1. Deploy RDS Infrastructure

The Terraform configuration creates:
- PostgreSQL 16.3 instance
- Security group (port 5432)
- DB subnet group
- Secrets Manager secret
- CloudWatch alarms
- Enhanced monitoring

**Deploy:**

```bash
cd terraform
terraform init
terraform apply -target=aws_db_instance.skymarshal_postgres
```

**Output:**
```
rds_endpoint = "skymarshal-aviation-db.xxxxxxxxx.us-east-1.rds.amazonaws.com:5432"
rds_database_name = "skymarshal_aviation"
rds_username = "skymarshal_admin"
rds_password_secret_arn = "arn:aws:secretsmanager:..."
```

**Cost**: ~$12-15/month for db.t4g.micro

### 2. Migrate Database Schema and Data

The migration script:
1. Retrieves credentials from Secrets Manager
2. Connects to RDS PostgreSQL
3. Loads schema from `schema/database_schema.sql`
4. Loads data from CSV files in correct order
5. Verifies data integrity

**Run:**

```bash
cd database
python3 migrate_to_rds.py
```

**Expected output:**

```
============================================================
SkyMarshal Database Migration to AWS RDS PostgreSQL
============================================================

🔐 Retrieving RDS credentials from Secrets Manager...
   Found secret: skymarshal/rds/password-xxx
   ✅ Retrieved credentials for: skymarshal-aviation-db.xxx.us-east-1.rds.amazonaws.com

🔌 Connecting to RDS PostgreSQL...
   ✅ Connected to: skymarshal-aviation-db.xxx.us-east-1.rds.amazonaws.com:5432

📄 Loading database schema...
   ✅ Schema loaded successfully

============================================================
Loading data from CSV files...
============================================================

📊 Loading data into: flights
   Found 35 rows
   ✅ Inserted 35 rows into flights

📊 Loading data into: passengers
   Found 8,800 rows
   Progress: 500/8,800 rows inserted...
   ✅ Inserted 8,800 rows into passengers

... (continues for all tables)

✅ Verifying data load...

   Table                       | Row Count
   --------------------------------------------------
   aircraft_types              | 9
   airports                    | 13
   flights                     | 35
   passengers                  | 8,800
   bookings                    | 8,800
   baggage                     | 11,673
   cargo_shipments             | 199
   cargo_flight_assignments    | 235
   crew_members                | 500
   crew_roster                 | 464
   crew_positions              | 5
   commodity_types             | 9
   frequent_flyer_tiers        | 4
   crew_type_ratings           | 150
   --------------------------------------------------
   TOTAL                       | 30,896

   ✅ Flights: 35, Bookings: 8,800, Passengers: 8,800

============================================================
✅ Migration completed successfully!
============================================================

Database endpoint: skymarshal-aviation-db.xxx.us-east-1.rds.amazonaws.com:5432
Database name: skymarshal_aviation
Username: skymarshal_admin

Configuration saved to: /path/to/.env.rds
```

---

## 🔧 Configuration Files

### .env.rds (Generated)

After migration, a `.env.rds` file is created:

```bash
# AWS RDS PostgreSQL Configuration
# Generated: 2026-01-30T16:30:00

RDS_HOST=skymarshal-aviation-db.xxx.us-east-1.rds.amazonaws.com
RDS_PORT=5432
RDS_DATABASE=skymarshal_aviation
RDS_USERNAME=skymarshal_admin
RDS_SECRET_ARN=arn:aws:secretsmanager:us-east-1:368613657554:secret:skymarshal/rds/password-xxx

# To get password, run:
# aws secretsmanager get-secret-value --secret-id arn:aws:secretsmanager:...
```

### Update Agent Configurations

All agents need to be updated to use RDS instead of local PostgreSQL.

**Option 1: Use environment variables**

```bash
# In your .env file
DB_HOST=skymarshal-aviation-db.xxx.us-east-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=skymarshal_aviation
DB_USER=skymarshal_admin
DB_PASSWORD=<from secrets manager>
```

**Option 2: Use Secrets Manager (Recommended)**

Update `database/manager/database.py`:

```python
import boto3
import json

def get_db_credentials():
    """Retrieve credentials from Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    secret = client.get_secret_value(SecretId='skymarshal/rds/password-xxx')
    return json.loads(secret['SecretString'])

class DatabaseManager:
    async def initialize(self):
        creds = get_db_credentials()
        self.pool = await asyncpg.create_pool(
            host=creds['host'],
            port=creds['port'],
            database=creds['dbname'],
            user=creds['username'],
            password=creds['password'],
            min_size=5,
            max_size=20
        )
```

---

## 🧪 Testing

### Test RDS Connection

```python
# test_rds_connection.py
import asyncio
import asyncpg
import boto3
import json

async def test_connection():
    # Get credentials
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='<your-secret-arn>')
    creds = json.loads(response['SecretString'])

    # Connect
    conn = await asyncpg.connect(
        host=creds['host'],
        port=creds['port'],
        database=creds['dbname'],
        user=creds['username'],
        password=creds['password']
    )

    # Test query
    result = await conn.fetchval('SELECT COUNT(*) FROM flights')
    print(f"✅ RDS Connection successful! Flights: {result}")

    await conn.close()

asyncio.run(test_connection())
```

### Query Examples

```sql
-- Get all flights
SELECT f.flight_number, f.scheduled_departure,
       o.iata_code as origin, d.iata_code as destination
FROM flights f
JOIN airports o ON f.origin_airport_id = o.airport_id
JOIN airports d ON f.destination_airport_id = d.airport_id
ORDER BY f.scheduled_departure;

-- Get passenger statistics
SELECT COUNT(*) as total_passengers,
       COUNT(CASE WHEN is_vip THEN 1 END) as vip_count,
       COUNT(CASE WHEN frequent_flyer_tier_id = 1 THEN 1 END) as platinum
FROM passengers;

-- Get cargo summary
SELECT COUNT(*) as total_shipments,
       SUM(total_weight_kg) as total_weight,
       AVG(total_weight_kg) as avg_weight
FROM cargo_shipments
WHERE shipment_status = 'Confirmed';
```

---

## 📊 Database Schema

### Core Tables (14)

#### Aviation Operations
1. **aircraft_types** - 9 aircraft types (A380, A350, B787, etc.)
2. **airports** - 13 airports (AUH hub + 12 destinations)
3. **flights** - 35 flights over 7 days

#### Passenger Management
4. **frequent_flyer_tiers** - 4 tiers (Platinum, Gold, Silver, Bronze)
5. **passengers** - 8,800 passengers with profiles
6. **bookings** - 8,800 bookings with PNR and seat assignments
7. **baggage** - 11,673 baggage items

#### Cargo Operations
8. **commodity_types** - 9 commodity types
9. **cargo_shipments** - 199 shipments with AWB numbers
10. **cargo_flight_assignments** - 235 cargo-to-flight mappings

#### Crew Management
11. **crew_positions** - 5 positions (CAPT, FO, CSM, PURSER, FA)
12. **crew_members** - 500 crew members
13. **crew_type_ratings** - 150 type ratings
14. **crew_roster** - 464 flight assignments

---

## 💰 Cost Estimate

### RDS Instance

```
Instance: db.t4g.micro (2 vCPUs, 1GB RAM)
Region: us-east-1

Monthly Costs:
  Compute:               $12.41/month
  Storage (20GB gp3):    $2.30/month
  Backup Storage (7d):   $0.00/month (free tier)
  Enhanced Monitoring:   $0.50/month
  Performance Insights:  $0.00/month (7-day retention)
  ────────────────────────────────────
  TOTAL:                 ~$15/month
```

### Scaling Options

```
Production Scaling:
  db.t4g.small  (2 vCPU, 2GB):   ~$25/month
  db.t4g.medium (2 vCPU, 4GB):   ~$50/month
  db.m6g.large  (2 vCPU, 8GB):   ~$130/month

Multi-AZ (High Availability):
  Adds 100% cost (doubles price)
```

---

## 🔒 Security

### Access Control

**Security Group Rules:**
```
Inbound:
  PostgreSQL (5432) from 0.0.0.0/0 (⚠️ Restrict in production)

Outbound:
  All traffic allowed
```

**Production Recommendations:**
1. Restrict security group to specific IP ranges/VPCs
2. Use VPN or VPC peering for access
3. Enable SSL/TLS for connections
4. Implement IAM authentication
5. Regular security audits

### Encryption

```
At Rest: ✅ Enabled (default RDS encryption)
In Transit: ⏳ Configure SSL/TLS in application
Backups: ✅ Encrypted automatically
```

---

## 📈 Monitoring

### CloudWatch Alarms

**Automatically created:**
1. **High CPU** - Alert when >80% for 10 minutes
2. **Low Storage** - Alert when <2GB free
3. **High Connections** - Alert when >80 connections

### Enhanced Monitoring

Monitors (every 60 seconds):
- OS processes
- CPU utilization
- Memory usage
- Disk I/O
- Network throughput

### Performance Insights

Free tier (7-day retention):
- Top SQL queries
- Wait events
- Database load

**Access:**
```
https://console.aws.amazon.com/rds/home?region=us-east-1#performance-insights-v20206:instanceId=skymarshal-aviation-db
```

---

## 🛠️ Maintenance

### Backups

```
Automated Backups:
  Retention: 7 days
  Window: 03:00-04:00 UTC (daily)

Manual Snapshots:
  Create anytime via AWS Console or CLI
  Retained until manually deleted
```

### Maintenance Window

```
Weekly Maintenance:
  Day: Monday
  Time: 04:00-05:00 UTC

Auto Minor Version Upgrade: ✅ Enabled
```

### Restore from Backup

```bash
# List available backups
aws rds describe-db-snapshots \
  --db-instance-identifier skymarshal-aviation-db

# Restore to new instance
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier skymarshal-aviation-db-restored \
  --db-snapshot-identifier rds:skymarshal-aviation-db-2026-01-30-03-00
```

---

## 🔧 Troubleshooting

### Connection Issues

**Problem**: Cannot connect to RDS

**Solution**:
```bash
# 1. Check security group allows your IP
aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=skymarshal-rds-*"

# 2. Check RDS is available
aws rds describe-db-instances \
  --db-instance-identifier skymarshal-aviation-db \
  --query 'DBInstances[0].DBInstanceStatus'

# 3. Test connection with psql
psql -h skymarshal-aviation-db.xxx.us-east-1.rds.amazonaws.com \
     -U skymarshal_admin \
     -d skymarshal_aviation
```

### Migration Failures

**Problem**: CSV data load fails

**Solution**:
1. Check CSV file encoding (UTF-8)
2. Verify column names match schema
3. Check for NULL values
4. Validate foreign key references

### Performance Issues

**Problem**: Slow queries

**Solution**:
```sql
-- Check missing indexes
SELECT schemaname, tablename, indexname
FROM pg_indexes
WHERE tablename IN ('flights', 'bookings', 'passengers');

-- Analyze query performance
EXPLAIN ANALYZE
SELECT * FROM flights WHERE flight_number = 'EY123';
```

---

## 📚 Next Steps

### Integration with Agents

1. **Update Database Manager**
   - Add Secrets Manager integration
   - Update connection pooling settings

2. **Test Multi-Agent Queries**
   - Verify all 10 agents can connect
   - Test concurrent access

3. **Optimize Queries**
   - Add indexes for common queries
   - Implement connection pooling

4. **Set Up Monitoring**
   - CloudWatch dashboards
   - SNS notifications for alarms

---

## 📞 Support

**AWS RDS Console:**
https://console.aws.amazon.com/rds/home?region=us-east-1

**Secrets Manager:**
https://console.aws.amazon.com/secretsmanager/home?region=us-east-1

**CloudWatch Logs:**
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1

---

**Deployment Complete! Your SkyMarshal database is now running on AWS RDS PostgreSQL** 🚀
