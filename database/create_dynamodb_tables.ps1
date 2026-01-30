# Create DynamoDB Tables and Upload CSV Data
# This script creates DynamoDB tables and uploads all CSV files

param(
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1"
)

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "DynamoDB Table Creation and Data Upload" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check if AWS CLI is available
try {
    $awsVersion = aws --version 2>&1
    Write-Host "✓ AWS CLI found" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS CLI not found" -ForegroundColor Red
    Write-Host "  Please restart your terminal and run setup_aws.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Check AWS credentials
try {
    $identity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
    Write-Host "✓ AWS Account: $($identity.Account)" -ForegroundColor Green
    Write-Host "✓ User: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS credentials not configured" -ForegroundColor Red
    Write-Host "  Please run: aws configure" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Region: $Region" -ForegroundColor Green
Write-Host ""

# Table definitions
$tables = @(
    @{
        Name = "Passengers"
        File = "output/passengers_enriched_final.csv"
        PrimaryKey = "passenger_id"
        Description = "Passenger records with enriched data"
    },
    @{
        Name = "Flights"
        File = "output/flights_enriched_mel.csv"
        PrimaryKey = "flight_id"
        Description = "Flight records with MEL data"
    },
    @{
        Name = "AircraftAvailability"
        File = "output/aircraft_availability_enriched_mel.csv"
        PrimaryKey = "aircraft_registration"
        SortKey = "availability_start"
        Description = "Aircraft availability with MEL status"
    },
    @{
        Name = "MaintenanceWorkOrders"
        File = "output/aircraft_maintenance_workorders.csv"
        PrimaryKey = "workorder_id"
        Description = "Aircraft maintenance work orders"
    },
    @{
        Name = "Weather"
        File = "output/weather.csv"
        PrimaryKey = "airport_code"
        SortKey = "forecast_time_zulu"
        Description = "Weather forecasts for airports"
    },
    @{
        Name = "DisruptedPassengers"
        File = "output/disrupted_passengers_scenario.csv"
        PrimaryKey = "passenger_id"
        Description = "Disruption scenario passenger data"
    },
    @{
        Name = "AircraftSwapOptions"
        File = "output/aircraft_swap_options.csv"
        PrimaryKey = "aircraft_registration"
        Description = "Aircraft swap options"
    },
    @{
        Name = "InboundFlightImpact"
        File = "output/inbound_flight_impact.csv"
        PrimaryKey = "scenario"
        Description = "Inbound flight impact analysis"
    },
    @{
        Name = "Bookings"
        File = "output/bookings.csv"
        PrimaryKey = "booking_id"
        Description = "Flight bookings"
    },
    @{
        Name = "Baggage"
        File = "output/baggage.csv"
        PrimaryKey = "baggage_tag"
        Description = "Baggage tracking"
    },
    @{
        Name = "CrewMembers"
        File = "output/crew_members.csv"
        PrimaryKey = "crew_id"
        Description = "Crew member information"
    },
    @{
        Name = "CrewRoster"
        File = "output/crew_roster.csv"
        PrimaryKey = "roster_id"
        Description = "Crew roster assignments"
    },
    @{
        Name = "CargoShipments"
        File = "output/cargo_shipments.csv"
        PrimaryKey = "shipment_id"
        Description = "Cargo shipment tracking"
    },
    @{
        Name = "CargoFlightAssignments"
        File = "output/cargo_flight_assignments.csv"
        PrimaryKey = "assignment_id"
        Description = "Cargo to flight assignments"
    },
    @{
        Name = "MaintenanceStaff"
        File = "output/maintenance_staff.csv"
        PrimaryKey = "staff_id"
        Description = "Maintenance staff information"
    },
    @{
        Name = "MaintenanceRoster"
        File = "output/maintenance_roster.csv"
        PrimaryKey = "roster_id"
        Description = "Maintenance staff roster"
    }
)

Write-Host "Note: For large datasets, use the Python script (create_dynamodb_tables.py)" -ForegroundColor Yellow
Write-Host "      This PowerShell script creates tables only." -ForegroundColor Yellow
Write-Host ""

$response = Read-Host "Create $($tables.Count) DynamoDB tables? (y/n)"

if ($response -ne 'y' -and $response -ne 'Y') {
    Write-Host "Operation cancelled" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Creating tables..." -ForegroundColor Yellow
Write-Host ""

$createdCount = 0
$skippedCount = 0
$failedCount = 0

foreach ($table in $tables) {
    Write-Host "[$($createdCount + $skippedCount + $failedCount + 1)/$($tables.Count)] $($table.Name)" -ForegroundColor Cyan
    Write-Host "  Description: $($table.Description)" -ForegroundColor White
    Write-Host "  Primary Key: $($table.PrimaryKey)" -ForegroundColor White
    
    if ($table.SortKey) {
        Write-Host "  Sort Key: $($table.SortKey)" -ForegroundColor White
    }
    
    # Check if table exists
    try {
        $existingTable = aws dynamodb describe-table --table-name $table.Name --region $Region 2>&1 | ConvertFrom-Json
        if ($existingTable.Table) {
            Write-Host "  ⚠ Table already exists, skipping" -ForegroundColor Yellow
            $skippedCount++
            Write-Host ""
            continue
        }
    } catch {
        # Table doesn't exist, continue with creation
    }
    
    # Build attribute definitions
    $attributeDefinitions = @(
        @{
            AttributeName = $table.PrimaryKey
            AttributeType = "S"
        }
    )
    
    $keySchema = @(
        @{
            AttributeName = $table.PrimaryKey
            KeyType = "HASH"
        }
    )
    
    if ($table.SortKey) {
        $attributeDefinitions += @{
            AttributeName = $table.SortKey
            AttributeType = "S"
        }
        $keySchema += @{
            AttributeName = $table.SortKey
            KeyType = "RANGE"
        }
    }
    
    # Convert to JSON
    $attributeDefJson = $attributeDefinitions | ConvertTo-Json -Compress
    $keySchemaJson = $keySchema | ConvertTo-Json -Compress
    
    # Create table
    try {
        Write-Host "  Creating table..." -NoNewline -ForegroundColor White
        
        $result = aws dynamodb create-table `
            --table-name $table.Name `
            --attribute-definitions $attributeDefJson `
            --key-schema $keySchemaJson `
            --billing-mode PAY_PER_REQUEST `
            --region $Region 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✓ Created" -ForegroundColor Green
            $createdCount++
        } else {
            Write-Host " ✗ Failed" -ForegroundColor Red
            Write-Host "  Error: $result" -ForegroundColor Red
            $failedCount++
        }
    } catch {
        Write-Host " ✗ Failed" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        $failedCount++
    }
    
    Write-Host ""
}

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Tables Created: $createdCount" -ForegroundColor Green
Write-Host "Tables Skipped (already exist): $skippedCount" -ForegroundColor Yellow
Write-Host "Tables Failed: $failedCount" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "White" })
Write-Host ""

if ($createdCount -gt 0 -or $skippedCount -gt 0) {
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Upload data using Python script:" -ForegroundColor Yellow
    Write-Host "   py create_dynamodb_tables.py" -ForegroundColor White
    Write-Host ""
    Write-Host "2. View tables in AWS Console:" -ForegroundColor Yellow
    Write-Host "   https://console.aws.amazon.com/dynamodbv2/home?region=$Region#tables" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Query a table:" -ForegroundColor Yellow
    Write-Host "   aws dynamodb scan --table-name Passengers --limit 10 --region $Region" -ForegroundColor White
    Write-Host ""
}

Write-Host "=" * 80 -ForegroundColor Cyan
