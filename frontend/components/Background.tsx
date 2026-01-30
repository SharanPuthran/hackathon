import React from 'react';
import { 
  Plane, 
  AlertTriangle, 
  Clock, 
  Wrench, 
  CloudRain, 
  Users, 
  Activity,
  ShieldCheck,
  Globe
} from 'lucide-react';

export const Background: React.FC = () => {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {/* Soft Gradient Blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-sky-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob"></div>
      <div className="absolute top-[-10%] right-[-10%] w-96 h-96 bg-indigo-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-2000"></div>
      <div className="absolute bottom-[-20%] left-[20%] w-96 h-96 bg-purple-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-blob animation-delay-4000"></div>

      {/* Grid Pattern Overlay */}
      <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
      
      {/* Floating Icons - Faded in background to represent the "Agentic Roster" */}
      <div className="absolute inset-0">
        {/* Safety & Compliance Icons */}
        <FloatingIcon icon={<ShieldCheck size={48} />} top="15%" left="10%" delay="0s" color="text-red-900" opacity={0.03} />
        <FloatingIcon icon={<Wrench size={40} />} top="25%" right="15%" delay="2s" color="text-slate-900" opacity={0.04} />
        <FloatingIcon icon={<AlertTriangle size={56} />} bottom="20%" left="15%" delay="4s" color="text-amber-900" opacity={0.03} />
        
        {/* Business Optimization Icons */}
        <FloatingIcon icon={<Users size={44} />} top="10%" right="30%" delay="1s" color="text-blue-900" opacity={0.04} />
        <FloatingIcon icon={<Globe size={64} />} bottom="30%" right="10%" delay="3s" color="text-indigo-900" opacity={0.03} />
        
        {/* Disruption Context Icons */}
        <FloatingIcon icon={<CloudRain size={50} />} top="40%" left="5%" delay="5s" color="text-slate-600" opacity={0.04} />
        <FloatingIcon icon={<Clock size={48} />} bottom="10%" left="40%" delay="1.5s" color="text-slate-600" opacity={0.04} />
        <FloatingIcon icon={<Plane size={80} />} top="50%" right="40%" delay="3.5s" color="text-sky-900" opacity={0.02} rotate={-45} />
      </div>
    </div>
  );
};

interface FloatingIconProps {
  icon: React.ReactNode;
  top?: string;
  left?: string;
  right?: string;
  bottom?: string;
  delay: string;
  color: string;
  opacity: number;
  rotate?: number;
}

const FloatingIcon: React.FC<FloatingIconProps> = ({ icon, top, left, right, bottom, delay, color, opacity, rotate = 0 }) => {
  return (
    <div 
      className={`absolute ${color} animate-float transition-all duration-1000`}
      style={{ 
        top, left, right, bottom, 
        animationDelay: delay, 
        opacity: opacity,
        transform: `rotate(${rotate}deg)`
      }}
    >
      {icon}
    </div>
  );
};