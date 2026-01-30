# SkyMarshal - Quick Start Guide

## 🚀 Get Running in 10 Minutes

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- API Keys (AWS, OpenAI, Google)

### Step 1: Install (2 minutes)

```bash
# Run installation script
./install.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure (2 minutes)

```bash
# Copy environment template
cp .env.example .env

# Edit with your keys
nano .env
```

Required keys:

```
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
OPENAI_API_KEY=your-key
GOOGLE_API_KEY=your-key
DB_PASSWORD=your-password
```

### Step 3: Setup Database (3 minutes)

```bash
# Create database
createdb etihad_aviation

# Load schema
psql -d etihad_aviation -f database_schema.sql

# Generate data
python generate_data.py
```

### Step 4: Test (1 minute)

```bash
python test_system.py
```

Expected output:

```
✅ PASS - Database
✅ PASS - Model Providers
✅ PASS - Agents
✅ PASS - Orchestrator
🎉 All tests passed! System is ready.
```

### Step 5: Run Demo (2 minutes)

**Option A: CLI Demo**

```bash
python run_demo.py
```

**Option B: Dashboard**

```bash
streamlit run app.py
```

Dashboard opens at: http://localhost:8501

## 🎬 Demo Flow

1. Click "Initialize System" in sidebar
2. Enter disruption details:
   - Flight: EY551
   - Aircraft: A380
   - Type: Technical
   - Description: Hydraulic failure
3. Click "Run Disruption Management"
4. Watch workflow execute (2-3 minutes)
5. Review ranked scenarios
6. See execution results

## 🐛 Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
pg_isready

# Check database exists
psql -l | grep etihad_aviation
```

### API Key Errors

```bash
# Test AWS
aws sts get-caller-identity

# Test OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Google
curl "https://generativelanguage.googleapis.com/v1/models?key=$GOOGLE_API_KEY"
```

### Import Errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📊 What to Expect

### CLI Output

```
=== PHASE 1: TRIGGER ===
Disruption: EY551 - Hydraulic system failure

=== PHASE 2: SAFETY ASSESSMENT ===
Safety constraints identified: 3

=== PHASE 3: IMPACT ASSESSMENT ===
Impact assessments completed: 4

=== PHASE 4: OPTION FORMULATION ===
Proposals generated: 4

=== PHASE 5: ARBITRATION ===
Scenarios ranked: 3

=== PHASE 6: HUMAN APPROVAL ===
Human approval received

=== PHASE 7: EXECUTION ===
Executing scenario: Aircraft Swap Recovery
```

### Dashboard View

- Phase tracker showing progress
- Safety constraints with reasoning
- Impact assessment cards
- Top-3 ranked scenarios with pros/cons
- Human approval interface
- Execution logs

## 💰 Cost Estimate

Per demo run: ~$1.10

- Safety agents: $0.46
- Business agents: $0.16
- Arbitrator: $0.11
- Orchestrator: $0.11
- Execution: $0.26

## 📚 Next Steps

1. **Explore Code**: Check `src/` directory
2. **Read Docs**: See `README_SKYMARSHAL.md`
3. **Customize**: Modify agents in `src/agents/`
4. **Extend**: Add new agents or phases

## 🆘 Need Help?

1. Check `SETUP.md` for detailed instructions
2. Run `python test_system.py` to diagnose issues
3. Check logs in console output
4. Verify all API keys are valid

## 🎯 Success Checklist

- [ ] Virtual environment activated
- [ ] Dependencies installed
- [ ] .env configured with API keys
- [ ] Database created and populated
- [ ] Test script passes
- [ ] Demo runs successfully

---

**Ready to go? Run: `python run_demo.py`**
