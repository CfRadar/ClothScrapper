import React from 'react';
import { Zap, AlertCircle } from 'lucide-react';
import type { QuotaInfo } from '../types';

interface QuotaBadgeProps {
  quota: QuotaInfo | null;
  loading: boolean;
  error: string | null;
}

export const QuotaBadge: React.FC<QuotaBadgeProps> = ({ quota, loading, error }) => {
  if (loading) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1 bg-slate-800/80 border border-slate-700/60 rounded-full text-xs text-slate-400">
        <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse" />
        <span>Checking AI quota...</span>
      </div>
    );
  }

  if (error || !quota) {
    return (
      <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-950/40 border border-amber-800/60 rounded-full text-xs text-amber-300">
        <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
        <span>Quota unavailable</span>
      </div>
    );
  }

  const remaining = quota.remaining_today;
  const isLow = remaining < 10;
  const isOut = remaining <= 0;

  return (
    <div
      className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
        isOut
          ? 'bg-rose-950/40 border-rose-800/70 text-rose-300'
          : isLow
          ? 'bg-amber-950/40 border-amber-800/70 text-amber-300'
          : 'bg-slate-800/90 border-slate-700/80 text-slate-300'
      }`}
      title={`Active Model: ${quota.active_model} | Daily Limit: ${quota.daily_limit} calls`}
    >
      <Zap className={`w-3.5 h-3.5 ${isOut ? 'text-rose-400' : isLow ? 'text-amber-400' : 'text-sky-400'}`} />
      <span>
        <strong className="text-white">{remaining}</strong> AI calls left today
      </span>
    </div>
  );
};
