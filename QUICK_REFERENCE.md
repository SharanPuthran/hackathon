# Etihad Airways Database - Quick Reference

## 📊 Generated Data Summary

```
┌──────────────────────────────────────────────────────────────┐
│           ETIHAD AIRWAYS AVIATION DATABASE                   │
│                  Synthetic Data Overview                     │
└──────────────────────────────────────────────────────────────┘

📅 DATE RANGE: 2026-01-30 to 2026-02-05 (7 days)

✈️  FLIGHTS
    • Total: 35 flights (5 per day)
    • Widebody: 21 flights (60%)
    • Narrowbody: 14 flights (40%)
    • All connected to AUH hub ✓

👥 PASSENGERS
    • Total: 8,820 passengers
    • Load Factor: 80-90% average
    • Frequent Flyers: 15%
    • VIP Passengers: 3%
    • Medical Conditions: 2%
    • Connections: 10%

🧳 BAGGAGE
    • Total Items: 11,052
    • Checked Bags: ~8,820
    • Average Weight: 24.5 kg
    • Priority: VIP + FF tiers

📦 CARGO
    • Shipments: 199
    • AWB Prefix: 607 ✓
    • Confirmed: 149 (75%)
    • Queued: 30 (15%)
    • Cancelled: 20 (10%)
    • Flight Assignments: 154

👨‍✈️ CREW
    • Total Crew: 715 members
    • Captains: 70
    • First Officers: 70
    • Cabin Service Managers: 50
    • Flight Attendants: 525
    • Duty Assignments: 448

┌──────────────────────────────────────────────────────────────┐
│                     TABLE STATISTICS                         │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────┬──────────┬──────────────┐
│ Table Name                  │ Records  │ File Size    │
├─────────────────────────────┼──────────┼──────────────┤
│ flights                     │       35 │       3.6 KB │
│ passengers                  │    8,820 │       867 KB │
│ bookings                    │    8,820 │       435 KB │
│ baggage                     │   11,052 │       622 KB │
│ cargo_shipments             │      199 │        26 KB │
│ cargo_flight_assignments    │      154 │       5.9 KB │
│ crew_members                │      715 │        45 KB │
│ crew_roster                 │      448 │        29 KB │
└─────────────────────────────┴──────────┴──────────────┘

                    TOTAL DATABASE SIZE: ~2.0 MB
```

## 🔑 Key Identifiers Format

```
Flight Number:     EY + 3-4 digits        (e.g., EY8086, EY432)
PNR:               6 alphanumeric chars   (e.g., A4B2C9)
AWB Number:        607 + 8 digits         (e.g., 60750956964)
Baggage Tag:       EY + 8 digits          (e.g., EY12345678)
FF Number:         EG + 8 digits          (e.g., EG12345678)
Employee ID:       EY + 6 digits          (e.g., EY123456)
```

## 🛫 Sample Flight Data

```
┌──────────┬─────────┬──────────┬──────────┬──────────────────────┐
│ Flight   │ Aircraft│ Route    │ DateTime │ Pax/Cargo/Crew       │
├──────────┼─────────┼──────────┼──────────┼──────────────────────┤
│ EY8086   │ A380    │ AUH→FCO  │ 01/30 03 │ 465pax 5crg 18crew   │
│ EY4943   │ B787-9  │ AUH→DOH  │ 01/30 00 │ 253pax 6crg 14crew   │
│ EY432    │ B787-10 │ JFK→AUH  │ 01/30 13 │ 270pax 4crg 16crew   │
│ EY1202   │ B787-9  │ AUH→DEL  │ 01/30 16 │ 245pax 7crg 14crew   │
│ EY8184   │ A350    │ AUH→LHR  │ 01/31 15 │ 241pax 5crg 14crew   │
└──────────┴─────────┴──────────┴──────────┴──────────────────────┘
```

## 📦 Commodity Type Distribution

```
General Cargo           ████████████████████░░░░░  40%
Pharma (SecureTech)     ███████░░░░░░░░░░░░░░░░░░  15%
Perishables/Fresh       █████░░░░░░░░░░░░░░░░░░░░  10%
Fresh (FreshForward)    █████░░░░░░░░░░░░░░░░░░░░  10%
Live Animals            █████░░░░░░░░░░░░░░░░░░░░  10%
E-Commerce              █████░░░░░░░░░░░░░░░░░░░░  10%
Human Remains           █░░░░░░░░░░░░░░░░░░░░░░░░   3%
Valuables               ░░░░░░░░░░░░░░░░░░░░░░░░░   2%
```

## 🎖️ Frequent Flyer Tiers

```
┌──────────┬───────┬────────────────┬──────────────┐
│ Tier     │ Level │ Extra Baggage  │ Benefits     │
├──────────┼───────┼────────────────┼──────────────┤
│ Platinum │   4   │     +20 kg     │ Board+Lounge │
│ Gold     │   3   │     +15 kg     │ Board+Lounge │
│ Silver   │   2   │     +10 kg     │ Board        │
│ Bronze   │   1   │      +5 kg     │ -            │
└──────────┴───────┴────────────────┴──────────────┘

Distribution: 10% Platinum, 20% Gold, 30% Silver, 40% Bronze
```

## 🌍 Airports in Database

```
HUB: ⭐ AUH - Abu Dhabi International (All flights)

DESTINATIONS:
  Europe:    LHR (London), CDG (Paris), FCO (Rome), FRA (Frankfurt)
  Americas:  JFK (New York)
  Asia:      DEL (Delhi), BKK (Bangkok), SIN (Singapore)
  Oceania:   SYD (Sydney)
  Middle East: DXB (Dubai), DOH (Doha), CAI (Cairo)
```

## 🛠️ Quick Commands

```bash
# Navigate to project
cd /Users/sharanputhran/.gemini/antigravity/scratch/etihad-aviation-db

# Generate fresh data
python3 generate_data.py

# Convert to SQL inserts
python3 csv_to_sql.py

# Create database (MySQL)
mysql -u root -p
CREATE DATABASE etihad_aviation;
USE etihad_aviation;
SOURCE database_schema.sql;

# View sample data
head -20 output/flights.csv
head -20 output/passengers.csv
```

## 📚 File Locations

```
Schema Design:
  📄 implementation_plan.md
  📄 database_schema.sql
  📄 er_diagram.md

Generated Data:
  📁 output/
     ├── flights.csv
     ├── passengers.csv
     ├── bookings.csv
     ├── baggage.csv
     ├── cargo_shipments.csv
     ├── cargo_flight_assignments.csv
     ├── crew_members.csv
     └── crew_roster.csv

Scripts:
  🐍 generate_data.py
  🐍 csv_to_sql.py
  📖 README.md
```

## ✅ Validation Checklist

- [x] 35 flights (5/day × 7 days)
- [x] All flight numbers start with EY
- [x] All flights connected to AUH
- [x] 80-90% load factor
- [x] AWB prefix 607
- [x] 8-digit master document numbers
- [x] Unique PNRs, passports, AWBs
- [x] Realistic crew assignments
- [x] No data constraint violations

## 🎯 Ready for Hackathon!

Database Location:
`/Users/sharanputhran/.gemini/antigravity/scratch/etihad-aviation-db`

Total Records: 30,243 across 8 tables
Data Quality: Production-ready ✓
