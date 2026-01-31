# Requirements Document

## Introduction

The SkyMarshal DynamoDB database contains data inconsistencies that prevent Global Secondary Indexes (GSIs) from functioning correctly. This feature addresses data type mismatches, missing GSI attributes, key field inconsistencies, and incomplete data across multiple tables. The solution will audit, correct, and validate all database content to ensure proper GSI functionality and data integrity.

## Glossary

- **GSI**: Global Secondary Index - DynamoDB feature enabling queries on non-primary-key attributes
- **Data_Auditor**: Component that scans CSV files and identifies data quality issues
- **Data_Transformer**: Component that corrects data type inconsistencies and adds missing attributes
- **Upload_Manager**: Component that handles batch uploads to DynamoDB with proper data formatting
- **Validation_Engine**: Component that verifies data integrity and GSI functionality after upload
- **CSV_Source**: Original data files in database/output/ directory
- **DynamoDB_Table**: Target table in AWS DynamoDB service
- **Type_Mismatch**: Condition where a field's data type doesn't match GSI requirements
- **Missing_Attribute**: Condition where a required GSI attribute is absent from source data

## Requirements

### Requirement 1: Data Audit and Issue Detection

**User Story:** As a database administrator, I want to automatically identify all data quality issues in CSV files, so that I can understand the scope of corrections needed.

#### Acceptance Criteria

1. WHEN the Data_Auditor scans a CSV file, THE System SHALL identify all fields with type mismatches against GSI requirements
2. WHEN the Data_Auditor scans a CSV file, THE System SHALL detect all missing GSI attributes
3. WHEN the Data_Auditor scans a CSV file, THE System SHALL identify key field name mismatches between CSV columns and upload script references
4. WHEN the Data_Auditor completes scanning, THE System SHALL generate a comprehensive report listing all issues by table and severity
5. THE Data_Auditor SHALL validate that all required GSI attributes exist in source data with correct data types

### Requirement 2: CSV Data Correction

**User Story:** As a database administrator, I want to automatically correct data quality issues in CSV files, so that all data meets GSI requirements before upload.

#### Acceptance Criteria

1. WHEN the Data_Transformer processes cargo_flight_assignments.csv, THE System SHALL add a loading_priority column derived from sequence_number
2. WHEN the Data_Transformer processes crew_roster_enriched.csv, THE System SHALL add a position column mapped from position_id values
3. WHEN the Data_Transformer processes baggage.csv, THE System SHALL add a status column copied from baggage_status
4. WHEN the Data_Transformer completes corrections, THE System SHALL preserve all existing data and relationships
5. THE Data_Transformer SHALL validate that all corrected files have proper data types for GSI attributes

### Requirement 3: Upload Script Correction

**User Story:** As a database administrator, I want upload scripts to use correct key schemas and file paths, so that data uploads succeed without errors.

#### Acceptance Criteria

1. WHEN the Upload_Manager processes MaintenanceWorkOrders, THE System SHALL use workorder_id as the partition key (not work_order_id)
2. WHEN the Upload_Manager processes MaintenanceStaff, THE System SHALL read from maintenance_staff.csv (not maintenance_roster.csv)
3. WHEN the Upload_Manager validates configurations, THE System SHALL verify all key schemas match actual table definitions
4. WHEN the Upload_Manager completes validation, THE System SHALL report any remaining mismatches
5. THE Upload_Manager SHALL ensure all table configurations reference existing CSV files

### Requirement 4: Data Upload and Table Management

**User Story:** As a database administrator, I want to upload corrected data to DynamoDB with proper table cleanup, so that the database contains only valid, current data.

#### Acceptance Criteria

1. WHEN the Upload_Manager initiates upload, THE System SHALL delete all existing tables before creating new ones
2. WHEN the Upload_Manager creates tables, THE System SHALL use correct key schemas for all 16 tables
3. WHEN the Upload_Manager uploads data, THE System SHALL process all CSV files concurrently for optimal performance
4. WHEN the Upload_Manager completes upload, THE System SHALL report total items uploaded and any errors encountered
5. THE Upload_Manager SHALL achieve 100% upload success rate with zero data loss

### Requirement 5: Global Secondary Index Creation

**User Story:** As a database administrator, I want all required GSIs created and active, so that agent queries can use efficient indexed lookups.

#### Acceptance Criteria

1. WHEN the GSI_Creator processes flights table, THE System SHALL create flight-number-date-index and aircraft-registration-index
2. WHEN the GSI_Creator processes bookings table, THE System SHALL create flight-id-index
3. WHEN the GSI_Creator processes CrewRoster table, THE System SHALL create flight-position-index
4. WHEN the GSI_Creator processes MaintenanceWorkOrders table, THE System SHALL create aircraft-registration-index
5. WHEN the GSI_Creator processes CargoFlightAssignments table, THE System SHALL create flight-loading-index and shipment-index
6. WHEN the GSI_Creator processes Baggage table, THE System SHALL create booking-index
7. WHEN the GSI_Creator completes creation, THE System SHALL verify all 8 GSIs are in ACTIVE status
8. THE GSI_Creator SHALL handle AWS limits on concurrent GSI creation per table

### Requirement 6: Data Validation and Verification

**User Story:** As a database administrator, I want comprehensive validation of uploaded data and GSIs, so that I can confirm the database is production-ready.

#### Acceptance Criteria

1. WHEN the Validation_Engine checks tables, THE System SHALL verify all 16 tables exist with correct item counts
2. WHEN the Validation_Engine checks GSIs, THE System SHALL verify all 8 GSIs are ACTIVE and queryable
3. WHEN the Validation_Engine checks data integrity, THE System SHALL verify foreign key relationships are intact
4. WHEN the Validation_Engine tests queries, THE System SHALL confirm GSIs are used (no table scans)
5. WHEN the Validation_Engine completes validation, THE System SHALL generate a comprehensive status report
6. THE Validation_Engine SHALL identify any data quality issues or missing relationships

### Requirement 7: Documentation and Reporting

**User Story:** As a database administrator, I want detailed documentation of all changes and validation results, so that I can track what was fixed and verify system readiness.

#### Acceptance Criteria

1. WHEN any component completes its work, THE System SHALL generate a detailed report of actions taken
2. WHEN the entire process completes, THE System SHALL produce a final status report with all metrics
3. THE System SHALL document all CSV file modifications with before/after schemas
4. THE System SHALL document all upload script changes with specific line numbers
5. THE System SHALL provide performance expectations for GSI-enabled queries
6. THE System SHALL include commands for verifying and testing the database

## Non-Functional Requirements

### Performance

- CSV data corrections SHALL complete within 5 minutes
- Data upload SHALL complete within 10 minutes for 26,000+ items
- GSI creation SHALL complete within 20 minutes including backfill
- Total end-to-end process SHALL complete within 30 minutes

### Reliability

- Upload process SHALL achieve 100% success rate with zero data loss
- All GSIs SHALL reach ACTIVE status without errors
- Validation SHALL detect any data integrity issues with 100% accuracy

### Maintainability

- All scripts SHALL be reusable for future data refreshes
- All changes SHALL be documented with clear explanations
- All reports SHALL be human-readable and actionable

### Scalability

- Upload process SHALL handle concurrent table creation efficiently
- GSI creation SHALL respect AWS service limits
- Validation SHALL scale to additional tables and GSIs as needed

## Constraints

- Must work with existing AWS DynamoDB infrastructure
- Must preserve all existing data relationships
- Must not modify original CSV generation logic
- Must complete within AWS service limits for GSI creation
- Must maintain backward compatibility with agent query patterns

## Dependencies

- AWS CLI configured with proper credentials
- Python 3.11+ with boto3 library
- Existing CSV files in database/output/ directory
- DynamoDB tables in us-east-1 region
- IAM permissions for table and GSI management
