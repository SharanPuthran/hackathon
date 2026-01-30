# SkyMarshal - AWS Cloud Deployment Guide

## Overview

Complete guide for deploying SkyMarshal to AWS cloud using Bedrock Agents, RDS, OpenSearch, and other managed services.

---

## ✅ Completed Setup

### 1. Local Development Environment

- ✅ **PostgreSQL** installed and running
- ✅ **Database schema** created (14 tables)
- ✅ **Seed data** loaded (aircraft types, airports, etc.)
- ✅ **AWS SSO** configured and authenticated
- ✅ **Bedrock models** tested (10/10 agents working with Nova Premier)

### 2. Architecture Documentation

- ✅ **[AWS_BEDROCK_AGENTS_ARCHITECTURE.md](AWS_BEDROCK_AGENTS_ARCHITECTURE.md)** - Complete agent architecture
- ✅ **[SYSTEM_TEST_RESULTS.md](SYSTEM_TEST_RESULTS.md)** - System test results
- ✅ **Terraform infrastructure templates** - Infrastructure as Code

### 3. Model Configuration

Current configuration (all agents using Amazon Nova Premier):
```
- orchestrator
- arbitrator
- crew_compliance_agent
- maintenance_agent
- regulatory_agent
- network_agent
- guest_experience_agent
- cargo_agent
- finance_agent
- execution_agent
```

---

## 🚀 AWS Cloud Deployment Steps

### Prerequisites

1. **AWS Account Setup**
   - AWS Account ID: 368613657554
   - SSO Configured: ✅
   - IAM Role: AWSAdministratorAccess
   - Region: us-east-1

2. **Required Tools**
   ```bash
   # Terraform
   brew install terraform

   # AWS CLI (already installed)
   aws --version

   # Authenticate
   aws sso login
   ```

3. **Submit Claude Use Case Form** (Optional but Recommended)
   - URL: https://pages.awscloud.com/GLOBAL-ln-GC-Bedrock-3pmodel-interest-form-2024.html
   - Purpose: Enable Claude models for better reasoning
   - Approval time: 15 minutes - few hours

---

## Step 1: Prepare Terraform State Backend

```bash
# Create S3 bucket for Terraform state
aws s3 mb s3://skymarshal-terraform-state --region us-east-1
aws s3api put-bucket-versioning \
  --bucket skymarshal-terraform-state \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name skymarshal-terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

---

## Step 2: Configure Terraform Variables

Create `terraform/environments/prod/terraform.tfvars`:

```hcl
# Environment
environment = "prod"
aws_region  = "us-east-1"

# Network
vpc_cidr         = "10.0.0.0/16"
private_subnets  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
public_subnets   = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
database_subnets = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]

# RDS
rds_instance_class   = "db.r6g.xlarge"
rds_allocated_storage = 500
rds_multi_az         = true
rds_backup_retention = 7

# OpenSearch
opensearch_instance_type  = "r6g.xlarge.search"
opensearch_instance_count = 3
opensearch_ebs_volume_size = 500

# Monitoring
alarm_email = "your-team@etihad.ae"
```

---

## Step 3: Deploy Infrastructure

```bash
cd terraform

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var-file=environments/prod/terraform.tfvars

# Apply (create infrastructure)
terraform apply -var-file=environments/prod/terraform.tfvars

# Save outputs
terraform output > ../outputs.txt
```

**Expected Deployment Time**: 30-45 minutes

**Resources Created**:
- VPC with 3 AZs
- RDS PostgreSQL (Multi-AZ)
- OpenSearch cluster (3 nodes)
- S3 buckets (4)
- Lambda functions (5)
- Bedrock Agents (10)
- API Gateway
- CloudWatch dashboards and alarms

---

## Step 4: Load Database

```bash
# Get RDS endpoint from Terraform outputs
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# Get database credentials from Secrets Manager
SECRET_ARN=$(terraform output -raw rds_credentials_secret_arn)
aws secretsmanager get-secret-value --secret-id $SECRET_ARN

# Connect to RDS
psql -h $RDS_ENDPOINT -U skymarshal_admin -d etihad_aviation

# Load schema (already created by init script)
# Load data from CSV files
\copy flights FROM 'output/flights.csv' CSV HEADER;
\copy passengers FROM 'output/passengers.csv' CSV HEADER;
\copy bookings FROM 'output/bookings.csv' CSV HEADER;
\copy baggage FROM 'output/baggage.csv' CSV HEADER;
\copy cargo_shipments FROM 'output/cargo_shipments.csv' CSV HEADER;
\copy cargo_flight_assignments FROM 'output/cargo_flight_assignments.csv' CSV HEADER;
\copy crew_members FROM 'output/crew_members.csv' CSV HEADER;
\copy crew_roster FROM 'output/crew_roster.csv' CSV HEADER;
```

---

## Step 5: Upload Knowledge Base Documents

```bash
# Get S3 bucket name
KB_BUCKET=$(terraform output -json s3_bucket_names | jq -r '.knowledge_base')

# Upload regulation documents
aws s3 cp regulations/ s3://$KB_BUCKET/regulations/ --recursive
aws s3 cp procedures/ s3://$KB_BUCKET/procedures/ --recursive
aws s3 cp historical-cases/ s3://$KB_BUCKET/historical-cases/ --recursive

# Trigger knowledge base sync (via Bedrock console or CLI)
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <KB_ID> \
  --data-source-id <DS_ID>
```

---

## Step 6: Test Bedrock Agents

```bash
# Get orchestrator agent ID
AGENT_ID=$(terraform output -json bedrock_agent_ids | jq -r '.orchestrator')
AGENT_ALIAS=$(terraform output -raw orchestrator_agent_alias)

# Test agent invocation
aws bedrock-agent-runtime invoke-agent \
  --agent-id $AGENT_ID \
  --agent-alias-id $AGENT_ALIAS \
  --session-id test-session-1 \
  --input-text "Analyze flight delay scenario: EY123, 2-hour delay due to technical issue"
```

---

## Step 7: Test API Gateway

```bash
# Get API Gateway URL
API_URL=$(terraform output -raw api_gateway_url)

# Submit disruption scenario
curl -X POST "$API_URL/api/v1/disruptions" \
  -H "Content-Type: application/json" \
  -d '{
    "flight_number": "EY123",
    "disruption_type": "delay",
    "delay_minutes": 120,
    "reason": "technical_issue",
    "aircraft_type": "A380",
    "origin": "AUH",
    "destination": "LHR",
    "passengers_affected": 615
  }'

# Check status
curl "$API_URL/api/v1/disruptions/{disruption_id}"
```

---

## Architecture Components

### Deployed Resources

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **RDS PostgreSQL** | Operational database | db.r6g.xlarge, Multi-AZ, 500GB |
| **OpenSearch** | Vector embeddings (RAG) | 3-node cluster, r6g.xlarge |
| **S3** | Document storage, logs | 4 buckets (KMS encrypted) |
| **Lambda** | Agent action groups | Python 3.11, VPC-enabled |
| **Bedrock Agents** | AI agents (10 agents) | Nova Premier models |
| **API Gateway** | REST API | Regional, private VPC link |
| **CloudWatch** | Monitoring & alarms | Dashboards + alarms |

---

## Cost Breakdown

### Monthly Costs (Production)

```
RDS PostgreSQL (db.r6g.xlarge, Multi-AZ):    $700
OpenSearch (3 × r6g.xlarge.search):           $1,200
Bedrock Agents (10 agents):                   $1,500
Bedrock Models (Nova Premier):                $500
Lambda (100K invocations):                    $20
S3 (1TB + requests):                          $50
API Gateway (1M requests):                    $10
CloudWatch (logs + metrics):                  $100
Data Transfer (500GB):                        $45
────────────────────────────────────────────
Total:                                        ~$4,125/month

Per-disruption cost:                          ~$0.50
```

---

## Monitoring & Operations

### CloudWatch Dashboards

1. **System Health**: `skymarshal-prod-system-health`
   - RDS connections & performance
   - OpenSearch cluster status
   - Lambda execution metrics

2. **Agent Performance**: `skymarshal-prod-agents`
   - Invocation counts per agent
   - Response latency (P50, P95, P99)
   - Error rates

3. **Business Metrics**: `skymarshal-prod-business`
   - Disruptions processed
   - Decision accuracy
   - Cost per disruption

### Alarms

```bash
# View active alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix "skymarshal-prod"

# Key alarms:
- high-error-rate (>5%)
- high-latency (P99 >30s)
- database-connections-low (<10 available)
- opensearch-cluster-red
```

---

## Security

### IAM Roles Created

- `skymarshal-bedrock-agent-role` - For Bedrock Agents
- `skymarshal-lambda-execution-role` - For Lambda functions
- `skymarshal-rds-access-role` - For database access

### Encryption

- **RDS**: Encrypted at rest with AWS KMS
- **S3**: SSE-KMS encryption
- **OpenSearch**: Node-to-node encryption
- **Secrets Manager**: Database credentials

### Network Security

- **Private subnets**: Lambda, RDS, OpenSearch
- **Security groups**: Least privilege access
- **VPC endpoints**: S3, Bedrock (no internet traffic)

---

## Disaster Recovery

### Backup Strategy

1. **RDS Automated Backups**
   - Retention: 7 days
   - Backup window: 03:00-04:00 UTC
   - Point-in-time recovery enabled

2. **S3 Versioning**
   - Enabled on all buckets
   - Lifecycle policies for cost optimization

3. **Manual Snapshots**
   ```bash
   # Create RDS snapshot
   aws rds create-db-snapshot \
     --db-instance-identifier skymarshal-prod \
     --db-snapshot-identifier skymarshal-manual-$(date +%Y%m%d)
   ```

### Recovery Procedures

**RDS Recovery**:
```bash
# Restore from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier skymarshal-prod-restored \
  --db-snapshot-identifier <snapshot-id>
```

**OpenSearch Recovery**:
```bash
# Restore from automated snapshot
aws opensearch restore-domain \
  --domain-name skymarshal-prod \
  --snapshot-name <snapshot-name>
```

---

## Scaling Considerations

### Vertical Scaling

**RDS**: Modify instance class
```bash
aws rds modify-db-instance \
  --db-instance-identifier skymarshal-prod \
  --db-instance-class db.r6g.2xlarge \
  --apply-immediately
```

**OpenSearch**: Add nodes
```bash
aws opensearch update-domain-config \
  --domain-name skymarshal-prod \
  --instance-count 5
```

### Horizontal Scaling

- **Lambda**: Auto-scales automatically
- **Bedrock Agents**: Pay-per-use, infinite scale
- **API Gateway**: Auto-scales

---

## Troubleshooting

### Common Issues

**1. Agent Timeout**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/skymarshal-prod-crew-ftl-check --follow

# Increase timeout in Terraform
```

**2. OpenSearch Cluster Red**
```bash
# Check cluster health
aws opensearch describe-domain --domain-name skymarshal-prod

# View cluster logs
aws logs tail /aws/opensearch/skymarshal-prod
```

**3. High RDS Connections**
```bash
# Check current connections
psql -h $RDS_ENDPOINT -c "SELECT count(*) FROM pg_stat_activity;"

# Increase max_connections in parameter group
```

---

## Next Steps

1. ✅ **Infrastructure Deployed**
2. ⏳ **Load Production Data** - Import real flight data
3. ⏳ **Train Agents** - Fine-tune prompts based on testing
4. ⏳ **Submit Claude Form** - Enable Claude models
5. ⏳ **Performance Testing** - Load testing with realistic scenarios
6. ⏳ **UAT** - User acceptance testing with operations team
7. ⏳ **Go Live** - Production cutover

---

## Support & Documentation

- **Architecture**: [AWS_BEDROCK_AGENTS_ARCHITECTURE.md](AWS_BEDROCK_AGENTS_ARCHITECTURE.md)
- **Test Results**: [SYSTEM_TEST_RESULTS.md](SYSTEM_TEST_RESULTS.md)
- **Terraform Docs**: `terraform/README.md`
- **AWS Support**: AWS Premium Support plan recommended

---

**Document Version**: 1.0
**Last Updated**: 2026-01-30
**Deployment Status**: Ready for Production
