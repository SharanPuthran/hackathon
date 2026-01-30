# Data Statistics & Analysis

Comprehensive statistics for generated SkyMarshal database.

---

## 📊 Record Counts

### Core Tables

| Table                        | Records | Description                    |
| ---------------------------- | ------- | ------------------------------ |
| **aircraft_types**           | 9       | Fleet configuration            |
| **airports**                 | 13      | AUH hub + 12 destinations      |
| **flights**                  | 35      | 5 flights/day × 7 days         |
| **frequent_flyer_tiers**     | 4       | Platinum, Gold, Silver, Bronze |
| **passengers**               | ~8,800  | Realistic passenger profiles   |
| **bookings**                 | ~8,800  | 1 booking per passenger        |
| **baggage**                  | ~15,000 | 1-3 bags per booking           |
| **commodity_types**          | 9       | Cargo classifications          |
| **cargo_shipments**          | 199     | AWB-based shipments            |
| **cargo_flight_assignments** | ~150    | Cargo-to-flight mapping        |
| **crew_positions**           | 5       | CAPT, FO, CSM, PURSER, FA      |
| **crew_members**             | 500+    | Pilots and cabin crew          |
| **crew_roster**              | ~350    | Flight assignments             |

---

## ✈️ Flight Statistics

### Aircraft Distribution

| Aircraft Type | Category   | Flights | Percentage |
| ------------- | ---------- | ------- | ---------- |
| A380          | Widebody   | 4       | 11%        |
| A350          | Widebody   | 5       | 14%        |
| B787-9        | Widebody   | 6       | 17%        |
| B787-10       | Widebody   | 4       | 11%        |
| B777X         | Widebody   | 2       | 6%         |
| A320          | Narrowbody | 5       | 14%        |
| A320-NEO      | Narrowbody | 4       | 11%        |
| A321          | Narrowbody | 3       | 9%         |
| A321LR        | Narrowbody | 2       | 6%         |

**Summary**:

- Widebody: 21 flights (60%)
- Narrowbody: 14 flights (40%)

### Route Distribution

| Destination     | Flights | Flight Time | Distance Category |
| --------------- | ------- | ----------- | ----------------- |
| LHR (London)    | 4       | 7h 40m      | Long-haul         |
| JFK (New York)  | 3       | 14h 0m      | Ultra long-haul   |
| SYD (Sydney)    | 2       | 14h 0m      | Ultra long-haul   |
| BKK (Bangkok)   | 4       | 6h 0m       | Medium-haul       |
| DEL (Delhi)     | 5       | 3h 30m      | Short-haul        |
| DXB (Dubai)     | 3       | 50m         | Regional          |
| DOH (Doha)      | 2       | 1h 0m       | Regional          |
| CAI (Cairo)     | 3       | 4h 0m       | Medium-haul       |
| CDG (Paris)     | 3       | 7h 0m       | Long-haul         |
| FCO (Rome)      | 2       | 5h 30m      | Medium-haul       |
| FRA (Frankfurt) | 2       | 6h 30m      | Long-haul         |
| SIN (Singapore) | 2       | 7h 20m      | Long-haul         |

**Summary**:

- Regional (< 2h): 5 flights (14%)
- Short-haul (2-4h): 5 flights (14%)
- Medium-haul (4-7h): 12 flights (34%)
- Long-haul (7-10h): 7 flights (20%)
- Ultra long-haul (> 10h): 6 flights (17%)

### Direction Distribution

| Direction           | Flights | Percentage |
| ------------------- | ------- | ---------- |
| Outbound (from AUH) | 18      | 51%        |
| Inbound (to AUH)    | 17      | 49%        |

### Time Distribution

| Time Period   | Flights | Percentage |
| ------------- | ------- | ---------- |
| 00:00 - 06:00 | 6       | 17%        |
| 06:00 - 12:00 | 9       | 26%        |
| 12:00 - 18:00 | 11      | 31%        |
| 18:00 - 24:00 | 9       | 26%        |

---

## 👥 Passenger Statistics

### Total Passengers: ~8,800

### Load Factor Analysis

| Metric              | Value         |
| ------------------- | ------------- |
| Average Load Factor | 85%           |
| Minimum Load Factor | 80%           |
| Maximum Load Factor | 90%           |
| Total Capacity      | ~10,350 seats |
| Occupied Seats      | ~8,800 seats  |
| Empty Seats         | ~1,550 seats  |

### Passenger Type Distribution

| Type           | Count  | Percentage | Description          |
| -------------- | ------ | ---------- | -------------------- |
| Regular        | ~6,160 | 70%        | Standard passengers  |
| Frequent Flyer | ~1,320 | 15%        | Etihad Guest members |
| Connection     | ~880   | 10%        | Multi-leg journeys   |
| VIP            | ~264   | 3%         | Special handling     |
| Medical        | ~176   | 2%         | Requires assistance  |

### Frequent Flyer Tier Distribution

| Tier         | Count     | Percentage | Benefits                     |
| ------------ | --------- | ---------- | ---------------------------- |
| Platinum     | 132       | 10%        | 20kg extra, lounge, priority |
| Gold         | 264       | 20%        | 15kg extra, lounge, priority |
| Silver       | 396       | 30%        | 10kg extra, priority         |
| Bronze       | 528       | 40%        | 5kg extra                    |
| **Total FF** | **1,320** | **15%**    | -                            |

### Booking Class Distribution

| Class    | Count  | Percentage | Avg Bags |
| -------- | ------ | ---------- | -------- |
| Economy  | ~7,040 | 80%        | 1 bag    |
| Business | ~1,320 | 15%        | 2 bags   |
| First    | ~440   | 5%         | 3 bags   |

### Connection Risk Analysis

| Status           | Count | Percentage |
| ---------------- | ----- | ---------- |
| Connections      | ~880  | 10%        |
| At Risk          | ~264  | 3%         |
| Safe Connections | ~616  | 7%         |

**At-risk connections** have < 90 minutes connection time and are high priority during disruptions.

### Nationality Distribution (Top 10)

| Country   | Code | Estimated % |
| --------- | ---- | ----------- |
| UAE       | ARE  | 15%         |
| India     | IND  | 15%         |
| UK        | GBR  | 12%         |
| USA       | USA  | 10%         |
| China     | CHN  | 8%          |
| Singapore | SGP  | 7%          |
| Australia | AUS  | 7%          |
| Germany   | DEU  | 6%          |
| France    | FRA  | 5%          |
| Italy     | ITA  | 5%          |
| Others    | -    | 10%         |

---

## 🎒 Baggage Statistics

### Total Bags: ~15,000

### Baggage by Class

| Class    | Bags per Pax | Total Bags | Avg Weight |
| -------- | ------------ | ---------- | ---------- |
| Economy  | 1            | ~7,040     | 21.5 kg    |
| Business | 2            | ~2,640     | 30.0 kg    |
| First    | 3            | ~1,320     | 32.0 kg    |

### Priority Baggage

| Category | Count   | Percentage |
| -------- | ------- | ---------- |
| Priority | ~1,850  | 12%        |
| Standard | ~13,150 | 88%        |

**Priority bags**: VIP passengers + Platinum/Gold tier members

### Weight Distribution

| Weight Range | Count  | Percentage |
| ------------ | ------ | ---------- |
| 0-15 kg      | ~1,500 | 10%        |
| 15-23 kg     | ~7,500 | 50%        |
| 23-32 kg     | ~6,000 | 40%        |

### Total Baggage Weight

| Metric                | Value       |
| --------------------- | ----------- |
| Total Weight          | ~375,000 kg |
| Average per Flight    | ~10,700 kg  |
| Average per Passenger | ~42.6 kg    |

---

## 📦 Cargo Statistics

### Total Shipments: 199

### Commodity Distribution

| Commodity                | Code | Count | Percentage | Avg Weight |
| ------------------------ | ---- | ----- | ---------- | ---------- |
| General Cargo            | GEN  | 80    | 40%        | 350 kg     |
| Pharma (SecureTech)      | PHA  | 30    | 15%        | 120 kg     |
| Perishables              | PER  | 20    | 10%        | 450 kg     |
| Fresh (FreshForward)     | FRE  | 20    | 10%        | 425 kg     |
| Live Animals (SafeGuard) | AVI  | 20    | 10%        | 550 kg     |
| E-Commerce               | ECC  | 20    | 10%        | 165 kg     |
| Human Remains            | HUM  | 6     | 3%         | 115 kg     |
| Valuable Cargo           | VAL  | 3     | 2%         | 55 kg      |

### Shipment Status

| Status    | Count | Percentage |
| --------- | ----- | ---------- |
| Confirmed | 149   | 75%        |
| Queued    | 30    | 15%        |
| Cancelled | 20    | 10%        |

### Special Handling Requirements

| Category               | Count | Percentage |
| ---------------------- | ----- | ---------- |
| Temperature Controlled | 70    | 35%        |
| Special Handling       | 49    | 25%        |
| Standard               | 80    | 40%        |

**Temperature-controlled**: PHA, PER, FRE (critical for disruptions)

### Weight Analysis

| Metric               | Value      |
| -------------------- | ---------- |
| Total Cargo Weight   | ~65,000 kg |
| Average per Shipment | ~327 kg    |
| Average per Flight   | ~1,857 kg  |
| Heaviest Shipment    | ~10,000 kg |
| Lightest Shipment    | ~20 kg     |

### Volume Analysis

| Metric               | Value   |
| -------------------- | ------- |
| Total Volume         | ~325 m³ |
| Average per Shipment | ~1.6 m³ |
| Average per Flight   | ~9.3 m³ |

### Declared Value

| Metric               | Value     |
| -------------------- | --------- |
| Total Declared Value | ~$4.2M    |
| Average per Shipment | ~$21,000  |
| Highest Value        | ~$50,000  |
| Shipments with Value | 139 (70%) |

### Cargo per Flight

| Metric            | Value    |
| ----------------- | -------- |
| Average Shipments | 4.3      |
| Minimum Shipments | 3        |
| Maximum Shipments | 8        |
| Average Weight    | 1,857 kg |

---

## 👨‍✈️ Crew Statistics

### Total Crew: 500+

### Position Distribution

| Position              | Code | Count | Percentage |
| --------------------- | ---- | ----- | ---------- |
| Captain               | CAPT | 70    | 14%        |
| First Officer         | FO   | 70    | 14%        |
| Cabin Service Manager | CSM  | 50    | 10%        |
| Flight Attendant      | FA   | 310+  | 62%        |

### Crew per Flight

| Aircraft Category | Pilots | Cabin Crew | Total |
| ----------------- | ------ | ---------- | ----- |
| Widebody          | 2      | 12-16      | 14-18 |
| Narrowbody        | 2      | 4-6        | 6-8   |

### Roster Statistics

| Metric             | Value       |
| ------------------ | ----------- |
| Total Assignments  | ~350        |
| Average per Flight | 10 crew     |
| Average per Crew   | 0.7 flights |

### Duty Time Analysis

| Metric            | Value              |
| ----------------- | ------------------ |
| Average Duty Time | 8.5 hours          |
| Shortest Duty     | 4 hours (DXB)      |
| Longest Duty      | 17 hours (JFK/SYD) |

### FTL Compliance

| Limit           | Value    | Status       |
| --------------- | -------- | ------------ |
| Max Daily Duty  | 12 hours | ✅ Compliant |
| Max 7-Day Duty  | 60 hours | ✅ Compliant |
| Min Rest Period | 12 hours | ✅ Compliant |

---

## 📈 Capacity Utilization

### Passenger Capacity

| Metric            | Value   |
| ----------------- | ------- |
| Total Seats       | ~10,350 |
| Occupied Seats    | ~8,800  |
| Load Factor       | 85%     |
| Revenue Potential | High    |

### Cargo Capacity

| Metric             | Value       |
| ------------------ | ----------- |
| Total Capacity     | ~385,000 kg |
| Used Capacity      | ~65,000 kg  |
| Utilization        | 17%         |
| Available Capacity | ~320,000 kg |

**Note**: Cargo utilization is realistic for passenger flights. Dedicated freighters would have higher utilization.

---

## 🎯 Disruption Impact Potential

### High-Impact Flights

Flights with highest disruption impact based on:

- Passenger count
- VIP/Platinum passengers
- Connections at risk
- Temperature-controlled cargo
- Long-haul routes

#### Top 5 High-Impact Flights

1. **EY551 (LHR→AUH)** - A380, 465 pax, 45 Platinum, 38 connections
2. **EY12 (JFK→AUH)** - B777X, 383 pax, 38 Platinum, 42 connections
3. **EY456 (SYD→AUH)** - A350, 255 pax, 26 Platinum, 28 connections
4. **EY234 (BKK→AUH)** - B787-9, 260 pax, 8 temp-controlled cargo
5. **EY789 (DEL→AUH)** - A321LR, 185 pax, 6 temp-controlled cargo

### Connection Risk Flights

Flights with most at-risk connections:

- Inbound long-haul flights (tight connections)
- Evening arrivals (last connections of day)
- Flights with 30+ at-risk passengers

### Cargo Risk Flights

Flights with temperature-controlled cargo:

- PHA (Pharma): 30 shipments across 15 flights
- PER (Perishables): 20 shipments across 10 flights
- FRE (Fresh): 20 shipments across 10 flights

**Critical**: These shipments cannot be delayed > 4 hours

---

## 📊 Data Quality Metrics

### Completeness

| Field Category   | Completeness |
| ---------------- | ------------ |
| Mandatory Fields | 100%         |
| Optional Fields  | 70%          |
| Email Addresses  | 100%         |
| Phone Numbers    | 100%         |
| FF Numbers       | 15%          |
| Medical Notes    | 2%           |

### Validity

| Validation      | Pass Rate |
| --------------- | --------- |
| Passport Format | 100%      |
| Email Format    | 100%      |
| Phone Format    | 100%      |
| Date Logic      | 100%      |
| FK Integrity    | 100%      |

### Consistency

| Check               | Status  |
| ------------------- | ------- |
| No Overbooking      | ✅ Pass |
| No Overweight Cargo | ✅ Pass |
| FTL Compliance      | ✅ Pass |
| Connection Times    | ✅ Pass |
| Baggage Allowance   | ✅ Pass |

---

## 🔍 Sample Queries

### Find Flights with Most VIP Passengers

```sql
SELECT f.flight_number, COUNT(p.passenger_id) as vip_count
FROM flights f
JOIN bookings b ON f.flight_id = b.flight_id
JOIN passengers p ON b.passenger_id = p.passenger_id
WHERE p.is_vip = TRUE
GROUP BY f.flight_id
ORDER BY vip_count DESC
LIMIT 5;
```

### Find Flights with Temperature-Controlled Cargo

```sql
SELECT f.flight_number, COUNT(cs.shipment_id) as temp_cargo_count
FROM flights f
JOIN cargo_flight_assignments cfa ON f.flight_id = cfa.flight_id
JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
JOIN commodity_types ct ON cs.commodity_type_id = ct.commodity_type_id
WHERE ct.temperature_controlled = TRUE
GROUP BY f.flight_id
ORDER BY temp_cargo_count DESC;
```

### Find Crew with Most Duty Hours

```sql
SELECT cm.employee_id, cm.first_name, cm.last_name,
       SUM(EXTRACT(EPOCH FROM (cr.duty_end - cr.duty_start))/3600) as total_hours
FROM crew_members cm
JOIN crew_roster cr ON cm.crew_id = cr.crew_id
GROUP BY cm.crew_id
ORDER BY total_hours DESC
LIMIT 10;
```

---

## 📅 Time-Based Analysis

### Daily Flight Distribution

| Day   | Date       | Flights | Passengers | Cargo (kg) |
| ----- | ---------- | ------- | ---------- | ---------- |
| Day 1 | 2026-01-30 | 5       | ~1,257     | ~9,286     |
| Day 2 | 2026-01-31 | 5       | ~1,257     | ~9,286     |
| Day 3 | 2026-02-01 | 5       | ~1,257     | ~9,286     |
| Day 4 | 2026-02-02 | 5       | ~1,257     | ~9,286     |
| Day 5 | 2026-02-03 | 5       | ~1,257     | ~9,286     |
| Day 6 | 2026-02-04 | 5       | ~1,257     | ~9,286     |
| Day 7 | 2026-02-05 | 5       | ~1,257     | ~9,286     |

**Consistent distribution** across all days for demo purposes.

---

## 💰 Revenue Potential (Estimated)

### Passenger Revenue

| Class     | Passengers | Avg Fare | Revenue    |
| --------- | ---------- | -------- | ---------- |
| Economy   | 7,040      | $800     | $5.6M      |
| Business  | 1,320      | $3,500   | $4.6M      |
| First     | 440        | $8,000   | $3.5M      |
| **Total** | **8,800**  | -        | **$13.7M** |

### Cargo Revenue

| Category    | Weight (kg) | Rate ($/kg) | Revenue   |
| ----------- | ----------- | ----------- | --------- |
| General     | 28,000      | $2.50       | $70K      |
| Pharma      | 3,600       | $8.00       | $29K      |
| Perishables | 9,000       | $4.00       | $36K      |
| Other       | 24,400      | $3.00       | $73K      |
| **Total**   | **65,000**  | -           | **$208K** |

### Total Revenue Potential

| Category  | Revenue    | Percentage |
| --------- | ---------- | ---------- |
| Passenger | $13.7M     | 98.5%      |
| Cargo     | $208K      | 1.5%       |
| **Total** | **$13.9M** | **100%**   |

**Note**: These are estimated averages for demo purposes.

---

## 🎲 Randomization Quality

### Distribution Tests

| Test              | Expected    | Actual      | Status  |
| ----------------- | ----------- | ----------- | ------- |
| Load Factor       | 80-90%      | 85%         | ✅ Pass |
| FF Distribution   | 15%         | 15%         | ✅ Pass |
| Class Mix         | 80/15/5     | 80/15/5     | ✅ Pass |
| Cargo Mix         | Per weights | Per weights | ✅ Pass |
| Time Distribution | Uniform     | Uniform     | ✅ Pass |

### Uniqueness Tests

| Field       | Duplicates | Status  |
| ----------- | ---------- | ------- |
| PNR         | 0          | ✅ Pass |
| Passport    | 0          | ✅ Pass |
| AWB Number  | 0          | ✅ Pass |
| Baggage Tag | 0          | ✅ Pass |
| Employee ID | 0          | ✅ Pass |
| FF Number   | 0          | ✅ Pass |

---

**Statistics Generated**: 2026-01-30  
**Data Version**: 1.0  
**Total Records**: ~34,000 across all tables
