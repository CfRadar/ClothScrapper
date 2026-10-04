import React from 'react';
import { CheckCircle2, Loader2, AlertTriangle } from 'lucide-react';

interface ProgressStripProps {
  status: 'idle' | 'running' | 'done' | 'error';
  stage: 'planner' | 'marketplace' | 'social' | 'analyst' | 'system';
  message: string;
  warnings: string[];
}

const STEPS = [
  { id: 'planner', label: '1. Planner' },
  { id: 'marketplace', label: '2. Marketplaces' },
  { id: 'social', label: '3. Social Buzz' },
  { id: 'analyst', label: '4. AI Analyst' },
] as const;

export const ProgressStrip: React.FC<ProgressStripProps> = ({
  status,
  stage,
  message,
  warnings,
}) => {
  if (status === 'idle') return null;

  const stageOrder = ['planner', 'marketplace', 'social', 'analyst', 'system'];
  const currentIdx = stageOrder.indexOf(stage);

  return (
    <div
      role="status"
      aria-live="polite"
      className="my-5 p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-sm"
    >
      {/* Horizontal Step Indicator */}
      <div className="flex items-center justify-between gap-2 mb-3">
        {STEPS.map((s, index) => {
          const stepIdx = stageOrder.indexOf(s.id);
          const isDone = status === 'done' || currentIdx > stepIdx;
          const isActive = status === 'running' && stage === s.id;

          return (
            <div key={s.id} className="flex-1 flex items-center gap-2">
              <div
                className={`flex items-center gap-1.5 text-xs font-medium transition-colors ${
                  isDone
                    ? 'text-emerald-400'
                    : isActive
                    ? 'text-sky-400'
                    : 'text-slate-500'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                ) : isActive ? (
                  <Loader2 className="w-4 h-4 text-sky-400 animate-spin shrink-0" />
                ) : (
                  <span className="w-4 h-4 rounded-full border border-slate-700 flex items-center justify-center text-[10px] shrink-0">
                    {index + 1}
                  </span>
                )}
                <span className="hidden sm:inline">{s.label}</span>
              </div>
              {index < STEPS.length - 1 && (
                <div
                  className={`flex-1 h-0.5 rounded transition-colors ${
                    isDone ? 'bg-emerald-500/50' : 'bg-slate-800'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Thin Animated Progress Bar */}
      <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full transition-all duration-500 ${
            status === 'done'
              ? 'w-full bg-emerald-500'
              : stage === 'planner'
              ? 'w-1/4 bg-sky-500'
              : stage === 'marketplace'
              ? 'w-2/4 bg-sky-500'
              : stage === 'social'
              ? 'w-3/4 bg-sky-500'
              : 'w-[90%] bg-sky-500'
          }`}
        />
      </div>

      {/* Live Single-Line Status Message */}
      <p className="text-xs text-slate-300 font-mono truncate">{message || 'Processing...'}</p>

      {/* Warnings List */}
      {warnings.length > 0 && (
        <div className="mt-2.5 pt-2 border-t border-slate-800 space-y-1">
          {warnings.map((w, idx) => (
            <div key={idx} className="flex items-center gap-1.5 text-xs text-amber-400">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
              <span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
