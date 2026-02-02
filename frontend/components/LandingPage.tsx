import React from "react";
import { InputBar } from "./InputBar";
import {
  Wind,
  ShieldAlert,
  BrainCircuit,
  Activity,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

interface LandingPageProps {
  onProcess: (text: string) => void;
  loading?: boolean;
  progress?: string;
  error?: string | null;
  onRetry?: () => void;
}

const LandingPage: React.FC<LandingPageProps> = ({
  onProcess,
  loading,
  progress,
  error,
  onRetry,
}) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 pb-20">
      {/* Header / Branding */}
      <div className="text-center mb-12 space-y-4 max-w-2xl mx-auto">
        <div className="flex items-center justify-center gap-2 mb-6">
          <div className="p-3 bg-gradient-to-br from-sky-500 to-indigo-600 rounded-2xl shadow-lg shadow-sky-500/30">
            <Wind className="text-white" size={32} />
          </div>
        </div>

        <h1 className="text-5xl md:text-7xl font-semibold tracking-tight text-slate-900 drop-shadow-sm">
          Sky<span className="gradient-text">Marshal</span>
        </h1>

        <p className="text-lg md:text-xl text-slate-500 font-light max-w-lg mx-auto leading-relaxed">
          Agentic AI for Disruption & Recovery Management.
          <br className="hidden md:block" />
          <span className="text-sm font-medium text-slate-400 uppercase tracking-widest mt-2 block">
            Orchestration Control Plane
          </span>
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 max-w-2xl w-full mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start gap-3">
            <AlertCircle
              className="text-red-500 flex-shrink-0 mt-0.5"
              size={20}
            />
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-red-800 mb-1">Error</h3>
              <p className="text-sm text-red-700">{error}</p>
            </div>
            {onRetry && (
              <button
                onClick={onRetry}
                className="flex items-center gap-2 px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-sm font-medium transition-colors">
                <RefreshCw size={14} />
                Retry
              </button>
            )}
          </div>
        </div>
      )}

      {/* Loading Indicator */}
      {loading && (
        <div className="mb-6 max-w-2xl w-full mx-auto">
          <div className="bg-sky-50 border border-sky-200 rounded-xl p-4 flex items-center gap-3">
            <div className="animate-spin">
              <BrainCircuit className="text-sky-500" size={20} />
            </div>
            <div className="flex-1">
              <p className="text-sm text-sky-700 font-medium">
                {progress || "Processing your request..."}
              </p>
              <p className="text-xs text-sky-600 mt-0.5">
                This may take 2-5 minutes for complex disruptions
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Main Input Area */}
      <InputBar onProcess={onProcess} disabled={loading} />

      {/* Feature Capabilities (Visual Cues) */}
      <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 opacity-60 hover:opacity-100 transition-opacity duration-500">
        <FeatureBadge
          icon={<ShieldAlert size={18} />}
          title="Safety First"
          desc="Automated compliance checks & binding constraints"
        />
        <FeatureBadge
          icon={<BrainCircuit size={18} />}
          title="Agentic Arbitration"
          desc="Multi-agent negotiation for optimal recovery"
        />
        <FeatureBadge
          icon={<Activity size={18} />}
          title="Live Execution"
          desc="MCP-driven actions with human oversight"
        />
      </div>
    </div>
  );
};

const FeatureBadge: React.FC<{
  icon: React.ReactNode;
  title: string;
  desc: string;
}> = ({ icon, title, desc }) => (
  <div className="flex flex-col items-center text-center p-4 rounded-2xl hover:bg-white/40 transition-colors cursor-default">
    <div className="p-2 bg-slate-100 rounded-lg text-slate-600 mb-2">
      {icon}
    </div>
    <h3 className="text-sm font-semibold text-slate-800">{title}</h3>
    <p className="text-xs text-slate-500 mt-1 max-w-[200px]">{desc}</p>
  </div>
);

export default LandingPage;
