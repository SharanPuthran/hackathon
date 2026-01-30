# ⚠️ DEPRECATED: AWS Bedrock Agents Architecture

**This document describes the old AWS Bedrock Agents architecture.**
**Status**: DEPRECATED - Migrated to AWS Bedrock AgentCore

---

## 🔄 Migration Notice

This architecture has been **replaced with AWS Bedrock AgentCore**.

**New Documentation**: See [`AWS_AGENTCORE_ARCHITECTURE.md`](AWS_AGENTCORE_ARCHITECTURE.md)

**Key Improvements in AgentCore**:
- ✅ **Local Development**: Test agents before cloud deployment
- ✅ **CLI Deployment**: Single command (`agentcore deploy`)
- ✅ **Framework Support**: Full LangGraph, Strands, CrewAI support
- ✅ **Managed Services**: Built-in memory, gateway, tools, observability
- ✅ **Better Permissions**: Simplified IAM model
- ✅ **MCP Integration**: Model Context Protocol server support

**Migration Details**: See [`DEPRECATED_BEDROCK_AGENTS.md`](DEPRECATED_BEDROCK_AGENTS.md)

---

# SkyMarshal - AWS Bedrock Agents Architecture (ARCHIVED)

## Overview

This document outlines the migration from custom LangGraph orchestration to AWS Bedrock Agents for production deployment.

**Note**: This approach is now deprecated in favor of AgentCore.

---

## Architecture Components

### 1. AWS Bedrock Agents (Multi-Agent Orchestrator)

Replace custom orchestrator with AWS Bedrock's native multi-agent system:

```
┌─────────────────────────────────────────────────────────────┐
│                   AWS Bedrock Agents                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Supervisor Agent (Orchestrator)              │  │
│  │  - Coordinates all sub-agents                         │  │
│  │  - Manages workflow state                             │  │
│  │  - Routes requests to appropriate agents              │  │
│  └───────────────────────────────────────────────────────┘  │
│                          │                                   │
│          ┌───────────────┼───────────────┐                  │
│          │               │               │                  │
│  ┌───────▼─────┐ ┌──────▼──────┐ ┌─────▼──────┐          │
│  │   Safety    │ │  Business   │ │ Execution  │          │
│  │   Agents    │ │   Agents    │ │  Agents    │          │
│  │  (3 agents) │ │  (4 agents) │ │ (2 agents) │          │
│  └─────────────┘ └─────────────┘ └────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### 2. Agent Configuration

Each agent configured as a Bedrock Agent with:
- **Model**: Amazon Nova Premier (or Claude after approval)
- **Knowledge Base**: RAG from S3/OpenSearch
- **Action Groups**: Lambda functions for specific tasks
- **Guardrails**: Safety constraints and validation

---

## Agent Definitions

### Supervisor Agent (Orchestrator)

**Role**: Main coordinator
**Model**: Amazon Nova Premier
**Action Groups**:
- `initiate_disruption_analysis`
- `coordinate_safety_review`
- `orchestrate_business_debate`
- `execute_final_decision`

**Prompt Template**:
```
You are the SkyMarshal Supervisor Agent responsible for coordinating
airline disruption management. Your role is to:

1. Analyze incoming disruption scenarios
2. Route tasks to specialized safety and business agents
3. Ensure all regulatory requirements are met
4. Synthesize recommendations into actionable decisions

Current disruption: {disruption_details}
Aircraft: {aircraft_type}
Route: {origin} → {destination}
Passengers affected: {pax_count}
```

### Safety Agents

#### 1. Crew Compliance Agent
**Model**: Nova Premier
**Knowledge Base**: FTL regulations, crew duty limits
**Action Groups**:
- `check_crew_ftl_compliance`
- `calculate_duty_hours`
- `suggest_crew_alternatives`

#### 2. Maintenance Agent
**Model**: Nova Premier
**Knowledge Base**: MEL/AOG procedures, aircraft maintenance data
**Action Groups**:
- `check_mel_deferral`
- `assess_aog_status`
- `query_maintenance_history`

#### 3. Regulatory Agent
**Model**: Nova Premier
**Knowledge Base**: NOTAMs, airspace restrictions, curfews
**Action Groups**:
- `check_notams`
- `verify_curfew_compliance`
- `validate_route_restrictions`

### Business Agents

#### 1. Network Agent
**Model**: Nova Premier
**Knowledge Base**: Flight network data, connection banks
**Action Groups**:
- `analyze_network_propagation`
- `identify_critical_connections`
- `calculate_domino_effects`

#### 2. Guest Experience Agent
**Model**: Nova Premier
**Knowledge Base**: Customer service policies, compensation rules
**Action Groups**:
- `assess_passenger_impact`
- `calculate_compensation`
- `suggest_rebooking_options`

#### 3. Cargo Agent
**Model**: Nova Premier
**Knowledge Base**: Cargo handling procedures, SLAs
**Action Groups**:
- `assess_cargo_impact`
- `prioritize_shipments`
- `suggest_cargo_rerouting`

#### 4. Finance Agent
**Model**: Nova Premier
**Knowledge Base**: Cost models, operational budgets
**Action Groups**:
- `calculate_scenario_costs`
- `perform_cost_benefit_analysis`
- `generate_financial_report`

### Arbitrator Agent

**Model**: Nova Premier
**Role**: Final decision maker
**Action Groups**:
- `evaluate_scenarios`
- `rank_options`
- `select_optimal_solution`

---

## AWS Services Integration

### 1. Amazon RDS PostgreSQL

**Purpose**: Operational database
**Configuration**:
```
Instance Class: db.r6g.xlarge
Storage: 500 GB GP3
Multi-AZ: Enabled
Backup: Automated (7-day retention)
```

**Tables**: All aviation data (flights, passengers, cargo, crew)

### 2. Amazon S3

**Buckets**:
```
skymarshal-prod-disruptions/
├── scenarios/           # Disruption scenarios
├── agent-logs/         # Agent conversation logs
├── decisions/          # Final decisions and reports
└── knowledge-base/     # Document store for RAG
```

### 3. Amazon OpenSearch (Vector DB)

**Purpose**: Vector embeddings for RAG
**Configuration**:
```
Instance: r6g.xlarge.search
Nodes: 3 (multi-AZ)
Storage: 500 GB EBS
```

**Indices**:
- `ftl-regulations` - Crew duty regulations
- `mel-procedures` - Maintenance procedures
- `historical-disruptions` - Past cases
- `sops` - Standard operating procedures

### 4. AWS Lambda

**Functions**:
```
skymarshal-crew-ftl-check       # Check FTL compliance
skymarshal-mel-assessment       # Assess MEL deferrals
skymarshal-notam-check          # Query NOTAMs
skymarshal-network-analysis     # Analyze flight network
skymarshal-cost-calculation     # Calculate costs
skymarshal-database-query       # Query RDS
```

### 5. Amazon Bedrock Knowledge Bases

**Knowledge Bases**:
1. **Aviation Regulations KB**
   - Source: S3 bucket with PDF documents
   - Embedding: Amazon Titan Embeddings
   - Vector Store: OpenSearch

2. **Historical Disruptions KB**
   - Source: Past disruption cases
   - Embedding: Amazon Titan Embeddings
   - Vector Store: OpenSearch

3. **Operational Procedures KB**
   - Source: SOPs, policies, procedures
   - Embedding: Amazon Titan Embeddings
   - Vector Store: OpenSearch

### 6. AWS Step Functions

**Purpose**: Workflow orchestration (backup to Bedrock Agents)
**State Machine**: `skymarshal-disruption-workflow`

```json
{
  "Comment": "SkyMarshal Disruption Management Workflow",
  "StartAt": "InvokeOrchestrator",
  "States": {
    "InvokeOrchestrator": {
      "Type": "Task",
      "Resource": "arn:aws:states:::bedrock:invokeAgent",
      "Parameters": {
        "AgentId": "${OrchestratorAgentId}",
        "AgentAliasId": "PROD",
        "SessionId.$": "$.sessionId",
        "InputText.$": "$.disruptionScenario"
      },
      "Next": "CheckDecision"
    },
    "CheckDecision": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.decisionStatus",
          "StringEquals": "APPROVED",
          "Next": "ExecuteDecision"
        }
      ],
      "Default": "NotifyFailure"
    },
    "ExecuteDecision": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "skymarshal-execute-decision",
        "Payload.$": "$"
      },
      "End": true
    },
    "NotifyFailure": {
      "Type": "Fail",
      "Cause": "Decision rejected or error"
    }
  }
}
```

### 7. Amazon EventBridge

**Purpose**: Event-driven triggers
**Rules**:
- `flight-delay-rule` - Trigger on flight delays
- `aircraft-aog-rule` - Trigger on AOG events
- `crew-unavailable-rule` - Trigger on crew issues

### 8. Amazon API Gateway

**Purpose**: REST API for external integrations
**Endpoints**:
```
POST /api/v1/disruptions          # Submit new disruption
GET  /api/v1/disruptions/{id}     # Get disruption status
POST /api/v1/scenarios/evaluate   # Evaluate scenario
GET  /api/v1/decisions/{id}       # Get decision details
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         AWS Cloud                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 API Gateway (REST)                      │ │
│  └───────────────────────┬────────────────────────────────┘ │
│                          │                                   │
│  ┌───────────────────────▼────────────────────────────────┐ │
│  │            Amazon Bedrock Agents                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │ │
│  │  │ Orchestrator │  │ Safety       │  │  Business   │  │ │
│  │  │    Agent     │  │  Agents (3)  │  │ Agents (4)  │  │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘  │ │
│  └─────────┼──────────────────┼──────────────────┼─────────┘ │
│            │                  │                  │           │
│  ┌─────────▼──────────────────▼──────────────────▼─────────┐ │
│  │              AWS Lambda Functions                        │ │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐           │ │
│  │  │  FTL   │ │  MEL   │ │ NOTAM  │ │  Cost  │           │ │
│  │  │ Check  │ │ Assess │ │ Query  │ │  Calc  │           │ │
│  │  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘           │ │
│  └──────┼──────────┼──────────┼──────────┼────────────────┘ │
│         │          │          │          │                   │
│  ┌──────▼──────────▼──────────▼──────────▼────────────────┐ │
│  │                   Amazon RDS PostgreSQL                  │ │
│  │  (Aviation Data: Flights, Pax, Crew, Cargo)             │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              Amazon OpenSearch (Vector DB)               │ │
│  │  (Embeddings: Regulations, MEL, Historical Cases)        │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                       Amazon S3                          │ │
│  │  (Knowledge Base Docs, Logs, Scenarios, Decisions)       │ │
│  └──────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Cost Estimation

### Monthly Costs (Production)

| Service | Configuration | Monthly Cost |
|---------|--------------|--------------|
| **Bedrock Agents** | 10 agents × 1000 invocations/day | $1,500 |
| **Bedrock Models** | Nova Premier (~50K tokens/day) | $500 |
| **RDS PostgreSQL** | db.r6g.xlarge, Multi-AZ | $700 |
| **OpenSearch** | 3-node cluster, r6g.xlarge | $1,200 |
| **Lambda** | 100K invocations/month | $20 |
| **S3** | 1 TB storage + requests | $50 |
| **API Gateway** | 1M requests/month | $10 |
| **CloudWatch** | Logs + Metrics | $100 |
| **Data Transfer** | 500 GB/month | $45 |
| **Total** | | **~$4,125/month** |

### Per-Disruption Cost: ~$0.50

---

## Security & Compliance

### IAM Roles

```
skymarshal-bedrock-agent-role     # For Bedrock Agents
skymarshal-lambda-execution-role  # For Lambda functions
skymarshal-step-functions-role    # For Step Functions
skymarshal-rds-access-role        # For RDS access
```

### Security Groups

```
sg-bedrock-agents     # Bedrock Agents → Lambda, RDS
sg-lambda-functions   # Lambda → RDS, OpenSearch
sg-rds-database       # RDS access control
sg-opensearch         # OpenSearch access control
```

### Encryption

- **At Rest**: All data encrypted with AWS KMS
- **In Transit**: TLS 1.2+ for all connections
- **Secrets**: AWS Secrets Manager for credentials

---

## Monitoring & Observability

### CloudWatch Dashboards

1. **Agent Performance**
   - Invocation counts
   - Latency metrics
   - Error rates

2. **System Health**
   - RDS connections
   - Lambda execution times
   - OpenSearch query performance

3. **Business Metrics**
   - Disruptions processed
   - Decision accuracy
   - Cost per disruption

### Alarms

```
high-error-rate           # Error rate > 5%
high-latency              # P99 latency > 30s
database-connections-low  # < 10 available connections
opensearch-unhealthy      # Cluster status red
```

---

## Migration Plan

### Phase 1: Infrastructure Setup (Week 1)
- Deploy RDS PostgreSQL
- Set up S3 buckets
- Deploy OpenSearch cluster
- Configure IAM roles

### Phase 2: Knowledge Base Creation (Week 2)
- Upload regulation documents
- Create embeddings
- Configure Bedrock Knowledge Bases
- Test RAG queries

### Phase 3: Agent Development (Week 3-4)
- Create agent configurations
- Develop Lambda action groups
- Test individual agents
- Integrate with knowledge bases

### Phase 4: Integration Testing (Week 5)
- End-to-end workflow testing
- Performance optimization
- Cost optimization

### Phase 5: Production Deployment (Week 6)
- Blue/green deployment
- Traffic migration
- Monitoring and alerting setup

---

## Advantages Over Custom LangGraph

1. **Managed Service**: No infrastructure to maintain
2. **Built-in RAG**: Native knowledge base integration
3. **Scalability**: Auto-scaling without configuration
4. **Security**: AWS-native security and compliance
5. **Monitoring**: Built-in CloudWatch integration
6. **Cost**: Pay-per-use pricing model

---

## Next Steps

1. Submit Anthropic Claude use case form (for better models)
2. Create Terraform templates for infrastructure
3. Develop agent configurations and prompts
4. Prepare knowledge base documents
5. Set up CI/CD pipeline

---

**Document Version**: 1.0
**Last Updated**: 2026-01-30
**Author**: Claude Code (SkyMarshal Team)
