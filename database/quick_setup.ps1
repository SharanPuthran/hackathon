# Quick Setup for DynamoDB (No AWS CLI Required)

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Quick DynamoDB Setup (No AWS CLI Required!)" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

Write-Host "Good news! You don't need AWS CLI." -ForegroundColor Green
Write-Host "You can use Python boto3 directly!" -ForegroundColor Green
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = py --version 2>&1
    Write-Host "✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found" -ForegroundColor Red
    exit 1
}

# Check boto3
Write-Host "Checking boto3..." -ForegroundColor Yellow
try {
    $boto3Version = py -c "import boto3; print(boto3.__version__)" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ boto3: version $boto3Version" -ForegroundColor Green
    } else {
        Write-Host "✗ boto3 not installed" -ForegroundColor Red
        Write-Host "  Installing boto3..." -ForegroundColor Yellow
        py -m pip install boto3
    }
} catch {
    Write-Host "✗ boto3 not installed" -ForegroundColor Red
    Write-Host "  Installing boto3..." -ForegroundColor Yellow
    py -m pip install boto3
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Green
Write-Host "✓ Ready to configure AWS credentials!" -ForegroundColor Green
Write-Host "=" * 80 -ForegroundColor Green
Write-Host ""

Write-Host "You need AWS credentials to proceed." -ForegroundColor Yellow
Write-Host ""
Write-Host "If you don't have them yet:" -ForegroundColor Cyan
Write-Host "  1. Go to: https://console.aws.amazon.com/" -ForegroundColor White
Write-Host "  2. Sign in to your AWS account" -ForegroundColor White
Write-Host "  3. Go to IAM service" -ForegroundColor White
Write-Host "  4. Click Users → Create User" -ForegroundColor White
Write-Host "  5. Enable 'Programmatic access'" -ForegroundColor White
Write-Host "  6. Attach policy: AmazonDynamoDBFullAccess" -ForegroundColor White
Write-Host "  7. Download the credentials CSV file" -ForegroundColor White
Write-Host ""

$response = Read-Host "Do you have your AWS credentials ready? (y/n)"

if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host ""
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host "Running AWS credentials configuration..." -ForegroundColor Cyan
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""
    
    py configure_aws_credentials.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=" * 80 -ForegroundColor Green
        Write-Host "Next Step: Create DynamoDB Tables" -ForegroundColor Green
        Write-Host "=" * 80 -ForegroundColor Green
        Write-Host ""
        
        $response2 = Read-Host "Create DynamoDB tables and upload data now? (y/n)"
        
        if ($response2 -eq 'y' -or $response2 -eq 'Y') {
            Write-Host ""
            Write-Host "=" * 80 -ForegroundColor Cyan
            Write-Host "Creating DynamoDB tables and uploading data..." -ForegroundColor Cyan
            Write-Host "=" * 80 -ForegroundColor Cyan
            Write-Host ""
            
            py create_dynamodb_tables.py
        } else {
            Write-Host ""
            Write-Host "You can create tables later by running:" -ForegroundColor Yellow
            Write-Host "  py create_dynamodb_tables.py" -ForegroundColor White
        }
    }
} else {
    Write-Host ""
    Write-Host "Please get your AWS credentials first, then run:" -ForegroundColor Yellow
    Write-Host "  .\quick_setup.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Or manually run:" -ForegroundColor Yellow
    Write-Host "  py configure_aws_credentials.py" -ForegroundColor White
    Write-Host ""
}

Write-Host ""
Write-Host "For detailed instructions, read:" -ForegroundColor Cyan
Write-Host "  SETUP_WITHOUT_AWS_CLI.md" -ForegroundColor White
Write-Host ""
