import React, { useState } from 'react';
import { AgentAvatar, AgentType } from './AgentAvatar';
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
  Users
} from 'lucide-react';

export interface MessageData {
  id: string;
  agent: AgentType;
  safetyAnalysis?: string;
  businessImpact?: string;
  crossImpactAnalysis?: string;
  isCrossImpactRound?: boolean;
  isDecision?: boolean;
  solutionTitle?: string;
}

interface AgentMessageProps {
  message: MessageData;
  isNew?: boolean;
}

export const AgentMessage: React.FC<AgentMessageProps> = ({ message, isNew = false }) => {
  const [activeModal, setActiveModal] = useState<'recovery' | 'report' | null>(null);

  // --- Specialized Decision Card Render ---
  if (message.isDecision) {
    return (
      <>
        <div className={`w-full max-w-4xl mx-auto mb-8 ${isNew ? 'animate-fade-in-up' : 'opacity-100'}`}>
          <div className="relative overflow-hidden rounded-2xl border-l-4 border-l-indigo-600 bg-gradient-to-br from-indigo-50/90 via-white to-purple-50/90 shadow-xl p-6 md:p-8">
            
            {/* Background Decoration */}
            <div className="absolute top-0 right-0 p-8 opacity-5">
              <BrainCircuit size={120} />
            </div>

            {/* Header Badge */}
            <div className="flex items-center justify-between mb-4">
               <div className="flex items-center gap-2 px-3 py-1 bg-indigo-600 text-white rounded-full text-[10px] font-bold uppercase tracking-widest shadow-md">
                 <BrainCircuit size={12} />
                 Decision Executed
               </div>
               <div className="flex items-center gap-2 text-indigo-700/60 text-xs font-semibold">
                 <span className="relative flex h-2 w-2">
                   <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                   <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                 </span>
                 Live in OCC
               </div>
            </div>

            {/* Content */}
            <div className="relative z-10">
              <h2 className="text-2xl font-bold text-slate-800 mb-2">{message.solutionTitle}</h2>
              <p className="text-slate-600 leading-relaxed mb-6 border-l-2 border-indigo-200 pl-4">
                {message.crossImpactAnalysis}
              </p>

              {/* Action Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <button 
                  onClick={() => setActiveModal('recovery')}
                  className="group flex items-center justify-between p-4 bg-white border border-slate-200 rounded-xl hover:border-indigo-400 hover:shadow-lg transition-all duration-300"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                      <ListChecks size={20} />
                    </div>
                    <div className="text-left">
                       <div className="text-sm font-bold text-slate-800">View Detailed Recovery</div>
                       <div className="text-xs text-slate-500">Monitor automated workflows</div>
                    </div>
                  </div>
                  <Activity size={16} className="text-slate-300 group-hover:text-indigo-500" />
                </button>

                <button 
                   onClick={() => setActiveModal('report')}
                   className="group flex items-center justify-between p-4 bg-white border border-slate-200 rounded-xl hover:border-emerald-400 hover:shadow-lg transition-all duration-300"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-emerald-50 rounded-lg text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                      <FileText size={20} />
                    </div>
                    <div className="text-left">
                       <div className="text-sm font-bold text-slate-800">View Detailed Report</div>
                       <div className="text-xs text-slate-500">Impact analysis & learnings</div>
                    </div>
                  </div>
                  <Download size={16} className="text-slate-300 group-hover:text-emerald-500" />
                </button>
              </div>

              {/* Footer Sync Indicator */}
              <div className="mt-6 pt-4 border-t border-indigo-100 flex items-center gap-2 text-slate-500 text-xs font-medium">
                <div className="flex items-center gap-1.5 text-indigo-600">
                  <Database size={14} />
                  <Check size={14} />
                </div>
                Strategy synced to Neural Knowledge Base (ID: #KB-9921) for future reinforcement learning.
              </div>
            </div>
          </div>
        </div>

        {/* --- Modals --- */}
        {activeModal === 'recovery' && (
          <RecoveryModal onClose={() => setActiveModal(null)} title={message.solutionTitle || 'Recovery Protocol'} />
        )}
        {activeModal === 'report' && (
          <ReportModal onClose={() => setActiveModal(null)} title={message.solutionTitle || 'Impact Report'} />
        )}
      </>
    );
  }

  // --- Standard Message Render ---
  return (
    <div className={`flex gap-3 w-full max-w-4xl mx-auto mb-4 ${isNew ? 'animate-fade-in-up' : 'opacity-100'}`}>
      <div className="flex-shrink-0 mt-1">
        <AgentAvatar type={message.agent} size="sm" status="idle" />
      </div>
      
      <div className="flex-1 bg-white/80 backdrop-blur-sm border border-slate-200 shadow-sm rounded-2xl rounded-tl-none p-4 overflow-hidden hover:shadow-md transition-all duration-300">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-baseline gap-2">
            <h4 className="font-bold text-slate-800 text-sm">{message.agent.replace('_', ' ')}</h4>
            <span className="text-[10px] text-slate-400 uppercase tracking-wide font-medium">Domain Agent</span>
          </div>
          
          {message.isCrossImpactRound && (
             <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-600 text-[10px] font-bold uppercase tracking-wider border border-indigo-100">
               Cross-Impact
             </span>
          )}
        </div>

        {!message.isCrossImpactRound && (
          <div className="space-y-3">
            {message.safetyAnalysis && (
              <div className="group flex gap-3 items-start p-3 rounded-lg bg-red-50/50 border border-red-100/50 hover:bg-red-50 transition-colors">
                <ShieldCheck size={16} className="text-red-500 mt-0.5 flex-shrink-0 opacity-70 group-hover:opacity-100 transition-opacity" />
                <div className="text-sm text-slate-700 leading-relaxed">
                  <span className="font-semibold text-red-700 block text-xs mb-0.5 uppercase tracking-wide opacity-80">Safety Constraint</span>
                  {message.safetyAnalysis}
                </div>
              </div>
            )}
            
            {message.businessImpact && (
              <div className="group flex gap-3 items-start p-3 rounded-lg bg-blue-50/50 border border-blue-100/50 hover:bg-blue-50 transition-colors">
                <TrendingUp size={16} className="text-blue-500 mt-0.5 flex-shrink-0 opacity-70 group-hover:opacity-100 transition-opacity" />
                <div className="text-sm text-slate-700 leading-relaxed">
                  <span className="font-semibold text-blue-700 block text-xs mb-0.5 uppercase tracking-wide opacity-80">Business Impact</span>
                  {message.businessImpact}
                </div>
              </div>
            )}
          </div>
        )}

        {message.isCrossImpactRound && (
          <div className="text-sm text-slate-700 leading-relaxed pl-2 border-l-2 border-indigo-200">
             {message.crossImpactAnalysis}
          </div>
        )}
      </div>
    </div>
  );
};

// --- Sub-Components for Modals ---

const RecoveryModal: React.FC<{ onClose: () => void; title: string }> = ({ onClose, title }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
    <div className="w-full max-w-3xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      {/* Modal Header */}
      <div className="px-6 py-4 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold text-slate-800">Automated Recovery Workflow</h3>
          <p className="text-xs text-slate-500">Executing strategy: {title}</p>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full text-slate-500 transition-colors">
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
        <button className="px-4 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 rounded-lg">Close</button>
        <button className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg flex items-center gap-2 shadow-lg shadow-indigo-200">
          <Download size={16} />
          Export Log
        </button>
      </div>
    </div>
  </div>
);

const RecoveryItem: React.FC<{ agent: string; time: string; task: string; status: 'completed' | 'processing' | 'pending'; details: string }> = ({ agent, time, task, status, details }) => (
  <div className="flex gap-4 p-4 bg-white border border-slate-100 rounded-xl shadow-sm">
    <div className="flex flex-col items-center gap-1 min-w-[60px]">
      <span className="text-[10px] font-mono text-slate-400">{time}</span>
      <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
        status === 'completed' ? 'bg-emerald-100 text-emerald-600' :
        status === 'processing' ? 'bg-amber-100 text-amber-600 animate-pulse' :
        'bg-slate-100 text-slate-400'
      }`}>
        {status === 'completed' ? <Check size={16} /> : <Activity size={16} />}
      </div>
    </div>
    <div className="flex-1">
      <div className="flex justify-between items-start">
        <h4 className="text-sm font-bold text-slate-800">{task}</h4>
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 bg-slate-50 px-2 py-0.5 rounded">{agent}</span>
      </div>
      <p className="text-xs text-slate-600 mt-1">{details}</p>
    </div>
  </div>
);


const ReportModal: React.FC<{ onClose: () => void; title: string }> = ({ onClose, title }) => (
  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
    <div className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
      
      {/* Header */}
      <div className="px-8 py-6 bg-slate-900 text-white flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2 mb-2 opacity-80">
            <BrainCircuit size={16} />
            <span className="text-xs font-mono tracking-widest uppercase">Arbitrator Analysis Engine</span>
          </div>
          <h2 className="text-2xl font-bold">{title}</h2>
          <p className="text-sm text-slate-300 mt-1">Full Impact Assessment & Decision Logic</p>
        </div>
        <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full text-white/70 transition-colors">
          <X size={24} />
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-8 grid grid-cols-1 md:grid-cols-2 gap-8">
        
        {/* Left Column */}
        <div className="space-y-6">
          <section>
            <h4 className="flex items-center gap-2 text-sm font-bold text-slate-800 uppercase tracking-wider mb-3 pb-2 border-b border-slate-100">
              <Users size={16} className="text-indigo-500" />
              Executive Summary
            </h4>
            <p className="text-sm text-slate-600 leading-relaxed text-justify">
              The decision to <strong>Repair & Delay (Option A)</strong> was prioritized over cancellation to protect brand equity among premium segments and ensure cargo contract fulfillment. While immediate direct costs are higher than a simple cancellation, the long-term NPS damage and cargo insurance liabilities of Option B were deemed unacceptable.
            </p>
          </section>

          <section>
             <h4 className="flex items-center gap-2 text-sm font-bold text-slate-800 uppercase tracking-wider mb-3 pb-2 border-b border-slate-100">
              <TrendingUp size={16} className="text-emerald-500" />
              Financial Breakdown
            </h4>
            <div className="bg-slate-50 rounded-xl p-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Engineering & Parts</span>
                <span className="font-mono font-medium">$42,000</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">EU261 Compensation</span>
                <span className="font-mono font-medium">$265,000</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-slate-600">Care & Interline</span>
                <span className="font-mono font-medium">$13,500</span>
              </div>
              <div className="flex justify-between text-sm font-bold pt-2 border-t border-slate-200 mt-2">
                <span className="text-slate-800">Total Estimated Cost</span>
                <span className="font-mono text-slate-900">$320,500</span>
              </div>
            </div>
          </section>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
           <section>
            <h4 className="flex items-center gap-2 text-sm font-bold text-slate-800 uppercase tracking-wider mb-3 pb-2 border-b border-slate-100">
              <AlertTriangle size={16} className="text-amber-500" />
              Risk Assessment
            </h4>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 bg-white border border-slate-100 rounded-lg shadow-sm">
                <div className="w-2 h-2 rounded-full bg-red-500"></div>
                <div className="flex-1">
                   <div className="text-xs font-bold text-slate-700">Downstream Connection Loss</div>
                   <div className="text-[10px] text-slate-500">High probability for non-protected pax (SYD/MEL)</div>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-white border border-slate-100 rounded-lg shadow-sm">
                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                <div className="flex-1">
                   <div className="text-xs font-bold text-slate-700">Crew Fatigue Limits</div>
                   <div className="text-[10px] text-slate-500">Reserve crew callout tight (90m buffer)</div>
                </div>
              </div>
            </div>
          </section>

          <section>
            <h4 className="flex items-center gap-2 text-sm font-bold text-slate-800 uppercase tracking-wider mb-3 pb-2 border-b border-slate-100">
              <BrainCircuit size={16} className="text-purple-500" />
              AI Learnings
            </h4>
            <ul className="list-disc list-inside text-xs text-slate-600 space-y-2">
              <li>VIP handling protocol triggered faster than previous event (12s improvement).</li>
              <li>Cargo weight logic successfully overrode Finance cancellation preference.</li>
              <li>New pattern identified: Hydraulic failures at LHR trending up (+15% YoY).</li>
            </ul>
          </section>
        </div>
      </div>

      {/* Footer */}
      <div className="px-8 py-5 border-t border-slate-200 bg-slate-50 flex justify-end gap-3">
        <button className="px-6 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-200 rounded-lg transition-colors">Close Report</button>
        <button className="px-6 py-2.5 text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg flex items-center gap-2 shadow-lg hover:shadow-xl transition-all">
          <Download size={18} />
          Download PDF
        </button>
      </div>
    </div>
  </div>
);