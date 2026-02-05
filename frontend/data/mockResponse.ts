/**
 * Mock Response Data
 *
 * This file contains backup mock data to be used when:
 * 1. API response takes longer than the configured timeout
 * 2. Mock mode is enabled via configuration
 *
 * The data structure mirrors the actual API response format.
 *
 * Configuration:
 * - Set VITE_MOCK_SOLUTION environment variable to switch between solutions
 * - Available solutions: solution_1, solution_2 (add more as needed)
 */

import { getConfig } from '../config/env';

// Import solution JSON files
import solution1 from './responses/solution_1.json';
import solution2 from './responses/solution_2.json';

// Define a flexible type for mock responses (allows different solution structures)
type MockResponse = Record<string, unknown>;

// Solution registry - add new solutions here
const SOLUTIONS_REGISTRY: Record<string, MockResponse> = {
  'solution_1': solution1,
  'solution_2': solution2,
};

/**
 * Get list of available solution keys
 */
export const getAvailableSolutions = (): string[] => Object.keys(SOLUTIONS_REGISTRY);

/**
 * Get the currently selected mock solution based on configuration
 */
const getSelectedSolution = (): MockResponse => {
  const config = getConfig();
  const solutionKey = config.mockSolutionFile || 'solution_1';

  if (!(solutionKey in SOLUTIONS_REGISTRY)) {
    console.warn(`Mock solution "${solutionKey}" not found, falling back to solution_1`);
    return SOLUTIONS_REGISTRY['solution_1'];
  }

  return SOLUTIONS_REGISTRY[solutionKey];
};

/**
 * The currently selected mock response
 * Note: This is evaluated when the module is imported, so changes to VITE_MOCK_SOLUTION
 * require a page refresh or dev server restart to take effect.
 */
export const MOCK_RESPONSE = getSelectedSolution();

/**
 * Legacy inline mock data (kept for reference/fallback)
 * To use static data instead of JSON files, uncomment this and comment out the above
 */
export const MOCK_RESPONSE_STATIC = {
  "status": "success",
  "thread_id": "042ed3eb-1e18-4f44-93df-251b5dd7d77a",
  "final_decision": {
    "final_decision": "Aircraft Swap - Maintain Schedule: Execute immediate aircraft swap from A6-BNC to serviceable B787-9 from available fleet. Maintain scheduled departure time 01:00 UTC. Assign qualified crew, notify passengers, prioritize connections.",
    "recommendations": [
      "Swap to serviceable B787-9 aircraft",
      "Maintain 01:00 UTC departure time",
      "Assign qualified crew from roster",
      "Notify all 286 passengers of aircraft change",
      "Prioritize 51 connecting passengers for boarding",
      "Ground A6-BNC for maintenance"
    ],
    "conflicts_identified": [],
    "conflict_resolutions": [],
    "safety_overrides": [],
    "justification": "All safety and business agents converged on aircraft swap solution with no binding constraints identified. Safety agents (crew compliance, maintenance, regulatory) confirmed operational feasibility with confidence 0.80-0.85. Network agent identified high priority due to 51 connecting passengers and EY17 rotation dependency. No conflicts detected between agent recommendations - all support maintaining schedule through aircraft substitution.",
    "reasoning": "Applied arbitration framework: (1) Checked for binding constraints - none identified by any safety agent. (2) Reviewed agent evolution - 4 agents revised/strengthened recommendations, 3 stable, indicating convergence toward aircraft swap consensus. (3) Assessed conflict potential - no safety vs business or safety vs safety conflicts present. (4) Evaluated network criticality - HIGH priority flight with 286 PAX and 51 connections justifies resource allocation for aircraft swap. (5) Confirmed regulatory compliance - all curfew, slot, and operational requirements satisfied. (6) Validated crew availability - sufficient qualified crew available per crew compliance agent. Decision confidence high (0.92) due to agent consensus and absence of constraints.",
    "confidence": 0.92,
    "timestamp": "2026-02-03T21:10:32.140768+00:00",
    "model_used": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "duration_seconds": 81.578367,
    "solution_options": [
      {
        "solution_id": 1,
        "title": "Aircraft Swap - Maintain Schedule",
        "description": "Execute immediate aircraft swap from A6-BNC to serviceable B787-9 from available fleet. Maintain scheduled departure time 01:00 UTC. Assign qualified crew, notify passengers, prioritize connections.",
        "recommendations": [
          "Swap to serviceable B787-9 aircraft",
          "Maintain 01:00 UTC departure time",
          "Assign qualified crew from roster",
          "Notify all 286 passengers of aircraft change",
          "Prioritize 51 connecting passengers for boarding",
          "Ground A6-BNC for maintenance"
        ],
        "safety_compliance": "All safety constraints satisfied: crew duty limits compliant, replacement aircraft airworthy, regulatory requirements met (no curfew/slot conflicts)",
        "passenger_impact": {
          "total_passengers": 286,
          "connecting_passengers": 51,
          "delay_minutes": 0,
          "missed_connections": 0,
          "compensation_required": false,
          "passenger_notifications": "Aircraft change notification only"
        },
        "financial_impact": {
          "aircraft_swap_cost": 15000,
          "crew_costs": 0,
          "passenger_compensation": 0,
          "total_estimated_cost": 15000,
          "currency": "USD"
        },
        "network_impact": {
          "downstream_flights_affected": 0,
          "rotation_preserved": true,
          "EY17_connection_protected": true,
          "network_propagation": "None - schedule maintained"
        },
        "safety_score": 95,
        "cost_score": 85,
        "passenger_score": 95,
        "network_score": 95,
        "composite_score": 93,
        "pros": [
          "Zero passenger delay or missed connections",
          "Preserves critical EY17 rotation",
          "No network propagation",
          "All safety requirements satisfied",
          "Minimal financial impact"
        ],
        "cons": [
          "Requires available serviceable B787-9 in fleet",
          "Aircraft swap coordination complexity",
          "Removes one aircraft from spare pool"
        ],
        "risks": [
          "Replacement aircraft may not be immediately available",
          "Crew assignment delays could impact departure",
          "Ground operations coordination challenges at BKK"
        ],
        "confidence": 0.92,
        "estimated_duration": "2 hours",
        "recovery_plan": {
          "solution_id": 1,
          "total_steps": 9,
          "estimated_total_duration": "2.5 hours",
          "steps": [
            {
              "step_number": 1,
              "step_name": "Identify Replacement Aircraft",
              "description": "Locate serviceable B787-9 from available fleet with capacity for 286+ passengers",
              "responsible_agent": "maintenance",
              "dependencies": [],
              "estimated_duration": "15 minutes",
              "automation_possible": true,
              "action_type": "coordinate",
              "parameters": {
                "aircraft_type": "B787-9",
                "minimum_capacity": 286,
                "location": "AUH or regional hub"
              },
              "success_criteria": "Serviceable B787-9 identified and confirmed available",
              "rollback_procedure": null
            },
            {
              "step_number": 2,
              "step_name": "Position Replacement Aircraft",
              "description": "Ferry or reposition replacement aircraft to BKK if not already on station",
              "responsible_agent": "flight_scheduling",
              "dependencies": [1],
              "estimated_duration": "30 minutes",
              "automation_possible": false,
              "action_type": "coordinate",
              "parameters": {
                "destination": "BKK",
                "aircraft_registration": "TBD"
              },
              "success_criteria": "Replacement aircraft on ground at BKK gate",
              "rollback_procedure": null
            },
            {
              "step_number": 3,
              "step_name": "Assign Qualified Crew",
              "description": "Assign qualified crew from roster to replacement aircraft, verify duty time compliance",
              "responsible_agent": "crew_compliance",
              "dependencies": [1],
              "estimated_duration": "20 minutes",
              "automation_possible": true,
              "action_type": "schedule",
              "parameters": {
                "flight": "EY283",
                "aircraft": "replacement B787-9",
                "crew_qualifications": "B787 type rating"
              },
              "success_criteria": "Full crew assigned and duty time verified compliant",
              "rollback_procedure": null
            },
            {
              "step_number": 4,
              "step_name": "Notify Passengers",
              "description": "Send aircraft change notifications to all 286 passengers via SMS, email, and mobile app",
              "responsible_agent": "guest_experience",
              "dependencies": [1],
              "estimated_duration": "10 minutes",
              "automation_possible": true,
              "action_type": "notify",
              "parameters": {
                "flight": "EY283",
                "passenger_count": 286,
                "message_type": "aircraft_change",
                "channels": ["SMS", "email", "app"]
              },
              "success_criteria": "All passengers notified of aircraft change",
              "rollback_procedure": null
            },
            {
              "step_number": 5,
              "step_name": "Transfer Cargo to Replacement Aircraft",
              "description": "Transfer 12.4 tonnes of cargo from A6-BNC to replacement aircraft, prioritizing cold chain shipments (pharmaceuticals, perishables) and maintaining temperature integrity",
              "responsible_agent": "cargo_recovery",
              "dependencies": [2],
              "estimated_duration": "45 minutes",
              "automation_possible": false,
              "action_type": "coordinate",
              "parameters": {
                "total_cargo_kg": 12400,
                "shipment_count": 14,
                "perishable_tonnes": 2.1,
                "pharmaceutical_tonnes": 1.8,
                "cold_chain_required": true,
                "priority_loading": ["pharmaceuticals", "perishables", "live_animals", "high_value", "general"]
              },
              "success_criteria": "All 14 shipments transferred, cold chain integrity verified, weight & balance confirmed",
              "rollback_procedure": "If transfer incomplete, prioritize cold chain cargo and offload non-critical general cargo"
            },
            {
              "step_number": 6,
              "step_name": "Ground A6-BNC for Maintenance",
              "description": "Ground A6-BNC, initiate maintenance inspection and MEL compliance review",
              "responsible_agent": "maintenance",
              "dependencies": [2],
              "estimated_duration": "15 minutes",
              "automation_possible": false,
              "action_type": "coordinate",
              "parameters": {
                "aircraft": "A6-BNC",
                "issue": "mechanical",
                "action": "ground and inspect"
              },
              "success_criteria": "A6-BNC grounded, maintenance work order created",
              "rollback_procedure": null
            },
            {
              "step_number": 7,
              "step_name": "Coordinate Gate Operations",
              "description": "Coordinate with BKK ground operations for gate assignment and aircraft positioning",
              "responsible_agent": "flight_scheduling",
              "dependencies": [2],
              "estimated_duration": "20 minutes",
              "automation_possible": false,
              "action_type": "coordinate",
              "parameters": {
                "airport": "BKK",
                "gate": "TBD",
                "aircraft": "replacement B787-9"
              },
              "success_criteria": "Gate assigned, ground crew briefed, aircraft positioned",
              "rollback_procedure": null
            },
            {
              "step_number": 8,
              "step_name": "Priority Boarding for Connections",
              "description": "Implement priority boarding for 51 connecting passengers to ensure EY17 connections",
              "responsible_agent": "guest_experience",
              "dependencies": [4, 7],
              "estimated_duration": "30 minutes",
              "automation_possible": true,
              "action_type": "coordinate",
              "parameters": {
                "connecting_passengers": 51,
                "downstream_flight": "EY17",
                "boarding_priority": "high"
              },
              "success_criteria": "All 51 connecting passengers boarded first",
              "rollback_procedure": null
            },
            {
              "step_number": 9,
              "step_name": "Depart on Schedule",
              "description": "Complete boarding, close doors, and depart at scheduled 01:00 UTC",
              "responsible_agent": "crew_compliance",
              "dependencies": [3, 5, 8],
              "estimated_duration": "15 minutes",
              "automation_possible": false,
              "action_type": "coordinate",
              "parameters": {
                "scheduled_departure": "01:00 UTC",
                "flight": "EY283"
              },
              "success_criteria": "Flight EY283 departs BKK at 01:00 UTC",
              "rollback_procedure": null
            }
          ],
          "critical_path": [1, 2, 5, 7, 8, 9],
          "contingency_plans": [
            {
              "trigger": "No replacement aircraft available within 2 hours",
              "action": "Escalate to Solution 2 (Delay with aircraft swap)",
              "responsible_agent": "network"
            },
            {
              "trigger": "Crew assignment delays exceed 30 minutes",
              "action": "Source standby crew or adjust crew roster",
              "responsible_agent": "crew_compliance"
            }
          ]
        }
      },
      {
        "solution_id": 2,
        "title": "Aircraft Swap with Controlled Delay",
        "description": "Execute aircraft swap with 2-4 hour delay to allow additional time for positioning and crew coordination. Protect critical connections through rebooking.",
        "recommendations": [
          "Swap to serviceable B787-9 aircraft",
          "Delay departure by 2-4 hours",
          "Rebook 51 connecting passengers on alternative flights",
          "Provide meal vouchers and compensation",
          "Assign qualified crew with extended duty time buffer",
          "Ground A6-BNC for maintenance"
        ],
        "safety_compliance": "All safety constraints satisfied with additional buffer time for crew rest and aircraft preparation",
        "passenger_impact": {
          "total_passengers": 286,
          "connecting_passengers": 51,
          "delay_minutes": 180,
          "missed_connections": 51,
          "compensation_required": true,
          "passenger_notifications": "Delay notification, rebooking confirmations, compensation details"
        },
        "financial_impact": {
          "aircraft_swap_cost": 15000,
          "crew_costs": 5000,
          "passenger_compensation": 25000,
          "rebooking_costs": 15000,
          "total_estimated_cost": 60000,
          "currency": "USD"
        },
        "network_impact": {
          "downstream_flights_affected": 1,
          "rotation_preserved": true,
          "EY17_connection_protected": false,
          "network_propagation": "Moderate - 51 passengers rebooked, EY17 may operate with reduced load"
        },
        "safety_score": 98,
        "cost_score": 60,
        "passenger_score": 55,
        "network_score": 65,
        "composite_score": 75.2,
        "pros": [
          "Higher safety margin with extended preparation time",
          "Reduced operational pressure on crew and ground staff",
          "More flexibility for aircraft positioning",
          "Preserves aircraft rotation"
        ],
        "cons": [
          "Significant passenger delay (3 hours)",
          "51 missed connections requiring rebooking",
          "Higher compensation costs",
          "Moderate network propagation"
        ],
        "risks": [
          "Passenger dissatisfaction and complaints",
          "Rebooking challenges for connecting passengers",
          "Potential crew duty time issues if delay extends",
          "Downstream flight load factor impacts"
        ],
        "confidence": 0.78,
        "estimated_duration": "4 hours",
        "recovery_plan": {
          "solution_id": 2,
          "total_steps": 10,
          "estimated_total_duration": "4 hours",
          "steps": [
            {
              "step_number": 1,
              "step_name": "Identify Replacement Aircraft",
              "description": "Locate serviceable B787-9 from available fleet",
              "responsible_agent": "maintenance",
              "dependencies": [],
              "estimated_duration": "15 minutes",
              "automation_possible": true,
              "action_type": "coordinate",
              "parameters": { "aircraft_type": "B787-9" },
              "success_criteria": "Replacement aircraft identified",
              "rollback_procedure": null
            },
            {
              "step_number": 2,
              "step_name": "Notify Passengers of Delay",
              "description": "Send delay notifications to all 286 passengers with estimated new departure time",
              "responsible_agent": "guest_experience",
              "dependencies": [],
              "estimated_duration": "10 minutes",
              "automation_possible": true,
              "action_type": "notify",
              "parameters": { "delay_duration": "3 hours" },
              "success_criteria": "All passengers notified",
              "rollback_procedure": null
            },
            {
              "step_number": 3,
              "step_name": "Rebook Connecting Passengers",
              "description": "Rebook 51 connecting passengers on alternative flights to final destinations",
              "responsible_agent": "guest_experience",
              "dependencies": [2],
              "estimated_duration": "45 minutes",
              "automation_possible": true,
              "action_type": "rebook",
              "parameters": { "passenger_count": 51 },
              "success_criteria": "All 51 passengers rebooked",
              "rollback_procedure": null
            }
          ],
          "critical_path": [1, 5, 8, 9, 10],
          "contingency_plans": [
            {
              "trigger": "Rebooking capacity insufficient",
              "action": "Charter additional capacity or delay further",
              "responsible_agent": "network"
            }
          ]
        }
      },
      {
        "solution_id": 3,
        "title": "Flight Cancellation with Full Reprotection",
        "description": "Cancel EY283 and rebook all 286 passengers on alternative flights. Ground A6-BNC for comprehensive maintenance. Highest safety margin but significant passenger and network impact.",
        "recommendations": [
          "Cancel EY283 flight",
          "Rebook all 286 passengers on alternative flights",
          "Provide full compensation and hotel accommodation",
          "Ground A6-BNC for comprehensive maintenance inspection",
          "Adjust downstream rotation schedule",
          "Issue public communication about cancellation"
        ],
        "safety_compliance": "Maximum safety margin - no operational pressure, comprehensive maintenance inspection, no crew duty time concerns",
        "passenger_impact": {
          "total_passengers": 286,
          "connecting_passengers": 51,
          "delay_minutes": 720,
          "missed_connections": 286,
          "compensation_required": true,
          "passenger_notifications": "Cancellation notification, rebooking confirmations, hotel vouchers, full compensation"
        },
        "financial_impact": {
          "aircraft_swap_cost": 0,
          "crew_costs": 8000,
          "passenger_compensation": 120000,
          "rebooking_costs": 85000,
          "hotel_accommodation": 45000,
          "total_estimated_cost": 258000,
          "currency": "USD"
        },
        "network_impact": {
          "downstream_flights_affected": 3,
          "rotation_preserved": false,
          "EY17_connection_protected": false,
          "network_propagation": "High - rotation disrupted, multiple downstream flights affected, significant rebooking required"
        },
        "safety_score": 100,
        "cost_score": 20,
        "passenger_score": 15,
        "network_score": 25,
        "composite_score": 52,
        "pros": [
          "Maximum safety margin",
          "No operational pressure on crew or maintenance",
          "Comprehensive aircraft inspection possible",
          "No risk of further delays or complications"
        ],
        "cons": [
          "Severe passenger impact (286 passengers affected)",
          "Very high financial cost ($258K)",
          "Major network disruption",
          "Rotation schedule disrupted",
          "Reputational damage",
          "High rebooking complexity"
        ],
        "risks": [
          "Insufficient rebooking capacity on alternative flights",
          "Passenger complaints and social media backlash",
          "Regulatory scrutiny for cancellation",
          "Long-term customer loyalty impact",
          "Crew scheduling complications for downstream flights"
        ],
        "confidence": 0.65,
        "estimated_duration": "12-24 hours",
        "recovery_plan": {
          "solution_id": 3,
          "total_steps": 9,
          "estimated_total_duration": "24 hours",
          "steps": [
            {
              "step_number": 1,
              "step_name": "Declare Flight Cancellation",
              "description": "Officially cancel EY283 and initiate cancellation protocols",
              "responsible_agent": "network",
              "dependencies": [],
              "estimated_duration": "15 minutes",
              "automation_possible": true,
              "action_type": "notify",
              "parameters": { "flight": "EY283" },
              "success_criteria": "Cancellation declared in all systems",
              "rollback_procedure": null
            }
          ],
          "critical_path": [1, 2, 3, 4, 5],
          "contingency_plans": [
            {
              "trigger": "Insufficient rebooking capacity",
              "action": "Charter additional aircraft or partner with other airlines",
              "responsible_agent": "network"
            }
          ]
        }
      }
    ],
    "recommended_solution_id": 1,
    "recommendation_evolution": {
      "phases_available": ["phase1", "phase2"],
      "agents_changed": 4,
      "agents_unchanged": 3,
      "convergence_detected": true,
      "divergence_detected": false,
      "evolution_details": [
        {
          "agent_name": "cargo",
          "phase1_recommendation": "No recommendation provided",
          "phase2_recommendation": "No recommendation provided",
          "phase1_confidence": 0,
          "phase2_confidence": 0,
          "change_type": "unchanged",
          "binding_constraints_added": [],
          "binding_constraints_removed": [],
          "change_summary": "cargo maintained recommendation (high confidence signal)"
        },
        {
          "agent_name": "crew_compliance",
          "phase1_recommendation": "## **CREW COMPLIANCE ANALYSIS - FLIGHT EY283 (2026-02-05)**\n\n### **Current Situation:**\n- **Flight:** EY283 BKK→AUH (B787-9)\n- **Scheduled Departure:** 2026-02-05 01:00 UTC\n- **Event:** Mechanical issue (delay expected)\n- **Crew:** 14 members (2 Captains, 2 First Officers, 2 Pursers, 8 Flight Attendants)\n\n### **FDP ANALYSIS:**\n\n**Current FDP (without delay):** 9.75 hours\n\n**Crew FDP Status:**\n- **Pilots (4-pilot crew):** Max FDP = 14h, Current = 9.75h, **Remaining = 4.25h**\n- **Cabin Crew:** Max FDP = 13h, Current = 9.75h, **Remaining = 3.25h**\n\n**Critical Assessment:**\n- **Pilots can tolerate up to 4.25h delay**\n- **Cabin crew can tolerate up to 3.25h delay**\n- **Binding constraint:** Cabin crew FDP limit of 13 hours\n\n### **RECOMMENDATION:**\n\n**rec:** APPROVED with conditions: Mechanical delay must not exceed 3h; departure by 04:00 UTC required\n\n**conf:** 0.78\n\n**constraints:** Max 3h delay permitted; Cabin crew 13h FDP limit; Min 10h rest post-duty required",
          "phase2_recommendation": "## CREW COMPLIANCE REVISION ANALYSIS\n\n**Revision Status: CONFIRM with enhanced analysis**\n\n### Current Crew Status Analysis:\n\n**FDP Analysis:**\n- **Pilots (4 crew):** Max FDP = 14h, Current = 9.75h, **Remaining = 4.25h** - Risk level: **70%** (LOW)\n- **Cabin Crew (10 crew):** Max FDP = 13h, Current = 9.75h, **Remaining = 3.25h** - Risk level: **75%** (MODERATE)\n\n**Critical Constraint:**\nCaptain's remarks note: \"FDP OK if departs by 04:30Z\" - this is **3.5 hours past scheduled departure**.\n\n### RECOMMENDATION:\n\n**rec:** APPROVED if delay ≤3h; CREW_CHANGE MANDATORY if delay >3.5h\n\n**conf:** 0.85\n\n**constraints:** Max 3.5h delay before FDP breach; B787 type rating required; Min 10h rest post-duty\n\n**revision_status:** CONFIRM - Initial assessment stands with enhanced detail.",
          "phase1_confidence": 0.85,
          "phase2_confidence": 0.85,
          "change_type": "converged",
          "binding_constraints_added": [],
          "binding_constraints_removed": [],
          "change_summary": "crew_compliance revised recommendation after seeing other agents"
        },
        {
          "agent_name": "maintenance",
          "phase1_recommendation": "## Initial Analysis - Flight EY283 (2026-02-05)\n\n**rec:** RESTRICTED: Mechanical issue reported; unable to verify MEL status - manual inspection required before dispatch\n\n**conf:** 0.45\n\n**constraints:** Ground inspection mandatory; MEL compliance verification required; Airworthiness certificate validation needed\n\n**reasoning:**\n* Flight EY283 (A6-BNC, B787-9) BKK-AUH scheduled departure 2026-02-05 01:00 UTC\n* HIGH network priority - feeds EY17 rotation with 51 connecting passengers\n* 286 passengers + VIP onboard - safety assessment mandatory before dispatch decision",
          "phase2_recommendation": "## REVISION ANALYSIS\n\n**Decision: STRENGTHEN**\n\n### Maintenance Assessment:\n\n**Flight Details Confirmed:**\n- **Aircraft**: A6-BNC (B787-9)\n- **Route**: BKK→AUH\n- **PAX Load**: 286/299 (96% load factor)\n- **Network Impact**: HIGH priority, feeds rotation\n\n### Maintenance Recommendation:\n\n**rec**: RESTRICTED: Mechanical issue unspecified; requires immediate diagnosis at BKK before dispatch determination\n\n**conf**: 0.65\n\n**constraints**: No dispatch until fault diagnosed; MEL compliance verification required\n\n**reasoning**: \n* Mechanical issue nature unknown - cannot assess MEL eligibility\n* BKK station has maintenance capability but night timing limits repair window\n* Must diagnose fault first: if Cat A/B → AOG; if Cat C/D → potential dispatch with restrictions\n\n**revision_status**: STRENGTHENED - Added specific diagnostic requirements",
          "phase1_confidence": 0.8,
          "phase2_confidence": 0.8,
          "change_type": "converged",
          "binding_constraints_added": [],
          "binding_constraints_removed": [],
          "change_summary": "maintenance revised recommendation after seeing other agents"
        },
        {
          "agent_name": "network",
          "phase1_recommendation": "## INITIAL ANALYSIS: EY283 Mechanical Disruption\n\n**Flight Details:**\n- **Flight:** EY283 (BKK→AUH) | Aircraft: A6-BNC (B787-9)\n- **Scheduled:** 2026-02-05 01:00 UTC departure\n- **Passengers:** 286 total | 51 connecting to downstream flights\n- **Status:** SCHEDULED | Network Priority: HIGH\n\n### **PROPAGATION IMPACT ASSESSMENT**\n\n**Aircraft Rotation Chain (A6-BNC):**\n\n| Sequence | Flight | Route | Priority | Status |\n|----------|--------|-------|----------|--------|\n| 1 | **EY283** | BKK→AUH | HIGH | **DISRUPTED** |\n| 2 | **EY17** | AUH→LHR | **CRITICAL** | AT RISK |\n| 3 | **EY18** | LHR→AUH | HIGH | AT RISK |\n\n**Downstream Flights Affected:** 2 flights\n**Total Passengers at Risk:** 465 pax\n\n### **RECOVERY SCENARIOS**\n\n**RS-002: Aircraft Swap (RECOMMENDED)**\n- Feasibility: MEDIUM (requires available B787-9 at BKK)\n- Cost: MEDIUM\n- Impact: Restores EY17 to slot compliance\n\n**CONFIDENCE:** 0.85",
          "phase2_recommendation": "## **NETWORK IMPACT ASSESSMENT - EY283 MECHANICAL DISRUPTION**\n\n**REVISION STATUS: CONFIRM WITH STRENGTHENED CONSTRAINTS**\n\n### **CRITICAL FINDINGS:**\n\n**DOWNSTREAM CASCADE - CRITICAL RISK:**\n\n| Flight | Route | Pax | Priority | Risk Level |\n|--------|-------|-----|----------|-----------|\n| **EY17** | AUH→LHR | 285 | **CRITICAL** | SLOT-CRITICAL |\n| **EY18** | LHR→AUH | 275 | HIGH | Dependent on EY17 |\n\n### **RECOVERY SCENARIOS (Ranked):**\n\n**RS-002: Aircraft Swap (RECOMMENDED)**\n- **Action:** Swap A6-BNC with available B787-9\n- **Impact:** Preserves EY17 LHR slot\n- **Confidence:** 0.82\n\n**RS-001: Delay Only (NOT RECOMMENDED)**\n- **Risk:** EY283 delay >3h → EY17 misses LHR slot\n- **Confidence:** 0.45",
          "phase1_confidence": 0.8,
          "phase2_confidence": 0.8,
          "change_type": "converged",
          "binding_constraints_added": [],
          "binding_constraints_removed": [],
          "change_summary": "network revised recommendation after seeing other agents"
        },
        {
          "agent_name": "regulatory",
          "phase1_recommendation": "## REGULATORY COMPLIANCE ANALYSIS - EY283\n\n**Flight:** EY283 BKK→AUH\n**Status:** COMPLIANT (with conditions)\n\n### Key Findings:\n- No curfew restrictions at BKK or AUH\n- Slot allocation confirmed for departure window\n- GCAA regulations satisfied for current crew configuration\n\n**rec:** COMPLIANT: No regulatory blockers identified; standard operations permitted\n\n**conf:** 0.80\n\n**constraints:** Maintain slot window compliance; GCAA crew duty requirements apply",
          "phase2_recommendation": "## REGULATORY REVISION ANALYSIS\n\n**Revision Status: CONFIRM**\n\n### Regulatory Assessment:\n\n- **Curfew Status:** No restrictions at BKK or AUH airports\n- **Slot Compliance:** Departure slot secured for 01:00 UTC window\n- **GCAA Requirements:** Crew configuration meets regulatory minimums\n\n**rec:** COMPLIANT: No regulatory blockers; aircraft swap or controlled delay both permissible\n\n**conf:** 0.85\n\n**constraints:** Maintain slot compliance; GCAA FDP regulations binding\n\n**revision_status:** CONFIRM - No changes to regulatory assessment",
          "phase1_confidence": 0.8,
          "phase2_confidence": 0.85,
          "change_type": "converged",
          "binding_constraints_added": [],
          "binding_constraints_removed": [],
          "change_summary": "regulatory revised recommendation after seeing other agents"
        }
      ]
    }
  },
  "audit_trail": {
    "phase1_initial": {
      "phase": "initial",
      "duration_seconds": 25.5,
      "timestamp": "2026-02-03T21:08:30.000000+00:00",
      "responses": {
        "crew_compliance": {
          "agent_name": "crew_compliance",
          "recommendation": "## **CREW COMPLIANCE ANALYSIS - FLIGHT EY283 (2026-02-05)**\n\n### **Current Situation:**\n- **Flight:** EY283 BKK→AUH (B787-9)\n- **Scheduled Departure:** 2026-02-05 01:00 UTC\n- **Event:** Mechanical issue (delay expected)\n- **Crew:** 14 members (2 Captains, 2 First Officers, 2 Pursers, 8 Flight Attendants)\n- **Current Duty:** Started 2026-02-04 23:30 UTC, scheduled end 2026-02-05 09:15 UTC\n\n### **FDP ANALYSIS:**\n\n**Current FDP (without delay):** 9.75 hours (23:30 UTC to 09:15 UTC)\n\n**Crew FDP Status:**\n- **Pilots (4-pilot crew):** Max FDP = 14h, Current = 9.75h, **Remaining = 4.25h**\n- **Cabin Crew:** Max FDP = 13h, Current = 9.75h, **Remaining = 3.25h**\n\n**Critical Assessment:**\nThe mechanical issue creates a time-critical situation:\n- **Pilots can tolerate up to 4.25h delay** (reaching 14h max FDP)\n- **Cabin crew can tolerate up to 3.25h delay** (reaching 13h max FDP)\n- **Binding constraint:** Cabin crew FDP limit of 13 hours\n\n### **RECOMMENDATION:**\n\n**rec:** APPROVED with conditions: Mechanical delay must not exceed 3h; departure by 04:00 UTC required; monitor crew FDP continuously\n\n**conf:** 0.78\n\n**constraints:** Max 3h delay permitted; Cabin crew 13h FDP limit; Min 10h rest post-duty required\n\n**reasoning:** \n* Current FDP 9.75h leaves 3.25h buffer for cabin crew (binding constraint)\n* 4-pilot configuration provides 14h FDP for flight deck (adequate)\n* All crew have B787 qualification and valid medical certificates per roster",
          "reasoning": "Current FDP 9.75h leaves 3.25h buffer for cabin crew (binding constraint). 4-pilot configuration provides 14h FDP for flight deck (adequate). All crew have B787 qualification.",
          "data_sources": ["CrewRoster", "CrewMembers", "Flights"],
          "status": "success",
          "confidence": 0.85,
          "duration_seconds": 8.2,
          "timestamp": "2026-02-03T21:08:38.200000+00:00"
        },
        "maintenance": {
          "agent_name": "maintenance",
          "recommendation": "## Initial Analysis - Flight EY283 (2026-02-05)\n\n**rec:** RESTRICTED: Mechanical issue reported; unable to verify MEL status due to system unavailability - manual inspection required before dispatch\n\n**conf:** 0.45\n\n**constraints:** Ground inspection mandatory; MEL compliance verification required; Airworthiness certificate validation needed\n\n**reasoning:**\n* Flight EY283 (A6-BNC, B787-9) BKK-AUH scheduled departure 2026-02-05 01:00 UTC\n* HIGH network priority - feeds EY17 rotation with 51 connecting passengers\n* Mechanical issue reported but maintenance systems unavailable\n* 286 passengers + VIP onboard - safety assessment mandatory before dispatch decision\n\n**Critical Actions Required:**\n1. **Immediate:** Maintenance engineer inspection at BKK to identify mechanical issue\n2. **Verify:** Current MEL status and any active deferrals on A6-BNC\n3. **Assess:** Whether issue is MEL-deferrable or requires immediate rectification\n4. **Evaluate:** Aircraft swap options if AOG",
          "reasoning": "Mechanical issue reported but maintenance systems unavailable - cannot verify MEL status. Manual inspection required at BKK station.",
          "data_sources": ["Aircraft", "MaintenanceConstraints", "Flights"],
          "status": "success",
          "confidence": 0.80,
          "duration_seconds": 7.8,
          "timestamp": "2026-02-03T21:08:37.800000+00:00"
        },
        "regulatory": {
          "agent_name": "regulatory",
          "recommendation": "## REGULATORY COMPLIANCE ANALYSIS - EY283\n\n**Flight:** EY283 BKK→AUH\n**Status:** COMPLIANT (with conditions)\n\n### Key Findings:\n- No curfew restrictions at BKK or AUH airports\n- Slot allocation confirmed for departure window\n- GCAA regulations satisfied for current crew configuration\n\n**rec:** COMPLIANT: No regulatory blockers identified; standard operations permitted\n\n**conf:** 0.80\n\n**constraints:** Maintain slot window compliance; GCAA crew duty requirements apply\n\n**reasoning:**\n* BKK (Suvarnabhumi) operates 24 hours - no night curfew\n* AUH (Abu Dhabi) operates 24 hours - no restrictions\n* Departure slot allocated for 01:00 UTC +/- 15 minutes\n* GCAA CAR-OPS 1.1095 crew duty requirements satisfied",
          "reasoning": "No curfew restrictions at BKK or AUH. Slot allocation confirmed. GCAA regulations satisfied for current crew configuration.",
          "data_sources": ["Regulations", "AirportConstraints", "Flights"],
          "status": "success",
          "confidence": 0.80,
          "duration_seconds": 6.5,
          "timestamp": "2026-02-03T21:08:36.500000+00:00"
        },
        "network": {
          "agent_name": "network",
          "recommendation": "## INITIAL ANALYSIS: EY283 Mechanical Disruption\n\n**Flight Details:**\n- **Flight:** EY283 (BKK→AUH) | Aircraft: A6-BNC (B787-9)\n- **Scheduled:** 2026-02-05 01:00 UTC departure | 04:45 UTC arrival\n- **Passengers:** 286 total | 51 connecting to downstream flights\n- **Status:** SCHEDULED | Network Priority: HIGH\n\n---\n\n### **PROPAGATION IMPACT ASSESSMENT**\n\n**Aircraft Rotation Chain (A6-BNC):**\n\n| Sequence | Flight | Route | Departure | Arrival | Pax | Priority | Status |\n|----------|--------|-------|-----------|---------|-----|----------|--------|\n| 1 | **EY283** | BKK→AUH | 01:00Z | 04:45Z | 286 | HIGH | **DISRUPTED** |\n| 2 | **EY17** | AUH→LHR | 07:25Z | 11:55Z | 285 | **CRITICAL** | AT RISK |\n| 3 | **EY18** | LHR→AUH | 14:30Z | 23:45Z | 275 | HIGH | AT RISK |\n\n**Downstream Flights Affected:** 2 flights  \n**Total Passengers at Risk:** 465 pax (180 connecting on EY17 + 95 on EY18)\n\n---\n\n### **RECOVERY SCENARIOS**\n\n**RS-002: Aircraft Swap (RECOMMENDED)**\n- Feasibility: MEDIUM (requires available B787-9 at BKK)\n- Cost: MEDIUM (positioning + crew swap)\n- Recommendation: **PREFERRED** if aircraft available\n- Impact: Restores EY17 to slot compliance\n\n**CONFIDENCE:** 0.85",
          "reasoning": "HIGH network priority flight feeding critical EY17 rotation. 51 connecting passengers at risk. Aircraft swap recommended to preserve network integrity.",
          "data_sources": ["Flights", "Connections", "Aircraft"],
          "status": "success",
          "confidence": 0.80,
          "duration_seconds": 9.1,
          "timestamp": "2026-02-03T21:08:39.100000+00:00"
        },
        "guest_experience": {
          "agent_name": "guest_experience",
          "recommendation": "## PASSENGER IMPACT ANALYSIS - EY283\n\n**Flight Profile:**\n- **Total Passengers:** 286\n- **Connecting Passengers:** 51 (17.8%)\n- **VIP Passengers:** 4 (First Class/Platinum)\n- **Special Assistance:** 8 passengers\n\n### Impact Assessment:\n\n**Scenario: Aircraft Swap (No Delay)**\n- Passenger notification: Aircraft change only\n- Compensation: None required\n- Rebooking: None required\n- Customer satisfaction impact: MINIMAL\n\n**Scenario: 3-Hour Delay**\n- EU261 compensation: €600 x 180 eligible = €108,000\n- Meal vouchers: €15 x 286 = €4,290\n- 51 missed connections requiring rebooking\n\n**rec:** Support aircraft swap to minimize passenger impact; notify all 286 pax of equipment change\n\n**conf:** 0.82\n\n**reasoning:** Aircraft swap preserves all connections, avoids compensation liability, maintains customer satisfaction",
          "reasoning": "Aircraft swap minimizes passenger impact. No delays means no compensation liability and all connections preserved.",
          "data_sources": ["PassengerManifest", "Connections", "Flights"],
          "status": "success",
          "confidence": 0.82,
          "duration_seconds": 7.3,
          "timestamp": "2026-02-03T21:08:37.300000+00:00"
        },
        "cargo": {
          "agent_name": "cargo",
          "recommendation": "## CARGO ANALYSIS - EY283\n\n**Cargo Manifest:**\n- **Total Weight:** 12.4 tonnes\n- **Perishables:** 2.1 tonnes (temperature-controlled)\n- **Live Animals:** None\n- **Dangerous Goods:** 0.3 tonnes (Class 9)\n- **Time-Critical:** 1.8 tonnes (pharmaceuticals)\n\n### Impact Assessment:\n\n**Aircraft Swap Scenario:**\n- All cargo transferable to replacement B787-9\n- No offload required\n- Perishables remain within cold chain limits\n\n**rec:** Aircraft swap supported; all cargo transferable; no operational constraints from cargo perspective\n\n**conf:** 0.78\n\n**reasoning:** Cargo manifest compatible with aircraft swap. No time-critical constraints that would prevent recovery.",
          "reasoning": "Cargo manifest compatible with aircraft swap. No time-critical constraints identified.",
          "data_sources": ["CargoManifest", "Aircraft"],
          "status": "success",
          "confidence": 0.78,
          "duration_seconds": 5.9,
          "timestamp": "2026-02-03T21:08:35.900000+00:00"
        },
        "finance": {
          "agent_name": "finance",
          "recommendation": "## FINANCIAL ANALYSIS - EY283 DISRUPTION\n\n### Cost Comparison:\n\n| Scenario | Direct Costs | Compensation | Total |\n|----------|-------------|--------------|-------|\n| **Aircraft Swap** | $15,000 | $0 | **$15,000** |\n| **3-Hour Delay** | $5,000 | $55,000 | **$60,000** |\n| **Cancellation** | $8,000 | $250,000 | **$258,000** |\n\n### Recommendation:\n\n**rec:** Aircraft swap is financially optimal at $15,000 total cost vs $60,000+ for delay scenarios\n\n**conf:** 0.85\n\n**reasoning:**\n* Aircraft swap: Positioning cost + ground handling = $15,000\n* Avoids EU261 compensation liability ($108,000 potential)\n* Protects revenue from 51 connecting passengers\n* Preserves network integrity and downstream revenue",
          "reasoning": "Aircraft swap is financially optimal at $15,000 total cost. Avoids EU261 compensation liability of $108,000+.",
          "data_sources": ["CostCenters", "Flights", "PassengerManifest"],
          "status": "success",
          "confidence": 0.85,
          "duration_seconds": 6.8,
          "timestamp": "2026-02-03T21:08:36.800000+00:00"
        }
      }
    },
    "phase2_revision": {
      "phase": "revision",
      "duration_seconds": 28.3,
      "timestamp": "2026-02-03T21:09:00.000000+00:00",
      "responses": {
        "crew_compliance": {
          "agent_name": "crew_compliance",
          "recommendation": "## CREW COMPLIANCE REVISION ANALYSIS\n\n**Revision Status: CONFIRM with enhanced analysis**\n\nBased on the crew roster data retrieved and review of other agents' recommendations:\n\n### Current Crew Status Analysis:\n\n**Flight Details:**\n- Flight: EY283 (BKK→AUH) on 2026-02-05\n- Aircraft: B787-9 (A6-BNC)\n- Crew: 14 members (all BKK-based layover crew)\n\n**FDP Analysis:**\n- **Pilots (4 crew):** Risk level: **70%** (LOW)\n- **Cabin Crew (10 crew):** Risk level: **75%** (MODERATE)\n\n**Critical Constraint:**\nCaptain's remarks: \"FDP OK if departs by 04:30Z\" - **3.5 hours buffer**\n\n### Integration with Other Agents:\n\n- **Maintenance (0.80 conf):** Aircraft swap recommended\n- **Network (0.80 conf):** HIGH priority, feeds EY17 rotation\n- **Regulatory (0.80 conf):** No regulatory blockers\n\n---\n\n## RECOMMENDATION:\n\n**rec:** APPROVED if delay ≤3h; CREW_CHANGE MANDATORY if delay >3.5h\n\n**conf:** 0.85\n\n**constraints:** Max 3.5h delay before FDP breach; B787 type rating required; Min 10h rest post-duty\n\n**revision_status:** CONFIRM - Initial assessment stands with enhanced detail.",
          "reasoning": "Current FDP analysis confirmed. 3.5h buffer available before crew change required. Integration with other agents confirms aircraft swap as preferred solution.",
          "data_sources": ["CrewRoster", "CrewMembers", "Flights"],
          "status": "success",
          "confidence": 0.85,
          "duration_seconds": 9.1,
          "timestamp": "2026-02-03T21:09:09.100000+00:00"
        },
        "maintenance": {
          "agent_name": "maintenance",
          "recommendation": "## REVISION ANALYSIS\n\n**Decision: STRENGTHEN**\n\n### Review of Other Agents' Inputs:\n\n1. **Network Agent (conf: 0.80)**: HIGH network priority, 286 PAX, feeds EY17 rotation\n2. **Crew Compliance (conf: 0.85)**: 3.5h buffer available\n3. **Regulatory (conf: 0.80)**: No regulatory blockers\n4. **Finance (conf: 0.85)**: Aircraft swap financially optimal\n\n### Maintenance Assessment:\n\n**Flight Details Confirmed:**\n- **Aircraft**: A6-BNC (B787-9)\n- **Route**: BKK→AUH\n- **PAX Load**: 286/299 (96% load factor)\n- **Network Impact**: HIGH priority\n\n### Maintenance Recommendation:\n\n**rec**: RESTRICTED pending diagnosis; RECOMMEND aircraft swap to preserve schedule and network integrity\n\n**conf**: 0.80\n\n**constraints**: No dispatch of A6-BNC until fault diagnosed; Aircraft swap eliminates maintenance uncertainty\n\n**reasoning**: \n* Mechanical issue nature unknown but aircraft swap removes diagnostic uncertainty\n* BKK station can ground A6-BNC for comprehensive inspection\n* Replacement B787-9 avoids dispatch risk\n\n**revision_status**: STRENGTHENED - Explicit recommendation for aircraft swap based on cross-agent consensus",
          "reasoning": "Aircraft swap removes diagnostic uncertainty. Cross-agent consensus supports swap. A6-BNC can be grounded for inspection.",
          "data_sources": ["Aircraft", "MaintenanceConstraints", "Flights"],
          "status": "success",
          "confidence": 0.80,
          "duration_seconds": 8.7,
          "timestamp": "2026-02-03T21:09:08.700000+00:00"
        },
        "regulatory": {
          "agent_name": "regulatory",
          "recommendation": "## REGULATORY REVISION ANALYSIS\n\n**Revision Status: CONFIRM**\n\n### Regulatory Assessment (Cross-Validated):\n\n- **Curfew Status:** No restrictions at BKK or AUH airports\n- **Slot Compliance:** Departure slot secured for 01:00 UTC window\n- **GCAA Requirements:** Crew configuration meets regulatory minimums\n- **Aircraft Swap:** No regulatory impediments to equipment change\n\n### Integration with Other Agents:\n\n- Crew Compliance confirmed GCAA FDP requirements satisfied\n- Network confirmed slot criticality for downstream EY17\n- Maintenance recommends aircraft swap\n\n**rec:** COMPLIANT: No regulatory blockers for aircraft swap; recommend proceeding with equipment change\n\n**conf:** 0.85\n\n**constraints:** Maintain slot compliance; GCAA FDP regulations binding; Aircraft swap permissible\n\n**revision_status:** CONFIRM - No changes to regulatory assessment; aircraft swap supported",
          "reasoning": "No regulatory blockers identified. Aircraft swap permissible under all applicable regulations.",
          "data_sources": ["Regulations", "AirportConstraints", "Flights"],
          "status": "success",
          "confidence": 0.85,
          "duration_seconds": 7.2,
          "timestamp": "2026-02-03T21:09:07.200000+00:00"
        },
        "network": {
          "agent_name": "network",
          "recommendation": "## **NETWORK IMPACT ASSESSMENT - REVISION**\n\n**REVISION STATUS: CONFIRM WITH STRENGTHENED CONSTRAINTS**\n\n### **CRITICAL FINDINGS (Cross-Validated):**\n\n**Flight EY283:**\n- **Aircraft:** A6-BNC (B787-9)\n- **Passengers:** 286 total | **51 connecting** to EY17\n- **Network Priority:** HIGH\n\n**DOWNSTREAM CASCADE - CONFIRMED CRITICAL:**\n\n| Flight | Route | Pax | Priority | Risk Level |\n|--------|-------|-----|----------|-----------|\n| **EY17** | AUH→LHR | 285 | **CRITICAL** | SLOT-CRITICAL |\n| **EY18** | LHR→AUH | 275 | HIGH | Dependent |\n\n### **CROSS-AGENT INTEGRATION:**\n\n- **Crew Compliance (0.85):** 3.5h buffer - supports swap\n- **Maintenance (0.80):** Recommends swap to remove uncertainty\n- **Regulatory (0.85):** No blockers for swap\n- **Finance (0.85):** Swap is financially optimal\n\n### **RECOVERY SCENARIO (CONFIRMED):**\n\n**RS-002: Aircraft Swap (STRONGLY RECOMMENDED)**\n- All agents converge on aircraft swap solution\n- Preserves EY17 slot compliance\n- Minimizes network propagation\n- Confidence: 0.90\n\n**rec**: Aircraft swap STRONGLY RECOMMENDED; all agents converged; network integrity preserved\n\n**conf**: 0.90\n\n**revision_status**: CONFIRM - Strengthened based on cross-agent consensus",
          "reasoning": "All agents converge on aircraft swap. Network integrity preserved. EY17 slot protected.",
          "data_sources": ["Flights", "Connections", "Aircraft"],
          "status": "success",
          "confidence": 0.90,
          "duration_seconds": 9.8,
          "timestamp": "2026-02-03T21:09:09.800000+00:00"
        },
        "guest_experience": {
          "agent_name": "guest_experience",
          "recommendation": "## PASSENGER IMPACT REVISION\n\n**Revision Status: CONFIRM**\n\n### Cross-Agent Integration:\n\nAll agents converging on aircraft swap solution:\n- Crew Compliance: APPROVED\n- Maintenance: RECOMMENDS SWAP\n- Regulatory: COMPLIANT\n- Network: STRONGLY RECOMMENDED\n- Finance: OPTIMAL\n\n### Passenger Impact (Aircraft Swap Scenario):\n\n- **Notifications Required:** 286 passengers - aircraft change only\n- **Rebooking Required:** 0\n- **Compensation Required:** $0\n- **Connections Protected:** 51 (100%)\n- **Customer Satisfaction:** PRESERVED\n\n**rec:** Aircraft swap is optimal passenger outcome; notify all 286 pax of equipment change; no rebooking required\n\n**conf:** 0.88\n\n**revision_status:** CONFIRM - Aircraft swap provides best passenger outcome",
          "reasoning": "Aircraft swap provides optimal passenger outcome. All connections protected. No compensation required.",
          "data_sources": ["PassengerManifest", "Connections", "Flights"],
          "status": "success",
          "confidence": 0.88,
          "duration_seconds": 7.5,
          "timestamp": "2026-02-03T21:09:07.500000+00:00"
        },
        "cargo": {
          "agent_name": "cargo",
          "recommendation": "## CARGO REVISION ANALYSIS\n\n**Revision Status: CONFIRM**\n\n### Cargo Assessment (Aircraft Swap Scenario):\n\n- All 12.4 tonnes transferable to replacement B787-9\n- Perishables (2.1 tonnes) within cold chain limits\n- No offload required\n- No cargo constraints on aircraft swap\n\n**rec:** Aircraft swap supported from cargo perspective; no operational constraints\n\n**conf:** 0.80\n\n**revision_status:** CONFIRM - No changes to cargo assessment",
          "reasoning": "Cargo fully compatible with aircraft swap. No constraints identified.",
          "data_sources": ["CargoManifest", "Aircraft"],
          "status": "success",
          "confidence": 0.80,
          "duration_seconds": 5.4,
          "timestamp": "2026-02-03T21:09:05.400000+00:00"
        },
        "finance": {
          "agent_name": "finance",
          "recommendation": "## FINANCIAL REVISION ANALYSIS\n\n**Revision Status: CONFIRM**\n\n### Cross-Agent Cost Validation:\n\n| Scenario | Direct Costs | Compensation | Network Value | Total Impact |\n|----------|-------------|--------------|---------------|-------------|\n| **Aircraft Swap** | $15,000 | $0 | Preserved | **$15,000** |\n| **3-Hour Delay** | $5,000 | $55,000 | At Risk | **$60,000+** |\n| **Cancellation** | $8,000 | $250,000 | Lost | **$258,000** |\n\n### Financial Recommendation:\n\n**rec:** Aircraft swap remains financially optimal; $15,000 cost vs $60,000+ alternatives\n\n**conf:** 0.88\n\n**reasoning:**\n* All agents converging on aircraft swap\n* $15,000 positioning cost is justified by:\n  - $0 compensation liability\n  - Protected revenue from 51 connections ($125,000+)\n  - Preserved network value (EY17 critical rotation)\n\n**revision_status:** CONFIRM - Aircraft swap is clear financial winner",
          "reasoning": "Aircraft swap is clear financial winner at $15,000 vs $60,000+ alternatives. All agents converging.",
          "data_sources": ["CostCenters", "Flights", "PassengerManifest"],
          "status": "success",
          "confidence": 0.88,
          "duration_seconds": 7.1,
          "timestamp": "2026-02-03T21:09:07.100000+00:00"
        }
      }
    },
    "phase3_arbitration": {
      "phase": "arbitration",
      "duration_seconds": 27.8,
      "timestamp": "2026-02-03T21:10:32.140768+00:00",
      "solution_options": [
        {
          "solution_id": 1,
          "title": "Aircraft Swap - Maintain Schedule",
          "description": "Execute immediate aircraft swap from A6-BNC to serviceable B787-9 from available fleet. Maintain scheduled departure time 01:00 UTC. Assign qualified crew, notify passengers, prioritize connections.",
          "recommendations": [
            "Swap to serviceable B787-9 aircraft",
            "Maintain 01:00 UTC departure time",
            "Assign qualified crew from roster",
            "Notify all 286 passengers of aircraft change",
            "Prioritize 51 connecting passengers for boarding",
            "Ground A6-BNC for maintenance"
          ],
          "safety_compliance": "All safety constraints satisfied: crew duty limits compliant, replacement aircraft airworthy, regulatory requirements met",
          "passenger_impact": {
            "total_passengers": 286,
            "connecting_passengers": 51,
            "delay_minutes": 0,
            "missed_connections": 0,
            "compensation_required": false,
            "passenger_notifications": "Aircraft change notification only"
          },
          "financial_impact": {
            "aircraft_swap_cost": 15000,
            "crew_costs": 0,
            "passenger_compensation": 0,
            "total_estimated_cost": 15000,
            "currency": "USD"
          },
          "network_impact": {
            "downstream_flights_affected": 0,
            "rotation_preserved": true,
            "EY17_connection_protected": true,
            "network_propagation": "None - schedule maintained"
          },
          "safety_score": 95,
          "cost_score": 85,
          "passenger_score": 95,
          "network_score": 95,
          "composite_score": 93,
          "justification": "All safety and business agents converged on aircraft swap solution with no binding constraints identified.",
          "pros": [
            "Zero passenger delay or missed connections",
            "Preserves critical EY17 rotation",
            "No network propagation",
            "All safety requirements satisfied",
            "Minimal financial impact"
          ],
          "cons": [
            "Requires available serviceable B787-9 in fleet",
            "Aircraft swap coordination complexity",
            "Removes one aircraft from spare pool"
          ],
          "risks": [
            "Replacement aircraft may not be immediately available",
            "Crew assignment delays could impact departure",
            "Ground operations coordination challenges at BKK"
          ],
          "confidence": 0.92,
          "estimated_duration": "2 hours"
        },
        {
          "solution_id": 2,
          "title": "Aircraft Swap with Controlled Delay",
          "description": "Execute aircraft swap with 2-4 hour delay to allow additional time for positioning and crew coordination. Protect critical connections through rebooking.",
          "recommendations": [
            "Swap to serviceable B787-9 aircraft",
            "Delay departure by 2-4 hours",
            "Rebook 51 connecting passengers on alternative flights",
            "Provide meal vouchers and compensation",
            "Assign qualified crew with extended duty time buffer",
            "Ground A6-BNC for maintenance"
          ],
          "safety_compliance": "All safety constraints satisfied with additional buffer time for crew rest and aircraft preparation",
          "passenger_impact": {
            "total_passengers": 286,
            "connecting_passengers": 51,
            "delay_minutes": 180,
            "missed_connections": 51,
            "compensation_required": true,
            "passenger_notifications": "Delay notification, rebooking confirmations, compensation details"
          },
          "financial_impact": {
            "aircraft_swap_cost": 15000,
            "crew_costs": 5000,
            "passenger_compensation": 25000,
            "rebooking_costs": 15000,
            "total_estimated_cost": 60000,
            "currency": "USD"
          },
          "network_impact": {
            "downstream_flights_affected": 1,
            "rotation_preserved": true,
            "EY17_connection_protected": false,
            "network_propagation": "Moderate - 51 passengers rebooked, EY17 may operate with reduced load"
          },
          "safety_score": 98,
          "cost_score": 60,
          "passenger_score": 55,
          "network_score": 65,
          "composite_score": 75,
          "justification": "Higher safety margin with extended preparation time but significant passenger impact.",
          "pros": [
            "Higher safety margin with extended preparation time",
            "Reduced operational pressure on crew and ground staff",
            "More flexibility for aircraft positioning",
            "Preserves aircraft rotation"
          ],
          "cons": [
            "Significant passenger delay (3 hours)",
            "51 missed connections requiring rebooking",
            "Higher compensation costs",
            "Moderate network propagation"
          ],
          "risks": [
            "Passenger dissatisfaction and complaints",
            "Rebooking challenges for connecting passengers",
            "Potential crew duty time issues if delay extends",
            "Downstream flight load factor impacts"
          ],
          "confidence": 0.78,
          "estimated_duration": "4 hours"
        },
        {
          "solution_id": 3,
          "title": "Flight Cancellation with Full Reprotection",
          "description": "Cancel EY283 and rebook all 286 passengers on alternative flights. Ground A6-BNC for comprehensive maintenance. Highest safety margin but significant passenger and network impact.",
          "recommendations": [
            "Cancel EY283 flight",
            "Rebook all 286 passengers on alternative flights",
            "Provide full compensation and hotel accommodation",
            "Ground A6-BNC for comprehensive maintenance inspection",
            "Adjust downstream rotation schedule",
            "Issue public communication about cancellation"
          ],
          "safety_compliance": "Maximum safety margin - no operational pressure, comprehensive maintenance inspection",
          "passenger_impact": {
            "total_passengers": 286,
            "connecting_passengers": 51,
            "delay_minutes": 720,
            "missed_connections": 286,
            "compensation_required": true,
            "passenger_notifications": "Cancellation notification, rebooking confirmations, hotel vouchers, full compensation"
          },
          "financial_impact": {
            "aircraft_swap_cost": 0,
            "crew_costs": 8000,
            "passenger_compensation": 120000,
            "rebooking_costs": 85000,
            "hotel_accommodation": 45000,
            "total_estimated_cost": 258000,
            "currency": "USD"
          },
          "network_impact": {
            "downstream_flights_affected": 3,
            "rotation_preserved": false,
            "EY17_connection_protected": false,
            "network_propagation": "High - rotation disrupted, multiple downstream flights affected"
          },
          "safety_score": 100,
          "cost_score": 20,
          "passenger_score": 15,
          "network_score": 25,
          "composite_score": 52,
          "justification": "Maximum safety margin but severe impact on passengers and network operations.",
          "pros": [
            "Maximum safety margin",
            "No operational pressure on crew or maintenance",
            "Comprehensive aircraft inspection possible",
            "No risk of further delays or complications"
          ],
          "cons": [
            "Severe passenger impact (286 passengers affected)",
            "Very high financial cost ($258K)",
            "Major network disruption",
            "Rotation schedule disrupted",
            "Reputational damage"
          ],
          "risks": [
            "Insufficient rebooking capacity on alternative flights",
            "Passenger complaints and social media backlash",
            "Regulatory scrutiny for cancellation",
            "Long-term customer loyalty impact"
          ],
          "confidence": 0.65,
          "estimated_duration": "12-24 hours"
        }
      ],
      "recommended_solution_id": 1,
      "reasoning": "All agents converged on aircraft swap solution. No conflicts identified. Safety constraints satisfied. Network integrity preserved.",
      "confidence": 0.92
    }
  }
};

/**
 * Generate a mock StatusResponse that wraps the mock data
 */
export function getMockStatusResponse(): any {
  return {
    request_id: 'mock-request-' + Date.now(),
    status: 'complete' as const,
    created_at: Date.now() - 60000,
    updated_at: Date.now(),
    execution_time_ms: 45000,
    session_id: 'mock-session-' + Date.now(),
    assessment: MOCK_RESPONSE
  };
}
