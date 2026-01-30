# SkyMarshal - Architecture Diagrams

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  ┌──────────────────────┐      ┌──────────────────────┐        │
│  │  Streamlit Dashboard │      │     CLI Runner       │        │
│  │  - Real-time updates │      │  - Batch processing  │        │
│  │  - Scenario review   │      │  - Detailed logs     │        │
│  └──────────┬───────────┘      └──────────┬───────────┘        │
└─────────────┼──────────────────────────────┼────────────────────┘
              │                              │
              └──────────────┬───────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LangGraph State Machine                     │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐        │  │
│  │  │Trigger │─>│Safety  │─>│Impact  │─>│Options │─> ...  │  │
│  │  └────────┘  └────────┘  └────────┘  └────────┘        │  │
│  │                                                           │  │
│  │  Phases: Trigger → Safety → Guardrail → Impact →        │  │
│  │          Options → Arbitration → Human → Execution       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                        AGENT LAYER                              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Model Router & Factory                     │  │
│  │  Routes to: AWS Bedrock | OpenAI | Google Gemini       │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ SAFETY (3)   │  │ BUSINESS (4) │  │ ARBITRATOR   │        │
│  │              │  │              │  │              │        │
│  │ • Crew       │  │ • Network    │  │ • Validate   │        │
│  │ • Maint      │  │ • Guest      │  │ • Compose    │        │
│  │ • Regulatory │  │ • Cargo      │  │ • Rank       │        │
│  │              │  │ • Finance    │  │ • Explain    │        │
│  │              │  │              │  │              │        │
│  │ Claude       │  │ GPT-4o       │  │ Gemini       │        │
│  │ Sonnet 4     │  │ Claude       │  │ 2.0 Flash    │        │
│  │              │  │ Gemini       │  │              │        │
│  │              │  │ Nova Pro     │  │              │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                        DATA LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  PostgreSQL  │  │  Shared      │  │  Historical  │         │
│  │              │  │  Memory      │  │  Knowledge   │         │
│  │ • Flights    │  │  (State)     │  │  Base        │         │
│  │ • Passengers │  │              │  │              │         │
│  │ • Cargo      │  │ • Disruption │  │ • Past       │         │
│  │ • Crew       │  │ • Constraints│  │   Scenarios  │         │
│  │              │  │ • Scenarios  │  │ • Outcomes   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow Sequence

```
┌─────────┐
│ TRIGGER │ Speech-to-text or system event
└────┬────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 1: TRIGGER                                        │
│ • Parse disruption event                                │
│ • Load flight context from database                     │
│ • Initialize shared memory                              │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 2: SAFETY ASSESSMENT (BLOCKING)                   │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Crew Agent   │  │ Maint Agent  │  │  Reg Agent   │ │
│  │              │  │              │  │              │ │
│  │ Chain-of-    │  │ MEL/AOG      │  │ NOTAMs       │ │
│  │ Thought      │  │ Analysis     │  │ Curfews      │ │
│  │              │  │              │  │              │ │
│  │ FTL Check    │  │ Airworthy?   │  │ ATC Slots    │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │          │
│         └─────────────────┼─────────────────┘          │
│                           ▼                            │
│                  Safety Constraints                    │
│                  (IMMUTABLE)                           │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 3: GUARDRAIL CHECK                                │
│ • Verify all safety agents completed                    │
│ • Check for timeouts or failures                        │
│ • Escalate if needed                                    │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 4: IMPACT ASSESSMENT                              │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Network  │  │  Guest   │  │  Cargo   │  │Finance │ │
│  │          │  │          │  │          │  │        │ │
│  │ Flights  │  │ PAX      │  │ AWBs     │  │ Cost   │ │
│  │ Affected │  │ At Risk  │  │ At Risk  │  │ Impact │ │
│  │          │  │          │  │          │  │        │ │
│  │ NO       │  │ NO       │  │ NO       │  │ NO     │ │
│  │ SOLUTIONS│  │ SOLUTIONS│  │ SOLUTIONS│  │ SOLNS  │ │
│  └──────┬───┘  └──────┬───┘  └──────┬───┘  └────┬───┘ │
│         │             │             │           │      │
│         └─────────────┼─────────────┼───────────┘      │
│                       ▼             ▼                  │
│              Impact Assessments (Quantified)          │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 5: OPTION FORMULATION                             │
│                                                          │
│  Round 1: Generate Proposals                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ Network  │  │  Guest   │  │  Cargo   │  │Finance │ │
│  │ Proposal │  │ Proposal │  │ Proposal │  │Proposal│ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│                                                          │
│  Round 2-3: Debate & Critique                           │
│  • Agents critique peer proposals                       │
│  • Reference safety constraints                         │
│  • Consider trade-offs                                  │
│  • Max 3 rounds or timeout                              │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 6: ARBITRATION                                    │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         Skymarshal Arbitrator                  │    │
│  │                                                 │    │
│  │  Step 1: Validate Proposals                    │    │
│  │  • Check safety constraint compliance          │    │
│  │  • Hard reject violations                      │    │
│  │                                                 │    │
│  │  Step 2: Compose Scenarios                     │    │
│  │  • Combine compatible proposals                │    │
│  │  • Create scenario variants                    │    │
│  │                                                 │    │
│  │  Step 3: Score Scenarios                       │    │
│  │  • Multi-criteria optimization                 │    │
│  │  • Historical pattern matching                 │    │
│  │                                                 │    │
│  │  Step 4: Rank & Explain                        │    │
│  │  • Top-3 scenarios                             │    │
│  │  • Rationale, pros, cons                       │    │
│  │  • Confidence scores                           │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  Output: Ranked Scenarios                               │
│  #1: [Best] Score: 0.85 Confidence: 0.80               │
│  #2: [Good] Score: 0.78 Confidence: 0.75               │
│  #3: [Safe] Score: 0.70 Confidence: 0.90               │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 7: HUMAN-IN-THE-LOOP                              │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │         Duty Manager Review                    │    │
│  │                                                 │    │
│  │  For each scenario:                            │    │
│  │  • Title & description                         │    │
│  │  • Estimated delay, cost, PAX impact           │    │
│  │  • Pros & cons                                 │    │
│  │  • Confidence score                            │    │
│  │  • Safety compliance proof                     │    │
│  │                                                 │    │
│  │  Actions:                                      │    │
│  │  [ Approve ] [ Override ] [ Request More ]     │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
│  Decision Captured:                                     │
│  • Chosen scenario ID                                   │
│  • Was override? (Y/N)                                  │
│  • Rationale                                            │
│  • Timestamp & decision maker                           │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ PHASE 8: EXECUTION                                      │
│                                                          │
│  For each action in chosen scenario:                    │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Aircraft     │  │ Passenger    │  │ Cargo        │ │
│  │ Swap         │  │ Rebooking    │  │ Re-routing   │ │
│  │              │  │              │  │              │ │
│  │ MCP: Fleet   │  │ MCP: PSS     │  │ MCP: CMS     │ │
│  │ System       │  │ System       │  │ System       │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │          │
│         └─────────────────┼─────────────────┘          │
│                           ▼                            │
│                  Execution Logs                        │
│                  (Streaming)                           │
│                                                          │
│  ✅ Aircraft A6-BND swapped to A6-BNE                  │
│  ✅ 47 passengers rebooked on EY552                    │
│  ✅ 3 cargo AWBs transferred                           │
│  ✅ Hotels booked for 12 passengers                    │
│  ✅ Notifications sent to all affected                 │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ LEARNING & AUDIT                                        │
│                                                          │
│  Store:                                                 │
│  • Complete disruption log                             │
│  • All agent conversations                             │
│  • All scenarios evaluated                             │
│  • Human decision & rationale                          │
│  • Execution results                                   │
│  • Final KPIs                                          │
│                                                          │
│  Update:                                               │
│  • Historical knowledge base                           │
│  • Pattern recognition models                          │
│  • Agent performance metrics                           │
└─────────────────────────────────────────────────────────┘
```

## Data Flow

```
┌──────────────┐
│  Disruption  │
│    Event     │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│         Shared Memory                    │
│  ┌────────────────────────────────────┐ │
│  │ disruption: DisruptionEvent        │ │
│  │ current_phase: str                 │ │
│  │ safety_constraints: List[...]      │ │
│  │ impact_assessments: Dict[...]      │ │
│  │ agent_proposals: List[...]         │ │
│  │ ranked_scenarios: List[...]        │ │
│  │ human_decision: Optional[...]      │ │
│  │ execution_results: List[...]       │ │
│  └────────────────────────────────────┘ │
└──────────────┬───────────────────────────┘
               │
       ┌───────┼───────┐
       │       │       │
       ▼       ▼       ▼
   ┌─────┐ ┌─────┐ ┌─────┐
   │Agent│ │Agent│ │Agent│
   │  1  │ │  2  │ │  3  │
   └──┬──┘ └──┬──┘ └──┬──┘
      │       │       │
      └───────┼───────┘
              │
              ▼
       ┌──────────────┐
       │  Arbitrator  │
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │    Human     │
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │  Execution   │
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │  Audit Log   │
       └──────────────┘
```

## Model Distribution

```
┌─────────────────────────────────────────────────────────┐
│                    MODEL PROVIDERS                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  AWS Bedrock                                            │
│  ├─ Claude Sonnet 4                                     │
│  │  ├─ Orchestrator                                     │
│  │  ├─ Crew Compliance Agent                           │
│  │  ├─ Maintenance Agent                               │
│  │  ├─ Regulatory Agent                                │
│  │  └─ Guest Experience Agent                          │
│  │                                                      │
│  └─ Amazon Nova Pro                                     │
│     └─ Finance Agent                                    │
│                                                          │
│  OpenAI                                                 │
│  └─ GPT-4o                                              │
│     └─ Network Agent                                    │
│                                                          │
│  Google AI                                              │
│  └─ Gemini 2.0 Flash                                    │
│     ├─ Arbitrator                                       │
│     └─ Cargo Agent                                      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Cost Breakdown

```
Per Disruption (~$1.10)
┌─────────────────────────────────────────┐
│ Orchestrator (Claude)      $0.11  10%  │
│ ████                                    │
│                                         │
│ Safety Agents (3x Claude)  $0.46  42%  │
│ ████████████████████                    │
│                                         │
│ Business Agents (Mixed)    $0.16  15%  │
│ ███████                                 │
│                                         │
│ Arbitrator (Gemini)        $0.11  10%  │
│ ████                                    │
│                                         │
│ Execution (Claude)         $0.26  23%  │
│ ███████████                             │
└─────────────────────────────────────────┘
```

---

**SkyMarshal Architecture - Built for Scale, Optimized for Cost**
