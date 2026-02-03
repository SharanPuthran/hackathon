import React, { useState } from "react";
import { AgentAvatar } from "./AgentAvatar";
import {
  BrainCircuit,
  CheckCircle2,
  AlertTriangle,
  Send,
  X,
  Star,
  Check,
  TrendingUp,
  Shield,
  Users,
  DollarSign,
  Network,
} from "lucide-react";

export interface Solution {
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
  cost: string;
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

interface ArbitratorPanelProps {
  stage:
    | "summoning"
    | "initial_round"
    | "waiting_for_user"
    | "cross_impact"
    | "decision_phase";
  liveAnalysis: string;
  solutions: Solution[];
  onSelectSolution: (solution: Solution) => void;
  onOverride: (text: string) => void;
  selectedSolutionId: string | null;
}

// Score Bar Component
const ScoreBar: React.FC<{
  label: string;
  value: number;
  icon: React.ReactNode;
}> = ({ label, value, icon }) => {
  const getColor = (score: number) => {
    if (score >= 75) return "bg-emerald-500";
    if (score >= 50) return "bg-amber-500";
    return "bg-red-500";
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex items-center gap-1 min-w-[80px]">
        <span className="text-slate-500">{icon}</span>
        <span className="text-xs text-slate-600 font-medium">{label}</span>
      </div>
      <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${getColor(value)} transition-all duration-500`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className="text-xs font-mono text-slate-700 min-w-[35px] text-right">
        {value}
      </span>
    </div>
  );
};

// Expanded Solution View Modal
const ExpandedSolutionView: React.FC<{
  solution: Solution;
  onClose: () => void;
}> = ({ solution, onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
    <div className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      {/* Header */}
      <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold text-slate-800">{solution.title}</h3>
          <p className="text-xs text-slate-500">
            Solution ID: {solution.solution_id}
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-slate-200 rounded-full text-slate-500 transition-colors">
          <X size={20} />
        </button>
      </div>

      {/* Body */}
      <div className="p-6 overflow-y-auto space-y-6">
        {/* Justification */}
        {solution.justification && (
          <section>
            <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2 pb-2 border-b border-slate-100">
              Justification
            </h4>
            <p className="text-sm text-slate-600 leading-relaxed">
              {solution.justification}
            </p>
          </section>
        )}

        {/* Reasoning */}
        {solution.reasoning && (
          <section>
            <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2 pb-2 border-b border-slate-100">
              Reasoning
            </h4>
            <p className="text-sm text-slate-600 leading-relaxed">
              {solution.reasoning}
            </p>
          </section>
        )}

        {/* Impact Analysis */}
        <section>
          <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2 pb-2 border-b border-slate-100">
            Impact Analysis
          </h4>
          <div className="space-y-3">
            {solution.passenger_impact && (
              <div className="p-3 bg-blue-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Users size={14} className="text-blue-600" />
                  <span className="text-xs font-semibold text-blue-900">
                    Passenger Impact
                  </span>
                </div>
                <p className="text-xs text-slate-600">
                  {solution.passenger_impact}
                </p>
              </div>
            )}
            {solution.financial_impact && (
              <div className="p-3 bg-emerald-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <DollarSign size={14} className="text-emerald-600" />
                  <span className="text-xs font-semibold text-emerald-900">
                    Financial Impact
                  </span>
                </div>
                <p className="text-xs text-slate-600">
                  {solution.financial_impact}
                </p>
              </div>
            )}
            {solution.network_impact && (
              <div className="p-3 bg-purple-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <Network size={14} className="text-purple-600" />
                  <span className="text-xs font-semibold text-purple-900">
                    Network Impact
                  </span>
                </div>
                <p className="text-xs text-slate-600">
                  {solution.network_impact}
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Pros */}
        {solution.pros && solution.pros.length > 0 && (
          <section>
            <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2 pb-2 border-b border-slate-100">
              Pros
            </h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-slate-600">
              {solution.pros.map((pro, idx) => (
                <li key={idx}>{pro}</li>
              ))}
            </ul>
          </section>
        )}

        {/* Cons */}
        {solution.cons && solution.cons.length > 0 && (
          <section>
            <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2 pb-2 border-b border-slate-100">
              Cons
            </h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-slate-600">
              {solution.cons.map((con, idx) => (
                <li key={idx}>{con}</li>
              ))}
            </ul>
          </section>
        )}

        {/* Risks */}
        {solution.risks && solution.risks.length > 0 && (
          <section>
            <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2 pb-2 border-b border-slate-100 flex items-center gap-2">
              <AlertTriangle size={14} className="text-amber-600" />
              Risks
            </h4>
            <ul className="list-disc list-inside space-y-1 text-sm text-slate-600">
              {solution.risks.map((risk, idx) => (
                <li key={idx}>{risk}</li>
              ))}
            </ul>
          </section>
        )}
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-100 bg-white flex justify-end">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 rounded-lg">
          Close
        </button>
      </div>
    </div>
  </div>
);

export const ArbitratorPanel: React.FC<ArbitratorPanelProps> = ({
  stage,
  liveAnalysis,
  solutions,
  onSelectSolution,
  onOverride,
  selectedSolutionId,
}) => {
  const [showOverride, setShowOverride] = useState(false);
  const [overrideText, setOverrideText] = useState("");
  const [expandedSolution, setExpandedSolution] = useState<Solution | null>(
    null,
  );

  const handleOverrideSubmit = () => {
    if (overrideText.trim()) {
      onOverride(overrideText);
      setShowOverride(false);
      setOverrideText("");
    }
  };

  return (
    <div className="w-full h-full bg-white border-l border-slate-200 shadow-xl flex flex-col z-30">
      {/* Header */}
      <div className="p-5 border-b border-slate-100 bg-slate-50/50 backdrop-blur-sm">
        <div className="flex items-center gap-3 mb-1">
          <AgentAvatar type="Arbitrator" size="sm" />
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-widest">
            Arbitrator Intelligence
          </h2>
        </div>
        <div className="flex items-center gap-2 ml-1">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <span className="text-xs text-slate-500 font-mono">
            Status:{" "}
            {stage === "decision_phase"
              ? "DECISION REQUIRED"
              : "ANALYZING STREAM"}
          </span>
        </div>
      </div>

      {/* Live Analysis Stream */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        {/* Dynamic Analysis Block */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Live Synthesis
          </h3>
          <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100 text-sm text-slate-700 leading-relaxed font-medium animate-fade-in-up">
            <BrainCircuit
              size={16}
              className="inline mr-2 text-indigo-500 mb-0.5"
            />
            {liveAnalysis}
          </div>

          {/* Show progress if available */}
          {stage === "summoning" && liveAnalysis.includes("Initializing") && (
            <div className="mt-2 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div className="flex items-center gap-2 text-xs text-slate-600">
                <div className="animate-spin rounded-full h-3 w-3 border-2 border-indigo-500 border-t-transparent"></div>
                <span>Connecting to AgentCore Runtime...</span>
              </div>
            </div>
          )}
        </div>

        {/* Proposed Solutions (Only visible in decision phase) */}
        {stage === "decision_phase" && (
          <div className="space-y-3 animate-fade-in-up">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>Strategic Options</span>
              {solutions.length > 0 && (
                <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                  Action Required
                </span>
              )}
            </h3>

            {solutions.length === 0 && (
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle size={16} className="text-amber-600" />
                  <span className="text-sm font-semibold text-amber-900">
                    No Solutions Available
                  </span>
                </div>
                <p className="text-xs text-amber-700 leading-relaxed">
                  The arbitrator was unable to generate solution options. This
                  may be due to system errors or conflicting constraints. Please
                  review the analysis above for details.
                </p>
              </div>
            )}

            {solutions.map((sol) => {
              const isSelected = selectedSolutionId === sol.id;
              const isRecommended = sol.recommended;
              const isOtherSelected = selectedSolutionId && !isSelected;

              return (
                <button
                  key={sol.id}
                  onClick={() => onSelectSolution(sol)}
                  disabled={!!selectedSolutionId}
                  className={`
                    w-full text-left group relative p-4 rounded-xl transition-all duration-300
                    ${
                      isSelected
                        ? "bg-emerald-50 border-2 border-emerald-500 ring-4 ring-emerald-500/20 shadow-lg scale-[1.02]"
                        : isRecommended && !isOtherSelected
                          ? "bg-gradient-to-br from-indigo-50 to-white border-2 border-indigo-500 ring-2 ring-indigo-500/10 shadow-md"
                          : "bg-white border border-slate-200 hover:border-indigo-300 hover:bg-slate-50"
                    }
                    ${isOtherSelected ? "opacity-50 grayscale" : "opacity-100"}
                  `}>
                  {/* Tags */}
                  <div className="flex gap-2 mb-2">
                    {isRecommended && (
                      <div
                        className={`
                        text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm
                        ${isSelected ? "bg-emerald-100 text-emerald-700" : "bg-indigo-600 text-white"}
                      `}>
                        <Star size={10} fill="currentColor" />
                        AI Recommended
                      </div>
                    )}
                    {isSelected && (
                      <div className="bg-emerald-600 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                        <Check size={10} />
                        Selected
                      </div>
                    )}
                  </div>

                  <div className="flex justify-between items-start mb-1 mt-1">
                    <h4
                      className={`font-semibold transition-colors ${isSelected ? "text-emerald-900" : isRecommended ? "text-indigo-900" : "text-slate-800 group-hover:text-indigo-700"}`}>
                      {sol.title}
                    </h4>
                    <span className="text-xs font-mono text-slate-500">
                      {sol.cost}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed mb-3">
                    {sol.description}
                  </p>

                  {/* NEW: Display recommendations */}
                  {sol.recommendations && sol.recommendations.length > 0 && (
                    <ul className="text-xs text-slate-600 space-y-1 mb-3 list-disc list-inside">
                      {sol.recommendations.slice(0, 2).map((rec, idx) => (
                        <li key={idx}>{rec}</li>
                      ))}
                    </ul>
                  )}

                  {/* NEW: Scoring bars */}
                  <div className="space-y-2 mb-3 bg-slate-50/50 p-3 rounded-lg">
                    <ScoreBar
                      label="Safety"
                      value={sol.safety_score}
                      icon={<Shield size={12} />}
                    />
                    <ScoreBar
                      label="Passenger"
                      value={sol.passenger_score}
                      icon={<Users size={12} />}
                    />
                    <ScoreBar
                      label="Network"
                      value={sol.network_score}
                      icon={<Network size={12} />}
                    />
                    <ScoreBar
                      label="Cost"
                      value={sol.cost_score}
                      icon={<DollarSign size={12} />}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        sol.impact === "high"
                          ? "bg-red-100 text-red-600"
                          : sol.impact === "medium"
                            ? "bg-amber-100 text-amber-600"
                            : "bg-green-100 text-green-600"
                      }`}>
                      {sol.impact} Risk
                    </span>

                    {/* NEW: View More button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setExpandedSolution(sol);
                      }}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1">
                      View More
                      <TrendingUp size={12} />
                    </button>
                  </div>

                  {/* Hover check circle (only if not selected) */}
                  {!isSelected && !selectedSolutionId && (
                    <div className="absolute right-4 bottom-4 opacity-0 group-hover:opacity-100 transition-opacity">
                      <CheckCircle2 className="text-indigo-600" size={20} />
                    </div>
                  )}
                </button>
              );
            })}

            {/* Override Button (Disabled if a selection is made) */}
            <div
              className={`pt-4 border-t border-slate-100 ${selectedSolutionId ? "opacity-40 pointer-events-none" : ""}`}>
              <button
                onClick={() => setShowOverride(true)}
                disabled={!!selectedSolutionId}
                className="w-full py-3 px-4 rounded-xl border border-dashed border-slate-300 text-slate-500 text-sm font-medium hover:bg-slate-50 hover:text-slate-800 transition-colors flex items-center justify-center gap-2">
                <AlertTriangle size={16} />
                Reject & Override Strategy
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Override Modal Overlay */}
      {showOverride && (
        <div className="absolute inset-0 bg-white/95 backdrop-blur-xl z-50 flex flex-col p-6 animate-fade-in">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-bold text-slate-800 text-lg">
              Manual Override
            </h3>
            <button
              onClick={() => setShowOverride(false)}
              className="p-2 hover:bg-slate-100 rounded-full text-slate-500">
              <X size={20} />
            </button>
          </div>
          <p className="text-sm text-slate-500 mb-4">
            Rejecting AI suggestions. Please specify the mandatory course of
            action for the recovery agents.
          </p>
          <textarea
            className="flex-1 w-full bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none mb-4"
            placeholder="E.g., Prioritize crew rest at outstation and delay flight 12 hours. Accept hotel costs..."
            value={overrideText}
            onChange={(e) => setOverrideText(e.target.value)}
          />
          <button
            onClick={handleOverrideSubmit}
            disabled={!overrideText.trim()}
            className="w-full py-3 bg-slate-900 text-white rounded-xl font-semibold shadow-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
            <Send size={18} />
            Submit Directive
          </button>
        </div>
      )}

      {/* Expanded Solution Modal */}
      {expandedSolution && (
        <ExpandedSolutionView
          solution={expandedSolution}
          onClose={() => setExpandedSolution(null)}
        />
      )}
    </div>
  );
};
