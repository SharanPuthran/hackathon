# Quick Setup Script for DynamoDB
# This script checks prerequisites and guides you through the setup

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "DynamoDB Quick Setup" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python
Write-Host "Step 1: Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = py --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
    $pythonOk = $true
} catch {
    Write-Host "✗ Python not found" -ForegroundColor Red
    $pythonOk = $false
}
Write-Host ""

# Step 2: Check AWS CLI
Write-Host "Step 2: Checking AWS CLI..." -ForegroundColor Yellow
try {
    $awsVersion = aws --version 2>&1
    Write-Host "✓ AWS CLI found: $awsVersion" -ForegroundColor Green
    $awsOk = $true
} catch {
    Write-Host "✗ AWS CLI not found" -ForegroundColor Red
    Write-Host "  Please restart your terminal or run setup_aws.ps1" -ForegroundColor Yellow
    $awsOk = $false
}
Write-Host ""

# Step 3: Check AWS credentials
Write-Host "Step 3: Checking AWS credentials..." -ForegroundColor Yellow
if ($awsOk) {
    try {
        $identity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
        Write-Host "✓ AWS credentials configured" -ForegroundColor Green
        Write-Host "  Account: $($identity.Account)" -ForegroundColor White
        Write-Host "  User: $($identity.Arn)" -ForegroundColor White
        $credsOk = $true
    } catch {
        Write-Host "✗ AWS credentials not configured" -ForegroundColor Red
        Write-Host "  Please run: aws configure" -ForegroundColor Yellow
        $credsOk = $false
    }
} else {
    $credsOk = $false
}
Write-Host ""

# Step 4: Check boto3
Write-Host "Step 4: Checking boto3 (Python AWS SDK)..." -ForegroundColor Yellow
if ($pythonOk) {
    try {
        $boto3Check = py -c "import boto3; print(boto3.__version__)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ boto3 installed: version $boto3Check" -ForegroundColor Green
            $boto3Ok = $true
        } else {
            Write-Host "✗ boto3 not installed" -ForegroundColor Red
            $boto3Ok = $false
        }
    } catch {
        Write-Host "✗ boto3 not installed" -ForegroundColor Red
        $boto3Ok = $false
    }
} else {
    $boto3Ok = $false
}
Write-Host ""

# Summary
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Prerequisites Check" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Python:         $(if ($pythonOk) { '✓' } else { '✗' })" -ForegroundColor $(if ($pythonOk) { 'Green' } else { 'Red' })
Write-Host "AWS CLI:        $(if ($awsOk) { '✓' } else { '✗' })" -ForegroundColor $(if ($awsOk) { 'Green' } else { 'Red' })
Write-Host "AWS Credentials: $(if ($credsOk) { '✓' } else { '✗' })" -ForegroundColor $(if ($credsOk) { 'Green' } else { 'Red' })
Write-Host "boto3:          $(if ($boto3Ok) { '✓' } else { '✗' })" -ForegroundColor $(if ($boto3Ok) { 'Green' } else { 'Red' })
Write-Host ""

# Install boto3 if needed
if ($pythonOk -and -not $boto3Ok) {
    Write-Host "boto3 is required to upload data to DynamoDB" -ForegroundColor Yellow
    $response = Read-Host "Install boto3 now? (y/n)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host ""
        Write-Host "Installing boto3..." -ForegroundColor Cyan
        py -m pip install boto3
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ boto3 installed successfully" -ForegroundColor Green
            $boto3Ok = $true
        } else {
            Write-Host "✗ Failed to install boto3" -ForegroundColor Red
        }
        Write-Host ""
    }
}

# Check if ready to proceed
$allOk = $pythonOk -and $awsOk -and $credsOk -and $boto3Ok

if ($allOk) {
    Write-Host "=" * 80 -ForegroundColor Green
    Write-Host "✓ All prerequisites met! Ready to create DynamoDB tables" -ForegroundColor Green
    Write-Host "=" * 80 -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Create tables and upload data (Recommended):" -ForegroundColor Yellow
    Write-Host "   py create_dynamodb_tables.py" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Or create tables only (PowerShell):" -ForegroundColor Yellow
    Write-Host "   .\create_dynamodb_tables.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Read the guide:" -ForegroundColor Yellow
    Write-Host "   DYNAMODB_SETUP_GUIDE.md" -ForegroundColor White
    Write-Host ""
    
    $response = Read-Host "Run create_dynamodb_tables.py now? (y/n)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host ""
        Write-Host "=" * 80 -ForegroundColor Cyan
        Write-Host "Running DynamoDB table creation..." -ForegroundColor Cyan
        Write-Host "=" * 80 -ForegroundColor Cyan
        Write-Host ""
        py create_dynamodb_tables.py
    }
} else {
    Write-Host "=" * 80 -ForegroundColor Red
    Write-Host "✗ Prerequisites not met" -ForegroundColor Red
    Write-Host "=" * 80 -ForegroundColor Red
    Write-Host ""
    Write-Host "Please fix the issues above and run this script again." -ForegroundColor Yellow
    Write-Host ""
    
    if (-not $pythonOk) {
        Write-Host "Install Python: https://www.python.org/downloads/" -ForegroundColor Yellow
    }
    
    if (-not $awsOk) {
        Write-Host "Restart terminal or run: .\setup_aws.ps1" -ForegroundColor Yellow
    }
    
    if (-not $credsOk) {
        Write-Host "Configure AWS: aws configure" -ForegroundColor Yellow
    }
    
    if (-not $boto3Ok -and $pythonOk) {
        Write-Host "Install boto3: py -m pip install boto3" -ForegroundColor Yellow
    }
}

Write-Host ""
