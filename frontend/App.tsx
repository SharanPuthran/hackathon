import React, { useState } from "react";
import LandingPage from "./components/LandingPage";
import OrchestrationView from "./components/OrchestrationView";
import { Background } from "./components/Background";
import { useAPI } from "./hooks/useAPI";
import { StatusResponse } from "./services/apiAsync";

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<"landing" | "orchestration">(
    "landing",
  );
  const [userPrompt, setUserPrompt] = useState<string>("");
  const [apiResponse, setApiResponse] = useState<StatusResponse | null>(null);
  const { invoke, loading, progress, error, clearError } = useAPI();

  const handleProcess = async (prompt: string) => {
    setUserPrompt(prompt);
    clearError();

    try {
      // Use async polling API
      const response = await invoke(prompt);
      setApiResponse(response);

      // Transition to orchestration view on success
      setCurrentView("orchestration");
    } catch (err) {
      // Error is already set by useAPI hook
      console.error("Failed to invoke API:", err);
      // Stay on landing page to show error
    }
  };

  const handleRetry = () => {
    if (userPrompt) {
      handleProcess(userPrompt);
    }
  };

  return (
    <div className="relative w-full h-screen text-slate-800 font-sans selection:bg-sky-200 overflow-hidden">
      <Background />

      <div className="relative z-10 w-full h-full flex flex-col">
        {currentView === "landing" && (
          <LandingPage
            onProcess={handleProcess}
            loading={loading}
            progress={progress}
            error={error}
            onRetry={handleRetry}
          />
        )}
        {currentView === "orchestration" && apiResponse && (
          <OrchestrationView
            prompt={userPrompt}
            apiResponse={{
              status: "success",
              request_id: apiResponse.request_id,
              session_id: apiResponse.session_id || "",
              execution_time_ms: apiResponse.execution_time_ms || 0,
              timestamp: new Date().toISOString(),
              assessment: apiResponse.assessment,
            }}
          />
        )}
      </div>
    </div>
  );
};

export default App;
