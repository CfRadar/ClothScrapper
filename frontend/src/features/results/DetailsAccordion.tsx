import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { PlatformDetails } from "../../types";

export interface DetailsAccordionProps {
  details: PlatformDetails;
  platform: string;
}

export function DetailsAccordion({ details, platform }: DetailsAccordionProps) {
  const [open, setOpen] = useState(false);

  if (!details) return null;

  const hasAnyDetails =
    (details.attributes_to_fill && details.attributes_to_fill.length > 0) ||
    details.price_band ||
    (details.negative_keywords && details.negative_keywords.length > 0) ||
    (details.hashtags_or_tags && details.hashtags_or_tags.length > 0) ||
    details.competition_note ||
    details.seasonality_note ||
    details.notes;

  if (!hasAnyDetails) return null;

  return (
    <div className="border border-border rounded-input bg-surface overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-3.5 sm:p-4 text-xs sm:text-sm font-bold text-text uppercase tracking-wider hover:bg-surface-2/40 transition-colors cursor-pointer"
      >
        <span className="flex items-center gap-2">
          <span>Other Platform Factors & Guidelines</span>
        </span>
        {open ? (
          <ChevronUp className="w-4 h-4 text-text-muted" />
        ) : (
          <ChevronDown className="w-4 h-4 text-text-muted" />
        )}
      </button>

      {open && (
        <div className="p-4 pt-1 space-y-4 border-t border-border text-sm divide-y divide-border/60">
          {/* Attributes to fill */}
          {details.attributes_to_fill && details.attributes_to_fill.length > 0 && (
            <div className="pt-3 first:pt-0">
              <span className="text-xs font-bold text-text-muted uppercase tracking-wider block mb-2">
                Key Listing Attributes to Fill ({platform})
              </span>
              <div className="flex flex-wrap gap-2">
                {details.attributes_to_fill.map((attr, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center text-xs sm:text-sm bg-surface-2 border border-border px-2.5 py-1 rounded text-text font-medium"
                  >
                    {attr}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Price band & Seasonality */}
          {(details.price_band || details.seasonality_note) && (
            <div className="pt-3 grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {details.price_band && (
                <div>
                  <span className="text-xs font-bold text-text-muted uppercase tracking-wider block mb-1">
                    Recommended Price Band
                  </span>
                  <span className="text-sm font-semibold text-text bg-surface-2/60 px-3 py-1.5 rounded border border-border inline-block">
                    {details.price_band}
                  </span>
                </div>
              )}
              {details.seasonality_note && (
                <div>
                  <span className="text-xs font-bold text-text-muted uppercase tracking-wider block mb-1">
                    Seasonality
                  </span>
                  <span className="text-sm font-medium text-text bg-surface-2/60 px-3 py-1.5 rounded border border-border inline-block">
                    {details.seasonality_note}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Negative keywords */}
          {details.negative_keywords && details.negative_keywords.length > 0 && (
            <div className="pt-3">
              <span className="text-xs font-bold text-danger uppercase tracking-wider block mb-2">
                Negative / Avoid Keywords (Do Not Target)
              </span>
              <div className="flex flex-wrap gap-2">
                {details.negative_keywords.map((neg, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center text-xs sm:text-sm bg-danger/5 border border-danger/25 text-danger px-2.5 py-1 rounded font-medium"
                  >
                    - {neg}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Tags & Hashtags */}
          {details.hashtags_or_tags && details.hashtags_or_tags.length > 0 && (
            <div className="pt-3">
              <span className="text-xs font-bold text-text-muted uppercase tracking-wider block mb-2">
                Tags & Trend Hashtags
              </span>
              <div className="flex flex-wrap gap-2">
                {details.hashtags_or_tags.map((tag, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center text-xs sm:text-sm bg-accent/10 border border-accent/25 text-accent px-2.5 py-1 rounded font-medium"
                  >
                    {tag.startsWith("#") ? tag : `#${tag}`}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Competition */}
          {details.competition_note && (
            <div className="pt-3">
              <span className="text-xs font-bold text-text-muted uppercase tracking-wider block mb-1">
                Competition Dynamics
              </span>
              <p className="text-sm text-text leading-relaxed">
                {details.competition_note}
              </p>
            </div>
          )}

          {/* Platform notes */}
          {details.notes && (
            <div className="pt-3">
              <span className="text-xs font-bold text-text-muted uppercase tracking-wider block mb-1">
                Platform Rules & Notes
              </span>
              <p className="text-sm text-text-muted leading-relaxed">
                {details.notes}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
