# Upload Airline Data to AWS S3
# This script uploads all your generated data files to an S3 bucket

param(
    [Parameter(Mandatory=$false)]
    [string]$BucketName = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1"
)

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Upload Airline Data to AWS S3" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check if AWS CLI is available
try {
    $awsVersion = aws --version 2>&1
    Write-Host "✓ AWS CLI found: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ AWS CLI not found" -ForegroundColor Red
    Write-Host "  Please restart your terminal and run setup_aws.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Check if AWS is configured
try {
    $identity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
    Write-Host "✓ AWS credentials configured" -ForegroundColor Green
    Write-Host "  Account: $($identity.Account)" -ForegroundColor White
    Write-Host "  User: $($identity.Arn)" -ForegroundColor White
} catch {
    Write-Host "✗ AWS credentials not configured" -ForegroundColor Red
    Write-Host "  Please run: aws configure" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Get bucket name if not provided
if ([string]::IsNullOrEmpty($BucketName)) {
    Write-Host "Enter S3 bucket name (or press Enter to create a new one):" -ForegroundColor Yellow
    $BucketName = Read-Host "Bucket name"
    
    if ([string]::IsNullOrEmpty($BucketName)) {
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $BucketName = "airline-data-$timestamp"
        Write-Host "Using auto-generated bucket name: $BucketName" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "Bucket: $BucketName" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Cyan
Write-Host ""

# Check if bucket exists
Write-Host "Checking if bucket exists..." -ForegroundColor Yellow
$bucketExists = $false
try {
    aws s3 ls "s3://$BucketName" 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $bucketExists = $true
        Write-Host "✓ Bucket exists" -ForegroundColor Green
    }
} catch {
    $bucketExists = $false
}

# Create bucket if it doesn't exist
if (-not $bucketExists) {
    Write-Host "Creating bucket..." -ForegroundColor Yellow
    try {
        if ($Region -eq "us-east-1") {
            aws s3 mb "s3://$BucketName" 2>&1
        } else {
            aws s3 mb "s3://$BucketName" --region $Region 2>&1
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Bucket created successfully" -ForegroundColor Green
        } else {
            Write-Host "✗ Failed to create bucket" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "✗ Error creating bucket: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# List files to upload
Write-Host "Files to upload:" -ForegroundColor Yellow
$files = @(
    "output/passengers_enriched_final.csv",
    "output/flights_enriched_mel.csv",
    "output/aircraft_availability_enriched_mel.csv",
    "output/weather.csv",
    "output/disrupted_passengers_scenario.csv",
    "output/aircraft_swap_options.csv",
    "output/inbound_flight_impact.csv"
)

$existingFiles = @()
foreach ($file in $files) {
    if (Test-Path $file) {
        $size = (Get-Item $file).Length / 1KB
        Write-Host "  ✓ $file ($([math]::Round($size, 2)) KB)" -ForegroundColor White
        $existingFiles += $file
    } else {
        Write-Host "  ✗ $file (not found)" -ForegroundColor Gray
    }
}

Write-Host ""

if ($existingFiles.Count -eq 0) {
    Write-Host "✗ No files found to upload" -ForegroundColor Red
    exit 1
}

Write-Host "Found $($existingFiles.Count) files to upload" -ForegroundColor Cyan
Write-Host ""

$response = Read-Host "Proceed with upload? (y/n)"

if ($response -ne 'y' -and $response -ne 'Y') {
    Write-Host "Upload cancelled" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Uploading files..." -ForegroundColor Yellow
Write-Host ""

$uploadedCount = 0
$failedCount = 0

foreach ($file in $existingFiles) {
    $fileName = Split-Path $file -Leaf
    $s3Key = "data/$fileName"
    
    Write-Host "Uploading $fileName..." -ForegroundColor Cyan
    try {
        aws s3 cp $file "s3://$BucketName/$s3Key" 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Uploaded successfully" -ForegroundColor Green
            $uploadedCount++
        } else {
            Write-Host "  ✗ Upload failed" -ForegroundColor Red
            $failedCount++
        }
    } catch {
        Write-Host "  ✗ Error: $_" -ForegroundColor Red
        $failedCount++
    }
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Upload Summary" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Bucket: s3://$BucketName" -ForegroundColor White
Write-Host "Uploaded: $uploadedCount files" -ForegroundColor Green
Write-Host "Failed: $failedCount files" -ForegroundColor $(if ($failedCount -gt 0) { "Red" } else { "White" })
Write-Host ""

if ($uploadedCount -gt 0) {
    Write-Host "View files in AWS Console:" -ForegroundColor Yellow
    Write-Host "  https://s3.console.aws.amazon.com/s3/buckets/$BucketName" -ForegroundColor White
    Write-Host ""
    Write-Host "List files via CLI:" -ForegroundColor Yellow
    Write-Host "  aws s3 ls s3://$BucketName/data/" -ForegroundColor White
    Write-Host ""
    Write-Host "Download a file:" -ForegroundColor Yellow
    Write-Host "  aws s3 cp s3://$BucketName/data/weather.csv ./" -ForegroundColor White
    Write-Host ""
    Write-Host "Sync entire folder:" -ForegroundColor Yellow
    Write-Host "  aws s3 sync s3://$BucketName/data/ ./downloaded_data/" -ForegroundColor White
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
