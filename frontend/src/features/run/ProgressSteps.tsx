import { AlertCircle, CheckCircle2, Loader2, StopCircle } from "lucide-react";
import { Button } from "../../ui/Button";
import type { StepStatus } from "./useRun";

export interface ProgressStepsProps {
  stepStatuses: Record<1 | 2 | 3 | 4, StepStatus>;
  activeMessage: string;
  onStop: () => void;
}

const STEPS = [
  { id: 1 as const, title: "Understanding your product", subtitle: "Target audience personas & marketplace search intent" },
  { id: 2 as const, title: "Searching marketplaces", subtitle: "Live catalog attributes & seller autosuggest" },
  { id: 3 as const, title: "Checking search trends", subtitle: "Social listening & organic shopper demand signals" },
  { id: 4 as const, title: "Writing keywords & titles", subtitle: "Deterministic scoring & platform formula composition" },
];

export function ProgressSteps({ stepStatuses, activeMessage, onStop }: ProgressStepsProps) {
  const getCompletedCount = () => {
    return Object.values(stepStatuses).filter((s) => s === "done").length;
  };

  const progressPercent = Math.min(100, Math.max(15, getCompletedCount() * 25 + 15));

  const renderIcon = (status: StepStatus) => {
    switch (status) {
      case "done":
        return <CheckCircle2 className="w-5 h-5 text-success shrink-0" />;
      case "running":
        return <Loader2 className="w-5 h-5 text-accent animate-spin shrink-0" />;
      case "error":
        return <AlertCircle className="w-5 h-5 text-danger shrink-0" />;
      case "pending":
      default:
        return <div className="w-5 h-5 rounded-full border border-border shrink-0 flex items-center justify-center bg-surface-2" />;
    }
  };

  return (
    <div className="bg-surface border border-border rounded-modal p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
        <div>
          <h3 className="text-base font-bold text-text">Generating SEO keywords & titles</h3>
          <p className="text-xs sm:text-sm text-text-muted mt-1 truncate max-w-md">
            {activeMessage || "Processing brief through agent pipeline..."}
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={onStop}
          className="gap-1.5 text-danger hover:text-danger hover:bg-danger/10 border-danger/30 text-xs sm:text-sm font-semibold"
        >
          <StopCircle className="w-4 h-4" />
          <span>Stop</span>
        </Button>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-surface-2 h-2 rounded-full overflow-hidden">
        <div
          className="bg-accent h-full transition-all duration-500 ease-out"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Steps List */}
      <div className="space-y-3.5">
        {STEPS.map((step) => {
          const status = stepStatuses[step.id];
          const isCurrent = status === "running";

          return (
            <div
              key={step.id}
              className={`flex items-start gap-3.5 p-3.5 rounded-input border transition-colors ${
                isCurrent
                  ? "bg-accent-soft/40 border-accent/40"
                  : status === "done"
                  ? "bg-surface border-border/80"
                  : "bg-surface-2/30 border-transparent opacity-60"
              }`}
            >
              <div className="mt-0.5">{renderIcon(status)}</div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <span
                    className={`text-sm font-semibold ${
                      isCurrent ? "text-accent" : "text-text"
                    }`}
                  >
                    {step.title}
                  </span>
                  <span className="text-xs font-mono text-text-muted capitalize">
                    {status}
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-text-muted mt-0.5">
                  {step.subtitle}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
