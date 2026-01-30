import React from 'react';
import { 
  Wrench, 
  Scale, 
  Users, 
  Share2, 
  HeartHandshake, 
  Package, 
  DollarSign, 
  BrainCircuit,
  LucideIcon
} from 'lucide-react';

export type AgentType = 
  | 'Arbitrator'
  | 'Maintenance' 
  | 'Regulatory' 
  | 'Crew_Compliance' 
  | 'Network' 
  | 'Guest_Experience' 
  | 'Cargo' 
  | 'Finance';

interface AgentAvatarProps {
  type: AgentType;
  status?: 'idle' | 'thinking' | 'speaking';
  size?: 'sm' | 'md' | 'lg';
  showName?: boolean;
}

export const AGENT_CONFIG: Record<AgentType, { icon: LucideIcon; color: string; label: string; bg: string }> = {
  Arbitrator: { icon: BrainCircuit, color: 'text-indigo-600', label: 'Arbitrator', bg: 'bg-indigo-100' },
  Maintenance: { icon: Wrench, color: 'text-slate-600', label: 'Maintenance', bg: 'bg-slate-100' },
  Regulatory: { icon: Scale, color: 'text-red-600', label: 'Regulatory', bg: 'bg-red-100' },
  Crew_Compliance: { icon: Users, color: 'text-purple-600', label: 'Crew', bg: 'bg-purple-100' },
  Network: { icon: Share2, color: 'text-sky-600', label: 'Network', bg: 'bg-sky-100' },
  Guest_Experience: { icon: HeartHandshake, color: 'text-pink-600', label: 'Guest Exp', bg: 'bg-pink-100' },
  Cargo: { icon: Package, color: 'text-amber-600', label: 'Cargo', bg: 'bg-amber-100' },
  Finance: { icon: DollarSign, color: 'text-emerald-600', label: 'Finance', bg: 'bg-emerald-100' },
};

export const AgentAvatar: React.FC<AgentAvatarProps> = ({ type, status = 'idle', size = 'md', showName = false }) => {
  const config = AGENT_CONFIG[type];
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'w-8 h-8 p-1.5',
    md: 'w-10 h-10 p-2',
    lg: 'w-16 h-16 p-4',
  };

  const iconSizes = {
    sm: 16,
    md: 20,
    lg: 32,
  };

  return (
    <div className="flex flex-col items-center gap-1.5 transition-all duration-300">
      <div className={`
        relative ${sizeClasses[size]} rounded-2xl ${config.bg} shadow-sm 
        flex items-center justify-center transition-all duration-500
        ${status === 'speaking' ? 'scale-110 ring-2 ring-offset-2 ring-sky-400 z-10' : ''}
        ${status === 'thinking' ? 'scale-105 ring-2 ring-amber-200 bg-amber-50' : ''}
      `}>
        {/* Thinking Pulse Animation */}
        {status === 'thinking' && (
          <div className="absolute inset-0 rounded-2xl animate-pulse ring-2 ring-amber-400 opacity-50"></div>
        )}

        <Icon size={iconSizes[size]} className={`${config.color} relative z-10`} />
        
        {/* Status Indicator Dot */}
        {status === 'speaking' && (
          <span className="absolute -top-1 -right-1 flex h-3 w-3 z-20">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-green-400"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
          </span>
        )}
      </div>
      
      {showName && (
        <span className={`
          text-[10px] font-bold uppercase tracking-wider text-center max-w-[80px] leading-tight transition-colors duration-300
          ${status === 'speaking' ? 'text-slate-800' : 'text-slate-400'}
        `}>
          {config.label}
        </span>
      )}
    </div>
  );
};