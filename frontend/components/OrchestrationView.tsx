import React, { useState, useEffect, useRef } from "react";
import { AgentAvatar, AgentType } from "./AgentAvatar";
import { AgentMessage, MessageData } from "./AgentMessage";
import { BrainCircuit, ChevronRight } from "lucide-react";
import { ArbitratorPanel, Solution } from "./ArbitratorPanel";
import { InvokeResponse } from "../services/api";
import { ResponseMapper } from "../services/responseMapper";

interface OrchestrationViewProps {
  prompt: string;
  apiResponse: InvokeResponse;
  loading?: boolean;
  progress?: string;
}

const AGENT_ROSTER: Exclude<AgentType, "Arbitrator">[] = [
  "Maintenance",
  "Regulatory",
  "Crew_Compliance",
  "Network",
  "Guest_Experience",
  "Cargo",
  "Finance",
];

/* ============================================================================
 * MOCK DATA - COMMENTED OUT FOR API INTEGRATION
 * 
 * To re-enable mock mode for testing:
 * 1. Uncomment the mock data below
 * 2. Uncomment the mock orchestration sequence in useEffect
 * 3. Comment out the API response parsing logic
 * ============================================================================

// Data-Rich Mock Responses
const MOCK_INITIAL_RESPONSES: Record<Exclude<AgentType, 'Arbitrator'>, { safety: string, business: string }> = {
  Maintenance: {
    safety: "AOG Confirmed: Hydraulic System Yellow Pump failure (ATA 29-11-02). MEL Category A - No dispatch allowed. Part P/N 5822-11 available in LHR fast-track stores (BA Engineering). Replacement requires jack-up.",
    business: "Turnaround Estimate: 4h 15m (Install) + 45m (Leak Check). Total Ground Time ~5h. Vendor overtime approved. Hangar slot unavailable; work must proceed at Gate E4 (Weather protected)."
  },
  Regulatory: {
    safety: "UK/EU261 Applicability: Confirmed. Delay >3hrs triggers compensation. Passenger Duty of Care (Refreshments) active immediately. Tarmac delay rule approaching (2h mark).",
    business: "Exposure Analysis: 412 Pax eligible for €600 comp if arrival delay >4hrs. Total Regulatory Risk: ~€247,200 ($265k). Cancellation triggers refund + return flight, potentially doubling liability."
  },
  Crew_Compliance: {
    safety: "FDP (Flight Duty Period) Alert: Captain & FO extended duty ends at 14:30Z. With 5h delay, they expire mid-flight. Absolute limit reached. Fatigue Risk Management (FRMS) rejects extension.",
    business: "Resource recovery: Reserve crew available at LHR hotel (Insight Hotel). Callout time 90 mins. Cost: $4,500/crew member extra + hotel retention for expired crew. Mandatory 12h rest for current set."
  },
  Network: {
    safety: "Hub Wave Impact: Inbound delay misses 'Bank 2' departure wave at AUH. Gate occupancy conflict at AUH Terminal A.",
    business: "Connectivity Crisis: 68 pax connecting to SYD (EY454), 22 to MEL (EY460), 15 to MNL. SYD flight is curfew-constrained; cannot hold. Misconnection means 24h layover at hub (Hotel cost + visa issues for 12 nationalities)."
  },
  Guest_Experience: {
    safety: "Terminal Conditions: Gate E4 seating capacity exceeded. 2 Medical Assistance (WCHR) pax onboard. 3 Unaccompanied Minors (UMNR) require continuous supervision.",
    business: "High-Value Breakdown: 6 Guests in The Residence/First. 14 Platinum, 32 Gold. 2 VIPs (Diplomatic status) requiring discrete handling. Risk of severe NPS degradation. Lounge capacity at LHR is 95% full."
  },
  Cargo: {
    safety: "Special Load: 2x AVI (Live Animals - Racehorses) in hold 2. Temperature regulation critical (requires APU/Ground Air). 1000kg Radioactive Pharma (RRY) - Time sensitive.",
    business: "Contract Penalties: Pharma shipment value $2.4M; spoilage risk if delay >8h. Racehorses require vet inspection if delay >5h. Reroute via EK/QR not possible due to DG restrictions."
  },
  Finance: {
    safety: "Procurement: Emergency PO #9921 generated for Hydraulic Pump ($42k).",
    business: "Cost Ledger: Engineering ($42k) + EU261 ($265k) + Crew Hotels ($12k) + Pax Meals/Hotels ($65k) + Cargo Risk ($500k insurance deductible). Total Event Cost: ~$884k. Cancellation reduces Cargo risk but spikes Brand damage."
  }
};

const MOCK_CROSS_IMPACT_RESPONSES: Record<Exclude<AgentType, 'Arbitrator'>, string> = {
  Maintenance: "Re-evaluating based on Cargo: We can expedite leak check with dual-team dispatch to save 45 mins, but cannot compress 4h install. APU is functional for Cargo cooling.",
  Regulatory: "Conflict: If we expedite Maintenance to 4h, we arguably enter 'Extraordinary Circumstances' defense for EU261, potentially saving $265k, but only if the root cause is manufacturing defect (unlikely).",
  Crew_Compliance: "Hard Constraint: Even with 45m saving, original crew IS ILLEGAL. We MUST swap crew. Reserve crew callout initiated tentatively to parallel-track maintenance.",
  Network: "Strategy Shift: If we delay 5h, we lose SYD connection. Propose: Hold EY454 (SYD) by 45 mins (max allowed) and put tight-connection pax on 'Rapid Transfer' protocol at AUH.",
  Guest_Experience: "Intervention: VIPs and Residence guests must be moved to Partner Airlines (BA/QR) immediately to protect relationship. Auth code required for interline booking.",
  Cargo: "Acceptable Risk: 5h delay is within Pharma tolerance (8h limit). Horses are fine if APU runs. Priority: DO NOT OFFLOAD Cargo. Offloading takes 3h and kills the recovery.",
  Finance: "Verdict: 5h Delay strategy is cheaper ($884k) than Cancellation ($1.2M + Reputational). Authorizing Overtime for Maintenance and Interline for VIPs only."
};

const ARBITRATOR_SOLUTIONS: Solution[] = [
  {
    id: 'sol-1',
    title: 'Option A: Integrated Recovery Protocol',
    description: 'Execute Repair (4h). Callout Reserve Crew. Hold SYD flight 45m. Interline 6 VIPs to BA. Keep Cargo onboard.',
    impact: 'medium',
    cost: '$320k Direct + Risk',
    recommended: true
  },
  {
    id: 'sol-2',
    title: 'Option B: Commercial Cancellation',
    description: 'Cancel Flight. Rebook all pax (24h+ delay). Offload Cargo to trucking. Position aircraft empty (Ferry) post-repair.',
    impact: 'high',
    cost: '$1.4M Estimate',
    recommended: false
  },
  {
    id: 'sol-3',
    title: 'Option C: Equipment Swap (A350)',
    description: 'Swap with inbound A350. Downgrade capacity (-100 seats). Offload 100 econ pax + Cargo. Depart in 2h.',
    impact: 'medium',
    cost: '$450k + Cargo Claims',
    recommended: false
  }
];

============================================================================ */

type Stage =
  | "summoning"
  | "initial_round"
  | "waiting_for_user"
  | "cross_impact"
  | "decision_phase";

export default function OrchestrationView({
  prompt,
  apiResponse,
  loading = false,
  progress = "",
}: OrchestrationViewProps) {
  const [stage, setStage] = useState<Stage>("summoning");
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [solutions, setSolutions] = useState<Solution[]>([]);
  const [activeAgent, setActiveAgent] = useState<AgentType | null>(null);
  const [thinkingAgent, setThinkingAgent] = useState<AgentType | null>(null);
  const [arbitratorAnalysis, setArbitratorAnalysis] = useState<string>(
    "Parsing scenario parameters...",
  );
  const [selectedSolutionId, setSelectedSolutionId] = useState<string | null>(
    null,
  );
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, activeAgent, thinkingAgent]);

  // Display phase1 messages with sequential animation
  const displayPhase1Messages = async (messages: MessageData[]) => {
    for (const message of messages) {
      setThinkingAgent(message.agent);
      await new Promise((r) => setTimeout(r, 800)); // Thinking indicator for 800ms
      setThinkingAgent(null);
      setActiveAgent(message.agent);

      setMessages((prev) => [...prev, message]);

      await new Promise((r) => setTimeout(r, 1000)); // Speaking duration 1000ms
      setActiveAgent(null);
    }

    // Update arbitrator analysis after all phase1 messages
    setArbitratorAnalysis(
      "Initial impact assessment complete. Analysis ready for review.",
    );
    setStage("waiting_for_user");
  };

  // Display phase2 messages with sequential animation
  const displayPhase2Messages = async (messages: MessageData[]) => {
    for (const message of messages) {
      setThinkingAgent(message.agent);
      await new Promise((r) => setTimeout(r, 800)); // Thinking indicator for 800ms
      setThinkingAgent(null);
      setActiveAgent(message.agent);

      setMessages((prev) => [...prev, message]);

      await new Promise((r) => setTimeout(r, 1000)); // Speaking duration 1000ms
      setActiveAgent(null);
    }
  };

  // Parse API response and display agent messages
  useEffect(() => {
    const displayApiResponse = async () => {
      // Don't process if still loading or no assessment
      if (loading || !apiResponse.assessment) {
        return;
      }

      // 1. Summoning stage
      setArbitratorAnalysis("Initializing swarm intelligence...");
      await new Promise((r) => setTimeout(r, 2000));

      setArbitratorAnalysis(
        "Processing agent responses from AgentCore Runtime...",
      );
      setStage("initial_round");

      // 2. Check for API errors first
      if (apiResponse.assessment) {
        const assessment = apiResponse.assessment as any;

        // Handle nested assessment structure (assessment.assessment)
        const actualAssessment = assessment.assessment || assessment;

        // Check if the assessment contains an error
        if (actualAssessment.error || actualAssessment.error_message) {
          const errorMsg =
            actualAssessment.error_message ||
            actualAssessment.error ||
            "Unknown error occurred";
          const errorType = actualAssessment.error_type || "API Error";

          setArbitratorAnalysis(
            `⚠️ ${errorType}: ${errorMsg}. Please check the backend logs for details.`,
          );
          setStage("waiting_for_user");

          // Display error message in the chat
          setMessages([
            {
              id: `error-${Date.now()}`,
              agent: "Arbitrator",
              recommendation: "System Error",
              reasoning: errorMsg,
              status: "error",
            },
          ]);
          return;
        }

        // 3. Parse API response with audit_trail structure
        if (actualAssessment.audit_trail) {
          // NEW: Parse three-phase audit trail structure
          const parsed = ResponseMapper.parseAuditTrail(
            actualAssessment.audit_trail,
          );

          // Display phase1 messages using dedicated function
          await displayPhase1Messages(parsed.phase1Messages);

          // Set solutions from phase3
          setSolutions(parsed.solutions);
        } else {
          // Fallback to old structure for backward compatibility
          const parsed = ResponseMapper.parseResponse(apiResponse.assessment);

          // Display messages using phase1 function
          await displayPhase1Messages(parsed.messages);

          // Set solutions
          setSolutions(parsed.solutions);
        }
      } else {
        // Handle case where assessment is missing
        setArbitratorAnalysis("Warning: No assessment data received from API.");
        setStage("waiting_for_user");
      }
    };

    if (stage === "summoning") {
      displayApiResponse();
    }
  }, [stage, apiResponse, loading]);

  /* ============================================================================
   * MOCK ORCHESTRATION SEQUENCE - COMMENTED OUT FOR API INTEGRATION
   * 
   * To re-enable mock mode, uncomment this section and comment out the API
   * response parsing logic above.
   * ============================================================================

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;

    const runSequence = async () => {
      // 1. Summoning
      setArbitratorAnalysis("Initializing swarm intelligence...");
      await new Promise(r => setTimeout(r, 2000));
      
      setArbitratorAnalysis("Summoning domain experts for impact assessment...");
      setStage('initial_round');
      
      // 2. Initial Round
      for (const agent of AGENT_ROSTER) {
        setThinkingAgent(agent);
        await new Promise(r => setTimeout(r, 800)); // Thinking
        setThinkingAgent(null);
        setActiveAgent(agent);
        
        const response = MOCK_INITIAL_RESPONSES[agent];
        setMessages(prev => [...prev, {
          id: `msg-${Date.now()}`,
          agent: agent,
          safetyAnalysis: response.safety,
          businessImpact: response.business
        }]);
        
        await new Promise(r => setTimeout(r, 1000)); // Speaking duration
        setActiveAgent(null);
      }

      setArbitratorAnalysis("Initial impact assessment complete. Conflict detected: Crew Expiry vs Maintenance Time. Cross-impact analysis advised.");
      setStage('waiting_for_user');
    };

    if (stage === 'summoning') {
      runSequence();
    }

    return () => clearTimeout(timeoutId);
  }, [stage]);

  ============================================================================ */

  const handleCrossImpact = async () => {
    setStage("cross_impact");
    setArbitratorAnalysis("Analyzing cross-impact between agents...");

    // Use the phase2 data that's already in the apiResponse
    if (apiResponse.assessment) {
      const assessment = apiResponse.assessment as any;
      const actualAssessment = assessment.assessment || assessment;

      console.log("=== Cross Impact Analysis Debug ===");
      console.log("actualAssessment:", actualAssessment);
      console.log("audit_trail exists:", !!actualAssessment.audit_trail);

      if (actualAssessment.audit_trail) {
        // Parse phase2_revision from the existing audit trail
        const parsed = ResponseMapper.parseAuditTrail(
          actualAssessment.audit_trail,
        );

        console.log(
          "Parsed phase2Messages count:",
          parsed.phase2Messages.length,
        );
        console.log("Parsed solutions count:", parsed.solutions.length);
        console.log("Phase2 messages:", parsed.phase2Messages);

        // Display phase2 messages using dedicated function
        if (parsed.phase2Messages.length > 0) {
          await displayPhase2Messages(parsed.phase2Messages);
        } else {
          console.warn("No phase2 messages to display");
        }

        // Update solutions from phase3 (arbitration)
        if (parsed.solutions.length > 0) {
          setSolutions(parsed.solutions);
          setArbitratorAnalysis(
            "Cross-impact analysis complete. Review the recommended solutions below.",
          );
        } else {
          // Check if there's an arbitration error
          const phase3 = actualAssessment.audit_trail.phase3_arbitration;
          if (phase3 && phase3.error) {
            setArbitratorAnalysis(
              `⚠️ Arbitration Error: ${phase3.error}. ${phase3.final_decision || "Manual review required."}`,
            );
          } else {
            setArbitratorAnalysis(
              "Cross-impact analysis complete. No solution options available.",
            );
          }
        }

        setStage("decision_phase");
      } else {
        // Fallback if no audit_trail
        console.error("No audit_trail found in assessment");
        setArbitratorAnalysis("Cross-impact data not available in response.");
        setStage("decision_phase");
      }
    } else {
      console.error("No assessment found in apiResponse");
      setArbitratorAnalysis("Cross-impact analysis data not available.");
      setStage("decision_phase");
    }
  };

  const handleSolutionSelect = (sol: Solution) => {
    setSelectedSolutionId(sol.id);
    setMessages((prev) => [
      ...prev,
      {
        id: `decision-${Date.now()}`,
        agent: "Arbitrator",
        crossImpactAnalysis: `Strategic course set. Initiating Operational Recovery Plan.`,
        isCrossImpactRound: true,
        isDecision: true,
        solutionTitle: sol.title,
      },
    ]);
    setArbitratorAnalysis(`EXECUTING: ${sol.title}`);
  };

  const handleOverride = (text: string) => {
    setSelectedSolutionId("override");
    setMessages((prev) => [
      ...prev,
      {
        id: `override-${Date.now()}`,
        agent: "Arbitrator",
        crossImpactAnalysis: `Manual Directive: "${text}"`,
        isCrossImpactRound: true,
        isDecision: true,
        solutionTitle: "Manual Override Strategy",
      },
    ]);
    setArbitratorAnalysis("Processing Manual Directive...");
  };

  return (
    <div className="flex w-full h-full bg-slate-50 relative overflow-hidden">
      {/* --- Left Side: Chat & Roster (75%) --- */}
      <div className="flex-1 flex flex-col relative h-full">
        {/* Teams-style Top Bar / Roster Overlay */}
        <div className="absolute top-0 left-0 right-0 h-36 bg-white/95 backdrop-blur-xl z-20 flex items-center justify-center border-b border-slate-200/80 shadow-sm pt-6">
          <div className="flex gap-4 md:gap-6 px-6 py-4 overflow-x-auto no-scrollbar w-full justify-center">
            {AGENT_ROSTER.map((agent) => (
              <div
                key={agent}
                className={`transition-all duration-500 transform ${stage === "summoning" ? "opacity-0 translate-y-[-50px]" : "opacity-100 translate-y-0"}`}>
                <AgentAvatar
                  type={agent}
                  size="md"
                  status={
                    activeAgent === agent
                      ? "speaking"
                      : thinkingAgent === agent
                        ? "thinking"
                        : "idle"
                  }
                  showName={true}
                />
              </div>
            ))}
          </div>
        </div>

        {/* Chat Stream */}
        <div className="flex-1 overflow-y-auto pt-40 pb-32 px-4 md:px-12 scroll-smooth">
          {stage === "summoning" && (
            <div className="h-full flex flex-col items-center justify-center opacity-60">
              <BrainCircuit
                size={64}
                className="text-slate-300 animate-pulse mb-4"
              />
              <p className="text-slate-400 font-light">
                Establishing Neural Link...
              </p>
            </div>
          )}

          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((msg) => (
              <AgentMessage key={msg.id} message={msg} isNew={true} />
            ))}

            {/* Thinking Indicator in Stream */}
            {thinkingAgent && (
              <div className="flex gap-4 w-full max-w-4xl mx-auto animate-pulse opacity-70">
                <div className="flex-shrink-0 mt-1">
                  <AgentAvatar
                    type={thinkingAgent}
                    size="sm"
                    status="thinking"
                  />
                </div>
                <div className="flex items-center text-slate-400 text-sm font-medium italic">
                  {thinkingAgent} agent is analyzing...
                </div>
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        </div>

        {/* Status Updates and Action Bar (Floating at bottom of left panel) */}
        <div className="absolute bottom-0 left-0 right-0 z-20 bg-gradient-to-t from-slate-50 via-slate-50/95 to-transparent pt-8 pb-6">
          {/* Loading Indicator with Status */}
          {loading && progress && (
            <div className="flex flex-col items-center gap-3 mb-4 px-6">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 bg-sky-500 rounded-full animate-pulse"></div>
                <span className="text-sm text-slate-600 font-medium">
                  {progress}
                </span>
              </div>
              <div className="w-64 h-1 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full bg-sky-500 rounded-full animate-pulse w-1/2"></div>
              </div>
            </div>
          )}

          {/* Action Button */}
          {stage === "waiting_for_user" && !loading && (
            <div className="flex justify-center">
              <button
                onClick={handleCrossImpact}
                className="group flex items-center gap-3 px-8 py-4 bg-slate-900 text-white rounded-full shadow-2xl hover:bg-slate-800 hover:scale-105 transition-all duration-300 ring-4 ring-white/50">
                <BrainCircuit size={20} className="text-sky-400" />
                <span className="font-semibold text-lg">
                  Run Cross-Impact Analysis
                </span>
                <ChevronRight className="group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* --- Right Side: Arbitrator Panel (25% or fixed width) --- */}
      <div className="w-[350px] md:w-[28%] flex-shrink-0 relative z-30 h-full hidden md:block">
        <ArbitratorPanel
          stage={stage}
          liveAnalysis={arbitratorAnalysis}
          solutions={solutions}
          onSelectSolution={handleSolutionSelect}
          onOverride={handleOverride}
          selectedSolutionId={selectedSolutionId}
        />
      </div>
    </div>
  );
}
