# Database Improvement Ideas

Comprehensive list of enhancements for iteration and production readiness.

---

## 🎯 Priority Matrix

| Priority | Complexity | Impact | Category             |
| -------- | ---------- | ------ | -------------------- |
| P0       | Low        | High   | Quick wins           |
| P1       | Medium     | High   | High value           |
| P2       | High       | High   | Strategic            |
| P3       | Low        | Medium | Nice to have         |
| P4       | High       | Low    | Future consideration |

---

## 🚀 P0: Quick Wins (Implement First)

### 1. Add Aircraft Registration Numbers

**Current**: Only aircraft type tracked  
**Improvement**: Add tail numbers (A6-APH, A6-EYA, etc.)

```sql
ALTER TABLE flights ADD COLUMN aircraft_registration VARCHAR(10);
CREATE INDEX idx_flights_registration ON flights(aircraft_registration);
```

**Benefits**:

- Track specific aircraft maintenance history
- Identify aircraft-specific issues
- Better MEL tracking
- Realistic disruption scenarios

**Effort**: 1 hour  
**Impact**: High for maintenance agent

---

### 2. Add Flight Delay Reasons

**Current**: Only status tracked  
**Improvement**: Add delay reason codes

```sql
CREATE TABLE delay_reasons (
    reason_id INT PRIMARY KEY,
    reason_code VARCHAR(10) UNIQUE,
    reason_name VARCHAR(100),
    category ENUM('Technical', 'Operational', 'Weather', 'ATC', 'Passenger')
);

ALTER TABLE flights ADD COLUMN delay_reason_id INT;
ALTER TABLE flights ADD COLUMN delay_minutes INT;
```

**Benefits**:

- Historical delay analysis
- Pattern recognition for ML
- Better disruption categorization
- Regulatory reporting

**Effort**: 2 hours  
**Impact**: High for analytics

---

### 3. Add Connection Flight Links

**Current**: Connection flag only  
**Improvement**: Link connecting flights

```sql
ALTER TABLE bookings ADD COLUMN inbound_flight_id INT;
ALTER TABLE bookings ADD COLUMN minimum_connection_time INT;
ALTER TABLE bookings ADD COLUMN connection_buffer_minutes INT;
```

**Benefits**:

- Calculate actual connection risk
- Identify cascading impacts
- Better rebooking logic
- Passenger journey tracking

**Effort**: 2 hours  
**Impact**: High for guest experience agent

---

### 4. Add Cargo Priority Levels

**Current**: All cargo treated equally  
**Improvement**: Add priority classification

```sql
ALTER TABLE cargo_shipments ADD COLUMN priority_level ENUM('Standard', 'Priority', 'Critical', 'Emergency');
ALTER TABLE cargo_shipments ADD COLUMN latest_delivery_time DATETIME;
```

**Benefits**:

- Better cargo offload decisions
- Revenue optimization
- SLA tracking
- Customer satisfaction

**Effort**: 1 hour  
**Impact**: High for cargo agent

---

### 5. Add Crew Rest Tracking

**Current**: Only duty times tracked  
**Improvement**: Add rest period tracking

```sql
ALTER TABLE crew_roster ADD COLUMN rest_start DATETIME;
ALTER TABLE crew_roster ADD COLUMN rest_end DATETIME;
ALTER TABLE crew_roster ADD COLUMN rest_location VARCHAR(3);
```

**Benefits**:

- FTL compliance validation
- Crew fatigue risk assessment
- Better crew assignment
- Regulatory compliance

**Effort**: 2 hours  
**Impact**: High for crew compliance agent

---

## 🎯 P1: High Value Enhancements

### 6. Add Maintenance Events Table

**Purpose**: Track MEL items and AOG status

```sql
CREATE TABLE maintenance_events (
    event_id INT PRIMARY KEY AUTO_INCREMENT,
    aircraft_registration VARCHAR(10) NOT NULL,
    event_type ENUM('MEL', 'AOG', 'Scheduled', 'Unscheduled'),
    mel_category ENUM('A', 'B', 'C', 'D'),
    description TEXT,
    reported_at DATETIME NOT NULL,
    resolved_at DATETIME,
    affects_dispatch BOOLEAN DEFAULT FALSE,
    estimated_repair_hours INT,
    status ENUM('Open', 'InProgress', 'Resolved', 'Deferred')
);
```

**Benefits**:

- Realistic maintenance disruptions
- MEL compliance tracking
- AOG impact assessment
- Maintenance agent decision support

**Effort**: 4 hours  
**Impact**: Critical for maintenance agent

---

### 7. Add NOTAM Table

**Purpose**: Track NOTAMs affecting operations

```sql
CREATE TABLE notams (
    notam_id INT PRIMARY KEY AUTO_INCREMENT,
    notam_number VARCHAR(20) UNIQUE,
    airport_id INT,
    notam_type ENUM('Runway', 'Taxiway', 'Apron', 'Navaid', 'Airspace', 'Other'),
    effective_from DATETIME NOT NULL,
    effective_to DATETIME,
    description TEXT,
    affects_operations BOOLEAN DEFAULT TRUE,
    severity ENUM('Low', 'Medium', 'High', 'Critical'),
    FOREIGN KEY (airport_id) REFERENCES airports(airport_id)
);
```

**Benefits**:

- Regulatory compliance
- Operational constraints tracking
- Route planning
- Regulatory agent decision support

**Effort**: 3 hours  
**Impact**: High for regulatory agent

---

### 8. Add Airport Curfews Table

**Purpose**: Track airport operating restrictions

```sql
CREATE TABLE airport_curfews (
    curfew_id INT PRIMARY KEY AUTO_INCREMENT,
    airport_id INT NOT NULL,
    day_of_week INT, -- 0=Sunday, 6=Saturday
    curfew_start TIME NOT NULL,
    curfew_end TIME NOT NULL,
    restriction_type ENUM('NoMovements', 'NoArrivals', 'NoDepartures', 'Restricted'),
    exemptions TEXT,
    FOREIGN KEY (airport_id) REFERENCES airports(airport_id)
);
```

**Benefits**:

- Realistic scheduling constraints
- Regulatory compliance
- Better recovery options
- Regulatory agent decision support

**Effort**: 2 hours  
**Impact**: High for regulatory agent

---

### 9. Add Passenger Notifications Table

**Purpose**: Track communication with passengers

```sql
CREATE TABLE passenger_notifications (
    notification_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    notification_type ENUM('SMS', 'Email', 'Push', 'Call'),
    notification_category ENUM('Delay', 'Cancellation', 'GateChange', 'Rebooking', 'Compensation'),
    sent_at DATETIME NOT NULL,
    message_content TEXT,
    delivery_status ENUM('Sent', 'Delivered', 'Failed', 'Bounced'),
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);
```

**Benefits**:

- Communication tracking
- Passenger satisfaction
- Audit trail
- Guest experience agent metrics

**Effort**: 3 hours  
**Impact**: High for guest experience agent

---

### 10. Add Revenue Data Table

**Purpose**: Track ticket prices and revenue

```sql
CREATE TABLE booking_revenue (
    revenue_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL UNIQUE,
    base_fare_usd DECIMAL(10,2),
    taxes_usd DECIMAL(10,2),
    fees_usd DECIMAL(10,2),
    total_paid_usd DECIMAL(10,2),
    payment_method VARCHAR(50),
    booking_channel ENUM('Website', 'Mobile', 'CallCenter', 'GDS', 'Partner'),
    commission_usd DECIMAL(10,2),
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);
```

**Benefits**:

- Revenue impact analysis
- Financial optimization
- Compensation calculations
- Finance agent decision support

**Effort**: 3 hours  
**Impact**: Critical for finance agent

---

## 🏗️ P2: Strategic Enhancements

### 11. Add Disruption Events Table

**Purpose**: Historical disruption tracking

```sql
CREATE TABLE disruption_events (
    disruption_id INT PRIMARY KEY AUTO_INCREMENT,
    flight_id INT NOT NULL,
    disruption_type ENUM('Delay', 'Cancellation', 'Diversion', 'AircraftSwap', 'CrewIssue'),
    root_cause VARCHAR(100),
    detected_at DATETIME NOT NULL,
    resolved_at DATETIME,
    duration_minutes INT,
    passengers_affected INT,
    cargo_affected_kg DECIMAL(10,2),
    estimated_cost_usd DECIMAL(12,2),
    recovery_scenario_id INT,
    human_decision TEXT,
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
);
```

**Benefits**:

- Historical analysis
- ML training data
- Pattern recognition
- System improvement

**Effort**: 6 hours  
**Impact**: Critical for learning phase

---

### 12. Add Recovery Scenarios Table

**Purpose**: Store generated recovery scenarios

```sql
CREATE TABLE recovery_scenarios (
    scenario_id INT PRIMARY KEY AUTO_INCREMENT,
    disruption_id INT NOT NULL,
    scenario_rank INT,
    scenario_type VARCHAR(50),
    description TEXT,
    estimated_cost_usd DECIMAL(12,2),
    estimated_delay_minutes INT,
    passengers_impacted INT,
    cargo_impacted_kg DECIMAL(10,2),
    safety_score DECIMAL(3,2),
    business_score DECIMAL(3,2),
    overall_score DECIMAL(3,2),
    was_selected BOOLEAN DEFAULT FALSE,
    selected_by VARCHAR(100),
    selection_reason TEXT,
    FOREIGN KEY (disruption_id) REFERENCES disruption_events(disruption_id)
);
```

**Benefits**:

- Scenario comparison
- Human decision tracking
- ML training data
- Arbitrator improvement

**Effort**: 5 hours  
**Impact**: Critical for arbitrator

---

### 13. Add Weather Conditions Table

**Purpose**: Track weather affecting operations

```sql
CREATE TABLE weather_conditions (
    weather_id INT PRIMARY KEY AUTO_INCREMENT,
    airport_id INT NOT NULL,
    observation_time DATETIME NOT NULL,
    temperature_c DECIMAL(4,1),
    wind_speed_kts INT,
    wind_direction INT,
    visibility_m INT,
    ceiling_ft INT,
    weather_code VARCHAR(20), -- METAR codes
    affects_operations BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (airport_id) REFERENCES airports(airport_id)
);
```

**Benefits**:

- Weather-related disruptions
- Realistic scenarios
- Predictive analytics
- Regulatory agent input

**Effort**: 4 hours  
**Impact**: Medium for realism

---

### 14. Add Slot Restrictions Table

**Purpose**: Track ATC slot allocations

```sql
CREATE TABLE slot_restrictions (
    slot_id INT PRIMARY KEY AUTO_INCREMENT,
    airport_id INT NOT NULL,
    slot_time DATETIME NOT NULL,
    slot_type ENUM('Arrival', 'Departure'),
    allocated_to_flight_id INT,
    slot_status ENUM('Available', 'Allocated', 'Used', 'Expired'),
    priority_level INT,
    FOREIGN KEY (airport_id) REFERENCES airports(airport_id),
    FOREIGN KEY (allocated_to_flight_id) REFERENCES flights(flight_id)
);
```

**Benefits**:

- Realistic slot constraints
- Regulatory compliance
- Better recovery options
- Network agent optimization

**Effort**: 5 hours  
**Impact**: High for network agent

---

### 15. Add Compensation Claims Table

**Purpose**: Track EU261 and other compensation

```sql
CREATE TABLE compensation_claims (
    claim_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    disruption_id INT,
    claim_type ENUM('EU261', 'Voluntary', 'Goodwill', 'Voucher'),
    claim_amount_usd DECIMAL(10,2),
    claim_status ENUM('Pending', 'Approved', 'Rejected', 'Paid'),
    filed_at DATETIME,
    processed_at DATETIME,
    reason TEXT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    FOREIGN KEY (disruption_id) REFERENCES disruption_events(disruption_id)
);
```

**Benefits**:

- Financial impact tracking
- Regulatory compliance
- Customer satisfaction
- Finance agent metrics

**Effort**: 4 hours  
**Impact**: High for finance agent

---

## 🔧 P3: Nice to Have

### 16. Add Family/Group Bookings

**Purpose**: Link related passengers

```sql
CREATE TABLE booking_groups (
    group_id INT PRIMARY KEY AUTO_INCREMENT,
    group_pnr VARCHAR(6) UNIQUE,
    group_type ENUM('Family', 'Tour', 'Corporate', 'Sports'),
    group_size INT,
    lead_passenger_id INT,
    FOREIGN KEY (lead_passenger_id) REFERENCES passengers(passenger_id)
);

ALTER TABLE bookings ADD COLUMN group_id INT;
```

**Benefits**:

- Keep families together
- Better rebooking
- Customer satisfaction
- Guest experience agent

**Effort**: 3 hours  
**Impact**: Medium

---

### 17. Add Special Meal Requests

**Purpose**: Track meal preferences

```sql
CREATE TABLE meal_requests (
    request_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    meal_code VARCHAR(10), -- VGML, KSML, GFML, etc.
    meal_description VARCHAR(100),
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);
```

**Benefits**:

- Operational realism
- Catering coordination
- Customer satisfaction

**Effort**: 2 hours  
**Impact**: Low

---

### 18. Add Loyalty Transactions

**Purpose**: Track miles earned/redeemed

```sql
CREATE TABLE loyalty_transactions (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    passenger_id INT NOT NULL,
    booking_id INT,
    transaction_type ENUM('Earn', 'Redeem', 'Bonus', 'Expire'),
    miles_amount INT,
    transaction_date DATETIME,
    description TEXT,
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);
```

**Benefits**:

- Loyalty program integration
- Customer value tracking
- Personalization

**Effort**: 3 hours  
**Impact**: Low

---

### 19. Add Ancillary Services

**Purpose**: Track extra purchases

```sql
CREATE TABLE ancillary_services (
    service_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    service_type ENUM('ExtraBaggage', 'SeatSelection', 'Meal', 'Lounge', 'FastTrack', 'WiFi'),
    service_description VARCHAR(200),
    price_usd DECIMAL(10,2),
    purchased_at DATETIME,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);
```

**Benefits**:

- Revenue tracking
- Customer preferences
- Upsell opportunities

**Effort**: 3 hours  
**Impact**: Low

---

### 20. Add Hotel Accommodations

**Purpose**: Track overnight stays

```sql
CREATE TABLE hotel_accommodations (
    accommodation_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    disruption_id INT,
    hotel_name VARCHAR(200),
    check_in_date DATE,
    check_out_date DATE,
    room_type VARCHAR(50),
    cost_usd DECIMAL(10,2),
    booking_reference VARCHAR(50),
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    FOREIGN KEY (disruption_id) REFERENCES disruption_events(disruption_id)
);
```

**Benefits**:

- Disruption cost tracking
- Customer care
- Regulatory compliance

**Effort**: 3 hours  
**Impact**: Medium

---

## 🔬 P4: Advanced Features

### 21. Add Predictive Delay Model

**Purpose**: ML-based delay prediction

```sql
CREATE TABLE delay_predictions (
    prediction_id INT PRIMARY KEY AUTO_INCREMENT,
    flight_id INT NOT NULL,
    predicted_at DATETIME NOT NULL,
    predicted_delay_minutes INT,
    confidence_score DECIMAL(3,2),
    contributing_factors JSON,
    actual_delay_minutes INT,
    prediction_accuracy DECIMAL(3,2),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
);
```

**Benefits**:

- Proactive disruption management
- Early passenger notification
- Better resource allocation

**Effort**: 20+ hours (ML model)  
**Impact**: High (future)

---

### 22. Add Crew Fatigue Risk Assessment

**Purpose**: Predict crew fatigue

```sql
CREATE TABLE crew_fatigue_assessments (
    assessment_id INT PRIMARY KEY AUTO_INCREMENT,
    crew_id INT NOT NULL,
    assessment_date DATE,
    duty_hours_7day DECIMAL(5,2),
    duty_hours_28day DECIMAL(6,2),
    consecutive_duty_days INT,
    time_zone_crossings INT,
    fatigue_risk_score DECIMAL(3,2),
    risk_level ENUM('Low', 'Medium', 'High', 'Critical'),
    FOREIGN KEY (crew_id) REFERENCES crew_members(crew_id)
);
```

**Benefits**:

- Safety enhancement
- Crew wellness
- Regulatory compliance

**Effort**: 15+ hours  
**Impact**: High (safety)

---

### 23. Add Passenger No-Show Prediction

**Purpose**: Predict no-shows for overbooking

```sql
CREATE TABLE noshow_predictions (
    prediction_id INT PRIMARY KEY AUTO_INCREMENT,
    booking_id INT NOT NULL,
    predicted_at DATETIME NOT NULL,
    noshow_probability DECIMAL(3,2),
    contributing_factors JSON,
    actual_noshow BOOLEAN,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);
```

**Benefits**:

- Revenue optimization
- Better capacity planning
- Reduced denied boarding

**Effort**: 20+ hours (ML model)  
**Impact**: Medium (revenue)

---

### 24. Add Cargo Demand Forecasting

**Purpose**: Predict cargo demand

```sql
CREATE TABLE cargo_demand_forecasts (
    forecast_id INT PRIMARY KEY AUTO_INCREMENT,
    route_id INT,
    forecast_date DATE,
    predicted_weight_kg DECIMAL(10,2),
    predicted_revenue_usd DECIMAL(12,2),
    confidence_interval_low DECIMAL(10,2),
    confidence_interval_high DECIMAL(10,2),
    actual_weight_kg DECIMAL(10,2),
    forecast_accuracy DECIMAL(3,2)
);
```

**Benefits**:

- Capacity planning
- Revenue optimization
- Fleet allocation

**Effort**: 20+ hours (ML model)  
**Impact**: Medium (revenue)

---

### 25. Add Real-Time Aircraft Position

**Purpose**: Track aircraft location

```sql
CREATE TABLE aircraft_positions (
    position_id INT PRIMARY KEY AUTO_INCREMENT,
    aircraft_registration VARCHAR(10) NOT NULL,
    flight_id INT,
    timestamp DATETIME NOT NULL,
    latitude DECIMAL(10,6),
    longitude DECIMAL(10,6),
    altitude_ft INT,
    ground_speed_kts INT,
    heading INT,
    phase_of_flight ENUM('Ground', 'Taxi', 'Takeoff', 'Climb', 'Cruise', 'Descent', 'Approach', 'Landing'),
    FOREIGN KEY (flight_id) REFERENCES flights(flight_id)
);
```

**Benefits**:

- Real-time tracking
- ETA calculations
- Operational awareness

**Effort**: 10+ hours (integration)  
**Impact**: High (operations)

---

## 📊 Data Quality Improvements

### 26. Add Audit Triggers

**Purpose**: Track all data changes

```sql
CREATE TABLE audit_log (
    audit_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(50),
    record_id INT,
    action ENUM('INSERT', 'UPDATE', 'DELETE'),
    old_values JSON,
    new_values JSON,
    changed_by VARCHAR(100),
    changed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create triggers for each table
CREATE TRIGGER flights_audit_insert AFTER INSERT ON flights...
CREATE TRIGGER flights_audit_update AFTER UPDATE ON flights...
CREATE TRIGGER flights_audit_delete AFTER DELETE ON flights...
```

**Benefits**:

- Complete audit trail
- Regulatory compliance
- Debugging
- Security

**Effort**: 8 hours  
**Impact**: High (compliance)

---

### 27. Add Data Validation Rules

**Purpose**: Enforce business rules

```sql
CREATE TABLE validation_rules (
    rule_id INT PRIMARY KEY AUTO_INCREMENT,
    table_name VARCHAR(50),
    column_name VARCHAR(50),
    rule_type ENUM('Range', 'Format', 'Lookup', 'Custom'),
    rule_definition JSON,
    error_message TEXT,
    is_active BOOLEAN DEFAULT TRUE
);
```

**Benefits**:

- Data quality
- Consistency
- Error prevention

**Effort**: 6 hours  
**Impact**: Medium

---

### 28. Add Data Masking for PII

**Purpose**: Protect sensitive data

```sql
-- Create masked views
CREATE VIEW passengers_masked AS
SELECT
    passenger_id,
    first_name,
    CONCAT(LEFT(last_name, 1), '***') as last_name,
    '***' as passport_number,
    CONCAT('***@', SUBSTRING_INDEX(email, '@', -1)) as email,
    '***' as phone
FROM passengers;
```

**Benefits**:

- Privacy protection
- GDPR compliance
- Security

**Effort**: 4 hours  
**Impact**: High (compliance)

---

## 🚀 Performance Optimizations

### 29. Add Materialized Views

**Purpose**: Pre-compute expensive queries

```sql
CREATE MATERIALIZED VIEW flight_summary AS
SELECT
    f.flight_id,
    f.flight_number,
    COUNT(DISTINCT b.booking_id) as passenger_count,
    SUM(CASE WHEN p.is_vip THEN 1 ELSE 0 END) as vip_count,
    COUNT(DISTINCT cs.shipment_id) as cargo_count,
    SUM(cfa.weight_on_flight_kg) as cargo_weight
FROM flights f
LEFT JOIN bookings b ON f.flight_id = b.flight_id
LEFT JOIN passengers p ON b.passenger_id = p.passenger_id
LEFT JOIN cargo_flight_assignments cfa ON f.flight_id = cfa.flight_id
LEFT JOIN cargo_shipments cs ON cfa.shipment_id = cs.shipment_id
GROUP BY f.flight_id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW flight_summary;
```

**Benefits**:

- Faster queries
- Better performance
- Reduced load

**Effort**: 4 hours  
**Impact**: High (performance)

---

### 30. Add Table Partitioning

**Purpose**: Partition large tables by date

```sql
-- Partition flights by month
ALTER TABLE flights PARTITION BY RANGE (YEAR(scheduled_departure) * 100 + MONTH(scheduled_departure)) (
    PARTITION p202601 VALUES LESS THAN (202602),
    PARTITION p202602 VALUES LESS THAN (202603),
    PARTITION p202603 VALUES LESS THAN (202604),
    ...
);
```

**Benefits**:

- Faster queries
- Easier archival
- Better maintenance

**Effort**: 6 hours  
**Impact**: High (scalability)

---

## 📝 Implementation Roadmap

### Phase 1: Foundation (Week 1)

- P0 items #1-5 (Quick wins)
- Basic audit logging
- Data validation

### Phase 2: Core Features (Week 2-3)

- P1 items #6-10 (High value)
- Maintenance events
- NOTAMs and curfews
- Revenue tracking

### Phase 3: Advanced Features (Week 4-6)

- P2 items #11-15 (Strategic)
- Disruption tracking
- Recovery scenarios
- Weather and slots

### Phase 4: Optimization (Week 7-8)

- Performance tuning
- Materialized views
- Partitioning
- Indexing

### Phase 5: ML & Analytics (Week 9-12)

- P4 items (Advanced)
- Predictive models
- Real-time tracking
- Analytics dashboards

---

## 🎯 Success Metrics

### Data Quality

- 100% referential integrity
- < 0.1% validation errors
- Complete audit trail

### Performance

- < 100ms for single flight queries
- < 500ms for complex joins
- Support 1000+ concurrent users

### Business Value

- 30% faster disruption resolution
- 25% cost reduction
- 15 NPS point improvement

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-30  
**Total Ideas**: 30 improvements across 5 priority levels
