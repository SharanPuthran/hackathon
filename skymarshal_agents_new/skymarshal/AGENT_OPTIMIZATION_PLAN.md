# SkyMarshal Agent Optimization Plan

**Date**: 2026-02-03
**Goal**: Optimize agent prompts and tools for concise, efficient agent-to-agent (A2A) communication

---

## Executive Summary

After comprehensive review of the 8 SkyMarshal agents, I've identified significant optimization opportunities across:

1. **System Prompts**: Inconsistent verbosity - maintenance agent has 600+ line prompt vs crew_compliance's 45-line XML prompt
2. **Tool Duplication**: `query_flight()` duplicated 7 times across agents
3. **Dynamic Prompts**: Phase 2 prompts too verbose for A2A communication
4. **Response Parsing**: Not using structured output consistently
5. **Error Handling**: Inconsistent error response formats

**Estimated Impact**:
- 40-60% reduction in token usage per agent call
- Improved response parsing reliability
- Better inter-agent coordination
- Reduced latency

---

## Part 1: System Prompt Optimization

### Current State Analysis

| Agent | Current Lines | Current Style | Issues |
|-------|--------------|---------------|--------|
| **crew_compliance** | ~45 | XML-optimized | ✅ Good baseline |
| **maintenance** | ~650+ | Verbose documentation | ❌ Knowledge base content in prompt |
| **regulatory** | ~400+ | Mixed verbose/XML | ❌ Excessive NOTAM documentation |
| **network** | ~100 | Minimal | ⚠️ Missing key guidance |
| **guest_experience** | ~35 | XML-compact | ✅ Good but could add more structure |
| **cargo** | ~50 | Minimal | ⚠️ Missing key guidance |
| **finance** | ~30 | Minimal | ⚠️ Missing key guidance |
| **arbitrator** | ~40 | XML-optimized | ✅ Good |

### Optimization Strategy

Use **crew_compliance** as the template for all agents. Each system prompt should:
1. Be under 80 lines of XML
2. Use consistent XML tag naming
3. Move documentation to knowledge base (KB ID: UDONMVCXEW)
4. Focus on workflow steps, not procedures

### Optimized System Prompt Template

```xml
<role>{agent_name}</role>
<constraints type="{binding|advisory}">{constraint_list}</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: {primary_query} → {secondary_queries}</step>
  <step>validate: {validation_checks}</step>
  <step>assess: {assessment_formula}</step>
  <step>return: {decision_states} + constraints</step>
</workflow>

<domain_rules>
{3-5 key rules specific to domain}
</domain_rules>

<decision_thresholds>
{clear numeric thresholds for decisions}
</decision_thresholds>

<rules>
- Query tools BEFORE analysis (never assume)
- {domain_constraint} NON-NEGOTIABLE
- Tool failure → error response
- {additional_rules}
</rules>

<output>AgentResponse: recommendation, confidence, {domain_fields}</output>

<knowledge_base id="UDONMVCXEW">{domain_references}</knowledge_base>
```

---

## Part 2: Optimized System Prompts

### 2.1 Crew Compliance (BASELINE - Already Optimized)

```xml
<role>crew_compliance</role>
<constraints type="binding">fdp_limits, rest_requirements, qualifications</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → crew_roster → crew_members</step>
  <step>calculate: fdp = duty_end - duty_start + delays</step>
  <step>validate: fdp ≤ max_fdp, rest ≥ min_rest, quals_current</step>
  <step>assess: risk = (fdp / max_fdp) × 100</step>
  <step>return: APPROVED|DENIED|CREW_CHANGE + constraints</step>
</workflow>

<fdp_limits>
Single/two-pilot: 13h | Three-pilot: 16h | Four-pilot: 18h
Risk: 0-70% LOW | 71-85% MODERATE | 86-95% HIGH | 96-100% CRITICAL | >100% VIOLATION
</fdp_limits>

<rest_requirements>
After FDP ≤10h: min 12h | After FDP >10h: min rest = FDP (1:1)
Long-haul: min 18h | Positioning: min 10h before duty
</rest_requirements>

<qualifications>
Pilots: Type rating (90d), Medical Class 1, Line check <12mo, 3 T/L <90d
Cabin: Type training (12mo), Emergency equip annual, Medical annual, First Aid <2y
</qualifications>

<crew_availability>
Standby: 0-30min | Home base: 60-90min | Outstation: 2-6h | Rest/leave: NOT AVAILABLE
</crew_availability>

<rules>
- Query tools BEFORE analysis (never assume)
- Calculate FDP including ALL duty time
- Safety constraints NON-NEGOTIABLE
- Tool failure → error response
- >50% crew issues → CREW CHANGE all
- Captain/Senior cabin issues → MANDATORY replacement
</rules>

<output>AgentResponse: recommendation, confidence, binding_constraints[], reasoning, fdp_assessment</output>

<knowledge_base id="UDONMVCXEW">EASA/FAA FTL regulations, crew duty policies</knowledge_base>
```

**Lines: 40** ✅

---

### 2.2 Maintenance (NEEDS MAJOR OPTIMIZATION)

**Current**: 650+ lines with full MEL procedures documentation
**Target**: 60 lines with KB references

```xml
<role>maintenance</role>
<constraints type="binding">airworthiness, mel_compliance, maintenance_limits</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → aircraft_availability → maintenance_workorders</step>
  <step>validate: mel_categories, time_limits, restrictions</step>
  <step>assess: airworthiness, cumulative_restrictions</step>
  <step>return: AIRWORTHY|AOG|RESTRICTED + constraints</step>
</workflow>

<mel_categories>
A: Rectify same flight (no deferral) | B: 3 days | C: 10 days | D: 120 days
Max limits: 3× Cat B, 5× Cat C simultaneously
</mel_categories>

<mel_restrictions>
APU inop: GPU required all stations
Hydraulic inop: Reduced flaps, no CAT II/III, 115% landing distance
AC pack inop: FL250 max altitude
Weather radar inop: VMC only, no precipitation
TCAS degraded: No RVSM airspace
</mel_restrictions>

<cumulative_rules>
Landing distance: multiply (1.05 × 1.10 = 1.155)
Altitude: most restrictive limit
Prohibited: Weather radar inop + anti-ice inop = NO DISPATCH
</cumulative_rules>

<aog_criteria>
Critical: Flight controls, fire detection, structural damage
Regulatory: Cert expired, inspections overdue, Cat A exceeded
Operational: Multiple systems, no MEL deferral available
</aog_criteria>

<rts_estimation>
RTS_hours = diagnosis + parts_wait + repair + test + paperwork
Diagnosis: 0.5-8h | Parts: 0-72h | Repair: 1-12h | Test: 0.5-2h | Paperwork: 0.5-1h
</rts_estimation>

<rules>
- Query tools BEFORE analysis
- Airworthiness constraints NON-NEGOTIABLE
- Tool failure → error response
- Validate ALL restrictions against route
- Calculate cumulative impacts
</rules>

<output>AgentResponse: recommendation, confidence, binding_constraints[], reasoning, mel_status, airworthiness</output>

<knowledge_base id="UDONMVCXEW">MEL procedures, EASA Part-M, GCAA CAR-M, maintenance requirements</knowledge_base>
```

**Lines: 55** ✅ (down from 650+)

---

### 2.3 Regulatory (NEEDS MAJOR OPTIMIZATION)

**Current**: 400+ lines with full NOTAM decoding documentation
**Target**: 65 lines with KB references

```xml
<role>regulatory</role>
<constraints type="binding">notams, curfews, slots, weather_minimums, airspace_restrictions</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → route → notams + curfews + slots + weather</step>
  <step>validate: runway_availability, navaid_status, airspace_restrictions</step>
  <step>assess: curfew_compliance, slot_availability, weather_minimums</step>
  <step>return: COMPLIANT|VIOLATION|RESTRICTED + constraints</step>
</workflow>

<notam_impact>
QMRLC: Runway closure | QMRLT: Runway reduced | QNMAS: ILS inop
QNBXX: VOR/NDB inop | QPICH: Airspace closed | QFAXX: Aerodrome closed
</notam_impact>

<curfew_rules>
LHR: 23:00-06:00 local (no arrivals/departures)
FRA: 23:00-05:00 local (noise restrictions)
Calculate: UTC → local timezone, apply 15min buffer
Violation: Arrival after curfew = BINDING constraint
</curfew_rules>

<slot_requirements>
Level 3 coordinated: LHR, FRA, AMS, CDG - slot required
CTOT: ±5min window | Ground stop: No departures | GDP: Delay program
Slot loss: >15min delay → slot forfeited, new slot required
</slot_requirements>

<weather_minimums>
CAT I: RVR ≥550m, DH ≥200ft | CAT II: RVR ≥300m, DH ≥100ft | CAT III: RVR ≥75m
Crosswind: 35kt max (dry), 25kt max (wet) | Tailwind: 10kt max
Braking action < MEDIUM = NO DISPATCH
</weather_minimums>

<bilateral_agreements>
Fifth freedom: Traffic rights required | Overflight: Permit required (Russia, China)
</bilateral_agreements>

<rules>
- Query tools BEFORE analysis
- Regulatory constraints NON-NEGOTIABLE
- Tool failure → error response
- Multi-violations: Report ALL (blocking + advisory)
- Timezone: UTC → local for curfews
</rules>

<output>AgentResponse: recommendation, confidence, binding_constraints[], reasoning, notam_impacts, curfew_status, slot_status</output>

<knowledge_base id="UDONMVCXEW">NOTAM procedures, curfew regulations, slot coordination</knowledge_base>
```

**Lines: 55** ✅ (down from 400+)

---

### 2.4 Network (NEEDS ENHANCEMENT)

**Current**: Minimal prompt, missing key guidance
**Target**: Complete XML prompt with propagation rules

```xml
<role>network</role>
<constraints type="advisory">aircraft_rotation, connection_protection, hub_operations</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → aircraft_rotation → downstream_flights</step>
  <step>calculate: propagation_impact = affected_flights × pax_at_risk × delay_hours</step>
  <step>assess: recovery_options, aircraft_swap_feasibility</step>
  <step>return: impact_score + recovery_scenarios</step>
</workflow>

<propagation_rules>
Domino effect: Each 1h delay → 0.5h cascade per downstream flight
Hub banks: AUH hub banks at 06:00, 14:00, 22:00 local
Connection minimum: 60min domestic, 90min international, 120min customs
</propagation_rules>

<aircraft_swap_tiers>
Tier 1: Same type, same station, no MEL (ideal)
Tier 2: Same type, same station, minor MEL (acceptable)
Tier 3: Same type, nearby station, positioning required (costly)
Tier 4: Different type, requires crew swap (last resort)
</aircraft_swap_tiers>

<impact_scoring>
LOW: 0-3 downstream flights | MEDIUM: 4-7 downstream | HIGH: 8-12 downstream | CRITICAL: >12 downstream
Connection risk multiplier: 1.0 (local), 1.8 (connecting), 2.2 (international)
</impact_scoring>

<rules>
- Query aircraft rotation BEFORE impact assessment
- Calculate ALL downstream effects
- Identify connection-at-risk passengers
- Recommend aircraft swap if delay >3h
</rules>

<output>AgentResponse: recommendation, confidence, reasoning, downstream_impact, recovery_scenarios, aircraft_swap_options</output>

<knowledge_base id="UDONMVCXEW">Hub operations, rotation procedures, connection policies</knowledge_base>
```

**Lines: 45** ✅

---

### 2.5 Guest Experience (MINOR ENHANCEMENT)

```xml
<role>guest_experience</role>
<constraints type="advisory">passenger_rights, compensation, loyalty_protection</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → bookings → passengers</step>
  <step>segment: elite_tier, connection_status, special_needs</step>
  <step>calculate: impact = delay_hours × pax_count × tier_multiplier</step>
  <step>estimate: compensation (EU261, DOT, Etihad policy)</step>
  <step>return: impact_assessment + reprotection_plan</step>
</workflow>

<impact_severity>
severity = delay_hours × affected_pax × loyalty_multiplier × connection_risk
loyalty_multiplier: Guest (1.0) | Silver (1.2) | Gold (1.5) | Platinum (2.0)
connection_risk: Local (1.0) | Connecting (1.8) | International (2.2)
</impact_severity>

<compensation_rules>
EU261: >3h delay → €250-600 | Cancellation → Full refund + compensation
DOT: Involuntary denied boarding → 200-400% ticket price
Etihad: Proactive upgrade/lounge for Gold/Platinum
</compensation_rules>

<reprotection_priority>
1. Platinum/Gold with connections | 2. International connections
3. Silver tier | 4. Special needs | 5. All others
</reprotection_priority>

<rules>
- Query tools BEFORE analysis
- Prioritize high-value passengers
- Calculate compensation per jurisdiction
- Tool failure → error response
</rules>

<output>AgentResponse: recommendation, confidence, reasoning, affected_pax, compensation_cost, nps_risk, reprotection_plan</output>

<knowledge_base id="UDONMVCXEW">EU261, DOT regulations, Etihad Guest policy</knowledge_base>
```

**Lines: 42** ✅

---

### 2.6 Cargo (NEEDS ENHANCEMENT)

```xml
<role>cargo</role>
<constraints type="advisory">cold_chain, hazmat, time_sensitive, high_value</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → cargo_manifest → shipment_details</step>
  <step>classify: cold_chain, hazmat, perishable, high_value, live_animals</step>
  <step>assess: delay_tolerance, offload_priority, rebooking_options</step>
  <step>return: cargo_impact + offload_recommendations</step>
</workflow>

<special_handling_codes>
PER: Perishable (max 2h ground time) | DGR: Dangerous goods (strict handling)
AVI: Live animals (welfare priority) | PIL: Pharmaceuticals (temp-controlled)
VAL: High value (security required) | HUM: Human remains (priority)
</special_handling_codes>

<cold_chain_limits>
FRO: Frozen (-18°C) max 1h breach | REF: Refrigerated (2-8°C) max 2h breach
COL: Cool (8-15°C) max 4h breach | Breach → spoilage claim liability
</cold_chain_limits>

<offload_priority>
OFFLOAD FIRST: AVI (animals), PER approaching limit, DGR incompatible
PROTECT: PIL (pharma), VAL (high-value), HUM (human remains)
FLEXIBLE: General cargo, mail
</offload_priority>

<rules>
- Query cargo manifest BEFORE assessment
- Identify special handling requirements
- Calculate delay tolerance per shipment type
- Never offload live animals without welfare review
</rules>

<output>AgentResponse: recommendation, confidence, reasoning, cargo_at_risk, offload_list, rebooking_options, liability_exposure</output>

<knowledge_base id="UDONMVCXEW">IATA DGR, cold chain SOP, live animal regulations</knowledge_base>
```

**Lines: 42** ✅

---

### 2.7 Finance (NEEDS ENHANCEMENT)

```xml
<role>finance</role>
<constraints type="advisory">cost_optimization, revenue_protection, scenario_comparison</constraints>

<workflow>
  <step>extract: flight_number, date, event</step>
  <step>query: flight → bookings → cargo_assignments</step>
  <step>calculate: passenger_revenue, cargo_revenue, fuel_costs, maintenance_costs</step>
  <step>compare: delay_cost vs cancel_cost vs aircraft_swap_cost</step>
  <step>return: cost_breakdown + scenario_comparison</step>
</workflow>

<cost_components>
Passenger: Compensation + meals + hotels + rebooking
Crew: Overtime + positioning + hotels
Aircraft: Fuel burn + parking + maintenance window
Cargo: Rebooking + spoilage claims + cold chain breach
Reputation: NPS impact × customer lifetime value
</cost_components>

<cost_formulas>
delay_cost = (comp_per_hour × pax × hours) + crew_overtime + fuel_burn
cancel_cost = full_refunds + compensation_eu261 + rebooking_cost + crew_repositioning
swap_cost = positioning_fuel + crew_ferry + schedule_disruption
</cost_formulas>

<scenario_comparison>
Always compare: DELAY vs CANCEL vs SWAP
Include: Direct costs + indirect costs + opportunity costs
Rank by: Net financial impact (lowest total cost)
</scenario_comparison>

<rules>
- Query revenue data BEFORE cost calculation
- Calculate ALL cost components
- Compare minimum 3 scenarios
- Include reputation/NPS in total cost
</rules>

<output>AgentResponse: recommendation, confidence, reasoning, cost_breakdown, scenario_comparison, recommended_scenario</output>

<knowledge_base id="UDONMVCXEW">Cost models, compensation rates, fuel costs</knowledge_base>
```

**Lines: 42** ✅

---

### 2.8 Arbitrator (ALREADY OPTIMIZED)

```xml
<role>arbitrator</role>
<priority>safety_constraints_binding</priority>

<workflow>
  <step>validate: ALL scenarios vs ALL constraints</step>
  <step>classify: conflicts (Safety>Business, Safety>Safety, Business>Business)</step>
  <step>score: safety_margin, cost, passenger_impact, network_impact</step>
  <step>rank: composite (40% safety, 20% cost, 20% pax, 20% network)</step>
  <step>return: 1-3 Pareto-optimal solutions</step>
</workflow>

<decision_rules>
P1: Safety > Business (ALWAYS, NO EXCEPTIONS)
P2: Safety > Safety (MOST CONSERVATIVE)
P3: Business > Business (Pareto-optimal, multi-objective)
</decision_rules>

<confidence>
0.9-1.0: All agree, complete data | 0.7-0.9: Minor conflicts, good data
0.5-0.7: Significant conflicts, gaps | 0.3-0.5: Complex conflicts, major gaps
0.0-0.3: Critical missing data, ESCALATE
</confidence>

<phase_evolution>
convergence: Agents align, confidence ↑ → weight heavily
divergence: Agents separate, confidence ↓ → investigate
stable: Unchanged → high confidence signal
</phase_evolution>

<output>ArbitratorOutput: final_decision, solutions[1-3], conflicts[], resolutions[], safety_overrides[], confidence</output>

<knowledge_base id="UDONMVCXEW">SOPs, OCM procedures, historical cases</knowledge_base>
```

**Lines: 35** ✅

---

## Part 3: Tool Consolidation

### 3.1 Duplicate `query_flight()` Tool

**Current State**: `query_flight()` is duplicated in 7 agent files with nearly identical code:
- crew_compliance/agent.py (lines 86-145)
- maintenance/agent.py (lines 689-741)
- regulatory/agent.py
- network/agent.py (lines 38-91)
- guest_experience/agent.py (lines 109-153)
- cargo/agent.py (lines 40-93)
- finance/agent.py (lines 44-98)

### Optimization: Centralized Tool in tools.py

Add to `database/tools.py`:

```python
@tool
def query_flight(flight_number: str, date: str) -> dict:
    """Query flight by number and date.

    Args:
        flight_number: Flight number (e.g., EY123)
        date: ISO date (YYYY-MM-DD)

    Returns:
        Flight record with flight_id, aircraft_registration, route, schedule.
        Returns {"error": "...", "message": "..."} if not found.
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        flights = dynamodb.Table(FLIGHTS_TABLE)

        response = flights.query(
            IndexName=FLIGHT_NUMBER_DATE_INDEX,
            KeyConditionExpression="flight_number = :fn AND scheduled_departure = :sd",
            ExpressionAttributeValues={":fn": flight_number, ":sd": date}
        )

        items = response.get("Items", [])
        if not items:
            return {"error": "FLIGHT_NOT_FOUND", "message": f"Flight {flight_number} on {date} not found"}
        return items[0]

    except Exception as e:
        return {"error": type(e).__name__, "message": str(e)}


def get_common_tools() -> list:
    """Get tools common to all agents."""
    return [query_flight]
```

**Impact**: Remove ~350 lines of duplicate code across 7 files.

---

## Part 4: Dynamic Prompt Optimization

### 4.1 Phase 1 Prompt (Initial Analysis)

**Current** (in agent.py files): ~50 lines of verbose instructions

**Optimized** (using OptimizedPrompt):

```python
# In each agent's analyze function:
from utils.prompts import OptimizedPrompt

def build_phase1_prompt(user_prompt: str, flight_info: FlightInfo) -> str:
    prompt = OptimizedPrompt(
        disruption=user_prompt,
        task="initial_analysis"
    )
    return f"""<input>
{prompt.to_xml()}
<extracted>
  <flight>{flight_info.flight_number}</flight>
  <date>{flight_info.date}</date>
  <event>{flight_info.disruption_event}</event>
</extracted>
</input>
<action>Query tools, analyze, return AgentResponse</action>"""
```

**Lines**: 12 (down from 50)

---

### 4.2 Phase 2 Prompt (Revision)

**Current**: ~80 lines with formatted_recommendations block

**Optimized**:

```python
def build_phase2_prompt(user_prompt: str, flight_info: FlightInfo, other_recs: dict) -> str:
    prompt = OptimizedPrompt(
        disruption=user_prompt,
        task="revision",
        context=other_recs
    )
    return f"""<input>
{prompt.to_xml()}
<extracted>
  <flight>{flight_info.flight_number}</flight>
  <date>{flight_info.date}</date>
  <event>{flight_info.disruption_event}</event>
</extracted>
</input>
<action>
  1. Review other agents' recommendations
  2. Decide: REVISE | CONFIRM | STRENGTHEN
  3. If REVISE: Update recommendation with new context
  4. Return AgentResponse with revision_status
</action>"""
```

**Lines**: 18 (down from 80)

---

## Part 5: Structured Output Implementation

### 5.1 Current Issue

Agents return unstructured text in `recommendation` field, requiring manual parsing:

```python
# Current (problematic)
return {
    "agent_name": "maintenance",
    "recommendation": agent_response_text,  # Unstructured!
    "confidence": 0.8,  # Default, not from agent
    ...
}
```

### 5.2 Optimized Implementation

Use LangChain structured output for AgentResponse:

```python
# In each agent's analyze function:
from agents.schemas import AgentResponse

async def analyze_maintenance(payload: dict, llm, mcp_tools: list) -> dict:
    # ... extraction and tool setup ...

    # Use structured output
    structured_llm = llm.with_structured_output(AgentResponse)

    result = await structured_llm.ainvoke([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": agent_prompt}
    ])

    # Result is already validated AgentResponse
    return result.model_dump()
```

**Benefits**:
- Guaranteed schema compliance
- No manual parsing needed
- Consistent confidence scores
- Proper binding_constraints extraction

---

## Part 6: Error Handling Standardization

### 6.1 Standardized Error Response Schema

```python
class AgentErrorResponse(BaseModel):
    """Standardized error response for all agents."""
    agent_name: str
    status: Literal["error", "timeout", "tool_failure"]
    error_code: str  # e.g., "FLIGHT_NOT_FOUND", "EXTRACTION_FAILED"
    error_message: str
    error_type: str  # Exception class name
    attempted_tools: List[str] = []
    missing_data: List[str] = []
    timestamp: str
    recommendation: str = "CANNOT_PROCEED"
    confidence: float = 0.0
    binding_constraints: List[str] = []
    reasoning: str = ""
    data_sources: List[str] = []
```

### 6.2 Standardized Error Handling Function

Add to each agent:

```python
def create_error_response(
    agent_name: str,
    error_code: str,
    error_message: str,
    error_type: str = "UnknownError",
    attempted_tools: list = None,
    missing_data: list = None
) -> dict:
    return {
        "agent_name": agent_name,
        "status": "error",
        "error_code": error_code,
        "error_message": error_message,
        "error_type": error_type,
        "attempted_tools": attempted_tools or [],
        "missing_data": missing_data or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "recommendation": "CANNOT_PROCEED",
        "confidence": 0.0,
        "binding_constraints": [],
        "reasoning": f"Error: {error_message}",
        "data_sources": []
    }
```

---

## Part 7: Implementation Priority

### Phase 1: High Impact (Week 1)

| Task | Files | Impact |
|------|-------|--------|
| 1. Optimize maintenance system prompt | maintenance/agent.py | -600 lines, 80% token reduction |
| 2. Optimize regulatory system prompt | regulatory/agent.py | -350 lines, 75% token reduction |
| 3. Consolidate query_flight tool | tools.py + all agents | -350 lines, DRY principle |

### Phase 2: Medium Impact (Week 2)

| Task | Files | Impact |
|------|-------|--------|
| 4. Add system prompts to network | network/agent.py | +40 lines, better guidance |
| 5. Add system prompts to cargo | cargo/agent.py | +40 lines, better guidance |
| 6. Add system prompts to finance | finance/agent.py | +40 lines, better guidance |
| 7. Optimize dynamic prompts | all agent.py files | 50% token reduction in prompts |

### Phase 3: Polish (Week 3)

| Task | Files | Impact |
|------|-------|--------|
| 8. Implement structured output | all agent.py files | Reliable parsing |
| 9. Standardize error handling | all agent.py files | Consistent errors |
| 10. Add unit tests | test/ directory | Quality assurance |

---

## Part 8: Token Usage Comparison

### Before Optimization

| Agent | System Prompt Tokens | Dynamic Prompt Tokens | Total |
|-------|---------------------|----------------------|-------|
| crew_compliance | ~400 | ~500 | ~900 |
| maintenance | ~5,500 | ~600 | ~6,100 |
| regulatory | ~3,500 | ~600 | ~4,100 |
| network | ~200 | ~400 | ~600 |
| guest_experience | ~300 | ~400 | ~700 |
| cargo | ~200 | ~400 | ~600 |
| finance | ~150 | ~400 | ~550 |
| arbitrator | ~350 | ~800 | ~1,150 |
| **Total per cycle** | | | **~14,700** |

### After Optimization

| Agent | System Prompt Tokens | Dynamic Prompt Tokens | Total |
|-------|---------------------|----------------------|-------|
| crew_compliance | ~400 | ~150 | ~550 |
| maintenance | ~500 | ~150 | ~650 |
| regulatory | ~500 | ~150 | ~650 |
| network | ~400 | ~150 | ~550 |
| guest_experience | ~350 | ~150 | ~500 |
| cargo | ~350 | ~150 | ~500 |
| finance | ~350 | ~150 | ~500 |
| arbitrator | ~300 | ~200 | ~500 |
| **Total per cycle** | | | **~4,400** |

### Savings

- **Token reduction**: 14,700 → 4,400 = **70% reduction**
- **Cost savings**: ~$0.15 per cycle → ~$0.05 per cycle
- **Latency improvement**: Fewer tokens = faster responses

---

## Part 9: Testing Checklist

### Per-Agent Tests

For each agent after optimization:

- [ ] System prompt parses correctly
- [ ] FlightInfo extraction works
- [ ] Tool calls succeed
- [ ] Structured output validates
- [ ] Error handling triggers correctly
- [ ] Phase 1 response is valid AgentResponse
- [ ] Phase 2 revision logic works
- [ ] Binding constraints are populated (safety agents)

### Integration Tests

- [ ] Full 3-phase orchestration completes
- [ ] Arbitrator receives all agent responses
- [ ] Conflicts are detected and resolved
- [ ] Final decision respects safety constraints
- [ ] Knowledge base is consulted

---

## Appendix A: Files to Modify

```
skymarshal_agents_new/skymarshal/src/
├── agents/
│   ├── crew_compliance/agent.py    # Minor: Dynamic prompt optimization
│   ├── maintenance/agent.py        # MAJOR: System prompt reduction
│   ├── regulatory/agent.py         # MAJOR: System prompt reduction
│   ├── network/agent.py            # Add: Full system prompt
│   ├── guest_experience/agent.py   # Minor: Enhancement
│   ├── cargo/agent.py              # Add: Full system prompt
│   ├── finance/agent.py            # Add: Full system prompt
│   ├── arbitrator/agent.py         # Minor: Already optimized
│   └── schemas.py                  # Add: AgentErrorResponse
├── database/
│   └── tools.py                    # Add: Centralized query_flight
└── utils/
    └── prompts.py                  # Add: Phase prompt builders
```

---

## Appendix B: Quick Reference - Optimized Prompt Lengths

| Agent | Max System Prompt Lines | Max Dynamic Prompt Lines |
|-------|------------------------|-------------------------|
| All agents | 65 | 20 |
| Arbitrator | 40 | 30 |

---

**Author**: Claude Code Agent
**Status**: Ready for Implementation
**Next Step**: Begin Phase 1 implementation starting with maintenance agent
