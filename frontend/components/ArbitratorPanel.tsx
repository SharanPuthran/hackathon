import React, { useState } from 'react';
import { AgentAvatar } from './AgentAvatar';
import { BrainCircuit, CheckCircle2, AlertTriangle, Send, X, Star, Check } from 'lucide-react';

export interface Solution {
  id: string;
  title: string;
  description: string;
  impact: 'low' | 'medium' | 'high';
  cost: string;
  recommended?: boolean;
}

interface ArbitratorPanelProps {
  stage: 'summoning' | 'initial_round' | 'waiting_for_user' | 'cross_impact' | 'decision_phase';
  liveAnalysis: string;
  solutions: Solution[];
  onSelectSolution: (solution: Solution) => void;
  onOverride: (text: string) => void;
  selectedSolutionId: string | null;
}

export const ArbitratorPanel: React.FC<ArbitratorPanelProps> = ({ 
  stage, 
  liveAnalysis, 
  solutions, 
  onSelectSolution, 
  onOverride,
  selectedSolutionId
}) => {
  const [showOverride, setShowOverride] = useState(false);
  const [overrideText, setOverrideText] = useState('');

  const handleOverrideSubmit = () => {
    if (overrideText.trim()) {
      onOverride(overrideText);
      setShowOverride(false);
      setOverrideText('');
    }
  };

  return (
    <div className="w-full h-full bg-white border-l border-slate-200 shadow-xl flex flex-col z-30">
      {/* Header */}
      <div className="p-5 border-b border-slate-100 bg-slate-50/50 backdrop-blur-sm">
        <div className="flex items-center gap-3 mb-1">
          <AgentAvatar type="Arbitrator" size="sm" />
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-widest">Arbitrator Intelligence</h2>
        </div>
        <div className="flex items-center gap-2 ml-1">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <span className="text-xs text-slate-500 font-mono">Status: {stage === 'decision_phase' ? 'DECISION REQUIRED' : 'ANALYZING STREAM'}</span>
        </div>
      </div>

      {/* Live Analysis Stream */}
      <div className="flex-1 overflow-y-auto p-5 space-y-6">
        
        {/* Dynamic Analysis Block */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Live Synthesis</h3>
          <div className="p-4 bg-indigo-50/50 rounded-xl border border-indigo-100 text-sm text-slate-700 leading-relaxed font-medium animate-fade-in-up">
            <BrainCircuit size={16} className="inline mr-2 text-indigo-500 mb-0.5" />
            {liveAnalysis}
          </div>
        </div>

        {/* Proposed Solutions (Only visible in decision phase) */}
        {stage === 'decision_phase' && (
          <div className="space-y-3 animate-fade-in-up">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center justify-between">
              <span>Strategic Options</span>
              <span className="text-[10px] bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">Action Required</span>
            </h3>
            
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
                    ${isSelected 
                      ? 'bg-emerald-50 border-2 border-emerald-500 ring-4 ring-emerald-500/20 shadow-lg scale-[1.02]' 
                      : isRecommended && !isOtherSelected
                        ? 'bg-gradient-to-br from-indigo-50 to-white border-2 border-indigo-500 ring-2 ring-indigo-500/10 shadow-md' 
                        : 'bg-white border border-slate-200 hover:border-indigo-300 hover:bg-slate-50'
                    }
                    ${isOtherSelected ? 'opacity-50 grayscale' : 'opacity-100'}
                  `}
                >
                  {/* Tags */}
                  <div className="flex gap-2 mb-2">
                    {isRecommended && (
                      <div className={`
                        text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full flex items-center gap-1 shadow-sm
                        ${isSelected ? 'bg-emerald-100 text-emerald-700' : 'bg-indigo-600 text-white'}
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
                     <h4 className={`font-semibold transition-colors ${isSelected ? 'text-emerald-900' : isRecommended ? 'text-indigo-900' : 'text-slate-800 group-hover:text-indigo-700'}`}>
                       {sol.title}
                     </h4>
                     <span className="text-xs font-mono text-slate-500">{sol.cost}</span>
                  </div>
                  <p className="text-xs text-slate-600 leading-relaxed mb-3">{sol.description}</p>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                      sol.impact === 'high' ? 'bg-red-100 text-red-600' : 
                      sol.impact === 'medium' ? 'bg-amber-100 text-amber-600' : 
                      'bg-green-100 text-green-600'
                    }`}>
                      {sol.impact} Risk
                    </span>
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
            <div className={`pt-4 border-t border-slate-100 ${selectedSolutionId ? 'opacity-40 pointer-events-none' : ''}`}>
               <button 
                 onClick={() => setShowOverride(true)}
                 disabled={!!selectedSolutionId}
                 className="w-full py-3 px-4 rounded-xl border border-dashed border-slate-300 text-slate-500 text-sm font-medium hover:bg-slate-50 hover:text-slate-800 transition-colors flex items-center justify-center gap-2"
               >
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
            <h3 className="font-bold text-slate-800 text-lg">Manual Override</h3>
            <button onClick={() => setShowOverride(false)} className="p-2 hover:bg-slate-100 rounded-full text-slate-500">
              <X size={20} />
            </button>
          </div>
          <p className="text-sm text-slate-500 mb-4">Rejecting AI suggestions. Please specify the mandatory course of action for the recovery agents.</p>
          <textarea 
            className="flex-1 w-full bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none mb-4"
            placeholder="E.g., Prioritize crew rest at outstation and delay flight 12 hours. Accept hotel costs..."
            value={overrideText}
            onChange={(e) => setOverrideText(e.target.value)}
          />
          <button 
            onClick={handleOverrideSubmit}
            disabled={!overrideText.trim()}
            className="w-full py-3 bg-slate-900 text-white rounded-xl font-semibold shadow-lg hover:bg-slate-800 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Send size={18} />
            Submit Directive
          </button>
        </div>
      )}
    </div>
  );
};