# SkyMarshal - Setup Guide

## Quick Start (Day 1 Build)

### Prerequisites

1. **Python 3.11+**
2. **PostgreSQL 13+** (running locally or remote)
3. **API Keys:**
   - AWS Account with Bedrock access
   - OpenAI API key
   - Google AI API key

### Step 1: Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Setup

```bash
# Create PostgreSQL database
createdb etihad_aviation

# Run schema creation
psql -d etihad_aviation -f database_schema.sql

# Generate and load data
python generate_data.py
python csv_to_sql.py

# Import data (if using SQL inserts)
# psql -d etihad_aviation -f sql_inserts/import_all.sql
```

### Step 3: Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

Required variables:

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

OPENAI_API_KEY=your-key
GOOGLE_API_KEY=your-key

DB_HOST=localhost
DB_PORT=5432
DB_NAME=etihad_aviation
DB_USER=postgres
DB_PASSWORD=your-password
```

### Step 4: Test Installation

```bash
# Test database connection
python -c "from src.database import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().initialize())"

# Test model providers
python -c "from src.model_providers import create_bedrock_client; create_bedrock_client()"
```

### Step 5: Run Demo

**Option A: CLI Demo**

```bash
python run_demo.py
```

**Option B: Streamlit Dashboard**

```bash
streamlit run app.py
```

The dashboard will open at http://localhost:8501

## Architecture Overview

```
src/
├── config.py              # Configuration and model mapping
├── models.py              # Pydantic data models
├── database.py            # Database manager
├── model_providers.py     # Multi-provider LLM abstraction
├── orchestrator.py        # LangGraph workflow
└── agents/
    ├── base_agent.py      # Base agent class
    ├── safety_agents.py   # 3 safety agents
    ├── business_agents.py # 4 business agents
    └── arbitrator.py      # Skymarshal arbitrator
```

## Model Distribution

| Component         | Model            | Provider | Reason                      |
| ----------------- | ---------------- | -------- | --------------------------- |
| Orchestrator      | Claude Sonnet 4  | Bedrock  | Workflow coordination       |
| Arbitrator        | Gemini 2.0 Flash | Google   | Multi-criteria optimization |
| Safety Agents (3) | Claude Sonnet 4  | Bedrock  | Chain-of-thought reasoning  |
| Network Agent     | GPT-4o           | OpenAI   | Network analysis            |
| Guest Agent       | Claude Sonnet 4  | Bedrock  | Customer sentiment          |
| Cargo Agent       | Gemini 2.0 Flash | Google   | Logistics optimization      |
| Finance Agent     | Nova Pro         | Bedrock  | Financial modeling          |

## Workflow Phases

1. **Trigger**: Initialize disruption event
2. **Safety Assessment**: 3 safety agents (mandatory, blocking)
3. **Guardrail Check**: Validate safety completion
4. **Impact Assessment**: 4 business agents quantify impacts
5. **Option Formulation**: Business agents propose solutions
6. **Arbitration**: Skymarshal ranks scenarios
7. **Human Approval**: Duty manager reviews (auto-approved in demo)
8. **Execution**: Execute chosen scenario (simulated)

## Demo Scenarios

### Scenario 1: Hydraulic Failure

```python
DisruptionEvent(
    flight_number="EY551",
    aircraft_code="A380",
    origin="LHR",
    destination="AUH",
    disruption_type="technical",
    description="Hydraulic system failure",
    severity="high"
)
```

### Scenario 2: Crew Timeout

```python
DisruptionEvent(
    flight_number="EY123",
    aircraft_code="A350",
    origin="AUH",
    destination="JFK",
    disruption_type="crew",
    description="Captain exceeds FTL duty limits",
    severity="medium"
)
```

### Scenario 3: Weather Diversion

```python
DisruptionEvent(
    flight_number="EY456",
    aircraft_code="B787-9",
    origin="AUH",
    destination="SYD",
    disruption_type="weather",
    description="Severe weather at destination",
    severity="high"
)
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready

# Test connection
psql -d etihad_aviation -c "SELECT COUNT(*) FROM flights;"
```

### AWS Bedrock Access

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1
```

### Model Provider Errors

**OpenAI:**

```bash
# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Google Gemini:**

```bash
# Test API key
curl "https://generativelanguage.googleapis.com/v1/models?key=$GOOGLE_API_KEY"
```

## Cost Estimation

Per disruption (estimated):

- Orchestrator: $0.11
- Safety Agents (3x): $0.46
- Business Agents (4x): $0.16
- Arbitrator: $0.11
- Execution: $0.26

**Total: ~$1.10 per disruption**

For 7 disruptions (demo): ~$7.70

## Performance Targets

- Response time: < 3 minutes from trigger to scenarios
- Safety constraint violations: 0 (hard requirement)
- Scenario quality: Top-3 include optimal solution 95%+
- System uptime: 99.9%

## Next Steps

1. **Add Vector Database**: Integrate Pinecone for historical disruption search
2. **Implement RAG**: Add Bedrock Knowledge Base for regulatory documents
3. **Add Guardrails**: Integrate Guardrails AI framework
4. **Real MCP Integration**: Connect to actual airline systems
5. **Production Deployment**: AWS ECS/EKS with auto-scaling

## Support

For issues or questions:

1. Check logs in console output
2. Verify all API keys are valid
3. Ensure database is populated with data
4. Test each component independently

## License

Proprietary - Hackathon Demo
