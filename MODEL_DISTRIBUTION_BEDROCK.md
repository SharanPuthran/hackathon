# SkyMarshal - AWS Bedrock Model Distribution

## Overview

SkyMarshal uses **AWS Bedrock exclusively** with the **latest and most powerful models** from multiple AI providers, all accessed through a single unified platform.

---

## 🎯 Complete Model Distribution

### All Models via AWS Bedrock

| Agent                | Model              | Series    | Purpose                                  |
| -------------------- | ------------------ | --------- | ---------------------------------------- |
| **Orchestrator**     | Claude 3.7 Sonnet  | Anthropic | Fast workflow coordination               |
| **Crew Compliance**  | Claude 3.7 Sonnet  | Anthropic | FTL regulations (Chain-of-thought)       |
| **Maintenance**      | Claude 3.7 Sonnet  | Anthropic | MEL/AOG analysis                         |
| **Regulatory**       | Claude 3.7 Sonnet  | Anthropic | NOTAMs, curfews, ATC                     |
| **Network**          | GPT-5 Turbo        | OpenAI    | Network propagation analysis             |
| **Guest Experience** | Claude 3.7 Sonnet  | Anthropic | Customer sentiment                       |
| **Cargo**            | Gemini 3.0 Flash   | Google    | Fast logistics optimization              |
| **Finance**          | Amazon Nova Pro    | Amazon    | Financial modeling                       |
| **Arbitrator**       | **Gemini 3.0 Pro** | Google    | **Strongest reasoning for optimization** |
| **Execution**        | Claude 3.7 Sonnet  | Anthropic | Action execution                         |

---

## 🏆 Model Selection Rationale

### Arbitrator: Gemini 3.0 Pro (Strongest Reasoning)

**Why the most powerful model?**

- **Complex multi-criteria optimization** requires strongest reasoning
- **Scenario composition** from multiple agent proposals
- **Constraint enforcement** with zero tolerance
- **Explainability generation** with detailed rationale
- **Historical pattern matching** for predictive analysis
- **Massive context window** (2M tokens) for comprehensive analysis

**Model ID**: `google.gemini-3-0-pro-v1:0`

### Safety Agents: Claude 3.7 Sonnet

**Why Claude for safety?**

- **Superior chain-of-thought reasoning**
- **Excellent at following complex regulations**
- **High accuracy for safety-critical decisions**
- **Consistent structured output**
- **Proven track record for compliance**

**Agents**: Crew Compliance, Maintenance, Regulatory

### Business Agents: Mixed Latest Models

**Why different models?**

- **Diverse perspectives** in debate phase
- **Optimal performance** for each specific task
- **Latest capabilities** from each AI provider

**Distribution**:

- **Network Agent**: GPT-5 Turbo (excellent graph reasoning)
- **Guest Experience**: Claude 3.7 Sonnet (empathy & sentiment)
- **Cargo Agent**: Gemini 3.0 Flash (fast logistics)
- **Finance Agent**: Nova Pro (cost-effective financial modeling)

---

## 📊 Model Specifications

### Gemini 3.0 Pro (Arbitrator)

- **Context Window**: 2M tokens
- **Strengths**: Multi-criteria optimization, complex reasoning, massive context
- **Speed**: Medium (8-12 seconds)
- **Cost**: Premium (highest quality)
- **Use Case**: Complex scenario ranking and optimization

### Claude 3.7 Sonnet (Safety + Orchestration)

- **Context Window**: 200K tokens
- **Strengths**: Chain-of-thought, safety compliance, structured output
- **Speed**: Fast (3-5 seconds)
- **Cost**: Medium
- **Use Case**: Safety-critical decisions, workflow coordination

### GPT-5 Turbo (Network Agent)

- **Context Window**: 256K tokens
- **Strengths**: Graph reasoning, network analysis, fast inference
- **Speed**: Very Fast (2-4 seconds)
- **Cost**: Medium
- **Use Case**: Network propagation analysis

### Gemini 3.0 Flash (Cargo Agent)

- **Context Window**: 1M tokens
- **Strengths**: Fast inference, logistics optimization
- **Speed**: Very Fast (2-3 seconds)
- **Cost**: Low
- **Use Case**: Quick logistics decisions

### Amazon Nova Pro (Finance Agent)

- **Context Window**: 300K tokens
- **Strengths**: Financial modeling, numerical reasoning
- **Speed**: Fast (3-5 seconds)
- **Cost**: Very Low
- **Use Case**: Cost analysis and financial optimization

---

## 🔄 Model Flow

```
Disruption Event
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  Orchestrator (Claude 3.7 Sonnet)                       │
│  Fast workflow coordination                             │
└────────┬─────────────────────────────────────────────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
┌─────────────────────┐            ┌─────────────────────┐
│  Safety Agents      │            │  Business Agents    │
│  (Claude 3.7)       │            │  (Mixed Models)     │
└─────────────────────┘            └─────────────────────┘
         │                                     │
         │  • Crew Compliance                 │  • Network (GPT-5 Turbo)
         │  • Maintenance                     │  • Guest (Claude 3.7)
         │  • Regulatory                      │  • Cargo (Gemini 3.0 Flash)
         │                                    │  • Finance (Nova Pro)
         │                                     │
         └─────────────────┬───────────────────┘
                           │
                           ▼
                  ┌─────────────────────┐
                  │   Arbitrator        │
                  │  (Gemini 3.0 Pro)   │
                  │  STRONGEST MODEL    │
                  └─────────┬───────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │  Human Approval     │
                  └─────────┬───────────┘
                            │
                            ▼
                  ┌─────────────────────┐
                  │  Execution          │
                  │  (Claude 3.7)       │
                  └─────────────────────┘
```

---

## 💰 Cost Optimization

### Per Disruption Estimate

| Model                 | Usage                                       | Estimated Cost | % of Total |
| --------------------- | ------------------------------------------- | -------------- | ---------- |
| **Gemini 3.0 Pro**    | Arbitrator (1x)                             | $0.25          | 23%        |
| **Claude 3.7 Sonnet** | Orchestrator + 3 Safety + Guest + Execution | $0.45          | 41%        |
| **GPT-5 Turbo**       | Network (1x)                                | $0.08          | 7%         |
| **Gemini 3.0 Flash**  | Cargo (1x)                                  | $0.02          | 2%         |
| **Nova Pro**          | Finance (1x)                                | $0.02          | 2%         |
| **Overhead**          | Multiple invocations                        | $0.28          | 25%        |
| **Total**             |                                             | **~$1.10**     | **100%**   |

### Cost Benefits

- **Single provider**: Simplified billing and management
- **Volume discounts**: AWS Bedrock enterprise pricing
- **No API key management**: Single AWS credential
- **Unified monitoring**: CloudWatch integration

---

## 🚀 Performance Characteristics

### Response Time by Model

| Model             | Avg Response | Use Case              |
| ----------------- | ------------ | --------------------- |
| Gemini 3.0 Flash  | 2-3 sec      | Fast logistics        |
| GPT-5 Turbo       | 2-4 sec      | Network analysis      |
| Claude 3.7 Sonnet | 3-5 sec      | Safety & coordination |
| Nova Pro          | 3-5 sec      | Financial modeling    |
| Gemini 3.0 Pro    | 8-12 sec     | Complex optimization  |

### Total Workflow Time

- **Target**: < 3 minutes from trigger to scenarios
- **Safety Assessment**: < 60 seconds (3 agents in parallel)
- **Impact Assessment**: < 30 seconds (4 agents in parallel)
- **Option Formulation**: < 45 seconds (debate rounds)
- **Arbitration**: < 30 seconds (Gemini 3.0 Pro)
- **Buffer**: 15 seconds

---

## 🔧 Configuration

### In Code (`src/config.py`)

```python
AGENT_MODEL_MAP = {
    "orchestrator": {
        "model_id": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "provider": "bedrock",
        "reason": "Fast workflow coordination"
    },
    "arbitrator": {
        "model_id": "google.gemini-3-0-pro-v1:0",
        "provider": "bedrock",
        "reason": "Strongest reasoning for complex optimization"
    },
    "crew_compliance_agent": {
        "model_id": "anthropic.claude-3-7-sonnet-20250219-v1:0",
        "provider": "bedrock",
        "reason": "Chain-of-thought for FTL regulations"
    },
    "network_agent": {
        "model_id": "openai.gpt-5-turbo-20250214-v1:0",
        "provider": "bedrock",
        "reason": "Fast network propagation analysis"
    },
    "cargo_agent": {
        "model_id": "google.gemini-3-0-flash-v1:0",
        "provider": "bedrock",
        "reason": "Fast logistics optimization"
    },
    # ... etc
}
```

### Environment Setup

```bash
# Only AWS credentials needed
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=etihad_aviation
DB_USER=postgres
DB_PASSWORD=your-password
```

---

## ✅ Benefits of AWS Bedrock Exclusive

### 1. Unified Platform

- **Single provider**: All models through one API
- **Consistent interface**: Same code for all models
- **Simplified management**: One set of credentials

### 2. Enterprise Features

- **Security**: AWS IAM integration
- **Compliance**: SOC 2, HIPAA, GDPR compliant
- **Monitoring**: CloudWatch integration
- **Logging**: CloudTrail audit logs

### 3. Cost Management

- **Volume discounts**: Enterprise pricing
- **Unified billing**: Single AWS bill
- **Cost allocation**: Tag-based tracking
- **Budget alerts**: AWS Budgets integration

### 4. Performance

- **Low latency**: AWS infrastructure
- **High availability**: Multi-AZ deployment
- **Auto-scaling**: Managed capacity
- **Global reach**: Multiple regions

### 5. Model Access

- **Latest models**: Immediate access to new releases
- **Multiple providers**: Anthropic, Google, OpenAI, Amazon
- **Model versioning**: Pin to specific versions
- **Easy upgrades**: Change model ID only

---

## 🔄 Model Upgrade Path

### Easy Model Swaps

```python
# Upgrade Arbitrator to even newer model
"arbitrator": {
    "model_id": "google.gemini-3-5-pro-v1:0",  # Future upgrade
    "provider": "bedrock",
    "reason": "Enhanced reasoning capabilities"
}

# Upgrade Safety Agents
"crew_compliance_agent": {
    "model_id": "anthropic.claude-4-opus-v1:0",  # Future upgrade
    "provider": "bedrock",
    "reason": "Maximum accuracy for safety"
}
```

### A/B Testing

```python
# Test different models for same agent
"network_agent": {
    "model_id": "anthropic.claude-3-7-sonnet-20250219-v1:0",  # Test Claude
    # "model_id": "openai.gpt-5-turbo-20250214-v1:0",  # vs GPT-5
    "provider": "bedrock",
    "reason": "A/B testing network analysis"
}
```

---

## 📈 Model Comparison

### By Capability

| Capability         | Best Model        | Second Best       |
| ------------------ | ----------------- | ----------------- |
| Complex Reasoning  | Gemini 3.0 Pro    | Claude 3.7 Sonnet |
| Chain-of-Thought   | Claude 3.7 Sonnet | Gemini 3.0 Pro    |
| Fast Inference     | Gemini 3.0 Flash  | GPT-5 Turbo       |
| Network Analysis   | GPT-5 Turbo       | Claude 3.7 Sonnet |
| Financial Modeling | Nova Pro          | Claude 3.7 Sonnet |
| Customer Sentiment | Claude 3.7 Sonnet | Gemini 3.0 Pro    |

### By Cost-Performance

| Model             | Cost     | Performance | Value      |
| ----------------- | -------- | ----------- | ---------- |
| Gemini 3.0 Flash  | ⭐       | ⭐⭐⭐⭐    | ⭐⭐⭐⭐⭐ |
| Nova Pro          | ⭐       | ⭐⭐⭐      | ⭐⭐⭐⭐⭐ |
| GPT-5 Turbo       | ⭐⭐     | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐   |
| Claude 3.7 Sonnet | ⭐⭐⭐   | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐   |
| Gemini 3.0 Pro    | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐  | ⭐⭐⭐⭐   |

---

## 🎯 Summary

### Model Distribution

- **Claude 3.7 Sonnet**: 6 agents (54%) - Safety & coordination
- **Gemini 3.0 Pro**: 1 agent (9%) - Strongest reasoning (Arbitrator)
- **Gemini 3.0 Flash**: 1 agent (9%) - Fast logistics
- **GPT-5 Turbo**: 1 agent (9%) - Network analysis
- **Nova Pro**: 1 agent (9%) - Financial modeling

### Key Advantages

✅ **Single provider** - AWS Bedrock only  
✅ **Latest models** - Claude 3.7, GPT-5, Gemini 3.0  
✅ **Strongest reasoning** - Gemini 3.0 Pro for Arbitrator  
✅ **Fast models** - GPT-5 Turbo, Gemini 3.0 Flash for speed  
✅ **Enterprise ready** - Security, compliance, monitoring  
✅ **Cost optimized** - Right model for each task  
✅ **Easy management** - Single credential, unified billing

---

**SkyMarshal: All Models via AWS Bedrock - Latest, Fastest, Strongest**
