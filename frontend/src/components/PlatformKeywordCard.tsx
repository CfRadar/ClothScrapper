import React, { useState } from 'react';
import { ShoppingBag, Check } from 'lucide-react';
import type { PlatformKeywords, PlatformName } from '../types';
import { CopyButton } from './CopyButton';

interface PlatformKeywordCardProps {
  data: PlatformKeywords;
  isPatched?: boolean;
}

const PLATFORM_STYLES: Record<
  PlatformName,
  { name: string; border: string; badge: string; text: string; dot: string }
> = {
  amazon: {
    name: 'Amazon.in',
    border: 'border-amber-600/40 hover:border-amber-500/70',
    badge: 'bg-amber-950/40 text-amber-300 border-amber-800/60',
    text: 'text-amber-400',
    dot: 'bg-amber-400',
  },
  myntra: {
    name: 'Myntra',
    border: 'border-rose-600/40 hover:border-rose-500/70',
    badge: 'bg-rose-950/40 text-rose-300 border-rose-800/60',
    text: 'text-rose-400',
    dot: 'bg-rose-400',
  },
  flipkart: {
    name: 'Flipkart',
    border: 'border-blue-600/40 hover:border-blue-500/70',
    badge: 'bg-blue-950/40 text-blue-300 border-blue-800/60',
    text: 'text-blue-400',
    dot: 'bg-blue-400',
  },
};

export const PlatformKeywordCard: React.FC<PlatformKeywordCardProps> = ({
  data,
  isPatched = false,
}) => {
  const [copiedChip, setCopiedChip] = useState<string | null>(null);

  const style = PLATFORM_STYLES[data.platform] || {
    name: data.platform,
    border: 'border-slate-700',
    badge: 'bg-slate-800 text-slate-300',
    text: 'text-slate-300',
    dot: 'bg-slate-400',
  };

  const handleChipClick = async (kw: string) => {
    try {
      await navigator.clipboard.writeText(kw);
      setCopiedChip(kw);
      setTimeout(() => setCopiedChip(null), 1500);
    } catch {
      // Ignore
    }
  };

  return (
    <div
      className={`p-5 rounded-2xl bg-slate-900/95 border transition-all duration-300 shadow-sm ${
        isPatched ? 'ring-2 ring-emerald-500/80 bg-slate-900' : ''
      } ${style.border}`}
    >
      {/* Header: Platform Badge + Title + Copy All */}
      <div className="flex items-center justify-between gap-3 mb-4 pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-slate-800/80 text-slate-300">
            <ShoppingBag className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              {style.name}
              <span className={`px-2 py-0.5 text-[11px] rounded-full font-mono border ${style.badge}`}>
                {data.keywords.length} keywords
              </span>
            </h3>
          </div>
        </div>

        {/* Copy All Button (Comma-separated) */}
        <CopyButton
          textToCopy={data.keywords}
          label="Copy all"
          size="sm"
        />
      </div>

      {/* Keywords Chips Container (ONLY chips, NO extra clutter) */}
      <ul className="flex flex-wrap gap-2">
        {data.keywords.map((kw, idx) => {
          const isCopied = copiedChip === kw;
          return (
            <li key={idx}>
              <button
                type="button"
                onClick={() => handleChipClick(kw)}
                title="Click to copy single keyword"
                className={`group flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs md:text-sm font-medium border transition-all cursor-pointer ${
                  isCopied
                    ? 'bg-emerald-950/60 border-emerald-500/80 text-emerald-300 shadow-sm'
                    : 'bg-slate-800/80 border-slate-700/70 text-slate-200 hover:bg-slate-700 hover:border-slate-600'
                }`}
              >
                <span>{kw}</span>
                {isCopied && <Check className="w-3 h-3 text-emerald-400 shrink-0" />}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
};
