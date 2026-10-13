import { useState } from "react";
import { Check, Copy } from "lucide-react";

export interface KeywordSectionProps {
  platform: string;
  keywords: string[];
}

export function KeywordSection({ platform, keywords }: KeywordSectionProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  const handleCopySingle = async (kw: string, index: number) => {
    try {
      await navigator.clipboard.writeText(kw);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch {
      // Ignored
    }
  };

  const handleCopyAll = async () => {
    if (!keywords || keywords.length === 0) return;
    const text = keywords.join(", ");
    try {
      await navigator.clipboard.writeText(text);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      // Ignored
    }
  };

  if (!keywords || keywords.length === 0) {
    return (
      <div className="p-4 text-sm text-text-muted text-center border border-dashed border-border rounded-input">
        No keywords generated for {platform}.
      </div>
    );
  }

  return (
    <div className="space-y-3.5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <h3 className="text-sm sm:text-base font-bold text-text uppercase tracking-wider">
            High-Search Keywords
          </h3>
          <span className="text-xs font-mono font-medium px-2.5 py-0.5 rounded-full bg-surface-2 border border-border text-text-muted">
            {keywords.length} found
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopyAll}
          className="self-start sm:self-auto flex items-center gap-1.5 text-xs sm:text-sm font-medium text-text-muted hover:text-text px-3 py-1.5 rounded bg-surface-2 hover:bg-surface border border-border transition-colors cursor-pointer"
        >
          {copiedAll ? (
            <>
              <Check className="w-4 h-4 text-success" />
              <span className="text-success font-semibold">Copied {keywords.length}</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span>Copy all keywords</span>
            </>
          )}
        </button>
      </div>

      {/* Pure chips container - Readable text-sm size with comfortable padding */}
      <div className="flex flex-wrap gap-2">
        {keywords.map((kw, idx) => {
          const isCopied = copiedIndex === idx;
          return (
            <button
              key={`${kw}-${idx}`}
              type="button"
              onClick={() => handleCopySingle(kw, idx)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-chip text-sm border transition-all select-none cursor-pointer ${
                isCopied
                  ? "bg-success/15 border-success/40 text-success font-semibold"
                  : "bg-surface-2 hover:bg-surface border-border hover:border-border-strong text-text font-medium"
              }`}
              title="Click to copy keyword"
            >
              {isCopied && <Check className="w-3.5 h-3.5 text-success" />}
              <span>{kw}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
