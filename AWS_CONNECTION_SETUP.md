# AWS Bedrock Connection Setup Guide

Quick guide to configure and test your AWS Bedrock connection.

---

## 🔴 Current Status: Not Configured

The AWS connection test shows that credentials are not yet configured.

---

## ✅ Setup Steps (5 minutes)

### Step 1: Create .env File

```bash
cp .env.example .env
```

### Step 2: Get AWS Credentials

You need AWS credentials with Bedrock access. Choose one option:

#### Option A: Use Existing AWS Account

1. Go to AWS Console → IAM → Users → Your User
2. Create Access Key (if you don't have one)
3. Copy the Access Key ID and Secret Access Key

#### Option B: Create New IAM User for Bedrock

1. Go to AWS Console → IAM → Users → Create User
2. User name: `skymarshal-bedrock`
3. Attach policies:
   - `AmazonBedrockFullAccess` (or custom policy below)
4. Create Access Key
5. Copy credentials

**Minimal IAM Policy** (if you want least privilege):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ListFoundationModels",
        "bedrock:GetFoundationModel"
      ],
      "Resource": "*"
    }
  ]
}
```

### Step 3: Edit .env File

Open `.env` and add your credentials:

```bash
# AWS Configuration (All models via Bedrock)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE    # Replace with your key
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY    # Replace with your secret

# Database Configuration (optional for now)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=etihad_aviation
DB_USER=postgres
DB_PASSWORD=your-db-password

# Application Configuration
LOG_LEVEL=INFO
ENABLE_COST_TRACKING=true
MAX_DEBATE_ROUNDS=3
SAFETY_TIMEOUT_SECONDS=60
```

### Step 4: Request Model Access

1. Go to AWS Console → Bedrock → Model access
2. Click "Manage model access"
3. Request access to these models:
   - ✅ **Anthropic Claude 3.7 Sonnet** (or Claude 3 Sonnet)
   - ✅ **Google Gemini 3.0 Pro** (or Gemini 2.0 Flash)
   - ✅ **OpenAI GPT-5 Turbo** (or GPT-4o)
   - ✅ **Amazon Nova Pro**
4. Click "Request model access"
5. Wait for approval (usually instant, sometimes a few minutes)

**Note**: Some newer models (3.7, 3.0, GPT-5) may not be available yet. Use these alternatives:

- Claude 3.7 Sonnet → **Claude 3 Sonnet** (`anthropic.claude-3-sonnet-20240229-v1:0`)
- Gemini 3.0 Pro → **Gemini 2.0 Flash** (`google.gemini-2.0-flash-v1:0`)
- GPT-5 Turbo → **GPT-4o** (`openai.gpt-4o-2024-05-13-v1:0`)

### Step 5: Test Connection

```bash
python3 test_aws_connection.py
```

Expected output:

```
======================================================================
AWS BEDROCK CONNECTION TEST
======================================================================

1. Checking AWS credentials...
   ✓ AWS_ACCESS_KEY_ID found: AKIAIOSF...
   ✓ AWS_SECRET_ACCESS_KEY found: wJalrXUt...
   ✓ AWS_REGION: us-east-1

2. Testing AWS Bedrock connection...
   ✓ Successfully connected to AWS Bedrock
   ✓ Found 50+ foundation models

3. Testing AWS Bedrock Runtime...
   ✓ Successfully connected to Bedrock Runtime

4. Checking model access...
   ✓ Claude 3.7 Sonnet
     Model ID: anthropic.claude-3-7-sonnet-20250219-v1:0
   ✓ Gemini 3.0 Pro
     Model ID: google.gemini-3-0-pro-v1:0
   ...

   Summary: 5/5 models accessible

5. Testing model invocation (optional)...
   ✓ Model invocation successful!
   ✓ Test model: anthropic.claude-3-sonnet-20240229-v1:0
   ✓ Response: Hello from AWS Bedrock!

======================================================================
RESULT: ✓ AWS Bedrock connection working!
======================================================================

✓ Credentials configured
✓ Bedrock connection successful
✓ Models accessible

You can now run the SkyMarshal system!
```

---

## 🔧 Troubleshooting

### Issue: "AWS credentials not configured"

**Solution**: Create `.env` file and add credentials (see Step 3)

```bash
cp .env.example .env
# Edit .env with your credentials
```

### Issue: "No AWS credentials found"

**Solution**: Check that `.env` file exists and has correct format

```bash
cat .env | grep AWS_ACCESS_KEY_ID
# Should show: AWS_ACCESS_KEY_ID=AKIA...
```

### Issue: "AccessDeniedException"

**Solution**: Request model access in AWS Console

1. AWS Console → Bedrock → Model access
2. Request access to required models
3. Wait for approval
4. Test again

### Issue: "Invalid credentials"

**Solution**: Verify credentials are correct

1. Check for extra spaces in `.env` file
2. Verify credentials in AWS Console → IAM → Users
3. Try creating new access key

### Issue: "Region not supported"

**Solution**: Use a supported region

Bedrock is available in these regions:

- `us-east-1` (N. Virginia) - **Recommended**
- `us-west-2` (Oregon)
- `eu-west-1` (Ireland)
- `ap-southeast-1` (Singapore)

Change in `.env`:

```bash
AWS_REGION=us-east-1
```

### Issue: "Models not accessible"

**Solution**: Request model access

Some models require explicit access request:

1. Go to AWS Console → Bedrock → Model access
2. Click "Manage model access"
3. Select models you need
4. Click "Request model access"
5. Wait for approval (usually instant)

---

## 🎯 Quick Test Commands

### Test 1: Check if .env exists

```bash
test -f .env && echo "✓ .env exists" || echo "✗ .env not found"
```

### Test 2: Check credentials in .env

```bash
grep AWS_ACCESS_KEY_ID .env
```

### Test 3: Test AWS CLI (if installed)

```bash
aws bedrock list-foundation-models --region us-east-1
```

### Test 4: Run full connection test

```bash
python3 test_aws_connection.py
```

---

## 📊 Model Requirements

SkyMarshal uses these models via AWS Bedrock:

| Agent             | Model             | Model ID                                    |
| ----------------- | ----------------- | ------------------------------------------- |
| Orchestrator      | Claude 3.7 Sonnet | `anthropic.claude-3-7-sonnet-20250219-v1:0` |
| Arbitrator        | Gemini 3.0 Pro    | `google.gemini-3-0-pro-v1:0`                |
| Safety Agents (3) | Claude 3.7 Sonnet | `anthropic.claude-3-7-sonnet-20250219-v1:0` |
| Network Agent     | GPT-5 Turbo       | `openai.gpt-5-turbo-20250214-v1:0`          |
| Guest Agent       | Claude 3.7 Sonnet | `anthropic.claude-3-7-sonnet-20250219-v1:0` |
| Cargo Agent       | Gemini 3.0 Flash  | `google.gemini-3-0-flash-v1:0`              |
| Finance Agent     | Amazon Nova Pro   | `us.amazon.nova-pro-v1:0`                   |
| Execution Agent   | Claude 3.7 Sonnet | `anthropic.claude-3-7-sonnet-20250219-v1:0` |

**Alternative models** (if newer versions not available):

- Claude 3 Sonnet: `anthropic.claude-3-sonnet-20240229-v1:0`
- Gemini 2.0 Flash: `google.gemini-2.0-flash-v1:0`
- GPT-4o: `openai.gpt-4o-2024-05-13-v1:0`

---

## 💰 Cost Estimate

Per disruption (approximate):

- Claude 3.7 Sonnet (6 agents): $0.45
- Gemini 3.0 Pro (1 agent): $0.25
- GPT-5 Turbo (1 agent): $0.08
- Gemini 3.0 Flash (1 agent): $0.02
- Nova Pro (1 agent): $0.02
- **Total**: ~$1.10 per disruption

For testing: ~$5-10 for 5-10 test runs

---

## 🔐 Security Best Practices

### 1. Never Commit .env File

```bash
# .env is already in .gitignore
git status  # Should not show .env
```

### 2. Use IAM Roles (Production)

For production, use IAM roles instead of access keys:

- EC2 instance role
- ECS task role
- Lambda execution role

### 3. Rotate Credentials Regularly

1. Create new access key
2. Update .env
3. Test connection
4. Delete old access key

### 4. Use Least Privilege

Only grant necessary permissions:

- `bedrock:InvokeModel`
- `bedrock:ListFoundationModels`

### 5. Monitor Usage

Set up AWS Budgets:

1. AWS Console → Billing → Budgets
2. Create budget for Bedrock
3. Set alert threshold (e.g., $50/month)

---

## ✅ Success Checklist

- [ ] Created .env file from .env.example
- [ ] Added AWS credentials to .env
- [ ] Requested model access in AWS Console
- [ ] Ran `python3 test_aws_connection.py`
- [ ] Saw "✓ AWS Bedrock connection working!"
- [ ] All required models accessible

---

## 🚀 Next Steps

Once connection is working:

1. **Test the system**:

   ```bash
   python3 run_demo.py
   ```

2. **Run the dashboard**:

   ```bash
   streamlit run app.py
   ```

3. **Check model configuration**:
   ```bash
   cat src/config.py | grep AGENT_MODEL_MAP -A 30
   ```

---

## 📞 Support

### AWS Support

- AWS Console: https://console.aws.amazon.com/bedrock
- Bedrock Documentation: https://docs.aws.amazon.com/bedrock/
- IAM Documentation: https://docs.aws.amazon.com/iam/

### Common Issues

- Check AWS_CONNECTION_SETUP.md (this file)
- Run test_aws_connection.py for diagnostics
- Review .env file format
- Verify model access in AWS Console

---

**Status**: Ready to configure  
**Test Script**: `test_aws_connection.py`  
**Next Action**: Create .env file and add credentials
