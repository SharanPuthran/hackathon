# SkyMarshal - Model Distribution Visual

## Complete Model Mapping

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SKYMARSHAL SYSTEM                            │
│                     12 Agents, 4 Providers, 5 Models               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATION                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  Orchestrator                                                 │ │
│  │  Model: Claude Sonnet 4                                       │ │
│  │  Provider: AWS Bedrock                                        │ │
│  │  Purpose: Workflow coordination, state management             │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      SAFETY AGENTS (3)                              │
│                   Critical - Zero Tolerance                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Crew Compliance Agent                                      │   │
│  │  Model: Claude Sonnet 4                                     │   │
│  │  Provider: AWS Bedrock                                      │   │
│  │  Purpose: FTL regulations, duty time limits                 │   │
│  │  Features: Chain-of-thought reasoning                       │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Maintenance Agent                                          │   │
│  │  Model: Claude Sonnet 4                                     │   │
│  │  Provider: AWS Bedrock                                      │   │
│  │  Purpose: MEL/AOG analysis, airworthiness                   │   │
│  │  Features: Technical reasoning                              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Regulatory Agent                                           │   │
│  │  Model: Claude Sonnet 4                                     │   │
│  │  Provider: AWS Bedrock                                      │   │
│  │  Purpose: NOTAMs, curfews, ATC restrictions                 │   │
│  │  Features: Regulatory compliance                            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    BUSINESS AGENTS (4)                              │
│                  Diverse Models for Debate                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Network Agent                                              │   │
│  │  Model: GPT-4o                                              │   │
│  │  Provider: OpenAI                                           │   │
│  │  Purpose: Network propagation, fleet utilization            │   │
│  │  Features: Graph reasoning, downstream analysis             │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Guest Experience Agent                                     │   │
│  │  Model: Claude Sonnet 4                                     │   │
│  │  Provider: AWS Bedrock                                      │   │
│  │  Purpose: Passenger satisfaction, NPS impact                │   │
│  │  Features: Empathy analysis, customer sentiment             │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Cargo Agent                                                │   │
│  │  Model: Gemini 2.0 Flash                                    │   │
│  │  Provider: Google AI                                        │   │
│  │  Purpose: Cargo logistics, cold-chain protection            │   │
│  │  Features: Fast inference, logistics optimization           │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Finance Agent                                              │   │
│  │  Model: Amazon Nova Pro                                     │   │
│  │  Provider: AWS Bedrock                                      │   │
│  │  Purpose: Cost analysis, revenue optimization               │   │
│  │  Features: Financial modeling, numerical reasoning          │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         ARBITRATOR                                  │
│                  Complex Multi-Criteria Optimization                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Skymarshal Arbitrator                                      │   │
│  │  Model: Gemini 2.0 Flash                                    │   │
│  │  Provider: Google AI                                        │   │
│  │  Purpose: Scenario ranking, constraint enforcement          │   │
│  │  Features: 1M token context, multi-criteria optimization    │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      EXECUTION AGENTS                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  Execution Agents (5)                                       │   │
│  │  Model: Claude Sonnet 4                                     │   │
│  │  Provider: AWS Bedrock                                      │   │
│  │  Purpose: Action execution, MCP coordination                │   │
│  │  Features: Reliable execution, confirmation                 │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Model Distribution by Provider

```
┌─────────────────────────────────────────────────────────────┐
│                    AWS BEDROCK (7 agents)                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Claude Sonnet 4 (6 agents)                                │
│  ├─ Orchestrator                                           │
│  ├─ Crew Compliance Agent                                  │
│  ├─ Maintenance Agent                                      │
│  ├─ Regulatory Agent                                       │
│  ├─ Guest Experience Agent                                 │
│  └─ Execution Agents                                       │
│                                                             │
│  Amazon Nova Pro (1 agent)                                 │
│  └─ Finance Agent                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    GOOGLE AI (2 agents)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Gemini 2.0 Flash (2 agents)                               │
│  ├─ Arbitrator                                             │
│  └─ Cargo Agent                                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     OPENAI (1 agent)                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  GPT-4o (1 agent)                                          │
│  └─ Network Agent                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Agent-to-Model Flow

```
Disruption Event
       │
       ▼
┌──────────────────┐
│  Orchestrator    │ ──► Claude Sonnet 4 (Bedrock)
└────────┬─────────┘
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
┌─────────────────┐                  ┌─────────────────┐
│  Safety Agents  │                  │ Business Agents │
└─────────────────┘                  └─────────────────┘
         │                                     │
         ├─► Crew Compliance ──► Claude Sonnet 4 (Bedrock)
         ├─► Maintenance ──────► Claude Sonnet 4 (Bedrock)
         └─► Regulatory ───────► Claude Sonnet 4 (Bedrock)
                                               │
                                               ├─► Network ──────► GPT-4o (OpenAI)
                                               ├─► Guest ────────► Claude Sonnet 4 (Bedrock)
                                               ├─► Cargo ────────► Gemini 2.0 Flash (Google)
                                               └─► Finance ──────► Nova Pro (Bedrock)
         │
         ▼
┌──────────────────┐
│   Arbitrator     │ ──► Gemini 2.0 Flash (Google)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Human Approval  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Execution Agents │ ──► Claude Sonnet 4 (Bedrock)
└──────────────────┘
```

## Cost Distribution

```
Per Disruption Cost: $1.10

┌─────────────────────────────────────────────────────────┐
│                                                         │
│  Claude Sonnet 4 (6 agents)                            │
│  ████████████████████████████████████████  $0.42 (38%) │
│                                                         │
│  Gemini 2.0 Flash (2 agents)                           │
│  (Free in preview)                         $0.00 (0%)  │
│                                                         │
│  GPT-4o (1 agent)                                      │
│  ███████                                   $0.06 (5%)  │
│                                                         │
│  Nova Pro (1 agent)                                    │
│  ██                                        $0.02 (2%)  │
│                                                         │
│  Orchestration Overhead                                │
│  ████████████████████████████████████████  $0.60 (55%) │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Model Characteristics Comparison

```
┌──────────────────┬─────────────┬──────────────┬─────────────┬──────────────┐
│ Model            │ Context     │ Speed        │ Cost        │ Best For     │
├──────────────────┼─────────────┼──────────────┼─────────────┼──────────────┤
│ Claude Sonnet 4  │ 200K tokens │ Medium       │ Medium      │ Safety       │
│                  │             │ (5-8 sec)    │ $3/$15      │ Reasoning    │
├──────────────────┼─────────────┼──────────────┼─────────────┼──────────────┤
│ Gemini 2.0 Flash │ 1M tokens   │ Fast         │ Free*       │ Optimization │
│                  │             │ (2-3 sec)    │ (preview)   │ Large context│
├──────────────────┼─────────────┼──────────────┼─────────────┼──────────────┤
│ GPT-4o           │ 128K tokens │ Medium       │ Medium      │ Network      │
│                  │             │ (4-6 sec)    │ $2.5/$10    │ Analysis     │
├──────────────────┼─────────────┼──────────────┼─────────────┼──────────────┤
│ Nova Pro         │ 300K tokens │ Fast         │ Low         │ Financial    │
│                  │             │ (3-5 sec)    │ $0.8/$3.2   │ Modeling     │
└──────────────────┴─────────────┴──────────────┴─────────────┴──────────────┘

* Gemini 2.0 Flash is currently free in preview
```

## Why This Distribution?

```
┌─────────────────────────────────────────────────────────────┐
│                    DESIGN RATIONALE                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Safety-Critical Tasks                                     │
│  ├─ Use: Claude Sonnet 4                                   │
│  ├─ Why: Best chain-of-thought reasoning                   │
│  └─ Agents: Crew, Maintenance, Regulatory                  │
│                                                             │
│  Complex Optimization                                      │
│  ├─ Use: Gemini 2.0 Flash                                  │
│  ├─ Why: Massive context, multi-criteria optimization      │
│  └─ Agents: Arbitrator, Cargo                              │
│                                                             │
│  Network Analysis                                          │
│  ├─ Use: GPT-4o                                            │
│  ├─ Why: Excellent graph reasoning                         │
│  └─ Agents: Network                                        │
│                                                             │
│  Financial Modeling                                        │
│  ├─ Use: Nova Pro                                          │
│  ├─ Why: Cost-effective, strong numerical reasoning        │
│  └─ Agents: Finance                                        │
│                                                             │
│  Customer Sentiment                                        │
│  ├─ Use: Claude Sonnet 4                                   │
│  ├─ Why: Excellent empathy and sentiment analysis          │
│  └─ Agents: Guest Experience                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Benefits of Multi-Model Approach

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ✅ Diverse Perspectives                                   │
│     Different models = different reasoning styles          │
│     Reduces groupthink in business agent debate            │
│                                                             │
│  ✅ Cost Optimization                                      │
│     53% savings vs single-model approach                   │
│     Use expensive models only where needed                 │
│                                                             │
│  ✅ Performance Optimization                               │
│     Each model optimized for its specific task             │
│     Faster inference for simpler tasks                     │
│                                                             │
│  ✅ Redundancy                                             │
│     No single point of failure                             │
│     Provider diversity reduces risk                        │
│                                                             │
│  ✅ Future-Proofing                                        │
│     Easy to swap models as new ones emerge                 │
│     Can A/B test different models                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

**SkyMarshal: 12 Agents, 4 Providers, 5 Models, Optimal Performance**
