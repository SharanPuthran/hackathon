import React, { useState } from 'react';
import LandingPage from './components/LandingPage';
import OrchestrationView from './components/OrchestrationView';
import { Background } from './components/Background';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'landing' | 'orchestration'>('landing');
  const [userPrompt, setUserPrompt] = useState<string>('');

  const handleProcess = (prompt: string) => {
    setUserPrompt(prompt);
    // Transition to the orchestration view
    setCurrentView('orchestration');
  };

  return (
    <div className="relative w-full h-screen text-slate-800 font-sans selection:bg-sky-200 overflow-hidden">
      <Background />
      
      <div className="relative z-10 w-full h-full flex flex-col">
        {currentView === 'landing' && (
          <LandingPage onProcess={handleProcess} />
        )}
        {currentView === 'orchestration' && (
          <OrchestrationView prompt={userPrompt} />
        )}
      </div>
    </div>
  );
};

export default App;