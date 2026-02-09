import React, { useState, useRef, useMemo } from "react";
import { AgentAvatar, AgentType } from "./AgentAvatar";
import { MarkdownContent } from "./MarkdownContent";
import { Solution, RecoveryPlanModal, RecoveryExecutionModal } from "./ArbitratorPanel";
import {
  PassengerImpact,
  FinancialImpact,
  NetworkImpact,
} from "../services/responseMapper";
import {
  ShieldCheck,
  TrendingUp,
  BrainCircuit,
  Database,
  Check,
  FileText,
  Activity,
  Download,
  X,
  ListChecks,
  Plane,
  Clock,
  AlertTriangle,
  Users,
  Shield,
  DollarSign,
  Network,
  CheckCircle,
} from "lucide-react";

export interface MessageData {
  id: string;
  agent: AgentType;
  safetyAnalysis?: string;
  businessImpact?: string;
  crossImpactAnalysis?: string;
  recommendation?: string;
  reasoning?: string;
  data_sources?: string[];
  status?: string;
  isCrossImpactRound?: boolean;
  isDecision?: boolean;
  solutionTitle?: string;
  selectedSolution?: Solution; // Full solution data for decision card
}

// Helper functions for formatting
function isPassengerImpact(impact: PassengerImpact | string): impact is PassengerImpact {
  return typeof impact === 'object' && impact !== null && 'total_passengers' in impact;
}

function isFinancialImpact(impact: FinancialImpact | string): impact is FinancialImpact {
  return typeof impact === 'object' && impact !== null && 'total_estimated_cost' in impact;
}

function isNetworkImpact(impact: NetworkImpact | string): impact is NetworkImpact {
  return typeof impact === 'object' && impact !== null && 'downstream_flights_affected' in impact;
}

// Alternative interfaces for solution_2.json format
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
    passenger_reprotection?: number;
    compensation_eu261?: number;
    hotel_accommodations?: number;
    compensation?: number;
    [key: string]: number | undefined;
  };
}

interface AlternativeNetworkImpact {
  downstream_flights: number;
  connection_misses: number;
}

// Type guards for alternative formats
function isAlternativePassengerImpact(impact: unknown): impact is AlternativePassengerImpact {
  return typeof impact === 'object' && impact !== null && 'affected_count' in impact;
}

function isAlternativeFinancialImpact(impact: unknown): impact is AlternativeFinancialImpact {
  return typeof impact === 'object' && impact !== null && 'total_cost' in impact;
}

function isAlternativeNetworkImpact(impact: unknown): impact is AlternativeNetworkImpact {
  return typeof impact === 'object' && impact !== null && 'downstream_flights' in impact;
}

function formatCurrency(amount: number, currency: string = 'USD'): string {
  if (amount >= 1000000) {
    return `$${(amount / 1000000).toFixed(1)}M ${currency}`;
  } else if (amount >= 1000) {
    return `$${(amount / 1000).toFixed(0)}K ${currency}`;
  }
  return `$${amount} ${currency}`;
}

// Score bar component for compact display
const CompactScoreBar: React.FC<{ label: string; value: number; icon: React.ReactNode }> = ({ label, value, icon }) => {
  const getColor = (score: number) => {
    if (score >= 75) return 'bg-emerald-500';
    if (score >= 50) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-slate-400">{icon}</span>
      <span className="text-xs text-slate-600 min-w-[60px]">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${getColor(value)}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs font-mono text-slate-600 min-w-[24px] text-right">{value}</span>
    </div>
  );
};

interface AgentMessageProps {
  message: MessageData;
  isNew?: boolean;
  onRecoveryComplete?: (solution: Solution) => void; // Callback when recovery is executed
}

export const AgentMessage: React.FC<AgentMessageProps> = ({
  message,
  isNew = false,
  onRecoveryComplete,
}) => {
  const [activeModal, setActiveModal] = useState<"recovery" | "report" | "execution" | null>(
    null,
  );
  const [recoveryExecuted, setRecoveryExecuted] = useState(false);

  // --- Specialized Decision Card Render ---
  if (message.isDecision) {
    const solution = message.selectedSolution;

    // Get metrics from solution if available
    const costDisplay = solution && isFinancialImpact(solution.financial_impact)
      ? formatCurrency(solution.financial_impact.total_estimated_cost, solution.financial_impact.currency)
      : '';
    const paxDisplay = solution && isPassengerImpact(solution.passenger_impact)
      ? `${solution.passenger_impact.total_passengers} pax`
      : '';
    const delayDisplay = solution && isPassengerImpact(solution.passenger_impact)
      ? `${solution.passenger_impact.delay_minutes} min delay`
      : '';

    return (
      <>
        <div
          className={`w-full max-w-4xl mx-auto mb-8 ${isNew ? "animate-fade-in-up" : "opacity-100"}`}>
          <div className="relative overflow-hidden rounded-2xl border-l-4 border-l-emerald-600 bg-gradient-to-br from-emerald-50/90 via-white to-indigo-50/90 shadow-xl p-6 md:p-8">
            {/* Background Decoration */}
            <div className="absolute top-0 right-0 p-8 opacity-5">
              <CheckCircle size={120} />
            </div>

            {/* Header Badge */}
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 px-3 py-1 bg-emerald-600 text-white rounded-full text-[10px] font-bold uppercase tracking-widest shadow-md">
                <CheckCircle size={12} />
                Decision Selected
              </div>
              <div className="flex items-center gap-2 text-emerald-700/60 text-xs font-semibold">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                Live in OCC
              </div>
            </div>

            {/* Content */}
            <div className="relative z-10">
              {/* Title Row with Score */}
              <div className="flex items-start justify-between mb-4">
                <h2 className="text-2xl font-bold text-slate-800">
                  {message.solutionTitle || solution?.title}
                </h2>
                {solution && (
                  <div className={`
                    flex items-center justify-center w-14 h-14 rounded-full text-lg font-bold
                    ${solution.composite_score >= 80 ? 'bg-emerald-100 text-emerald-700' :
                      solution.composite_score >= 60 ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'}
                  `}>
                    {solution.composite_score}
                  </div>
                )}
              </div>

              {/* Key Metrics Row */}
              {solution && (
                <div className="flex items-center gap-4 mb-4 flex-wrap">
                  {costDisplay && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 rounded-full">
                      <DollarSign size={14} className="text-emerald-600" />
                      <span className="text-emerald-700 font-semibold text-sm">{costDisplay}</span>
                    </div>
                  )}
                  {paxDisplay && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 rounded-full">
                      <Users size={14} className="text-blue-600" />
                      <span className="text-blue-700 font-semibold text-sm">{paxDisplay}</span>
                    </div>
                  )}
                  {delayDisplay && (
                    <div className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-50 rounded-full">
                      <Clock size={14} className="text-purple-600" />
                      <span className="text-purple-700 font-semibold text-sm">{delayDisplay}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Score Bars */}
              {solution && (
                <div className="bg-white/80 border border-slate-100 rounded-xl p-4 mb-4 space-y-2">
                  <CompactScoreBar label="Safety" value={solution.safety_score} icon={<Shield size={12} />} />
                  <CompactScoreBar label="Passenger" value={solution.passenger_score} icon={<Users size={12} />} />
                  <CompactScoreBar label="Network" value={solution.network_score} icon={<Network size={12} />} />
                  <CompactScoreBar label="Cost" value={solution.cost_score} icon={<DollarSign size={12} />} />
                </div>
              )}

              {/* Key Actions */}
              {solution && solution.recommendations && solution.recommendations.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Key Actions</h4>
                  <div className="space-y-1">
                    {solution.recommendations.slice(0, 3).map((rec, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm text-slate-700">
                        <Check size={14} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                        <span>{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Impact Summary */}
              {solution && (
                <div className="mb-6 p-3 bg-slate-50 rounded-lg">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Impact Summary</h4>
                  <ul className="space-y-1 text-sm text-slate-600">
                    {isPassengerImpact(solution.passenger_impact) && (
                      <li className="flex items-center gap-2">
                        <span className="text-blue-500">•</span>
                        {solution.passenger_impact.total_passengers} passengers, {solution.passenger_impact.connecting_passengers} connecting, {solution.passenger_impact.missed_connections} missed connections
                      </li>
                    )}
                    {isNetworkImpact(solution.network_impact) && (
                      <>
                        <li className="flex items-center gap-2">
                          <span className={solution.network_impact.EY17_connection_protected ? 'text-emerald-500' : 'text-red-500'}>•</span>
                          EY17 connection {solution.network_impact.EY17_connection_protected ? 'protected' : 'at risk'}
                        </li>
                        <li className="flex items-center gap-2">
                          <span className="text-purple-500">•</span>
                          {solution.network_impact.downstream_flights_affected} downstream flights affected
                        </li>
                      </>
                    )}
                  </ul>
                </div>
              )}

              {/* Fallback description if no solution data */}
              {!solution && message.crossImpactAnalysis && (
                <p className="text-slate-600 leading-relaxed mb-6 border-l-2 border-emerald-200 pl-4">
                  {message.crossImpactAnalysis}
                </p>
              )}

              {/* Action Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button
                  onClick={() => setActiveModal("recovery")}
                  className="group flex items-center justify-between p-4 bg-white border border-slate-200 rounded-xl hover:border-indigo-400 hover:shadow-lg transition-all duration-300">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                      <ListChecks size={20} />
                    </div>
                    <div className="text-left">
                      <div className="text-sm font-bold text-slate-800">
                        View Recovery Plan
                      </div>
                      <div className="text-xs text-slate-500">
                        {solution?.recovery_plan ? `${solution.recovery_plan.total_steps} steps • ${solution.recovery_plan.estimated_total_duration}` : 'View automated workflows'}
                      </div>
                    </div>
                  </div>
                  <Activity
                    size={16}
                    className="text-slate-300 group-hover:text-indigo-500"
                  />
                </button>

                <button
                  onClick={() => recoveryExecuted && setActiveModal("report")}
                  disabled={!recoveryExecuted}
                  title={!recoveryExecuted ? "Execute recovery plan first to view detailed report" : ""}
                  className={`group flex items-center justify-between p-4 bg-white border rounded-xl transition-all duration-300
                    ${recoveryExecuted
                      ? 'border-slate-200 hover:border-emerald-400 hover:shadow-lg cursor-pointer'
                      : 'border-slate-100 opacity-50 cursor-not-allowed'
                    }`}>
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg transition-colors
                      ${recoveryExecuted
                        ? 'bg-emerald-50 text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white'
                        : 'bg-slate-100 text-slate-400'
                      }`}>
                      <FileText size={20} />
                    </div>
                    <div className="text-left">
                      <div className={`text-sm font-bold ${recoveryExecuted ? 'text-slate-800' : 'text-slate-400'}`}>
                        View Detailed Report
                      </div>
                      <div className="text-xs text-slate-500">
                        {recoveryExecuted ? 'Impact analysis & learnings' : 'Execute recovery to unlock'}
                      </div>
                    </div>
                  </div>
                  <Download
                    size={16}
                    className={recoveryExecuted ? "text-slate-300 group-hover:text-emerald-500" : "text-slate-200"}
                  />
                </button>
              </div>

              {/* Footer Sync Indicator */}
              <div className="mt-6 pt-4 border-t border-emerald-100 flex items-center gap-2 text-slate-500 text-xs font-medium">
                <div className="flex items-center gap-1.5 text-emerald-600">
                  <Database size={14} />
                  <Check size={14} />
                </div>
                Strategy synced to SkyMarshal Knowledge Base for future reinforcement learning.
              </div>
            </div>
          </div>
        </div>

        {/* --- Modals --- */}
        {activeModal === "recovery" && solution && (
          <RecoveryPlanModal
            solution={solution}
            onClose={() => setActiveModal(null)}
            onExecuteRecovery={() => setActiveModal("execution")}
            recoveryExecuted={recoveryExecuted}
          />
        )}
        {activeModal === "recovery" && !solution && (
          <RecoveryModal
            onClose={() => setActiveModal(null)}
            title={message.solutionTitle || "Recovery Protocol"}
          />
        )}
        {activeModal === "execution" && solution && (
          <RecoveryExecutionModal
            solution={solution}
            onClose={() => setActiveModal("recovery")}
            onExecutionComplete={() => {
              setRecoveryExecuted(true);
              setActiveModal(null);
              // Trigger S3 save callback if provided
              if (onRecoveryComplete && solution) {
                onRecoveryComplete(solution);
              }
            }}
          />
        )}
        {activeModal === "report" && recoveryExecuted && solution && (
          <ReportModal
            onClose={() => setActiveModal(null)}
            solution={solution}
            executionTimestamp={new Date()}
          />
        )}
      </>
    );
  }

  // --- Standard Message Render ---
  return (
    <div
      className={`flex gap-3 w-full max-w-4xl mx-auto mb-4 ${isNew ? "animate-fade-in-up" : "opacity-100"}`}>
      <div className="flex-shrink-0 mt-1">
        <AgentAvatar type={message.agent} size="sm" status="idle" />
      </div>

      <div className="flex-1 bg-white/80 backdrop-blur-sm border border-slate-200 shadow-sm rounded-2xl rounded-tl-none p-4 overflow-hidden hover:shadow-md transition-all duration-300">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-baseline gap-2">
            <h4 className="font-bold text-slate-800 text-sm">
              {message.agent.replace("_", " ")}
            </h4>
            <span className="text-[10px] text-slate-400 uppercase tracking-wide font-medium">
              Domain Agent
            </span>
          </div>

          <div className="flex items-center gap-2">
            {message.status === "error" && (
              <span className="px-2 py-0.5 rounded-full bg-red-50 text-red-600 text-[10px] font-bold uppercase tracking-wider border border-red-100 flex items-center gap-1">
                <AlertTriangle size={10} />
                Error
              </span>
            )}
            {message.isCrossImpactRound && (
              <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600 text-[10px] font-bold uppercase tracking-wider border border-indigo-100">
                Negotiation
              </span>
            )}
          </div>
        </div>

        {/* NEW: Display recommendation field with markdown rendering */}
        {message.recommendation && (
          <div className="group p-3 rounded-lg bg-emerald-50/50 border border-emerald-100/50 hover:bg-emerald-50 transition-colors mb-3">
            <div className="flex gap-2 items-center mb-2">
              <Check
                size={16}
                className="text-emerald-500 flex-shrink-0 opacity-70 group-hover:opacity-100 transition-opacity"
              />
              <span className="font-semibold text-emerald-700 text-xs uppercase tracking-wide opacity-80">
                Initial Analysis
              </span>
            </div>
            <div className="text-slate-700">
              <MarkdownContent content={message.recommendation} />
            </div>
          </div>
        )}


        {/* NEW: Display data_sources field */}
        {message.data_sources && message.data_sources.length > 0 && (
          <div className="group flex gap-3 items-start p-3 rounded-lg bg-slate-50/50 border border-slate-100/50 hover:bg-slate-50 transition-colors mb-3">
            <Database
              size={16}
              className="text-slate-500 mt-0.5 flex-shrink-0 opacity-70 group-hover:opacity-100 transition-opacity"
            />
            <div className="text-sm text-slate-700 leading-relaxed">
              <span className="font-semibold text-slate-700 block text-xs mb-1 uppercase tracking-wide opacity-80">
                Data Sources
              </span>
              <ul className="list-disc list-inside space-y-1 text-xs text-slate-600">
                {message.data_sources.map((source, idx) => (
                  <li key={idx} className="break-words">
                    {source}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* LEGACY: Display old format fields for backward compatibility */}
        {!message.isCrossImpactRound && !message.recommendation && (
          <div className="space-y-3">
            {message.safetyAnalysis && (
              <div className="group flex gap-3 items-start p-3 rounded-lg bg-red-50/50 border border-red-100/50 hover:bg-red-50 transition-colors">
                <ShieldCheck
                  size={16}
                  className="text-red-500 mt-0.5 flex-shrink-0 opacity-70 group-hover:opacity-100 transition-opacity"
                />
                <div className="text-sm text-slate-700 leading-relaxed">
                  <span className="font-semibold text-red-700 block text-xs mb-0.5 uppercase tracking-wide opacity-80">
                    Safety Constraint
                  </span>
                  {message.safetyAnalysis}
                </div>
              </div>
            )}

            {message.businessImpact && (
              <div className="group flex gap-3 items-start p-3 rounded-lg bg-blue-50/50 border border-blue-100/50 hover:bg-blue-50 transition-colors">
                <TrendingUp
                  size={16}
                  className="text-blue-500 mt-0.5 flex-shrink-0 opacity-70 group-hover:opacity-100 transition-opacity"
                />
                <div className="text-sm text-slate-700 leading-relaxed">
                  <span className="font-semibold text-blue-700 block text-xs mb-0.5 uppercase tracking-wide opacity-80">
                    Business Impact
                  </span>
                  {message.businessImpact}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Display cross-impact analysis if present with markdown rendering */}
        {message.isCrossImpactRound && message.crossImpactAnalysis && (
          <div className="text-slate-700 pl-3 border-l-2 border-indigo-200">
            <MarkdownContent content={message.crossImpactAnalysis} />
          </div>
        )}
      </div>
    </div>
  );
};

// --- Sub-Components for Modals ---

const RecoveryModal: React.FC<{ onClose: () => void; title: string }> = ({
  onClose,
  title,
}) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
    <div className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      {/* Modal Header */}
      <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold text-slate-800">
            Automated Recovery Workflow
          </h3>
          <p className="text-xs text-slate-500">Executing strategy: {title}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 hover:bg-slate-200 rounded-full text-slate-500 transition-colors">
          <X size={20} />
        </button>
      </div>

      {/* Modal Body */}
      <div className="p-6 overflow-y-auto bg-slate-50/30 space-y-4">
        <RecoveryItem
          agent="Crew Compliance"
          time="00:01s"
          task="Reserve Crew Callout (CMDR + FO)"
          status="completed"
          details="Notification delivered via AIMS. Acknowledgement received from Cpt. James Miller."
        />
        <RecoveryItem
          agent="Guest Services"
          time="00:05s"
          task="Premium Passenger Interline"
          status="completed"
          details="6 VIPs rebooked on BA109 (LHR-AUH). E-tickets dispatched to mobile app."
        />
        <RecoveryItem
          agent="Maintenance"
          time="00:12s"
          task="Parts Logistics & Work Order"
          status="processing"
          details="Yellow Pump (P/N 5822-11) released from stores. Technicians en route to Gate E4."
        />
        <RecoveryItem
          agent="Network"
          time="00:15s"
          task="Downstream Schedule Adjustment"
          status="processing"
          details="Holding EY454 (SYD) for 45 mins. Slot revision requested from ATC."
        />
        <RecoveryItem
          agent="Finance"
          time="00:30s"
          task="Cost Center Allocation"
          status="pending"
          details="Approving OT for engineering and interline costs pending final invoice."
        />
      </div>

      {/* Modal Footer */}
      <div className="px-6 py-4 border-t border-slate-100 bg-white flex justify-end gap-3">
        <button className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 rounded-lg">
          Close
        </button>
        <button className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg flex items-center gap-2 shadow-lg shadow-indigo-200">
          <Download size={16} />
          Export Log
        </button>
      </div>
    </div>
  </div>
);

const RecoveryItem: React.FC<{
  agent: string;
  time: string;
  task: string;
  status: "completed" | "processing" | "pending";
  details: string;
}> = ({ agent, time, task, status, details }) => (
  <div className="flex gap-4 p-4 bg-white border border-slate-100 rounded-xl shadow-sm">
    <div className="flex flex-col items-center gap-1 min-w-[60px]">
      <span className="text-[10px] font-mono text-slate-400">{time}</span>
      <div
        className={`h-8 w-8 rounded-full flex items-center justify-center ${
          status === "completed"
            ? "bg-emerald-100 text-emerald-600"
            : status === "processing"
              ? "bg-amber-100 text-amber-600 animate-pulse"
              : "bg-slate-100 text-slate-400"
        }`}>
        {status === "completed" ? <Check size={16} /> : <Activity size={16} />}
      </div>
    </div>
    <div className="flex-1">
      <div className="flex justify-between items-start">
        <h4 className="text-sm font-bold text-slate-800">{task}</h4>
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-50 px-2 py-0.5 rounded">
          {agent}
        </span>
      </div>
      <p className="text-xs text-slate-600 mt-1">{details}</p>
    </div>
  </div>
);

const ReportModal: React.FC<{
  onClose: () => void;
  solution: Solution;
  executionTimestamp?: Date;
}> = ({ onClose, solution, executionTimestamp }) => {
  const reportRef = useRef<HTMLDivElement>(null);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);

  // Generate unique report ID
  const reportId = useMemo(() => {
    const date = new Date();
    return `RPT-${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}-${String(Math.floor(Math.random() * 1000)).padStart(3, '0')}`;
  }, []);

  // Format currency helper
  const formatCost = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  // PDF Download handler
  const handleDownloadPdf = async () => {
    if (!reportRef.current) return;
    setIsGeneratingPdf(true);

    try {
      const { default: jsPDF } = await import('jspdf');
      const { default: html2canvas } = await import('html2canvas');

      const canvas = await html2canvas(reportRef.current, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
      });

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
      });

      const imgWidth = 210; // A4 width in mm
      const pageHeight = 297; // A4 height in mm
      const imgHeight = (canvas.height * imgWidth) / canvas.width;
      let heightLeft = imgHeight;
      let position = 0;

      // Add first page
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pageHeight;

      // Add additional pages if needed
      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;
      }

      pdf.save(`SkyMarshal-Report-${reportId}.pdf`);
    } catch (error) {
      console.error('PDF generation failed:', error);
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  const recoveryPlan = solution.recovery_plan;
  const passengerImpact = isPassengerImpact(solution.passenger_impact) ? solution.passenger_impact : null;
  const altPassengerImpact = isAlternativePassengerImpact(solution.passenger_impact) ? solution.passenger_impact : null;
  const financialImpact = isFinancialImpact(solution.financial_impact) ? solution.financial_impact : null;
  const altFinancialImpact = isAlternativeFinancialImpact(solution.financial_impact) ? solution.financial_impact : null;
  const networkImpact = isNetworkImpact(solution.network_impact) ? solution.network_impact : null;
  const altNetworkImpact = isAlternativeNetworkImpact(solution.network_impact) ? solution.network_impact : null;

  // Score bar for report
  const ReportScoreBar: React.FC<{ label: string; value: number; color: string }> = ({ label, value, color }) => (
    <div className="flex items-center gap-3 py-2">
      <span className="text-sm text-slate-600 min-w-[80px]">{label}</span>
      <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="text-sm font-bold text-slate-700 min-w-[40px] text-right">{value}%</span>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-5xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[95vh]">
        {/* Header */}
        <div className="px-8 py-5 bg-gradient-to-r from-slate-900 to-indigo-900 text-white flex justify-between items-center flex-shrink-0">
          <div>
            <div className="flex items-center gap-2 mb-1 opacity-80">
              <BrainCircuit size={16} />
              <span className="text-xs font-mono tracking-widest uppercase">
                SkyMarshal Recovery Report
              </span>
            </div>
            <h2 className="text-xl font-bold">{solution.title}</h2>
            <p className="text-sm text-slate-300">Report ID: {reportId}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full">
            <X size={24} />
          </button>
        </div>

        {/* Scrollable Report Content */}
        <div className="flex-1 overflow-y-auto">
          <div ref={reportRef} className="p-8 bg-white">
            {/* Report Header for PDF */}
            <div className="mb-8 pb-6 border-b-2 border-slate-200">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h1 className="text-2xl font-bold text-slate-900">SKYMARSHAL DISRUPTION RECOVERY REPORT</h1>
                  <p className="text-sm text-slate-500 mt-1">
                    Date: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })} | Report ID: {reportId}
                  </p>
                </div>
                <div className="text-right">
                  <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold
                    ${solution.composite_score >= 80 ? 'bg-emerald-100 text-emerald-700' :
                      solution.composite_score >= 60 ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'}`}>
                    <CheckCircle size={16} />
                    RECOVERY COMPLETE
                  </div>
                </div>
              </div>
            </div>

            {/* Section 1: Executive Summary */}
            <section className="mb-8">
              <h3 className="flex items-center gap-2 text-lg font-bold text-slate-800 uppercase tracking-wider mb-4 pb-2 border-b border-slate-200">
                <Users size={18} className="text-indigo-500" />
                1. Executive Summary
              </h3>
              <div className="bg-slate-50 rounded-xl p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div className="text-center p-3 bg-white rounded-lg border border-slate-100">
                    <div className="text-2xl font-bold text-indigo-600">{solution.composite_score}</div>
                    <div className="text-xs text-slate-500 uppercase">Composite Score</div>
                  </div>
                  {passengerImpact && (
                    <div className="text-center p-3 bg-white rounded-lg border border-slate-100">
                      <div className="text-2xl font-bold text-blue-600">{passengerImpact.total_passengers}</div>
                      <div className="text-xs text-slate-500 uppercase">Passengers</div>
                    </div>
                  )}
                  {financialImpact && (
                    <div className="text-center p-3 bg-white rounded-lg border border-slate-100">
                      <div className="text-2xl font-bold text-emerald-600">{formatCost(financialImpact.total_estimated_cost, financialImpact.currency)}</div>
                      <div className="text-xs text-slate-500 uppercase">Total Cost</div>
                    </div>
                  )}
                  {recoveryPlan && (
                    <div className="text-center p-3 bg-white rounded-lg border border-slate-100">
                      <div className="text-2xl font-bold text-purple-600">{recoveryPlan.total_steps}</div>
                      <div className="text-xs text-slate-500 uppercase">Recovery Steps</div>
                    </div>
                  )}
                </div>
                <p className="text-sm text-slate-600 leading-relaxed">
                  <strong>Decision:</strong> {solution.title}
                  {solution.description && <span className="block mt-2">{solution.description}</span>}
                </p>
                {executionTimestamp && (
                  <p className="text-xs text-slate-500 mt-3">
                    Execution Time: {executionTimestamp.toISOString()}
                  </p>
                )}
              </div>
            </section>

            {/* Section 2: Score Breakdown */}
            <section className="mb-8">
              <h3 className="flex items-center gap-2 text-lg font-bold text-slate-800 uppercase tracking-wider mb-4 pb-2 border-b border-slate-200">
                <TrendingUp size={18} className="text-emerald-500" />
                2. Score Breakdown
              </h3>
              <div className="bg-white border border-slate-200 rounded-xl p-6">
                <ReportScoreBar label="Safety" value={solution.safety_score} color="bg-red-500" />
                <ReportScoreBar label="Passenger" value={solution.passenger_score} color="bg-blue-500" />
                <ReportScoreBar label="Network" value={solution.network_score} color="bg-purple-500" />
                <ReportScoreBar label="Cost" value={solution.cost_score} color="bg-emerald-500" />
              </div>
            </section>

            {/* Section 3: Impact Analysis */}
            <section className="mb-8">
              <h3 className="flex items-center gap-2 text-lg font-bold text-slate-800 uppercase tracking-wider mb-4 pb-2 border-b border-slate-200">
                <Activity size={18} className="text-blue-500" />
                3. Impact Analysis
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Passenger Impact */}
                <div className="bg-blue-50 border border-blue-100 rounded-xl p-5">
                  <h4 className="flex items-center gap-2 text-sm font-bold text-blue-800 uppercase mb-4">
                    <Users size={16} />
                    Passenger Impact
                  </h4>
                  {passengerImpact ? (
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-blue-700">Total Passengers</span>
                        <span className="font-bold">{passengerImpact.total_passengers}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-blue-700">Connecting</span>
                        <span className="font-bold">{passengerImpact.connecting_passengers}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-blue-700">Delay (mins)</span>
                        <span className="font-bold">{passengerImpact.delay_minutes}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-blue-700">Missed Connections</span>
                        <span className="font-bold text-red-600">{passengerImpact.missed_connections}</span>
                      </div>
                    </div>
                  ) : altPassengerImpact ? (
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-blue-700">Affected Passengers</span>
                        <span className="font-bold">{altPassengerImpact.affected_count}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-blue-700">Delay</span>
                        <span className="font-bold">{altPassengerImpact.delay_hours}h</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-blue-700">Cancellation</span>
                        <span className={`font-bold ${altPassengerImpact.cancellation_flag ? 'text-red-600' : 'text-emerald-600'}`}>
                          {altPassengerImpact.cancellation_flag ? 'Yes' : 'No'}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-blue-600">No passenger impact data available</p>
                  )}
                </div>

                {/* Financial Impact */}
                <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-5">
                  <h4 className="flex items-center gap-2 text-sm font-bold text-emerald-800 uppercase mb-4">
                    <DollarSign size={16} />
                    Financial Impact
                  </h4>
                  {financialImpact ? (
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-emerald-700">Aircraft Swap</span>
                        <span className="font-bold">{formatCost(financialImpact.aircraft_swap_cost, financialImpact.currency)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-emerald-700">Crew Costs</span>
                        <span className="font-bold">{formatCost(financialImpact.crew_costs, financialImpact.currency)}</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-emerald-700">Compensation</span>
                        <span className="font-bold">{formatCost(financialImpact.passenger_compensation, financialImpact.currency)}</span>
                      </div>
                      <div className="flex justify-between text-sm pt-2 border-t border-emerald-200">
                        <span className="text-emerald-800 font-bold">Total</span>
                        <span className="font-bold text-emerald-900">{formatCost(financialImpact.total_estimated_cost, financialImpact.currency)}</span>
                      </div>
                    </div>
                  ) : altFinancialImpact ? (
                    <div className="space-y-3">
                      {Object.entries(altFinancialImpact.breakdown).map(([key, value]) => (
                        <div key={key} className="flex justify-between text-sm">
                          <span className="text-emerald-700">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                          <span className="font-bold">{formatCost(value || 0)}</span>
                        </div>
                      ))}
                      <div className="flex justify-between text-sm pt-2 border-t border-emerald-200">
                        <span className="text-emerald-800 font-bold">Total</span>
                        <span className="font-bold text-emerald-900">{formatCost(altFinancialImpact.total_cost)}</span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-emerald-600">No financial impact data available</p>
                  )}
                </div>

                {/* Network Impact */}
                <div className="bg-purple-50 border border-purple-100 rounded-xl p-5">
                  <h4 className="flex items-center gap-2 text-sm font-bold text-purple-800 uppercase mb-4">
                    <Network size={16} />
                    Network Impact
                  </h4>
                  {networkImpact ? (
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-purple-700">Downstream Flights</span>
                        <span className="font-bold">{networkImpact.downstream_flights_affected}</span>
                      </div>
                      <div className="flex justify-between text-sm items-center">
                        <span className="text-purple-700">Rotation Preserved</span>
                        <span className={`font-bold ${networkImpact.rotation_preserved ? 'text-emerald-600' : 'text-red-600'}`}>
                          {networkImpact.rotation_preserved ? 'Yes' : 'No'}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm items-center">
                        <span className="text-purple-700">EY17 Protected</span>
                        <span className={`font-bold ${networkImpact.EY17_connection_protected ? 'text-emerald-600' : 'text-red-600'}`}>
                          {networkImpact.EY17_connection_protected ? 'Yes' : 'No'}
                        </span>
                      </div>
                    </div>
                  ) : altNetworkImpact ? (
                    <div className="space-y-3">
                      <div className="flex justify-between text-sm">
                        <span className="text-purple-700">Downstream Flights</span>
                        <span className="font-bold">{altNetworkImpact.downstream_flights}</span>
                      </div>
                      <div className="flex justify-between text-sm items-center">
                        <span className="text-purple-700">Connection Misses</span>
                        <span className={`font-bold ${altNetworkImpact.connection_misses === 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                          {altNetworkImpact.connection_misses}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-purple-600">No network impact data available</p>
                  )}
                </div>
              </div>
            </section>

            {/* Section 4: Recovery Plan Execution */}
            {recoveryPlan && recoveryPlan.steps && recoveryPlan.steps.length > 0 && (
              <section className="mb-8">
                <h3 className="flex items-center gap-2 text-lg font-bold text-slate-800 uppercase tracking-wider mb-4 pb-2 border-b border-slate-200">
                  <ListChecks size={18} className="text-indigo-500" />
                  4. Recovery Plan Execution
                </h3>
                <div className="bg-slate-50 rounded-xl p-6">
                  <div className="flex items-center gap-4 mb-4 text-sm text-slate-600">
                    <span><strong>Total Steps:</strong> {recoveryPlan.total_steps}</span>
                    <span><strong>Duration:</strong> {recoveryPlan.estimated_total_duration}</span>
                    <span className="px-2 py-1 bg-emerald-100 text-emerald-700 rounded-full text-xs font-bold">COMPLETE</span>
                  </div>
                  <div className="space-y-3">
                    {recoveryPlan.steps.map((step, idx) => (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-white border border-slate-100 rounded-lg">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
                          <Check size={16} />
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-800 text-sm">Step {step.step_number}: {step.step_name}</span>
                            <span className="text-xs text-slate-500">{step.estimated_duration}</span>
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded">{step.responsible_agent}</span>
                            {step.success_criteria && (
                              <span className="text-xs text-slate-500">{step.success_criteria}</span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}

            {/* Section 5: Contingency Plans */}
            {recoveryPlan && recoveryPlan.contingency_plans && recoveryPlan.contingency_plans.length > 0 && (
              <section className="mb-8">
                <h3 className="flex items-center gap-2 text-lg font-bold text-slate-800 uppercase tracking-wider mb-4 pb-2 border-b border-slate-200">
                  <AlertTriangle size={18} className="text-amber-500" />
                  5. Contingency Plans
                </h3>
                <div className="space-y-3">
                  {recoveryPlan.contingency_plans.map((plan, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-100 rounded-lg">
                      <div className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-200 text-amber-700 flex items-center justify-center text-xs font-bold">
                        {idx + 1}
                      </div>
                      <div>
                        <div className="text-sm font-bold text-amber-800">If: {plan.trigger}</div>
                        <div className="text-sm text-amber-700 mt-1">Then: {plan.action}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Section 6: Pros, Cons & Risks */}
            <section className="mb-8">
              <h3 className="flex items-center gap-2 text-lg font-bold text-slate-800 uppercase tracking-wider mb-4 pb-2 border-b border-slate-200">
                <Shield size={18} className="text-slate-500" />
                6. Analysis Summary
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Pros */}
                {solution.pros && solution.pros.length > 0 && (
                  <div className="bg-emerald-50 border border-emerald-100 rounded-xl p-5">
                    <h4 className="text-sm font-bold text-emerald-800 uppercase mb-3">Pros</h4>
                    <ul className="space-y-2">
                      {solution.pros.map((pro, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-emerald-700">
                          <Check size={14} className="flex-shrink-0 mt-0.5" />
                          <span>{pro}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Cons */}
                {solution.cons && solution.cons.length > 0 && (
                  <div className="bg-red-50 border border-red-100 rounded-xl p-5">
                    <h4 className="text-sm font-bold text-red-800 uppercase mb-3">Cons</h4>
                    <ul className="space-y-2">
                      {solution.cons.map((con, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-red-700">
                          <X size={14} className="flex-shrink-0 mt-0.5" />
                          <span>{con}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Risks */}
                {solution.risks && solution.risks.length > 0 && (
                  <div className="bg-amber-50 border border-amber-100 rounded-xl p-5">
                    <h4 className="text-sm font-bold text-amber-800 uppercase mb-3">Risks</h4>
                    <ul className="space-y-2">
                      {solution.risks.map((risk, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-amber-700">
                          <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                          <span>{risk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>

            {/* Section 7: Recommendations */}
            {solution.recommendations && solution.recommendations.length > 0 && (
              <section className="mb-8">
                <h3 className="flex items-center gap-2 text-lg font-bold text-slate-800 uppercase tracking-wider mb-4 pb-2 border-b border-slate-200">
                  <BrainCircuit size={18} className="text-purple-500" />
                  7. Recommendations
                </h3>
                <div className="bg-purple-50 border border-purple-100 rounded-xl p-6">
                  <ul className="space-y-3">
                    {solution.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex items-start gap-3 text-sm text-purple-800">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-200 text-purple-700 flex items-center justify-center text-xs font-bold">
                          {idx + 1}
                        </span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </section>
            )}

            {/* Report Footer */}
            <div className="mt-8 pt-6 border-t-2 border-slate-200 text-center text-xs text-slate-500">
              <p className="font-bold">Generated by SkyMarshal AI | Confidential | For Internal Use Only</p>
              <p className="mt-1">Report ID: {reportId} | Generated: {new Date().toISOString()}</p>
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="px-8 py-4 border-t border-slate-200 bg-slate-50 flex justify-end gap-3 flex-shrink-0">
          <button
            onClick={onClose}
            className="px-6 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">
            Close Report
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={isGeneratingPdf}
            className="px-6 py-2.5 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg flex items-center gap-2 shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed">
            {isGeneratingPdf ? (
              <>
                <Activity size={18} className="animate-spin" />
                Generating...
              </>
            ) : (
              <>
                <Download size={18} />
                Download PDF
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
