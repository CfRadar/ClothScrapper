import { AlertTriangle, Download, RefreshCw, Sparkles } from "lucide-react";
import {
  exportAllToCSV,
  exportKeywordsToCSV,
  exportTopScrapedTitlesToCSV,
} from "../../lib/csv";
import type { ProductBrief, RunResult } from "../../types";
import { Button } from "../../ui/Button";
import { ProgressSteps } from "../run/ProgressSteps";
import type { ChatMessage, RunStatus, StepStatus } from "../run/useRun";
import { PlatformTabs } from "./PlatformTabs";
import { RefineBox } from "./RefineBox";

export interface ResultsPanelProps {
  status: RunStatus;
  result: RunResult | null;
  error: string | null;
  activeMessage: string;
  stepStatuses: Record<1 | 2 | 3 | 4, StepStatus>;
  chatHistory: ChatMessage[];
  chatLoading: boolean;
  onStop: () => void;
  onReset: () => void;
  onSendMessage: (message: string) => void;
  onSelectSampleBrief: (sample: Partial<ProductBrief>) => void;
}

export function ResultsPanel({
  status,
  result,
  error,
  activeMessage,
  stepStatuses,
  chatHistory,
  chatLoading,
  onStop,
  onReset,
  onSendMessage,
  onSelectSampleBrief,
}: ResultsPanelProps) {
  // 1. Idle state
  if (status === "idle") {
    return (
      <div className="bg-surface border border-border rounded-modal p-8 shadow-sm flex flex-col items-center justify-center text-center space-y-6 min-h-[460px]">
        <div className="w-12 h-12 rounded-full bg-accent-soft flex items-center justify-center text-accent">
          <Sparkles className="w-6 h-6" />
        </div>

        <div className="max-w-md space-y-1.5">
          <h3 className="text-base font-semibold text-text">
            Ready to generate marketplace SEO
          </h3>
          <p className="text-xs text-text-muted leading-relaxed">
            Fill out the brief on the left with your T-shirt details and target marketplaces.
            We will research live listings, analyze search trends, and compose compliant titles.
          </p>
        </div>

        {/* Quick sample brief prompts */}
        <div className="space-y-2 pt-2">
          <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider block">
            Or try an example brief:
          </span>
          <div className="flex flex-wrap gap-2 justify-center max-w-lg">
            <button
              type="button"
              onClick={() =>
                onSelectSampleBrief({
                  platforms: ["amazon", "myntra", "flipkart", "meesho"],
                  tshirt_type: "oversized graphic tee",
                  color: "black",
                  gender: "unisex",
                  fit: "oversized",
                  fabric: "100% cotton 240 GSM",
                  neck: "round neck",
                  sleeve: "half sleeve",
                  pattern: "graphic streetwear print",
                  occasion: "casual streetwear",
                })
              }
              className="text-xs bg-surface-2 hover:bg-surface border border-border px-3 py-1.5 rounded-input text-text-muted hover:text-text transition-colors cursor-pointer"
            >
              Black Oversized Graphic Tee (240 GSM)
            </button>
            <button
              type="button"
              onClick={() =>
                onSelectSampleBrief({
                  platforms: ["amazon", "myntra", "flipkart"],
                  tshirt_type: "drop shoulder anime tee",
                  color: "sage green",
                  gender: "men",
                  fit: "drop shoulder",
                  fabric: "french terry cotton",
                  neck: "round neck",
                  sleeve: "half sleeve",
                  pattern: "anime graphic",
                  occasion: "college streetwear",
                })
              }
              className="text-xs bg-surface-2 hover:bg-surface border border-border px-3 py-1.5 rounded-input text-text-muted hover:text-text transition-colors cursor-pointer"
            >
              Sage Green Drop Shoulder Anime Tee
            </button>
            <button
              type="button"
              onClick={() =>
                onSelectSampleBrief({
                  platforms: ["amazon", "flipkart", "meesho"],
                  tshirt_type: "solid polo collar tee",
                  color: "navy blue",
                  gender: "men",
                  fit: "regular fit",
                  fabric: "cotton pique blend",
                  neck: "polo collar",
                  sleeve: "half sleeve",
                  pattern: "solid plain",
                  occasion: "semi-formal casual",
                })
              }
              className="text-xs bg-surface-2 hover:bg-surface border border-border px-3 py-1.5 rounded-input text-text-muted hover:text-text transition-colors cursor-pointer"
            >
              Navy Blue Polo Collar Casual Tee
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 2. Running state
  if (status === "running") {
    return (
      <ProgressSteps
        stepStatuses={stepStatuses}
        activeMessage={activeMessage}
        onStop={onStop}
      />
    );
  }

  // 3. Error state
  if (status === "error") {
    return (
      <div className="bg-surface border border-danger/40 rounded-modal p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-danger">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <h3 className="text-sm font-semibold">Generation encountered an error</h3>
        </div>
        <p className="text-xs text-text-muted bg-danger/5 p-3 rounded border border-danger/20">
          {error || "An unexpected error occurred while executing the agent workflow."}
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" size="sm" onClick={onReset}>
            Reset Form
          </Button>
        </div>
      </div>
    );
  }

  // 4. Cancelled state
  if (status === "cancelled") {
    return (
      <div className="bg-surface border border-border rounded-modal p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 text-warning">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <h3 className="text-sm font-semibold">Generation stopped</h3>
        </div>
        <p className="text-xs text-text-muted">
          The generation run was cancelled by user request. You can tweak your brief and try again.
        </p>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" size="sm" onClick={onReset}>
            Reset
          </Button>
        </div>
      </div>
    );
  }

  // 5. Done state
  if (status === "done" && result) {
    return (
      <div className="bg-surface border border-border rounded-modal p-6 shadow-sm space-y-6">
        {/* Top bar with Target Market & Exports */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-4">
          <div>
            <span className="text-xs font-bold text-text-muted uppercase tracking-wider block">
              Target Audience & Persona
            </span>
            <p className="text-sm sm:text-base font-semibold text-text mt-0.5">
              {result.target_market_summary || "Urban Fashion Shoppers"}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => exportKeywordsToCSV(result.platforms)}
              className="gap-1.5 text-xs sm:text-sm font-medium"
              title="Download keywords as CSV"
            >
              <Download className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>Keywords</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => exportTopScrapedTitlesToCSV(result.platforms)}
              className="gap-1.5 text-xs sm:text-sm font-medium"
              title="Download scraped competitor titles as CSV"
            >
              <Download className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>Scraped Titles</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => exportAllToCSV(result.platforms)}
              className="gap-1.5 text-xs sm:text-sm font-medium"
              title="Download all titles and keywords as CSV"
            >
              <Download className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>Export All</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={onReset}
              className="gap-1.5 text-xs sm:text-sm font-medium"
              title="Start a new brief"
            >
              <RefreshCw className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              <span>New</span>
            </Button>
          </div>
        </div>

        {/* Platform Tabs */}
        <PlatformTabs platforms={result.platforms} />

        {/* Inline AI refinement chat */}
        <div className="border-t border-border pt-4">
          <RefineBox
            chatHistory={chatHistory}
            chatLoading={chatLoading}
            onSendMessage={onSendMessage}
          />
        </div>
      </div>
    );
  }

  return null;
}
