# SkyMarshal Architecture Diagram

## System Architecture Overview

```mermaid
flowchart TB
    subgraph Frontend["🔵 FRONTEND LAYER"]
        direction TB
        React["⚛️ React 19"]
        TS["📘 TypeScript"]
        Vite["⚡ Vite 6"]
        Tailwind["🎨 Tailwind CSS"]

        subgraph Components["UI Components"]
            Landing["LandingPage"]
            Orchestration["OrchestrationView"]
            Arbitrator["ArbitratorPanel"]
            AgentMsg["AgentMessage"]
        end

        subgraph Services["Frontend Services"]
            ApiAsync["apiAsync.ts\n(Polling)"]
            ResponseMapper["responseMapper.ts"]
        end
    end

    subgraph AWS["☁️ AWS CLOUD"]
        subgraph APILayer["🟠 API GATEWAY"]
            Invoke["POST /invoke"]
            Status["GET /status/{id}"]
            SaveDecision["POST /save-decision"]
            Override["POST /submit-override"]
        end

        subgraph Lambda["🟠 AWS LAMBDA"]
            AsyncHandler["lambda_handler_async.py"]
            StatusChecker["Status Checker"]
        end

        subgraph AgentCore["🟣 AWS BEDROCK AGENTCORE RUNTIME"]
            subgraph LangGraph["🔗 LANGGRAPH ORCHESTRATOR"]
                Phase1["📋 PHASE 1\nInitial Analysis"]
                Phase2["🔄 PHASE 2\nRevision Round"]
                Phase3["⚖️ PHASE 3\nArbitration"]
            end

            subgraph SafetyAgents["🟢 SAFETY AGENTS"]
                Crew["👨‍✈️ Crew Compliance\n• FDP Validation\n• Rest Requirements"]
                Maintenance["🔧 Maintenance\n• Airworthiness\n• MEL Assessment"]
                Regulatory["📜 Regulatory\n• Compliance Check\n• Curfew Validation"]
            end

            subgraph BusinessAgents["🟡 BUSINESS AGENTS"]
                Network["🌐 Network\n• Route Impact\n• Downstream Flights"]
                GuestExp["😊 Guest Experience\n• Passenger Impact\n• Compensation"]
                Cargo["📦 Cargo\n• Shipment Priority\n• Cold Chain"]
                Finance["💰 Finance\n• Cost Analysis\n• Revenue Impact"]
            end

            subgraph ArbitratorAgent["🟣 ARBITRATOR"]
                Claude["🧠 Claude Opus 4.5\n(Primary)"]
                Fallback["Fallback Chain:\nSonnet 4.5 → Haiku 4.5\n→ Nova Premier → Nova Pro"]
                Decision["📊 Decision Engine\n• Conflict Resolution\n• Scenario Scoring"]
            end
        end

        subgraph DataLayer["🟠 DATA LAYER"]
            DynamoDB["🗄️ DynamoDB\n40+ Tables\nV1/V2 Versioning"]
            S3["📁 S3\nDecisions\nAudit Trails"]
            KnowledgeBase["🧠 Bedrock\nKnowledge Base\n(RAG)"]
        end

        subgraph Observability["⚪ OBSERVABILITY"]
            CloudWatch["📊 CloudWatch\nLogs & Metrics"]
            OpenTelemetry["🔍 OpenTelemetry\nDistributed Tracing"]
            IAM["🔐 IAM\nPermissions"]
        end
    end

    %% Connections
    Frontend --> APILayer
    APILayer --> Lambda
    Lambda --> AgentCore

    Phase1 --> SafetyAgents
    Phase1 --> BusinessAgents
    SafetyAgents --> Phase2
    BusinessAgents --> Phase2
    Phase2 --> Phase3
    Phase3 --> ArbitratorAgent

    ArbitratorAgent --> DataLayer
    SafetyAgents -.-> DynamoDB
    BusinessAgents -.-> DynamoDB
    ArbitratorAgent -.-> KnowledgeBase

    Lambda -.-> CloudWatch
    AgentCore -.-> CloudWatch
    AgentCore -.-> OpenTelemetry

    %% Styling
    classDef frontend fill:#3b82f6,stroke:#1d4ed8,color:#fff
    classDef aws fill:#ff9900,stroke:#cc7a00,color:#000
    classDef ai fill:#8b5cf6,stroke:#6d28d9,color:#fff
    classDef safety fill:#22c55e,stroke:#16a34a,color:#fff
    classDef business fill:#eab308,stroke:#ca8a04,color:#000
    classDef data fill:#f97316,stroke:#ea580c,color:#fff
    classDef observability fill:#6b7280,stroke:#4b5563,color:#fff

    class React,TS,Vite,Tailwind,Landing,Orchestration,Arbitrator,AgentMsg,ApiAsync,ResponseMapper frontend
    class Invoke,Status,SaveDecision,Override,AsyncHandler,StatusChecker aws
    class Claude,Fallback,Decision,Phase1,Phase2,Phase3 ai
    class Crew,Maintenance,Regulatory safety
    class Network,GuestExp,Cargo,Finance business
    class DynamoDB,S3,KnowledgeBase data
    class CloudWatch,OpenTelemetry,IAM observability
```

---

## Data Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    participant User as 👤 User
    participant React as ⚛️ React Frontend
    participant API as 🟠 API Gateway
    participant Lambda as 🟠 Lambda
    participant AgentCore as 🟣 AgentCore
    participant LangGraph as 🔗 LangGraph
    participant Safety as 🟢 Safety Agents
    participant Business as 🟡 Business Agents
    participant Arbitrator as 🧠 Claude Opus 4.5
    participant DynamoDB as 🗄️ DynamoDB
    participant S3 as 📁 S3

    User->>React: Enter disruption details
    React->>API: POST /invoke
    API->>Lambda: Trigger async handler
    Lambda->>DynamoDB: Store request (status: processing)
    Lambda-->>React: 202 Accepted + request_id

    Lambda->>AgentCore: Invoke orchestrator
    AgentCore->>LangGraph: Start workflow

    rect rgb(34, 197, 94, 0.1)
        Note over LangGraph,Business: PHASE 1: Initial Analysis (Parallel)
        LangGraph->>Safety: Analyze (parallel)
        LangGraph->>Business: Analyze (parallel)
        Safety-->>LangGraph: Safety assessments
        Business-->>LangGraph: Business recommendations
    end

    rect rgb(234, 179, 8, 0.1)
        Note over LangGraph,Business: PHASE 2: Revision Round
        LangGraph->>Safety: Re-analyze with context
        LangGraph->>Business: Re-analyze with context
        Safety-->>LangGraph: Revised assessments
        Business-->>LangGraph: Revised recommendations
    end

    rect rgb(139, 92, 246, 0.1)
        Note over LangGraph,Arbitrator: PHASE 3: Arbitration
        LangGraph->>Arbitrator: All agent outputs
        Arbitrator->>Arbitrator: Conflict resolution
        Arbitrator->>Arbitrator: Generate 3-5 scenarios
        Arbitrator->>Arbitrator: Score & rank scenarios
        Arbitrator-->>LangGraph: Final decision + rationale
    end

    LangGraph-->>AgentCore: Complete assessment
    AgentCore->>DynamoDB: Update status: complete
    AgentCore->>S3: Store decision record

    loop Polling (every 2s)
        React->>API: GET /status/{request_id}
        API->>DynamoDB: Check status
        DynamoDB-->>API: Status response
        API-->>React: Processing... / Complete
    end

    React->>React: Display OrchestrationView
    React->>React: Show ArbitratorPanel

    opt Save Decision
        User->>React: Click "Save Decision"
        React->>API: POST /save-decision
        API->>S3: Store final decision
    end

    opt Override Decision
        User->>React: Submit override
        React->>API: POST /submit-override
        API->>S3: Store human override
    end
```

---

## Technology Stack

```mermaid
mindmap
  root((SkyMarshal))
    Frontend
      React 19
      TypeScript 5.8
      Vite 6
      Tailwind CSS
      Lucide Icons
      react-markdown
    Backend
      Python 3.10
      LangGraph
      LangChain
      Pydantic
      boto3
    AWS Services
      Bedrock AgentCore
        Runtime
        SDK
      Bedrock Models
        Claude Opus 4.5
        Claude Sonnet 4.5
        Amazon Nova
      API Gateway
        REST API
        WebSocket
      Lambda
        Async Handler
        Status Checker
      DynamoDB
        40+ Tables
        GSI Indexes
      S3
        Decisions
        Audit Logs
      CloudWatch
        Logs
        Metrics
    AI Models
      Claude Opus 4.5 Primary
      Claude Sonnet 4.5 Fallback
      Claude Haiku 4.5 Fallback
      Amazon Nova Premier
      Amazon Nova Pro
```

---

## Agent Architecture

```mermaid
flowchart LR
    subgraph Input["📥 INPUT"]
        Disruption["Flight Disruption\n• Flight: EY123\n• Issue: Hydraulic fault\n• Passengers: 615"]
    end

    subgraph Phase1["📋 PHASE 1"]
        direction TB
        P1Safety["🟢 Safety Analysis"]
        P1Business["🟡 Business Analysis"]
    end

    subgraph SafetyDetail["Safety Agents Detail"]
        direction TB
        S1["👨‍✈️ Crew Compliance\nFDP: 3.5hrs remaining\nStatus: APPROVED"]
        S2["🔧 Maintenance\nMEL Category B\nStatus: DEFERRABLE"]
        S3["📜 Regulatory\nCurfew Risk: 20:00\nStatus: CONDITIONAL"]
    end

    subgraph BusinessDetail["Business Agents Detail"]
        direction TB
        B1["🌐 Network\nDownstream: $450K impact\nPriority: HIGH"]
        B2["😊 Guest Experience\nCompensation: €125K\nRisk: MEDIUM"]
        B3["📦 Cargo\nCritical: 3 shipments\nOffload: NO"]
        B4["💰 Finance\nCancel: €1.2M\nDelay: €210K"]
    end

    subgraph Phase2["🔄 PHASE 2"]
        Revision["Context-Aware\nRevision"]
    end

    subgraph Phase3["⚖️ PHASE 3"]
        ArbitratorBox["🧠 ARBITRATOR\nClaude Opus 4.5"]
    end

    subgraph Output["📤 OUTPUT"]
        Decision["✅ Final Decision\nScenario: RS-001\nScore: 75.9/100\nConfidence: 78%"]
        Scenarios["📊 Recovery Scenarios\n1. Expedited Delay\n2. Aircraft Swap\n3. Passenger Rebooking\n4. Cancel & Reroute"]
    end

    Disruption --> Phase1
    Phase1 --> SafetyDetail
    Phase1 --> BusinessDetail
    SafetyDetail --> Phase2
    BusinessDetail --> Phase2
    Phase2 --> Phase3
    Phase3 --> Output

    style Input fill:#e0e7ff,stroke:#4f46e5
    style Phase1 fill:#dcfce7,stroke:#16a34a
    style Phase2 fill:#fef9c3,stroke:#ca8a04
    style Phase3 fill:#f3e8ff,stroke:#9333ea
    style Output fill:#dbeafe,stroke:#2563eb
```

---

## Infrastructure Deployment

```mermaid
flowchart TB
    subgraph Dev["💻 Development"]
        LocalDev["Local Development\napp.run() on :8080"]
        Testing["Unit Tests\nIntegration Tests"]
    end

    subgraph CICD["🔄 CI/CD"]
        CodeBuild["AWS CodeBuild"]
        AgentCoreCLI["agentcore deploy"]
    end

    subgraph Production["🚀 Production"]
        subgraph Compute["Compute"]
            AgentCoreRuntime["AgentCore Runtime\nAuto-scaling"]
            LambdaFunctions["Lambda Functions"]
        end

        subgraph Networking["Networking"]
            APIGW["API Gateway"]
            VPC["VPC"]
        end

        subgraph Storage["Storage"]
            DynamoDBProd["DynamoDB\nOn-demand"]
            S3Prod["S3\nVersioned"]
        end

        subgraph Security["Security"]
            IAMRoles["IAM Roles"]
            Secrets["Secrets Manager"]
        end
    end

    Dev --> CICD
    CICD --> Production

    style Dev fill:#dbeafe,stroke:#2563eb
    style CICD fill:#fef3c7,stroke:#d97706
    style Production fill:#dcfce7,stroke:#16a34a
```

---

## Legend

| Icon | Component | Description |
|------|-----------|-------------|
| ⚛️ | React | Frontend framework |
| 📘 | TypeScript | Type-safe JavaScript |
| ⚡ | Vite | Build tool |
| 🔗 | LangGraph | Orchestration framework |
| 🧠 | Claude Opus 4.5 | Primary AI model |
| 🟢 | Safety Agents | Crew, Maintenance, Regulatory |
| 🟡 | Business Agents | Network, Guest, Cargo, Finance |
| 🟠 | AWS Services | Lambda, API Gateway, DynamoDB, S3 |
| 🟣 | AI/ML | Bedrock, AgentCore |
| ⚪ | Observability | CloudWatch, OpenTelemetry |

---

## Key Metrics

| Metric | Value |
|--------|-------|
| **Total Agents** | 7 domain + 1 arbitrator |
| **DynamoDB Tables** | 40+ (V1 & V2) |
| **Processing Phases** | 3 (Initial → Revision → Arbitration) |
| **Model Fallback Depth** | 5 models |
| **Typical Response Time** | 45-60 seconds |
| **Context Window** | 200K tokens (Claude Opus 4.5) |
