# Design Document

## Overview

This design enhances the SkyMarshal frontend to properly parse and display the three-phase orchestration workflow from the AgentCore Runtime API. The system will transform the nested API response structure (`assessment.audit_trail` containing `phase1_initial`, `phase2_revision`, and `phase3_arbitration`) into a sequential, animated UI experience that guides users through initial assessments, cross-impact analysis, and strategic solution selection.

The design focuses on three key areas:

1. **Response Parsing**: Extending the ResponseMapper to handle the three-phase audit trail structure
2. **Sequential Display**: Implementing animation logic to show agent messages one at a time with proper timing
3. **Solution Visualization**: Creating rich solution cards with expandable details and scoring visualization

## Architecture

### Component Hierarchy

```
App
├── LandingPage (unchanged)
└── OrchestrationView (enhanced)
    ├── AgentAvatar (roster display)
    ├── AgentMessage (enhanced for new fields)
    └── ArbitratorPanel (enhanced for solution cards)
```

### Data Flow

```
API Response → ResponseMapper → OrchestrationView State → Component Rendering
```

**Phase 1 Flow:**

1. API returns complete response with `assessment.audit_trail.phase1_initial`
2. ResponseMapper extracts agent responses from phase1_initial.responses object
3. OrchestrationView iterates through agents, displaying messages sequentially
4. Each message shows recommendation, reasoning, and data_sources

**Phase 2 Flow:**

1. User clicks "Run Cross-Impact Analysis" button
2. OrchestrationView calls API with session_id
3. ResponseMapper extracts agent responses from phase2_revision.responses object
4. Messages are displayed sequentially with `isCrossImpactRound: true` flag

**Phase 3 Flow:**

1. After phase 2 completes, stage transitions to "decision_phase"
2. ResponseMapper extracts solution_options from phase3_arbitration
3. ArbitratorPanel displays solution cards with scoring and details
4. User selects a solution, triggering decision message display

### State Management

OrchestrationView manages the following state:

```typescript
stage: 'summoning' | 'initial_round' | 'waiting_for_user' | 'cross_impact' | 'decision_phase'
messages: MessageData[]
solutions: Solution[]
activeAgent: AgentType | null
thinkingAgent: AgentType | null
arbitratorAnalysis: string
selectedSolutionId: string | null
```

## Components and Interfaces

### ResponseMapper Enhancements

**New Methods:**

```typescript
// Parse phase1_initial responses
static parsePhase1(phase1: Phase1Initial): MessageData[]

// Parse phase2_revision responses
static parsePhase2(phase2: Phase2Revision): MessageData[]

// Parse phase3_arbitration solution options
static parseSolutions(phase3: Phase3Arbitration): Solution[]

// Main entry point for three-phase parsing
static parseAuditTrail(auditTrail: AuditTrail): {
  phase1Messages: MessageData[];
  phase2Messages: MessageData[];
  solutions: Solution[];
  recommendedSolutionId: string | null;
}
```

**Updated MessageData Interface:**

```typescript
interface MessageData {
  id: string;
  agent: AgentType;
  recommendation?: string; // NEW: from agent response
  reasoning?: string; // NEW: from agent response
  data_sources?: string[]; // NEW: from agent response
  status?: string; // NEW: agent status (success/error)
  isCrossImpactRound?: boolean;
  isDecision?: boolean;
  solutionTitle?: string;
}
```

**Updated Solution Interface:**

```typescript
interface Solution {
  id: string;
  solution_id: number; // NEW: numeric ID from API
  title: string;
  description: string;
  recommendations: string[]; // NEW: array of recommendation strings
  safety_score: number; // NEW: 0-100
  passenger_score: number; // NEW: 0-100
  network_score: number; // NEW: 0-100
  cost_score: number; // NEW: 0-100
  composite_score: number; // NEW: 0-100
  impact: "low" | "medium" | "high"; // Derived from scores
  justification: string; // NEW: detailed justification
  reasoning: string; // NEW: reasoning text
  passenger_impact: string; // NEW: passenger impact details
  financial_impact: string; // NEW: financial impact details
  network_impact: string; // NEW: network impact details
  pros: string[]; // NEW: array of pros
  cons: string[]; // NEW: array of cons
  risks: string[]; // NEW: array of risks
  recommended: boolean; // Derived from recommended_solution_id
}
```

### OrchestrationView Enhancements

**New Display Logic:**

```typescript
// Phase 1 display sequence
async function displayPhase1Messages(messages: MessageData[]) {
  for (const message of messages) {
    setThinkingAgent(message.agent);
    await delay(800);
    setThinkingAgent(null);
    setActiveAgent(message.agent);
    setMessages((prev) => [...prev, message]);
    await delay(1000);
    setActiveAgent(null);
  }
  setStage("waiting_for_user");
}

// Phase 2 cross-impact handler
async function handleCrossImpact() {
  setStage("cross_impact");
  const response = await apiService.invoke({
    prompt: "Perform cross-impact analysis",
    session_id: apiResponse.session_id,
  });

  const parsed = ResponseMapper.parseAuditTrail(
    response.assessment.audit_trail,
  );
  await displayPhase2Messages(parsed.phase2Messages);
  setSolutions(parsed.solutions);
  setStage("decision_phase");
}
```

### AgentMessage Enhancements

**New Content Display:**

```typescript
// Display recommendation and reasoning
{message.recommendation && (
  <div className="recommendation-section">
    <h5>Recommendation</h5>
    <p>{message.recommendation}</p>
  </div>
)}

{message.reasoning && (
  <div className="reasoning-section">
    <h5>Reasoning</h5>
    <p>{message.reasoning}</p>
  </div>
)}

{message.data_sources && message.data_sources.length > 0 && (
  <div className="data-sources-section">
    <h5>Data Sources</h5>
    <ul>
      {message.data_sources.map((source, idx) => (
        <li key={idx}>{source}</li>
      ))}
    </ul>
  </div>
)}
```

### ArbitratorPanel Solution Cards

**Solution Card Structure:**

```typescript
<div className="solution-card">
  {/* Header with recommendation badge */}
  <div className="card-header">
    {solution.recommended && <Badge>AI Recommended</Badge>}
    <h4>{solution.title}</h4>
  </div>

  {/* Description and recommendations */}
  <p>{solution.description}</p>
  <ul>
    {solution.recommendations.map(rec => <li>{rec}</li>)}
  </ul>

  {/* Scoring visualization */}
  <div className="scores">
    <ScoreBar label="Safety" value={solution.safety_score} />
    <ScoreBar label="Passenger" value={solution.passenger_score} />
    <ScoreBar label="Network" value={solution.network_score} />
    <ScoreBar label="Cost" value={solution.cost_score} />
    <ScoreBar label="Composite" value={solution.composite_score} />
  </div>

  {/* Risk indicator */}
  <RiskBadge level={solution.impact} />

  {/* Expand button */}
  <button onClick={() => expandSolution(solution)}>View More</button>
</div>
```

**Expanded Solution View:**

```typescript
<Modal>
  <h2>{solution.title}</h2>

  <Section title="Justification">
    {solution.justification}
  </Section>

  <Section title="Reasoning">
    {solution.reasoning}
  </Section>

  <Section title="Impact Analysis">
    <div>Passenger: {solution.passenger_impact}</div>
    <div>Financial: {solution.financial_impact}</div>
    <div>Network: {solution.network_impact}</div>
  </Section>

  <Section title="Pros">
    <ul>{solution.pros.map(p => <li>{p}</li>)}</ul>
  </Section>

  <Section title="Cons">
    <ul>{solution.cons.map(c => <li>{c}</li>)}</ul>
  </Section>

  <Section title="Risks">
    <ul>{solution.risks.map(r => <li>{r}</li>)}</ul>
  </Section>
</Modal>
```

## Data Models

### API Response Structure

```typescript
interface APIResponse {
  status: "complete" | "processing" | "error";
  request_id: string;
  session_id: string;
  execution_time_ms: number;
  assessment: {
    audit_trail: AuditTrail;
  };
}

interface AuditTrail {
  phase1_initial: Phase1Initial;
  phase2_revision: Phase2Revision;
  phase3_arbitration: Phase3Arbitration;
}

interface Phase1Initial {
  phase: "initial";
  responses: {
    [agentName: string]: AgentResponse;
  };
}

interface Phase2Revision {
  phase: "revision";
  responses: {
    [agentName: string]: AgentResponse;
  };
}

interface Phase3Arbitration {
  phase: "arbitration";
  solution_options: SolutionOption[];
  recommended_solution_id: number;
}

interface AgentResponse {
  agent_name: string;
  recommendation: string;
  reasoning: string;
  data_sources: string[];
  status: "success" | "error";
}

interface SolutionOption {
  solution_id: number;
  title: string;
  description: string;
  recommendations: string[];
  safety_score: number;
  passenger_score: number;
  network_score: number;
  cost_score: number;
  composite_score: number;
  justification: string;
  reasoning: string;
  passenger_impact: string;
  financial_impact: string;
  network_impact: string;
  pros: string[];
  cons: string[];
  risks: string[];
}
```

### Agent Name Mapping

```typescript
const AGENT_NAME_MAP: Record<string, AgentType> = {
  crew_compliance: "Crew_Compliance",
  maintenance: "Maintenance",
  regulatory: "Regulatory",
  network: "Network",
  guest_experience: "Guest_Experience",
  cargo: "Cargo",
  finance: "Finance",
};
```

### Risk Level Derivation

```typescript
function deriveRiskLevel(solution: SolutionOption): "low" | "medium" | "high" {
  const avgScore =
    (solution.safety_score +
      solution.passenger_score +
      solution.network_score +
      solution.cost_score) /
    4;

  if (avgScore >= 75) return "low";
  if (avgScore >= 50) return "medium";
  return "high";
}
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Property Reflection

After analyzing all acceptance criteria, I identified the following testable properties. Many requirements focus on UI behavior (animations, state transitions, rendering) which are better tested through integration tests. The properties below focus on the core data transformation and business logic that can be tested with property-based testing.

**Redundancy Analysis:**

- Properties 1.1, 1.2, and 1.3 all test phase extraction from audit_trail - these can be combined into a single comprehensive property
- Property 1.7 and 7.5 both test graceful handling of missing fields - these are the same requirement
- Properties 2.4, 5.4, and 5.7 all test that rendered content includes required fields - these can be combined into a property about complete field rendering

### Properties

**Property 1: Complete Audit Trail Parsing**

_For any_ valid API response containing an audit_trail object, parsing should successfully extract all three phases (phase1_initial, phase2_revision, phase3_arbitration) with their respective data structures intact.

**Validates: Requirements 1.1, 1.2, 1.3**

**Property 2: Agent Name Mapping Consistency**

_For any_ agent name string from the API (lowercase with underscores), the mapping function should produce a valid AgentType enum value that matches the expected PascalCase format.

**Validates: Requirements 1.4**

**Property 3: Agent Response Field Extraction**

_For any_ agent response object from the API, parsing should extract all required fields (recommendation, reasoning, data_sources, status) and include them in the resulting MessageData object.

**Validates: Requirements 1.5**

**Property 4: Solution Option Field Extraction**

_For any_ solution option object from the API, parsing should extract all required fields including solution_id, title, description, recommendations array, all scoring properties (safety_score, passenger_score, network_score, cost_score, composite_score), and all impact details (justification, reasoning, passenger_impact, financial_impact, network_impact, pros, cons, risks).

**Validates: Requirements 1.6**

**Property 5: Graceful Handling of Missing Fields**

_For any_ API response with missing or null fields, the ResponseMapper should not throw errors and should provide sensible default values (empty strings for text, empty arrays for lists, 0 for numbers, false for booleans) allowing processing to continue.

**Validates: Requirements 1.7, 7.5**

**Property 6: Cross-Impact Round Flagging**

_For any_ message created from phase2_revision responses, the resulting MessageData object should have the isCrossImpactRound flag set to true, while messages from phase1_initial should have it set to false or undefined.

**Validates: Requirements 4.5**

**Property 7: Solution Recommendation Identification**

_For any_ solution option where solution_id matches the recommended_solution_id from phase3_arbitration, the resulting Solution object should have the recommended flag set to true, while all other solutions should have it set to false.

**Validates: Requirements 5.3**

**Property 8: Risk Level Derivation**

_For any_ solution option with scoring properties, the derived risk level should be 'low' when the average of all scores is >= 75, 'medium' when >= 50, and 'high' when < 50, ensuring consistent risk assessment across all solutions.

**Validates: Requirements 5.5**

**Property 9: Complete Content Rendering**

_For any_ MessageData object with populated fields, the rendered output should include all non-empty fields (recommendation, reasoning, data_sources) in the final HTML/JSX structure, ensuring no data is lost during rendering.

**Validates: Requirements 2.4, 5.4, 5.7**

## Error Handling

### Parsing Errors

**Missing Audit Trail:**

- If `assessment.audit_trail` is missing, log warning and return empty arrays
- Display user-friendly message: "No orchestration data available"
- Allow UI to render in degraded state

**Invalid Phase Structure:**

- If a phase object is malformed, skip that phase and continue with others
- Log detailed error for debugging
- Display partial results with warning indicator

**Agent Response Errors:**

- If an agent response has `status: "error"`, include it in the message stream
- Display error indicator in AgentMessage component
- Show error details in expandable section

### API Errors

**Network Failures:**

- Catch fetch errors and display retry option
- Preserve session_id for retry attempts
- Show user-friendly error message

**Timeout Errors:**

- Display progress indicator during long-running requests
- Allow user to cancel and retry
- Provide estimated time remaining

**Cross-Impact Failures:**

- If phase2 API call fails, log error and continue with phase1 data
- Update arbitrator analysis to indicate partial results
- Allow user to retry cross-impact analysis

### Data Validation

**Score Validation:**

- Clamp all score values to 0-100 range
- If score is NaN or undefined, use 50 as default
- Log validation warnings for debugging

**Array Validation:**

- If recommendations/pros/cons/risks is not an array, convert to empty array
- If array contains non-string values, filter them out
- Ensure at least one recommendation exists per solution

## Testing Strategy

### Dual Testing Approach

This feature requires both **unit tests** and **property-based tests** for comprehensive coverage:

**Unit Tests** focus on:

- Specific example API responses with known structures
- Edge cases like empty arrays, null values, malformed data
- Error conditions and error handling paths
- Integration between ResponseMapper and React components
- UI state transitions and event handlers

**Property-Based Tests** focus on:

- Universal properties that hold for all valid inputs
- Comprehensive input coverage through randomization
- Data transformation correctness across many scenarios
- Invariants that must be maintained during parsing

### Property-Based Testing Configuration

**Library:** Use `fast-check` for TypeScript property-based testing

**Configuration:**

- Minimum 100 iterations per property test
- Each test must reference its design document property
- Tag format: `// Feature: orchestration-ui-enhancement, Property N: [property text]`

**Example Test Structure:**

```typescript
import fc from "fast-check";

// Feature: orchestration-ui-enhancement, Property 1: Complete Audit Trail Parsing
test("should extract all three phases from audit trail", () => {
  fc.assert(
    fc.property(
      fc.record({
        phase1_initial: fc.record({
          responses: fc.dictionary(fc.string(), fc.anything()),
        }),
        phase2_revision: fc.record({
          responses: fc.dictionary(fc.string(), fc.anything()),
        }),
        phase3_arbitration: fc.record({
          solution_options: fc.array(fc.anything()),
        }),
      }),
      (auditTrail) => {
        const result = ResponseMapper.parseAuditTrail(auditTrail);
        expect(result.phase1Messages).toBeDefined();
        expect(result.phase2Messages).toBeDefined();
        expect(result.solutions).toBeDefined();
      },
    ),
    { numRuns: 100 },
  );
});
```

### Unit Testing Focus Areas

**ResponseMapper Tests:**

- Test with real API response examples
- Test with minimal valid responses
- Test with missing optional fields
- Test with invalid data types
- Test error handling paths

**Component Tests:**

- Test OrchestrationView with mock API responses
- Test AgentMessage rendering with various MessageData
- Test ArbitratorPanel with different solution counts
- Test sequential animation timing
- Test user interactions (button clicks, solution selection)

**Integration Tests:**

- Test complete flow from API response to UI display
- Test cross-impact analysis workflow
- Test solution selection and decision message creation
- Test error recovery and retry logic

### Test Coverage Goals

- **ResponseMapper:** 100% coverage (pure functions, easily testable)
- **Components:** 80% coverage (focus on logic, not styling)
- **Integration:** Key user flows covered (phase1 → phase2 → decision)

### Testing Tools

- **Jest:** Test runner and assertion library
- **React Testing Library:** Component testing
- **fast-check:** Property-based testing
- **MSW (Mock Service Worker):** API mocking for integration tests
