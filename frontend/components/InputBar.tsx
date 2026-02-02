import React, { useState, useRef, useEffect } from "react";
import { Mic, ArrowRight, Sparkles } from "lucide-react";

interface InputBarProps {
  onProcess: (text: string) => void;
  disabled?: boolean;
}

export const InputBar: React.FC<InputBarProps> = ({
  onProcess,
  disabled = false,
}) => {
  const [text, setText] = useState("");
  const [isListening, setIsListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  }, [text]);

  const handleProcessClick = () => {
    if (text.trim() && !disabled) {
      onProcess(text);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !disabled) {
      e.preventDefault();
      handleProcessClick();
    }
  };

  const toggleListening = () => {
    if (disabled) return;
    setIsListening(!isListening);
    if (!isListening) {
      setTimeout(() => {
        setText(
          (prev) => prev + "EY551 LHR->AUH hydraulic issue reported at gate...",
        );
        setIsListening(false);
      }, 2000);
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto px-4">
      <div className="relative group">
        {/* Glow Effect behind input (reduced opacity) */}
        <div className="absolute -inset-1 bg-gradient-to-r from-sky-400 to-indigo-400 rounded-3xl blur opacity-10 group-hover:opacity-30 transition duration-1000 group-hover:duration-200"></div>

        {/* Glassmorphic Container - Removed focus ring */}
        <div className="relative flex items-end gap-2 bg-white/80 backdrop-blur-xl border border-white/60 shadow-xl rounded-3xl px-2 py-2 transition-all duration-300">
          {/* Text Input */}
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the disruption event..."
            disabled={disabled}
            className="flex-1 max-h-[200px] bg-transparent border-none focus:ring-0 text-slate-700 placeholder-slate-400 resize-none py-3 pl-4 text-lg leading-relaxed font-normal outline-none disabled:opacity-50 disabled:cursor-not-allowed"
            rows={1}
            style={{ minHeight: "52px" }}
          />

          {/* Right Action Cluster */}
          <div className="flex items-center gap-1 pb-1.5 pr-1.5">
            {/* Mic Button */}
            <button
              onClick={toggleListening}
              disabled={disabled}
              className={`p-2 rounded-full transition-all duration-300 ${
                isListening
                  ? "bg-red-50 text-red-500 animate-pulse"
                  : "text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}>
              <Mic size={20} />
            </button>

            {/* Process Button - Circular Icon Only */}
            <button
              onClick={handleProcessClick}
              disabled={!text.trim() || disabled}
              className={`
                flex items-center justify-center h-10 w-10 rounded-full transition-all duration-300
                flex-shrink-0
                ${
                  text.trim() && !disabled
                    ? "bg-gradient-to-r from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20 transform hover:scale-105"
                    : "bg-slate-100 text-slate-300 cursor-not-allowed"
                }
              `}
              aria-label="Process">
              <ArrowRight size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* Helper Chips / Suggestions */}
      <div className="mt-6 flex flex-wrap justify-center gap-3 animate-fade-in-up">
        <SuggestionChip
          label="EY551 LHR→AUH hydraulic issue"
          delay="0.1s"
          onClick={() =>
            !disabled &&
            setText(
              "EY551 LHR->AUH hydraulic issue requiring immediate assessment.",
            )
          }
          disabled={disabled}
        />
        <SuggestionChip
          label="Crew Duty Limit Exceeded - QR102"
          delay="0.2s"
          onClick={() =>
            !disabled &&
            setText(
              "Flight QR102 crew is approaching duty limits due to 2h delay.",
            )
          }
          disabled={disabled}
        />
        <SuggestionChip
          label="A380 AOG @ JFK"
          delay="0.3s"
          onClick={() =>
            !disabled &&
            setText(
              "A380 AOG at JFK. Needs MEL status check and part sourcing.",
            )
          }
          disabled={disabled}
        />
      </div>
    </div>
  );
};

const SuggestionChip: React.FC<{
  label: string;
  delay: string;
  onClick: () => void;
  disabled?: boolean;
}> = ({ label, delay, onClick, disabled = false }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className={`flex items-center gap-1.5 px-4 py-2 bg-white/40 hover:bg-white/90 backdrop-blur-md border border-white/40 rounded-full text-sm text-slate-600 shadow-sm hover:shadow-md transition-all duration-300 cursor-pointer ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    style={{ animationDelay: delay }}>
    <Sparkles size={12} className="text-sky-500" />
    {label}
  </button>
);
