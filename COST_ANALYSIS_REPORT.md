# SkyMarshal Unit Economics & Cost Analysis
## Claude vs Gemini 3 — Full Comparison Report
**Date**: February 6, 2026 | **Project**: SkyMarshal Multi-Agent Airline Disruption Management

---

## Context

SkyMarshal is a multi-agent airline disruption management system that uses 9 specialized LLM agents orchestrated via LangGraph on AWS Bedrock. This analysis covers the full cost structure: LLM token consumption, AWS infrastructure, and sustainability — comparing Claude (current) vs Gemini 3 (alternative).

---

## 1. LLM Model Costs Per Invocation

### Models Used & Pricing (AWS Bedrock, as of Jan 2026)

| Model | Used By | Input $/1M tokens | Output $/1M tokens |
|-------|---------|-------------------|-------------------|
| **Claude Sonnet 4.5** (Global CRIS) | Safety agents (3), Orchestrator, Arbitrator fallback | ~$3 | ~$15 |
| **Claude Haiku 4.5** (Global CRIS) | Business agents (4), Execution | ~$0.80 | ~$4 |
| **Claude Opus 4.5** (US region) | Arbitrator (primary) | ~$15 | ~$75 |
| **Amazon Titan Embed v2** | Knowledge Base embeddings | ~$0.02 | N/A |

### Token Consumption Per Disruption Analysis (Single Run)

The system executes in 3 phases per disruption:

#### Phase 1: Initial Agent Analysis (7 agents in parallel)

| Agent | Model | Est. Input Tokens | Est. Output Tokens | Est. Cost |
|-------|-------|------------------|-------------------|-----------|
| Crew Compliance | Sonnet 4.5 | ~3,000 | ~2,000 | $0.039 |
| Maintenance | Sonnet 4.5 | ~3,000 | ~2,000 | $0.039 |
| Regulatory | Sonnet 4.5 | ~3,000 | ~2,000 | $0.039 |
| Network | Haiku 4.5 | ~2,500 | ~1,500 | $0.008 |
| Guest Experience | Haiku 4.5 | ~2,500 | ~1,500 | $0.008 |
| Cargo | Haiku 4.5 | ~2,500 | ~1,500 | $0.008 |
| Finance | Haiku 4.5 | ~2,500 | ~1,500 | $0.008 |
| **Phase 1 Subtotal** | | **~19,000** | **~12,000** | **~$0.149** |

#### Phase 2: Revision (7 agents review other agents' output)

Phase 2 includes augmented prompts with all Phase 1 responses, increasing input tokens.

| Agent | Model | Est. Input Tokens | Est. Output Tokens | Est. Cost |
|-------|-------|------------------|-------------------|-----------|
| Safety agents (3) | Sonnet 4.5 | ~5,000 each | ~2,500 each | $0.053 each |
| Business agents (4) | Haiku 4.5 | ~4,000 each | ~1,500 each | $0.009 each |
| **Phase 2 Subtotal** | | **~31,000** | **~15,500** | **~$0.195** |

#### Phase 3: Arbitration (single agent, most expensive)

| Component | Model | Est. Input Tokens | Est. Output Tokens | Est. Cost |
|-----------|-------|------------------|-------------------|-----------|
| Arbitrator (Opus) | Opus 4.5 | ~8,000-12,000 | ~4,000-6,000 | **$0.48-$0.63** |
| Arbitrator (Sonnet fallback) | Sonnet 4.5 | ~8,000-12,000 | ~4,000-6,000 | $0.084-$0.126 |
| KB Query (embedding) | Titan Embed v2 | ~500 | N/A | $0.00001 |

#### Total LLM Cost Per Disruption Analysis

| Scenario | Phase 1 | Phase 2 | Phase 3 | **Total** |
|----------|---------|---------|---------|-----------|
| **With Opus Arbitrator** | $0.15 | $0.20 | $0.55 | **$0.90** |
| **With Sonnet Arbitrator** | $0.15 | $0.20 | $0.10 | **$0.45** |
| **Best case (optimized)** | $0.10 | $0.13 | $0.07 | **$0.30** |
| **Worst case (complex)** | $0.20 | $0.25 | $0.63 | **$1.08** |

**Key insight**: The Arbitrator (Phase 3) accounts for **50-60% of total LLM cost** when using Opus 4.5, but only ~22% when using the Sonnet fallback.

---

## 2. Token Budget Summary

### Total Tokens Per Disruption

| Phase | Input Tokens | Output Tokens | Total Tokens |
|-------|-------------|---------------|-------------|
| Phase 1 | ~19,000 | ~12,000 | ~31,000 |
| Phase 2 | ~31,000 | ~15,500 | ~46,500 |
| Phase 3 | ~10,000 | ~5,000 | ~15,000 |
| **TOTAL** | **~60,000** | **~32,500** | **~92,500** |

### Token Configuration Per Agent

| Agent Type | max_tokens | temperature | Model |
|------------|-----------|-------------|-------|
| Safety agents | 8,192 | 0.3 | Sonnet 4.5 |
| Business agents | 4,096 | 0.3 | Haiku 4.5 |
| Orchestrator | 8,192 | 0.3 | Sonnet 4.5 |
| Arbitrator (Opus) | 16,384 | 0.1 | Opus 4.5 |
| Arbitrator (Sonnet fallback) | 12,000 | 0.1 | Sonnet 4.5 |

### Arbitrator Token Breakdown (4,072 input tokens to the LLM prompt itself)

| Component | Tokens | % of Prompt |
|-----------|--------|-------------|
| System Prompt | 1,150 | 28.2% |
| Knowledge Base Context | 1,050 | 25.8% |
| Phase Comparison | 829 | 20.4% |
| Agent Responses | 843 | 20.7% |
| Structure/Formatting | 200 | 4.9% |

---

## 3. AWS Infrastructure Costs (Monthly)

### Compute & Serverless

| Service | Configuration | Est. Monthly Cost |
|---------|--------------|------------------|
| **API Gateway** | REST API (dev stage) | ~$3.50/million requests |
| **Lambda** (if used) | Per-invocation | ~$0.20/million requests |
| **DynamoDB** (16+ tables) | PAY_PER_REQUEST | ~$1.25/million writes, $0.25/million reads |
| **DynamoDB** (agent memory) | PAY_PER_REQUEST + TTL 90d | Variable, ~$5-20/month |

### Storage

| Service | Configuration | Est. Monthly Cost |
|---------|--------------|------------------|
| **S3** (4 buckets) | Versioning, encryption, 90d lifecycle on logs | ~$0.023/GB/month |
| **RDS PostgreSQL** | db.t4g.micro, 20GB gp3, encrypted | ~$13-15/month (free tier eligible) |
| **Secrets Manager** | 1 secret (DB password) | ~$0.40/month |

### AI/ML Services

| Service | Configuration | Est. Monthly Cost |
|---------|--------------|------------------|
| **OpenSearch Serverless** | Vector search collection | ~$175-350/month (2 OCUs minimum) |
| **Bedrock Knowledge Base** | Titan Embed v2, 512-token chunks | ~$0.02/million tokens embedded |
| **Bedrock Model Invocations** | See LLM costs above | Variable (usage-based) |

### Monitoring & Logging

| Service | Configuration | Est. Monthly Cost |
|---------|--------------|------------------|
| **CloudWatch Logs** | 2 log groups, 30d retention | ~$0.50/GB ingested |
| **CloudWatch Alarms** | 3 RDS alarms | ~$0.30/alarm = $0.90 |
| **RDS Performance Insights** | 7-day retention (free tier) | $0 |
| **RDS Enhanced Monitoring** | 60s interval | ~$0 (free tier) |

### Infrastructure Cost Summary (Monthly)

| Category | Low Estimate | High Estimate |
|----------|-------------|---------------|
| RDS (db.t4g.micro) | $0 (free tier) | $15 |
| OpenSearch Serverless | $175 | $350 |
| DynamoDB (all tables) | $5 | $50 |
| S3 (all buckets) | $1 | $5 |
| CloudWatch + Monitoring | $2 | $10 |
| Secrets Manager | $0.40 | $0.40 |
| API Gateway | $0 | $10 |
| **Infrastructure Subtotal** | **~$183** | **~$440** |

**Note**: OpenSearch Serverless is the dominant fixed infrastructure cost at $175-350/month (minimum 2 OCUs). This is the largest line item regardless of usage volume.

---

## 4. Unit Economics at Scale

### Cost Per Disruption Analysis (All-In)

| Volume (analyses/month) | LLM Cost | Infra Cost (amortized) | **Total Per Analysis** |
|------------------------|----------|----------------------|----------------------|
| 10 | $9 | $25 | **$34.00** |
| 50 | $45 | $5 | **$5.90** |
| 100 | $90 | $2.50 | **$3.40** |
| 500 | $450 | $0.50 | **$1.40** |
| 1,000 | $900 | $0.25 | **$1.15** |
| 5,000 | $4,500 | $0.05 | **$0.95** |

*Assumes $0.90/analysis with Opus arbitrator, infrastructure at ~$250/month average*

### Break-Even Analysis

The value SkyMarshal provides per disruption:
- **Average disruption cost avoided**: $15,000 - $258,000 (from sample data)
- **Cheapest recovery (aircraft swap)**: $15,000
- **Most expensive (cancellation)**: $258,000
- **SkyMarshal cost per analysis**: $0.45 - $1.08

**ROI**: Even at the worst-case LLM cost ($1.08), the system needs to improve disruption recovery by just **0.007%** (7 basis points) on a $15,000 disruption to break even on the LLM cost alone.

### Disruption Cost Categories (from operational data)

| Cost Item | Per-Unit Cost | Notes |
|-----------|-------------|-------|
| EU261 compensation (long-haul) | $600/passenger | Mandatory for >3h delay |
| Hotel accommodation | $180/passenger/night | Stranded passengers |
| Meal vouchers | $25/passenger/meal | Per meal period |
| OAL rebooking (business) | $2,500/passenger | Other airline |
| OAL rebooking (economy) | $800/passenger | Other airline |
| Crew overtime | $75/hour/crew member | Extended duty |
| Aircraft swap logistics | $5,000-15,000/swap | Operational coordination |
| LHR slot miss penalty | $75,000/occurrence | Airport-specific |
| NPS impact | $5,000/point | Brand damage |
| VIP/Influencer impact | $50,000/occurrence | Reputation risk |

---

## 5. Execution Time & Performance Economics

### Current Performance Baseline

| Phase | Duration | % of Total | Bottleneck |
|-------|----------|-----------|------------|
| Phase 1 (7 agents parallel) | 29-47s | 18-29% | Slowest agent |
| Phase 2 (revision) | 21-60s | 13-37% | Augmented prompts |
| Phase 3 (arbitration) | 49-109s | 31-68% | **LLM generation** |
| **Total** | **99-162s** | | |

### Arbitration Bottleneck Breakdown (109s)

| Component | Time | % | Driver |
|-----------|------|---|--------|
| LLM token generation | 80-90s | 73-83% | Output ~5,000 tokens at ~30-40 tok/s |
| Knowledge Base query | 5-15s | 5-14% | Vector search + network |
| Phase evolution analysis | 2-5s | 2-5% | Text comparison |
| Prompt construction | 1-2s | 1-2% | String formatting |
| Overhead (checkpoints) | 5-10s | 5-9% | I/O |

### Token Generation Speed by Model

| Model | Speed (tokens/sec) | Time for 5,000 output tokens |
|-------|-------------------|------------------------------|
| Claude Opus 4.5 | ~15-25 | ~200-333s |
| Claude Sonnet 4.5 | ~30-40 | ~125-167s |
| Claude Haiku 4.5 | ~100-120 | ~42-50s |

---

## 6. Cost Optimization Levers (Identified in Codebase)

### Already Implemented
1. **Tiered model strategy**: Sonnet for safety, Haiku for business (~50% cost reduction on business agents)
2. **Global CRIS endpoints**: Better availability, reduced throttling
3. **Skip model testing on startup**: -5-10s cold start
4. **Increased Phase 2 timeout**: 90s prevents premature failures
5. **Compact arbitrator prompt format**: Pipe-delimited for token efficiency

### Documented but Not Yet Implemented
1. **Input token reduction** (41% reduction, ~1,672 tokens saved on arbitrator)
   - Compress reasoning text: -401 tokens
   - Reduce KB documents 5->3: -420 tokens
   - Simplify phase comparison: -414 tokens
   - Compress system prompt: -345 tokens
   - Skip inactive agents: -33 tokens

2. **Haiku for simple arbitration**: When all agents agree, use Haiku instead of Opus/Sonnet (3-4x faster, ~85% cheaper)

3. **Simplified output schema for emergencies**: Single solution instead of 1-3 (reduces output tokens ~60%)

4. **Parallel KB query + LLM invocation**: Save 5-10s

5. **KB result caching**: Save 5-15s on cache hits

---

## 7. Sustainability Analysis

### Energy & Carbon Considerations

| Factor | Current State | Notes |
|--------|-------------|-------|
| **Region** | us-east-1 (Virginia) + eu-west-1 (Ireland) | Both regions have significant renewable energy commitments |
| **Total tokens per analysis** | ~92,500 | Moderate for a 9-agent system |
| **Compute time per analysis** | 99-162 seconds | Relatively high; optimization could reduce by 50-77% |
| **Model efficiency hierarchy** | Haiku >> Sonnet >> Opus | Haiku uses ~10x less compute than Opus for similar tasks |

### Sustainability Improvement Opportunities

1. **Shift more workload to Haiku 4.5**: Currently 4 agents use Haiku; if simple arbitrations also used Haiku, ~70% of compute shifts to the most efficient model.
2. **Reduce total token consumption**: The 41% input reduction guide would cut ~38,000 tokens per analysis across all phases.
3. **Early termination for data-unavailable scenarios**: Skip Phase 2+3 when flight data isn't found (saves ~60,000 tokens and 100s of compute).
4. **Caching for repeated disruption types**: Similar disruptions (e.g., weather delays at same airport) could reuse KB results and partial agent outputs.
5. **Right-size the Opus usage**: Opus is 10-15x more expensive and slower than Sonnet.

### Infrastructure Sustainability

| Resource | Concern | Mitigation |
|----------|---------|------------|
| OpenSearch Serverless | Always-on (2 OCUs minimum) | Consider scheduled scaling or Bedrock's built-in vector store |
| RDS db.t4g.micro | ARM-based (Graviton) - efficient | Good choice for sustainability |
| DynamoDB PAY_PER_REQUEST | Scales to zero | Sustainable for variable loads |
| S3 with lifecycle policies | 90-day auto-delete on logs | Prevents storage bloat |

---

## 8. Key Numbers Summary

| Metric | Value |
|--------|-------|
| **Cost per disruption analysis (Opus arbitrator)** | ~$0.90 |
| **Cost per disruption analysis (Sonnet arbitrator)** | ~$0.45 |
| **Total tokens per analysis** | ~92,500 |
| **Execution time** | 99-162 seconds |
| **Monthly infrastructure (fixed)** | ~$183-440 |
| **Dominant fixed cost** | OpenSearch Serverless ($175-350/mo) |
| **Dominant variable cost** | Arbitrator LLM (50-60% of LLM spend) |
| **Break-even improvement needed** | 0.007% on a $15K disruption |
| **Models in active use** | 3 (Sonnet 4.5, Haiku 4.5, Opus 4.5) |
| **Agents per analysis** | 9 (3 safety + 4 business + 1 orchestrator + 1 arbitrator) |
| **Potential cost reduction** | 40-60% via documented optimizations |
| **Potential time reduction** | 50-77% (target: 40-50s from 159s) |

---

## 9. Recommendations

1. **Implement the input token reduction guide** - 41% fewer arbitrator input tokens for ~$0.15-0.20 savings per analysis
2. **Use Sonnet as default arbitrator** instead of Opus - cuts Phase 3 cost by ~80%
3. **Evaluate OpenSearch Serverless alternatives** - at $175-350/month, this is the largest fixed cost
4. **Add token/cost tracking** - the codebase has `ENABLE_COST_TRACKING=true` but no actual token counting implementation
5. **Implement early termination** - skip Phase 2+3 when data is unavailable to avoid wasting ~$0.65 per failed lookup

---

## 10. Gemini 3 Migration: Cost Comparison

### Gemini 3 Model Pricing (as of Feb 2026)

| Model | Input $/1M tokens | Output $/1M tokens | Notes |
|-------|-------------------|-------------------|-------|
| **Gemini 3 Pro** (<=200K ctx) | $2.00 | $12.00 | Frontier reasoning, 1M context window |
| **Gemini 3 Pro** (>200K ctx) | $4.00 | $18.00 | 2x pricing for long context |
| **Gemini 3 Flash** | $0.50 | $3.00 | 3x faster than Pro, strong quality |
| Gemini 2.5 Pro | $1.25 | $10.00 | Previous gen, still available |
| Gemini 2.5 Flash | $0.30 | $2.50 | Budget option |
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 | Ultra-budget |

### Model Mapping: Claude -> Gemini

| SkyMarshal Role | Current (Claude) | Gemini Equivalent | Rationale |
|----------------|-----------------|-------------------|-----------|
| Safety agents (3) | Sonnet 4.5 ($3/$15) | **Gemini 3 Pro** ($2/$12) | Safety-critical needs frontier reasoning |
| Business agents (4) | Haiku 4.5 ($0.80/$4) | **Gemini 3 Flash** ($0.50/$3) | Speed + cost optimized |
| Orchestrator | Sonnet 4.5 ($3/$15) | Gemini 3 Pro ($2/$12) | Workflow coordination |
| Arbitrator | Opus 4.5 ($15/$75) | **Gemini 3 Pro** ($2/$12) | Biggest savings - no Opus-tier needed |

### Scenario A: Tiered Gemini (Pro + Flash) -- Recommended

#### Phase 1: Initial Agent Analysis

| Agent | Model | Input Tokens | Output Tokens | Cost |
|-------|-------|-------------|--------------|------|
| Crew Compliance | Gemini 3 Pro | ~3,000 | ~2,000 | $0.030 |
| Maintenance | Gemini 3 Pro | ~3,000 | ~2,000 | $0.030 |
| Regulatory | Gemini 3 Pro | ~3,000 | ~2,000 | $0.030 |
| Network | Gemini 3 Flash | ~2,500 | ~1,500 | $0.006 |
| Guest Experience | Gemini 3 Flash | ~2,500 | ~1,500 | $0.006 |
| Cargo | Gemini 3 Flash | ~2,500 | ~1,500 | $0.006 |
| Finance | Gemini 3 Flash | ~2,500 | ~1,500 | $0.006 |
| **Phase 1 Subtotal** | | **~19,000** | **~12,000** | **$0.114** |

#### Phase 2: Revision

| Agent | Model | Input Tokens | Output Tokens | Cost |
|-------|-------|-------------|--------------|------|
| Safety agents (3) | Gemini 3 Pro | ~5,000 each | ~2,500 each | $0.040 each |
| Business agents (4) | Gemini 3 Flash | ~4,000 each | ~1,500 each | $0.007 each |
| **Phase 2 Subtotal** | | **~31,000** | **~15,500** | **$0.148** |

#### Phase 3: Arbitration

| Component | Model | Input Tokens | Output Tokens | Cost |
|-----------|-------|-------------|--------------|------|
| Arbitrator | Gemini 3 Pro | ~10,000 | ~5,000 | **$0.080** |

#### Tiered Gemini Total

| Phase | Claude (Opus arb.) | Claude (Sonnet arb.) | **Gemini Tiered** | Savings vs Opus | Savings vs Sonnet |
|-------|-------------------|---------------------|-------------------|-----------------|-------------------|
| Phase 1 | $0.149 | $0.149 | **$0.114** | 24% | 24% |
| Phase 2 | $0.195 | $0.195 | **$0.148** | 24% | 24% |
| Phase 3 | $0.525 | $0.105 | **$0.080** | 85% | 24% |
| **TOTAL** | **$0.87** | **$0.45** | **$0.34** | **61%** | **24%** |

### Scenario B: All Gemini 3 Pro

| Phase | Cost | vs Claude (Opus) | vs Claude (Sonnet) |
|-------|------|-----------------|-------------------|
| Phase 1 | $0.182 | -22% | +22% (Pro costs more than Haiku) |
| Phase 2 | $0.224 | -15% | +15% |
| Phase 3 | $0.080 | -85% | -24% |
| **TOTAL** | **$0.49** | **-44%** | **+9%** |

### Scenario C: All Gemini 3 Flash

| Phase | Cost | vs Claude (Opus) | vs Claude (Sonnet) |
|-------|------|-----------------|-------------------|
| Phase 1 | $0.046 | -69% | -69% |
| Phase 2 | $0.056 | -71% | -71% |
| Phase 3 | $0.020 | -96% | -81% |
| **TOTAL** | **$0.12** | **-86%** | **-73%** |

### Hybrid Architecture Option

| Role | Model | Cost | Rationale |
|------|-------|------|-----------|
| Safety agents (3) | Claude Sonnet 4.5 | $0.039 each | Proven reliability on safety |
| Business agents (4) | Gemini 3 Flash | $0.006 each | 25% cheaper than Haiku |
| Arbitrator | Gemini 3 Pro | $0.080 | 85% cheaper than Opus |
| **Total** | Mixed | **$0.22** | Best of both worlds |

---

## 11. Unified Cost Breakdown: Claude vs Gemini (Complete Comparison)

### A. Model Pricing -- Head-to-Head

| Tier | Claude Model | Claude In/Out ($/1M) | Gemini Model | Gemini In/Out ($/1M) | Gemini Savings |
|------|-------------|---------------------|-------------|---------------------|---------------|
| **Frontier** | Opus 4.5 | $15 / $75 | Gemini 3 Pro | $2 / $12 | **87% in, 84% out** |
| **Mid-tier** | Sonnet 4.5 | $3 / $15 | Gemini 3 Pro | $2 / $12 | 33% in, 20% out |
| **Fast/Cheap** | Haiku 4.5 | $0.80 / $4 | Gemini 3 Flash | $0.50 / $3 | 38% in, 25% out |
| **Budget** | -- | -- | Gemini 2.5 Flash-Lite | $0.10 / $0.40 | N/A (no Claude equivalent) |
| **Embeddings** | Titan Embed v2 | $0.02 / -- | Gecko Embed | $0.025 / -- | Comparable |

### B. Per-Agent Cost Comparison (Single Invocation)

| Agent | Role | Claude Model | Claude Cost | Gemini Model | Gemini Cost | Saving |
|-------|------|-------------|------------|-------------|------------|--------|
| Crew Compliance | Safety | Sonnet 4.5 | $0.039 | Gemini 3 Pro | $0.030 | 23% |
| Maintenance | Safety | Sonnet 4.5 | $0.039 | Gemini 3 Pro | $0.030 | 23% |
| Regulatory | Safety | Sonnet 4.5 | $0.039 | Gemini 3 Pro | $0.030 | 23% |
| Network | Business | Haiku 4.5 | $0.008 | Gemini 3 Flash | $0.006 | 25% |
| Guest Experience | Business | Haiku 4.5 | $0.008 | Gemini 3 Flash | $0.006 | 25% |
| Cargo | Business | Haiku 4.5 | $0.008 | Gemini 3 Flash | $0.006 | 25% |
| Finance | Business | Haiku 4.5 | $0.008 | Gemini 3 Flash | $0.006 | 25% |
| Orchestrator | Coord. | Sonnet 4.5 | $0.039 | Gemini 3 Pro | $0.030 | 23% |
| **Arbitrator** | Decision | **Opus 4.5** | **$0.525** | **Gemini 3 Pro** | **$0.080** | **85%** |

### C. Full Pipeline Cost -- All Scenarios

| # | Scenario | Phase 1 | Phase 2 | Phase 3 | **LLM Total** | vs Baseline |
|---|----------|---------|---------|---------|-------------|-------------|
| 1 | **Claude Tiered + Opus Arb.** (current) | $0.149 | $0.195 | $0.525 | **$0.87** | -- |
| 2 | Claude Tiered + Sonnet Arb. | $0.149 | $0.195 | $0.105 | **$0.45** | -48% |
| 3 | Claude (optimized tokens) | $0.100 | $0.130 | $0.070 | **$0.30** | -66% |
| 4 | **Gemini Tiered (Pro+Flash)** | $0.114 | $0.148 | $0.080 | **$0.34** | -61% |
| 5 | Gemini All-Pro | $0.182 | $0.224 | $0.080 | **$0.49** | -44% |
| 6 | Gemini All-Flash | $0.046 | $0.056 | $0.020 | **$0.12** | -86% |
| 7 | **Hybrid** (Claude safety + Gemini biz/arb) | $0.114 | $0.148 | $0.080 | **$0.34** | -61% |

### D. Infrastructure Costs -- Claude (AWS) vs Gemini (GCP/Hybrid)

#### Option 1: Keep Full AWS Stack (LLM-only migration to Gemini)

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| OpenSearch Serverless | $175-350 | Still needed for Bedrock KB |
| RDS PostgreSQL (db.t4g.micro) | $0-15 | Free tier eligible |
| DynamoDB (16+ tables) | $5-50 | PAY_PER_REQUEST |
| S3 (4 buckets) | $1-5 | Minimal storage |
| CloudWatch + Monitoring | $2-10 | Logging |
| API Gateway | $0-10 | REST API |
| Secrets Manager | $0.40 | DB password |
| **Infrastructure Total** | **$183-440** | **Same as current** |

#### Option 2: Full GCP Migration (replace AWS entirely)

| AWS Service | GCP Equivalent | GCP Monthly Cost | Savings |
|------------|---------------|-----------------|---------|
| OpenSearch Serverless ($175-350) | Vertex AI Search or Cloud SQL + pgvector | $0-10 | **-$175 to -$350** |
| RDS PostgreSQL ($0-15) | Cloud SQL Micro ($7-10) | $7-10 | Comparable |
| DynamoDB ($5-50) | Firestore ($5-40) | $5-40 | Comparable |
| S3 ($1-5) | Cloud Storage ($1-5) | $1-5 | Same |
| CloudWatch ($2-10) | Cloud Logging ($2-10) | $2-10 | Same |
| API Gateway ($0-10) | Cloud Run + API Gateway ($0-10) | $0-10 | Same |
| Bedrock KB ($0.02/1M embed) | Vertex AI Embeddings | $0.025/1M | Same |
| **Infrastructure Total** | | **$15-80** | **$100-360 saved** |

### E. Total Cost of Ownership (Monthly)

#### At 100 analyses/month

| Scenario | LLM Cost | Infrastructure | **Total Monthly** | **Per Analysis** |
|----------|----------|---------------|------------------|-----------------|
| Claude+Opus (current, AWS) | $87 | $250 | **$337** | **$3.37** |
| Claude+Sonnet (AWS) | $45 | $250 | **$295** | **$2.95** |
| Gemini Tiered (keep AWS infra) | $34 | $250 | **$284** | **$2.84** |
| **Gemini Tiered (full GCP)** | **$34** | **$50** | **$84** | **$0.84** |
| **Gemini Flash (full GCP)** | **$12** | **$50** | **$62** | **$0.62** |
| Hybrid Claude+Gemini (AWS) | $34 | $250 | **$284** | **$2.84** |

#### At 500 analyses/month

| Scenario | LLM Cost | Infrastructure | **Total Monthly** | **Per Analysis** |
|----------|----------|---------------|------------------|-----------------|
| Claude+Opus (current, AWS) | $435 | $250 | **$685** | **$1.37** |
| Claude+Sonnet (AWS) | $225 | $250 | **$475** | **$0.95** |
| Gemini Tiered (keep AWS infra) | $170 | $250 | **$420** | **$0.84** |
| **Gemini Tiered (full GCP)** | **$170** | **$50** | **$220** | **$0.44** |
| **Gemini Flash (full GCP)** | **$60** | **$50** | **$110** | **$0.22** |
| Hybrid Claude+Gemini (AWS) | $170 | $250 | **$420** | **$0.84** |

#### At 1,000 analyses/month

| Scenario | LLM Cost | Infrastructure | **Total Monthly** | **Per Analysis** |
|----------|----------|---------------|------------------|-----------------|
| Claude+Opus (current, AWS) | $870 | $250 | **$1,120** | **$1.12** |
| Claude+Sonnet (AWS) | $450 | $250 | **$700** | **$0.70** |
| Gemini Tiered (keep AWS infra) | $340 | $250 | **$590** | **$0.59** |
| **Gemini Tiered (full GCP)** | **$340** | **$50** | **$390** | **$0.39** |
| **Gemini Flash (full GCP)** | **$120** | **$50** | **$170** | **$0.17** |

#### At 5,000 analyses/month

| Scenario | LLM Cost | Infrastructure | **Total Monthly** | **Per Analysis** |
|----------|----------|---------------|------------------|-----------------|
| Claude+Opus (current, AWS) | $4,350 | $300 | **$4,650** | **$0.93** |
| Claude+Sonnet (AWS) | $2,250 | $300 | **$2,550** | **$0.51** |
| Gemini Tiered (keep AWS infra) | $1,700 | $300 | **$2,000** | **$0.40** |
| **Gemini Tiered (full GCP)** | **$1,700** | **$75** | **$1,775** | **$0.36** |
| **Gemini Flash (full GCP)** | **$600** | **$75** | **$675** | **$0.14** |

### F. Annual Cost Projections

| Scenario | 100/mo | 500/mo | 1,000/mo | 5,000/mo |
|----------|--------|--------|----------|----------|
| **Claude+Opus (current)** | **$4,044** | **$8,220** | **$13,440** | **$55,800** |
| Claude+Sonnet | $3,540 | $5,700 | $8,400 | $30,600 |
| Gemini Tiered (AWS infra) | $3,408 | $5,040 | $7,080 | $24,000 |
| **Gemini Tiered (full GCP)** | **$1,008** | **$2,640** | **$4,680** | **$21,300** |
| **Gemini Flash (full GCP)** | **$744** | **$1,320** | **$2,040** | **$8,100** |

### G. Execution Speed Comparison

| Model | Est. Speed (tok/s) | Phase 1 (parallel) | Phase 3 (arbitrator) | Total Est. |
|-------|-------------------|-------------------|---------------------|-----------|
| Claude Opus 4.5 | ~15-25 | 29-47s | 109s | **138-156s** |
| Claude Sonnet 4.5 | ~30-40 | 29-47s | 49-80s | **78-127s** |
| Claude Haiku 4.5 | ~100-120 | 15-20s | N/A | -- |
| **Gemini 3 Pro** | ~50-80 | 20-30s | 40-60s | **60-90s** |
| **Gemini 3 Flash** | ~150-200 | 10-15s | 20-30s | **30-45s** |

### H. Feature & Capability Comparison

| Capability | Claude (Bedrock) | Gemini 3 (Vertex AI / API) |
|-----------|-----------------|---------------------------|
| **Context window** | 200K tokens | **1M tokens** (5x larger) |
| **Structured output** | Excellent (best instruction-following) | Good (needs precise prompts) |
| **Tool calling** | Excellent (LangChain native) | Good (LangChain native) |
| **Coding/SWE-bench** | **80.9%** (Opus 4.5) | 74.2% (Gemini 3 Pro) |
| **Multimodal** | Text + images | **Text + images + video + audio** |
| **Batch API** | Not available on Bedrock | **50% discount** |
| **Context caching** | Not available on Bedrock | **90% discount on cached input** |
| **Free tier** | None | 1,000 req/day (Flash) |
| **Max output tokens** | 8K-16K | **64K** (4x larger) |
| **Regions** | us-east-1, eu-west-1 via CRIS | Global (auto-routing) |
| **Enterprise compliance** | SOC2, HIPAA via AWS | SOC2, HIPAA via GCP |

### I. Cost Per Token -- Visual Comparison ($/1M tokens)

```
INPUT COST ($/1M tokens)
Claude Opus 4.5     ████████████████████████████████████████ $15.00
Gemini 3 Pro        █████ $2.00
Claude Sonnet 4.5   ████████ $3.00
Gemini 3 Flash      █▎ $0.50
Claude Haiku 4.5    ██ $0.80
Gemini 2.5 Flash    ▊ $0.30
Gemini Flash-Lite   ▎ $0.10

OUTPUT COST ($/1M tokens)
Claude Opus 4.5     ████████████████████████████████████████████████████████████████████████████ $75.00
Gemini 3 Pro        ████████████ $12.00
Claude Sonnet 4.5   ███████████████ $15.00
Claude Haiku 4.5    ████ $4.00
Gemini 3 Flash      ███ $3.00
Gemini 2.5 Flash    ██▌ $2.50
Gemini Flash-Lite   ▍ $0.40
```

### J. Decision Matrix

| Factor | Weight | Claude (current) | Gemini Tiered | Gemini Flash | Hybrid |
|--------|--------|-----------------|--------------|-------------|--------|
| **LLM cost** | 25% | 2/10 | 7/10 | **10/10** | 7/10 |
| **Infrastructure cost** | 15% | 3/10 | 3/10 (AWS) or 8/10 (GCP) | 8/10 (GCP) | 3/10 |
| **Reasoning quality** | 25% | **10/10** | 8/10 | 5/10 | **9/10** |
| **Safety reliability** | 20% | **10/10** | 7/10 | 4/10 | **10/10** |
| **Speed** | 10% | 3/10 | 7/10 | **10/10** | 7/10 |
| **Migration effort** | 5% | **10/10** (none) | 5/10 | 5/10 | 4/10 |
| **Weighted Score** | 100% | **6.3** | **6.5-7.3** | **6.6** | **7.3** |

### K. Bottom Line

**Cheapest option**: Gemini 3 Flash on GCP -- **$0.12/analysis** (87% cheaper than current) but risks safety reasoning quality.

**Best value option**: Gemini Tiered on GCP -- **$0.34/analysis** (61% cheaper) with reasonable quality trade-offs and eliminates the $175-350/month OpenSearch cost.

**Lowest risk option**: Hybrid (Claude safety + Gemini business/arbitrator) on AWS -- **$0.34/analysis** (61% cheaper) preserving Claude's proven safety reasoning while cutting the Opus arbitrator cost by 85%.

**Fastest ROI**: Simply switching the arbitrator from Opus to Sonnet (no provider change) -- saves $0.42/analysis immediately with zero migration effort.

| Action | Effort | Monthly Savings (at 500/mo) | Annual Savings |
|--------|--------|----------------------------|----------------|
| Opus -> Sonnet arbitrator | 1 line change | $210 | **$2,520** |
| + Token optimizations | 1-2 days | $75 | **$900** |
| + Gemini for business agents | 2-3 days | $16 | **$192** |
| + Gemini for arbitrator | 1-2 days | $13 | **$156** |
| + Full GCP migration | 1-2 weeks | $200 | **$2,400** |
| **All combined** | **2-3 weeks** | **$514** | **$6,168** |

---

### Architecture Change Summary

#### Files That Need Modification (for Gemini migration)

| File | Change Required |
|------|----------------|
| `skymarshal_agents_new/skymarshal/src/model/load.py` | Replace `ChatBedrock` with `ChatGoogleGenerativeAI`; update model IDs |
| `src/config.py` | Update `AGENT_MODEL_MAP` with Gemini model IDs |
| `skymarshal_agents_new/skymarshal/src/agents/arbitrator/agent.py` | Update Opus model loading to Gemini 3 Pro |
| `requirements.txt` | Add `langchain-google-genai` or `langchain-google-vertexai` |
| `.env` | Add `GOOGLE_API_KEY` or GCP service account config |

#### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reasoning quality drop on safety agents | HIGH | A/B test Gemini 3 Pro vs Claude Sonnet before switching |
| Structured output reliability | MEDIUM | Claude has better instruction-following; test Pydantic schemas |
| Multi-cloud complexity | LOW | LangChain abstracts the difference |
| Knowledge Base migration | HIGH (if migrated) | Keep Bedrock KB, only migrate LLM calls |
| Prompt compatibility | MEDIUM | Gemini needs more precise prompts; tune system prompts |

---

*Report generated: February 6, 2026*
*Sources: AWS Bedrock Pricing, Google AI Gemini API Pricing, Vertex AI Pricing, project codebase analysis*
