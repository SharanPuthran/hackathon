import React, { useState, useMemo } from "react";
import { AgentAvatar } from "./AgentAvatar";
import { MarkdownContent } from "./MarkdownContent";
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
  Clock,
  Plane,
  CheckCircle,
  XCircle,
  Info,
  Play,
  Activity,
  RefreshCw,
} from "lucide-react";
import {
  PassengerImpact,
  FinancialImpact,
  NetworkImpact,
  RecoveryPlan,
  RecoveryStep,
  ContingencyPlan,
} from "../services/responseMapper";

export interface Solution {
  id: string;
  solution_id: number;
  title: string;
  description: string;
  recommendations: string[];
  safety_score: number;
  passenger_score: number;
  network_score: number;
  cost_score: number;
  composite_score: number;
  impact: "low" | "medium" | "high";
  cost: string;
  justification: string;
  reasoning: string;
  passenger_impact: PassengerImpact | string;
  financial_impact: FinancialImpact | string;
  network_impact: NetworkImpact | string;
  safety_compliance?: string;
  pros: string[];
  cons: string[];
  risks: string[];
  confidence: number;
  estimated_duration: string;
  recommended: boolean;
  recovery_plan?: RecoveryPlan;
}

// Backend name → Frontend recovery agent name mapping
const AGENT_ALIAS_MAP: Record<string, string> = {
  network: 'flight_scheduling',
  guest_experience: 'guest_recovery',
  crew_compliance: 'crew_recovery',
  cargo: 'cargo_recovery',
  maintenance: 'maintenance',
  regulatory: 'regulatory',
  finance: 'finance',
  communications: 'communications',
};

// Recovery agent styles with new names and labels
const RECOVERY_AGENT_CONFIG: Record<string, { bg: string; text: string; icon: string; label: string }> = {
  flight_scheduling: { bg: 'bg-purple-50', text: 'text-purple-700', icon: '✈️', label: 'Flight Scheduling' },
  guest_recovery: { bg: 'bg-pink-50', text: 'text-pink-700', icon: '💺', label: 'Guest Recovery' },
  crew_recovery: { bg: 'bg-blue-50', text: 'text-blue-700', icon: '👥', label: 'Crew Recovery' },
  cargo_recovery: { bg: 'bg-orange-50', text: 'text-orange-700', icon: '📦', label: 'Cargo Recovery' },
  communications: { bg: 'bg-cyan-50', text: 'text-cyan-700', icon: '📢', label: 'Communications' },
  maintenance: { bg: 'bg-amber-50', text: 'text-amber-700', icon: '🔧', label: 'Maintenance' },
  regulatory: { bg: 'bg-slate-100', text: 'text-slate-700', icon: '📜', label: 'Regulatory' },
  finance: { bg: 'bg-emerald-50', text: 'text-emerald-700', icon: '💰', label: 'Finance' },
};

function getAgentStyle(agent: string | undefined): { bg: string; text: string; icon: string; label: string } {
  // Handle undefined or null agent
  if (!agent) {
    return {
      bg: 'bg-slate-50',
      text: 'text-slate-700',
      icon: '🔹',
      label: 'Unknown Agent'
    };
  }
  const normalizedName = agent.toLowerCase().replace(/\s+/g, '_');
  const aliasedName = AGENT_ALIAS_MAP[normalizedName] || normalizedName;
  return RECOVERY_AGENT_CONFIG[aliasedName] || {
    bg: 'bg-slate-50',
    text: 'text-slate-700',
    icon: '🔹',
    label: normalizedName.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  };
}

// Alternative impact formats (from some solution files)
interface AlternativePassengerImpact {
  affected_count: number;
  delay_hours: number;
  cancellation_flag: boolean;
}

interface AlternativeFinancialImpact {
  total_cost: number;
  breakdown: {
    aircraft_positioning?: number;
    crew_coordination?: number;
    passenger_compensation?: number;
    [key: string]: number | undefined;
  };
}

interface AlternativeNetworkImpact {
  downstream_flights: number;
  connection_misses: number;
}

// Helper functions to format impact objects
function isPassengerImpact(impact: PassengerImpact | string | AlternativePassengerImpact): impact is PassengerImpact {
  return typeof impact === 'object' && impact !== null && 'total_passengers' in impact;
}

function isAlternativePassengerImpact(impact: unknown): impact is AlternativePassengerImpact {
  return typeof impact === 'object' && impact !== null && 'affected_count' in impact;
}

function isAlternativeFinancialImpact(impact: unknown): impact is AlternativeFinancialImpact {
  return typeof impact === 'object' && impact !== null && 'total_cost' in impact && 'breakdown' in impact;
}

function isAlternativeNetworkImpact(impact: unknown): impact is AlternativeNetworkImpact {
  return typeof impact === 'object' && impact !== null && 'downstream_flights' in impact && 'connection_misses' in impact;
}

function isFinancialImpact(impact: FinancialImpact | string): impact is FinancialImpact {
  return typeof impact === 'object' && impact !== null && 'total_estimated_cost' in impact;
}

function isNetworkImpact(impact: NetworkImpact | string): impact is NetworkImpact {
  return typeof impact === 'object' && impact !== null && 'downstream_flights_affected' in impact;
}

function formatCurrency(amount: number, currency: string = 'USD'): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M ${currency}`;
  } else if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K ${currency}`;
  }
  return `$${amount} ${currency}`;
}

function getPassengerSummary(impact: PassengerImpact | string | AlternativePassengerImpact): string {
  if (isPassengerImpact(impact)) {
    return `${impact.total_passengers} pax`;
  }
  if (isAlternativePassengerImpact(impact)) {
    return `${impact.affected_count} pax`;
  }
  return typeof impact === 'string' ? impact.substring(0, 20) + '...' : '';
}

function getDelaySummary(impact: PassengerImpact | string | AlternativePassengerImpact): string {
  if (isPassengerImpact(impact)) {
    return `${impact.delay_minutes} min`;
  }
  if (isAlternativePassengerImpact(impact)) {
    return `${impact.delay_hours}h`;
  }
  return '';
}

function getCostSummary(impact: FinancialImpact | string | AlternativeFinancialImpact): string {
  if (isFinancialImpact(impact)) {
    return formatCurrency(impact.total_estimated_cost, impact.currency);
  }
  if (isAlternativeFinancialImpact(impact)) {
    return formatCurrency(impact.total_cost);
  }
  return typeof impact === 'string' ? impact.substring(0, 20) + '...' : '';
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
  onUnselectSolution?: () => void;
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

// Passenger Impact Detail Component
const PassengerImpactDetail: React.FC<{ impact: PassengerImpact | string | AlternativePassengerImpact }> = ({ impact }) => {
  // Handle standard PassengerImpact format
  if (isPassengerImpact(impact)) {
    return (
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="flex items-center gap-2">
          <Users size={14} className="text-blue-500" />
          <span className="text-slate-600">Total Passengers:</span>
          <span className="font-semibold text-slate-800">{impact.total_passengers}</span>
        </div>
        <div className="flex items-center gap-2">
          <Plane size={14} className="text-blue-500" />
          <span className="text-slate-600">Connecting:</span>
          <span className="font-semibold text-slate-800">{impact.connecting_passengers}</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-blue-500" />
          <span className="text-slate-600">Delay:</span>
          <span className="font-semibold text-slate-800">{impact.delay_minutes} min</span>
        </div>
        <div className="flex items-center gap-2">
          <XCircle size={14} className="text-red-500" />
          <span className="text-slate-600">Missed Connections:</span>
          <span className="font-semibold text-slate-800">{impact.missed_connections}</span>
        </div>
        <div className="flex items-center gap-2">
          {impact.compensation_required ? (
            <CheckCircle size={14} className="text-amber-500" />
          ) : (
            <XCircle size={14} className="text-green-500" />
          )}
          <span className="text-slate-600">Compensation:</span>
          <span className="font-semibold text-slate-800">
            {impact.compensation_required ? 'Required' : 'Not Required'}
          </span>
        </div>
        <div className="flex items-center gap-2 col-span-2">
          <Info size={14} className="text-blue-500" />
          <span className="text-slate-600">Notifications:</span>
          <span className="font-semibold text-slate-800">{impact.passenger_notifications}</span>
        </div>
      </div>
    );
  }

  // Handle alternative format (affected_count, delay_hours, cancellation_flag)
  if (isAlternativePassengerImpact(impact)) {
    return (
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="flex items-center gap-2">
          <Users size={14} className="text-blue-500" />
          <span className="text-slate-600">Affected Passengers:</span>
          <span className="font-semibold text-slate-800">{impact.affected_count}</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock size={14} className="text-blue-500" />
          <span className="text-slate-600">Delay:</span>
          <span className="font-semibold text-slate-800">{impact.delay_hours} hours</span>
        </div>
        <div className="flex items-center gap-2">
          {impact.cancellation_flag ? (
            <XCircle size={14} className="text-red-500" />
          ) : (
            <CheckCircle size={14} className="text-green-500" />
          )}
          <span className="text-slate-600">Cancellation:</span>
          <span className="font-semibold text-slate-800">
            {impact.cancellation_flag ? 'Yes' : 'No'}
          </span>
        </div>
      </div>
    );
  }

  // Handle string format
  if (typeof impact === 'string') {
    return <div className="text-sm text-slate-600">{impact}</div>;
  }

  // Fallback for unknown object format - display as JSON
  return <div className="text-sm text-slate-600">{JSON.stringify(impact, null, 2)}</div>;
};

// Financial Impact Detail Component
const FinancialImpactDetail: React.FC<{ impact: FinancialImpact | string | AlternativeFinancialImpact }> = ({ impact }) => {
  // Handle standard FinancialImpact format
  if (isFinancialImpact(impact)) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between p-2 bg-emerald-100 rounded-lg">
          <span className="text-sm font-semibold text-emerald-900">Total Estimated Cost</span>
          <span className="text-lg font-bold text-emerald-700">{formatCurrency(impact.total_estimated_cost, impact.currency)}</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          {impact.aircraft_swap_cost > 0 && (
            <div className="flex justify-between p-2 bg-slate-50 rounded">
              <span className="text-slate-600">Aircraft Swap</span>
              <span className="font-medium text-slate-800">{formatCurrency(impact.aircraft_swap_cost, impact.currency)}</span>
            </div>
          )}
          {impact.crew_costs > 0 && (
            <div className="flex justify-between p-2 bg-slate-50 rounded">
              <span className="text-slate-600">Crew Costs</span>
              <span className="font-medium text-slate-800">{formatCurrency(impact.crew_costs, impact.currency)}</span>
            </div>
          )}
          {impact.passenger_compensation > 0 && (
            <div className="flex justify-between p-2 bg-slate-50 rounded">
              <span className="text-slate-600">Passenger Comp.</span>
              <span className="font-medium text-slate-800">{formatCurrency(impact.passenger_compensation, impact.currency)}</span>
            </div>
          )}
          {impact.rebooking_costs && impact.rebooking_costs > 0 && (
            <div className="flex justify-between p-2 bg-slate-50 rounded">
              <span className="text-slate-600">Rebooking</span>
              <span className="font-medium text-slate-800">{formatCurrency(impact.rebooking_costs, impact.currency)}</span>
            </div>
          )}
          {impact.hotel_accommodation && impact.hotel_accommodation > 0 && (
            <div className="flex justify-between p-2 bg-slate-50 rounded">
              <span className="text-slate-600">Hotel</span>
              <span className="font-medium text-slate-800">{formatCurrency(impact.hotel_accommodation, impact.currency)}</span>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Handle alternative format (total_cost + breakdown)
  if (isAlternativeFinancialImpact(impact)) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between p-2 bg-emerald-100 rounded-lg">
          <span className="text-sm font-semibold text-emerald-900">Total Cost</span>
          <span className="text-lg font-bold text-emerald-700">{formatCurrency(impact.total_cost)}</span>
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(impact.breakdown).map(([key, value]) => (
            value && value > 0 && (
              <div key={key} className="flex justify-between p-2 bg-slate-50 rounded">
                <span className="text-slate-600 capitalize">{key.replace(/_/g, ' ')}</span>
                <span className="font-medium text-slate-800">{formatCurrency(value)}</span>
              </div>
            )
          ))}
        </div>
      </div>
    );
  }

  // Handle string format
  if (typeof impact === 'string') {
    return <div className="text-sm text-slate-600">{impact}</div>;
  }

  // Fallback for unknown object format
  return <div className="text-sm text-slate-600">{JSON.stringify(impact, null, 2)}</div>;
};

// Network Impact Detail Component
const NetworkImpactDetail: React.FC<{ impact: NetworkImpact | string | AlternativeNetworkImpact }> = ({ impact }) => {
  // Handle standard NetworkImpact format
  if (isNetworkImpact(impact)) {
    return (
      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between p-2 bg-purple-100 rounded-lg">
          <span className="text-purple-900">Downstream Flights Affected</span>
          <span className="text-lg font-bold text-purple-700">{impact.downstream_flights_affected}</span>
        </div>
        <div className="flex items-center gap-2 p-2 bg-slate-50 rounded">
          {impact.rotation_preserved ? (
            <>
              <CheckCircle size={16} className="text-green-500" />
              <span className="text-green-700 font-medium">Rotation Preserved</span>
            </>
          ) : (
            <>
              <XCircle size={16} className="text-red-500" />
              <span className="text-red-700 font-medium">Rotation Not Preserved</span>
            </>
          )}
        </div>
        {impact.EY17_connection_protected !== undefined && (
          <div className="flex items-center gap-2 p-2 bg-slate-50 rounded">
            {impact.EY17_connection_protected ? (
              <>
                <CheckCircle size={16} className="text-green-500" />
                <span className="text-green-700 font-medium">EY17 Connection Protected</span>
              </>
            ) : (
              <>
                <XCircle size={16} className="text-red-500" />
                <span className="text-red-700 font-medium">EY17 Connection At Risk</span>
              </>
            )}
          </div>
        )}
        <div className="p-2 bg-slate-50 rounded">
          <span className="text-slate-600">Propagation: </span>
          <span className="font-medium text-slate-800">{impact.network_propagation}</span>
        </div>
      </div>
    );
  }

  // Handle alternative format (downstream_flights + connection_misses)
  if (isAlternativeNetworkImpact(impact)) {
    return (
      <div className="space-y-2 text-sm">
        <div className="flex items-center justify-between p-2 bg-purple-100 rounded-lg">
          <span className="text-purple-900">Downstream Flights</span>
          <span className="text-lg font-bold text-purple-700">{impact.downstream_flights}</span>
        </div>
        <div className="flex items-center gap-2 p-2 bg-slate-50 rounded">
          {impact.connection_misses === 0 ? (
            <>
              <CheckCircle size={16} className="text-green-500" />
              <span className="text-green-700 font-medium">No Connection Misses</span>
            </>
          ) : (
            <>
              <XCircle size={16} className="text-red-500" />
              <span className="text-red-700 font-medium">{impact.connection_misses} Connection Misses</span>
            </>
          )}
        </div>
      </div>
    );
  }

  // Handle string format
  if (typeof impact === 'string') {
    return <div className="text-sm text-slate-600">{impact}</div>;
  }

  // Fallback for unknown object format
  return <div className="text-sm text-slate-600">{JSON.stringify(impact, null, 2)}</div>;
};

// Expanded Solution View Modal
const ExpandedSolutionView: React.FC<{
  solution: Solution;
  onClose: () => void;
}> = ({ solution, onClose }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
    <div className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-slate-50 to-indigo-50 border-b border-slate-100">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              {solution.recommended && (
                <span className="bg-indigo-600 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1">
                  <Star size={10} fill="currentColor" />
                  SkyMarshal Recommended
                </span>
              )}
            </div>
            <h3 className="text-xl font-bold text-slate-800">{solution.title}</h3>
            <p className="text-sm text-slate-500 mt-1">{solution.description}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-200 rounded-full text-slate-500 transition-colors ml-4">
            <X size={20} />
          </button>
        </div>
        {/* Score Summary */}
        <div className="flex items-center gap-4 mt-4 pt-4 border-t border-slate-200">
          <div className="flex items-center gap-2">
            <div className="w-12 h-12 rounded-full bg-indigo-600 flex items-center justify-center">
              <span className="text-white font-bold text-lg">{solution.composite_score}</span>
            </div>
            <div>
              <div className="text-xs text-slate-500">Composite</div>
              <div className="text-sm font-semibold text-slate-700">Score</div>
            </div>
          </div>
          <div className="h-10 w-px bg-slate-200" />
          <div className="flex items-center gap-2">
            <div className="text-2xl font-bold text-slate-700">{Math.round((solution.confidence || 0) * 100)}%</div>
            <div className="text-xs text-slate-500">Confidence</div>
          </div>
          <div className="h-10 w-px bg-slate-200" />
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-slate-400" />
            <span className="text-sm text-slate-600">{solution.estimated_duration || 'N/A'}</span>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-6 overflow-y-auto space-y-6">
        {/* Recommendations */}
        {solution.recommendations && solution.recommendations.length > 0 && (
          <section>
            <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3 flex items-center gap-2">
              <CheckCircle size={16} className="text-indigo-500" />
              Recommendations
            </h4>
            <div className="space-y-2">
              {solution.recommendations.map((rec, idx) => (
                <div key={idx} className="flex items-start gap-2 p-2 bg-indigo-50 rounded-lg">
                  <Check size={14} className="text-indigo-600 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-slate-700">{rec}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Score Breakdown */}
        <section>
          <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
            Score Breakdown
          </h4>
          <div className="space-y-2 bg-slate-50 p-4 rounded-xl">
            <ScoreBar label="Safety" value={solution.safety_score} icon={<Shield size={12} />} />
            <ScoreBar label="Passenger" value={solution.passenger_score} icon={<Users size={12} />} />
            <ScoreBar label="Network" value={solution.network_score} icon={<Network size={12} />} />
            <ScoreBar label="Cost" value={solution.cost_score} icon={<DollarSign size={12} />} />
          </div>
        </section>

        {/* Impact Analysis */}
        <section>
          <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-3">
            Impact Analysis
          </h4>
          <div className="space-y-4">
            {solution.passenger_impact && (
              <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                <div className="flex items-center gap-2 mb-3">
                  <Users size={16} className="text-blue-600" />
                  <span className="text-sm font-semibold text-blue-900">Passenger Impact</span>
                </div>
                <PassengerImpactDetail impact={solution.passenger_impact} />
              </div>
            )}
            {solution.financial_impact && (
              <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                <div className="flex items-center gap-2 mb-3">
                  <DollarSign size={16} className="text-emerald-600" />
                  <span className="text-sm font-semibold text-emerald-900">Financial Impact</span>
                </div>
                <FinancialImpactDetail impact={solution.financial_impact} />
              </div>
            )}
            {solution.network_impact && (
              <div className="p-4 bg-purple-50 rounded-xl border border-purple-100">
                <div className="flex items-center gap-2 mb-3">
                  <Network size={16} className="text-purple-600" />
                  <span className="text-sm font-semibold text-purple-900">Network Impact</span>
                </div>
                <NetworkImpactDetail impact={solution.network_impact} />
              </div>
            )}
          </div>
        </section>

        {/* Justification */}
        {solution.justification && (
          <section>
            <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-2 pb-2 border-b border-slate-100">
              Justification
            </h4>
            <div className="text-sm text-slate-600">
              <MarkdownContent content={solution.justification} />
            </div>
          </section>
        )}

        {/* Pros, Cons, Risks Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Pros */}
          {solution.pros && solution.pros.length > 0 && (
            <div className="p-4 bg-green-50 rounded-xl border border-green-100">
              <h4 className="text-sm font-bold text-green-800 mb-2 flex items-center gap-2">
                <CheckCircle size={14} className="text-green-600" />
                Pros
              </h4>
              <ul className="space-y-1.5">
                {solution.pros.map((pro, idx) => (
                  <li key={idx} className="text-xs text-green-700 flex items-start gap-1.5">
                    <Check size={12} className="text-green-500 mt-0.5 flex-shrink-0" />
                    {pro}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Cons */}
          {solution.cons && solution.cons.length > 0 && (
            <div className="p-4 bg-amber-50 rounded-xl border border-amber-100">
              <h4 className="text-sm font-bold text-amber-800 mb-2 flex items-center gap-2">
                <AlertTriangle size={14} className="text-amber-600" />
                Cons
              </h4>
              <ul className="space-y-1.5">
                {solution.cons.map((con, idx) => (
                  <li key={idx} className="text-xs text-amber-700 flex items-start gap-1.5">
                    <AlertTriangle size={12} className="text-amber-500 mt-0.5 flex-shrink-0" />
                    {con}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Risks */}
          {solution.risks && solution.risks.length > 0 && (
            <div className="p-4 bg-red-50 rounded-xl border border-red-100">
              <h4 className="text-sm font-bold text-red-800 mb-2 flex items-center gap-2">
                <XCircle size={14} className="text-red-600" />
                Risks
              </h4>
              <ul className="space-y-1.5">
                {solution.risks.map((risk, idx) => (
                  <li key={idx} className="text-xs text-red-700 flex items-start gap-1.5">
                    <XCircle size={12} className="text-red-500 mt-0.5 flex-shrink-0" />
                    {risk}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">
          Close
        </button>
      </div>
    </div>
  </div>
);

// Recovery Plan Modal Component
export const RecoveryPlanModal: React.FC<{
  solution: Solution;
  onClose: () => void;
  onExecuteRecovery?: () => void;
  recoveryExecuted?: boolean;
}> = ({ solution, onClose, onExecuteRecovery, recoveryExecuted = false }) => {
  const [showContingencies, setShowContingencies] = useState(true);
  const recoveryPlan = solution.recovery_plan;

  if (!recoveryPlan) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
        <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl p-8 text-center">
          <AlertTriangle size={48} className="text-amber-500 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-800 mb-2">No Recovery Plan Available</h3>
          <p className="text-slate-600 mb-6">The recovery plan data is not available for this solution.</p>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-slate-800 text-white rounded-lg font-semibold hover:bg-slate-700">
            Close
          </button>
        </div>
      </div>
    );
  }

  const criticalPath = new Set(recoveryPlan.critical_path);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[95vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-indigo-600 to-purple-600 text-white">
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">📋</span>
                <h3 className="text-xl font-bold">Recovery Plan</h3>
              </div>
              <p className="text-indigo-100 text-sm">{solution.title}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-full transition-colors">
              <X size={20} />
            </button>
          </div>
          {/* Stats Row */}
          <div className="flex items-center gap-6 mt-4 pt-4 border-t border-white/20">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-bold">{recoveryPlan.total_steps}</span>
              <span className="text-indigo-200 text-sm">Total Steps</span>
            </div>
            <div className="h-6 w-px bg-white/30" />
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-indigo-200" />
              <span className="font-semibold">{recoveryPlan.estimated_total_duration}</span>
            </div>
            <div className="h-6 w-px bg-white/30" />
            <div className="flex items-center gap-2">
              <span className="text-amber-300">⚡</span>
              <span className="text-indigo-200 text-sm">{recoveryPlan.critical_path.length} Critical</span>
            </div>
          </div>
        </div>

        {/* Body - Steps Timeline */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {recoveryPlan.steps.map((step, index) => {
            const isCritical = criticalPath.has(step.step_number);
            const agentStyle = getAgentStyle(step.responsible_agent);
            const hasDependencies = step.dependencies && step.dependencies.length > 0;

            return (
              <div key={step.step_number} className="relative">
                {/* Connection Line */}
                {index < recoveryPlan.steps.length - 1 && (
                  <div className="absolute left-6 top-16 w-0.5 h-8 bg-slate-200" />
                )}

                {/* Step Card */}
                <div className={`
                  rounded-xl border-2 transition-all
                  ${isCritical
                    ? 'border-amber-400 bg-amber-50/50 shadow-md'
                    : 'border-slate-200 bg-white hover:border-slate-300'}
                `}>
                  {/* Step Header */}
                  <div className="px-4 py-3 flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      {/* Step Number */}
                      <div className={`
                        w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0
                        ${isCritical ? 'bg-amber-500 text-white' : 'bg-slate-200 text-slate-700'}
                      `}>
                        {step.step_number}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <h4 className="font-bold text-slate-800">{step.step_name}</h4>
                          {isCritical && (
                            <span className="text-[10px] bg-amber-500 text-white px-2 py-0.5 rounded-full font-bold flex items-center gap-1">
                              ⚡ CRITICAL PATH
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-600 mt-1">{step.description}</p>
                      </div>
                    </div>
                    {/* Agent Badge */}
                    <div className={`${agentStyle.bg} ${agentStyle.text} px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1 flex-shrink-0`}>
                      <span>{agentStyle.icon}</span>
                      {agentStyle.label.toUpperCase()}
                    </div>
                  </div>

                  {/* Step Details */}
                  <div className="px-4 pb-3 flex flex-wrap items-center gap-3 text-xs">
                    {/* Duration */}
                    <div className="flex items-center gap-1 text-slate-600">
                      <Clock size={12} />
                      <span>{step.estimated_duration}</span>
                    </div>

                    {/* Automation Badge */}
                    {step.automation_possible ? (
                      <div className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                        <span>🤖</span>
                        <span>Automatable</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                        <span>👤</span>
                        <span>Manual</span>
                      </div>
                    )}

                    {/* Action Type */}
                    <div className="text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full capitalize">
                      {step.action_type}
                    </div>

                    {/* Dependencies */}
                    {hasDependencies && (
                      <div className="flex items-center gap-1 text-slate-500">
                        <span>🔗</span>
                        <span>Depends on: Step {step.dependencies.join(', ')}</span>
                      </div>
                    )}
                  </div>

                  {/* Success Criteria */}
                  <div className="px-4 pb-3">
                    <div className="flex items-start gap-2 text-xs p-2 bg-emerald-50 rounded-lg">
                      <CheckCircle size={14} className="text-emerald-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-emerald-800">Success: </span>
                        <span className="text-emerald-700">{step.success_criteria}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {/* Contingency Plans Section */}
          {recoveryPlan.contingency_plans && recoveryPlan.contingency_plans.length > 0 && (
            <div className="mt-6 pt-6 border-t border-slate-200">
              <button
                onClick={() => setShowContingencies(!showContingencies)}
                className="w-full flex items-center justify-between p-3 bg-amber-50 rounded-xl border border-amber-200 hover:bg-amber-100 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <AlertTriangle size={18} className="text-amber-600" />
                  <span className="font-bold text-amber-800">Contingency Plans</span>
                  <span className="text-xs bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full">
                    {recoveryPlan.contingency_plans.length}
                  </span>
                </div>
                <span className="text-amber-600">{showContingencies ? '▲' : '▼'}</span>
              </button>

              {showContingencies && (
                <div className="mt-3 space-y-3">
                  {recoveryPlan.contingency_plans.map((contingency, idx) => {
                    const agentStyle = getAgentStyle(contingency.responsible_agent);
                    return (
                      <div key={idx} className="p-4 bg-white border border-amber-200 rounded-xl">
                        <div className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
                            <span className="text-amber-600 text-xs font-bold">{idx + 1}</span>
                          </div>
                          <div className="flex-1">
                            <div className="text-sm">
                              <span className="font-semibold text-slate-700">IF: </span>
                              <span className="text-slate-600">{contingency.trigger}</span>
                            </div>
                            <div className="text-sm mt-1">
                              <span className="font-semibold text-emerald-700">THEN: </span>
                              <span className="text-slate-600">{contingency.action}</span>
                            </div>
                            <div className="flex items-center gap-2 mt-2">
                              <span className="text-xs text-slate-500">Owner:</span>
                              <span className={`${agentStyle.bg} ${agentStyle.text} text-xs px-2 py-0.5 rounded-full`}>
                                {agentStyle.icon} {agentStyle.label}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-between">
          {onExecuteRecovery && (
            <button
              onClick={onExecuteRecovery}
              disabled={recoveryExecuted}
              className={`px-6 py-2 font-semibold rounded-lg transition-colors flex items-center gap-2
                ${recoveryExecuted
                  ? 'bg-emerald-100 text-emerald-700 cursor-not-allowed'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-lg'
                }`}>
              {recoveryExecuted ? (
                <>
                  <CheckCircle size={18} />
                  Recovery Executed
                </>
              ) : (
                <>
                  <Play size={18} />
                  Execute Recovery
                </>
              )}
            </button>
          )}
          <button
            onClick={onClose}
            className="px-6 py-2 bg-slate-800 text-white rounded-lg font-semibold hover:bg-slate-700 transition-colors ml-auto">
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

// Recovery Execution Modal Component
export const RecoveryExecutionModal: React.FC<{
  solution: Solution;
  onClose: () => void;
  onExecutionComplete: () => void;
}> = ({ solution, onClose, onExecutionComplete }) => {
  const [executionState, setExecutionState] = useState<'not_started' | 'in_progress' | 'completed'>('not_started');
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [agentStatuses, setAgentStatuses] = useState<Map<string, 'idle' | 'working' | 'done'>>(new Map());

  const recoveryPlan = solution.recovery_plan;

  // Extract unique agents from recovery steps
  const uniqueAgents = useMemo(() => {
    if (!recoveryPlan?.steps) return [];
    return [...new Set(recoveryPlan.steps.map(s => s.responsible_agent))];
  }, [recoveryPlan]);

  // Calculate progress percentage
  const progress = useMemo(() => {
    if (!recoveryPlan?.steps) return 0;
    return Math.round((completedSteps.size / recoveryPlan.steps.length) * 100);
  }, [completedSteps, recoveryPlan]);

  // Start execution - simulates step-by-step progress
  const startExecution = async () => {
    if (!recoveryPlan?.steps) return;
    setExecutionState('in_progress');

    // Initialize all agents as idle
    const initialStatus = new Map<string, 'idle' | 'working' | 'done'>();
    uniqueAgents.forEach(agent => initialStatus.set(agent, 'idle'));
    setAgentStatuses(initialStatus);

    // Execute each step sequentially with animation
    for (let i = 0; i < recoveryPlan.steps.length; i++) {
      const step = recoveryPlan.steps[i];
      setCurrentStepIndex(i);

      // Set current agent as working
      setAgentStatuses(prev => new Map(prev).set(step.responsible_agent, 'working'));

      // Simulate step execution (1.5-3 seconds per step)
      await new Promise(r => setTimeout(r, 1500 + Math.random() * 1500));

      // Mark step complete and agent as done
      setCompletedSteps(prev => new Set(prev).add(step.step_number));
      setAgentStatuses(prev => new Map(prev).set(step.responsible_agent, 'done'));
    }

    setExecutionState('completed');
  };

  if (!recoveryPlan) {
    return (
      <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-fade-in">
        <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl p-8 text-center">
          <AlertTriangle size={48} className="text-amber-500 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-slate-800 mb-2">No Recovery Plan Available</h3>
          <p className="text-slate-600 mb-6">Cannot execute recovery without a plan.</p>
          <button
            onClick={onClose}
            className="px-6 py-2 bg-slate-800 text-white rounded-lg font-semibold hover:bg-slate-700">
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[95vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-700 text-white">
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Activity size={20} className="animate-pulse" />
                <h3 className="text-xl font-bold">Recovery Execution</h3>
              </div>
              <p className="text-indigo-100 text-sm">{solution.title}</p>
            </div>
            <button
              onClick={onClose}
              disabled={executionState === 'in_progress'}
              className="p-2 hover:bg-white/20 rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
              <X size={20} />
            </button>
          </div>
          {/* Status Row */}
          <div className="flex items-center gap-6 mt-4 pt-4 border-t border-white/20">
            <div className="flex items-center gap-2">
              <span className={`text-2xl font-bold ${executionState === 'completed' ? 'text-emerald-300' : ''}`}>
                {completedSteps.size}
              </span>
              <span className="text-indigo-200 text-sm">/ {recoveryPlan.total_steps} Steps</span>
            </div>
            <div className="h-6 w-px bg-white/30" />
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${
                executionState === 'not_started' ? 'bg-slate-500/50 text-white' :
                executionState === 'in_progress' ? 'bg-sky-400/50 text-white animate-pulse' :
                'bg-emerald-400/50 text-white'
              }`}>
                {executionState === 'not_started' ? 'Ready' :
                 executionState === 'in_progress' ? 'Executing...' : 'Complete'}
              </span>
            </div>
          </div>
        </div>

        {/* Agent Grid */}
        <div className="px-6 py-4 border-b border-slate-100 bg-slate-50">
          <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">
            Recovery Agents
          </h4>
          <div className="grid grid-cols-4 md:grid-cols-7 gap-3">
            {uniqueAgents.map(agent => {
              const style = getAgentStyle(agent);
              const status = agentStatuses.get(agent) || 'idle';
              return (
                <div
                  key={agent}
                  className={`
                    flex flex-col items-center p-3 rounded-xl border-2 transition-all duration-300
                    ${status === 'working' ? 'border-sky-500 shadow-lg scale-105 bg-sky-50' : ''}
                    ${status === 'done' ? 'border-emerald-500 bg-emerald-50' : ''}
                    ${status === 'idle' ? 'border-slate-200 opacity-50 bg-white' : ''}
                  `}>
                  <span className={`text-2xl mb-1 ${status === 'working' ? 'animate-bounce' : ''}`}>
                    {style.icon}
                  </span>
                  <span className={`text-[9px] font-bold uppercase tracking-wider text-center ${style.text}`}>
                    {style.label}
                  </span>
                  {status === 'done' && <CheckCircle size={14} className="text-emerald-500 mt-1" />}
                  {status === 'working' && <Activity size={14} className="text-sky-500 mt-1 animate-pulse" />}
                </div>
              );
            })}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="px-6 py-3 bg-white border-b border-slate-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-slate-700">Execution Progress</span>
            <span className="text-sm font-mono text-slate-600">{progress}%</span>
          </div>
          <div className="h-3 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-indigo-500 to-emerald-500 transition-all duration-500"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Steps Timeline */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {recoveryPlan.steps.map((step, index) => {
            const style = getAgentStyle(step.responsible_agent);
            const isActive = index === currentStepIndex;
            const isCompleted = completedSteps.has(step.step_number);
            const isPending = !isActive && !isCompleted;

            return (
              <div
                key={step.step_number}
                className={`
                  flex items-start gap-3 p-4 rounded-xl border transition-all duration-300
                  ${isActive ? 'border-sky-500 bg-sky-50 shadow-md' : ''}
                  ${isCompleted ? 'border-emerald-200 bg-emerald-50/50' : ''}
                  ${isPending ? 'border-slate-100 bg-white opacity-50' : ''}
                `}>
                {/* Step number indicator */}
                <div className={`
                  w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0
                  ${isCompleted ? 'bg-emerald-500 text-white' : ''}
                  ${isActive ? 'bg-sky-500 text-white animate-pulse' : ''}
                  ${isPending ? 'bg-slate-200 text-slate-500' : ''}
                `}>
                  {isCompleted ? <Check size={16} /> : step.step_number}
                </div>

                {/* Step content */}
                <div className="flex-1 min-w-0">
                  <h4 className="font-bold text-slate-800">{step.step_name}</h4>
                  <p className="text-sm text-slate-600 mt-1 line-clamp-2">{step.description}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs flex-wrap">
                    <span className={`${style.bg} ${style.text} px-2 py-0.5 rounded-full`}>
                      {style.icon} {style.label}
                    </span>
                    <span className="text-slate-500 flex items-center gap-1">
                      <Clock size={12} /> {step.estimated_duration}
                    </span>
                  </div>
                </div>

                {/* Status indicator */}
                {isActive && (
                  <div className="flex items-center gap-1 text-sky-600 text-xs font-semibold">
                    <Activity size={14} className="animate-pulse" />
                    In Progress
                  </div>
                )}
                {isCompleted && (
                  <div className="flex items-center gap-1 text-emerald-600 text-xs font-semibold">
                    <CheckCircle size={14} />
                    Complete
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-between">
          {executionState === 'not_started' && (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">
                Cancel
              </button>
              <button
                onClick={startExecution}
                className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 flex items-center gap-2 shadow-lg">
                <Play size={18} />
                Start Execution
              </button>
            </>
          )}
          {executionState === 'in_progress' && (
            <div className="w-full text-center py-2 text-slate-600 flex items-center justify-center gap-3">
              <div className="animate-spin h-5 w-5 border-2 border-indigo-500 border-t-transparent rounded-full" />
              Executing recovery plan...
            </div>
          )}
          {executionState === 'completed' && (
            <>
              <div className="flex items-center gap-2 text-emerald-600">
                <CheckCircle size={20} />
                <span className="font-semibold">Recovery Complete</span>
              </div>
              <button
                onClick={onExecutionComplete}
                className="px-6 py-2 bg-emerald-600 text-white rounded-lg font-semibold hover:bg-emerald-700 transition-colors">
                Complete & Close
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export const ArbitratorPanel: React.FC<ArbitratorPanelProps> = ({
  stage,
  liveAnalysis,
  solutions,
  onSelectSolution,
  onUnselectSolution,
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
            SkyMarshal Intelligence
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
          <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100 text-sm text-slate-700 leading-relaxed animate-fade-in-up">
            <div className="flex gap-2 items-start">
              <BrainCircuit
                size={16}
                className="text-indigo-500 flex-shrink-0 mt-0.5"
              />
              <div className="flex-1">
                <MarkdownContent content={liveAnalysis} />
              </div>
            </div>
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

            {solutions.map((sol, index) => {
              const isSelected = selectedSolutionId === sol.id;
              const isRecommended = sol.recommended;
              const isOtherSelected = selectedSolutionId && !isSelected;

              // Get key metrics for compact display
              const costDisplay = getCostSummary(sol.financial_impact);
              const paxDisplay = getPassengerSummary(sol.passenger_impact);
              const delayDisplay = getDelaySummary(sol.passenger_impact);

              return (
                <div
                  key={sol.id}
                  onClick={() => !selectedSolutionId && onSelectSolution(sol)}
                  role="button"
                  tabIndex={selectedSolutionId ? -1 : 0}
                  onKeyDown={(e) => {
                    if (!selectedSolutionId && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault();
                      onSelectSolution(sol);
                    }
                  }}
                  className={`
                    w-full text-left group relative p-4 rounded-xl transition-all duration-300
                    ${!selectedSolutionId ? 'cursor-pointer' : ''}
                    ${
                      isSelected
                        ? "bg-emerald-50 border-2 border-emerald-500 ring-4 ring-emerald-500/20 shadow-lg scale-[1.02]"
                        : isRecommended && !isOtherSelected
                          ? "bg-gradient-to-br from-indigo-50 to-white border-2 border-indigo-500 ring-2 ring-indigo-500/10 shadow-md"
                          : "bg-white border border-slate-200 hover:border-indigo-300 hover:bg-slate-50"
                    }
                    ${isOtherSelected ? "opacity-50 grayscale" : "opacity-100"}
                  `}>
                  {/* Header Row: Tags + Score Badge */}
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex gap-2 flex-wrap">
                      {isRecommended && (
                        <div
                          className={`
                          text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm
                          ${isSelected ? "bg-emerald-100 text-emerald-700" : "bg-indigo-600 text-white"}
                        `}>
                          <Star size={10} fill="currentColor" />
                          SkyMarshal Recommended
                        </div>
                      )}
                      {isSelected && (
                        <div className="bg-emerald-600 text-white text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm">
                          <Check size={10} />
                          Selected
                        </div>
                      )}
                      <span className="text-[10px] text-slate-400 font-mono">
                        Solution {index + 1} of {solutions.length}
                      </span>
                    </div>
                    {/* Composite Score Badge */}
                    <div className={`
                      flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold
                      ${sol.composite_score >= 80 ? 'bg-emerald-100 text-emerald-700' :
                        sol.composite_score >= 60 ? 'bg-amber-100 text-amber-700' :
                        'bg-red-100 text-red-700'}
                    `}>
                      {sol.composite_score}
                    </div>
                  </div>

                  {/* Title */}
                  <h4
                    className={`font-semibold text-base mb-1 transition-colors ${isSelected ? "text-emerald-900" : isRecommended ? "text-indigo-900" : "text-slate-800 group-hover:text-indigo-700"}`}>
                    {sol.title}
                  </h4>

                  {/* Description - Truncated */}
                  <p className="text-xs text-slate-600 leading-relaxed mb-3 line-clamp-2">
                    {sol.description}
                  </p>

                  {/* Key Metrics Row */}
                  <div className="flex items-center gap-3 mb-3 text-xs">
                    {costDisplay && (
                      <div className="flex items-center gap-1 px-2 py-1 bg-emerald-50 rounded-full">
                        <DollarSign size={12} className="text-emerald-600" />
                        <span className="text-emerald-700 font-medium">{costDisplay}</span>
                      </div>
                    )}
                    {paxDisplay && (
                      <div className="flex items-center gap-1 px-2 py-1 bg-blue-50 rounded-full">
                        <Users size={12} className="text-blue-600" />
                        <span className="text-blue-700 font-medium">{paxDisplay}</span>
                      </div>
                    )}
                    {delayDisplay && (
                      <div className="flex items-center gap-1 px-2 py-1 bg-purple-50 rounded-full">
                        <Clock size={12} className="text-purple-600" />
                        <span className="text-purple-700 font-medium">{delayDisplay}</span>
                      </div>
                    )}
                  </div>

                  {/* Compact Score Preview */}
                  <div className="flex items-center gap-2 mb-3">
                    <div className="flex-1 flex gap-1">
                      <div className="flex items-center gap-1" title="Safety Score">
                        <Shield size={10} className="text-slate-400" />
                        <div className="w-8 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${sol.safety_score >= 75 ? 'bg-emerald-500' : sol.safety_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                            style={{ width: `${sol.safety_score}%` }}
                          />
                        </div>
                      </div>
                      <div className="flex items-center gap-1" title="Passenger Score">
                        <Users size={10} className="text-slate-400" />
                        <div className="w-8 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${sol.passenger_score >= 75 ? 'bg-emerald-500' : sol.passenger_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                            style={{ width: `${sol.passenger_score}%` }}
                          />
                        </div>
                      </div>
                      <div className="flex items-center gap-1" title="Network Score">
                        <Network size={10} className="text-slate-400" />
                        <div className="w-8 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${sol.network_score >= 75 ? 'bg-emerald-500' : sol.network_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                            style={{ width: `${sol.network_score}%` }}
                          />
                        </div>
                      </div>
                      <div className="flex items-center gap-1" title="Cost Score">
                        <DollarSign size={10} className="text-slate-400" />
                        <div className="w-8 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${sol.cost_score >= 75 ? 'bg-emerald-500' : sol.cost_score >= 50 ? 'bg-amber-500' : 'bg-red-500'}`}
                            style={{ width: `${sol.cost_score}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Footer: Risk Badge + View More */}
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

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setExpandedSolution(sol);
                      }}
                      className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1 px-2 py-1 hover:bg-indigo-50 rounded transition-colors">
                      View Details
                      <TrendingUp size={12} />
                    </button>
                  </div>

                  {/* Hover check circle (only if not selected) */}
                  {!isSelected && !selectedSolutionId && (
                    <div className="absolute right-4 top-16 opacity-0 group-hover:opacity-100 transition-opacity">
                      <CheckCircle2 className="text-indigo-600" size={20} />
                    </div>
                  )}

                  {/* Change Decision button (only if selected) */}
                  {isSelected && onUnselectSolution && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onUnselectSolution();
                      }}
                      className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors border border-slate-200">
                      <RefreshCw size={14} />
                      Change Decision
                    </button>
                  )}
                </div>
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
