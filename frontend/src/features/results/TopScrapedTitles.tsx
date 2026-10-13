import { useState } from "react";
import { Check, Copy, Trophy } from "lucide-react";
import type { CompetitorTitle, PlatformName } from "../../types";

export interface TopScrapedTitlesProps {
  platform: PlatformName;
  competitors?: CompetitorTitle[];
}

const PLATFORM_LABELS: Record<string, string> = {
  amazon: "Amazon",
  myntra: "Myntra",
  flipkart: "Flipkart",
  meesho: "Meesho",
};

export function TopScrapedTitles({
  platform,
  competitors = [],
}: TopScrapedTitlesProps) {
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [copiedAll, setCopiedAll] = useState(false);

  if (!competitors || competitors.length === 0) {
    return null;
  }

  const platformLabel = PLATFORM_LABELS[platform] || platform;

  const handleCopy = async (title: string, index: number) => {
    try {
      await navigator.clipboard.writeText(title);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch {
      // Ignored
    }
  };

  const handleCopyAll = async () => {
    const text = competitors
      .map(
        (c) =>
          `#${c.rank} (${c.length} chars)${c.brand ? ` [${c.brand}]` : ""}:\n${c.title}`
      )
      .join("\n\n");
    try {
      await navigator.clipboard.writeText(text);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch {
      // Ignored
    }
  };

  return (
    <div className="bg-surface border border-border rounded-input p-4 sm:p-5 space-y-4">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div className="flex items-start sm:items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-accent/10 text-accent mt-0.5 sm:mt-0">
            <Trophy className="w-4 h-4 sm:w-5 sm:h-5" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-text uppercase tracking-wider">
              Top 10 Scraped Titles on {platformLabel}
            </h3>
            <p className="text-xs sm:text-sm text-text-muted mt-0.5">
              Live ranking titles extracted from top {platformLabel} search
              results. Use them to benchmark keywords, attributes, and phrasing.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={handleCopyAll}
          className="self-start sm:self-auto flex items-center gap-1.5 text-xs sm:text-sm font-medium text-text-muted hover:text-text px-3 py-1.5 rounded bg-surface-2 hover:bg-surface border border-border transition-colors cursor-pointer"
          title="Copy all 10 scraped titles"
        >
          {copiedAll ? (
            <>
              <Check className="w-4 h-4 text-success" />
              <span className="text-success font-semibold">All 10 Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span>Copy all 10</span>
            </>
          )}
        </button>
      </div>

      {/* Competitors List */}
      <div className="space-y-2.5">
        {competitors.slice(0, 10).map((comp, idx) => {
          const isCopied = copiedIndex === idx;
          const isTop3 = comp.rank <= 3;

          return (
            <div
              key={`${comp.rank}-${idx}`}
              className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-md bg-surface-2/50 border border-border/70 hover:border-border-strong hover:bg-surface-2 transition-colors"
            >
              {/* Left: Rank & Title */}
              <div className="flex items-start gap-3 min-w-0 flex-1">
                <span
                  className={`flex-shrink-0 inline-flex items-center justify-center w-7 h-7 rounded text-xs font-mono font-bold ${
                    isTop3
                      ? "bg-accent/20 text-accent border border-accent/40"
                      : "bg-surface text-text-muted border border-border"
                  }`}
                  title={`Search rank #${comp.rank}`}
                >
                  #{comp.rank}
                </span>

                <div className="min-w-0 flex-1 space-y-1.5">
                  <p className="text-sm sm:text-base font-medium text-text leading-snug break-words select-all">
                    {comp.title}
                  </p>

                  {/* Metadata Chips */}
                  <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
                    <span className="font-mono bg-surface border border-border/80 px-2 py-0.5 rounded font-medium">
                      {comp.length} chars
                    </span>
                    {comp.brand && (
                      <span className="bg-surface border border-border/80 px-2 py-0.5 rounded">
                        Brand: <strong className="text-text font-semibold">{comp.brand}</strong>
                      </span>
                    )}
                    {comp.price && (
                      <span className="bg-surface border border-border/80 px-2 py-0.5 rounded text-text font-medium">
                        {comp.price}
                      </span>
                    )}
                    {(comp.rating !== undefined && comp.rating !== null) && (
                      <span className="bg-warning/10 border border-warning/30 px-2 py-0.5 rounded text-warning font-semibold flex items-center gap-1">
                        <span>★ {comp.rating.toFixed(1)}</span>
                        {(comp.reviews_count || comp.rating_count) && (
                          <span className="text-text-muted font-normal text-[11px]">
                            ({(comp.reviews_count || comp.rating_count)! >= 1000
                              ? `${(((comp.reviews_count || comp.rating_count)!) / 1000).toFixed(1)}k reviews`
                              : `${comp.reviews_count || comp.rating_count} reviews`})
                          </span>
                        )}
                      </span>
                    )}
                    {isTop3 && (
                      <span className="bg-accent/10 border border-accent/30 text-accent font-semibold px-2 py-0.5 rounded text-[11px] uppercase tracking-wider">
                        Top Rank
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Right: Copy Button */}
              <div className="flex-shrink-0 flex items-center self-end sm:self-center">
                <button
                  type="button"
                  onClick={() => handleCopy(comp.title, idx)}
                  className="flex items-center gap-1.5 text-xs sm:text-sm font-medium text-text-muted hover:text-text px-2.5 py-1.5 rounded bg-surface hover:bg-surface-2 border border-border transition-colors cursor-pointer"
                  title="Copy this title"
                >
                  {isCopied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-success" />
                      <span className="text-success font-semibold">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
