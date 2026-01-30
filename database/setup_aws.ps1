# AWS CLI Setup and Verification Script
# Run this script after restarting your terminal

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "AWS CLI Setup and Configuration Helper" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Step 1: Check if AWS CLI is installed
Write-Host "Step 1: Checking AWS CLI installation..." -ForegroundColor Yellow
try {
    $awsVersion = aws --version 2>&1
    Write-Host "✓ AWS CLI is installed: $awsVersion" -ForegroundColor Green
    $awsInstalled = $true
} catch {
    Write-Host "✗ AWS CLI is not found in PATH" -ForegroundColor Red
    Write-Host "  Please restart your terminal or IDE and try again." -ForegroundColor Yellow
    Write-Host "  If issue persists, manually add to PATH:" -ForegroundColor Yellow
    Write-Host "  C:\Program Files\Amazon\AWSCLIV2\" -ForegroundColor Yellow
    $awsInstalled = $false
}

Write-Host ""

if (-not $awsInstalled) {
    Write-Host "Please restart your terminal and run this script again." -ForegroundColor Yellow
    exit 1
}

# Step 2: Check if AWS is configured
Write-Host "Step 2: Checking AWS configuration..." -ForegroundColor Yellow
$credentialsPath = "$env:USERPROFILE\.aws\credentials"
$configPath = "$env:USERPROFILE\.aws\config"

if (Test-Path $credentialsPath) {
    Write-Host "✓ AWS credentials file exists" -ForegroundColor Green
    $configured = $true
} else {
    Write-Host "✗ AWS credentials not configured" -ForegroundColor Red
    $configured = $false
}

Write-Host ""

# Step 3: Configure AWS if needed
if (-not $configured) {
    Write-Host "Step 3: AWS Configuration Required" -ForegroundColor Yellow
    Write-Host "=" * 80 -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You need to configure AWS CLI with your credentials." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To get AWS credentials:" -ForegroundColor Cyan
    Write-Host "  1. Log in to AWS Console: https://console.aws.amazon.com/" -ForegroundColor White
    Write-Host "  2. Go to IAM → Users → Your User → Security Credentials" -ForegroundColor White
    Write-Host "  3. Create Access Key (if you don't have one)" -ForegroundColor White
    Write-Host "  4. Download the credentials CSV file" -ForegroundColor White
    Write-Host ""
    
    $response = Read-Host "Do you want to configure AWS CLI now? (y/n)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host ""
        Write-Host "Running: aws configure" -ForegroundColor Cyan
        Write-Host ""
        aws configure
    } else {
        Write-Host ""
        Write-Host "You can configure AWS CLI later by running:" -ForegroundColor Yellow
        Write-Host "  aws configure" -ForegroundColor White
        Write-Host ""
    }
} else {
    Write-Host "Step 3: Testing AWS connection..." -ForegroundColor Yellow
    try {
        $identity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
        Write-Host "✓ AWS connection successful!" -ForegroundColor Green
        Write-Host "  Account: $($identity.Account)" -ForegroundColor White
        Write-Host "  User ARN: $($identity.Arn)" -ForegroundColor White
        Write-Host "  User ID: $($identity.UserId)" -ForegroundColor White
    } catch {
        Write-Host "✗ AWS connection failed" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please check your credentials and try:" -ForegroundColor Yellow
        Write-Host "  aws configure" -ForegroundColor White
    }
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Quick Commands:" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "Check your identity:" -ForegroundColor Yellow
Write-Host "  aws sts get-caller-identity" -ForegroundColor White
Write-Host ""
Write-Host "List S3 buckets:" -ForegroundColor Yellow
Write-Host "  aws s3 ls" -ForegroundColor White
Write-Host ""
Write-Host "List EC2 instances:" -ForegroundColor Yellow
Write-Host "  aws ec2 describe-instances --region us-east-1" -ForegroundColor White
Write-Host ""
Write-Host "Upload files to S3:" -ForegroundColor Yellow
Write-Host "  aws s3 cp output/weather.csv s3://your-bucket-name/" -ForegroundColor White
Write-Host ""
Write-Host "Get help:" -ForegroundColor Yellow
Write-Host "  aws help" -ForegroundColor White
Write-Host "  aws s3 help" -ForegroundColor White
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "For detailed guide, see: AWS_CLI_SETUP_GUIDE.md" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
