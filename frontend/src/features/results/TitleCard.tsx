import { useState } from "react";
import { Check, ChevronDown, ChevronUp, Copy, Sparkles } from "lucide-react";
import type { PlatformName, TitleSuggestion } from "../../types";

export interface TitleCardProps {
  platform: PlatformName;
  suggestion: TitleSuggestion;
  isPrimary?: boolean;
}

const STYLE_LABELS: Record<string, string> = {
  search: "Search-Optimised",
  balanced: "Balanced",
  short: "Short / Mobile",
};

const PLATFORM_MAX_LENGTHS: Record<PlatformName, number> = {
  amazon: 200,
  myntra: 60,
  flipkart: 120,
  meesho: 100,
};

export function TitleCard({
  platform,
  suggestion,
  isPrimary = false,
}: TitleCardProps) {
  const [copied, setCopied] = useState(false);
  const [showBreakdown, setShowBreakdown] = useState(false);

  const maxLen = PLATFORM_MAX_LENGTHS[platform] || 150;
  const currentLen = suggestion.length;

  // Length badge color
  let lengthColorClass = "bg-success/10 text-success border-success/30";
  if (currentLen > maxLen) {
    lengthColorClass = "bg-danger/10 text-danger border-danger/30";
  } else if (currentLen > maxLen * 0.95 || currentLen < maxLen * 0.25) {
    lengthColorClass = "bg-warning/10 text-warning border-warning/30";
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(suggestion.title);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignored
    }
  };

  return (
    <div
      className={`rounded-input p-4 space-y-3 transition-colors ${
        isPrimary
          ? "bg-surface border-2 border-accent/60 shadow-sm ring-1 ring-accent/20"
          : "bg-surface border border-border hover:border-border-strong"
      }`}
    >
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2.5">
          {isPrimary && (
            <span className="flex items-center gap-1.5 text-xs font-semibold text-accent bg-accent/15 border border-accent/30 px-2.5 py-0.5 rounded-full">
              <Sparkles className="w-3.5 h-3.5" />
              Primary Title to Put in Place
            </span>
          )}
          <span className="text-xs font-bold text-text uppercase tracking-wider">
            {STYLE_LABELS[suggestion.style] || suggestion.style}
          </span>
          <span
            className={`text-xs font-mono px-2.5 py-0.5 rounded-full border ${lengthColorClass}`}
          >
            {currentLen} / {maxLen} chars
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className={`flex items-center gap-1.5 text-xs px-3.5 py-1.5 rounded-md transition-colors cursor-pointer ${
            isPrimary
              ? "bg-accent text-accent-foreground font-semibold hover:opacity-90 shadow-sm"
              : "text-text-muted hover:text-text bg-surface-2 hover:bg-surface border border-border"
          }`}
          title="Copy exact title to clipboard"
        >
          {copied ? (
            <>
              <Check className="w-4 h-4 text-success" />
              <span className="text-success font-semibold">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span>{isPrimary ? "Copy Exact Title" : "Copy"}</span>
            </>
          )}
        </button>
      </div>

      {/* Composed Title Text - Large, Prominent, Highly Legible */}
      <div
        className={`p-3.5 rounded-md border select-all ${
          isPrimary
            ? "bg-surface-2/80 border-accent/30 text-text font-semibold text-base sm:text-[17px] leading-relaxed tracking-tight"
            : "bg-surface-2/40 border-border/60 text-text font-medium text-sm sm:text-base leading-relaxed"
        }`}
      >
        {suggestion.title}
      </div>

      {/* Warnings if any */}
      {suggestion.warnings && suggestion.warnings.length > 0 && (
        <div className="text-xs text-warning bg-warning/5 border border-warning/20 px-2.5 py-1.5 rounded">
          {suggestion.warnings.join("; ")}
        </div>
      )}

      {/* Part breakdown toggle */}
      {suggestion.parts && suggestion.parts.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowBreakdown(!showBreakdown)}
            className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors cursor-pointer"
          >
            <span>Word breakdown ({suggestion.parts.length} parts)</span>
            {showBreakdown ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>

          {showBreakdown && (
            <div className="flex flex-wrap gap-2 mt-2 pt-2.5 border-t border-border/50">
              {suggestion.parts.map((p, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center text-xs bg-surface-2 border border-border px-2 py-0.5 rounded text-text"
                >
                  <span className="text-text-muted mr-1.5 capitalize font-normal">
                    {p.label}:
                  </span>
                  <span className="font-semibold">{p.text}</span>
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
