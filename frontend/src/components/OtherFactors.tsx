import React, { useState } from 'react';
import { ShieldAlert, Tag, Compass, Info } from 'lucide-react';
import type { OtherFactors as OtherFactorsType, PlatformName } from '../types';

interface OtherFactorsProps {
  factors: OtherFactorsType;
}

export const OtherFactors: React.FC<OtherFactorsProps> = ({ factors }) => {
  const platforms = Object.keys(factors.per_platform) as PlatformName[];
  const [activeTab, setActiveTab] = useState<PlatformName>(platforms[0] || 'amazon');

  if (platforms.length === 0) return null;

  const currentPlatformFactors = factors.per_platform[activeTab] || factors.per_platform[platforms[0]];

  return (
    <div className="my-8 pt-8 border-t border-slate-800">
      <div className="flex items-center gap-2 mb-4">
        <Compass className="w-5 h-5 text-sky-400" />
        <h2 className="text-xl font-bold text-slate-100">Other factors</h2>
      </div>
      <p className="text-sm text-slate-400 mb-6">
        Strategic marketplace intelligence, recommended listing structures, price boundaries, and risk flags.
      </p>

      {/* Target Market Persona Summary Banner */}
      {factors.target_market_summary && (
        <div className="mb-6 p-4 rounded-xl bg-slate-900/90 border border-slate-800 text-sm text-slate-300 flex items-start gap-3">
          <Info className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
          <div>
            <strong className="text-slate-100 block mb-1">Target Market Persona</strong>
            <p className="leading-relaxed">{factors.target_market_summary}</p>
          </div>
        </div>
      )}

      {/* Platform Factors Card with Tabs */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 shadow-sm mb-6">
        {/* Platform Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3 mb-5">
          {platforms.map((p) => (
            <button
              type="button"
              key={p}
              onClick={() => setActiveTab(p)}
              className={`px-3.5 py-1.5 rounded-lg text-xs md:text-sm font-medium capitalize transition-all cursor-pointer ${
                activeTab === p
                  ? 'bg-slate-800 text-sky-400 border border-slate-700 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {p} Listing Strategy
            </button>
          ))}
        </div>

        {/* Selected Platform Factor Details */}
        {currentPlatformFactors && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-xs md:text-sm">
            {/* Title Formula & Example */}
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-xs uppercase font-semibold text-slate-400 block mb-1">
                  Recommended Title Formula
                </span>
                <p className="font-mono text-xs text-sky-300">
                  {currentPlatformFactors.title_formula}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-xs uppercase font-semibold text-slate-400 block mb-1">
                  Example Optimized Title
                </span>
                <p className="text-slate-200 leading-relaxed">
                  {currentPlatformFactors.recommended_title_example}
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-xs uppercase font-semibold text-slate-400 block mb-1">
                  Competitive Price Band
                </span>
                <p className="text-emerald-400 font-semibold">
                  {currentPlatformFactors.price_band}
                </p>
              </div>
            </div>

            {/* Attributes, Negative Keywords & Tags */}
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-xs uppercase font-semibold text-slate-400 block mb-1.5">
                  Core Attributes to Fill in Portal
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {currentPlatformFactors.attributes_to_fill.map((attr, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-xs text-slate-300"
                    >
                      {attr}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-xs uppercase font-semibold text-rose-400 flex items-center gap-1.5 mb-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" />
                  Negative Keywords (Avoid / Exclude)
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {currentPlatformFactors.negative_keywords.map((neg, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300"
                    >
                      ✕ {neg}
                    </span>
                  ))}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60">
                <span className="text-xs uppercase font-semibold text-slate-400 flex items-center gap-1.5 mb-1.5">
                  <Tag className="w-3.5 h-3.5" />
                  Search Tags & Themes
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {currentPlatformFactors.hashtags_or_tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-sky-950/40 border border-sky-800/60 text-xs text-sky-300"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* General Cross-Platform Rules */}
      {factors.general.length > 0 && (
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <strong className="text-xs uppercase tracking-wider text-slate-400 block mb-2">
            Cross-Platform Execution Guidelines
          </strong>
          <ul className="list-disc list-inside space-y-1 text-xs md:text-sm text-slate-300">
            {factors.general.map((note, idx) => (
              <li key={idx} className="leading-relaxed">
                {note}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
