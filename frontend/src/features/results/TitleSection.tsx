import { useState } from "react";
import { Check, Copy } from "lucide-react";
import type { PlatformName, TitleSuggestion } from "../../types";
import { TitleCard } from "./TitleCard";

export interface TitleSectionProps {
  platform: PlatformName;
  titles: TitleSuggestion[];
}

export function TitleSection({ platform, titles }: TitleSectionProps) {
  const [copiedAll, setCopiedAll] = useState(false);

  const handleCopyAll = async () => {
    if (!titles || titles.length === 0) return;
    const text = titles
      .map((t) => `[${t.style.toUpperCase()} - ${t.length} chars]\n${t.title}`)
      .join("\n\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      // Ignored
    }
  };

  if (!titles || titles.length === 0) {
    return null;
  }

  const primaryTitle = titles[0];
  const alternativeTitles = titles.slice(1);

  return (
    <div className="space-y-3.5">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-sm sm:text-base font-bold text-text uppercase tracking-wider">
            Exact Listing Titles to Put in Place
          </h3>
          <p className="text-xs sm:text-sm text-text-muted mt-0.5">
            Crafted and benchmarked against top-ranking search results, strictly bounded to platform character limits.
          </p>
        </div>

        <button
          type="button"
          onClick={handleCopyAll}
          className="self-start sm:self-auto flex items-center gap-1.5 text-xs sm:text-sm font-medium text-text-muted hover:text-text px-3 py-1.5 rounded bg-surface-2 hover:bg-surface border border-border transition-colors cursor-pointer"
          title="Copy all title variants"
        >
          {copiedAll ? (
            <>
              <Check className="w-4 h-4 text-success" />
              <span className="text-success font-semibold">All Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span>Copy all variants</span>
            </>
          )}
        </button>
      </div>

      {/* Primary Recommended Title */}
      <div className="space-y-3">
        <TitleCard
          platform={platform}
          suggestion={primaryTitle}
          isPrimary={true}
        />

        {/* Alternative Variations */}
        {alternativeTitles.length > 0 && (
          <div className="pt-2 space-y-2.5">
            <span className="text-xs font-bold text-text-muted uppercase tracking-wider block">
              Alternative Formats ({alternativeTitles.length})
            </span>
            <div className="space-y-2.5">
              {alternativeTitles.map((titleSug, idx) => (
                <TitleCard
                  key={`${titleSug.style}-${idx}`}
                  platform={platform}
                  suggestion={titleSug}
                  isPrimary={false}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
